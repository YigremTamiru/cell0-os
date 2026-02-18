"""
cell0/engine/security/secrets.py - Secrets Management System

Production-grade secrets management for Cell 0 OS:
- 1Password CLI integration for production
- Environment variable fallback for development
- Encrypted TPV (Twin Prime Vectors) store at rest
- Secret rotation support
- Secure memory handling
- Audit logging for secret access
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("cell0.security.secrets")


# ============================================================================
# Configuration
# ============================================================================

class SecretsConfig:
    """Secrets management configuration"""
    # 1Password settings
    ONEPASSWORD_ENABLED: bool = os.environ.get("CELL0_1PASSWORD_ENABLED", "false").lower() == "true"
    ONEPASSWORD_VAULT: str = os.environ.get("CELL0_1PASSWORD_VAULT", "Cell0")
    ONEPASSWORD_ACCOUNT: Optional[str] = os.environ.get("CELL0_1PASSWORD_ACCOUNT")
    
    # Encryption settings
    MASTER_KEY_ENV: str = "CELL0_MASTER_KEY"
    KEY_DERIVATION_ITERATIONS: int = 480000
    
    # Storage settings
    TPV_STORE_PATH: Path = Path(os.environ.get("CELL0_TPV_STORE", "~/.cell0/tpv_store.enc")).expanduser()
    BACKUP_STORE_PATH: Path = Path(os.environ.get("CELL0_TPV_BACKUP", "~/.cell0/tpv_backup.enc")).expanduser()
    
    # Security settings
    SECRET_CACHE_TTL: int = int(os.environ.get("CELL0_SECRET_CACHE_TTL", "300"))  # 5 minutes
    AUDIT_LOG_ACCESS: bool = os.environ.get("CELL0_AUDIT_SECRETS", "true").lower() == "true"
    
    @classmethod
    def get_master_key(cls) -> Optional[bytes]:
        """Get master encryption key from environment"""
        key = os.environ.get(cls.MASTER_KEY_ENV)
        if key:
            return key.encode()
        return None


# ============================================================================
# Exceptions
# ============================================================================

class SecretsError(Exception):
    """Base secrets error"""
    pass


class SecretNotFoundError(SecretsError):
    """Secret not found"""
    pass


class SecretAccessDeniedError(SecretsError):
    """Access to secret denied"""
    pass


class EncryptionError(SecretsError):
    """Encryption/decryption error"""
    pass


class OnePasswordError(SecretsError):
    """1Password CLI error"""
    pass


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SecretMetadata:
    """Metadata for a secret"""
    name: str
    source: str  # '1password', 'env', 'tpv'
    created_at: datetime
    updated_at: datetime
    version: int = 1
    tags: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "tags": self.tags,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_count": self.access_count,
        }


@dataclass
class SecretValue:
    """Secret value with metadata"""
    value: str
    metadata: SecretMetadata
    
    def __str__(self) -> str:
        return "***REDACTED***"
    
    def reveal(self) -> str:
        """Get the actual secret value"""
        return self.value


# ============================================================================
# Backends
# ============================================================================

class SecretsBackend(ABC):
    """Abstract base class for secrets backends"""
    
    @abstractmethod
    async def get(self, name: str) -> Optional[SecretValue]:
        """Get a secret by name"""
        pass
    
    @abstractmethod
    async def set(self, name: str, value: str, metadata: Optional[Dict] = None) -> bool:
        """Set a secret"""
        pass
    
    @abstractmethod
    async def delete(self, name: str) -> bool:
        """Delete a secret"""
        pass
    
    @abstractmethod
    async def list_secrets(self) -> List[str]:
        """List all secret names"""
        pass


class EnvironmentBackend(SecretsBackend):
    """Environment variable secrets backend"""
    
    PREFIX = "CELL0_SECRET_"
    
    async def get(self, name: str) -> Optional[SecretValue]:
        """Get secret from environment"""
        env_name = f"{self.PREFIX}{name.upper()}"
        value = os.environ.get(env_name)
        
        if not value:
            # Also try without prefix for common vars
            value = os.environ.get(name.upper())
        
        if value:
            return SecretValue(
                value=value,
                metadata=SecretMetadata(
                    name=name,
                    source="env",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
        return None
    
    async def set(self, name: str, value: str, metadata: Optional[Dict] = None) -> bool:
        """Cannot set env vars programmatically"""
        raise SecretsError("Cannot set environment variables programmatically")
    
    async def delete(self, name: str) -> bool:
        """Cannot delete env vars programmatically"""
        raise SecretsError("Cannot delete environment variables programmatically")
    
    async def list_secrets(self) -> List[str]:
        """List secrets from environment"""
        return [
            k[len(self.PREFIX):].lower()
            for k in os.environ.keys()
            if k.startswith(self.PREFIX)
        ]


class OnePasswordBackend(SecretsBackend):
    """1Password CLI secrets backend"""
    
    def __init__(self, vault: Optional[str] = None, account: Optional[str] = None):
        self.vault = vault or SecretsConfig.ONEPASSWORD_VAULT
        self.account = account or SecretsConfig.ONEPASSWORD_ACCOUNT
        self._cache: Dict[str, Tuple[SecretValue, float]] = {}
        self._lock = asyncio.Lock()
    
    def _op(self, *args) -> Tuple[int, str, str]:
        """Execute 1Password CLI command"""
        cmd = ["op"]
        if self.account:
            cmd.extend(["--account", self.account])
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise OnePasswordError("1Password CLI command timed out")
        except FileNotFoundError:
            raise OnePasswordError("1Password CLI (op) not found. Install from https://1password.com/downloads/command-line/")
    
    async def _op_async(self, *args) -> Tuple[int, str, str]:
        """Execute 1Password CLI command asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._op, *args)
    
    async def get(self, name: str) -> Optional[SecretValue]:
        """Get secret from 1Password"""
        # Check cache
        cached = self._cache.get(name)
        if cached:
            value, cached_at = cached
            if time.time() - cached_at < SecretsConfig.SECRET_CACHE_TTL:
                return value
        
        # Fetch from 1Password
        code, stdout, stderr = await self._op_async(
            "item", "get", name,
            "--vault", self.vault,
            "--format", "json"
        )
        
        if code != 0:
            if "not found" in stderr.lower():
                return None
            raise OnePasswordError(f"Failed to get secret: {stderr}")
        
        try:
            data = json.loads(stdout)
            # Extract password field
            password = None
            for field in data.get("fields", []):
                if field.get("purpose") == "PASSWORD":
                    password = field.get("value")
                    break
            
            if not password:
                raise OnePasswordError(f"No password field found for {name}")
            
            secret = SecretValue(
                value=password,
                metadata=SecretMetadata(
                    name=name,
                    source="1password",
                    created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
                    version=data.get("version", 1),
                    tags=data.get("tags", []),
                )
            )
            
            # Cache result
            async with self._lock:
                self._cache[name] = (secret, time.time())
            
            return secret
            
        except json.JSONDecodeError as e:
            raise OnePasswordError(f"Invalid JSON response: {e}")
    
    async def set(self, name: str, value: str, metadata: Optional[Dict] = None) -> bool:
        """Create or update secret in 1Password"""
        tags = metadata.get("tags", []) if metadata else []
        
        code, stdout, stderr = await self._op_async(
            "item", "create",
            "--category", "password",
            "--vault", self.vault,
            f"password={value}",
            f"title={name}",
            *[f"--tags={tag}" for tag in tags]
        )
        
        if code != 0:
            raise OnePasswordError(f"Failed to set secret: {stderr}")
        
        # Invalidate cache
        async with self._lock:
            self._cache.pop(name, None)
        
        return True
    
    async def delete(self, name: str) -> bool:
        """Delete secret from 1Password"""
        code, stdout, stderr = await self._op_async(
            "item", "delete", name,
            "--vault", self.vault
        )
        
        if code != 0:
            if "not found" in stderr.lower():
                return False
            raise OnePasswordError(f"Failed to delete secret: {stderr}")
        
        # Invalidate cache
        async with self._lock:
            self._cache.pop(name, None)
        
        return True
    
    async def list_secrets(self) -> List[str]:
        """List secrets from 1Password"""
        code, stdout, stderr = await self._op_async(
            "item", "list",
            "--vault", self.vault,
            "--format", "json"
        )
        
        if code != 0:
            raise OnePasswordError(f"Failed to list secrets: {stderr}")
        
        try:
            items = json.loads(stdout)
            return [item.get("title") for item in items]
        except json.JSONDecodeError:
            return []


