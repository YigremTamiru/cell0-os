"""
Tests for Cell 0 OS Skill System

Run with: pytest tests/test_skills.py -v
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from cell0.engine.skills import (
    SkillManifest,
    SkillDependency,
    SkillType,
    SkillStatus,
    SkillLoader,
    SkillRegistry,
    SkillManager,
    satisfies_version,
)


# Fixtures

@pytest.fixture
def temp_skills_dir():
    """Create a temporary directory for skills"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_skill_manifest():
    """Create a sample skill manifest for testing"""
    return SkillManifest(
        skill_id="test_skill",
        name="Test Skill",
        version="1.0.0",
        description="A test skill",
        author="Test Author",
        skill_type=SkillType.WORKSPACE
    )


@pytest.fixture
def skill_loader(temp_skills_dir):
    """Create a skill loader instance"""
    return SkillLoader(
        system_path=temp_skills_dir / "system",
        workspace_path=temp_skills_dir / "workspace",
        installed_path=temp_skills_dir / "installed"
    )


@pytest.fixture
def skill_registry():
    """Create a skill registry instance"""
    registry = SkillRegistry()
    yield registry
    registry.clear()


@pytest.fixture
def skill_manager(temp_skills_dir):
    """Create a skill manager instance"""
    manager = SkillManager(
        system_path=temp_skills_dir / "system",
        workspace_path=temp_skills_dir / "workspace",
        installed_path=temp_skills_dir / "installed",
        auto_discover=False
    )
    yield manager
    # Cleanup
    asyncio.run(manager.shutdown())


# Version Tests

class TestVersionParsing:
    """Test version parsing and comparison"""
    
    def test_exact_version_match(self):
        assert satisfies_version("1.0.0", "1.0.0")
        assert not satisfies_version("1.0.0", "1.0.1")
    
    def test_wildcard_version(self):
        assert satisfies_version("1.0.0", "*")
        assert satisfies_version("2.5.3", "*")
    
    def test_greater_than_or_equal(self):
        assert satisfies_version("1.0.0", ">=1.0.0")
        assert satisfies_version("1.1.0", ">=1.0.0")
        assert satisfies_version("2.0.0", ">=1.0.0")
        assert not satisfies_version("0.9.0", ">=1.0.0")
    
    def test_greater_than(self):
        assert satisfies_version("1.1.0", ">1.0.0")
        assert not satisfies_version("1.0.0", ">1.0.0")
    
    def test_less_than_or_equal(self):
        assert satisfies_version("1.0.0", "<=1.0.0")
        assert satisfies_version("0.9.0", "<=1.0.0")
        assert not satisfies_version("1.1.0", "<=1.0.0")
    
    def test_compatible_version(self):
        # ^1.0.0 means >=1.0.0 and <2.0.0
        assert satisfies_version("1.0.0", "^1.0.0")
        assert satisfies_version("1.5.0", "^1.0.0")
        assert not satisfies_version("2.0.0", "^1.0.0")
        assert not satisfies_version("0.9.0", "^1.0.0")
    
    def test_approximate_version(self):
        # ~1.0.0 means >=1.0.0 and <1.1.0
        assert satisfies_version("1.0.0", "~1.0.0")
        assert satisfies_version("1.0.5", "~1.0.0")


# Manifest Tests

class TestSkillManifest:
    """Test skill manifest functionality"""
    
    def test_manifest_creation(self, sample_skill_manifest):
        assert sample_skill_manifest.skill_id == "test_skill"
        assert sample_skill_manifest.name == "Test Skill"
        assert sample_skill_manifest.version == "1.0.0"
        assert sample_skill_manifest.full_id == "workspace:test_skill"
    
    def test_manifest_validation_valid(self, sample_skill_manifest):
        errors = sample_skill_manifest.validate()
        assert len(errors) == 0
    
    def test_manifest_validation_missing_id(self):
        manifest = SkillManifest(skill_id="", name="Test", version="1.0.0")
        errors = manifest.validate()
        assert any("ID is required" in e for e in errors)
    
    def test_manifest_validation_invalid_id(self):
        manifest = SkillManifest(skill_id="invalid id!", name="Test", version="1.0.0")
        errors = manifest.validate()
        assert any("alphanumeric" in e for e in errors)
    
    def test_manifest_validation_missing_name(self):
        manifest = SkillManifest(skill_id="test", name="", version="1.0.0")
        errors = manifest.validate()
        assert any("name is required" in e for e in errors)
    
    def test_manifest_validation_invalid_version(self):
        manifest = SkillManifest(skill_id="test", name="Test", version="invalid")
        errors = manifest.validate()
        assert any("semantic versioning" in e for e in errors)
    
    def test_dependency_parsing_string(self):
        dep = SkillDependency.from_dict("core_utils")
        assert dep.skill_id == "core_utils"
        assert dep.version_range == "*"
        assert not dep.optional
    
    def test_dependency_parsing_with_version(self):
        dep = SkillDependency.from_dict("database>=2.0.0")
        assert dep.skill_id == "database"
        assert dep.version_range == ">=2.0.0"
    
    def test_dependency_parsing_dict(self):
        dep = SkillDependency.from_dict({
            "id": "my_skill",
            "version": "^1.0.0",
            "optional": True
        })
        assert dep.skill_id == "my_skill"
        assert dep.version_range == "^1.0.0"
        assert dep.optional


