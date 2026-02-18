"""Tests for Cell 0 OS Tool Security System"""
import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta

# Import security modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.security.tool_profiles import (
    ToolProfile, ToolPolicy, PermissionLevel, RiskLevel,
    ToolGroup, ProfileRegistry, get_profile, get_registry
)
from engine.security.tool_policy import (
    PolicyEnforcer, PolicyViolation, RateLimitExceeded,
    ToolCallContext, AgentPolicyManager, get_policy_manager,
    PathValidator, RateLimiter
)
from engine.security.tool_audit import (
    ToolAuditor, AuditEvent, MemoryBackend, FileBackend,
    SQLiteBackend, AuditFormatter
)
from engine.security.sandbox import (
    SandboxManager, SandboxConfig, SandboxResult,
    SubprocessSandbox, SandboxError, get_sandbox_manager
)


class TestToolProfiles:
    """Test tool profile definitions."""
    
    def test_permission_levels(self):
        """Test permission level enum."""
        assert PermissionLevel.DENY != PermissionLevel.ALLOW
        assert PermissionLevel.SANDBOX != PermissionLevel.ELEVATED
    
    def test_risk_levels(self):
        """Test risk level enum."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CRITICAL.value == "critical"
    
    def test_tool_policy_defaults(self):
        """Test tool policy defaults."""
        policy = ToolPolicy()
        assert policy.permission == PermissionLevel.DENY
        assert policy.risk_level == RiskLevel.MEDIUM
        assert policy.rate_limit is None
    
    def test_tool_policy_custom(self):
        """Test tool policy with custom values."""
        policy = ToolPolicy(
            permission=PermissionLevel.ALLOW,
            risk_level=RiskLevel.HIGH,
            rate_limit=60,
            allowed_paths=["./workspace/*"]
        )
        assert policy.permission == PermissionLevel.ALLOW
        assert policy.risk_level == RiskLevel.HIGH
        assert policy.rate_limit == 60
        assert "./workspace/*" in policy.allowed_paths
    
    def test_profile_creation(self):
        """Test profile creation."""
        profile = ToolProfile(
            name="test",
            description="Test profile"
        )
        assert profile.name == "test"
        assert profile.description == "Test profile"
        assert profile.tool_policies == {}
    
    def test_tool_group_members(self):
        """Test tool group membership."""
        fs_tools = ToolGroup.get_members(ToolGroup.FILESYSTEM)
        assert "read" in fs_tools
        assert "write" in fs_tools
        assert "edit" in fs_tools
    
    def test_tool_group_lookup(self):
        """Test finding groups for a tool."""
        groups = ToolGroup.get_groups_for_tool("read")
        assert ToolGroup.FILESYSTEM in groups
    
    def test_built_in_profiles(self):
        """Test built-in profiles exist."""
        registry = ProfileRegistry()
        
        profiles = ["minimal", "coding", "messaging", "full"]
        for name in profiles:
            profile = registry.get(name)
            assert profile is not None, f"Profile {name} should exist"
            assert profile.name == name
    
    def test_profile_inheritance(self):
        """Test profile inheritance."""
        registry = get_registry()
        coding = registry.get("coding")
        
        assert coding.inherits == "minimal"
        # Should have filesystem group policy
        assert ToolGroup.FILESYSTEM in coding.group_policies


class TestPathValidator:
    """Test path validation."""
    
    def test_allow_all(self):
        """Test with no restrictions."""
        assert PathValidator.validate("/any/path", None, None) is True
    
    def test_allowed_pattern(self):
        """Test allowed path pattern."""
        assert PathValidator.validate(
            "./workspace/file.txt",
            ["./workspace/*"],
            None
        ) is True
    
    def test_denied_pattern(self):
        """Test denied path pattern."""
        assert PathValidator.validate(
            "./secrets/key.txt",
            None,
            ["*/secrets/*"]
        ) is False
    
    def test_allow_override_deny(self):
        """Test denied takes precedence over allowed."""
        # Denied should be checked first
        result = PathValidator.validate(
            "./workspace/secrets/key.txt",
            ["./workspace/*"],
            ["*/secrets/*"]
        )
        assert result is False
    
    def test_not_in_allowed(self):
        """Test path not in allowed patterns."""
        assert PathValidator.validate(
            "/etc/passwd",
            ["./workspace/*"],
            None
        ) is False


class TestRateLimiter:
    """Test rate limiting."""
    
    def test_basic_limit(self):
        """Test basic rate limiting."""
        limiter = RateLimiter()
        
        # Should allow 5 calls
        for i in range(5):
            assert limiter.check_and_consume("key1", 5) is True
        
        # 6th should fail
        assert limiter.check_and_consume("key1", 5) is False
    
    def test_separate_keys(self):
        """Test separate rate limit buckets."""
        limiter = RateLimiter()
        
        # Use up key1
        for i in range(5):
            limiter.check_and_consume("key1", 5)
        
        # key2 should still work
        assert limiter.check_and_consume("key2", 5) is True
    
    def test_remaining_tokens(self):
        """Test remaining token calculation."""
        limiter = RateLimiter()
        
        assert limiter.get_remaining("key3", 10) == 10.0
        
        limiter.check_and_consume("key3", 10)
        remaining = limiter.get_remaining("key3", 10)
        assert remaining == 9.0


class TestPolicyEnforcer:
    """Test policy enforcement."""
    
    def test_resolve_tool_policy(self):
        """Test policy resolution for tool."""
        profile = get_profile("minimal")
        enforcer = PolicyEnforcer(profile=profile)
        
        # read should be allowed
        policy = enforcer.resolver.resolve("read")
        assert policy.permission == PermissionLevel.ALLOW
        
        # write should be denied
        policy = enforcer.resolver.resolve("write")
        assert policy.permission == PermissionLevel.DENY
    
    def test_check_permission_allow(self):
        """Test checking allowed permission."""
        profile = get_profile("minimal")
        enforcer = PolicyEnforcer(profile=profile)
        
        policy = enforcer.check_permission("read")
        assert policy.permission == PermissionLevel.ALLOW
    
    def test_check_permission_deny(self):
        """Test checking denied permission."""
        profile = get_profile("minimal")
        enforcer = PolicyEnforcer(profile=profile)
        
        with pytest.raises(PolicyViolation) as exc:
            enforcer.check_permission("exec")
        
        assert "denied" in str(exc.value).lower()
    
    def test_validate_call_allow(self):
        """Test validating allowed call."""
        profile = get_profile("coding")
        enforcer = PolicyEnforcer(profile=profile)
        
        context = ToolCallContext(
            tool_name="read",
            agent_id="test-agent",
            profile_name="coding",
            args={"path": "./workspace/file.txt"},
            kwargs={},
            timestamp=datetime.utcnow()
        )
        
        policy = enforcer.validate_call(context)
        assert policy.permission == PermissionLevel.ALLOW
    
    def test_validate_call_path_denied(self):
        """Test validating call with denied path."""
        profile = get_profile("minimal")
        enforcer = PolicyEnforcer(profile=profile)
        
        context = ToolCallContext(
            tool_name="read",
            agent_id="test-agent",
            profile_name="minimal",
            args={"path": "./secrets/key.txt"},
            kwargs={},
            timestamp=datetime.utcnow()
        )
        
        with pytest.raises(PolicyViolation) as exc:
            enforcer.validate_call(context)
        
        assert "path" in str(exc.value).lower()


class TestAuditLogging:
    """Test audit logging."""
    
    def test_audit_event_creation(self):
        """Test creating audit event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            tool_name="read",
            agent_id="test-agent",
            action="ALLOW",
            details={"path": "./file.txt"}
        )
        
        assert event.tool_name == "read"
        assert event.action == "ALLOW"
        assert "path" in event.details
    
    def test_audit_event_to_json(self):
        """Test JSON serialization."""
        event = AuditEvent(
            timestamp="2024-01-01T00:00:00",
            tool_name="write",
            agent_id="agent-1",
            action="DENY",
            details={"reason": "path denied"}
        )
        
        json_str = event.to_json()
        data = json.loads(json_str)
        
        assert data["tool_name"] == "write"
        assert data["action"] == "DENY"
    
    def test_memory_backend(self):
        """Test in-memory audit backend."""
        backend = MemoryBackend({"max_size": 100})
        
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            tool_name="exec",
            agent_id="test",
            action="ALLOW",
            details={}
        )
        
        backend.write(event)
        
        results = backend.query(limit=10)
        assert len(results) == 1
        assert results[0].tool_name == "exec"
    
    def test_memory_backend_filter(self):
        """Test querying with filters."""
        backend = MemoryBackend({})
        
        backend.write(AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            tool_name="read",
            agent_id="agent-1",
            action="ALLOW",
            details={}
        ))
        
        backend.write(AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            tool_name="write",
            agent_id="agent-2",
            action="DENY",
            details={}
        ))
        
        results = backend.query(agent_id="agent-1")
        assert len(results) == 1
        assert results[0].tool_name == "read"
    
    def test_file_backend(self):
        """Test file-based audit backend."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            backend = FileBackend({
                "path": temp_path,
                "format": "jsonl"
            })
            
            event = AuditEvent(
                timestamp=datetime.utcnow().isoformat(),
                tool_name="delete",
                agent_id="test",
                action="DENY",
                details={}
            )
            
            backend.write(event)
            backend.close()
            
            # Read back
            with open(temp_path, 'r') as f:
                line = f.readline()
                data = json.loads(line)
                assert data["tool_name"] == "delete"
        
        finally:
            os.unlink(temp_path)
    
    def test_sqlite_backend(self):
        """Test SQLite audit backend."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        
        try:
            backend = SQLiteBackend({"path": temp_path})
            
            # Write events
            for i in range(5):
                backend.write(AuditEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    tool_name=f"tool-{i}",
                    agent_id="test",
                    action="ALLOW",
                    details={"index": i}
                ))
            
            # Query
            results = backend.query(limit=3)
            assert len(results) == 3
            
            # Stats
            stats = backend.get_stats(hours=1)
            assert stats["action_counts"]["ALLOW"] == 5
            
            backend.close()
        
        finally:
            os.unlink(temp_path)
    
    def test_audit_formatter(self):
        """Test audit formatters."""
        event = AuditEvent(
            timestamp="2024-01-15T10:30:00",
            tool_name="web_search",
            agent_id="agent-abc123",
            action="ALLOW",
            details={"query": "python"}
        )
        
        # JSONL format
        jsonl = AuditFormatter.jsonl(event)
        assert "web_search" in jsonl
        
        # Human readable
        human = AuditFormatter.human_readable(event)
        assert "web_search" in human
        assert "ALLOW" in human


