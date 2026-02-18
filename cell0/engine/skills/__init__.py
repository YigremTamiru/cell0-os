"""
Skill System for Cell 0 OS

A dynamic plugin system for extending Cell 0 OS functionality.

Example usage:
    from cell0.engine.skills import get_manager, SkillStatus
    
    # Get the skill manager
    manager = get_manager()
    
    # List all skills
    skills = manager.list_skills()
    
    # Enable a skill
    await manager.enable_skill("workspace:my_skill")
"""

from .skill_manifest import (
    SkillManifest,
    SkillDependency,
    SkillType,
    SkillStatus,
    ToolRegistration,
    CommandRegistration,
    EventHandler,
    satisfies_version
)

from .skill_loader import SkillLoader, SkillLoadError, initialize_loader, get_loader
from .skill_registry import SkillRegistry, initialize_registry, get_registry
from .skill_manager import SkillManager, SkillManagerError, DependencyError, initialize, get_manager

__all__ = [
    # Manifest
    'SkillManifest',
    'SkillDependency',
    'SkillType',
    'SkillStatus',
    'ToolRegistration',
    'CommandRegistration',
    'EventHandler',
    'satisfies_version',
    
    # Loader
    'SkillLoader',
    'SkillLoadError',
    'initialize_loader',
    'get_loader',
    
    # Registry
    'SkillRegistry',
    'initialize_registry',
    'get_registry',
    
    # Manager
    'SkillManager',
    'SkillManagerError',
    'DependencyError',
    'initialize',
    'get_manager',
]
