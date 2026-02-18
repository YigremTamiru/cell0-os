"""
Cell 0 OS - Sovereign Edge Model Operating System

Cell 0 is a production-ready edge AI operating system with:
- Multi-agent coordination
- Local LLM inference (Ollama, MLX)
- Real-time WebSocket gateway
- Prometheus metrics and health checks
- Comprehensive security and rate limiting
"""

__version__ = "1.2.0"
__author__ = "Vael Zaru'Tahl Xeth (Yige)"
__license__ = "GPL-3.0"

from pathlib import Path

# Cell 0 paths
CELL0_HOME = Path.home() / "cell0"
CELL0_STATE_DIR = Path.home() / ".cell0"

# Ensure directories exist
CELL0_STATE_DIR.mkdir(parents=True, exist_ok=True)
(CELL0_STATE_DIR / "logs").mkdir(exist_ok=True)
(CELL0_STATE_DIR / "config").mkdir(exist_ok=True)
