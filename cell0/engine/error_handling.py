"""
cell0/engine/error_handling.py - Error Handling & Recovery System

Production-grade error handling for Cell 0 OS:
- Cell0Exception base class with structured error responses
- Error codes, user messages, and remediation guidance
- Sentry integration for error tracking
- Graceful degradation for failed services
- Retry logic with exponential backoff
- Error classification and severity levels
"""

import functools
import logging
import os
import sys
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

# Optional imports - graceful degradation if not available
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger("cell0.error_handling")


# ============================================================================
# Configuration
# ============================================================================

class ErrorConfig:
    """Error handling configuration"""
    # Sentry settings
    SENTRY_DSN: Optional[str] = os.environ.get("SENTRY_DSN")
    SENTRY_ENVIRONMENT: str = os.environ.get("SENTRY_ENVIRONMENT", "production")
    SENTRY_RELEASE: Optional[str] = os.environ.get("SENTRY_RELEASE")
    SENTRY_TRACES_SAMPLE_RATE: float = float(
        os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")
    )
    SENTRY_ENABLED: bool = os.environ.get("SENTRY_ENABLED", "true").lower() == "true"
    
    # Error handling settings
    INCLUDE_TRACEBACK_IN_RESPONSE: bool = os.environ.get(
        "CELL0_DEBUG_ERRORS", "false"
    ).lower() == "true"
    MAX_RETRY_ATTEMPTS: int = int(os.environ.get("CELL0_MAX_RETRIES", "3"))
    RETRY_BASE_DELAY: float = float(os.environ.get("CELL0_RETRY_DELAY", "1.0"))
    RETRY_MAX_DELAY: float = float(os.environ.get("CELL0_RETRY_MAX_DELAY", "60.0"))
    
    # Graceful degradation
    ENABLE_FALLBACKS: bool = os.environ.get("CELL0_ENABLE_FALLBACKS", "true").lower() == "true"
    FALLBACK_MODEL: str = os.environ.get("CELL0_FALLBACK_MODEL", "qwen2.5:1.8b")


# ============================================================================
# Enums
# ============================================================================

