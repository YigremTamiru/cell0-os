"""
cell0/engine/security/auth.py - Production-Grade Authentication System

Comprehensive authentication for Cell 0 OS:
- JWT-based authentication with RS256/HS256 support
- API key management with scopes and rotation
- @require_auth decorator for protected endpoints
- Support for both JWT tokens and API keys
- Token revocation and blacklisting
- RBAC (Role-Based Access Control) foundation
"""

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import jwt
from cryptography.fernet import Fernet

logger = logging.getLogger("cell0.security.auth")


# ============================================================================
# Configuration
# ============================================================================

class AuthConfig:
    """Authentication configuration"""
    # JWT settings
    JWT_SECRET_KEY: str = os.environ.get("CELL0_JWT_SECRET", "")
    JWT_PRIVATE_KEY: Optional[str] = os.environ.get("CELL0_JWT_PRIVATE_KEY", None)
    JWT_PUBLIC_KEY: Optional[str] = os.environ.get("CELL0_JWT_PUBLIC_KEY", None)
    JWT_ALGORITHM: str = os.environ.get("CELL0_JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("CELL0_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.environ.get("CELL0_JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )
    JWT_ISSUER: str = os.environ.get("CELL0_JWT_ISSUER", "cell0-os")
    JWT_AUDIENCE: str = os.environ.get("CELL0_JWT_AUDIENCE", "cell0-api")
    
    # API Key settings
    API_KEY_PREFIX: str = "cell0_"
    API_KEY_LENGTH: int = 64
    API_KEY_ENCRYPTION_KEY: Optional[str] = os.environ.get("CELL0_API_KEY_ENCRYPTION_KEY", None)
    
    # Security settings
    REQUIRE_HTTPS: bool = os.environ.get("CELL0_REQUIRE_HTTPS", "false").lower() == "true"
    MAX_FAILED_AUTH_ATTEMPTS: int = int(
        os.environ.get("CELL0_MAX_FAILED_AUTH_ATTEMPTS", "5")
    )
    FAILED_AUTH_LOCKOUT_MINUTES: int = int(
        os.environ.get("CELL0_FAILED_AUTH_LOCKOUT_MINUTES", "30")
    )
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # For HS256, we need a secret key
        if cls.JWT_ALGORITHM == "HS256" and not cls.JWT_SECRET_KEY:
            # Generate a warning but not an error for development
            logger.warning("JWT_SECRET_KEY not set - using development key (INSECURE)")
            cls.JWT_SECRET_KEY = Fernet.generate_key().decode()[:32]
        
        # For RS256, we need key pair
        if cls.JWT_ALGORITHM == "RS256":
            if not cls.JWT_PRIVATE_KEY:
                errors.append("JWT_PRIVATE_KEY required for RS256 algorithm")
            if not cls.JWT_PUBLIC_KEY:
                errors.append("JWT_PUBLIC_KEY required for RS256 algorithm")
        
        # API key encryption
        if not cls.API_KEY_ENCRYPTION_KEY:
            logger.warning("API_KEY_ENCRYPTION_KEY not set - keys stored in plaintext (INSECURE)")
        
        return errors


# ============================================================================
# Enums and Data Classes
# ============================================================================

class TokenType(Enum):
    """Types of authentication tokens"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SERVICE_ACCOUNT = "service_account"


class PermissionScope(Enum):
    """Permission scopes for API keys and tokens"""
    # System scopes
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    
    # Agent scopes
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"
    
    # Model scopes
    MODEL_INFERENCE = "model:inference"
    MODEL_MANAGE = "model:manage"
    
    # Channel scopes
    CHANNEL_READ = "channel:read"
    CHANNEL_WRITE = "channel:write"
    CHANNEL_ADMIN = "channel:admin"
    
    # Tool scopes
    TOOL_USE = "tool:use"
    TOOL_MANAGE = "tool:manage"
    
    # User scopes
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    
    # Gateway scopes
    GATEWAY_CONNECT = "gateway:connect"
    GATEWAY_ADMIN = "gateway:admin"


class TokenStatus(Enum):
    """Token status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


@dataclass
class TokenPayload:
    """JWT token payload structure"""
    sub: str  # Subject (user/agent ID)
    typ: str  # Token type
    iss: str  # Issuer
    aud: str  # Audience
    iat: float  # Issued at
    exp: float  # Expiration
    jti: str  # JWT ID (unique token ID)
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub": self.sub,
            "typ": self.typ,
            "iss": self.iss,
            "aud": self.aud,
            "iat": self.iat,
            "exp": self.exp,
            "jti": self.jti,
            "scopes": self.scopes,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        return cls(
            sub=data["sub"],
            typ=data["typ"],
            iss=data.get("iss", AuthConfig.JWT_ISSUER),
            aud=data.get("aud", AuthConfig.JWT_AUDIENCE),
            iat=data["iat"],
            exp=data["exp"],
            jti=data.get("jti", str(uuid.uuid4())),
            scopes=data.get("scopes", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class APIKeyInfo:
    """API Key information"""
    key_id: str
    key_hash: str  # Hashed key (never store raw key)
    name: str
    owner_id: str
    owner_type: str  # 'user', 'agent', 'service'
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    status: TokenStatus
    usage_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "scopes": self.scopes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "status": self.status.value,
            "usage_count": self.usage_count,
            "metadata": self.metadata,
        }


@dataclass
class AuthenticationContext:
    """Context passed to authenticated endpoints"""
    principal_id: str  # User/agent/service ID
    principal_type: str  # 'user', 'agent', 'service_account'
    auth_method: str  # 'jwt', 'api_key'
    scopes: Set[str]
    token_id: Optional[str] = None
    api_key_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    authenticated_at: datetime = field(default_factory=datetime.utcnow)
    
    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope"""
        # Support wildcards like "agent:*"
        for ctx_scope in self.scopes:
            if ctx_scope == scope:
                return True
            if ctx_scope.endswith(":*"):
                prefix = ctx_scope[:-2]
                if scope.startswith(prefix + ":"):
                    return True
            if ctx_scope == "*":
                return True
        return False
    
    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if context has any of the specified scopes"""
        return any(self.has_scope(scope) for scope in scopes)
    
    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if context has all specified scopes"""
        return all(self.has_scope(scope) for scope in scopes)


# ============================================================================
# Exceptions
# ============================================================================

class AuthenticationError(Exception):
    """Base authentication error"""
    code: str = "AUTH_ERROR"
    status_code: int = 401
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token"""
    code = "AUTH_INVALID_TOKEN"
    status_code = 401


class ExpiredTokenError(AuthenticationError):
    """Token has expired"""
    code = "AUTH_TOKEN_EXPIRED"
    status_code = 401


class RevokedTokenError(AuthenticationError):
    """Token has been revoked"""
    code = "AUTH_TOKEN_REVOKED"
    status_code = 401


class InsufficientScopeError(AuthenticationError):
    """Token lacks required scope"""
    code = "AUTH_INSUFFICIENT_SCOPE"
    status_code = 403


class InvalidAPIKeyError(AuthenticationError):
    """Invalid API key"""
    code = "AUTH_INVALID_API_KEY"
    status_code = 401


class RateLimitAuthError(AuthenticationError):
    """Too many authentication attempts"""
    code = "AUTH_RATE_LIMIT"
    status_code = 429


# ============================================================================
# Singleton Instance
# ============================================================================

# Global authentication manager instance
_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get or create the global authentication manager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager


def set_auth_manager(manager: AuthenticationManager):
    """Set the global authentication manager"""
    global _auth_manager
    _auth_manager = manager


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Config
    'AuthConfig',
    # Enums
    'TokenType',
    'PermissionScope',
    'TokenStatus',
    # Data Classes
    'TokenPayload',
    'APIKeyInfo',
    'AuthenticationContext',
    # Exceptions
    'AuthenticationError',
    'InvalidTokenError',
    'ExpiredTokenError',
    'RevokedTokenError',
    'InsufficientScopeError',
    'InvalidAPIKeyError',
    'RateLimitAuthError',
    # Managers
    'JWTTokenManager',
    'APIKeyManager',
    'AuthenticationManager',
    # Singleton
    'get_auth_manager',
    'set_auth_manager',
    # Decorators
    'require_auth',
    'optional_auth',
]


# ============================================================================
# JWT Token Manager
# ============================================================================

class JWTTokenManager:
    """Manages JWT token lifecycle"""
    
    def __init__(self):
        self._config = AuthConfig
        self._token_blacklist: Set[str] = set()  # Set of revoked jtis
        self._token_cache: Dict[str, TokenPayload] = {}  # jti -> payload cache
        self._lock = asyncio.Lock()
        
        # Validate config on init
        errors = self._config.validate()
        if errors:
            raise RuntimeError(f"Auth configuration errors: {errors}")
    
    def _get_signing_key(self) -> Union[str, bytes]:
        """Get the appropriate signing key based on algorithm"""
        if self._config.JWT_ALGORITHM == "RS256":
            return self._config.JWT_PRIVATE_KEY.encode() if self._config.JWT_PRIVATE_KEY else b""
        return self._config.JWT_SECRET_KEY
    
    def _get_verification_key(self) -> Union[str, bytes]:
        """Get the appropriate verification key based on algorithm"""
        if self._config.JWT_ALGORITHM == "RS256":
            return self._config.JWT_PUBLIC_KEY.encode() if self._config.JWT_PUBLIC_KEY else b""
        return self._config.JWT_SECRET_KEY
    
    def create_token(
        self,
        subject: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, TokenPayload]:
        """Create a new JWT token"""
        now = datetime.utcnow()
        
        # Determine expiration
        if expires_delta:
            expire = now + expires_delta
        elif token_type == TokenType.REFRESH:
            expire = now + timedelta(days=self._config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            expire = now + timedelta(minutes=self._config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Create payload
        payload = TokenPayload(
            sub=subject,
            typ=token_type.value,
            iss=self._config.JWT_ISSUER,
            aud=self._config.JWT_AUDIENCE,
            iat=now.timestamp(),
            exp=expire.timestamp(),
            jti=str(uuid.uuid4()),
            scopes=scopes or [PermissionScope.SYSTEM_READ.value],
            metadata=metadata or {},
        )
        
        # Encode token
        token = jwt.encode(
            payload.to_dict(),
            self._get_signing_key(),
            algorithm=self._config.JWT_ALGORITHM,
        )
        
        logger.debug(f"Created {token_type.value} token for {subject}")
        return token, payload
    
    def decode_token(self, token: str, verify_exp: bool = True) -> TokenPayload:
        """Decode and validate a JWT token"""
        try:
            payload_dict = jwt.decode(
                token,
                self._get_verification_key(),
                algorithms=[self._config.JWT_ALGORITHM],
                audience=self._config.JWT_AUDIENCE,
                issuer=self._config.JWT_ISSUER,
                options={"verify_exp": verify_exp},
            )
            
            payload = TokenPayload.from_dict(payload_dict)
            
            # Check blacklist
            if payload.jti in self._token_blacklist:
                raise RevokedTokenError("Token has been revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenError("Token has expired")
        except jwt.InvalidAudienceError:
            raise InvalidTokenError("Invalid token audience")
        except jwt.InvalidIssuerError:
            raise InvalidTokenError("Invalid token issuer")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding its JTI to blacklist"""
        try:
            payload = self.decode_token(token, verify_exp=False)
            async with self._lock:
                self._token_blacklist.add(payload.jti)
                self._token_cache.pop(payload.jti, None)
            
            logger.info(f"Revoked token {payload.jti}")
            return True
        except AuthenticationError:
            return False
    
    async def revoke_token_by_jti(self, jti: str) -> bool:
        """Revoke a token by its JTI"""
        async with self._lock:
            self._token_blacklist.add(jti)
            self._token_cache.pop(jti, None)
        logger.info(f"Revoked token by JTI: {jti}")
        return True
    
    async def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked"""
        async with self._lock:
            return jti in self._token_blacklist


# ============================================================================
# API Key Manager
# ============================================================================

class APIKeyManager:
    """Manages API key lifecycle"""
    
    def __init__(self):
        self._config = AuthConfig
        self._keys: Dict[str, APIKeyInfo] = {}  # key_id -> info
        self._key_hash_map: Dict[str, str] = {}  # key_hash -> key_id
        self._lock = asyncio.Lock()
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _generate_key(self) -> Tuple[str, str]:
        """Generate a new API key and its ID"""
        key_id = f"key_{uuid.uuid4().hex[:16]}"
        random_bytes = secrets.token_bytes(self._config.API_KEY_LENGTH // 2)
        key = f"{self._config.API_KEY_PREFIX}{random_bytes.hex()}"
        return key_id, key
    
    async def create_key(
        self,
        name: str,
        owner_id: str,
        owner_type: str = "user",
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, APIKeyInfo]:
        """Create a new API key"""
        key_id, raw_key = self._generate_key()
        key_hash = self._hash_key(raw_key)
        
        now = datetime.utcnow()
        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)
        
        key_info = APIKeyInfo(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            owner_id=owner_id,
            owner_type=owner_type,
            scopes=scopes or [PermissionScope.SYSTEM_READ.value],
            created_at=now,
            expires_at=expires_at,
            last_used_at=None,
            status=TokenStatus.ACTIVE,
            metadata=metadata or {},
        )
        
        async with self._lock:
            self._keys[key_id] = key_info
            self._key_hash_map[key_hash] = key_id
        
        logger.info(f"Created API key {key_id} for {owner_id}")
        return raw_key, key_info
    
    async def validate_key(self, key: str) -> Optional[APIKeyInfo]:
        """Validate an API key and return its info"""
        # Check prefix
        if not key.startswith(self._config.API_KEY_PREFIX):
            raise InvalidAPIKeyError("Invalid API key format")
        
        key_hash = self._hash_key(key)
        
        async with self._lock:
            key_id = self._key_hash_map.get(key_hash)
            if not key_id:
                raise InvalidAPIKeyError("Invalid API key")
            
            key_info = self._keys.get(key_id)
            if not key_info:
                raise InvalidAPIKeyError("API key not found")
        
        # Check status
        if key_info.status == TokenStatus.REVOKED:
            raise InvalidAPIKeyError("API key has been revoked")
        
        if key_info.status == TokenStatus.SUSPENDED:
            raise InvalidAPIKeyError("API key has been suspended")
        
        # Check expiration
        if key_info.expires_at and datetime.utcnow() > key_info.expires_at:
            raise InvalidAPIKeyError("API key has expired")
        
        # Update usage stats
        await self._record_key_usage(key_id)
        
        return key_info
    
    async def _record_key_usage(self, key_id: str):
        """Record API key usage"""
        async with self._lock:
            if key_id in self._keys:
                self._keys[key_id].last_used_at = datetime.utcnow()
                self._keys[key_id].usage_count += 1
    
    async def revoke_key(self, key_id: str, reason: str = "") -> bool:
        """Revoke an API key"""
        async with self._lock:
            if key_id not in self._keys:
                return False
            
            self._keys[key_id].status = TokenStatus.REVOKED
            key_hash = self._keys[key_id].key_hash
            self._key_hash_map.pop(key_hash, None)
        
        logger.info(f"Revoked API key {key_id}: {reason}")
        return True
    
    async def rotate_key(
        self,
        key_id: str,
        grace_period_hours: int = 24
    ) -> Tuple[str, APIKeyInfo]:
        """Rotate an API key"""
        async with self._lock:
            old_key = self._keys.get(key_id)
            if not old_key:
                raise InvalidAPIKeyError("API key not found")
        
        # Create new key with same permissions
        new_raw_key, new_key_info = await self.create_key(
            name=f"{old_key.name} (rotated)",
            owner_id=old_key.owner_id,
            owner_type=old_key.owner_type,
            scopes=old_key.scopes,
            metadata={**old_key.metadata, "rotated_from": key_id},
        )
        
        # Schedule old key for deletion after grace period
        asyncio.create_task(self._delayed_revoke(key_id, grace_period_hours))
        
        logger.info(f"Rotated API key {key_id} -> {new_key_info.key_id}")
        return new_raw_key, new_key_info
    
    async def _delayed_revoke(self, key_id: str, hours: int):
        """Delayed revocation (for grace period)"""
        await asyncio.sleep(hours * 3600)
        await self.revoke_key(key_id, reason="Rotation grace period expired")
    
    def get_key_info(self, key_id: str) -> Optional[APIKeyInfo]:
        """Get API key info by ID (without validating)"""
        return self._keys.get(key_id)
    
    def list_keys(
        self,
        owner_id: Optional[str] = None,
        owner_type: Optional[str] = None,
        status: Optional[TokenStatus] = None,
    ) -> List[APIKeyInfo]:
        """List API keys with optional filters"""
        results = []
        for key_info in self._keys.values():
            if owner_id and key_info.owner_id != owner_id:
                continue
            if owner_type and key_info.owner_type != owner_type:
                continue
            if status and key_info.status != status:
                continue
            results.append(key_info)
        return results


# ============================================================================
# Authentication Manager
# ============================================================================

class AuthenticationManager:
    """Central authentication manager combining JWT and API key auth"""
    
    def __init__(self):
        self.jwt_manager = JWTTokenManager()
        self.api_key_manager = APIKeyManager()
        self._failed_attempts: Dict[str, List[float]] = {}  # IP -> list of timestamps
        self._lock = asyncio.Lock()
    
    async def authenticate(
        self,
        credential: str,
        client_ip: Optional[str] = None,
    ) -> AuthenticationContext:
        """Authenticate using either JWT token or API key"""
        # Check rate limiting
        if client_ip and await self._is_rate_limited(client_ip):
            raise RateLimitAuthError("Too many authentication attempts. Please try again later.")
        
        try:
            # Try JWT first (starts with "ey")
            if credential.startswith("ey") or credential.count(".") == 2:
                context = await self._authenticate_jwt(credential)
            else:
                # Try API key
                context = await self._authenticate_api_key(credential)
            
            # Clear failed attempts on success
            if client_ip:
                async with self._lock:
                    self._failed_attempts.pop(client_ip, None)
            
            return context
            
        except AuthenticationError:
            # Record failed attempt
            if client_ip:
                await self._record_failed_attempt(client_ip)
            raise
    
    async def _authenticate_jwt(self, token: str) -> AuthenticationContext:
        """Authenticate using JWT token"""
        payload = self.jwt_manager.decode_token(token)
        
        return AuthenticationContext(
            principal_id=payload.sub,
            principal_type=payload.metadata.get("principal_type", "user"),
            auth_method="jwt",
            scopes=set(payload.scopes),
            token_id=payload.jti,
            metadata=payload.metadata,
        )
    
    async def _authenticate_api_key(self, key: str) -> AuthenticationContext:
        """Authenticate using API key"""
        key_info = await self.api_key_manager.validate_key(key)
        
        return AuthenticationContext(
            principal_id=key_info.owner_id,
            principal_type=key_info.owner_type,
            auth_method="api_key",
            scopes=set(key_info.scopes),
            api_key_id=key_info.key_id,
            metadata=key_info.metadata,
        )
    
    async def _record_failed_attempt(self, client_ip: str):
        """Record a failed authentication attempt"""
        now = time.time()
        window = AuthConfig.FAILED_AUTH_LOCKOUT_MINUTES * 60
        
        async with self._lock:
            if client_ip not in self._failed_attempts:
                self._failed_attempts[client_ip] = []
            
            # Clean old attempts
            self._failed_attempts[client_ip] = [
                t for t in self._failed_attempts[client_ip] if now - t < window
            ]
            
            self._failed_attempts[client_ip].append(now)
    
    async def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited"""
        now = time.time()
        window = AuthConfig.FAILED_AUTH_LOCKOUT_MINUTES * 60
        
        async with self._lock:
            if client_ip not in self._failed_attempts:
                return False
            
            # Clean and count recent attempts
            recent = [
                t for t in self._failed_attempts[client_ip] if now - t < window
            ]
            return len(recent) >= AuthConfig.MAX_FAILED_AUTH_ATTEMPTS
    
    def create_access_token(
        self,
        subject: str,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, TokenPayload]:
        """Create a new access token"""
        return self.jwt_manager.create_token(
            subject=subject,
            token_type=TokenType.ACCESS,
            scopes=scopes,
            metadata=metadata,
        )
    
    def create_refresh_token(
        self,
        subject: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, TokenPayload]:
        """Create a new refresh token"""
        return self.jwt_manager.create_token(
            subject=subject,
            token_type=TokenType.REFRESH,
            scopes=[],
            metadata=metadata,
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        return await self.jwt_manager.revoke_token(token)
    
    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, TokenPayload]:
        """Create a new access token using a refresh token"""
        payload = self.jwt_manager.decode_token(refresh_token)
        
        if payload.typ != TokenType.REFRESH.value:
            raise InvalidTokenError("Not a refresh token")
        
        return self.jwt_manager.create_token(
            subject=payload.sub,
            token_type=TokenType.ACCESS,
            scopes=payload.metadata.get("original_scopes", []),
            metadata=payload.metadata,
        )


# ============================================================================
# Decorators
# ============================================================================

def require_auth(
    scopes: Optional[List[str]] = None,
    any_scope: bool = False,
    allow_api_key: bool = True,
    allow_jwt: bool = True,
):
    """Decorator to require authentication for an endpoint"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = kwargs.get('request')
            if not request and args:
                request = args[0]
            
            if not request:
                raise AuthenticationError("No request object found")
            
            # Get auth header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header:
                raise AuthenticationError("Missing Authorization header")
            
            # Parse Bearer token
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                raise AuthenticationError("Invalid Authorization header format")
            
            credential = parts[1]
            
            # Authenticate
            auth_manager = get_auth_manager()
            
            # Get client IP for rate limiting
            client_ip = getattr(request, 'client', None)
            if client_ip:
                client_ip = getattr(client_ip, 'host', None)
            
            auth_context = await auth_manager.authenticate(credential, client_ip)
            
            # Check allowed auth methods
            if auth_context.auth_method == "api_key" and not allow_api_key:
                raise AuthenticationError("API key authentication not allowed for this endpoint")
            if auth_context.auth_method == "jwt" and not allow_jwt:
                raise AuthenticationError("JWT authentication not allowed for this endpoint")
            
            # Check scopes
            if scopes:
                if any_scope:
                    if not auth_context.has_any_scope(scopes):
                        raise InsufficientScopeError(f"Need any of: {', '.join(scopes)}")
                else:
                    if not auth_context.has_all_scopes(scopes):
                        raise InsufficientScopeError(f"Need all of: {', '.join(scopes)}")
            
            # Attach context to request
            request.auth_context = auth_context
            
            # Call the actual function
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            raise RuntimeError("@require_auth only works with async functions")
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def optional_auth(func: Callable) -> Callable:
    """Decorator to optionally authenticate requests"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if not request and args:
            request = args[0]
        
        auth_context = None
        
        if request:
            auth_header = request.headers.get("Authorization", "")
            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    try:
                        auth_manager = get_auth_manager()
                        client_ip = getattr(request, 'client', None)
                        if client_ip:
                            client_ip = getattr(client_ip, 'host', None)
                        auth_context = await auth_manager.authenticate(parts[1], client_ip)
                    except AuthenticationError:
                        pass
        
        if request:
            request.auth_context = auth_context
        
        return await func(*args, **kwargs)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return func
