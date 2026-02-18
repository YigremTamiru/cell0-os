"""
Skill Registry Module for Cell 0 OS

Central registry for managing skill metadata, tools, commands, and event handlers.
"""

from collections import defaultdict
from typing import Any, Callable, Optional
import logging

from .skill_manifest import SkillManifest, SkillStatus, ToolRegistration, CommandRegistration, EventHandler

logger = logging.getLogger(__name__)


class RegisteredTool:
    """A registered tool with its metadata and callable"""
    def __init__(self, registration: ToolRegistration, callable_fn: Callable, skill_id: str):
        self.registration = registration
        self.callable = callable_fn
        self.skill_id = skill_id
        self.enabled = True
    
    def __call__(self, *args, **kwargs):
        if not self.enabled:
            raise RuntimeError(f"Tool '{self.registration.name}' is disabled")
        return self.callable(*args, **kwargs)
    
    def to_dict(self) -> dict:
        return {
            'name': self.registration.name,
            'skill_id': self.skill_id,
            'description': self.registration.description,
            'enabled': self.enabled,
            'parameters': self.registration.parameters
        }


class RegisteredCommand:
    """A registered CLI command with its metadata and callable"""
    def __init__(self, registration: CommandRegistration, callable_fn: Callable, skill_id: str):
        self.registration = registration
        self.callable = callable_fn
        self.skill_id = skill_id
        self.enabled = True
    
    def __call__(self, *args, **kwargs):
        if not self.enabled:
            raise RuntimeError(f"Command '{self.registration.name}' is disabled")
        return self.callable(*args, **kwargs)
    
    def to_dict(self) -> dict:
        return {
            'name': self.registration.name,
            'skill_id': self.skill_id,
            'description': self.registration.description,
            'enabled': self.enabled,
            'aliases': self.registration.aliases
        }


class RegisteredEventHandler:
    """A registered event handler"""
    def __init__(self, registration: EventHandler, callable_fn: Callable, skill_id: str):
        self.registration = registration
        self.callable = callable_fn
        self.skill_id = skill_id
        self.enabled = True
    
    async def __call__(self, event_data: Any):
        if not self.enabled:
            return None
        
        import asyncio
        if asyncio.iscoroutinefunction(self.callable):
            return await self.callable(event_data)
        else:
            return self.callable(event_data)
    
    def to_dict(self) -> dict:
        return {
            'event_type': self.registration.event_type,
            'skill_id': self.skill_id,
            'priority': self.registration.priority,
            'enabled': self.enabled
        }