class EncryptedTPVBackend(SecretsBackend):
    """Encrypted Twin Prime Vectors store backend"""
    
    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or SecretsConfig.TPV_STORE_PATH
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._cipher: Optional[Fernet] = None
        
        # Initialize encryption
        self._init_cipher()
        
        # Load existing data
        self._load()
    
    def _init_cipher(self):
        """Initialize encryption cipher"""
        master_key = SecretsConfig.get_master_key()
        if not master_key:
            logger.warning("No master key set - TPV store will not be encrypted")
            return
        
        # Derive encryption key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"cell0_tpv_salt_v1",  # In production, use random salt stored separately
            iterations=SecretsConfig.KEY_DERIVATION_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        self._cipher = Fernet(key)
    
    def _load(self):
        """Load encrypted store from disk"""
        if not self.store_path.exists():
            return
        
        try:
            with open(self.store_path, "rb") as f:
                encrypted = f.read()
            
            if self._cipher:
                decrypted = self._cipher.decrypt(encrypted)
                self._data = json.loads(decrypted.decode())
            else:
                # Unencrypted fallback
                self._data = json.loads(encrypted.decode())
                
        except Exception as e:
            logger.error(f"Failed to load TPV store: {e}")
            self._data = {}
    
    def _save(self):
        """Save encrypted store to disk"""
        try:
            json_data = json.dumps(self._data).encode()
            
            if self._cipher:
                encrypted = self._cipher.encrypt(json_data)
            else:
                encrypted = json_data
            
            # Write to temp file first
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.store_path.parent,
                delete=False,
                prefix=".tpv_",
                suffix=".tmp"
            ) as f:
                f.write(encrypted)
                temp_path = f.name
            
            # Atomic rename
            os.replace(temp_path, self.store_path)
            
        except Exception as e:
            logger.error(f"Failed to save TPV store: {e}")
            raise EncryptionError(f"Failed to save TPV store: {e}")
    
    async def get(self, name: str) -> Optional[SecretValue]:
        """Get secret from TPV store"""
        async with self._lock:
            entry = self._data.get(name)
            if not entry:
                return None
            
            # Update access metadata
            entry["metadata"]["last_accessed_at"] = datetime.utcnow().isoformat()
            entry["metadata"]["access_count"] = entry["metadata"].get("access_count", 0) + 1
            
            return SecretValue(
                value=entry["value"],
                metadata=SecretMetadata(
                    name=name,
                    source="tpv",
                    created_at=datetime.fromisoformat(entry["metadata"]["created_at"]),
                    updated_at=datetime.fromisoformat(entry["metadata"]["updated_at"]),
                    version=entry["metadata"].get("version", 1),
                    tags=entry["metadata"].get("tags", []),
                    expires_at=datetime.fromisoformat(entry["metadata"]["expires_at"]) if entry["metadata"].get("expires_at") else None,
                    last_accessed_at=datetime.utcnow(),
                    access_count=entry["metadata"]["access_count"],
                )
            )
    
    async def set(self, name: str, value: str, metadata: Optional[Dict] = None) -> bool:
        """Set secret in TPV store"""
        async with self._lock:
            now = datetime.utcnow()
            
            # Get existing or create new
            if name in self._data:
                entry = self._data[name]
                entry["value"] = value
                entry["metadata"]["updated_at"] = now.isoformat()
                entry["metadata"]["version"] = entry["metadata"].get("version", 1) + 1
            else:
                entry = {
                    "value": value,
                    "metadata": {
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "version": 1,
                        "tags": metadata.get("tags", []) if metadata else [],
                        "expires_at": metadata.get("expires_at") if metadata else None,
                        "access_count": 0,
                    }
                }
                self._data[name] = entry
            
            # Save to disk
            self._save()
            
            return True
    
    async def delete(self, name: str) -> bool:
        """Delete secret from TPV store"""
        async with self._lock:
            if name not in self._data:
                return False
            
            del self._data[name]
            self._save()
            return True
    
    async def list_secrets(self) -> List[str]:
        """List secrets in TPV store"""
        async with self._lock:
            return list(self._data.keys())
    
    async def rotate_key(self, new_master_key: bytes):
        """Rotate encryption key"""
        async with self._lock:
            # Save current data
            old_data = self._data.copy()
            
            # Re-initialize with new key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"cell0_tpv_salt_v1",
                iterations=SecretsConfig.KEY_DERIVATION_ITERATIONS,
            )
            key = base64.urlsafe_b64encode(kdf.derive(new_master_key))
            self._cipher = Fernet(key)
            
            # Save with new encryption
            self._save()
            
            logger.info("TPV store encryption key rotated successfully")


