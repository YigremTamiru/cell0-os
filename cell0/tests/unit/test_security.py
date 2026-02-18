"""
Unit Tests for Cell 0 OS Security Module

Tests authentication, rate limiting, and security features.
"""

import pytest
import asyncio
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

# Import modules under test
try:
    from cell0.engine.security.rate_limiter import (
        RateLimiter,
        RateLimitExceeded,
        TokenBucket,
        SlidingWindow,
    )
    HAS_RATE_LIMITER = True
except ImportError:
    HAS_RATE_LIMITER = False
    
try:
    from cell0.engine.security.auth import (
        AuthMiddleware,
        TokenValidator,
        Permission,
    )
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False


# =============================================================================
# Token Bucket Tests
# =============================================================================

@pytest.mark.skipif(not HAS_RATE_LIMITER, reason="Rate limiter not available")
class TestTokenBucket:
    """Tests for TokenBucket rate limiting"""
    
    @pytest.fixture
    def bucket(self):
        """Create fresh token bucket"""
        return TokenBucket(
            capacity=10,
            refill_rate=1.0  # 1 token per second
        )
    
    def test_initial_capacity(self, bucket):
        """Test bucket starts full"""
        assert bucket.tokens == 10
        assert bucket.capacity == 10
    
    def test_consume_tokens(self, bucket):
        """Test consuming tokens"""
        assert bucket.consume(5) is True
        assert bucket.tokens == 5
        
        assert bucket.consume(5) is True
        assert bucket.tokens == 0
    
    def test_consume_more_than_available(self, bucket):
        """Test consuming more tokens than available"""
        assert bucket.consume(15) is False
        assert bucket.tokens == 10  # No change
    
    def test_token_refill(self, bucket):
        """Test token refill over time"""
        bucket.consume(10)  # Empty the bucket
        assert bucket.tokens == 0
        
        # Wait for refill
        time.sleep(1.1)
        
        # Should have 1 token now
        assert bucket.tokens >= 1
        assert bucket.consume(1) is True
    
    def test_refill_does_not_exceed_capacity(self, bucket):
        """Test refill doesn't exceed max capacity"""
        # Wait without consuming
        time.sleep(2)
        
        # Should still be at capacity
        assert bucket.tokens <= bucket.capacity


# =============================================================================
# Sliding Window Tests
# =============================================================================

@pytest.mark.skipif(not HAS_RATE_LIMITER, reason="Rate limiter not available")
class TestSlidingWindow:
    """Tests for SlidingWindow rate limiting"""
    
    @pytest.fixture
    def window(self):
        """Create fresh sliding window"""
        return SlidingWindow(
            window_size=60,  # 60 second window
            max_requests=10
        )
    
    def test_allow_request_under_limit(self, window):
        """Test requests allowed under limit"""
        for i in range(10):
            assert window.allow_request(f"user_{i}") is True
    
    def test_block_request_over_limit(self, window):
        """Test requests blocked over limit"""
        user_id = "test_user"
        
        # Make 10 requests
        for _ in range(10):
            window.allow_request(user_id)
        
        # 11th request should be blocked
        assert window.allow_request(user_id) is False
    
    def test_separate_windows_per_user(self, window):
        """Test each user has separate window"""
        # User 1 makes max requests
        for _ in range(10):
            window.allow_request("user1")
        
        # User 2 should still be able to make requests
        assert window.allow_request("user2") is True
    
    def test_window_slides_over_time(self, window):
        """Test old requests fall out of window"""
        user_id = "test_user"
        
        # Use smaller window for test
        window.window_size = 1  # 1 second
        
        # Make requests
        for _ in range(10):
            window.allow_request(user_id)
        
        # Blocked
        assert window.allow_request(user_id) is False
        
        # Wait for window to slide
        time.sleep(1.1)
        
        # Should be allowed again
        assert window.allow_request(user_id) is True


# =============================================================================
# RateLimiter Tests
# =============================================================================

@pytest.mark.skipif(not HAS_RATE_LIMITER, reason="Rate limiter not available")
class TestRateLimiter:
    """Tests for RateLimiter class"""
    
    @pytest.fixture
    def limiter(self):
        """Create fresh rate limiter"""
        return RateLimiter(
            default_limit=100,
            window_seconds=60
        )
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, limiter):
        """Test rate limit check allows requests under limit"""
        result = await limiter.check_rate_limit("user123", "/api/test")
        
        assert result.allowed is True
        assert result.remaining > 0
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, limiter):
        """Test rate limit check blocks exceeded requests"""
        # Set very low limit
        limiter.default_limit = 2
        
        # Make requests up to limit
        await limiter.check_rate_limit("user123", "/api/test")
        await limiter.check_rate_limit("user123", "/api/test")
        
        # Third request should be blocked
        result = await limiter.check_rate_limit("user123", "/api/test")
        
        assert result.allowed is False
        assert result.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_different_endpoints_separate_limits(self, limiter):
        """Test different endpoints have separate rate limits"""
        user_id = "user123"
        limiter.default_limit = 5
        
        # Exhaust limit on one endpoint
        for _ in range(5):
            await limiter.check_rate_limit(user_id, "/api/a")
        
        # Different endpoint should still work
        result = await limiter.check_rate_limit(user_id, "/api/b")
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_custom_limits_per_endpoint(self, limiter):
        """Test custom rate limits for specific endpoints"""
        limiter.set_endpoint_limit("/api/expensive", 5)
        
        # Make requests up to custom limit
        for _ in range(5):
            result = await limiter.check_rate_limit("user123", "/api/expensive")
            assert result.allowed is True
        
        # Should be blocked at 6
        result = await limiter.check_rate_limit("user123", "/api/expensive")
        assert result.allowed is False