class TestSandbox:
    """Test sandbox functionality."""
    
    def test_sandbox_config_defaults(self):
        """Test sandbox config defaults."""
        config = SandboxConfig()
        
        assert config.timeout_seconds == 60
        assert config.memory_limit_mb == 512
        assert config.network_access is False
        assert config.max_processes == 10
    
    def test_sandbox_config_from_dict(self):
        """Test creating config from dict."""
        config = SandboxConfig.from_dict({
            "timeout": 120,
            "memory_limit": "1g",
            "network": True
        })
        
        assert config.timeout_seconds == 120
        assert config.memory_limit_mb == "1g"  # Kept as string for parsing
        assert config.network_access is True
    
    def test_sandbox_result(self):
        """Test sandbox result."""
        result = SandboxResult(
            return_code=0,
            stdout="hello",
            stderr="",
            duration_ms=100
        )
        
        assert result.success is True
        assert result.stdout == "hello"
    
    def test_sandbox_result_failure(self):
        """Test failed sandbox result."""
        result = SandboxResult(
            return_code=1,
            stdout="",
            stderr="error",
            duration_ms=50,
            timed_out=False
        )
        
        assert result.success is False
    
    def test_subprocess_sandbox_execute(self):
        """Test subprocess sandbox command execution."""
        config = SandboxConfig(
            timeout_seconds=5,
            memory_limit_mb=128
        )
        
        with SubprocessSandbox(config) as sandbox:
            result = sandbox.execute(["echo", "hello"])
            
            assert result.return_code == 0
            assert "hello" in result.stdout
            assert result.timed_out is False
    
    def test_subprocess_sandbox_timeout(self):
        """Test subprocess sandbox timeout."""
        config = SandboxConfig(timeout_seconds=1)
        
        with SubprocessSandbox(config) as sandbox:
            result = sandbox.execute(["sleep", "5"])
            
            assert result.timed_out is True
    
    def test_sandbox_manager(self):
        """Test sandbox manager."""
        manager = SandboxManager()
        
        config = SandboxConfig(timeout_seconds=5)
        
        with manager.create_session(config, "subprocess") as session:
            result = session.execute(["echo", "test"])
            assert result.return_code == 0
    
    def test_sandbox_manager_quick_execute(self):
        """Test quick execute helper."""
        manager = SandboxManager()
        
        result = manager.quick_execute(
            ["python3", "-c", "print('hello from sandbox')"],
            SandboxConfig(timeout_seconds=5)
        )
        
        assert result.return_code == 0
        assert "hello from sandbox" in result.stdout


