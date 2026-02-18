"""
Cell 0 Engine Module

Core engine components for Cell 0 OS.
"""

from pathlib import Path

ENGINE_ROOT = Path(__file__).parent

# Export engine modules
# Only import modules that exist
from . import security
from . import monitoring

# Optional modules with graceful fallback
try:
    from . import ai_engine
    from .ai_engine import (
        AIEngine,
        ModelConfig,
        ModelPrecision,
        TPVResonance,
        InferenceResult,
        get_ai_engine,
    )
    HAS_AI_ENGINE = True
except ImportError as e:
    HAS_AI_ENGINE = False

try:
    from . import mlx_bridge
    HAS_MLX_BRIDGE = True
except ImportError:
    HAS_MLX_BRIDGE = False
