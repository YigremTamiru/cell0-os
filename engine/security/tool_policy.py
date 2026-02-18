"""
Tool Policy Enforcement for Cell 0 OS

Enforces security policies on tool invocations.
Integrates with tool profiles, audit logging, and sandboxing.
"""
import re
import fnmatch
import os
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
import threading
import time

from .tool_profiles import (
    ToolProfile, ToolPolicy, PermissionLevel, RiskLevel,
    ToolGroup, ProfileRegistry, get_profile, get_registry
)
from .tool_audit import ToolAuditor, AuditEvent
from .sandbox import SandboxManager, SandboxConfig


class PolicyViolation(Exception):
    """Raised when a tool invocation violates security policy."""
    
    def __init__(self, tool: str, reason: str, policy: Optional[ToolPolicy] = None):
        self.tool = tool
        self.reason = reason
        self.policy = policy
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(f"Policy violation for '{tool}': {reason}")


class RateLimitExceeded(PolicyViolation):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, tool: str, limit: int, window_seconds: int = 60):
        super().__init__(tool, f"Rate limit exceeded: {limit} calls per {window_seconds}s")
        self.limit = limit
        self.window_seconds = window_seconds


@dataclass
class ToolCallContext:
    """Context for a tool invocation."""
    tool_name: str
    agent_id: str
    profile_name: str
    args: Dict[str, Any]
    kwargs: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None