class TestIntegration:
    """Integration tests."""
    
    def test_end_to_end_policy_flow(self):
        """Test complete policy enforcement flow."""
        # Setup
        registry = ProfileRegistry()
        profile = registry.get("coding")
        
        enforcer = PolicyEnforcer(profile=profile)
        
        # Test allowed operation
        context = ToolCallContext(
            tool_name="read",
            agent_id="integration-test",
            profile_name="coding",
            args={"path": "./workspace/main.py"},
            kwargs={},
            timestamp=datetime.utcnow()
        )
        
        policy = enforcer.validate_call(context)
        assert policy.permission == PermissionLevel.ALLOW
    
    def test_agent_policy_manager(self):
        """Test agent policy manager."""
        manager = AgentPolicyManager()
        
        # Assign profile
        manager.assign_profile("agent-1", "minimal")
        
        # Check access
        assert manager.check_tool_access("agent-1", "read") is True
        assert manager.check_tool_access("agent-1", "exec") is False
        
        # List accessible tools
        tools = manager.list_accessible_tools("agent-1")
        assert "read" in tools
        assert "exec" not in tools
    
    def test_yaml_serialization(self):
        """Test YAML profile serialization."""
        import tempfile
        import yaml
        
        registry = ProfileRegistry()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save profiles
            registry.save_to_yaml(temp_path)
            
            # Load and verify
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            assert 'profiles' in data
            profile_names = [p['name'] for p in data['profiles']]
            assert 'minimal' in profile_names
            assert 'coding' in profile_names
        
        finally:
            os.unlink(temp_path)


