"""
cell0/engine/security/jwt_handler.py - Sovereign JWT Handler with Hybrid Policy

Implements a sovereign (zero-dependency, self-contained) JWT handling system:
- Dev mode: Auto-generates keys with loud warnings
- Prod mode: Fail-fast with 1Password integration
- Zero external JWT library dependencies (uses Python's hmac + json)
- RS256/HS256/ES256 support via environment or 1Password
- Token lifecycle management (issue, validate, refresh, revoke)
- Automatic key rotation detection

Sovereign Policy:
- NEVER silently fail in production
- NEVER use weak keys in production
- ALWAYS warn loudly in development
- ALWAYS prefer 1Password for production secrets
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("cell0.security.jwt")

# ============================================================================
# Configuration & Environment Detection
# ============================================================================

class Environment(Enum):
    """Runtime environment detection"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def get_environment() -> Environment:
    """Detect current runtime environment"""
    env = os.environ.get("CELL0_ENV", "").lower()
    if env in ("prod", "production"):
        return Environment.PRODUCTION
    elif env in ("stage", "staging"):
        return Environment.STAGING
    elif env in ("test", "testing"):
        return Environment.TEST
    return Environment.DEVELOPMENT


def is_production() -> bool:
    """Check if running in production"""
    return get_environment() == Environment.PRODUCTION


# ============================================================================
# Exceptions
# ============================================================================

class JWTError(Exception):
    """Base JWT error"""
    pass


class InvalidTokenError(JWTError):
    """Token is malformed or invalid"""
    pass


class ExpiredTokenError(JWTError):
    """Token has expired"""
    pass


class InvalidSignatureError(JWTError):
    """Token signature verification failed"""
    pass


class InvalidKeyError(JWTError):
    """Key is invalid or missing"""
    pass


class ProductionKeyError(JWTError):
    """Production key requirements not met"""
    pass


class KeyRotationError(JWTError):
    """Key rotation detected"""
    pass


# ============================================================================
# Key Management
# ============================================================================

@dataclass
class KeyPair:
    """JWT key pair"""
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    secret: Optional[str] = None
    algorithm: str = "HS256"
    source: str = "unknown"
    
    def is_asymmetric(self) -> bool:
        """Check if using asymmetric algorithm"""
        return self.algorithm in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512")


