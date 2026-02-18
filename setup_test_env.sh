#!/usr/bin/env bash
# Cell 0 OS - Test Environment Setup Script (OFFLINE-CAPABLE)
# Usage: ./setup_test_env.sh [options]
# Options:
#   -f, --force      Force recreate environment
#   -n, --no-network Skip network operations (offline mode)
#   -q, --quiet      Quiet mode
#   -h, --help       Show help
#
# OFFLINE MODE:
#   This script supports true offline operation using:
#   1. Pre-existing venv with pytest (fastest)
#   2. Local wheels cache in tests/wheels/
#   3. System Python fallback (if available)

set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
FORCE=false
NO_NETWORK=false
QUIET=false
USE_SYSTEM_PYTEST=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -n|--no-network)
            NO_NETWORK=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        --use-system-pytest)
            USE_SYSTEM_PYTEST=true
            shift
            ;;
        -h|--help)
            echo "Cell 0 OS - Test Environment Setup (Offline-Capable)"
            echo ""
            echo "Usage: ./setup_test_env.sh [options]"
            echo ""
            echo "Options:"
            echo "  -f, --force           Force recreate environment"
            echo "  -n, --no-network      Skip network operations (offline mode)"
            echo "  -q, --quiet           Quiet mode"
            echo "  --use-system-pytest   Use system pytest if available"
            echo "  -h, --help            Show this help"
            echo ""
            echo "Offline Mode Support:"
            echo "  This script will try (in order):"
            echo "    1. Use existing venv with pytest"
            echo "    2. Install from local wheels cache"
            echo "    3. Use system Python with pytest"
            echo "    4. Create minimal venv (tests can use python -m pytest)"
            echo ""
            echo "Examples:"
            echo "  ./setup_test_env.sh              # Standard setup"
            echo "  ./setup_test_env.sh -f           # Force recreate"
            echo "  ./setup_test_env.sh -n           # Offline mode"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    if [[ "$QUIET" == false ]]; then
        echo -e "$1"
    fi
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Wheels cache location
WHEELS_DIR="${PROJECT_ROOT}/tests/wheels"

log "${BLUE}========================================${NC}"
log "${BLUE}  Cell 0 OS - Test Environment Setup${NC}"
log "${BLUE}  (Offline-Capable Version)${NC}"
log "${BLUE}========================================${NC}"
log ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
REQUIRED_VERSION="3.9"

if [[ -z "$PYTHON_VERSION" ]]; then
    log "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    log "${RED}✗ Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

log "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# ============================================================================
# Determine venv location
# ============================================================================

VENV_PATH="${PROJECT_ROOT}/.venv"
VENV_EXISTS=false
USING_EXISTING=false

# Check for existing working venvs
if [[ -d "${PROJECT_ROOT}/cell0/venv" ]] && [[ -f "${PROJECT_ROOT}/cell0/venv/bin/python" ]]; then
    # Check if it has pytest
    if [[ -f "${PROJECT_ROOT}/cell0/venv/bin/pytest" ]]; then
        VENV_PATH="${PROJECT_ROOT}/cell0/venv"
        VENV_EXISTS=true
        USING_EXISTING=true
        log "${GREEN}✓ Found existing venv with pytest: cell0/venv${NC}"
    fi
fi

if [[ "$USING_EXISTING" == false ]] && [[ -d "$VENV_PATH" ]] && [[ -f "$VENV_PATH/bin/python" ]]; then
    if [[ -f "$VENV_PATH/bin/pytest" ]] || [[ "$FORCE" == false ]]; then
        VENV_EXISTS=true
        if [[ -f "$VENV_PATH/bin/pytest" ]]; then
            USING_EXISTING=true
            log "${GREEN}✓ Found existing venv with pytest: .venv${NC}"
        fi
    fi
fi

# Handle force recreate
if [[ "$FORCE" == true ]] && [[ "$VENV_EXISTS" == true ]]; then
    log "${YELLOW}🔧 Force mode: Removing existing environment...${NC}"
    rm -rf "$VENV_PATH"
    VENV_EXISTS=false
    USING_EXISTING=false
fi

# Create virtual environment if needed
if [[ "$VENV_EXISTS" == false ]]; then
    log "${YELLOW}🔧 Creating virtual environment at $VENV_PATH...${NC}"
    if python3 -m venv "$VENV_PATH" 2>/dev/null; then
        log "${GREEN}✓ Virtual environment created${NC}"
    else
        log "${RED}✗ Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# ============================================================================
# Handle dependencies (offline-aware)
# ============================================================================

INSTALL_NEEDED=false
if [[ "$USING_EXISTING" == false ]] || [[ "$FORCE" == true ]]; then
    INSTALL_NEEDED=true
fi