class SkillRegistry:
    """
    Central registry for all skill components.
    
    Maintains:
    - Skill manifests and their status
    - Registered tools
    - Registered CLI commands
    - Registered event handlers
    """
    
    def __init__(self):
        # Skill manifests by full_id
        self._skills: dict[str, SkillManifest] = {}
        self._skill_status: dict[str, SkillStatus] = {}
        
        # Registered tools by name
        self._tools: dict[str, RegisteredTool] = {}
        
        # Registered commands by name
        self._commands: dict[str, RegisteredCommand] = {}
        
        # Event handlers by event type
        self._event_handlers: dict[str, list[RegisteredEventHandler]] = defaultdict(list)
        
        # Track which components belong to which skill
        self._skill_tools: dict[str, set[str]] = defaultdict(set)
        self._skill_commands: dict[str, set[str]] = defaultdict(set)
        self._skill_events: dict[str, set[str]] = defaultdict(set)
        
        logger.debug("SkillRegistry initialized")
    
    # Skill Management
    
    def register_skill(self, manifest: SkillManifest, status: SkillStatus = SkillStatus.DISCOVERED):
        """Register a skill manifest"""
        self._skills[manifest.full_id] = manifest
        self._skill_status[manifest.full_id] = status
        logger.debug(f"Registered skill: {manifest.full_id} ({status.value})")
    
    def unregister_skill(self, skill_id: str) -> bool:
        """Remove a skill from the registry"""
        if skill_id not in self._skills:
            return False
        
        # Unregister all components
        self.unregister_all_tools(skill_id)
        self.unregister_all_commands(skill_id)
        self.unregister_all_event_handlers(skill_id)
        
        del self._skills[skill_id]
        del self._skill_status[skill_id]
        
        logger.debug(f"Unregistered skill: {skill_id}")
        return True
    
    def get_skill(self, skill_id: str) -> Optional[SkillManifest]:
        """Get a skill manifest by ID"""
        return self._skills.get(skill_id)
    
    def get_skill_status(self, skill_id: str) -> Optional[SkillStatus]:
        """Get the status of a skill"""
        return self._skill_status.get(skill_id)
    
    def set_skill_status(self, skill_id: str, status: SkillStatus):
        """Update a skill's status"""
        if skill_id in self._skill_status:
            old_status = self._skill_status[skill_id]
            self._skill_status[skill_id] = status
            logger.debug(f"Skill {skill_id} status: {old_status.value} -> {status.value}")
    
    def list_skills(self, status: Optional[SkillStatus] = None) -> list[SkillManifest]:
        """List all registered skills, optionally filtered by status"""
        if status is None:
            return list(self._skills.values())
        return [
            manifest for sid, manifest in self._skills.items()
            if self._skill_status.get(sid) == status
        ]
    
    # Tool Management
    
    def register_tool(self, skill_id: str, registration: ToolRegistration, callable_fn: Callable) -> bool:
        """Register a tool from a skill"""
        if registration.name in self._tools:
            existing = self._tools[registration.name]
            logger.warning(f"Tool '{registration.name}' already registered by {existing.skill_id}")
            return False
        
        tool = RegisteredTool(registration, callable_fn, skill_id)
        self._tools[registration.name] = tool
        self._skill_tools[skill_id].add(registration.name)
        
        logger.debug(f"Registered tool '{registration.name}' from {skill_id}")
        return True
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name not in self._tools:
            return False
        
        tool = self._tools[tool_name]
        self._skill_tools[tool.skill_id].discard(tool_name)
        del self._tools[tool_name]
        
        logger.debug(f"Unregistered tool '{tool_name}'")
        return True
    
    def unregister_all_tools(self, skill_id: str):
        """Unregister all tools from a skill"""
        for tool_name in list(self._skill_tools[skill_id]):
            self.unregister_tool(tool_name)
        del self._skill_tools[skill_id]
    
    def get_tool(self, tool_name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name"""
        return self._tools.get(tool_name)
    
    def list_tools(self, skill_id: Optional[str] = None) -> list[RegisteredTool]:
        """List all registered tools, optionally filtered by skill"""
        if skill_id:
            return [
                self._tools[name] for name in self._skill_tools.get(skill_id, [])
                if name in self._tools
            ]
        return list(self._tools.values())
    
    def enable_tool(self, tool_name: str, enabled: bool = True) -> bool:
        """Enable or disable a tool"""
        if tool_name not in self._tools:
            return False
        self._tools[tool_name].enabled = enabled
        return True
    
    # Command Management
    
    def register_command(self, skill_id: str, registration: CommandRegistration, callable_fn: Callable) -> bool:
        """Register a CLI command from a skill"""
        if registration.name in self._commands:
            existing = self._commands[registration.name]
            logger.warning(f"Command '{registration.name}' already registered by {existing.skill_id}")
            return False
        
        cmd = RegisteredCommand(registration, callable_fn, skill_id)
        self._commands[registration.name] = cmd
        self._skill_commands[skill_id].add(registration.name)
        
        # Also register aliases
        for alias in registration.aliases:
            if alias not in self._commands:
                self._commands[alias] = cmd
        
        logger.debug(f"Registered command '{registration.name}' from {skill_id}")
        return True
    
    def unregister_command(self, command_name: str) -> bool:
        """Unregister a command"""
        if command_name not in self._commands:
            return False
        
        cmd = self._commands[command_name]
        self._skill_commands[cmd.skill_id].discard(command_name)
        
        # Also remove aliases
        for alias in cmd.registration.aliases:
            if alias in self._commands and self._commands[alias] is cmd:
                del self._commands[alias]
        
        del self._commands[command_name]
        
        logger.debug(f"Unregistered command '{command_name}'")
        return True
    
    def unregister_all_commands(self, skill_id: str):
        """Unregister all commands from a skill"""
        for cmd_name in list(self._skill_commands[skill_id]):
            self.unregister_command(cmd_name)
        del self._skill_commands[skill_id]
    
    def get_command(self, command_name: str) -> Optional[RegisteredCommand]:
        """Get a registered command by name"""
        return self._commands.get(command_name)
    
    def list_commands(self, skill_id: Optional[str] = None) -> list[RegisteredCommand]:
        """List all registered commands, optionally filtered by skill"""
        if skill_id:
            return [
                self._commands[name] for name in self._skill_commands.get(skill_id, [])
                if name in self._commands
            ]
        # Return unique commands (not aliases)
        seen = set()
        unique_cmds = []
        for cmd in self._commands.values():
            if cmd.registration.name not in seen:
                seen.add(cmd.registration.name)
                unique_cmds.append(cmd)
        return unique_cmds
    
    def enable_command(self, command_name: str, enabled: bool = True) -> bool:
        """Enable or disable a command"""
        if command_name not in self._commands:
            return False
        self._commands[command_name].enabled = enabled
        return True
    
    # Event Handler Management
    
    def register_event_handler(self, skill_id: str, registration: EventHandler, callable_fn: Callable) -> bool:
        """Register an event handler from a skill"""
        handler = RegisteredEventHandler(registration, callable_fn, skill_id)
        self._event_handlers[registration.event_type].append(handler)
        self._skill_events[skill_id].add(f"{registration.event_type}:{id(handler)}")
        
        # Sort by priority (lower = higher priority)
        self._event_handlers[registration.event_type].sort(
            key=lambda h: h.registration.priority
        )
        
        logger.debug(f"Registered handler for '{registration.event_type}' from {skill_id}")
        return True
    
    def unregister_event_handler(self, skill_id: str, event_type: str, handler_id: int) -> bool:
        """Unregister a specific event handler"""
        handlers = self._event_handlers.get(event_type, [])
        for i, handler in enumerate(handlers):
            if id(handler) == handler_id and handler.skill_id == skill_id:
                handlers.pop(i)
                self._skill_events[skill_id].discard(f"{event_type}:{handler_id}")
                logger.debug(f"Unregistered handler for '{event_type}' from {skill_id}")
                return True
        return False
    
    def unregister_all_event_handlers(self, skill_id: str):
        """Unregister all event handlers from a skill"""
        for key in list(self._skill_events.get(skill_id, [])):
            event_type, handler_id = key.rsplit(':', 1)
            self.unregister_event_handler(skill_id, event_type, int(handler_id))
        del self._skill_events[skill_id]
    
    def get_event_handlers(self, event_type: str) -> list[RegisteredEventHandler]:
        """Get all handlers for an event type"""
        return self._event_handlers.get(event_type, [])
    
    def list_event_types(self) -> list[str]:
        """List all registered event types"""
        return list(self._event_handlers.keys())
    
    async def emit_event(self, event_type: str, event_data: Any) -> list[Any]:
        """
        Emit an event to all registered handlers.
        
        Returns:
            List of results from all handlers
        """
        handlers = self._event_handlers.get(event_type, [])
        results = []
        
        for handler in handlers:
            if not handler.enabled:
                continue
            
            try:
                result = await handler(event_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in event handler for '{event_type}' from {handler.skill_id}: {e}")
        
        return results
    
    # Statistics
    
    def get_stats(self) -> dict:
        """Get registry statistics"""
        return {
            'skills': len(self._skills),
            'tools': len(self._tools),
            'commands': len(self._commands),
            'event_types': len(self._event_handlers),
            'status_breakdown': {
                status.value: sum(1 for s in self._skill_status.values() if s == status)
                for status in SkillStatus
            }
        }
    
    def clear(self):
        """Clear all registrations (use with caution)"""
        self._skills.clear()
        self._skill_status.clear()
        self._tools.clear()
        self._commands.clear()
        self._event_handlers.clear()
        self._skill_tools.clear()
        self._skill_commands.clear()
        self._skill_events.clear()
        logger.warning("SkillRegistry cleared")


# Global registry instance
_default_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """Get the default skill registry instance"""
    if _default_registry is None:
        raise RuntimeError("Skill registry not initialized. Call initialize_registry() first.")
    return _default_registry


def initialize_registry() -> SkillRegistry:
    """Initialize the global skill registry"""
    global _default_registry
    _default_registry = SkillRegistry()
    return _default_registry
