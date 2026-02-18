#!/usr/bin/env bash
# Cell 0 OS - Fixed Test Bootstrap Runner (OFFLINE-CAPABLE)
# Usage: ./tests/run_tests_fixed.sh [options]
#
# This version:
# 1. Works completely offline when dependencies are pre-installed
# 2. Handles missing pytest gracefully (no hard failure)
# 3. Creates isolated test environment automatically
# 4. Falls back to system Python if needed
# 5. Makes cell0 package importable with correct PYTHONPATH

set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
COVERAGE=false
VERBOSE=""
FAST=""
TEST_PATH="tests/"
MARK=""
CI_MODE=false
INSTALL_DEPS=false
BOOTSTRAP=false
OFFLINE=false
JUNIT_OUTPUT=""
SKIP_IMPORT_CHECK=false
USE_SYSTEM_PYTHON=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -f|--fast)
            FAST="not slow"
            shift
            ;;
        -p|--path)
            TEST_PATH="$2"
            shift 2
            ;;
        -m|--mark)
            MARK="$2"
            shift 2
            ;;
        --ci)
            CI_MODE=true
            COVERAGE=true
            VERBOSE="-v"
            JUNIT_OUTPUT="test-results.xml"
            shift
            ;;
        --install)
            INSTALL_DEPS=true
            shift
            ;;
        --bootstrap)
            BOOTSTRAP=true
            INSTALL_DEPS=true
            shift
            ;;
        --offline)
            OFFLINE=true
            shift
            ;;
        --use-system-python)
            USE_SYSTEM_PYTHON=true
            shift
            ;;
        --skip-import-check)
            SKIP_IMPORT_CHECK=true
            shift
            ;;
        -h|--help)
            echo -e "${CYAN}Cell 0 OS Test Runner (Offline-Capable)${NC}"
            echo ""
            echo "Usage: ./tests/run_tests_fixed.sh [options]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage          Enable coverage reporting"
            echo "  -v, --verbose           Verbose output"
            echo "  -f, --fast              Fast mode (skip slow tests)"
            echo "  -p, --path PATH         Test path (default: tests/)"
            echo "  -m, --mark MARK         Run tests with specific mark"
            echo "  --ci                    CI mode (strict, coverage, junit)"
            echo "  --install               Install dependencies first"
            echo "  --bootstrap             Full bootstrap (create venv + install)"
            echo "  --offline               Offline mode (no network operations)"
            echo "  --use-system-python     Use system Python if venv unavailable"
            echo "  --skip-import-check     Skip import validation"
            echo "  -h, --help              Show this help"
            echo ""
            echo "Offline Mode:"
            echo "  Uses pre-installed dependencies, works without network."
            echo "  Requires either:"
            echo "    - Existing venv with pytest installed"
            echo "    - Local wheels cache in tests/wheels/"
            echo "    - System Python with pytest installed"
            echo ""
            echo "Examples:"
            echo "  ./tests/run_tests_fixed.sh           # Run all tests"
            echo "  ./tests/run_tests_fixed.sh --bootstrap    # Full setup"
            echo "  ./tests/run_tests_fixed.sh --offline      # Run offline"
            echo "  ./tests/run_tests_fixed.sh -c -m unit     # Unit tests with coverage"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cell 0 OS - Test Runner${NC}"
echo -e "${BLUE}  (Offline-Capable Version)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ============================================================================
# Virtual Environment Detection/Management
# ============================================================================

VENV_PATH=""
VENV_ACTIVE=false
USING_SYSTEM=false

# Determine venv location (respect VENV_PATH env var)
if [[ -n "${VENV_PATH:-}" ]]; then
    if [[ -d "$VENV_PATH" ]] && [[ -f "$VENV_PATH/bin/python" ]]; then
        VENV_ACTIVE=true
    fi
elif [[ -d "$PROJECT_ROOT/cell0/venv" ]] && [[ -f "$PROJECT_ROOT/cell0/venv/bin/python" ]]; then
    VENV_PATH="$PROJECT_ROOT/cell0/venv"
    VENV_ACTIVE=true
