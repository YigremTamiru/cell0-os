#!/bin/bash
# Cell 0 OS - Start Script
# Quick start for local development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [[ ! -d "venv" ]]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

source venv/bin/activate

# Start Ollama if available and not running
if command -v ollama &> /dev/null; then
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "Starting Ollama..."
        ollama serve &
        OLLAMA_PID=$!
        sleep 2
    fi
fi

# Set environment
export CELL0_HOME="$SCRIPT_DIR"
export CELL0_STATE_DIR="$HOME/.cell0"
export CELL0_ENV="development"
export PYTHONPATH="$SCRIPT_DIR"

echo "Starting Cell 0 OS..."
echo "  API: http://localhost:18800"
echo "  WS:  ws://localhost:18801"
echo "  Press Ctrl+C to stop"
echo ""

# Start the daemon
exec python cell0d.py "$@"