# =============================================================================
# Auth Middleware Tests
# =============================================================================

@pytest.mark.skipif(not HAS_AUTH, reason="Auth module not available")
class TestAuthMiddleware:
    """Tests for authentication middleware"""
    
    @pytest.fixture
    def middleware(self):
        """Create auth middleware"""
        return AuthMiddleware(
            secret_key="test-secret-key",
            token_ttl=3600
        )
    
    @pytest.mark.asyncio
    async def test_validate_valid_token(self, middleware):
        """Test validating a valid token"""
        # Create a token
        token = middleware.create_token(
            user_id="user123",
            permissions=["read", "write"]
        )
        
        # Validate it
        result = await middleware.validate_token(token)
        
        assert result.valid is True
        assert result.user_id == "user123"
        assert "read" in result.permissions
    
    @pytest.mark.asyncio
    async def test_validate_expired_token(self, middleware):
        """Test validating an expired token"""
        # Create token with very short TTL
        middleware.token_ttl = -1  # Already expired
        token = middleware.create_token(user_id="user123")
        
        # Reset TTL for validation
        middleware.token_ttl = 3600
        
        result = await middleware.validate_token(token)
        
        assert result.valid is False
        assert result.error == "token_expired"
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, middleware):
        """Test validating an invalid token"""
        result = await middleware.validate_token("invalid-token")
        
        assert result.valid is False
    
    @pytest.mark.asyncio
    async def test_check_permissions(self, middleware):
        """Test permission checking"""
        token = middleware.create_token(
            user_id="user123",
            permissions=["read", "write"]
        )
        
        # Has permission
        assert await middleware.check_permission(token, "read") is True
        
        # Doesn't have permission
        assert await middleware.check_permission(token, "admin") is False


# =============================================================================
# Security Utility Tests
# =============================================================================

class TestSecurityUtils:
    """Tests for security utilities"""
    
    def test_secure_compare(self):
        """Test constant-time comparison"""
        from hmac import compare_digest
        
        a = b"secret-token-123"
        b = b"secret-token-123"
        c = b"different-token"
        
        assert compare_digest(a, b) is True
        assert compare_digest(a, c) is False
    
    def test_hash_consistency(self):
        """Test hash function consistency"""
        data = "test-data-123"
        
        hash1 = hashlib.sha256(data.encode()).hexdigest()
        hash2 = hashlib.sha256(data.encode()).hexdigest()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_hash_uniqueness(self):
        """Test different inputs produce different hashes"""
        hash1 = hashlib.sha256(b"data1").hexdigest()
        hash2 = hashlib.sha256(b"data2").hexdigest()
        
        assert hash1 != hash2


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.skipif(not HAS_RATE_LIMITER or not HAS_AUTH, 
                    reason="Security modules not available")
class TestSecurityIntegration:
    """Integration tests for security features"""
    
    @pytest.mark.asyncio
    async def test_auth_with_rate_limiting(self):
        """Test authentication with rate limiting"""
        auth = AuthMiddleware(secret_key="test-key")
        limiter = RateLimiter(default_limit=5)
        
        user_id = "user123"
        
        # Create token
        token = auth.create_token(user_id=user_id)
        
        # Simulate API calls with auth and rate limiting
        for i in range(5):
            # Check rate limit
            rate_result = await limiter.check_rate_limit(user_id, "/api/protected")
            assert rate_result.allowed is True
            
            # Validate token
            auth_result = await auth.validate_token(token)
            assert auth_result.valid is True
        
        # Should be rate limited now
        rate_result = await limiter.check_rate_limit(user_id, "/api/protected")
        assert rate_result.allowed is False


# =============================================================================
# Mock Tests (when modules not available)
# =============================================================================

@pytest.mark.skipif(HAS_RATE_LIMITER, reason="Using real rate limiter")
class TestRateLimiterMock:
    """Mock tests for rate limiter"""
    
    def test_rate_limit_concept(self):
        """Test rate limiting concept"""
        # Simple counter-based rate limit simulation
        requests = []
        limit = 5
        window = 60
        
        now = time.time()
        
        # Simulate requests
        for i in range(10):
            # Clean old requests
            requests = [r for r in requests if now - r < window]
            
            if len(requests) < limit:
                requests.append(now)
                allowed = True
            else:
                allowed = False
            
            if i < 5:
                assert allowed is True
            else:
                assert allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