# Loader Tests

class TestSkillLoader:
    """Test skill loader functionality"""
    
    def test_discover_empty_directory(self, skill_loader, temp_skills_dir):
        skills = skill_loader.discover_skills()
        assert len(skills) == 0
    
    def test_discover_single_skill(self, skill_loader, temp_skills_dir):
        # Create a test skill
        skill_dir = temp_skills_dir / "workspace" / "test_skill"
        skill_dir.mkdir(parents=True)
        
        manifest_content = """
id: test_skill
name: Test Skill
version: 1.0.0
description: A test skill
"""
        (skill_dir / "skill.yaml").write_text(manifest_content)
        
        skills = skill_loader.discover_skills()
        assert len(skills) == 1
        assert skills[0].skill_id == "test_skill"
    
    def test_create_skill_template(self, skill_loader, temp_skills_dir):
        skill_dir = skill_loader.create_skill_template(
            "new_skill",
            "New Skill",
            temp_skills_dir / "workspace"
        )
        
        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "__init__.py").exists()
        assert (skill_dir / "tools.py").exists()
        assert (skill_dir / "cli.py").exists()
        
        # Check manifest content
        manifest = SkillManifest.from_yaml(skill_dir / "skill.yaml")
        assert manifest.skill_id == "new_skill"
        assert manifest.name == "New Skill"


# Registry Tests

class TestSkillRegistry:
    """Test skill registry functionality"""
    
    def test_register_skill(self, skill_registry, sample_skill_manifest):
        skill_registry.register_skill(sample_skill_manifest)
        
        retrieved = skill_registry.get_skill("workspace:test_skill")
        assert retrieved is not None
        assert retrieved.skill_id == "test_skill"
    
    def test_unregister_skill(self, skill_registry, sample_skill_manifest):
        skill_registry.register_skill(sample_skill_manifest)
        skill_registry.unregister_skill("workspace:test_skill")
        
        assert skill_registry.get_skill("workspace:test_skill") is None
    
    def test_register_tool(self, skill_registry):
        from cell0.engine.skills.skill_manifest import ToolRegistration
        
        def dummy_tool(**kwargs):
            return {"result": "ok"}
        
        reg = ToolRegistration(
            name="test_tool",
            module="test.module",
            function="execute",
            description="A test tool"
        )
        
        success = skill_registry.register_tool("workspace:test", reg, dummy_tool)
        assert success
        
        tool = skill_registry.get_tool("test_tool")
        assert tool is not None
        assert tool.registration.name == "test_tool"
    
    def test_register_duplicate_tool(self, skill_registry):
        from cell0.engine.skills.skill_manifest import ToolRegistration
        
        reg = ToolRegistration(
            name="test_tool",
            module="test.module",
            function="execute",
            description="A test tool"
        )
        
        def dummy_tool(**kwargs):
            return {}
        
        skill_registry.register_tool("skill1", reg, dummy_tool)
        success = skill_registry.register_tool("skill2", reg, dummy_tool)
        
        assert not success  # Should fail (duplicate name)
    
    def test_register_command(self, skill_registry):
        from cell0.engine.skills.skill_manifest import CommandRegistration
        
        def dummy_cmd(args):
            return 0
        
        reg = CommandRegistration(
            name="test-cmd",
            module="test.module",
            function="run",
            description="A test command",
            aliases=["tc"]
        )
        
        success = skill_registry.register_command("workspace:test", reg, dummy_cmd)
        assert success
        
        cmd = skill_registry.get_command("test-cmd")
        assert cmd is not None
        
        # Check alias also works
        alias_cmd = skill_registry.get_command("tc")
        assert alias_cmd is cmd
    
    def test_register_event_handler(self, skill_registry):
        from cell0.engine.skills.skill_manifest import EventHandler
        
        def on_test_event(data):
            return f"handled: {data}"
        
        reg = EventHandler(
            event_type="test.event",
            module="test.module",
            function="on_test_event",
            priority=50
        )
        
        success = skill_registry.register_event_handler("workspace:test", reg, on_test_event)
        assert success
        
        handlers = skill_registry.get_event_handlers("test.event")
        assert len(handlers) == 1
        assert handlers[0].registration.priority == 50
    
    @pytest.mark.asyncio
    async def test_emit_event(self, skill_registry):
        from cell0.engine.skills.skill_manifest import EventHandler
        
        results = []
        
        def handler1(data):
            results.append("handler1")
            return "result1"
        
        def handler2(data):
            results.append("handler2")
            return "result2"
        
        reg1 = EventHandler(event_type="test.event", module="m1", function="f1", priority=100)
        reg2 = EventHandler(event_type="test.event", module="m2", function="f2", priority=50)
        
        skill_registry.register_event_handler("skill1", reg1, handler1)
        skill_registry.register_event_handler("skill2", reg2, handler2)
        
        results_list = await skill_registry.emit_event("test.event", {"test": "data"})
        
        assert len(results_list) == 2
        assert "result1" in results_list
        assert "result2" in results_list
    
    def test_get_stats(self, skill_registry, sample_skill_manifest):
        skill_registry.register_skill(sample_skill_manifest, SkillStatus.DISCOVERED)
        
        stats = skill_registry.get_stats()
        
        assert stats['skills'] == 1
        assert stats['tools'] == 0
        assert stats['commands'] == 0
        assert stats['status_breakdown']['discovered'] == 1