if [[ "$INSTALL_NEEDED" == true ]]; then
    if [[ "$NO_NETWORK" == false ]]; then
        # Online mode - normal installation
        log "${YELLOW}📦 Installing dependencies (online mode)...${NC}"
        
        # Upgrade pip
        pip install --upgrade pip 2>/dev/null || {
            log "${YELLOW}⚠ pip upgrade failed, continuing...${NC}"
        }
        
        # Install requirements
        if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
            log "${BLUE}   Installing core requirements...${NC}"
            pip install -r "$PROJECT_ROOT/requirements.txt" || {
                log "${YELLOW}⚠ Some core dependencies failed${NC}"
            }
        fi
        
        if [[ -f "$PROJECT_ROOT/requirements-test.txt" ]]; then
            log "${BLUE}   Installing test requirements...${NC}"
            pip install -r "$PROJECT_ROOT/requirements-test.txt" || {
                log "${YELLOW}⚠ Some test dependencies failed${NC}"
            }
        fi
        
        log "${GREEN}✓ Dependencies installed${NC}"
        
    else
        # Offline mode - try local wheels
        log "${YELLOW}📦 Offline mode: Checking for local wheels...${NC}"
        
        WHEELS_INSTALLED=false
        if [[ -d "$WHEELS_DIR" ]]; then
            WHEEL_COUNT=$(find "$WHEELS_DIR" -name "*.whl" 2>/dev/null | wc -l)
            if [[ $WHEEL_COUNT -gt 0 ]]; then
                log "${BLUE}   Found $WHEEL_COUNT wheels in $WHEELS_DIR${NC}"
                log "${BLUE}   Installing from local wheels...${NC}"
                
                # Install from wheels with no-index
                if pip install --no-index --find-links="$WHEELS_DIR" pytest pytest-asyncio 2>/dev/null; then
                    WHEELS_INSTALLED=true
                    log "${GREEN}✓ Installed pytest from local wheels${NC}"
                else
                    log "${YELLOW}⚠ Failed to install from wheels${NC}"
                fi
            fi
        fi
        
        if [[ "$WHEELS_INSTALLED" == false ]]; then
            log "${YELLOW}⚠ No local wheels available${NC}"
            log "${YELLOW}   Tests will use system Python or python -m pytest${NC}"
        fi
    fi
fi

# ============================================================================
# Verify pytest availability (GRACEFUL - no hard fail)
# ============================================================================

PYTEST_AVAILABLE=false
PYTEST_CMD=""

log "${YELLOW}🔍 Checking pytest availability...${NC}"

# Check venv pytest
if [[ -f "$VENV_PATH/bin/pytest" ]]; then
    PYTEST_VERSION=$("$VENV_PATH/bin/pytest" --version 2>&1 | head -1)
    log "${GREEN}✓ $PYTEST_VERSION (venv)${NC}"
    PYTEST_AVAILABLE=true
    PYTEST_CMD="$VENV_PATH/bin/pytest"
# Check importable module
elif python3 -c "import pytest" 2>/dev/null; then
    PYTEST_VERSION=$(python3 -c "import pytest; print(pytest.__version__)" 2>/dev/null)
    log "${GREEN}✓ pytest $PYTEST_VERSION (module)${NC}"
    PYTEST_AVAILABLE=true
    PYTEST_CMD="python3 -m pytest"
# Check system pytest fallback
elif [[ "$USE_SYSTEM_PYTEST" == true ]] && command -v pytest &> /dev/null; then
    PYTEST_VERSION=$(pytest --version 2>&1 | head -1)
    log "${YELLOW}⚠ $PYTEST_VERSION (system fallback)${NC}"
    PYTEST_CMD="pytest"
else
    log "${YELLOW}⚠ pytest not available in venv${NC}"
    log "${YELLOW}   Tests can still run with: python -m pytest${NC}"
    log "${YELLOW}   (after pytest is installed)${NC}"
fi

# ============================================================================
# Create test results directory
# ============================================================================

mkdir -p "$PROJECT_ROOT/test-results"

# ============================================================================
# Verify imports (GRACEFUL - warn only)
# ============================================================================

log "${YELLOW}🔍 Verifying imports...${NC}"

python3 << 'EOF'
import sys
import os

project_root = os.environ.get('PROJECT_ROOT', '.')
sys.path.insert(0, project_root)

errors = []
warnings = []

# Test core imports
test_imports = [
    ('col', True),
    ('engine', True),
    ('service', True),
    ('cell0', True),
]

for module, required in test_imports:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError as e:
        if required:
            errors.append(f"{module}: {e}")
            print(f"  ✗ {module}: {e}")
        else:
            warnings.append(f"{module}: {e}")
            print(f"  ⚠ {module}: {e}")

if errors:
    print()
    print("Some imports failed - tests may be limited")
    sys.exit(0)  # Don't fail, just warn
EOF

IMPORT_CHECK=$?
if [[ $IMPORT_CHECK -eq 0 ]]; then
    log "${GREEN}✓ Import check complete${NC}"
else
    log "${YELLOW}⚠ Some imports failed (tests may be limited)${NC}"
fi

# ============================================================================
# Summary
# ============================================================================

log ""
log "${GREEN}========================================${NC}"
log "${GREEN}  ✓ Test environment ready!${NC}"
log "${GREEN}========================================${NC}"
log ""
log "Virtual environment: $VENV_PATH"
log "Python: $(python3 --version 2>&1)"
if [[ -n "$PYTEST_CMD" ]]; then
    log "Pytest: $PYTEST_CMD"
else
    log "Pytest: ${YELLOW}Not available (install with: pip install pytest)${NC}"
fi
log ""
log "To run tests:"
log "  source $VENV_PATH/bin/activate"
if [[ -n "$PYTEST_CMD" ]]; then
    log "  $PYTEST_CMD tests/"
else
    log "  pip install pytest  # Then run tests"
fi
log ""
log "Or use the test runner:"
log "  ./tests/run_tests_fixed.sh --offline"