# ============================================================================
# Secrets Manager
# ============================================================================

class SecretsManager:
    """Unified secrets manager with fallback chain"""
    
    def __init__(
        self,
        backends: Optional[List[SecretsBackend]] = None,
        audit_log: bool = True,
    ):
        # Default backend chain: 1Password -> TPV -> Environment
        if backends is None:
            backends = []
            
            if SecretsConfig.ONEPASSWORD_ENABLED:
                try:
                    backends.append(OnePasswordBackend())
                    logger.info("1Password backend enabled")
                except Exception as e:
                    logger.warning(f"Failed to initialize 1Password backend: {e}")
            
            backends.append(EncryptedTPVBackend())
            backends.append(EnvironmentBackend())
        
        self.backends = backends
        self.audit_log = audit_log
        self._access_log: List[Dict] = []
    
    def _log_access(self, name: str, source: str, success: bool):
        """Log secret access"""
        if not self.audit_log:
            return
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "secret_name": name,
            "source": source,
            "success": success,
        }
        
        self._access_log.append(entry)
        logger.debug(f"Secret access: {name} from {source} (success={success})")
    
    async def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret with fallback chain"""
        for backend in self.backends:
            try:
                secret = await backend.get(name)
                if secret:
                    self._log_access(name, secret.metadata.source, True)
                    return secret.value
            except Exception as e:
                logger.debug(f"Backend {type(backend).__name__} failed for {name}: {e}")
                continue
        
        self._log_access(name, "none", False)
        return default
    
    async def require(self, name: str) -> str:
        """Get required secret, raise if not found"""
        value = await self.get(name)
        if value is None:
            raise SecretNotFoundError(f"Required secret '{name}' not found")
        return value
    
    async def set(
        self,
        name: str,
        value: str,
        backend: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Set secret in specified or first available backend"""
        if backend:
            # Find specific backend
            for b in self.backends:
                if b.__class__.__name__.lower().startswith(backend.lower()):
                    return await b.set(name, value, metadata)
            raise SecretsError(f"Backend '{backend}' not found")
        
        # Try first writable backend
        for b in self.backends:
            try:
                if await b.set(name, value, metadata):
                    return True
            except Exception as e:
                logger.debug(f"Backend {type(b).__name__} failed to set {name}: {e}")
                continue
        
        raise SecretsError(f"No backend available to set secret '{name}'")
    
    async def delete(self, name: str, backend: Optional[str] = None) -> bool:
        """Delete secret"""
        if backend:
            for b in self.backends:
                if b.__class__.__name__.lower().startswith(backend.lower()):
                    return await b.delete(name)
            raise SecretsError(f"Backend '{backend}' not found")
        
        # Delete from all backends
        deleted = False
        for b in self.backends:
            try:
                if await b.delete(name):
                    deleted = True
            except Exception as e:
                logger.debug(f"Backend {type(b).__name__} failed to delete {name}: {e}")
        
        return deleted
    
    async def list_secrets(self) -> List[str]:
        """List all secrets from all backends"""
        secrets = set()
        for backend in self.backends:
            try:
                secrets.update(await backend.list_secrets())
            except Exception as e:
                logger.debug(f"Backend {type(backend).__name__} failed to list: {e}")
        return sorted(secrets)
    
    def get_access_log(self) -> List[Dict]:
        """Get audit log of secret access"""
        return self._access_log.copy()


