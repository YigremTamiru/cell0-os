"""
Cell 0 Security Module

Provides security features for Cell 0 OS:
- Authentication and authorization
- Rate limiting
- Secrets management
- Error handling
"""

# These will be populated by the security agent
__all__ = [
    "AuthMiddleware",
    "RateLimiter",
    "CircuitBreaker",
    "Cell0Exception",
    "setup_security",
]
