"""
test_jwt_handler.py - Unit tests for sovereign JWT handler
"""

import os
import pytest
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

# Add cell0 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cell0.engine.security.jwt_handler import (
    Environment,
    JWTError,
    InvalidTokenError,
    ExpiredTokenError,
    InvalidSignatureError,
    ProductionKeyError,
    KeyPair,
    KeyManager,
    TokenPayload,
    JWTHandler,
    TokenManager,
    get_key_manager,
    create_token,
    validate_token,
    decode_token,
    verify_production_readiness,
)


class TestEnvironmentDetection:
    """Test environment detection"""
    
    def test_development_default(self, monkeypatch):
        monkeypatch.delenv("CELL0_ENV", raising=False)
        from cell0.engine.security.jwt_handler import get_environment
        assert get_environment() == Environment.DEVELOPMENT
    
    def test_production_env(self, monkeypatch):
        monkeypatch.setenv("CELL0_ENV", "production")
        from cell0.engine.security.jwt_handler import get_environment
        assert get_environment() == Environment.PRODUCTION
    
    def test_staging_env(self, monkeypatch):
        monkeypatch.setenv("CELL0_ENV", "staging")
        from cell0.engine.security.jwt_handler import get_environment
        assert get_environment() == Environment.STAGING


class TestKeyManager:
    """Test key management with sovereign policy"""
    
    def test_auto_generate_in_dev(self, monkeypatch, capsys):
        """Dev mode should auto-generate with warnings"""
        monkeypatch.setenv("CELL0_ENV", "development")
        monkeypatch.delenv("CELL0_JWT_SECRET", raising=False)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            km = KeyManager()
            key = km.get_key()
            
            assert key.secret is not None
            assert len(key.secret) >= 32
            assert key.source.startswith("auto-generated")
    
    def test_fail_fast_in_production_no_key(self, monkeypatch):
        """Production should fail fast without keys"""
        monkeypatch.setenv("CELL0_ENV", "production")
        monkeypatch.delenv("CELL0_JWT_SECRET", raising=False)
        
        km = KeyManager()
        with pytest.raises(ProductionKeyError) as exc_info:
            km.get_key()
        
        assert "PRODUCTION SECURITY VIOLATION" in str(exc_info.value)
    
    def test_load_from_env_secret(self, monkeypatch):
        """Load key from environment variable"""
        monkeypatch.setenv("CELL0_ENV", "production")
        monkeypatch.setenv("CELL0_JWT_SECRET", "a" * 64)
        
        km = KeyManager()
        km._key_cache.clear()  # Reset cache
        key = km._load_from_env()
        
        assert key is not None
        assert key.secret == "a" * 64
        assert key.algorithm == "HS256"
    
    def test_load_from_env_insufficient_secret(self, monkeypatch):
        """Reject short secrets"""
        monkeypatch.setenv("CELL0_JWT_SECRET", "short")  # Too short
        
        km = KeyManager()
        key = km._load_from_env()
        
        assert key is None


