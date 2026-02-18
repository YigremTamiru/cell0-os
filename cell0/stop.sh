#!/bin/bash
# Cell 0 OS - Stop Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stop using cell0ctl if available
if [[ -f "$SCRIPT_DIR/venv/bin/python" ]]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    python "$SCRIPT_DIR/cell0ctl.py" stop || true
fi

# Kill any remaining cell0d processes
pkill -f "cell0d.py" 2>/dev/null || true

echo "Cell 0 OS stopped."
