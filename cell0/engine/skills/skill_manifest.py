"""
Skill Manifest Module for Cell 0 OS

Parses and validates skill.yaml manifest files for the skill system.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import logging

import yaml

logger = logging.getLogger(__name__)


class SkillType(Enum):
    """Skill type enumeration"""
    SYSTEM = "system"      # System-level skills shipped with Cell 0 OS
    WORKSPACE = "workspace"  # User workspace skills
    INSTALLED = "installed"  # Third-party installed skills


class SkillStatus(Enum):
    """Skill lifecycle status"""
    DISCOVERED = "discovered"    # Found on filesystem but not loaded
    LOADED = "loaded"            # Loaded into memory
    ENABLED = "enabled"          # Active and functional
    DISABLED = "disabled"        # Loaded but inactive
    ERROR = "error"              # Error state
    UNLOADED = "unloaded"        # Removed from memory


@dataclass
class SkillDependency:
    """Skill dependency specification"""
    skill_id: str
    version_range: str = "*"  # Semver range (e.g., ">=1.0.0", "^2.0.0")
    optional: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "SkillDependency":
        """Parse dependency from dict (supports simple string or complex object)"""
        if isinstance(data, str):
            # Simple format: "skill_id" or "skill_id>=1.0.0"
            parts = data.split(">=")
            if len(parts) == 2:
                return cls(skill_id=parts[0].strip(), version_range=f">={parts[1].strip()}")
            return cls(skill_id=data)
        
        return cls(
            skill_id=data.get("id", ""),
            version_range=data.get("version", "*"),
            optional=data.get("optional", False)
        )


@dataclass
class ToolRegistration:
    """Tool registration specification"""
    name: str
    module: str
    function: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass
class CommandRegistration:
    """CLI command registration specification"""
    name: str
    module: str
    function: str
    description: str
    aliases: list[str] = field(default_factory=list)
    arguments: list[dict] = field(default_factory=list)


@dataclass
class EventHandler:
    """Event handler registration"""
    event_type: str
    module: str
    function: str
    priority: int = 100  # Lower = higher priority


@dataclass
class SkillManifest:
    """
    Skill manifest - defines a skill's metadata, dependencies, and registrations
    
    Example skill.yaml:
        id: my_skill
        name: My Skill
        version: 1.0.0
        description: A sample skill
        author: Cell 0 Team
        type: workspace
        
        dependencies:
          - core_utils
          - database>=2.0.0
        
        tools:
          - name: my_tool
            module: my_skill.tools
            function: execute
            description: Does something useful
        
        commands:
          - name: my-cmd
            module: my_skill.cli
            function: run
            description: My CLI command
        
        events:
          - event_type: skill.loaded
            module: my_skill.handlers
            function: on_skill_loaded
    """
    # Required fields
    skill_id: str
    name: str
    version: str
    
    # Optional metadata
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    
    # Skill type
    skill_type: SkillType = SkillType.WORKSPACE
    
    # Dependencies
    dependencies: list[SkillDependency] = field(default_factory=list)
    
    # Registrations
    tools: list[ToolRegistration] = field(default_factory=list)
    commands: list[CommandRegistration] = field(default_factory=list)
    events: list[EventHandler] = field(default_factory=list)
    
    # Paths (set by loader)
    path: Optional[Path] = None
    entry_point: Optional[str] = None
    
    @property
    def full_id(self) -> str:
        """Get fully qualified skill ID"""
        prefix = self.skill_type.value
        return f"{prefix}:{self.skill_id}"
    
    @classmethod
    def from_yaml(cls, path: Path) -> "SkillManifest":
        """Load manifest from YAML file"""
        logger.debug(f"Loading skill manifest from {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError(f"Empty or invalid YAML file: {path}")
        
        # Parse dependencies
        deps = []
        for dep_data in data.get('dependencies', []):
            deps.append(SkillDependency.from_dict(dep_data))
        
        # Parse tools
        tools = []
        for tool_data in data.get('tools', []):
            tools.append(ToolRegistration(
                name=tool_data['name'],
                module=tool_data['module'],
                function=tool_data['function'],
                description=tool_data.get('description', ''),
                parameters=tool_data.get('parameters', {})
            ))
        
        # Parse commands
        commands = []
        for cmd_data in data.get('commands', []):
            commands.append(CommandRegistration(
                name=cmd_data['name'],
                module=cmd_data['module'],
                function=cmd_data['function'],
                description=cmd_data.get('description', ''),
                aliases=cmd_data.get('aliases', []),
                arguments=cmd_data.get('arguments', [])
            ))
        
        # Parse events
        events = []
        for evt_data in data.get('events', []):
            events.append(EventHandler(
                event_type=evt_data['event_type'],
                module=evt_data['module'],
                function=evt_data['function'],
                priority=evt_data.get('priority', 100)
            ))
        
        # Determine skill type
        type_str = data.get('type', 'workspace')
        skill_type = SkillType(type_str) if type_str in [t.value for t in SkillType] else SkillType.WORKSPACE
        
        manifest = cls(
            skill_id=data['id'],
            name=data['name'],
            version=data['version'],
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', 'MIT'),
            homepage=data.get('homepage', ''),
            repository=data.get('repository', ''),
            skill_type=skill_type,
            dependencies=deps,
            tools=tools,
            commands=commands,
            events=events,
            path=path.parent,
            entry_point=data.get('entry_point', '__init__.py')
        )
        
        logger.debug(f"Loaded manifest for skill: {manifest.full_id}")
        return manifest
    
    def to_dict(self) -> dict:
        """Convert manifest to dictionary"""
        return {
            'id': self.skill_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'type': self.skill_type.value,
            'dependencies': [
                {'id': d.skill_id, 'version': d.version_range, 'optional': d.optional}
                for d in self.dependencies
            ],
            'tools': [
                {
                    'name': t.name,
                    'module': t.module,
                    'function': t.function,
                    'description': t.description
                }
                for t in self.tools
            ],
            'commands': [
                {
                    'name': c.name,
                    'module': c.module,
                    'function': c.function,
                    'description': c.description,
                    'aliases': c.aliases
                }
                for c in self.commands
            ],
            'events': [
                {
                    'event_type': e.event_type,
                    'module': e.module,
                    'function': e.function,
                    'priority': e.priority
                }
                for e in self.events
            ]
        }
    
    def validate(self) -> list[str]:
        """Validate manifest and return list of errors"""
        errors = []
        
        if not self.skill_id:
            errors.append("Skill ID is required")
        elif not self.skill_id.replace('_', '').replace('-', '').isalnum():
            errors.append("Skill ID must be alphanumeric with underscores/hyphens only")
        
        if not self.name:
            errors.append("Skill name is required")
        
        if not self.version:
            errors.append("Skill version is required")
        
        # Validate semantic version format (basic check)
        version_parts = self.version.split('.')
        if len(version_parts) < 2:
            errors.append("Version should follow semantic versioning (e.g., 1.0.0)")
        
        # Validate tool registrations
        for tool in self.tools:
            if not tool.name or not tool.module or not tool.function:
                errors.append(f"Tool '{tool.name}' has incomplete registration")
        
        # Validate command registrations
        for cmd in self.commands:
            if not cmd.name or not cmd.module or not cmd.function:
                errors.append(f"Command '{cmd.name}' has incomplete registration")
        
        return errors


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison"""
    parts = version_str.split('.')
    result = []
    for part in parts:
        # Extract numeric portion
        num = ''.join(c for c in part if c.isdigit())
        result.append(int(num) if num else 0)
    return tuple(result)


