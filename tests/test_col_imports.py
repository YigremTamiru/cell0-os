"""
Test COL (Cognitive Operating Layer) module imports.

This test verifies that all COL modules can be imported correctly
and that the public API is properly exported.

Run with: pytest tests/test_col_imports.py -v
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_col_package_import():
    """Test that the col package can be imported."""
    import col
    assert col is not None
    assert hasattr(col, '__version__')
    assert col.__version__ == "1.0.0-cell0"


def test_col_orchestrator_imports():
    """Test orchestrator module imports."""
    from col.orchestrator import (
        COL,
        OperationContext,
        OperationResult,
        OrchestratorState,
        GovernanceError,
        govern,
        get_stats,
        shutdown,
    )
    assert COL is not None
    assert OperationContext is not None
    assert OperationResult is not None
    assert OrchestratorState is not None
    assert GovernanceError is not None
    assert callable(govern)
    assert callable(get_stats)
    assert callable(shutdown)


def test_col_classifier_imports():
    """Test classifier module imports."""
    from col.classifier import (
        RequestClassifier,
        ClassificationResult,
        RequestType,
        RiskPattern,
    )
    assert RequestClassifier is not None
    assert ClassificationResult is not None
    assert RequestType is not None
    assert RiskPattern is not None


def test_col_protocol_loader_imports():
    """Test protocol_loader module imports."""
    from col.protocol_loader import (
        ProtocolLoader,
        Protocol,
        ProtocolRule,
        ProtocolPriority,
        ProtocolAction,
        ProtocolDecision,
        BaseProtocol,
    )
    assert ProtocolLoader is not None
    assert Protocol is not None
    assert ProtocolRule is not None
    assert ProtocolPriority is not None
    assert ProtocolAction is not None
    assert ProtocolDecision is not None
    assert BaseProtocol is not None


def test_col_token_economy_imports():
    """Test token_economy module imports."""
    from col.token_economy import (
        TokenEconomy,
        TokenBudget,
        TokenTransaction,
        TokenTransactionType,
        TokenEconomyConfig,
    )
    assert TokenEconomy is not None
    assert TokenBudget is not None
    assert TokenTransaction is not None
    assert TokenTransactionType is not None
    assert TokenEconomyConfig is not None


def test_col_checkpoint_imports():
    """Test checkpoint module imports."""
    from col.checkpoint import (
        CheckpointManager,
        Checkpoint,
        CheckpointPolicy,
        CheckpointError,
    )
    assert CheckpointManager is not None
    assert Checkpoint is not None
    assert CheckpointPolicy is not None
    assert CheckpointError is not None


def test_col_init_exports():
    """Test that col/__init__.py exports all public API."""
    import col
    
    # Core exports
    assert hasattr(col, 'COL')
    assert hasattr(col, 'OperationContext')
    assert hasattr(col, 'OperationResult')
    assert hasattr(col, 'OrchestratorState')
    assert hasattr(col, 'GovernanceError')
    assert hasattr(col, 'govern')
    assert hasattr(col, 'get_stats')
    assert hasattr(col, 'shutdown')
    
    # Classifier exports
    assert hasattr(col, 'RequestClassifier')
    assert hasattr(col, 'ClassificationResult')
    assert hasattr(col, 'RequestType')
    assert hasattr(col, 'RiskPattern')
    
    # Protocol exports
    assert hasattr(col, 'ProtocolLoader')
    assert hasattr(col, 'Protocol')
    assert hasattr(col, 'ProtocolRule')
    assert hasattr(col, 'ProtocolPriority')
    assert hasattr(col, 'ProtocolAction')
    assert hasattr(col, 'ProtocolDecision')
    assert hasattr(col, 'BaseProtocol')
    
    # Token economy exports
    assert hasattr(col, 'TokenEconomy')
    assert hasattr(col, 'TokenBudget')
    assert hasattr(col, 'TokenTransaction')
    assert hasattr(col, 'TokenTransactionType')
    assert hasattr(col, 'TokenEconomyConfig')
    
    # Checkpoint exports
    assert hasattr(col, 'CheckpointManager')
    assert hasattr(col, 'Checkpoint')
    assert hasattr(col, 'CheckpointPolicy')
    assert hasattr(col, 'CheckpointError')


def test_col_all_exports():
    """Test that __all__ is properly defined."""
    import col
    
    assert hasattr(col, '__all__')
    expected_exports = [
        'COL',
        'OperationContext',
        'OperationResult',
        'OrchestratorState',
        'GovernanceError',
        'govern',
        'get_stats',
        'shutdown',
        'RequestClassifier',
        'ClassificationResult',
        'RequestType',
        'RiskPattern',
        'ProtocolLoader',
        'Protocol',
        'ProtocolRule',
        'ProtocolPriority',
        'ProtocolAction',
        'ProtocolDecision',
        'BaseProtocol',
        'TokenEconomy',
        'TokenBudget',
        'TokenTransaction',
        'TokenTransactionType',
        'TokenEconomyConfig',
        'CheckpointManager',
        'Checkpoint',
        'CheckpointPolicy',
        'CheckpointError',
    ]
    
    for export in expected_exports:
        assert export in col.__all__, f"{export} not in __all__"


def test_col_singleton():
    """Test that COL is a singleton."""
    from col import COL
    
    col1 = COL()
    col2 = COL()
    
    assert col1 is col2, "COL should be a singleton"


def test_govern_decorator():
    """Test that the govern decorator works."""
    from col import govern, COL
    
    @govern(priority=5)
    def test_function():
        return "test"
    
    # Decorator should wrap the function
    assert test_function is not None


def test_demo_imports():
    """Test imports used by demo_community_launch.py."""
    # These are the imports from examples/demo_community_launch.py
    from col.orchestrator import COL, govern, get_stats
    from col.classifier import RequestClassifier, RequestType
    from col.checkpoint import CheckpointManager
    
    assert COL is not None
    assert govern is not None
    assert get_stats is not None
    assert RequestClassifier is not None
    assert RequestType is not None
    assert CheckpointManager is not None


if __name__ == "__main__":
    print("Running COL import tests...")
    
    tests = [
        test_col_package_import,
        test_col_orchestrator_imports,
        test_col_classifier_imports,
        test_col_protocol_loader_imports,
        test_col_token_economy_imports,
        test_col_checkpoint_imports,
        test_col_init_exports,
        test_col_all_exports,
        test_col_singleton,
        test_govern_decorator,
        test_demo_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("All COL import tests passed!")