class TestSecurityEdgeCases:
    """Test security edge cases and vulnerabilities."""
    
    def test_path_traversal_attempt(self):
        """Test path traversal protection."""
        # Try to access file outside allowed paths
        allowed = ["./workspace/*"]
        
        assert PathValidator.validate("./workspace/../../etc/passwd", allowed, None) is False
        assert PathValidator.validate("./workspace/..\\..\\windows\\system32", allowed, None) is False
    
    def test_sensitive_data_redaction(self):
        """Test sensitive data is redacted in audit logs."""
        enforcer = PolicyEnforcer(profile_name="minimal")
        
        sanitized = enforcer._sanitize_args({
            "path": "./file.txt",
            "api_key": "secret123",
            "password": "hunter2",
            "nested": {
                "token": "bearer_token"
            }
        })
        
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["nested"]["token"] == "***REDACTED***"
        assert sanitized["path"] == "./file.txt"
    
    def test_rate_limit_burst(self):
        """Test rate limiting under burst conditions."""
        limiter = RateLimiter()
        
        # Exhaust limit
        for i in range(100):
            limiter.check_and_consume("burst-key", 10)
        
        # Should be denied
        assert limiter.check_and_consume("burst-key", 10) is False
    
    def test_sandbox_escape_attempt(self):
        """Test sandbox handles malicious commands."""
        config = SandboxConfig(
            timeout_seconds=2,
            network_access=False,
            max_processes=1
        )
        
        with SubprocessSandbox(config) as sandbox:
            # Try to spawn many processes
            result = sandbox.execute([
                "sh", "-c", 
                "for i in $(seq 1 100); do sleep 1 & done"
            ])
            
            # Should fail due to process limits
            assert not result.success or result.timed_out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
