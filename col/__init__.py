"""
COL (Cognitive Operating Layer) - Cell 0 OS
============================================

The core governance layer that intercepts ALL operations.

Architecture: STOP → CLASSIFY → LOAD → APPLY → EXECUTE

This module provides:
- Orchestrator: Core governance engine
- Classifier: Request classification
- ProtocolLoader: Dynamic protocol loading
- TokenEconomy: Token budget management
- CheckpointManager: State persistence

Usage:
    from col import COL, govern
    
    # Govern any function
    @govern(priority=8, require_checkpoint=True)
    def my_function():
        pass
    
    # Or submit manually
    result = await COL.submit(operation)
"""

__version__ = "1.0.0-cell0"
__author__ = "Cell 0 OS"

# Core orchestrator
from .orchestrator import (
    COL,
    OperationContext,
    OperationResult,
    OrchestratorState,
    GovernanceError,
    govern,
    get_stats,
    shutdown,
)

# Classifier
from .classifier import (
    RequestClassifier,
    ClassificationResult,
    RequestType,
    RiskPattern,
)

# Protocol loader
from .protocol_loader import (
    ProtocolLoader,
    Protocol,
    ProtocolRule,
    ProtocolPriority,
    ProtocolAction,
    ProtocolDecision,
    BaseProtocol,
)

# Token economy
from .token_economy import (
    TokenEconomy,
    TokenBudget,
    TokenTransaction,
    TokenTransactionType,
    TokenEconomyConfig,
)

# Checkpoint manager
from .checkpoint import (
    CheckpointManager,
    Checkpoint,
    CheckpointPolicy,
    CheckpointError,
)

# Public API
__all__ = [
    # Core
    'COL',
    'OperationContext',
    'OperationResult',
    'OrchestratorState',
    'GovernanceError',
    'govern',
    'get_stats',
    'shutdown',
    
    # Classification
    'RequestClassifier',
    'ClassificationResult',
    'RequestType',
    'RiskPattern',
    
    # Protocols
    'ProtocolLoader',
    'Protocol',
    'ProtocolRule',
    'ProtocolPriority',
    'ProtocolAction',
    'ProtocolDecision',
    'BaseProtocol',
    
    # Token Economy
    'TokenEconomy',
    'TokenBudget',
    'TokenTransaction',
    'TokenTransactionType',
    'TokenEconomyConfig',
    
    # Checkpointing
    'CheckpointManager',
    'Checkpoint',
    'CheckpointPolicy',
    'CheckpointError',
]

# Module version info
def get_version():
    """Get COL module version."""
    return __version__

def get_info():
    """Get COL module information."""
    return {
        'version': __version__,
        'architecture': 'STOP → CLASSIFY → LOAD → APPLY → EXECUTE',
        'components': [
            'orchestrator',
            'classifier',
            'protocol_loader',
            'token_economy',
            'checkpoint'
        ]
    }