"""
cell0/security/jwt_handler.py

JWT Token Management for Cell 0 OS

Features:
- Refresh token support
- Token blacklisting
- Token expiration handling
- Secure cookie storage

Usage:
    from cell0.security.jwt_handler import (
        create_access_token,
        create_refresh_token,
        jwt_required,
        set_token_cookies
    )
    
    # Create tokens
    access = create_access_token({"user_id": "123", "role": "admin"})
    refresh = create_refresh_token({"user_id": "123"})
    
    # Protect endpoint
    @app.get("/protected")
    @jwt_required
    async def protected(current_user: dict = Depends(get_current_user)):
        return {"user": current_user}
"""

import os
import json
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Union, List
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

# JWT support
try:
    import jwt
    from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    jwt = None
    InvalidTokenError = Exception
    ExpiredSignatureError = Exception

# Optional FastAPI support
try:
    from fastapi import HTTPException, Request, Response, Depends, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    HTTPException = Exception
    Request = Any
    Response = Any
    Depends = lambda func: func
    status = type('status', (), {
        'HTTP_401_UNAUTHORIZED': 401,
        'HTTP_403_FORBIDDEN': 403,
    })()

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of JWT tokens."""
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class TokenConfig:
    """Configuration for JWT tokens."""
    # Secrets
    secret_key: str
    refresh_secret_key: Optional[str] = None  # Separate key for refresh tokens
    
    # Token lifetimes
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Algorithm
    algorithm: str = "HS256"
    
    # Cookie settings
    cookie_name_access: str = "access_token"
    cookie_name_refresh: str = "refresh_token"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    cookie_domain: Optional[str] = None
    cookie_path: str = "/"
    
    # Issuer
    issuer: str = "cell0"
    audience: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'TokenConfig':
        """
        Create configuration from environment variables.
        
        SOVEREIGN SECURITY POLICY:
        - Production: Requires explicit JWT_SECRET_KEY (fail fast)
        - Development: Auto-generates with warnings and 24h expiry
        - 1Password integration preferred for production
        """
        secret = os.getenv("JWT_SECRET_KEY")
        env = os.getenv("CELL0_ENV", "production").lower()
        
        if not secret:
            if env == "development":
                # Development mode: Auto-generate with loud warnings
                import secrets
                secret = secrets.token_urlsafe(64)
                logger.warning("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  🔴 DEVELOPMENT MODE — AUTO-GENERATING TEMPORARY JWT SECRET      ║
    ║                                                                  ║
    ║  ⚠️  WARNING: This is insecure and only for development!         ║
    ║                                                                  ║
    ║  • Secret expires in: 24 hours                                   ║
    ║  • Stored in: Process memory only                                ║
    ║  • This warning appears on every startup                         ║
    ║                                                                  ║
    ║  For production security, configure 1Password:                   ║
    ║    cell0ctl setup --1password                                    ║
    ║                                                                  ║
    ║  Or generate manually:                                           ║
    ║    export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" ║
    ╚══════════════════════════════════════════════════════════════════╝
                """)
                # Set expiry marker
                os.environ["_CELL0_DEV_SECRET_EXPIRES"] = str(
                    (datetime.utcnow() + timedelta(hours=24)).timestamp()
                )
            else:
                # Production: Fail fast with sovereign security guidance
                raise cls._sovereign_security_error()
        
        # Check for 1Password integration
        if os.getenv("JWT_SECRET_KEY_1PASSWORD_REF"):
            secret = cls._load_from_1password()
        
        # Validate secret strength
        if len(secret) < 64:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 64 characters for sovereign security.\n"
                f"Current length: {len(secret)} characters.\n"
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        
        # Check if dev secret expired
        if os.getenv("_CELL0_DEV_SECRET_EXPIRES"):
            expires = float(os.getenv("_CELL0_DEV_SECRET_EXPIRES"))
            if datetime.utcnow().timestamp() > expires:
                raise ValueError(
                    "Development JWT secret has expired (24 hours).\n"
                    "Generate new: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
        
        return cls(
            secret_key=secret,
            refresh_secret_key=os.getenv("JWT_REFRESH_SECRET_KEY"),
            access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            refresh_token_expire_days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            cookie_secure=os.getenv("JWT_COOKIE_SECURE", "true").lower() in ("true", "1", "yes"),
            cookie_httponly=os.getenv("JWT_COOKIE_HTTPONLY", "true").lower() in ("true", "1", "yes"),
            cookie_samesite=os.getenv("JWT_COOKIE_SAMESITE", "lax"),
            cookie_domain=os.getenv("JWT_COOKIE_DOMAIN"),
            cookie_path=os.getenv("JWT_COOKIE_PATH", "/"),
            issuer=os.getenv("JWT_ISSUER", "cell0"),
            audience=os.getenv("JWT_AUDIENCE"),
        )
    
    @staticmethod
    def _sovereign_security_error() -> ValueError:
        """
        Generate sovereign security error with comprehensive guidance.
        
        Cell 0 OS requires explicit JWT secret configuration for production.
        This is a core sovereign security principle - no magic, no silent fallbacks.
        """
        error_msg = """
🔐 SOVEREIGN SECURITY VIOLATION — JWT_SECRET_KEY REQUIRED

Cell 0 OS refuses to start without explicit JWT secret configuration.
This protects your sovereign identity and prevents accidental security holes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️  RECOMMENDED: 1Password Integration (Sovereign-Grade Security)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   cell0ctl setup --1password

   Benefits:
   • Secret never touches disk in plaintext
   • Biometric unlock (Touch ID / Face ID / Apple Watch)
   • Automatic rotation support
   • Audit trail in 1Password
   • Shared securely across cluster nodes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☁️  ALTERNATIVE: Kubernetes Secrets (Cloud-Native)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   cell0ctl setup --k8s

   kubectl create secret generic cell0-jwt \
     --from-literal=JWT_SECRET_KEY="$(openssl rand -base64 64)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧  MANUAL: Environment Variable (Less Secure)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Generate:
     export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
   
   Or:
     export JWT_SECRET_KEY="$(openssl rand -base64 64)"
   
   Verify strength:
     echo "${JWT_SECRET_KEY}" | wc -c  # Should be 64+ characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢  ENTERPRISE: HashiCorp Vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   cell0ctl setup --vault

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ NEVER USE IN PRODUCTION:
   • Auto-generated secrets (CRIT-003 vulnerability)
   • Hardcoded secrets in code
   • Secrets in Docker layers
   • Secrets in Git repositories

The glass has melted. Your keys are sovereign. 🌊

For help: cell0ctl doctor --security
        """
        return ValueError(error_msg)
    
    @staticmethod
    def _load_from_1password() -> str:
        """
        Load JWT secret from 1Password vault.
        
        Requires 1Password CLI (op) to be installed and authenticated.
        Reference: op://vault/item/field
        """
        import subprocess
        
        ref = os.getenv("JWT_SECRET_KEY_1PASSWORD_REF", "op://Cell0-Sovereign/jwt/key")
        
        try:
            result = subprocess.run(
                ["op", "read", ref],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                secret = result.stdout.strip()
                logger.info("🔐 Loaded JWT secret from 1Password (sovereign-secure)")
                return secret
            else:
                logger.error(f"1Password read failed: {result.stderr}")
                raise ValueError(
                    "Failed to load JWT secret from 1Password.\n"
                    "Ensure 'op' CLI is installed and you're signed in:\n"
                    "  op signin\n"
                    f"Reference: {ref}"
                )
        except FileNotFoundError:
            raise ValueError(
                "1Password CLI (op) not found. Install from:\n"
                "  https://1password.com/downloads/command-line/\n"
                "Or use: cell0ctl setup --1password"
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                "1Password read timed out. Check biometric prompt or sign in:\n"
                "  op signin"
            )
    
    def get_secret(self, token_type: TokenType) -> str:
        """Get the appropriate secret for token type."""
        if token_type == TokenType.REFRESH and self.refresh_secret_key:
            return self.refresh_secret_key
        return self.secret_key


@dataclass
class TokenPair:
    """Pair of access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # Seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


class TokenBlacklist:
    """
    Manages blacklisted (revoked) tokens.
    
    Uses file-based storage with in-memory cache.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".cell0" / "token_blacklist.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._blacklist: Dict[str, datetime] = {}  # jti -> expiration
        self._lock = asyncio.Lock()
        
        self._load()
    
    def _load(self):
        """Load blacklist from storage."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            now = datetime.utcnow()
            for jti, expiry_str in data.get("blacklist", {}).items():
                expiry = datetime.fromisoformat(expiry_str)
                # Only keep non-expired entries
                if expiry > now:
                    self._blacklist[jti] = expiry
            
            logger.info(f"Loaded {len(self._blacklist)} blacklisted tokens")
        except Exception as e:
            logger.error(f"Failed to load token blacklist: {e}")
    
    async def _save(self):
        """Save blacklist to storage."""
        async with self._lock:
            # Clean up expired entries before saving
            now = datetime.utcnow()
            self._blacklist = {jti: exp for jti, exp in self._blacklist.items() if exp > now}
            
            data = {
                "blacklist": {jti: exp.isoformat() for jti, exp in self._blacklist.items()},
                "saved_at": datetime.utcnow().isoformat(),
            }
            
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.storage_path)
    
    async def add(self, jti: str, expires_at: datetime):
        """
        Add a token to the blacklist.
        
        Args:
            jti: JWT ID (unique token identifier)
            expires_at: When the token naturally expires
        """
        async with self._lock:
            self._blacklist[jti] = expires_at
        
        await self._save()
        logger.info(f"Blacklisted token: {jti}")
    
    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted."""
        if jti not in self._blacklist:
            return False
        
        # Check if entry has expired
        if datetime.utcnow() > self._blacklist[jti]:
            # Remove expired entry
            del self._blacklist[jti]
            return False
        
        return True
    
    async def cleanup(self) -> int:
        """Remove expired entries and return count removed."""
        async with self._lock:
            now = datetime.utcnow()
            expired = [jti for jti, exp in self._blacklist.items() if exp <= now]
            for jti in expired:
                del self._blacklist[jti]
        
        if expired:
            await self._save()
            logger.info(f"Cleaned up {len(expired)} expired blacklist entries")
        
        return len(expired)


class JWTManager:
    """
    Manages JWT token creation, validation, and refresh.
    """
    
    def __init__(self, config: Optional[TokenConfig] = None):
        if not HAS_JWT:
            raise ImportError("PyJWT is required. Install with: pip install PyJWT")
        
        self.config = config or TokenConfig.from_env()
        self.blacklist = TokenBlacklist()
    
    def _generate_jti(self) -> str:
        """Generate a unique JWT ID."""
        import secrets
        return secrets.token_urlsafe(16)
    
    def _create_token(
        self,
        data: Dict[str, Any],
        token_type: TokenType,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT token.
        
        Args:
            data: Payload data
            token_type: Type of token
            expires_delta: Optional custom expiration
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        
        # Set expiration
        if expires_delta:
            expire = now + expires_delta
        elif token_type == TokenType.ACCESS:
            expire = now + timedelta(minutes=self.config.access_token_expire_minutes)
        else:
            expire = now + timedelta(days=self.config.refresh_token_expire_days)
        
        # Build payload
        payload = {
            **data,
            "exp": expire,
            "iat": now,
            "jti": self._generate_jti(),
            "type": token_type.value,
            "iss": self.config.issuer,
        }
        
        if self.config.audience:
            payload["aud"] = self.config.audience
        
        # Get appropriate secret
        secret = self.config.get_secret(token_type)
        
        # Encode
        token = jwt.encode(
            payload,
            secret,
            algorithm=self.config.algorithm,
        )
        
        return token
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create an access token.
        
        Args:
            data: User data (user_id, roles, etc.)
            expires_delta: Optional custom expiration
            
        Returns:
            Access token
        """
        return self._create_token(data, TokenType.ACCESS, expires_delta)
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a refresh token.
        
        Args:
            data: User data (user_id)
            expires_delta: Optional custom expiration
            
        Returns:
            Refresh token
        """
        # Refresh tokens contain minimal data
        refresh_data = {
            "sub": data.get("user_id") or data.get("sub"),
            "version": data.get("token_version", 1),
        }
        return self._create_token(refresh_data, TokenType.REFRESH, expires_delta)
    
    def create_token_pair(
        self,
        user_data: Dict[str, Any],
    ) -> TokenPair:
        """
        Create both access and refresh tokens.
        
        Args:
            user_data: User information
            
        Returns:
            TokenPair containing both tokens
        """
        access = self.create_access_token(user_data)
        refresh = self.create_refresh_token(user_data)
        
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.config.access_token_expire_minutes * 60,
        )
    
    def decode_token(
        self,
        token: str,
        token_type: TokenType = TokenType.ACCESS,
    ) -> Dict[str, Any]:
        """
        Decode and validate a token.
        
        Args:
            token: JWT token
            token_type: Expected token type
            
        Returns:
            Decoded payload
            
        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        secret = self.config.get_secret(token_type)
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=[self.config.algorithm],
            issuer=self.config.issuer,
            audience=self.config.audience,
        )
        
        # Check token type
        if payload.get("type") != token_type.value:
            raise InvalidTokenError(f"Invalid token type. Expected {token_type.value}")
        
        # Check blacklist
        jti = payload.get("jti")
        if jti and self.blacklist.is_blacklisted(jti):
            raise InvalidTokenError("Token has been revoked")
        
        return payload
    
    def refresh_access_token(
        self,
        refresh_token: str,
        user_data: Dict[str, Any],
    ) -> str:
        """
        Create a new access token from a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            user_data: Updated user data
            
        Returns:
            New access token
        """
        # Validate refresh token
        payload = self.decode_token(refresh_token, TokenType.REFRESH)
        
        # Create new access token
        return self.create_access_token(user_data)
    
    async def revoke_token(self, token: str, token_type: TokenType = TokenType.ACCESS):
        """
        Revoke a token by adding it to the blacklist.
        
        Args:
            token: Token to revoke
            token_type: Type of token
        """
        try:
            # Decode without validation to get expiration
            secret = self.config.get_secret(token_type)
            payload = jwt.decode(
                token,
                secret,
                algorithms=[self.config.algorithm],
                options={"verify_exp": False},
            )
            
            jti = payload.get("jti")
            exp = datetime.fromtimestamp(payload["exp"])
            
            if jti:
                await self.blacklist.add(jti, exp)
                
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
    
    def set_token_cookies(
        self,
        response: Response,
        token_pair: TokenPair,
    ):
        """
        Set tokens as HTTP-only cookies.
        
        Args:
            response: FastAPI response object
            token_pair: Tokens to set
        """
        if not HAS_FASTAPI:
            raise RuntimeError("FastAPI is required for cookie support")
        
        # Set access token cookie
        response.set_cookie(
            key=self.config.cookie_name_access,
            value=token_pair.access_token,
            httponly=self.config.cookie_httponly,
            secure=self.config.cookie_secure,
            samesite=self.config.cookie_samesite,
            domain=self.config.cookie_domain,
            path=self.config.cookie_path,
            max_age=self.config.access_token_expire_minutes * 60,
        )
        
        # Set refresh token cookie
        response.set_cookie(
            key=self.config.cookie_name_refresh,
            value=token_pair.refresh_token,
            httponly=True,  # Always httpOnly for refresh
            secure=self.config.cookie_secure,
            samesite="strict",  # Stricter for refresh
            domain=self.config.cookie_domain,
            path="/api/auth/refresh",  # Restricted path
            max_age=self.config.refresh_token_expire_days * 86400,
        )
    
    def clear_token_cookies(self, response: Response):
        """
        Clear token cookies.
        
        Args:
            response: FastAPI response object
        """
        if not HAS_FASTAPI:
            raise RuntimeError("FastAPI is required for cookie support")
        
        response.delete_cookie(
            key=self.config.cookie_name_access,
            path=self.config.cookie_path,
            domain=self.config.cookie_domain,
        )
        
        response.delete_cookie(
            key=self.config.cookie_name_refresh,
            path="/api/auth/refresh",
            domain=self.config.cookie_domain,
        )


# Global manager instance
_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get or create the global JWT manager."""
    global _manager
    if _manager is None:
        _manager = JWTManager()
    return _manager


def set_jwt_manager(manager: JWTManager):
    """Set the global JWT manager."""
    global _manager
    _manager = manager


# Convenience functions

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create an access token.
    
    Args:
        data: User data
        expires_delta: Optional custom expiration
        
    Returns:
        Access token string
    """
    manager = get_jwt_manager()
    return manager.create_access_token(data, expires_delta)


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a refresh token.
    
    Args:
        data: User data
        expires_delta: Optional custom expiration
        
    Returns:
        Refresh token string
    """
    manager = get_jwt_manager()
    return manager.create_refresh_token(data, expires_delta)


def refresh_access_token(
    refresh_token: str,
    user_data: Dict[str, Any],
) -> str:
    """
    Refresh an access token.
    
    Args:
        refresh_token: Valid refresh token
        user_data: Updated user data
        
    Returns:
        New access token
    """
    manager = get_jwt_manager()
    return manager.refresh_access_token(refresh_token, user_data)


async def revoke_token(token: str, token_type: TokenType = TokenType.ACCESS):
    """
    Revoke a token.
    
    Args:
        token: Token to revoke
        token_type: Type of token
    """
    manager = get_jwt_manager()
    await manager.revoke_token(token, token_type)


# FastAPI dependencies

async def get_current_user(
    request: Request = None,
    authorization: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get the current user from JWT token.
    
    Supports:
    - Authorization header: Bearer <token>
    - Cookie: access_token
    
    Args:
        request: FastAPI request
        authorization: Authorization header value
        
    Returns:
        User data from token
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    manager = get_jwt_manager()
    token = None
    
    # Try header
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif request and authorization:
        token = authorization
    
    # Try cookie
    if not token and request:
        token = request.cookies.get(manager.config.cookie_name_access)
    
    if not token:
        if HAS_FASTAPI:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise Exception("Authentication required")
    
    try:
        payload = manager.decode_token(token, TokenType.ACCESS)
        return payload
    except ExpiredSignatureError:
        if HAS_FASTAPI:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise Exception("Token expired")
    except InvalidTokenError as e:
        if HAS_FASTAPI:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise Exception(f"Invalid token: {str(e)}")


def jwt_required(func: Callable) -> Callable:
    """
    Decorator to require JWT authentication.
    
    Usage:
        @app.get("/protected")
        @jwt_required
        async def endpoint(user: dict = Depends(get_current_user)):
            return {"user": user}
    """
    # Store metadata for middleware processing
    func._jwt_required = True
    return func


def set_token_cookies(response: Response, token_pair: TokenPair):
    """
    Set tokens as HTTP-only cookies.
    
    Args:
        response: FastAPI response
        token_pair: Tokens to set
    """
    manager = get_jwt_manager()
    manager.set_token_cookies(response, token_pair)


def clear_token_cookies(response: Response):
    """
    Clear token cookies.
    
    Args:
        response: FastAPI response
    """
    manager = get_jwt_manager()
    manager.clear_token_cookies(response)
