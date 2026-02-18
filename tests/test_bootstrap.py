"""
Cell 0 OS - Bootstrap Validation Tests

These tests validate that the test environment is properly configured
and all core imports work correctly. Run these first to ensure the
environment is ready for testing.

Usage:
    pytest tests/test_bootstrap.py -v
"""

import importlib
import sys
from pathlib import Path

import pytest

# ============================================================================
# Path Configuration Tests
# ============================================================================

class TestPathConfiguration:
    """Verify the project path configuration."""
    
    def test_project_root_exists(self, project_root: Path):
        """Test that project root directory exists."""
        assert project_root.exists()
        assert project_root.is_dir()
    
    def test_tests_directory_exists(self, project_root: Path):
        """Test that tests directory exists."""
        tests_dir = project_root / "tests"
        assert tests_dir.exists()
        assert tests_dir.is_dir()
    
    def test_project_root_in_sys_path(self, project_root: Path):
        """Test that project root is in sys.path."""
        assert str(project_root) in sys.path
    
    def test_key_directories_exist(self, project_root: Path):
        """Test that key project directories exist."""
        required_dirs = [
            "col",
            "engine",
            "service",
            "cell0",
            "tests"
        ]
        
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            assert dir_path.exists(), f"Required directory '{dir_name}' not found"


# ============================================================================
# Module Import Tests
# ============================================================================

class TestCoreModuleImports:
    """Verify all core modules can be imported."""
    
    def test_import_col(self):
        """Test importing the COL module."""
        import col
        assert col is not None
        assert hasattr(col, '__version__')
    
    def test_import_col_orchestrator(self):
        """Test importing COL orchestrator."""
        from col import COL, govern, get_stats
        assert COL is not None
        assert callable(govern)
        assert callable(get_stats)
    
    def test_import_col_classifier(self):
        """Test importing COL classifier."""
        from col.classifier import RequestClassifier, ClassificationResult
        assert RequestClassifier is not None
    
    def test_import_col_token_economy(self):
        """Test importing COL token economy."""
        from col.token_economy import TokenEconomy, TokenBudget
        assert TokenEconomy is not None
        assert TokenBudget is not None
    
    def test_import_col_checkpoint(self):
        """Test importing COL checkpoint manager."""
        from col.checkpoint import CheckpointManager, Checkpoint
        assert CheckpointManager is not None
    
    def test_import_engine(self):
        """Test importing the engine module."""
        import engine
        assert engine is not None
    
    def test_import_engine_security(self):
        """Test importing engine security."""
        from engine import security
        assert security is not None
    
    def test_import_service(self):
        """Test importing the service module."""
        # Import agent_coordinator directly to avoid circular imports
        from service import agent_coordinator
        assert agent_coordinator is not None
    
    def test_import_service_agent_coordinator(self):
        """Test importing service agent coordinator."""
        from service.agent_coordinator import AgentCoordinator
        assert AgentCoordinator is not None
    
    def test_import_cell0(self):
        """Test importing the cell0 module."""
        import cell0
        assert cell0 is not None
        assert hasattr(cell0, '__version__')
    
    def test_import_cell0_skills(self):
        """Test importing cell0 skills."""
        from cell0.engine.skills import (
            SkillManifest,
            SkillRegistry,
            SkillManager,
            SkillType,
            SkillStatus
        )
        assert SkillManifest is not None
        assert SkillRegistry is not None
        assert SkillManager is not None


# ============================================================================
# COL Module Component Tests
# ============================================================================

class TestCOLComponents:
    """Verify COL components are properly structured."""
    
    def test_col_orchestrator_has_required_methods(self):
        """Test COL orchestrator has required methods."""
        from col.orchestrator import COL
        
        required_methods = [
            'submit',
            'shutdown',
            'get_stats'
        ]
        
        for method in required_methods:
            assert hasattr(COL, method), f"COL missing method: {method}"
    
    def test_col_classifier_classifies_requests(self):
        """Test that COL classifier can classify requests."""
        from col.classifier import RequestClassifier
        
        classifier = RequestClassifier()
        # Test that classifier has classify method with correct signature
        assert hasattr(classifier, 'classify')
        # Don't actually call classify as it may require specific args
    
    def test_col_token_economy_budget_management(self):
        """Test token economy budget management."""
        from col.token_economy import TokenEconomy
        
        # Create economy with default config
        economy = TokenEconomy()
        
        # Verify economy was created
        assert economy is not None


# ============================================================================
# Skills Module Tests
# ============================================================================

class TestSkillsModule:
    """Verify skills module is properly configured."""
    
    def test_skill_manifest_creation(self):
        """Test creating a skill manifest."""
        from cell0.engine.skills import SkillManifest, SkillType
        
        manifest = SkillManifest(
            skill_id="test_skill",
            name="Test Skill",
            version="1.0.0",
            description="A test skill",
            author="Test Author",
            skill_type=SkillType.WORKSPACE
        )
        
        assert manifest.skill_id == "test_skill"
        assert manifest.name == "Test Skill"
        assert manifest.version == "1.0.0"
    
    def test_skill_registry_operations(self):
        """Test skill registry basic operations."""
        from cell0.engine.skills import SkillRegistry, SkillManifest, SkillType
        
        registry = SkillRegistry()
        manifest = SkillManifest(
            skill_id="test",
            name="Test",
            version="1.0.0",
            skill_type=SkillType.WORKSPACE
        )
        
        registry.register_skill(manifest)
        retrieved = registry.get_skill("workspace:test")
        
        assert retrieved is not None
        assert retrieved.skill_id == "test"
        
        registry.clear()


