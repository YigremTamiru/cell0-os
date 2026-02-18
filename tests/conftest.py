"""
Cell 0 OS - PyTest Configuration and Fixtures

This file is automatically loaded by pytest and provides:
1. Test fixtures for common objects
2. Test configuration
3. Shared utilities
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

import pytest
import pytest_asyncio

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "security: marks tests as security-related")
    config.addinivalue_line("markers", "requires_env(name): marks tests requiring specific env vars")


def pytest_collection_modifyitems(config, items):
    """Modify test collection - add markers based on test location."""
    for item in items:
        # Auto-mark tests based on path
        if "/integration/" in str(item.path):
            item.add_marker(pytest.mark.integration)
        elif "/unit/" in str(item.path):
            item.add_marker(pytest.mark.unit)
        
        # Auto-mark slow tests
        if "stress" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)


# ============================================================================
# Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def temp_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary file for tests."""
    file_path = temp_dir / "test_file.txt"
    yield file_path


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def clean_env():
    """Provide a clean environment by temporarily clearing specific env vars."""
    preserved_vars = [
        "PATH", "HOME", "USER", "SHELL", "LANG",
        "PYTHONPATH", "VIRTUAL_ENV"
    ]
    
    old_env = os.environ.copy()
    
    # Clear all non-essential env vars
    for key in list(os.environ.keys()):
        if key not in preserved_vars:
            del os.environ[key]
    
    yield os.environ
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch):
    """Set common mock environment variables for testing."""
    env_vars = {
        "CELL0_ENV": "test",
        "CELL0_LOG_LEVEL": "DEBUG",
        "CELL0_DATA_DIR": str(PROJECT_ROOT / "test-results" / "data"),
        "CELL0_CONFIG_DIR": str(PROJECT_ROOT / "test-results" / "config"),
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


# ============================================================================
# COL Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def col_orchestrator():
    """Create a fresh COL orchestrator instance."""
    from col.orchestrator import COL, OrchestratorState
    
    # Reset orchestrator state
    COL.state = OrchestratorState.IDLE
    COL._operation_queue.clear()
    COL._results.clear()
    
    yield COL
    
    # Cleanup
    asyncio.run(COL.shutdown())


@pytest.fixture(scope="function")
def col_classifier():
    """Create a COL classifier instance."""
    from col.classifier import RequestClassifier
    return RequestClassifier()


@pytest.fixture(scope="function")
def token_economy():
    """Create a token economy instance."""
    from col.token_economy import TokenEconomy, TokenEconomyConfig
    
    config = TokenEconomyConfig(
        default_budget=1000,
        max_transaction=100
    )
    
    return TokenEconomy(config)


# ============================================================================
# Engine Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def skill_registry():
    """Create a fresh skill registry."""
    from cell0.engine.skills import SkillRegistry
    
    registry = SkillRegistry()
    yield registry
    registry.clear()


@pytest.fixture(scope="function")
def skill_manager(temp_dir: Path):
    """Create a skill manager with temporary directories."""
    from cell0.engine.skills import SkillManager
    
    manager = SkillManager(
        system_path=temp_dir / "system",
        workspace_path=temp_dir / "workspace",
        installed_path=temp_dir / "installed",
        auto_discover=False
    )
    
    yield manager
    
    # Cleanup
    asyncio.run(manager.shutdown())


@pytest.fixture(scope="function")
def sample_skill_manifest():
    """Create a sample skill manifest for testing."""
    from cell0.engine.skills import SkillManifest, SkillType
    
    return SkillManifest(
        skill_id="test_skill",
        name="Test Skill",
        version="1.0.0",
        description="A test skill for unit testing",
        author="Test Author",
        skill_type=SkillType.WORKSPACE
    )


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def agent_coordinator():
    """Create an agent coordinator instance."""
    from service.agent_coordinator import AgentCoordinator
    return AgentCoordinator()


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_tool():
    """Create a mock tool for testing."""
    tool = MagicMock()
    tool.name = "mock_tool"
    tool.description = "A mock tool for testing"
    tool.execute = MagicMock(return_value={"result": "success"})
    return tool


@pytest.fixture(scope="function")
def mock_async_tool():
    """Create a mock async tool for testing."""
    tool = MagicMock()
    tool.name = "mock_async_tool"
    tool.description = "A mock async tool for testing"
    tool.execute = AsyncMock(return_value={"result": "async_success"})
    return tool


@pytest.fixture(scope="function")
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock()
    agent.id = "test-agent-001"
    agent.name = "Test Agent"
    agent.run = AsyncMock(return_value={"status": "completed", "result": "test_result"})
    return agent


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def sample_yaml_content() -> str:
    """Return sample YAML content for testing."""
    return """
id: test_skill
name: Test Skill
version: 1.0.0
description: A test skill
author: Test Author
type: workspace

tools:
  - name: test_tool
    module: test_module
    function: test_function
    description: A test tool

commands:
  - name: test-cmd
    module: test_module
    function: test_command
    description: A test command
"""


@pytest.fixture(scope="function")
def sample_json_data() -> dict:
    """Return sample JSON data for testing."""
    return {
        "id": "test-001",
        "name": "Test Object",
        "version": "1.0.0",
        "metadata": {
            "created": "2024-01-01T00:00:00Z",
            "author": "Test"
        },
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
    }


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def async_temp_dir() -> AsyncGenerator[Path, None]:
    """Create a temporary directory for async tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest_asyncio.fixture(scope="function")
async def websocket_client():
    """Create a mock WebSocket client for testing."""
    client = AsyncMock()
    client.send = AsyncMock()
    client.recv = AsyncMock(return_value='{"type": "test"}')
    client.close = AsyncMock()
    return client


# ============================================================================
# Security Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def security_context():
    """Create a security context for testing."""
    from cell0.engine.security import SecurityContext
    
    return SecurityContext(
        user_id="test-user",
        permissions=["read", "write"],
        session_id="test-session-001"
    )
