"""
Skill Loader Module for Cell 0 OS

Discovers and loads skills from filesystem directories.
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional

from .skill_manifest import SkillManifest, SkillStatus, SkillType

logger = logging.getLogger(__name__)


class SkillLoadError(Exception):
    """Exception raised when skill loading fails"""
    pass


class SkillLoader:
    """
    Discovers and loads skills from the filesystem.
    
    Skills are discovered by looking for skill.yaml files in:
    - System skills: <cell0_root>/skills/system/
    - Workspace skills: <workspace>/.cell0/skills/
    - Installed skills: <cell0_root>/skills/installed/
    
    Each skill directory should contain:
    - skill.yaml (manifest)
    - __init__.py (entry point)
    - Other skill modules
    """
    
    MANIFEST_FILE = "skill.yaml"
    
    def __init__(self, system_skills_path: Path, workspace_skills_path: Path, installed_skills_path: Path):
        self.system_skills_path = Path(system_skills_path)
        self.workspace_skills_path = Path(workspace_skills_path)
        self.installed_skills_path = Path(installed_skills_path)
        
        # Track loaded modules for cleanup
        self._loaded_modules: dict[str, str] = {}  # module_name -> file_path
        
        logger.debug(f"SkillLoader initialized with paths:")
        logger.debug(f"  System: {self.system_skills_path}")
        logger.debug(f"  Workspace: {self.workspace_skills_path}")
        logger.debug(f"  Installed: {self.installed_skills_path}")
    
    def discover_skills(self, skill_type: Optional[SkillType] = None) -> list[SkillManifest]:
        """
        Discover all skills in the configured directories.
        
        Args:
            skill_type: If specified, only discover skills of this type
            
        Returns:
            List of discovered skill manifests
        """
        manifests = []
        
        paths_to_search = []
        if skill_type is None or skill_type == SkillType.SYSTEM:
            paths_to_search.append((self.system_skills_path, SkillType.SYSTEM))
        if skill_type is None or skill_type == SkillType.WORKSPACE:
            paths_to_search.append((self.workspace_skills_path, SkillType.WORKSPACE))
        if skill_type is None or skill_type == SkillType.INSTALLED:
            paths_to_search.append((self.installed_skills_path, SkillType.INSTALLED))
        
        for base_path, stype in paths_to_search:
            if not base_path.exists():
                logger.debug(f"Skills path does not exist: {base_path}")
                continue
            
            logger.debug(f"Discovering {stype.value} skills in {base_path}")
            
            for skill_dir in base_path.iterdir():
                if not skill_dir.is_dir():
                    continue
                
                manifest_path = skill_dir / self.MANIFEST_FILE
                if not manifest_path.exists():
                    logger.debug(f"No {self.MANIFEST_FILE} in {skill_dir}")
                    continue
                
                try:
                    manifest = self._load_manifest(manifest_path, stype)
                    if manifest:
                        manifests.append(manifest)
                except Exception as e:
                    logger.error(f"Failed to load manifest from {manifest_path}: {e}")
        
        logger.info(f"Discovered {len(manifests)} skills")
        return manifests
    
    def _load_manifest(self, path: Path, skill_type: SkillType) -> Optional[SkillManifest]:
        """Load a single manifest file"""
        try:
            manifest = SkillManifest.from_yaml(path)
            manifest.skill_type = skill_type
            
            # Validate manifest
            errors = manifest.validate()
            if errors:
                logger.warning(f"Manifest validation errors for {path}: {', '.join(errors)}")
                return None
            
            return manifest
        except Exception as e:
            logger.error(f"Error parsing manifest {path}: {e}")
            return None
    
    def load_skill(self, manifest: SkillManifest) -> Optional[module]:
        """
        Load a skill module into memory.
        
        Args:
            manifest: The skill manifest to load
            
        Returns:
            Loaded module or None if loading failed
        """
        if not manifest.path:
            raise SkillLoadError(f"Manifest has no path: {manifest.skill_id}")
        
        logger.info(f"Loading skill: {manifest.full_id}")
        
        # Determine entry point
        entry_file = manifest.entry_point or "__init__.py"
        entry_path = manifest.path / entry_file
        
        if not entry_path.exists():
            raise SkillLoadError(f"Entry point not found: {entry_path}")
        
        # Create unique module name to avoid conflicts
        module_name = f"cell0_skill_{manifest.skill_type.value}_{manifest.skill_id}"
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            if not spec or not spec.loader:
                raise SkillLoadError(f"Could not create module spec for {entry_path}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Add skill directory to sys.path for imports
            if str(manifest.path) not in sys.path:
                sys.path.insert(0, str(manifest.path))
            
            # Execute module
            spec.loader.exec_module(module)
            
            # Track loaded module
            self._loaded_modules[module_name] = str(entry_path)
            
            # Store reference on manifest
            manifest._module = module
            
            logger.debug(f"Successfully loaded skill module: {module_name}")
            return module
            
        except Exception as e:
            logger.error(f"Failed to load skill {manifest.full_id}: {e}")
            raise SkillLoadError(f"Failed to load {manifest.full_id}: {e}") from e
    
    def unload_skill(self, manifest: SkillManifest) -> bool:
        """
        Unload a skill module from memory.
        
        Args:
            manifest: The skill manifest to unload
            
        Returns:
            True if successfully unloaded
        """
        module_name = f"cell0_skill_{manifest.skill_type.value}_{manifest.skill_id}"
        
        if module_name in sys.modules:
            try:
                # Call cleanup if available
                module = sys.modules[module_name]
                if hasattr(module, 'cleanup') and callable(module.cleanup):
                    logger.debug(f"Calling cleanup for {manifest.full_id}")
                    module.cleanup()
                
                # Remove from sys.modules
                del sys.modules[module_name]
                
                # Remove from tracking
                if module_name in self._loaded_modules:
                    del self._loaded_modules[module_name]
                
                # Clean up path
                if manifest.path and str(manifest.path) in sys.path:
                    sys.path.remove(str(manifest.path))
                
                logger.info(f"Unloaded skill: {manifest.full_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error unloading skill {manifest.full_id}: {e}")
                return False
        
        return True
    
    def reload_skill(self, manifest: SkillManifest) -> Optional[module]:
        """
        Reload a skill module.
        
        Args:
            manifest: The skill manifest to reload
            
        Returns:
            Reloaded module or None if reloading failed
        """
        logger.info(f"Reloading skill: {manifest.full_id}")
        self.unload_skill(manifest)
        return self.load_skill(manifest)
    
    def get_skill_directory(self, skill_id: str, skill_type: SkillType) -> Optional[Path]:
        """Get the directory path for a skill"""
        if skill_type == SkillType.SYSTEM:
            base = self.system_skills_path
        elif skill_type == SkillType.WORKSPACE:
            base = self.workspace_skills_path
        else:
            base = self.installed_skills_path
        
        skill_dir = base / skill_id
        if skill_dir.exists():
            return skill_dir
        return None
    
    def create_skill_template(self, skill_id: str, name: str, path: Path) -> Path:
        """
        Create a new skill template directory.
        
        Args:
            skill_id: Unique identifier for the skill
            name: Human-readable name
            path: Directory to create skill in
            
        Returns:
            Path to created skill directory
        """
        skill_dir = path / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Create skill.yaml
        manifest_content = f'''id: {skill_id}
name: {name}
version: 0.1.0
description: A new Cell 0 skill
author: Your Name
type: workspace

# Dependencies on other skills
dependencies: []
  # - core_utils
  # - database>=2.0.0

# Tools to register with the engine
tools: []
  # - name: my_tool
  #   module: {skill_id}.tools
  #   function: execute
  #   description: Does something useful

# CLI commands to register
commands: []
  # - name: my-cmd
  #   module: {skill_id}.cli
  #   function: run
  #   description: My CLI command
  #   aliases: [mc]

# Event handlers
events: []
  # - event_type: skill.loaded
  #   module: {skill_id}.handlers
  #   function: on_skill_loaded
  #   priority: 100
'''
        (skill_dir / "skill.yaml").write_text(manifest_content)
        
        # Create __init__.py
        init_content = f'''"""
{name} - A Cell 0 OS Skill
"""

# Skill metadata
__version__ = "0.1.0"
__author__ = "Your Name"

def initialize():
    """
    Called when the skill is enabled.
    Use this to set up any resources your skill needs.
    """
    print(f"Initializing {{__name__}}")

def cleanup():
    """
    Called when the skill is unloaded.
    Use this to clean up any resources.
    """
    print(f"Cleaning up {{__name__}}")
'''
        (skill_dir / "__init__.py").write_text(init_content)
        
        # Create tools module
        tools_dir = skill_dir / "tools.py"
        tools_content = f'''"""
Tools for {name}
"""

def execute(**kwargs):
    """
    Example tool function.
    
    Args:
        **kwargs: Parameters passed by the engine
        
    Returns:
        Result of the tool execution
    """
    return {{"status": "success", "message": "Tool executed"}}
'''
        tools_dir.write_text(tools_content)
        
        # Create cli module
        cli_file = skill_dir / "cli.py"
        cli_content = f'''"""
CLI commands for {name}
"""

def run(args):
    """
    Example CLI command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print(f"Running command with args: {{args}}")
    return 0
'''
        cli_file.write_text(cli_content)
        
        logger.info(f"Created skill template at {skill_dir}")
        return skill_dir


# Global loader instance (initialized by skill manager)
_default_loader: Optional[SkillLoader] = None


def get_loader() -> SkillLoader:
    """Get the default skill loader instance"""
    if _default_loader is None:
        raise RuntimeError("Skill loader not initialized. Call initialize_loader() first.")
    return _default_loader


def initialize_loader(system_path: Path, workspace_path: Path, installed_path: Path) -> SkillLoader:
    """Initialize the global skill loader"""
    global _default_loader
    _default_loader = SkillLoader(system_path, workspace_path, installed_path)
    return _default_loader
