#!/bin/bash
# Cell 0 OS - Quick Setup Script
# For developers who already have the repository cloned

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}[INFO]${NC} Cell 0 OS Quick Setup"
echo ""

# Detect Python
if command -v python3.11 &> /dev/null; then
    PYTHON="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    echo "Error: Python 3 not found"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Using Python: $PYTHON ($($PYTHON --version))"

# Create virtual environment
echo -e "${BLUE}[INFO]${NC} Creating virtual environment..."
$PYTHON -m venv venv
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}[INFO]${NC} Upgrading pip..."
pip install --quiet --upgrade pip setuptools wheel

# Install Cell 0
echo -e "${BLUE}[INFO]${NC} Installing Cell 0 OS..."
pip install --quiet -e ".[dev]"

# Create state directory
echo -e "${BLUE}[INFO]${NC} Creating state directory..."
mkdir -p "$HOME/.cell0"/{data,logs,config,backups,temp}

# Run diagnostics
echo ""
echo -e "${BLUE}[INFO]${NC} Running diagnostics..."
python scripts/cell0-doctor.py --quick || true

echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Quick start commands:"
echo "  ./start.sh              # Start Cell 0 daemon"
echo "  python cell0ctl.py      # CLI management"
echo "  python -m pytest tests/ # Run tests"
echo ""