class RateLimiter:
    """Token bucket rate limiter for tool calls."""
    
    def __init__(self):
        self._buckets: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def check_and_consume(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """
        Check if call is allowed and consume token.
        Returns True if allowed, False if rate limited.
        """
        now = time.time()
        
        with self._lock:
            bucket = self._buckets.get(key)
            
            if bucket is None:
                # New bucket
                self._buckets[key] = {
                    'tokens': limit - 1,
                    'last_update': now
                }
                return True
            
            # Add tokens based on time passed
            elapsed = now - bucket['last_update']
            tokens_to_add = elapsed * (limit / window_seconds)
            bucket['tokens'] = min(limit, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = now
            
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            
            return False
    
    def get_remaining(self, key: str, limit: int) -> float:
        """Get remaining tokens in bucket."""
        bucket = self._buckets.get(key)
        if bucket is None:
            return float(limit)
        return bucket['tokens']
    
    def reset(self, key: Optional[str] = None):
        """Reset rate limiter for a key or all keys."""
        with self._lock:
            if key:
                self._buckets.pop(key, None)
            else:
                self._buckets.clear()


class PolicyResolver:
    """Resolves effective policy for a tool call."""
    
    def __init__(self, profile: ToolProfile):
        self.profile = profile
        self._resolved_policies: Dict[str, ToolPolicy] = {}
    
    def resolve(self, tool_name: str) -> ToolPolicy:
        """Resolve effective policy for a tool."""
        if tool_name in self._resolved_policies:
            return self._resolved_policies[tool_name]
        
        # 1. Check direct tool policy
        if tool_name in self.profile.tool_policies:
            policy = self.profile.tool_policies[tool_name]
            self._resolved_policies[tool_name] = policy
            return policy
        
        # 2. Check provider-specific policy
        provider = self._get_tool_provider(tool_name)
        if provider and f"provider:{provider}" in self.profile.provider_policies:
            policy = self.profile.provider_policies[f"provider:{provider}"]
            self._resolved_policies[tool_name] = policy
            return policy
        
        # 3. Check group policies
        groups = ToolGroup.get_groups_for_tool(tool_name)
        for group in groups:
            if group in self.profile.group_policies:
                policy = self.profile.group_policies[group]
                self._resolved_policies[tool_name] = policy
                return policy
        
        # 4. Fall back to default
        self._resolved_policies[tool_name] = self.profile.default_policy
        return self.profile.default_policy
    
    def _get_tool_provider(self, tool_name: str) -> Optional[str]:
        """Determine provider for a tool."""
        # Map tools to providers
        provider_map = {
            'read': 'filesystem',
            'write': 'filesystem',
            'edit': 'filesystem',
            'exec': 'runtime',
            'process': 'runtime',
            'web_search': 'network',
            'web_fetch': 'network',
            'browser_navigate': 'browser',
            'message_send': 'messaging',
            'db_query': 'database',
        }
        return provider_map.get(tool_name)


class PathValidator:
    """Validates file paths against allow/deny patterns."""
    
    @staticmethod
    def validate(path: str, allowed_patterns: Optional[List[str]], 
                 denied_patterns: Optional[List[str]]) -> bool:
        """
        Validate a path against allow/deny patterns.
        Returns True if allowed, False if denied.
        """
        # Normalize path (keep leading ./ if present)
        original_path = path
        path = os.path.normpath(path)
        
        # Also check with original for relative path patterns
        paths_to_check = [path, original_path]
        
        # Check denied patterns first
        if denied_patterns:
            for pattern in denied_patterns:
                for p in paths_to_check:
                    if PathValidator._match_pattern(p, pattern):
                        return False
        
        # Check allowed patterns
        if allowed_patterns:
            for pattern in allowed_patterns:
                for p in paths_to_check:
                    if PathValidator._match_pattern(p, pattern):
                        return True
            # Not in any allowed pattern
            return False
        
        # No restrictions
        return True
    
    @staticmethod
    def _match_pattern(path: str, pattern: str) -> bool:
        """Match path against glob pattern."""
        # Normalize pattern too
        pattern = os.path.normpath(pattern)
        
        # Handle ** wildcards (matches any depth)
        if '**' in pattern:
            regex = pattern
            # Escape regex special chars except our wildcards
            for char in '.+(){}[]^$|':
                regex = regex.replace(char, f'\\{char}')
            regex = regex.replace('**', '<<DOUBLESTAR>>')
            regex = regex.replace('*', '[^/]*')
            regex = regex.replace('?', '.')
            regex = regex.replace('<<DOUBLESTAR>>', '.*')
            return bool(re.match(f'^{regex}$', path)) or bool(re.match(f'^{regex}', path + '/'))
        
        # Standard glob matching - also check if path is under the pattern directory
        if fnmatch.fnmatch(path, pattern):
            return True
        
        # Check if path is within a directory that matches the pattern
        # Pattern like "./workspace/*" should match "./workspace/subdir/file.txt"
        if pattern.endswith('/*'):
            dir_pattern = pattern[:-2]
            if path.startswith(dir_pattern + os.sep) or path.startswith(dir_pattern + '/'):
                return True
        
        # Check if pattern is a directory prefix
        if not pattern.endswith('*'):
            if path.startswith(pattern + os.sep) or path.startswith(pattern + '/'):
                return True
        
        return False


class PolicyEnforcer:
    """
    Main policy enforcement engine.
    Validates tool calls against profiles and manages sandboxing.
    """
    
    def __init__(self, 
                 profile: Optional[ToolProfile] = None,
                 profile_name: Optional[str] = None,
                 auditor: Optional[ToolAuditor] = None,
                 sandbox_manager: Optional[SandboxManager] = None):
        """
        Initialize enforcer.
        
        Args:
            profile: Tool profile to enforce (or load by name)
            profile_name: Name of profile to load
            auditor: Audit logger (creates default if None)
            sandbox_manager: Sandbox manager (creates default if None)
        """
        if profile:
            self.profile = profile
        elif profile_name:
            self.profile = get_profile(profile_name)
            if not self.profile:
                raise ValueError(f"Profile not found: {profile_name}")
        else:
            # Default to minimal
            self.profile = get_profile("minimal")
        
        self.resolver = PolicyResolver(self.profile)
        self.rate_limiter = RateLimiter()
        self.auditor = auditor or ToolAuditor()
        self.sandbox = sandbox_manager or SandboxManager()
        
        # Approval callbacks for elevated operations
        self._approval_callbacks: List[Callable[[ToolCallContext, ToolPolicy], bool]] = []
    
    def register_approval_callback(self, callback: Callable[[ToolCallContext, ToolPolicy], bool]):
        """Register a callback for elevated permission approval."""
        self._approval_callbacks.append(callback)
    
    def check_permission(self, tool_name: str) -> ToolPolicy:
        """
        Check if tool is allowed without invoking it.
        Returns the effective policy.
        """
        policy = self.resolver.resolve(tool_name)
        
        if policy.permission == PermissionLevel.DENY:
            raise PolicyViolation(tool_name, "Tool is denied by policy")
        
        return policy
    
    def validate_call(self, context: ToolCallContext) -> ToolPolicy:
        """
        Validate a tool call against all policies.
        Returns the effective policy if valid.
        Raises PolicyViolation if not allowed.
        """
        tool_name = context.tool_name
        policy = self.resolver.resolve(tool_name)
        
        # 1. Check basic permission
        if policy.permission == PermissionLevel.DENY:
            self._audit_deny(context, policy, "Tool denied by policy")
            raise PolicyViolation(tool_name, "Tool is denied by policy", policy)
        
        # 2. Check path restrictions for file operations
        if 'path' in context.args or 'file_path' in context.args:
            path = context.args.get('path') or context.args.get('file_path')
            
            # Combine paths from tool policy and relevant group policies
            allowed_paths = list(policy.allowed_paths or [])
            denied_paths = list(policy.denied_paths or [])
            
            # Add group-level path restrictions
            groups = ToolGroup.get_groups_for_tool(tool_name)
            for group in groups:
                if group in self.profile.group_policies:
                    group_policy = self.profile.group_policies[group]
                    if group_policy.allowed_paths:
                        allowed_paths.extend(group_policy.allowed_paths)
                    if group_policy.denied_paths:
                        denied_paths.extend(group_policy.denied_paths)
            
            if path and not PathValidator.validate(
                path, 
                allowed_paths if allowed_paths else None, 
                denied_paths if denied_paths else None
            ):
                self._audit_deny(context, policy, f"Path denied: {path}")
                raise PolicyViolation(tool_name, f"Path not allowed: {path}", policy)
        
        # 3. Check rate limits
        if policy.rate_limit:
            rate_key = f"{context.agent_id}:{tool_name}"
            if not self.rate_limiter.check_and_consume(
                rate_key, 
                policy.rate_limit,
                window_seconds=60
            ):
                self._audit_deny(context, policy, "Rate limit exceeded")
                raise RateLimitExceeded(tool_name, policy.rate_limit)
        
        # 4. Check elevated approval
        if policy.permission == PermissionLevel.ELEVATED:
            if not self._request_approval(context, policy):
                self._audit_deny(context, policy, "Elevated approval denied")
                raise PolicyViolation(tool_name, "Elevated approval required and denied", policy)
        
        # Audit allow
        self.auditor.log_event(AuditEvent(
            timestamp=context.timestamp.isoformat(),
            tool_name=tool_name,
            agent_id=context.agent_id,
            action="ALLOW",
            details={
                'profile': self.profile.name,
                'permission': policy.permission.name,
                'risk_level': policy.risk_level.value,
                'args': self._sanitize_args(context.args)
            }
        ))
        
        return policy
    
    def should_sandbox(self, tool_name: str) -> bool:
        """Check if tool should run in sandbox."""
        policy = self.resolver.resolve(tool_name)
        return policy.permission == PermissionLevel.SANDBOX
    
    def get_sandbox_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get sandbox configuration for a tool."""
        policy = self.resolver.resolve(tool_name)
        return policy.sandbox_config
    
    def _request_approval(self, context: ToolCallContext, policy: ToolPolicy) -> bool:
        """Request approval for elevated operation."""
        for callback in self._approval_callbacks:
            if not callback(context, policy):
                return False
        
        # If no callbacks, default to deny for safety
        if not self._approval_callbacks:
            return False
        
        return True
    
    def _audit_deny(self, context: ToolCallContext, policy: ToolPolicy, reason: str):
        """Log denied tool call."""
        self.auditor.log_event(AuditEvent(
            timestamp=context.timestamp.isoformat(),
            tool_name=context.tool_name,
            agent_id=context.agent_id,
            action="DENY",
            details={
                'profile': self.profile.name,
                'reason': reason,
                'policy_permission': policy.permission.name if policy else None
            }
        ))
    
    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from args for audit logging."""
        sensitive_keys = {'password', 'token', 'secret', 'key', 'api_key', 'credential'}
        sanitized = {}
        
        for k, v in args.items():
            if any(sk in k.lower() for sk in sensitive_keys):
                sanitized[k] = '***REDACTED***'
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_args(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    self._sanitize_args(item) if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                sanitized[k] = v
        
        return sanitized


def enforce_tool_call(profile_name: Optional[str] = None,
                      profile: Optional[ToolProfile] = None):
    """
    Decorator to enforce policy on a tool function.
    
    Usage:
        @enforce_tool_call(profile_name="coding")
        def my_tool(arg1, arg2):
            ...
    """
    enforcer = PolicyEnforcer(profile=profile, profile_name=profile_name)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build context
            context = ToolCallContext(
                tool_name=func.__name__,
                agent_id=kwargs.get('_agent_id', 'unknown'),
                profile_name=enforcer.profile.name,
                args={'args': args, **kwargs},
                kwargs=kwargs,
                timestamp=datetime.utcnow()
            )
            
            # Validate
            policy = enforcer.validate_call(context)
            
            # Execute (with sandbox if needed)
            if enforcer.should_sandbox(func.__name__):
                config = enforcer.get_sandbox_config(func.__name__)
                with enforcer.sandbox.create_session(config) as session:
                    return session.run(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class AgentPolicyManager:
    """Manages per-agent tool policies."""
    
    def __init__(self):
        self._agent_profiles: Dict[str, str] = {}
        self._enforcers: Dict[str, PolicyEnforcer] = {}
    
    def assign_profile(self, agent_id: str, profile_name: str):
        """Assign a profile to an agent."""
        self._agent_profiles[agent_id] = profile_name
        # Clear cached enforcer
        self._enforcers.pop(agent_id, None)
    
    def get_enforcer(self, agent_id: str) -> PolicyEnforcer:
        """Get or create policy enforcer for an agent."""
        if agent_id in self._enforcers:
            return self._enforcers[agent_id]
        
        profile_name = self._agent_profiles.get(agent_id, "minimal")
        enforcer = PolicyEnforcer(profile_name=profile_name)
        self._enforcers[agent_id] = enforcer
        return enforcer
    
    def check_tool_access(self, agent_id: str, tool_name: str) -> bool:
        """Check if agent can access a tool."""
        try:
            enforcer = self.get_enforcer(agent_id)
            enforcer.check_permission(tool_name)
            return True
        except PolicyViolation:
            return False
    
    def list_accessible_tools(self, agent_id: str) -> List[str]:
        """List all tools an agent can access."""
        enforcer = self.get_enforcer(agent_id)
        accessible = []
        
        # Get all known tools from registry
        registry = get_registry()
        
        # Check common tools
        all_tools = set()
        for group_tools in ToolGroup.GROUP_MEMBERS.values():
            all_tools.update(group_tools)
        
        for tool in all_tools:
            policy = enforcer.resolver.resolve(tool)
            if policy.permission != PermissionLevel.DENY:
                accessible.append(tool)
        
        return accessible


# Global manager instance
_policy_manager: Optional[AgentPolicyManager] = None


def get_policy_manager() -> AgentPolicyManager:
    """Get global policy manager."""
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = AgentPolicyManager()
    return _policy_manager