# Manager Tests

class TestSkillManager:
    """Test skill manager functionality"""
    
    @pytest.mark.asyncio
    async def test_discover_all(self, skill_manager, temp_skills_dir):
        # Create test skills
        for name in ["skill1", "skill2"]:
            skill_dir = temp_skills_dir / "workspace" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "skill.yaml").write_text(f"""
id: {name}
name: {name.title()}
version: 1.0.0
""")
        
        skills = await skill_manager.discover_all()
        
        assert len(skills) == 2
        skill_ids = [s.skill_id for s in skills]
        assert "skill1" in skill_ids
        assert "skill2" in skill_ids
    
    @pytest.mark.asyncio
    async def test_load_skill(self, skill_manager, temp_skills_dir):
        # Create a test skill with Python module
        skill_dir = temp_skills_dir / "workspace" / "loadable_skill"
        skill_dir.mkdir(parents=True)
        
        (skill_dir / "skill.yaml").write_text("""
id: loadable_skill
name: Loadable Skill
version: 1.0.0
type: workspace
""")
        
        (skill_dir / "__init__.py").write_text("""
def initialize():
    pass
""")
        
        # Discover first
        await skill_manager.discover_all()
        
        # Load the skill
        success = await skill_manager.load_skill("workspace:loadable_skill")
        
        assert success
        assert skill_manager.get_skill_status("workspace:loadable_skill") == SkillStatus.LOADED
    
    @pytest.mark.asyncio
    async def test_enable_disable_skill(self, skill_manager, temp_skills_dir):
        # Create a test skill
        skill_dir = temp_skills_dir / "workspace" / "toggle_skill"
        skill_dir.mkdir(parents=True)
        
        (skill_dir / "skill.yaml").write_text("""
id: toggle_skill
name: Toggle Skill
version: 1.0.0
type: workspace
""")
        
        (skill_dir / "__init__.py").write_text("""
enabled = False

def enable():
    global enabled
    enabled = True

def disable():
    global enabled
    enabled = False
""")
        
        # Discover and load
        await skill_manager.discover_all()
        await skill_manager.load_skill("workspace:toggle_skill")
        
        # Enable
        success = await skill_manager.enable_skill("workspace:toggle_skill")
        assert success
        assert skill_manager.get_skill_status("workspace:toggle_skill") == SkillStatus.ENABLED
        
        # Disable
        success = await skill_manager.disable_skill("workspace:toggle_skill")
        assert success
        assert skill_manager.get_skill_status("workspace:toggle_skill") == SkillStatus.DISABLED
    
    @pytest.mark.asyncio
    async def test_list_skills_filtering(self, skill_manager, temp_skills_dir):
        # Create skills of different types
        for stype in ["system", "workspace", "installed"]:
            skill_dir = temp_skills_dir / stype / f"{stype}_skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "skill.yaml").write_text(f"""
