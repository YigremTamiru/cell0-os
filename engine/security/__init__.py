"""
Cell 0 OS Security Module

Tool security, profiles, sandboxing, and audit logging.
"""
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
    RateLimitExceeded,
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
    'RateLimitExceeded',
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
]
