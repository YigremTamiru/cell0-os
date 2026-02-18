import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add cell0 to path
cell0_path = project_root / "cell0"
if cell0_path.exists():
    sys.path.insert(0, str(cell0_path))

# Set environment
os.environ["CELL0_ENV"] = "testing"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-ci-only"