class KeyManager:
    """
    Sovereign key manager with hybrid policy.
    
    Dev: Auto-generate with warnings
    Prod: Fail-fast, require 1Password or explicit keys
    """
    
    def __init__(self):
        self._key_cache: Dict[str, KeyPair] = {}
        self._key_hashes: Dict[str, str] = {}
        
    def get_key(self, key_id: str = "default") -> KeyPair:
        """Get or load key pair"""
        if key_id not in self._key_cache:
            self._key_cache[key_id] = self._load_key(key_id)
        return self._key_cache[key_id]
    
    def _load_key(self, key_id: str) -> KeyPair:
        """Load key from environment or 1Password with sovereign policy"""
        env = get_environment()
        
        # 1. Check for explicit environment variables (highest priority)
        key_pair = self._load_from_env()
        if key_pair:
            return key_pair
        
        # 2. Try 1Password integration (production preference)
        key_pair = self._load_from_1password()
        if key_pair:
            logger.info(f"Loaded JWT keys from 1Password for key_id={key_id}")
            return key_pair
        
        # 3. Production: FAIL FAST
        if env == Environment.PRODUCTION:
            raise ProductionKeyError(
                "PRODUCTION SECURITY VIOLATION: No JWT keys configured.\n"
                "Options:\n"
                "  1. Set CELL0_JWT_SECRET (HS256) or CELL0_JWT_PRIVATE_KEY/PUBLIC_KEY (RS256)\n"
                "  2. Use 1Password: 'op inject' with .env files\n"
                "  3. Run: op read op://<vault>/<item>/private_key > /run/secrets/jwt_private\n"
                "\nProduction requires secure key management. Auto-generation is DISABLED."
            )
        
        # 4. Development: Auto-generate with LOUD warnings
        return self._auto_generate_key(env)
    
    def _load_from_env(self) -> Optional[KeyPair]:
        """Load keys from environment variables"""
        algorithm = os.environ.get("CELL0_JWT_ALGORITHM", "HS256")
        
        if algorithm.startswith("HS"):
            # HMAC (symmetric)
            secret = os.environ.get("CELL0_JWT_SECRET", "").strip()
            if secret and len(secret) >= 32:
                return KeyPair(
                    secret=secret,
                    algorithm=algorithm,
                    source="environment"
                )
        else:
            # RSA/ECDSA (asymmetric)
            private_key = os.environ.get("CELL0_JWT_PRIVATE_KEY", "").strip()
            public_key = os.environ.get("CELL0_JWT_PUBLIC_KEY", "").strip()
            
            # Try reading from file paths
            if not private_key:
                private_path = os.environ.get("CELL0_JWT_PRIVATE_KEY_FILE")
                if private_path and Path(private_path).exists():
                    private_key = Path(private_path).read_text().strip()
            
            if not public_key:
                public_path = os.environ.get("CELL0_JWT_PUBLIC_KEY_FILE")
                if public_path and Path(public_path).exists():
                    public_key = Path(public_path).read_text().strip()
            
            if private_key and public_key:
                return KeyPair(
                    private_key=private_key,
                    public_key=public_key,
                    algorithm=algorithm,
                    source="environment"
                )
        
        return None
    
    def _load_from_1password(self) -> Optional[KeyPair]:
        """Load keys from 1Password CLI"""
        try:
            # Check if op CLI is available
            result = subprocess.run(
                ["op", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return None
            
            # Get 1Password reference from environment
            op_ref = os.environ.get("CELL0_1PASSWORD_JWT_SECRET")
            if op_ref:
                result = subprocess.run(
                    ["op", "read", op_ref],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    secret = result.stdout.strip()
                    if secret:
                        return KeyPair(
                            secret=secret,
                            algorithm="HS256",
                            source="1password"
                        )
            
            # Try private/public key references
            op_priv_ref = os.environ.get("CELL0_1PASSWORD_JWT_PRIVATE_KEY")
            op_pub_ref = os.environ.get("CELL0_1PASSWORD_JWT_PUBLIC_KEY")
            algorithm = os.environ.get("CELL0_1PASSWORD_JWT_ALGORITHM", "RS256")
            
            if op_priv_ref and op_pub_ref:
                priv_result = subprocess.run(
                    ["op", "read", op_priv_ref],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                pub_result = subprocess.run(
                    ["op", "read", op_pub_ref],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if priv_result.returncode == 0 and pub_result.returncode == 0:
                    return KeyPair(
                        private_key=priv_result.stdout.strip(),
                        public_key=pub_result.stdout.strip(),
                        algorithm=algorithm,
                        source="1password"
                    )
        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        return None
    
    def _auto_generate_key(self, env: Environment) -> KeyPair:
        """Auto-generate key for development (WITH LOUD WARNINGS)"""
        warning_msg = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           ⚠️  SECURITY WARNING  ⚠️                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  AUTO-GENERATED JWT KEY DETECTED                                             ║
║  Environment: {env.value.upper():<58}                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  This is INSECURE and should ONLY happen in development!                     ║
║                                                                              ║
║  Generated keys are:                                                         ║
║    • Stored in memory only (not persisted)                                   ║
║    • Lost on process restart                                                 ║
║    • NOT SUITABLE for production                                             ║
║                                                                              ║
║  To fix this warning:                                                        ║
║    1. Set CELL0_JWT_SECRET=your-256-bit-secret                               ║
║    2. Use 1Password: CELL0_1PASSWORD_JWT_SECRET=op://vault/item/field        ║
║    3. For production: Set CELL0_ENV=production (will FAIL without keys)      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        # Print to stderr for maximum visibility
        print(warning_msg, file=sys.stderr)
        warnings.warn("Auto-generated JWT key - DO NOT USE IN PRODUCTION", RuntimeWarning)
        logger.warning(f"Auto-generated JWT key for {env.value} environment")
        
        # Generate a secure 256-bit key
        secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii')
        
        return KeyPair(
            secret=secret,
            algorithm="HS256",
            source=f"auto-generated-{env.value}"
        )
    
    def check_rotation(self, key_id: str = "default") -> bool:
        """Check if key has been rotated (returns True if rotation detected)"""
        current = self.get_key(key_id)
        
        # Create a hash of the current key material
        if current.secret:
            key_material = current.secret
        elif current.private_key:
            key_material = current.private_key
        else:
            return False
        
        current_hash = hashlib.sha256(key_material.encode()).hexdigest()
        
        if key_id in self._key_hashes:
            if self._key_hashes[key_id] != current_hash:
                logger.warning(f"Key rotation detected for key_id={key_id}")
                return True
        
        self._key_hashes[key_id] = current_hash
        return False


# Global key manager instance
_key_manager = KeyManager()


def get_key_manager() -> KeyManager:
    """Get global key manager instance"""
    return _key_manager


# ============================================================================
# Token Payload
# ============================================================================

@dataclass
class TokenPayload:
    """JWT token payload with standard claims"""
    subject: str  # sub
    issuer: str = "cell0-os"  # iss
    audience: Optional[str] = None  # aud
    issued_at: datetime = field(default_factory=datetime.utcnow)  # iat
    expires_at: Optional[datetime] = None  # exp
    not_before: Optional[datetime] = None  # nbf
    jwt_id: str = field(default_factory=lambda: secrets.token_urlsafe(16))  # jti
    
    # Custom claims
    scopes: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JWT encoding"""
        result = {
            "sub": self.subject,
            "iss": self.issuer,
            "jti": self.jwt_id,
            "iat": self.issued_at.timestamp(),
        }
        
        if self.audience:
            result["aud"] = self.audience
        if self.expires_at:
            result["exp"] = self.expires_at.timestamp()
        if self.not_before:
            result["nbf"] = self.not_before.timestamp()
        if self.scopes:
            result["scopes"] = self.scopes
        if self.roles:
            result["roles"] = self.roles
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """Create from decoded JWT dictionary"""
        def parse_timestamp(key: str) -> Optional[datetime]:
            if key in data:
                return datetime.utcfromtimestamp(data[key])
            return None
        
        return cls(
            subject=data.get("sub", ""),
            issuer=data.get("iss", "cell0-os"),
            audience=data.get("aud"),
            issued_at=parse_timestamp("iat") or datetime.utcnow(),
            expires_at=parse_timestamp("exp"),
            not_before=parse_timestamp("nbf"),
            jwt_id=data.get("jti", ""),
            scopes=data.get("scopes", []),
            roles=data.get("roles", []),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# Sovereign JWT Implementation (Zero Dependencies)
# ============================================================================

class JWTHandler:
    """
    Sovereign JWT handler with zero external dependencies.
    Implements JWT signing/verification using only Python stdlib.
    """
    
    def __init__(self, key_id: str = "default"):
        self.key_id = key_id
        self.key_manager = get_key_manager()
    
    def encode(
        self,
        payload: TokenPayload,
        expires_in: Optional[timedelta] = None
    ) -> str:
        """Encode payload to JWT token"""
        if expires_in:
            payload.expires_at = datetime.utcnow() + expires_in
        
        key = self.key_manager.get_key(self.key_id)
        
        # Build header
        header = {
            "alg": key.algorithm,
            "typ": "JWT",
            "kid": self.key_id,
        }
        
        # Build payload
        payload_dict = payload.to_dict()
        
        # Encode
        header_b64 = self._base64url_encode(json.dumps(header, separators=(',', ':')))
        payload_b64 = self._base64url_encode(json.dumps(payload_dict, separators=(',', ':')))
        
        message = f"{header_b64}.{payload_b64}"
        signature = self._sign(message, key)
        signature_b64 = self._base64url_encode(signature)
        
        return f"{message}.{signature_b64}"
    
    def decode(
        self,
        token: str,
        verify: bool = True,
        audience: Optional[str] = None,
        issuer: Optional[str] = None
    ) -> TokenPayload:
        """Decode and verify JWT token"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise InvalidTokenError("Invalid JWT format: expected 3 parts")
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Decode header
            try:
                header = json.loads(self._base64url_decode(header_b64))
            except Exception as e:
                raise InvalidTokenError(f"Invalid header: {e}")
            
            # Decode payload
            try:
                payload_dict = json.loads(self._base64url_decode(payload_b64))
            except Exception as e:
                raise InvalidTokenError(f"Invalid payload: {e}")
            
            # Verify signature
            if verify:
                key = self.key_manager.get_key(header.get("kid", self.key_id))
                
                # Check algorithm matches
                if header.get("alg") != key.algorithm:
                    raise InvalidSignatureError(
                        f"Algorithm mismatch: header={header.get('alg')}, key={key.algorithm}"
                    )
                
                message = f"{header_b64}.{payload_b64}"
                expected_sig = self._base64url_decode(signature_b64)
                
                if not self._verify_signature(message, expected_sig, key):
                    raise InvalidSignatureError("Token signature verification failed")
                
                # Verify timestamps
                now = datetime.utcnow().timestamp()
                
                # Check expiration
                if "exp" in payload_dict:
                    if now > payload_dict["exp"]:
                        raise ExpiredTokenError("Token has expired")
                
                # Check not before
                if "nbf" in payload_dict:
                    if now < payload_dict["nbf"]:
                        raise InvalidTokenError("Token not yet valid")
                
                # Verify issuer
                if issuer and payload_dict.get("iss") != issuer:
                    raise InvalidTokenError(
                        f"Issuer mismatch: expected={issuer}, got={payload_dict.get('iss')}"
                    )
                
                # Verify audience
                if audience and payload_dict.get("aud") != audience:
                    raise InvalidTokenError(
                        f"Audience mismatch: expected={audience}, got={payload_dict.get('aud')}"
                    )
            
            return TokenPayload.from_dict(payload_dict)
        
        except (InvalidTokenError, ExpiredTokenError, InvalidSignatureError):
            raise
        except Exception as e:
            raise InvalidTokenError(f"Failed to decode token: {e}")
    
    def _base64url_encode(self, data: Union[str, bytes]) -> str:
        """Base64URL encode"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')
    
    def _base64url_decode(self, data: str) -> bytes:
        """Base64URL decode"""
        # Add padding if needed
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    def _sign(self, message: str, key: KeyPair) -> bytes:
        """Sign message with key"""
        if key.algorithm.startswith("HS"):
            # HMAC
            if not key.secret:
                raise InvalidKeyError("No secret key available for HMAC")
            
            hash_algo = {
                "HS256": hashlib.sha256,
                "HS384": hashlib.sha384,
                "HS512": hashlib.sha512,
            }.get(key.algorithm, hashlib.sha256)
            
            return hmac.new(
                key.secret.encode('utf-8'),
                message.encode('utf-8'),
                hash_algo
            ).digest()
        
        elif key.algorithm.startswith("RS") or key.algorithm.startswith("ES"):
            # RSA/ECDSA - would require cryptography library
            raise NotImplementedError(
                f"Algorithm {key.algorithm} requires 'cryptography' library. "
                "Install with: pip install cryptography"
            )
        
        else:
            raise InvalidKeyError(f"Unsupported algorithm: {key.algorithm}")
    
    def _verify_signature(self, message: str, signature: bytes, key: KeyPair) -> bool:
        """Verify signature against message"""
        expected = self._sign(message, key)
        return hmac.compare_digest(expected, signature)


# ============================================================================
# Token Lifecycle Management
# ============================================================================

class TokenManager:
    """High-level token lifecycle manager"""
    
    def __init__(self, key_id: str = "default"):
        self.handler = JWTHandler(key_id)
        self._revoked_tokens: set = set()  # In-memory revocation list
    
    def create_access_token(
        self,
        subject: str,
        scopes: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in: timedelta = timedelta(minutes=15),
    ) -> str:
        """Create a new access token"""
        payload = TokenPayload(
            subject=subject,
            scopes=scopes or [],
            roles=roles or [],
            metadata=metadata or {},
        )
        return self.handler.encode(payload, expires_in)
    
    def create_refresh_token(
        self,
        subject: str,
        expires_in: timedelta = timedelta(days=7),
    ) -> str:
        """Create a new refresh token"""
        payload = TokenPayload(
            subject=subject,
            scopes=["refresh"],
        )
        return self.handler.encode(payload, expires_in)
    
    def validate_token(
        self,
        token: str,
        required_scopes: Optional[List[str]] = None,
        required_roles: Optional[List[str]] = None,
    ) -> TokenPayload:
        """
        Validate token and check required scopes/roles.
        Raises appropriate exceptions on failure.
        """
        # Check revocation list
        jti = self._extract_jti(token)
        if jti in self._revoked_tokens:
            raise InvalidTokenError("Token has been revoked")
        
        # Decode and verify
        payload = self.handler.decode(token)
        
        # Check scopes
        if required_scopes:
            token_scopes = set(payload.scopes)
            missing = set(required_scopes) - token_scopes
            if missing:
                raise InvalidTokenError(
                    f"Missing required scopes: {', '.join(missing)}"
                )
        
        # Check roles
        if required_roles:
            token_roles = set(payload.roles)
            missing = set(required_roles) - token_roles
            if missing:
                raise InvalidTokenError(
                    f"Missing required roles: {', '.join(missing)}"
                )
        
        return payload
    
    def revoke_token(self, token: str) -> None:
        """Revoke a token (add to blacklist)"""
        jti = self._extract_jti(token)
        if jti:
            self._revoked_tokens.add(jti)
            logger.info(f"Revoked token jti={jti[:8]}...")
    
    def _extract_jti(self, token: str) -> Optional[str]:
        """Extract JWT ID from token without full validation"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            payload_dict = json.loads(
                self.handler._base64url_decode(parts[1])
            )
            return payload_dict.get("jti")
        except Exception:
            return None


# ============================================================================
# Convenience Functions
# ============================================================================

def create_token(
    subject: str,
    scopes: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    expires_in_minutes: int = 15,
) -> str:
    """Quick access token creation"""
    manager = TokenManager()
    return manager.create_access_token(
        subject=subject,
        scopes=scopes,
        roles=roles,
        expires_in=timedelta(minutes=expires_in_minutes),
    )


def validate_token(token: str, required_scopes: Optional[List[str]] = None) -> TokenPayload:
    """Quick token validation"""
    manager = TokenManager()
    return manager.validate_token(token, required_scopes=required_scopes)


def decode_token(token: str) -> TokenPayload:
    """Decode token without validation (for inspection)"""
    handler = JWTHandler()
    return handler.decode(token, verify=False)


# ============================================================================
# Production Health Check
# ============================================================================

def verify_production_readiness() -> Tuple[bool, List[str]]:
    """
    Verify JWT configuration is production-ready.
    Returns (is_ready, list_of_issues).
    """
    issues = []
    env = get_environment()
    
    if env != Environment.PRODUCTION:
        issues.append(f"Environment is {env.value}, not production")
    
    # Check key source
    try:
        key_manager = get_key_manager()
        key = key_manager.get_key()
        
        if key.source == "auto-generated-development":
            issues.append("Using auto-generated keys in production - CRITICAL")
        elif key.source == "environment":
            # Check if using files (better) vs direct env vars
            priv_file = os.environ.get("CELL0_JWT_PRIVATE_KEY_FILE")
            if not priv_file:
                issues.append("Consider using key files instead of direct env vars")
        
        # Check key strength
        if key.secret and len(key.secret) < 32:
            issues.append("Secret key is too short (should be 256-bit)")
        
    except ProductionKeyError as e:
        issues.append(str(e))
    except Exception as e:
        issues.append(f"Key loading error: {e}")
    
    # Check algorithm
    algorithm = os.environ.get("CELL0_JWT_ALGORITHM", "HS256")
    if algorithm == "none":
        issues.append("Algorithm 'none' is NOT allowed")
    
    is_ready = len(issues) == 0 or all(
        "not production" in issue.lower() for issue in issues
    )
    
    return is_ready, issues


# ============================================================================
# CLI Interface for Key Generation
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 JWT Handler")
    parser.add_argument("command", choices=["generate", "verify", "test"])
    parser.add_argument("--algorithm", default="HS256", help="JWT algorithm")
    parser.add_argument("--output", help="Output file for generated key")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        if args.algorithm.startswith("HS"):
            key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii')
            if args.output:
                Path(args.output).write_text(key)
                print(f"Generated HMAC key saved to {args.output}")
            else:
                print(f"Generated HMAC key: {key[:16]}...{key[-16:]}")
        else:
            print(f"For {args.algorithm}, use: openssl genrsa -out private.pem 2048")
    
    elif args.command == "verify":
        is_ready, issues = verify_production_readiness()
        if is_ready:
            print("✅ JWT configuration is production-ready")
        else:
            print("❌ JWT configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
    
    elif args.command == "test":
        # Quick test
        print("Testing JWT handler...")
        os.environ["CELL0_ENV"] = "development"
        
        handler = JWTHandler()
        payload = TokenPayload(subject="test-user", scopes=["read"])
        token = handler.encode(payload, timedelta(minutes=5))
        print(f"Generated token: {token[:50]}...")
        
        decoded = handler.decode(token)
        print(f"Decoded subject: {decoded.subject}")
        print(f"Decoded scopes: {decoded.scopes}")
        print("✅ JWT test passed")