class TestJWTEncodeDecode:
    """Test JWT encoding and decoding"""
    
    def test_encode_decode_success(self, monkeypatch):
        """Basic encode/decode roundtrip"""
        monkeypatch.setenv("CELL0_ENV", "development")
        monkeypatch.delenv("CELL0_JWT_SECRET", raising=False)
        
        handler = JWTHandler()
        
        payload = TokenPayload(
            subject="user123",
            scopes=["read", "write"],
            roles=["operator"],
        )
        
        token = handler.encode(payload, expires_in=timedelta(hours=1))
        assert token.count(".") == 2  # JWT format
        
        decoded = handler.decode(token)
        assert decoded.subject == "user123"
        assert decoded.scopes == ["read", "write"]
        assert decoded.roles == ["operator"]
    
    def test_expired_token(self, monkeypatch):
        """Expired tokens should be rejected"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        handler = JWTHandler()
        
        payload = TokenPayload(subject="user123")
        token = handler.encode(payload, expires_in=timedelta(seconds=-1))  # Already expired
        
        with pytest.raises(ExpiredTokenError):
            handler.decode(token)
    
    def test_invalid_signature(self, monkeypatch):
        """Tampered tokens should be rejected"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        handler = JWTHandler()
        
        payload = TokenPayload(subject="user123")
        token = handler.encode(payload, expires_in=timedelta(hours=1))
        
        # Tamper with the token
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        with pytest.raises(InvalidTokenError):
            handler.decode(tampered)
    
    def test_invalid_format(self, monkeypatch):
        """Invalid JWT format should be rejected"""
        handler = JWTHandler()
        
        with pytest.raises(InvalidTokenError):
            handler.decode("not.a.valid.jwt")
        
        with pytest.raises(InvalidTokenError):
            handler.decode("invalid")
    
    def test_verify_audience(self, monkeypatch):
        """Audience verification"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        handler = JWTHandler()
        
        payload = TokenPayload(subject="user123", audience="cell0-api")
        token = handler.encode(payload)
        
        # Correct audience
        decoded = handler.decode(token, audience="cell0-api")
        assert decoded.subject == "user123"
        
        # Wrong audience
        with pytest.raises(InvalidTokenError):
            handler.decode(token, audience="wrong-api")


class TestTokenManager:
    """Test high-level token lifecycle"""
    
    def test_create_access_token(self, monkeypatch):
        """Create access token with scopes"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        manager = TokenManager()
        token = manager.create_access_token(
            subject="user123",
            scopes=["agents:read", "tasks:write"],
            roles=["operator"],
            expires_in=timedelta(minutes=30),
        )
        
        assert token.count(".") == 2
        
        # Validate the token
        payload = manager.validate_token(token)
        assert payload.subject == "user123"
        assert "agents:read" in payload.scopes
    
    def test_validate_token_with_required_scopes(self, monkeypatch):
        """Validate with required scopes"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        manager = TokenManager()
        token = manager.create_access_token(
            subject="user123",
            scopes=["read", "write"],
        )
        
        # Should succeed
        payload = manager.validate_token(token, required_scopes=["read"])
        assert payload.subject == "user123"
        
        # Should fail
        with pytest.raises(InvalidTokenError) as exc_info:
            manager.validate_token(token, required_scopes=["admin"])
        
        assert "Missing required scopes" in str(exc_info.value)
    
    def test_revoke_token(self, monkeypatch):
        """Token revocation"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        manager = TokenManager()
        token = manager.create_access_token(subject="user123")
        
        # Token should be valid initially
        manager.validate_token(token)
        
        # Revoke the token
        manager.revoke_token(token)
        
        # Token should now be invalid
        with pytest.raises(InvalidTokenError) as exc_info:
            manager.validate_token(token)
        
        assert "revoked" in str(exc_info.value).lower()
    
    def test_create_refresh_token(self, monkeypatch):
        """Create refresh token"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        manager = TokenManager()
        token = manager.create_refresh_token(
            subject="user123",
            expires_in=timedelta(days=7),
        )
        
        payload = manager.validate_token(token)
        assert payload.subject == "user123"
        assert "refresh" in payload.scopes


class TestConvenienceFunctions:
    """Test quick access functions"""
    
    def test_create_and_validate_token(self, monkeypatch):
        """Quick token creation and validation"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        token = create_token(
            subject="user123",
            scopes=["read"],
            expires_in_minutes=60,
        )
        
        payload = validate_token(token, required_scopes=["read"])
        assert payload.subject == "user123"
    
    def test_decode_without_verification(self, monkeypatch):
        """Decode token without signature verification"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        handler = JWTHandler()
        payload = TokenPayload(subject="user123")
        token = handler.encode(payload)
        
        decoded = decode_token(token)
        assert decoded.subject == "user123"


class TestProductionReadiness:
    """Test production readiness verification"""
    
    def test_not_production_environment(self, monkeypatch):
        """Not ready if not in production"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        is_ready, issues = verify_production_readiness()
        assert not is_ready
        assert any("not production" in issue.lower() for issue in issues)
    
    def test_production_with_auto_generated_keys(self, monkeypatch):
        """Not ready with auto-generated keys in production"""
        monkeypatch.setenv("CELL0_ENV", "production")
        monkeypatch.delenv("CELL0_JWT_SECRET", raising=False)
        
        is_ready, issues = verify_production_readiness()
        assert not is_ready
        # Should fail because no keys configured


class TestTokenPayload:
    """Test TokenPayload data class"""
    
    def test_to_dict(self):
        """Convert payload to dictionary"""
        payload = TokenPayload(
            subject="user123",
            issuer="test-issuer",
            audience="test-audience",
            scopes=["read", "write"],
            metadata={"custom": "data"},
        )
        
        d = payload.to_dict()
        assert d["sub"] == "user123"
        assert d["iss"] == "test-issuer"
        assert d["aud"] == "test-audience"
        assert d["scopes"] == ["read", "write"]
        assert d["metadata"] == {"custom": "data"}
    
    def test_from_dict(self):
        """Create payload from dictionary"""
        d = {
            "sub": "user123",
            "iss": "test-issuer",
            "exp": datetime.utcnow().timestamp() + 3600,
            "scopes": ["read"],
            "jti": "test-id",
        }
        
        payload = TokenPayload.from_dict(d)
        assert payload.subject == "user123"
        assert payload.issuer == "test-issuer"
        assert payload.scopes == ["read"]
        assert payload.jwt_id == "test-id"
    
    def test_jwt_id_auto_generated(self):
        """JWT ID should be auto-generated"""
        payload1 = TokenPayload(subject="user1")
        payload2 = TokenPayload(subject="user2")
        
        assert payload1.jwt_id != payload2.jwt_id
        assert len(payload1.jwt_id) > 0


class TestKeyRotation:
    """Test key rotation detection"""
    
    def test_rotation_detection(self, monkeypatch):
        """Detect key rotation"""
        monkeypatch.setenv("CELL0_ENV", "development")
        
        km = KeyManager()
        km._key_cache.clear()
        km._key_hashes.clear()
        
        # Initial key
        key = km.get_key()
        km._key_hashes["default"] = "fake_hash"
        
        # Should detect rotation (key changed but hash didn't update)
        rotated = km.check_rotation()
        assert rotated is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
