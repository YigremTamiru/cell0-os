"""
COL-Continuity Module

Temporal state persistence for Cell 0 OS.
Ensures sessions are continuous across restarts.

Usage:
    from col.continuity import CheckpointManager, StateRestorer
    
    # Create checkpoint manager
    manager = CheckpointManager(storage_path=".col/continuity")
    
    # Register state provider
    manager.register_state_provider(get_current_state)
    
    # Start auto-checkpointing
    await manager.start_auto_checkpointing()
    
    # On session start, restore state
    restorer = StateRestorer(manager)
    result = await restorer.restore_latest()
    
    if result.status == RestorationStatus.SUCCESS:
        print(f"Restored {len(result.restored_keys)} state keys")
"""

from col.continuity.checkpoint import (
    CheckpointManager,
    CheckpointMetadata,
    CheckpointStatus,
    CheckpointType,
)
from col.continuity.serializer import (
    StateSerializer,
    SerializedState,
    SerializationFormat,
    CompressionAlgorithm,
    EncryptionAlgorithm,
)
from col.continuity.persistence import (
    PersistenceBackend,
    StorageBackend,
    FileSystemBackend,
    SQLiteBackend,
    HybridBackend,
    StorageConfig,
)
from col.continuity.restore import (
    StateRestorer,
    RestorationResult,
    RestorationStatus,
    TemporalCoherenceManager,
    TemporalCoherenceError,
)
from col.continuity.merger import (
    StateMerger,
    ConflictResolver,
    Conflict,
    ConflictType,
    MergeStrategy,
    MergeResult,
)

__all__ = [
    # Checkpoint
    "CheckpointManager",
    "CheckpointMetadata",
    "CheckpointStatus",
    "CheckpointType",
    # Serializer
    "StateSerializer",
    "SerializedState",
    "SerializationFormat",
    "CompressionAlgorithm",
    "EncryptionAlgorithm",
    # Persistence
    "PersistenceBackend",
    "StorageBackend",
    "FileSystemBackend",
    "SQLiteBackend",
    "HybridBackend",
    "StorageConfig",
    # Restore
    "StateRestorer",
    "RestorationResult",
    "RestorationStatus",
    "TemporalCoherenceManager",
    "TemporalCoherenceError",
    # Merger
    "StateMerger",
    "ConflictResolver",
    "Conflict",
    "ConflictType",
    "MergeStrategy",
    "MergeResult",
]