class ErrorSeverity(Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    NETWORK = "network"


# ============================================================================
# Cell0Exception Base Class
# ============================================================================

@dataclass
class ErrorContext:
    """Context information for errors"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    extra: Dict[str, Any] = field(default_factory=dict)


class Cell0Exception(Exception):
    """
    Base exception class for Cell 0 OS
    
    Provides:
    - Structured error codes
    - User-friendly messages
    - Remediation guidance
    - Severity classification
    - Error categorization
    """
    
    # Default values - override in subclasses
    code: str = "CELL0_ERROR"
    status_code: int = 500
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.INTERNAL
    default_user_message: str = "An unexpected error occurred"
    default_remediation: str = "Please try again later or contact support"
    retryable: bool = False
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        user_message: Optional[str] = None,
        remediation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message or self.default_user_message)
        
        self.code = code or self.code
        self.message = message or self.default_user_message
        self.user_message = user_message or self.default_user_message
        self.remediation = remediation or self.default_remediation
        self.details = details or {}
        self.cause = cause
        self.context = context or ErrorContext()
        self.timestamp = datetime.utcnow()
        self.traceback_str = traceback.format_exc() if sys.exc_info()[0] else None
    
    def to_dict(self, include_traceback: bool = False) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        result = {
            "error": {
                "code": self.code,
                "message": self.user_message,
                "remediation": self.remediation,
                "severity": self.severity.value,
                "category": self.category.value,
                "retryable": self.retryable,
                "timestamp": self.timestamp.isoformat(),
            }
        }
        
        if self.details:
            result["error"]["details"] = self.details
        
        if include_traceback and self.traceback_str:
            result["error"]["traceback"] = self.traceback_str
        
        return result
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ============================================================================
# Specific Exception Classes
# ============================================================================

# Authentication Errors
class AuthenticationException(Cell0Exception):
    """Base authentication error"""
    code = "AUTH_ERROR"
    status_code = 401
    severity = ErrorSeverity.WARNING
    category = ErrorCategory.AUTHENTICATION
    default_user_message = "Authentication failed"
    default_remediation = "Please check your credentials and try again"


class InvalidCredentialsException(AuthenticationException):
    """Invalid username or password"""
    code = "AUTH_INVALID_CREDENTIALS"
    default_user_message = "Invalid username or password"


class TokenExpiredException(AuthenticationException):
    """Token has expired"""
    code = "AUTH_TOKEN_EXPIRED"
    default_user_message = "Your session has expired"
    default_remediation = "Please log in again"


class InsufficientPermissionsException(Cell0Exception):
    """Not authorized for operation"""
    code = "AUTH_INSUFFICIENT_PERMISSIONS"
    status_code = 403
    severity = ErrorSeverity.WARNING
    category = ErrorCategory.AUTHORIZATION
    default_user_message = "You don't have permission for this action"
    default_remediation = "Contact your administrator for access"


# Validation Errors
class ValidationException(Cell0Exception):
    """Input validation error"""
    code = "VALIDATION_ERROR"
    status_code = 400
    severity = ErrorSeverity.WARNING
    category = ErrorCategory.VALIDATION
    default_user_message = "Invalid input"
    default_remediation = "Please check your input and try again"


class ResourceNotFoundException(Cell0Exception):
    """Requested resource not found"""
    code = "NOT_FOUND"
    status_code = 404
    severity = ErrorSeverity.WARNING
    category = ErrorCategory.NOT_FOUND
    default_user_message = "The requested resource was not found"
    default_remediation = "Please verify the resource identifier"


# Service Errors
class ServiceUnavailableException(Cell0Exception):
    """Service temporarily unavailable"""
    code = "SERVICE_UNAVAILABLE"
    status_code = 503
    severity = ErrorSeverity.ERROR
    category = ErrorCategory.SERVICE_UNAVAILABLE
    default_user_message = "Service temporarily unavailable"
    default_remediation = "Please try again in a few moments"
    retryable = True


class ExternalServiceException(Cell0Exception):
    """External service error"""
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502
    severity = ErrorSeverity.ERROR
    category = ErrorCategory.EXTERNAL_SERVICE
    default_user_message = "External service error"
    default_remediation = "Please try again later"
    retryable = True


class OllamaException(ExternalServiceException):
    """Ollama service error"""
    code = "OLLAMA_ERROR"
    default_user_message = "AI model service unavailable"
    default_remediation = "Using fallback model. Check Ollama status with 'systemctl status ollama'"


class SignalException(ExternalServiceException):
    """Signal service error"""
    code = "SIGNAL_ERROR"
    default_user_message = "Messaging service unavailable"
    default_remediation = "Check Signal daemon status with 'systemctl status signal-cli'"


class RateLimitException(Cell0Exception):
    """Rate limit exceeded"""
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    severity = ErrorSeverity.WARNING
    category = ErrorCategory.RATE_LIMIT
    default_user_message = "Too many requests"
    default_remediation = "Please slow down and try again later"
    retryable = True
    
    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.remediation = f"Please wait {retry_after} seconds before retrying"


class TimeoutException(Cell0Exception):
    """Operation timed out"""
    code = "TIMEOUT"
    status_code = 504
    severity = ErrorSeverity.WARNING
    category = ErrorCategory.TIMEOUT
    default_user_message = "The operation timed out"
    default_remediation = "Please try again with a longer timeout"
    retryable = True


class ConfigurationException(Cell0Exception):
    """Configuration error"""
    code = "CONFIG_ERROR"
    status_code = 500
    severity = ErrorSeverity.ERROR
    category = ErrorCategory.CONFIGURATION
    default_user_message = "Configuration error"
    default_remediation = "Please check your configuration and restart the service"


class NetworkException(Cell0Exception):
    """Network error"""
    code = "NETWORK_ERROR"
    status_code = 502
    severity = ErrorSeverity.ERROR
    category = ErrorCategory.NETWORK
    default_user_message = "Network error"
    default_remediation = "Please check your network connection"
    retryable = True


# ============================================================================
# Sentry Integration
# ============================================================================

class SentryManager:
    """Manages Sentry error tracking integration"""
    
    def __init__(self):
        self.initialized = False
        
        if not SENTRY_AVAILABLE:
            logger.debug("Sentry SDK not available")
            return
        
        if not ErrorConfig.SENTRY_ENABLED:
            logger.debug("Sentry disabled by configuration")
            return
        
        if not ErrorConfig.SENTRY_DSN:
            logger.debug("SENTRY_DSN not set, Sentry disabled")
            return
    
    def initialize(self):
        """Initialize Sentry SDK"""
        if not SENTRY_AVAILABLE or self.initialized:
            return
        
        try:
            sentry_logging = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )
            
            sentry_sdk.init(
                dsn=ErrorConfig.SENTRY_DSN,
                environment=ErrorConfig.SENTRY_ENVIRONMENT,
                release=ErrorConfig.SENTRY_RELEASE,
                traces_sample_rate=ErrorConfig.SENTRY_TRACES_SAMPLE_RATE,
                integrations=[sentry_logging],
                attach_stacktrace=True,
                include_local_variables=True,
            )
            
            self.initialized = True
            logger.info("Sentry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict] = None,
        tags: Optional[Dict] = None,
    ) -> Optional[str]:
        """Capture exception in Sentry"""
        if not SENTRY_AVAILABLE or not self.initialized:
            return None
        
        try:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)
                
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                
                event_id = sentry_sdk.capture_exception(exception)
                return event_id
                
        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")
            return None
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        tags: Optional[Dict] = None,
    ) -> Optional[str]:
        """Capture message in Sentry"""
        if not SENTRY_AVAILABLE or not self.initialized:
            return None
        
        try:
            with sentry_sdk.push_scope() as scope:
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                
                event_id = sentry_sdk.capture_message(message, level=level)
                return event_id
                
        except Exception as e:
            logger.error(f"Failed to capture message in Sentry: {e}")
            return None
    
    def set_user_context(self, user_id: str, **kwargs):
        """Set user context for Sentry"""
        if not SENTRY_AVAILABLE or not self.initialized:
            return
        
        sentry_sdk.set_user({"id": user_id, **kwargs})


# Global Sentry manager instance
_sentry_manager: Optional[SentryManager] = None


def get_sentry_manager() -> SentryManager:
    """Get or create Sentry manager"""
    global _sentry_manager
    if _sentry_manager is None:
        _sentry_manager = SentryManager()
    return _sentry_manager


# ============================================================================
# Retry Logic
# ============================================================================

def retry_with_backoff(
    max_attempts: int = None,
    base_delay: float = None,
    max_delay: float = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator to retry function with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Callback function(exception, attempt_number) called on each retry
    """
    max_attempts = max_attempts or ErrorConfig.MAX_RETRY_ATTEMPTS
    base_delay = base_delay or ErrorConfig.RETRY_BASE_DELAY
    max_delay = max_delay or ErrorConfig.RETRY_MAX_DELAY
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff and jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay = delay * (0.5 + 0.5 * __import__('random').random())
                        
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {delay:.1f}s: {e}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        await __import__('asyncio').sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay = delay * (0.5 + 0.5 * __import__('random').random())
                        
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {delay:.1f}s: {e}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        __import__('time').sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
            
            raise last_exception
        
        if __import__('asyncio').iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================================
# Graceful Degradation
# ============================================================================

class FallbackManager:
    """Manages graceful fallbacks for failed services"""
    
    def __init__(self):
        self.fallbacks: Dict[str, Callable] = {}
        self.failure_counts: Dict[str, int] = {}
        self._lock = __import__('asyncio').Lock()
    
    def register_fallback(self, service_name: str, fallback_func: Callable):
        """Register a fallback function for a service"""
        self.fallbacks[service_name] = fallback_func
        logger.debug(f"Registered fallback for {service_name}")
    
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with fallback on failure"""
        try:
            result = await primary_func(*args, **kwargs)
            
            # Reset failure count on success
            async with self._lock:
                if service_name in self.failure_counts:
                    del self.failure_counts[service_name]
            
            return result
            
        except Exception as e:
            # Increment failure count
            async with self._lock:
                self.failure_counts[service_name] = self.failure_counts.get(service_name, 0) + 1
            
            logger.warning(
                f"Primary service {service_name} failed "
                f"(failure #{self.failure_counts[service_name]}): {e}"
            )
            
            # Try fallback if available
            fallback = self.fallbacks.get(service_name)
            if fallback and ErrorConfig.ENABLE_FALLBACKS:
                logger.info(f"Using fallback for {service_name}")
                
                # Track fallback usage in Sentry
                sentry = get_sentry_manager()
                sentry.capture_message(
                    f"Fallback activated for {service_name}",
                    level="warning",
                    tags={"service": service_name, "failure_count": self.failure_counts[service_name]},
                )
                
                return await fallback(*args, **kwargs)
            
            # No fallback available - re-raise
            raise
    
    def is_degraded(self, service_name: str) -> bool:
        """Check if service is in degraded mode"""
        return self.failure_counts.get(service_name, 0) >= 3


# Global fallback manager
_fallback_manager: Optional[FallbackManager] = None


def get_fallback_manager() -> FallbackManager:
    """Get or create fallback manager"""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = FallbackManager()
    return _fallback_manager


# ============================================================================
# Error Handler
# ============================================================================

class ErrorHandler:
    """Central error handler for Cell 0 OS"""
    
    def __init__(self):
        self.sentry = get_sentry_manager()
        self.sentry.initialize()
    
    def handle_exception(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        capture: bool = True,
    ) -> Cell0Exception:
        """
        Handle an exception and convert to Cell0Exception if needed
        
        Args:
            exception: The exception to handle
            context: Error context information
            capture: Whether to capture in Sentry
        
        Returns:
            Cell0Exception (original or converted)
        """
        # If already Cell0Exception, just capture and return
        if isinstance(exception, Cell0Exception):
            if capture and exception.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL, ErrorSeverity.FATAL):
                self.sentry.capture_exception(
                    exception,
                    context=exception.details,
                    tags={
                        "code": exception.code,
                        "severity": exception.severity.value,
                        "category": exception.category.value,
                    },
                )
            return exception
        
        # Convert to Cell0Exception
        converted = self._convert_exception(exception, context)
        
        if capture:
            self.sentry.capture_exception(
                exception,
                context={"converted_to": converted.code},
            )
        
        return converted
    
    def _convert_exception(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
    ) -> Cell0Exception:
        """Convert a generic exception to Cell0Exception"""
        # Map common exceptions
        exc_type = type(exception)
        exc_str = str(exception).lower()
        
        # Network errors
        if "connection" in exc_str or "timeout" in exc_str:
            if "ollama" in exc_str:
                return OllamaException(
                    message=str(exception),
                    cause=exception,
                    context=context,
                )
            elif "signal" in exc_str:
                return SignalException(
                    message=str(exception),
                    cause=exception,
                    context=context,
                )
            else:
                return NetworkException(
                    message=str(exception),
                    cause=exception,
                    context=context,
                )
        
        # Default conversion
        return Cell0Exception(
            message=str(exception),
            cause=exception,
            context=context,
            details={"original_type": exc_type.__name__},
        )


# Global error handler
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get or create error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Config
    'ErrorConfig',
    # Enums
    'ErrorSeverity',
    'ErrorCategory',
    # Base Class
    'Cell0Exception',
    'ErrorContext',
    # Authentication
    'AuthenticationException',
    'InvalidCredentialsException',
    'TokenExpiredException',
    'InsufficientPermissionsException',
    # Validation
    'ValidationException',
    'ResourceNotFoundException',
    # Service
    'ServiceUnavailableException',
    'ExternalServiceException',
    'OllamaException',
    'SignalException',
    'RateLimitException',
    'TimeoutException',
    'ConfigurationException',
    'NetworkException',
    # Sentry
    'SentryManager',
    'get_sentry_manager',
    # Retry
    'retry_with_backoff',
    # Fallback
    'FallbackManager',
    'get_fallback_manager',
    # Handler
    'ErrorHandler',
    'get_error_handler',
]
