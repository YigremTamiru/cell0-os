"""
Cell 0 OS Test Runner - Run tests directly
"""

import sys
import os
from pathlib import Path

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Now run pytest with proper path
import pytest

if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/unit/test_monitoring.py", "-v", "--tb=short"]
    sys.exit(pytest.main(args))