# ============================================================================
# Global Instance
# ============================================================================

_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def set_secrets_manager(manager: SecretsManager):
    """Set global secrets manager"""
    global _secrets_manager
    _secrets_manager = manager


# ============================================================================
# Convenience Functions
# ============================================================================

async def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get secret value"""
    return await get_secrets_manager().get(name, default)


async def require_secret(name: str) -> str:
    """Get required secret"""
    return await get_secrets_manager().require(name)


async def set_secret(name: str, value: str, **kwargs) -> bool:
    """Set secret value"""
    return await get_secrets_manager().set(name, value, **kwargs)


async def delete_secret(name: str) -> bool:
    """Delete secret"""
    return await get_secrets_manager().delete(name)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Config
    'SecretsConfig',
    # Exceptions
    'SecretsError',
    'SecretNotFoundError',
    'SecretAccessDeniedError',
    'EncryptionError',
    'OnePasswordError',
    # Data Classes
    'SecretMetadata',
    'SecretValue',
    # Backends
    'SecretsBackend',
    'EnvironmentBackend',
    'OnePasswordBackend',
    'EncryptedTPVBackend',
    # Manager
    'SecretsManager',
    # Global
    'get_secrets_manager',
    'set_secrets_manager',
    # Convenience
    'get_secret',
    'require_secret',
    'set_secret',
    'delete_secret',
]

import time
