#!/usr/bin/env bash
# Cell 0 OS - Test Bootstrap Runner
# Usage: ./tests/run_tests.sh [options]
# Options:
#   -c, --coverage     Enable coverage reporting
#   -v, --verbose      Verbose output
#   -f, --fast         Fast mode (skip slow tests)
#   -p, --path PATH    Test path (default: tests/)
#   -m, --mark MARK    Run tests with specific mark
#   --ci               CI mode (strict, coverage, junit)
#   --install          Install dependencies first
#   --bootstrap        Full bootstrap (create venv + install)
#   -h, --help         Show help

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
JUNIT_OUTPUT=""

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
            FAST="-m 'not slow'"
            shift
            ;;
        -p|--path)
            TEST_PATH="$2"
            shift 2
            ;;
        -m|--mark)
            MARK="-m $2"
            shift 2
            ;;
        --ci)
            CI_MODE=true
            COVERAGE=true
            VERBOSE="-v"
            JUNIT_OUTPUT="--junitxml=test-results.xml"
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
        -h|--help)
            echo "Cell 0 OS Test Runner"
            echo ""
            echo "Usage: ./tests/run_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage     Enable coverage reporting"
            echo "  -v, --verbose      Verbose output"
            echo "  -f, --fast         Fast mode (skip slow tests)"
            echo "  -p, --path PATH    Test path (default: tests/)"
            echo "  -m, --mark MARK    Run tests with specific mark"
            echo "  --ci               CI mode (strict, coverage, junit output)"
            echo "  --install          Install dependencies first"
            echo "  --bootstrap        Full bootstrap (create venv + install)"
            echo "  -h, --help         Show this help"
            echo ""
            echo "Examples:"
            echo "  ./tests/run_tests.sh                    # Run all tests"
            echo "  ./tests/run_tests.sh -c                 # Run with coverage"
            echo "  ./tests/run_tests.sh -p tests/unit      # Run specific path"
            echo "  ./tests/run_tests.sh -m integration     # Run integration tests"
            echo "  ./tests/run_tests.sh --ci               # CI mode"
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
echo -e "${BLUE}  Cell 0 OS - Test Bootstrap${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Bootstrap mode: create virtual environment
if [[ "$BOOTSTRAP" == true ]]; then
    echo -e "${YELLOW}🔧 Bootstrap mode: Creating virtual environment...${NC}"
    
    if [[ -d "$PROJECT_ROOT/.venv" ]]; then
        echo -e "${YELLOW}   Virtual environment exists, removing...${NC}"
        rm -rf "$PROJECT_ROOT/.venv"
    fi
    
    python3 -m venv "$PROJECT_ROOT/.venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
    echo ""
fi

# Activate virtual environment if it exists
if [[ -d "$PROJECT_ROOT/.venv" ]]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
REQUIRED_VERSION="3.9"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo -e "${RED}✗ Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Install dependencies
if [[ "$INSTALL_DEPS" == true ]]; then
    echo ""
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    
    pip install --upgrade pip
    
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        echo -e "${BLUE}   Installing core requirements...${NC}"
        pip install -r "$PROJECT_ROOT/requirements.txt"
    fi
    
    if [[ -f "$PROJECT_ROOT/requirements-test.txt" ]]; then
        echo -e "${BLUE}   Installing test requirements...${NC}"
        pip install -r "$PROJECT_ROOT/requirements-test.txt"
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
fi

# Environment validation
echo -e "${YELLOW}🔍 Validating environment...${NC}"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found. Run with --install flag.${NC}"
    exit 1
fi

# Validate imports work
echo -e "${BLUE}   Testing core imports...${NC}"
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')

errors = []

# Test COL imports
try:
    import col
    print('  ✓ col')
except Exception as e:
    errors.append(f'col: {e}')
    print(f'  ✗ col: {e}')

# Test engine imports
try:
    import engine
    print('  ✓ engine')
except Exception as e:
    errors.append(f'engine: {e}')
    print(f'  ✗ engine: {e}')

# Test service imports
try:
    import service
    print('  ✓ service')
except Exception as e:
    errors.append(f'service: {e}')
    print(f'  ✗ service: {e}')

# Test cell0 imports
try:
    import cell0
    print('  ✓ cell0')
except Exception as e:
    errors.append(f'cell0: {e}')
    print(f'  ✗ cell0: {e}')

if errors:
    print()
    print('Import errors detected. Some tests may fail.')
    sys.exit(1)
" || {
    echo -e "${RED}✗ Import validation failed${NC}"
    echo "  Run with --install to fix dependencies"
    exit 1
}

echo -e "${GREEN}✓ Environment validated${NC}"
echo ""

# Create test results directory
mkdir -p "$PROJECT_ROOT/test-results"

# Build pytest command
PYTEST_ARGS="$VERBOSE $MARK $FAST $JUNIT_OUTPUT"

if [[ "$COVERAGE" == true ]]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=col --cov=engine --cov=service --cov=cell0 --cov-report=term-missing --cov-report=html:test-results/htmlcov --cov-report=xml:test-results/coverage.xml"
fi

# Set PYTHONPATH for tests
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

echo -e "${YELLOW}🧪 Running tests...${NC}"
echo -e "${BLUE}   Path: $TEST_PATH${NC}"
echo -e "${BLUE}   Args: $PYTEST_ARGS${NC}"
echo ""

# Run tests
if pytest "$TEST_PATH" $PYTEST_ARGS; then
    echo ""
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
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ✗ Tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
