"""
Pytest configuration for Cell 0 tests
"""

import sys
import os

# Add project root to Python path (parent of tests/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Also add parent directory so cell0 can be found as package
PARENT_DIR = os.path.dirname(PROJECT_ROOT)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Verify path setup
print(f"Python path configured:", file=sys.stderr)
for i, p in enumerate(sys.path[:3]):
    print(f"  [{i}] {p}", file=sys.stderr)

# Import check
try:
    import cell0
    print(f"Cell0 package found: {cell0.__file__}", file=sys.stderr)
except ImportError as e:
    print(f"Warning: Could not import cell0: {e}", file=sys.stderr)

# Pytest hooks
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "slow: mark test as slow")


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers based on test location
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)


import pytest