def satisfies_version(version: str, version_range: str) -> bool:
    """
    Check if version satisfies the version range.
    
    Supports:
    - * (any version)
    - >=1.0.0 (greater than or equal)
    - >1.0.0 (greater than)
    - <=1.0.0 (less than or equal)
    - <1.0.0 (less than)
    - ^1.0.0 (compatible - same major version)
    - ~1.0.0 (approximately - same major.minor)
    - 1.0.0 (exact match)
    """
    if version_range == '*' or version_range == '':
        return True
    
    v = parse_version(version)
    
    if version_range.startswith('>='):
        target = parse_version(version_range[2:])
        return v >= target
    elif version_range.startswith('>'):
        target = parse_version(version_range[1:])
        return v > target
    elif version_range.startswith('<='):
        target = parse_version(version_range[2:])
        return v <= target
    elif version_range.startswith('<'):
        target = parse_version(version_range[1:])
        return v < target
    elif version_range.startswith('^'):
        target = parse_version(version_range[1:])
        return v[0] == target[0] and v >= target
    elif version_range.startswith('~'):
        target = parse_version(version_range[1:])
        return len(v) >= 2 and len(target) >= 2 and v[0] == target[0] and v[1] == target[1] and v >= target
    else:
        # Exact match
        return parse_version(version_range) == v