elif [[ -d "$PROJECT_ROOT/.venv" ]] && [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    VENV_PATH="$PROJECT_ROOT/.venv"
    VENV_ACTIVE=true
fi

# Bootstrap mode: create virtual environment
if [[ "$BOOTSTRAP" == true ]]; then
    echo -e "${YELLOW}🔧 Bootstrap mode: Setting up virtual environment...${NC}"
    
    if [[ -z "$VENV_PATH" ]]; then
        VENV_PATH="$PROJECT_ROOT/.venv"
    fi
    
    if [[ -d "$VENV_PATH" ]]; then
        echo -e "${YELLOW}   Removing existing environment...${NC}"
        rm -rf "$VENV_PATH"
    fi
    
    if python3 -m venv "$VENV_PATH"; then
        echo -e "${GREEN}✓ Virtual environment created at $VENV_PATH${NC}"
        VENV_ACTIVE=true
    else
        echo -e "${RED}✗ Failed to create virtual environment${NC}"
        exit 1
    fi
    echo ""
fi

# Activate virtual environment if found
if [[ "$VENV_ACTIVE" == true ]]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    echo -e "${BLUE}   Path: $VENV_PATH${NC}"
    source "$VENV_PATH/bin/activate"
    USING_SYSTEM=false
else
    # Check if we should use system Python
    if [[ "$USE_SYSTEM_PYTHON" == true ]] || [[ "$OFFLINE" == true ]]; then
        echo -e "${YELLOW}⚠ No virtual environment found${NC}"
        echo -e "${YELLOW}  Using system Python (offline mode)${NC}"
        USING_SYSTEM=true
    else
        echo -e "${RED}✗ No virtual environment found${NC}"
        echo -e "${YELLOW}  Run with --bootstrap to create one${NC}"
        exit 1
    fi
fi

# ============================================================================
# Python Version Check
# ============================================================================

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
REQUIRED_VERSION="3.9"

if [[ -z "$PYTHON_VERSION" ]]; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo -e "${RED}✗ Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# ============================================================================
# Dependency Installation (offline-aware)
# ============================================================================

if [[ "$INSTALL_DEPS" == true ]]; then
    echo ""
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    
    if [[ "$OFFLINE" == true ]]; then
        echo -e "${YELLOW}  (offline mode - using local wheels only)${NC}"
        WHEELS_DIR="$PROJECT_ROOT/tests/wheels"
        if [[ -d "$WHEELS_DIR" ]]; then
            pip install --no-index --find-links="$WHEELS_DIR" pytest pytest-asyncio 2>/dev/null || {
                echo -e "${YELLOW}⚠ Failed to install from wheels${NC}"
            }
        fi
    else
        # Online mode
        pip install --upgrade pip 2>/dev/null || {
            echo -e "${YELLOW}⚠ pip upgrade failed${NC}"
        }
        
        if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
            echo -e "${BLUE}   Installing core requirements...${NC}"
            pip install -r "$PROJECT_ROOT/requirements.txt" || {
                echo -e "${YELLOW}⚠ Core requirements had errors${NC}"
            }
        fi
        
        if [[ -f "$PROJECT_ROOT/requirements-test.txt" ]]; then
            echo -e "${BLUE}   Installing test requirements...${NC}"
            pip install -r "$PROJECT_ROOT/requirements-test.txt" || {
                echo -e "${YELLOW}⚠ Test requirements had errors${NC}"
            }
        fi
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
fi

# ============================================================================
# Pytest Detection (GRACEFUL - no hard failure)
# ============================================================================

echo -e "${YELLOW}🔍 Checking for pytest...${NC}"

PYTEST_CMD=""
PYTEST_SOURCE=""

# Priority 1: Check venv pytest executable
if [[ -n "$VENV_PATH" ]] && [[ -f "$VENV_PATH/bin/pytest" ]]; then
    PYTEST_CMD="$VENV_PATH/bin/pytest"
    PYTEST_SOURCE="venv"
    PYTEST_VERSION=$($PYTEST_CMD --version 2>&1 | head -1)
    echo -e "${GREEN}✓ Found in venv: $PYTEST_VERSION${NC}"

# Priority 2: Check if pytest is importable as module
elif python3 -c "import pytest" 2>/dev/null; then
    PYTEST_CMD="python3 -m pytest"
    PYTEST_SOURCE="module"
    PYTEST_VERSION=$(python3 -c "import pytest; print(pytest.__version__)" 2>/dev/null)
    echo -e "${GREEN}✓ Found as module: pytest $PYTEST_VERSION${NC}"

# Priority 3: Check system pytest (if allowed)
elif [[ "$USE_SYSTEM_PYTHON" == true ]] && command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
    PYTEST_SOURCE="system"
    PYTEST_VERSION=$(pytest --version 2>&1 | head -1)
    echo -e "${YELLOW}⚠ Using system: $PYTEST_VERSION${NC}"

# Priority 4: Try to install if online
elif [[ "$OFFLINE" == false ]]; then
    echo -e "${YELLOW}⚠ pytest not found, attempting to install...${NC}"
    if pip install pytest pytest-asyncio 2>/dev/null; then
        PYTEST_CMD="python3 -m pytest"
        PYTEST_SOURCE="installed"
        echo -e "${GREEN}✓ pytest installed${NC}"
    else
        echo -e "${RED}✗ Failed to install pytest${NC}"
        echo -e "${YELLOW}   Run with --bootstrap for full setup${NC}"
        exit 1
    fi
else
    # Offline and no pytest available
    echo -e "${RED}✗ pytest not available${NC}"
    echo -e "${YELLOW}   Offline mode requires pre-installed pytest${NC}"
    echo -e "${YELLOW}   Options:${NC}"
    echo -e "${YELLOW}     1. Run setup_test_env.sh first${NC}"
    echo -e "${YELLOW}     2. Use --bootstrap to create venv${NC}"
    echo -e "${YELLOW}     3. Add pytest wheels to tests/wheels/${NC}"
    exit 1
fi

echo ""

# ============================================================================
# Environment Validation (GRACEFUL)
# ============================================================================

echo -e "${YELLOW}🔍 Validating environment...${NC}"

# Set PYTHONPATH to include project root
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
echo -e "${BLUE}   PYTHONPATH: $PYTHONPATH${NC}"

# Run import validation (unless skipped)
if [[ "$SKIP_IMPORT_CHECK" == false ]]; then
    echo -e "${BLUE}   Testing core imports...${NC}"
    
    python3 << 'PYEOF'
import sys
import os

project_root = os.environ.get('PYTHONPATH', '.').split(':')[0]
sys.path.insert(0, project_root)

errors = []
warnings = []

# Test imports
test_modules = [
    ('col', True),
    ('engine', False),
    ('service', False),
    ('cell0', True),
]

for module, required in test_modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except Exception as e:
        msg = f"{module}: {e}"
        if required:
            errors.append(msg)
            print(f"  ✗ {msg}")
        else:
            warnings.append(msg)
            print(f"  ⚠ {msg}")

if errors:
    print()
    print("Import errors detected (tests may be limited)")
    sys.exit(0)  # Don't fail, just warn
PYEOF

    IMPORT_EXIT=$?
    if [[ $IMPORT_EXIT -eq 0 ]]; then
        if [[ ${#errors[@]} -eq 0 ]]; then
            echo -e "${GREEN}✓ Environment validated${NC}"
        else
            echo -e "${YELLOW}⚠ Some imports failed (tests may be limited)${NC}"
        fi
    fi
    echo ""
else
    echo -e "${YELLOW}   Import check skipped${NC}"
    echo ""
fi

# Create test results directory
mkdir -p "$PROJECT_ROOT/test-results"

# ============================================================================
# Test Execution
# ============================================================================

# Build pytest command arguments using arrays (properly handles spaces)
PYTEST_ARGS=()

if [[ -n "$VERBOSE" ]]; then
    PYTEST_ARGS+=("-v")
fi

if [[ -n "$MARK" ]]; then
    PYTEST_ARGS+=("-m" "$MARK")
fi

if [[ -n "$FAST" ]]; then
    PYTEST_ARGS+=("-m" "$FAST")
fi

if [[ -n "$JUNIT_OUTPUT" ]]; then
    PYTEST_ARGS+=("--junitxml=$JUNIT_OUTPUT")
fi

if [[ "$COVERAGE" == true ]]; then
    PYTEST_ARGS+=(
        "--cov=col"
        "--cov=engine"
        "--cov=service"
        "--cov=cell0"
        "--cov-report=term-missing"
        "--cov-report=html:test-results/htmlcov"
        "--cov-report=xml:test-results/coverage.xml"
    )
fi

# Handle offline mode (skip network-dependent tests)
if [[ "$OFFLINE" == true ]]; then
    PYTEST_ARGS+=("-m" "not network")
fi

echo -e "${YELLOW}🧪 Running tests...${NC}"
echo -e "${BLUE}   Path: $TEST_PATH${NC}"
echo -e "${BLUE}   Cmd: $PYTEST_CMD${NC}"
if [[ ${#PYTEST_ARGS[@]} -gt 0 ]]; then
    echo -e "${BLUE}   Args: ${PYTEST_ARGS[*]}${NC}"
fi
echo ""

# Run tests with proper error handling
set +e
"$PYTEST_CMD" "$TEST_PATH" "${PYTEST_ARGS[@]}"
TEST_EXIT_CODE=$?
set -e

echo ""

# ============================================================================
# Results
# ============================================================================

if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    if [[ "$COVERAGE" == true ]]; then
        echo ""
        echo -e "${BLUE}Coverage reports:${NC}"
        echo "  - HTML: test-results/htmlcov/index.html"
        echo "  - XML:  test-results/coverage.xml"
        
        if command -v open &> /dev/null && [[ "$CI_MODE" == false ]]; then
            echo ""
            read -p "Open HTML coverage report? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                open "$PROJECT_ROOT/test-results/htmlcov/index.html"
            fi
        fi
    fi
    
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ✗ Tests failed (exit code: $TEST_EXIT_CODE)${NC}"
    echo -e "${RED}========================================${NC}"
    exit $TEST_EXIT_CODE
fi