id: {stype}_skill
name: {stype.title()} Skill
version: 1.0.0
type: {stype}
""")
            (skill_dir / "__init__.py").touch()
        
        await skill_manager.discover_all()
        
        # Filter by type
        system_skills = skill_manager.list_skills(skill_type=SkillType.SYSTEM)
        assert len(system_skills) == 1
        assert system_skills[0].skill_type == SkillType.SYSTEM
        
        workspace_skills = skill_manager.list_skills(skill_type=SkillType.WORKSPACE)
        assert len(workspace_skills) == 1
    
    @pytest.mark.asyncio
    async def test_event_system(self, skill_manager):
        events_received = []
        
        def on_event(data):
            events_received.append(data)
        
        skill_manager.on_event("test.event", on_event)
        
        await skill_manager.emit_event("test.event", {"key": "value"})
        
        assert len(events_received) == 1
        assert events_received[0]["key"] == "value"


# Integration Tests

class TestSkillSystemIntegration:
    """Integration tests for the complete skill system"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, temp_skills_dir):
        """Test complete skill lifecycle: create -> discover -> load -> enable -> disable -> unload"""
        
        # Create skill manager
        manager = SkillManager(
            system_path=temp_skills_dir / "system",
            workspace_path=temp_skills_dir / "workspace",
            installed_path=temp_skills_dir / "installed",
            auto_discover=False
        )
        
        # Create a skill
        loader = manager._loader
        skill_dir = loader.create_skill_template(
            "lifecycle_test",
            "Lifecycle Test",
            temp_skills_dir / "workspace"
        )
        
        # Discover
        skills = await manager.discover_all()
        assert len(skills) == 1
        
        skill_id = skills[0].full_id
        
        # Load
        await manager.load_skill(skill_id)
        assert manager.get_skill_status(skill_id) == SkillStatus.LOADED
        
        # Enable
        await manager.enable_skill(skill_id)
        assert manager.get_skill_status(skill_id) == SkillStatus.ENABLED
        
        # Check registry
        stats = manager.get_stats()
        assert stats['skills'] == 1
        
        # Disable
        await manager.disable_skill(skill_id)
        assert manager.get_skill_status(skill_id) == SkillStatus.DISABLED
        
        # Unload
        await manager.unload_skill(skill_id)
        assert manager.get_skill_status(skill_id) == SkillStatus.UNLOADED
        
        # Cleanup
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_skill_with_components(self, temp_skills_dir):
        """Test a skill that registers tools and commands"""
        
        manager = SkillManager(
            system_path=temp_skills_dir / "system",
            workspace_path=temp_skills_dir / "workspace",
            installed_path=temp_skills_dir / "installed",
            auto_discover=False
        )
        
        # Create skill with components
        skill_dir = temp_skills_dir / "workspace" / "component_skill"
        skill_dir.mkdir(parents=True)
        
        (skill_dir / "skill.yaml").write_text("""
id: component_skill
name: Component Skill
version: 1.0.0
type: workspace

tools:
  - name: test_echo
    module: component_skill.tools
    function: echo
    description: Echo tool

commands:
  - name: test-echo
    module: component_skill.cli
    function: echo_cmd
    description: Echo command
""")
        
        (skill_dir / "__init__.py").write_text("")
        
        (skill_dir / "tools.py").write_text("""
def echo(message=""):
    return {"echo": message}
""")
        
        (skill_dir / "cli.py").write_text("""
def echo_cmd(args):
    print(f"Echo: {args}")
    return 0
""")
        
        # Discover, load, enable
        await manager.discover_all()
        await manager.load_skill("workspace:component_skill")
        await manager.enable_skill("workspace:component_skill")
        
        # Check registry
        registry = manager._registry
        
        tool = registry.get_tool("test_echo")
        assert tool is not None
        result = tool(message="hello")
        assert result == {"echo": "hello"}
        
        cmd = registry.get_command("test-echo")
        assert cmd is not None
        
        stats = manager.get_stats()
        assert stats['tools'] == 1
        assert stats['commands'] == 1
        
        # Cleanup
        await manager.shutdown()


# CLI Tests

class TestSkillCommands:
    """Test CLI commands"""
    
    @pytest.mark.asyncio
    async def test_list_command_output(self, temp_skills_dir):
        """Test that list command produces output"""
        from cell0.interface.cli.skill_commands import cmd_list
        import argparse
        
        # Setup
        manager = SkillManager(
            system_path=temp_skills_dir / "system",
            workspace_path=temp_skills_dir / "workspace",
            installed_path=temp_skills_dir / "installed",
            auto_discover=False
        )
        
        # Create a skill
        skill_dir = temp_skills_dir / "workspace" / "cli_test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "skill.yaml").write_text("""
id: cli_test_skill
name: CLI Test Skill
version: 2.0.0
type: workspace
""")
        
        await manager.discover_all()
        
        # Test list command
        args = argparse.Namespace(enabled=False, disabled=False)
        result = await cmd_list(args)
        
        assert result == 0
        
        # Cleanup
        await manager.shutdown()