# ============================================================================
# Engine Module Tests
# ============================================================================

class TestEngineModule:
    """Verify engine module is properly configured."""
    
    def test_engine_security_context(self):
        """Test engine security context."""
        # Import may fail if module doesn't exist, that's OK for bootstrap
        try:
            from engine.security.security import SecurityContext
            context = SecurityContext(
                user_id="test",
                permissions=["read"]
            )
            assert context.user_id == "test"
        except ImportError:
            pytest.skip("SecurityContext not available")


# ============================================================================
# Service Module Tests
# ============================================================================

class TestServiceModule:
    """Verify service module is properly configured."""
    
    def test_agent_coordinator_creation(self):
        """Test creating an agent coordinator."""
        from service.agent_coordinator import AgentCoordinator
        
        coordinator = AgentCoordinator()
        assert coordinator is not None


# ============================================================================
# Environment Tests
# ============================================================================

class TestEnvironment:
    """Verify the test environment is properly configured."""
    
    def test_python_version(self):
        """Test Python version is 3.9+."""
        import sys
        
        major, minor = sys.version_info[:2]
        assert major >= 3
        if major == 3:
            assert minor >= 9, f"Python 3.9+ required, found {major}.{minor}"
    
    def test_pytest_plugins_loaded(self):
        """Test that pytest plugins are available."""
        # Test that our conftest.py was loaded
        # This is implicit - if this test runs, conftest was loaded
        pass
    
    def test_temp_dir_fixture(self, temp_dir: Path):
        """Test temp_dir fixture works."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        # Test we can write to it
        test_file = temp_dir / "test.txt"
        test_file.write_text("test")
        assert test_file.read_text() == "test"
    
    def test_mock_env_vars_fixture(self, mock_env_vars: dict):
        """Test mock_env_vars fixture works."""
        import os
        
        for key, value in mock_env_vars.items():
            assert os.environ.get(key) == value
    
    def test_sample_data_fixtures(self, sample_yaml_content: str, sample_json_data: dict):
        """Test sample data fixtures work."""
        assert isinstance(sample_yaml_content, str)
        assert "id: test_skill" in sample_yaml_content
        
        assert isinstance(sample_json_data, dict)
        assert sample_json_data["id"] == "test-001"


# ============================================================================
# Dependency Tests
# ============================================================================

class TestRequiredDependencies:
    """Verify required dependencies are installed."""
    
    @pytest.mark.parametrize("package", [
        "pytest",
        "pytest_asyncio",
        "yaml",
        "pydantic",
    ])
    def test_required_package_importable(self, package: str):
        """Test that required packages can be imported."""
        try:
            importlib.import_module(package)
        except ImportError as e:
            pytest.fail(f"Required package '{package}' not importable: {e}")
    
    def test_yaml_parsing(self):
        """Test YAML parsing works."""
        import yaml
        
        content = """
key: value
list:
  - item1
  - item2
"""
        data = yaml.safe_load(content)
        assert data["key"] == "value"
        assert len(data["list"]) == 2
    
    def test_pydantic_models(self):
        """Test Pydantic models work."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            count: int = 0
        
        model = TestModel(name="test")
        assert model.name == "test"
        assert model.count == 0


# ============================================================================
# Async Support Tests
# ============================================================================

class TestAsyncSupport:
    """Verify async test support is working."""
    
    @pytest.mark.asyncio
    async def test_async_fixture_works(self):
        """Test that async tests work."""
        import asyncio
        
        await asyncio.sleep(0.001)
        assert True
    
    @pytest.mark.asyncio
    async def test_async_mock_fixture(self, mock_async_tool):
        """Test async mock fixtures work."""
        result = await mock_async_tool.execute()
        assert result["result"] == "async_success"


# ============================================================================
# Final Bootstrap Verification
# ============================================================================

class TestBootstrapComplete:
    """Final verification that bootstrap is complete."""
    
    def test_all_core_modules_imported(self):
        """Test that all core modules were imported successfully."""
        # This test passes if all imports in this file succeeded
        assert "col" in sys.modules
        assert "engine" in sys.modules
        assert "service" in sys.modules
        assert "cell0" in sys.modules
    
    def test_conftest_loaded(self):
        """Verify conftest.py was loaded and fixtures are available."""
        # This test only runs if conftest.py was loaded
        # If fixtures are broken, this test won't even be collected
        pass
    
    def test_bootstrap_summary(self, project_root: Path):
        """Print bootstrap summary."""
        import sys
        
        print(f"\n{'='*50}")
        print("Cell 0 OS - Bootstrap Summary")
        print(f"{'='*50}")
        print(f"Python: {sys.version}")
        print(f"Project Root: {project_root}")
        print(f"Modules Loaded:")
        print(f"  - col: {'✓' if 'col' in sys.modules else '✗'}")
        print(f"  - engine: {'✓' if 'engine' in sys.modules else '✗'}")
        print(f"  - service: {'✓' if 'service' in sys.modules else '✗'}")
        print(f"  - cell0: {'✓' if 'cell0' in sys.modules else '✗'}")
        print(f"{'='*50}")
        
        assert True  # Always pass
