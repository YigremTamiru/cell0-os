"""
Cell 0 OS Security Module

Production-grade security features:
- Authentication (JWT, API keys)
- Rate limiting and circuit breakers
- Secrets management (1Password, encrypted storage)
- Tool security profiles and sandboxing
- Audit logging
"""

# Tool security (existing)
from .tool_profiles import (
    ToolProfile,
    ToolPolicy,
    PermissionLevel,
    RiskLevel,
    ToolGroup,
    ProfileRegistry,
    get_profile,
    get_registry
)

from .tool_policy import (
    PolicyEnforcer,
    PolicyViolation,
    RateLimitExceeded as ToolRateLimitExceeded,
    ToolCallContext,
    AgentPolicyManager,
    get_policy_manager,
    enforce_tool_call
)

from .tool_audit import (
    ToolAuditor,
    AuditEvent,
    AuditBackend,
    get_auditor,
    configure_auditor
)

from .sandbox import (
    SandboxManager,
    SandboxConfig,
    SandboxResult,
    SandboxError,
    SubprocessSandbox,
    DockerSandbox,
    get_sandbox_manager,
    sandboxed
)

# Authentication (new)
from .auth import (
    # Config
    AuthConfig,
    # Enums
    TokenType,
    PermissionScope,
    TokenStatus,
    # Data Classes
    TokenPayload,
    APIKeyInfo,
    AuthenticationContext,
    # Exceptions
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
    RevokedTokenError,
    InsufficientScopeError,
    InvalidAPIKeyError,
    RateLimitAuthError,
    # Managers
    JWTTokenManager,
    APIKeyManager,
    AuthenticationManager,
    # Singleton
    get_auth_manager,
    set_auth_manager,
    # Decorators
    require_auth,
    optional_auth,
)

# Rate Limiting (new)
from .rate_limiter import (
    # Exceptions
    RateLimitExceeded,
    CircuitBreakerOpen,
    ConcurrencyLimitExceeded,
    # Classes
    RateLimitConfig,
    RateLimitState,
    CircuitBreakerState,
    RateLimitBackend,
    InMemoryRateLimitBackend,
    TokenBucketBackend,
    RateLimiter,
    CircuitBreaker,
    # Functions
    get_rate_limiter,
    get_circuit_breaker,
    call_with_circuit_breaker,
    call_ollama_with_circuit_breaker,
    call_signal_with_circuit_breaker,
    call_brave_with_circuit_breaker,
    # Decorators
    rate_limit,
    circuit_breaker,
    concurrent_limit,
)

# Secrets Management (new)
from .secrets import (
    # Config
    SecretsConfig,
    # Exceptions
    SecretsError,
    SecretNotFoundError,
    SecretAccessDeniedError,
    EncryptionError,
    OnePasswordError,
    # Data Classes
    SecretMetadata,
    SecretValue,
    # Backends
    SecretsBackend,
    EnvironmentBackend,
    OnePasswordBackend,
    EncryptedTPVBackend,
    # Manager
    SecretsManager,
    # Global
    get_secrets_manager,
    set_secrets_manager,
    # Convenience
    get_secret,
    require_secret,
    set_secret,
    delete_secret,
)

__all__ = [
    # Tool Profiles
    'ToolProfile',
    'ToolPolicy',
    'PermissionLevel',
    'RiskLevel',
    'ToolGroup',
    'ProfileRegistry',
    'get_profile',
    'get_registry',
    
    # Policy Enforcement
    'PolicyEnforcer',
    'PolicyViolation',
    'ToolRateLimitExceeded',
    'ToolCallContext',
    'AgentPolicyManager',
    'get_policy_manager',
    'enforce_tool_call',
    
    # Audit
    'ToolAuditor',
    'AuditEvent',
    'AuditBackend',
    'get_auditor',
    'configure_auditor',
    
    # Sandbox
    'SandboxManager',
    'SandboxConfig',
    'SandboxResult',
    'SandboxError',
    'SubprocessSandbox',
    'DockerSandbox',
    'get_sandbox_manager',
    'sandboxed',
    
    # Authentication
    'AuthConfig',
    'TokenType',
    'PermissionScope',
    'TokenStatus',
    'TokenPayload',
    'APIKeyInfo',
    'AuthenticationContext',
    'AuthenticationError',
    'InvalidTokenError',
    'ExpiredTokenError',
    'RevokedTokenError',
    'InsufficientScopeError',
    'InvalidAPIKeyError',
    'RateLimitAuthError',
    'JWTTokenManager',
    'APIKeyManager',
    'AuthenticationManager',
    'get_auth_manager',
    'set_auth_manager',
    'require_auth',
    'optional_auth',
    
    # Rate Limiting
    'RateLimitExceeded',
    'CircuitBreakerOpen',
    'ConcurrencyLimitExceeded',
    'RateLimitConfig',
    'RateLimitState',
    'CircuitBreakerState',
    'RateLimitBackend',
    'InMemoryRateLimitBackend',
    'TokenBucketBackend',
    'RateLimiter',
    'CircuitBreaker',
    'get_rate_limiter',
    'get_circuit_breaker',
    'call_with_circuit_breaker',
    'call_ollama_with_circuit_breaker',
    'call_signal_with_circuit_breaker',
    'call_brave_with_circuit_breaker',
    'rate_limit',
    'circuit_breaker',
    'concurrent_limit',
    
    # Secrets Management
    'SecretsConfig',
    'SecretsError',
    'SecretNotFoundError',
    'SecretAccessDeniedError',
    'EncryptionError',
    'OnePasswordError',
    'SecretMetadata',
    'SecretValue',
    'SecretsBackend',
    'EnvironmentBackend',
    'OnePasswordBackend',
    'EncryptedTPVBackend',
    'SecretsManager',
    'get_secrets_manager',
    'set_secrets_manager',
    'get_secret',
    'require_secret',
    'set_secret',
    'delete_secret',
]
