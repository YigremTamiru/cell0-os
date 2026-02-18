"""
Tool Profiles for Cell 0 OS

Defines security profiles that control which tools agents can use.
Similar to OpenClaw's tool profiles.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum, auto
import yaml
import os


class PermissionLevel(Enum):
    """Permission levels for tool access."""
    DENY = auto()      # Tool is explicitly denied
    ALLOW = auto()     # Tool is allowed
    SANDBOX = auto()   # Tool runs in sandbox
    ELEVATED = auto()  # Requires elevated approval


class RiskLevel(Enum):
    """Risk classification for tools."""
    LOW = "low"           # Read-only, safe operations
    MEDIUM = "medium"     # File writes, local execution
    HIGH = "high"         # Network access, system changes
    CRITICAL = "critical" # Destructive operations, privilege escalation


@dataclass
class ToolPolicy:
    """Policy for a specific tool or tool group."""
    permission: PermissionLevel = PermissionLevel.DENY
    risk_level: RiskLevel = RiskLevel.MEDIUM
    allowed_paths: Optional[List[str]] = None
    denied_paths: Optional[List[str]] = None
    rate_limit: Optional[int] = None  # calls per minute
    requires_approval_above: Optional[int] = None  # file size, timeout, etc.
    sandbox_config: Optional[Dict[str, Any]] = None


@dataclass
class ToolProfile:
    """Complete tool profile defining agent capabilities."""
    name: str
    description: str
    
    # Tool-specific policies (overrides group policies)
    tool_policies: Dict[str, ToolPolicy] = field(default_factory=dict)
    
    # Group policies (e.g., group:fs, group:network)
    group_policies: Dict[str, ToolPolicy] = field(default_factory=dict)
    
    # Provider-specific policies (e.g., provider:filesystem)
    provider_policies: Dict[str, ToolPolicy] = field(default_factory=dict)
    
    # Global defaults
    default_policy: ToolPolicy = field(default_factory=lambda: ToolPolicy(
        permission=PermissionLevel.DENY
    ))
    
    # Inherited profile (for profile composition)
    inherits: Optional[str] = None
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: str = "1.0.0"


class ToolGroup:
    """Predefined tool groups for easier policy management."""
    
    FILESYSTEM = "group:fs"
    RUNTIME = "group:runtime"
    NETWORK = "group:network"
    BROWSER = "group:browser"
    MESSAGING = "group:messaging"
    SYSTEM = "group:system"
    CODE = "group:code"
    DATA = "group:data"
    EXTERNAL = "group:external"
    
    # Tool to group mappings
    GROUP_MEMBERS: Dict[str, List[str]] = {
        FILESYSTEM: [
            "read", "write", "edit", "delete", "copy", "move",
            "list_dir", "file_info", "watch_file"
        ],
        RUNTIME: [
            "exec", "process", "spawn", "kill", "signal"
        ],
        NETWORK: [
            "web_search", "web_fetch", "http_request", "download"
        ],
        BROWSER: [
            "browser_navigate", "browser_click", "browser_type",
            "browser_screenshot", "browser_evaluate"
        ],
        MESSAGING: [
            "message_send", "message_broadcast", "message_react",
            "email_send", "notify"
        ],
        SYSTEM: [
            "system_info", "env_get", "env_set", "config_read", "config_write"
        ],
        CODE: [
            "code_complete", "code_analyze", "code_lint", "code_format"
        ],
        DATA: [
            "db_query", "cache_get", "cache_set", "kv_get", "kv_set"
        ],
        EXTERNAL: [
            "api_call", "webhook_trigger", "integration_invoke"
        ]
    }
    
    @classmethod
    def get_members(cls, group: str) -> List[str]:
        """Get all tools in a group."""
        return cls.GROUP_MEMBERS.get(group, [])
    
    @classmethod
    def get_groups_for_tool(cls, tool_name: str) -> List[str]:
        """Get all groups a tool belongs to."""
        groups = []
        for group, members in cls.GROUP_MEMBERS.items():
            if tool_name in members:
                groups.append(group)
        return groups


class ProfileRegistry:
    """Registry for managing tool profiles."""
    
    def __init__(self):
        self._profiles: Dict[str, ToolProfile] = {}
        self._load_builtin_profiles()
    
    def _load_builtin_profiles(self):
        """Load built-in security profiles."""
        
        # Minimal profile - read-only, no external access
        self._profiles["minimal"] = ToolProfile(
            name="minimal",
            description="Read-only access to files. No network, no execution.",
            group_policies={
                ToolGroup.FILESYSTEM: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.LOW,
                    allowed_paths=["./workspace/*"],
                    denied_paths=["*/.*", "*/secrets/*", "*/.env*"]
                ),
                ToolGroup.SYSTEM: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.LOW
                )
            },
            tool_policies={
                "read": ToolPolicy(permission=PermissionLevel.ALLOW),
                "write": ToolPolicy(permission=PermissionLevel.DENY),
                "edit": ToolPolicy(permission=PermissionLevel.DENY),
                "exec": ToolPolicy(permission=PermissionLevel.DENY),
                "web_search": ToolPolicy(permission=PermissionLevel.DENY),
                "browser_navigate": ToolPolicy(permission=PermissionLevel.DENY),
                "message_send": ToolPolicy(permission=PermissionLevel.DENY),
            }
        )
        
        # Coding profile - file operations and local execution
        self._profiles["coding"] = ToolProfile(
            name="coding",
            description="Standard development tasks. File operations, local execution, web search.",
            inherits="minimal",
            group_policies={
                ToolGroup.FILESYSTEM: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    allowed_paths=["./workspace/*", "./src/*", "./tests/*"],
                ),
                ToolGroup.RUNTIME: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    sandbox_config={"timeout": 300, "memory_limit": "512m"}
                ),
                ToolGroup.NETWORK: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    rate_limit=60
                ),
                ToolGroup.CODE: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.LOW
                )
            },
            tool_policies={
                "exec": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    sandbox_config={"timeout": 60, "network": False}
                ),
                "web_search": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    rate_limit=30
                ),
                "web_fetch": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    rate_limit=60
                ),
            }
        )
        
        # Messaging profile - communication capabilities
        self._profiles["messaging"] = ToolProfile(
            name="messaging",
            description="Communication with external channels. Email, chat, notifications.",
            inherits="coding",
            group_policies={
                ToolGroup.MESSAGING: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.HIGH,
                    requires_approval_above=10  # >10 recipients needs approval
                ),
                ToolGroup.BROWSER: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM
                )
            },
            tool_policies={
                "message_send": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.HIGH,
                    rate_limit=10
                ),
                "email_send": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.HIGH,
                    requires_approval_above=1  # External emails need approval
                ),
                "browser_navigate": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM
                ),
            }
        )
        
        # Full profile - elevated access with sandboxing for risky operations
        self._profiles["full"] = ToolProfile(
            name="full",
            description="Full access with sandboxing for high-risk operations.",
            inherits="messaging",
            group_policies={
                ToolGroup.SYSTEM: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.HIGH
                ),
                ToolGroup.EXTERNAL: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.HIGH,
                    sandbox_config={"timeout": 60}
                ),
                ToolGroup.DATA: ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM
                )
            },
            tool_policies={
                "exec": ToolPolicy(
                    permission=PermissionLevel.SANDBOX,
                    risk_level=RiskLevel.HIGH,
                    sandbox_config={
                        "timeout": 300,
                        "network": True,
                        "memory_limit": "1g",
                        "cpu_limit": "1.0"
                    }
                ),
                "write": ToolPolicy(
                    permission=PermissionLevel.ALLOW,
                    risk_level=RiskLevel.MEDIUM,
                    denied_paths=["*/system/*", "*/boot/*", "/etc/*"]
                ),
                "delete": ToolPolicy(
                    permission=PermissionLevel.ELEVATED,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval_above=0
                ),
                "process_kill": ToolPolicy(
                    permission=PermissionLevel.ELEVATED,
                    risk_level=RiskLevel.HIGH
                ),
            }
        )
    
    def register(self, profile: ToolProfile) -> None:
        """Register a new profile."""
        self._profiles[profile.name] = profile
    
    def get(self, name: str) -> Optional[ToolProfile]:
        """Get a profile by name."""
        return self._profiles.get(name)
    
    def list_profiles(self) -> List[str]:
        """List all available profile names."""
        return list(self._profiles.keys())
    
    def load_from_yaml(self, path: str) -> None:
        """Load profiles from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        for profile_data in data.get('profiles', []):
            profile = self._deserialize_profile(profile_data)
            self.register(profile)
    
    def save_to_yaml(self, path: str) -> None:
        """Save all profiles to YAML file."""
        data = {'profiles': []}
        for profile in self._profiles.values():
            data['profiles'].append(self._serialize_profile(profile))
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def _deserialize_profile(self, data: Dict) -> ToolProfile:
        """Deserialize profile from dict."""
        def deserialize_policy(p):
            return ToolPolicy(
                permission=PermissionLevel[p.get('permission', 'DENY').upper()],
                risk_level=RiskLevel[p.get('risk_level', 'MEDIUM').lower()],
                allowed_paths=p.get('allowed_paths'),
                denied_paths=p.get('denied_paths'),
                rate_limit=p.get('rate_limit'),
                requires_approval_above=p.get('requires_approval_above'),
                sandbox_config=p.get('sandbox_config')
            )
        
        return ToolProfile(
            name=data['name'],
            description=data.get('description', ''),
            inherits=data.get('inherits'),
            tool_policies={
                k: deserialize_policy(v) 
                for k, v in data.get('tool_policies', {}).items()
            },
            group_policies={
                k: deserialize_policy(v) 
                for k, v in data.get('group_policies', {}).items()
            },
            provider_policies={
                k: deserialize_policy(v) 
                for k, v in data.get('provider_policies', {}).items()
            },
            version=data.get('version', '1.0.0')
        )
    
    def _serialize_profile(self, profile: ToolProfile) -> Dict:
        """Serialize profile to dict."""
        def serialize_policy(p: ToolPolicy):
            d = {
                'permission': p.permission.name,
                'risk_level': p.risk_level.value
            }
            if p.allowed_paths:
                d['allowed_paths'] = p.allowed_paths
            if p.denied_paths:
                d['denied_paths'] = p.denied_paths
            if p.rate_limit:
                d['rate_limit'] = p.rate_limit
            if p.requires_approval_above is not None:
                d['requires_approval_above'] = p.requires_approval_above
            if p.sandbox_config:
                d['sandbox_config'] = p.sandbox_config
            return d
        
        data = {
            'name': profile.name,
            'description': profile.description,
            'version': profile.version
        }
        
        if profile.inherits:
            data['inherits'] = profile.inherits
        if profile.tool_policies:
            data['tool_policies'] = {
                k: serialize_policy(v) for k, v in profile.tool_policies.items()
            }
        if profile.group_policies:
            data['group_policies'] = {
                k: serialize_policy(v) for k, v in profile.group_policies.items()
            }
        if profile.provider_policies:
            data['provider_policies'] = {
                k: serialize_policy(v) for k, v in profile.provider_policies.items()
            }
        
        return data


# Global registry instance
_registry: Optional[ProfileRegistry] = None


def get_registry() -> ProfileRegistry:
    """Get the global profile registry."""
    global _registry
    if _registry is None:
        _registry = ProfileRegistry()
    return _registry


def get_profile(name: str) -> Optional[ToolProfile]:
    """Get a profile by name."""
    return get_registry().get(name)
