"""
Skill Manager Module for Cell 0 OS

Central orchestrator for the skill system. Manages skill lifecycle,
dependencies, and coordinates between loader and registry.
"""

import asyncio
import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from .skill_manifest import SkillManifest, SkillStatus, SkillType, satisfies_version
from .skill_loader import SkillLoader, initialize_loader
from .skill_registry import SkillRegistry, initialize_registry

logger = logging.getLogger(__name__)


class SkillManagerError(Exception):
    """Exception raised for skill management errors"""
    pass


class DependencyError(SkillManagerError):
    """Exception raised for dependency-related errors"""
    pass


class SkillManager:
    """
    Central manager for the Cell 0 OS skill system.
    
    Responsibilities:
    - Initialize and configure the skill system
    - Discover and load skills
    - Manage skill lifecycle (load, enable, disable, unload)
    - Resolve and validate dependencies
    - Emit lifecycle events
    
    Example usage:
        manager = SkillManager(
            system_path=Path("/opt/cell0/skills/system"),
            workspace_path=Path("~/.cell0/skills"),
            installed_path=Path("/opt/cell0/skills/installed")
        )
        await manager.initialize()
        await manager.enable_skill("workspace:my_skill")
    """
    
    def __init__(
        self,
        system_path: Path,
        workspace_path: Path,
        installed_path: Path,
        auto_discover: bool = True
    ):
        self.system_path = Path(system_path)
        self.workspace_path = Path(workspace_path)
        self.installed_path = Path(installed_path)
        self.auto_discover = auto_discover
        
        # Initialize loader and registry
        self._loader = initialize_loader(system_path, workspace_path, installed_path)
        self._registry = initialize_registry()
        
        # Event bus for skill lifecycle events
        self._event_handlers: dict[str, list[Callable]] = {}
        
        logger.info("SkillManager initialized")
    
    async def initialize(self):
        """Initialize the skill system and discover skills"""
        logger.info("Initializing skill system...")
        
        if self.auto_discover:
            await self.discover_all()
        
        await self.emit_event("skill_system.initialized", {
            "system_path": str(self.system_path),
            "workspace_path": str(self.workspace_path),
            "installed_path": str(self.installed_path),
            "skills_discovered": len(self._registry.list_skills())
        })
        
        logger.info("Skill system initialized")
    
    async def shutdown(self):
        """Shutdown the skill system and unload all skills"""
        logger.info("Shutting down skill system...")
        
        # Disable all enabled skills
        enabled_skills = self._registry.list_skills(SkillStatus.ENABLED)
        for manifest in enabled_skills:
            await self.disable_skill(manifest.full_id)
        
        # Unload all loaded skills
        loaded_skills = self._registry.list_skills(SkillStatus.LOADED)
        for manifest in loaded_skills:
            await self.unload_skill(manifest.full_id)
        
        await self.emit_event("skill_system.shutdown", {})
        logger.info("Skill system shutdown complete")
    
    # Discovery
    
    async def discover_all(self) -> list[SkillManifest]:
        """Discover all skills from all paths"""
        manifests = self._loader.discover_skills()
        
        for manifest in manifests:
            self._registry.register_skill(manifest, SkillStatus.DISCOVERED)
        
        await self.emit_event("skill_system.discovered", {
            "count": len(manifests),
            "skills": [m.full_id for m in manifests]
        })
        
        return manifests
    
    async def discover_by_type(self, skill_type: SkillType) -> list[SkillManifest]:
        """Discover skills of a specific type"""
        manifests = self._loader.discover_skills(skill_type)
        
        for manifest in manifests:
            self._registry.register_skill(manifest, SkillStatus.DISCOVERED)
        
        return manifests
    
    # Skill Lifecycle
    
    async def load_skill(self, skill_id: str) -> bool:
        """
        Load a skill into memory.
        
        Args:
            skill_id: Full skill ID (e.g., "workspace:my_skill")
            
        Returns:
            True if successfully loaded
        """
        manifest = self._registry.get_skill(skill_id)
        if not manifest:
            raise SkillManagerError(f"Skill not found: {skill_id}")
        
        current_status = self._registry.get_skill_status(skill_id)
        if current_status in (SkillStatus.LOADED, SkillStatus.ENABLED):
            logger.debug(f"Skill {skill_id} already loaded")
            return True
        
        logger.info(f"Loading skill: {skill_id}")
        
        try:
            # Load dependencies first
            await self._load_dependencies(manifest)
            
            # Load the skill module
            module = self._loader.load_skill(manifest)
            
            # Update status
            self._registry.set_skill_status(skill_id, SkillStatus.LOADED)
            
            # Register components
            await self._register_components(skill_id, manifest, module)
            
            # Emit event
            await self.emit_event("skill.loaded", {
                "skill_id": skill_id,
                "manifest": manifest.to_dict()
            })
            
            logger.info(f"Skill loaded: {skill_id}")
            return True
            
        except Exception as e:
            self._registry.set_skill_status(skill_id, SkillStatus.ERROR)
            logger.error(f"Failed to load skill {skill_id}: {e}")
            raise SkillManagerError(f"Failed to load {skill_id}: {e}") from e
    
    async def unload_skill(self, skill_id: str) -> bool:
        """
        Unload a skill from memory.
        
        Args:
            skill_id: Full skill ID
            
        Returns:
            True if successfully unloaded
        """
        manifest = self._registry.get_skill(skill_id)
        if not manifest:
            return False
        
        current_status = self._registry.get_skill_status(skill_id)
        if current_status == SkillStatus.UNLOADED:
            return True
        
        # Disable first if enabled
        if current_status == SkillStatus.ENABLED:
            await self.disable_skill(skill_id)
        
        logger.info(f"Unloading skill: {skill_id}")
        
        try:
            # Unregister components
            self._registry.unregister_all_tools(skill_id)
            self._registry.unregister_all_commands(skill_id)
            self._registry.unregister_all_event_handlers(skill_id)
            
            # Unload module
            self._loader.unload_skill(manifest)
            
            # Update status
            self._registry.set_skill_status(skill_id, SkillStatus.UNLOADED)
            
            # Emit event
            await self.emit_event("skill.unloaded", {"skill_id": skill_id})
            
            logger.info(f"Skill unloaded: {skill_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading skill {skill_id}: {e}")
            return False
    
    async def enable_skill(self, skill_id: str) -> bool:
        """
        Enable a skill (make it active).
        
        Args:
            skill_id: Full skill ID
            
        Returns:
            True if successfully enabled
        """
        manifest = self._registry.get_skill(skill_id)
        if not manifest:
            raise SkillManagerError(f"Skill not found: {skill_id}")
        
        current_status = self._registry.get_skill_status(skill_id)
        
        # Load if not loaded
        if current_status in (SkillStatus.DISCOVERED, SkillStatus.DISABLED, SkillStatus.UNLOADED):
            await self.load_skill(skill_id)
        
        if current_status == SkillStatus.ENABLED:
            return True
        
        logger.info(f"Enabling skill: {skill_id}")
        
        try:
            # Enable all components
            for tool in self._registry.list_tools(skill_id):
                self._registry.enable_tool(tool.registration.name, True)
            
            for cmd in self._registry.list_commands(skill_id):
                self._registry.enable_command(cmd.registration.name, True)
            
            # Call skill's enable function if exists
            if hasattr(manifest, '_module'):
                module = manifest._module
                if hasattr(module, 'enable') and callable(module.enable):
                    if asyncio.iscoroutinefunction(module.enable):
                        await module.enable()
                    else:
                        module.enable()
            
            # Update status
            self._registry.set_skill_status(skill_id, SkillStatus.ENABLED)
            
            # Emit event
            await self.emit_event("skill.enabled", {"skill_id": skill_id})
            
            logger.info(f"Skill enabled: {skill_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling skill {skill_id}: {e}")
            return False
    
    async def disable_skill(self, skill_id: str) -> bool:
        """
        Disable a skill (make it inactive but keep loaded).
        
        Args:
            skill_id: Full skill ID
            
        Returns:
            True if successfully disabled
        """
        manifest = self._registry.get_skill(skill_id)
        if not manifest:
            return False
        
        current_status = self._registry.get_skill_status(skill_id)
        if current_status != SkillStatus.ENABLED:
            return True
        
        logger.info(f"Disabling skill: {skill_id}")
        
        try:
            # Disable all components
            for tool in self._registry.list_tools(skill_id):
                self._registry.enable_tool(tool.registration.name, False)
            
            for cmd in self._registry.list_commands(skill_id):
                self._registry.enable_command(cmd.registration.name, False)
            
            # Call skill's disable function if exists
            if hasattr(manifest, '_module'):
                module = manifest._module
                if hasattr(module, 'disable') and callable(module.disable):
                    if asyncio.iscoroutinefunction(module.disable):
                        await module.disable()
                    else:
                        module.disable()
            
            # Update status
            self._registry.set_skill_status(skill_id, SkillStatus.DISABLED)
            
            # Emit event
            await self.emit_event("skill.disabled", {"skill_id": skill_id})
            
            logger.info(f"Skill disabled: {skill_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling skill {skill_id}: {e}")
            return False
    
    async def reload_skill(self, skill_id: str) -> bool:
        """Reload a skill (unload and load again)"""
        logger.info(f"Reloading skill: {skill_id}")
        
        was_enabled = self._registry.get_skill_status(skill_id) == SkillStatus.ENABLED
        
        await self.unload_skill(skill_id)
        
        # Re-discover in case manifest changed
        manifest = self._loader._load_manifest(
            manifest.path / "skill.yaml",
            manifest.skill_type
        )
        if manifest:
            self._registry.register_skill(manifest, SkillStatus.DISCOVERED)
        
        await self.load_skill(skill_id)
        
        if was_enabled:
            await self.enable_skill(skill_id)
        
        await self.emit_event("skill.reloaded", {"skill_id": skill_id})
        return True
    
    # Dependencies
    
    async def _load_dependencies(self, manifest: SkillManifest):
        """Load all dependencies for a skill"""
        for dep in manifest.dependencies:
            if dep.optional:
                try:
                    await self._resolve_dependency(dep)
                except DependencyError as e:
                    logger.warning(f"Optional dependency not met: {e}")
            else:
                await self._resolve_dependency(dep)
    
    async def _resolve_dependency(self, dep):
        """Resolve a single dependency"""
        # Look for skill in registry
        dep_skill = None
        for skill_id, manifest in self._registry._skills.items():
            if manifest.skill_id == dep.skill_id:
                dep_skill = manifest
                break
        
        if not dep_skill:
            # Try to discover
            all_manifests = self._loader.discover_skills()
            for manifest in all_manifests:
                if manifest.skill_id == dep.skill_id:
                    self._registry.register_skill(manifest, SkillStatus.DISCOVERED)
                    dep_skill = manifest
                    break
        
        if not dep_skill:
            raise DependencyError(f"Dependency not found: {dep.skill_id}")
        
        # Check version
        if not satisfies_version(dep_skill.version, dep.version_range):
            raise DependencyError(
                f"Dependency version mismatch: {dep.skill_id} "
                f"(have {dep_skill.version}, need {dep.version_range})"
            )
        
        # Load if not already loaded
        if self._registry.get_skill_status(dep_skill.full_id) not in (SkillStatus.LOADED, SkillStatus.ENABLED):
            await self.load_skill(dep_skill.full_id)
    
    # Component Registration
    
    async def _register_components(self, skill_id: str, manifest: SkillManifest, module):
        """Register all components (tools, commands, events) from a skill"""
        # Register tools
        for tool_reg in manifest.tools:
            try:
                callable_fn = self._get_callable(module, tool_reg.module, tool_reg.function)
                self._registry.register_tool(skill_id, tool_reg, callable_fn)
            except Exception as e:
                logger.error(f"Failed to register tool '{tool_reg.name}': {e}")
        
        # Register commands
        for cmd_reg in manifest.commands:
            try:
                callable_fn = self._get_callable(module, cmd_reg.module, cmd_reg.function)
                self._registry.register_command(skill_id, cmd_reg, callable_fn)
            except Exception as e:
                logger.error(f"Failed to register command '{cmd_reg.name}': {e}")
        
        # Register event handlers
        for evt_reg in manifest.events:
            try:
                callable_fn = self._get_callable(module, evt_reg.module, evt_reg.function)
                self._registry.register_event_handler(skill_id, evt_reg, callable_fn)
            except Exception as e:
                logger.error(f"Failed to register event handler for '{evt_reg.event_type}': {e}")
    
    def _get_callable(self, module, module_name: str, function_name: str) -> Callable:
        """Get a callable function from a module"""
        # First check if it's in the main module
        if hasattr(module, function_name):
            return getattr(module, function_name)
        
        # Otherwise try to import the submodule
        submodule = importlib.import_module(module_name, module.__name__)
        return getattr(submodule, function_name)
    
    # Event System
    
    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def emit_event(self, event_type: str, data: dict):
        """Emit an event to all registered handlers"""
        # First emit to skill registry handlers
        await self._registry.emit_event(event_type, data)
        
        # Then emit to manager handlers
        for handler in self._event_handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for '{event_type}': {e}")
    
    # Queries
    
    def list_skills(self, status: Optional[SkillStatus] = None, skill_type: Optional[SkillType] = None) -> list[SkillManifest]:
        """List skills with optional filtering"""
        skills = self._registry.list_skills(status)
        
        if skill_type:
            skills = [s for s in skills if s.skill_type == skill_type]
        
        return skills
    
    def get_skill(self, skill_id: str) -> Optional[SkillManifest]:
        """Get a skill by ID"""
        return self._registry.get_skill(skill_id)
    
    def get_skill_status(self, skill_id: str) -> Optional[SkillStatus]:
        """Get a skill's status"""
        return self._registry.get_skill_status(skill_id)
    
    def get_stats(self) -> dict:
        """Get skill system statistics"""
        return {
            **self._registry.get_stats(),
            'paths': {
                'system': str(self.system_path),
                'workspace': str(self.workspace_path),
                'installed': str(self.installed_path)
            }
        }


# Global manager instance
_default_manager: Optional[SkillManager] = None


def get_manager() -> SkillManager:
    """Get the default skill manager instance"""
    if _default_manager is None:
        raise RuntimeError("Skill manager not initialized. Call initialize() first.")
    return _default_manager


def initialize(
    system_path: Path,
    workspace_path: Path,
    installed_path: Path,
    auto_discover: bool = True
) -> SkillManager:
    """Initialize the global skill manager"""
    global _default_manager
    _default_manager = SkillManager(system_path, workspace_path, installed_path, auto_discover)
    return _default_manager
