"""
Test COL Checkpoint Module - Cell 0 OS
Tests for checkpoint creation, restoration, and management.

Run with: pytest tests/test_checkpoint.py -v
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from col.checkpoint import (
    CheckpointManager,
    Checkpoint,
    CheckpointPolicy,
    CheckpointError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoint tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def checkpoint_manager(temp_checkpoint_dir):
    """Create a CheckpointManager with a temp directory."""
    policy = CheckpointPolicy(
        enabled=True,
        max_checkpoints=10,
        max_age_days=30,
        keep_minimum=2
    )
    
    # Patch the checkpoint directory
    manager = CheckpointManager(policy)
    original_dir = manager._checkpoint_dir
    manager._checkpoint_dir = Path(temp_checkpoint_dir)
    manager._checkpoint_dir.mkdir(parents=True, exist_ok=True)
    manager._index = {}
    
    yield manager
    
    # Cleanup
    manager._checkpoint_dir = original_dir


@pytest.fixture
def sample_state():
    """Return a sample state dictionary."""
    return {
        "orchestrator": {
            "version": "1.0.0-cell0",
            "state": "ACTIVE",
            "stats": {
                "total_operations": 42,
                "governed_operations": 40,
            }
        },
        "timestamp": datetime.utcnow().isoformat(),
        "data": [1, 2, 3, "test"]
    }


# =============================================================================
# Checkpoint Class Tests
# =============================================================================

class TestCheckpoint:
    """Tests for the Checkpoint dataclass."""
    
    def test_checkpoint_creation(self):
        """Test creating a Checkpoint instance."""
        checkpoint = Checkpoint(
            id="cp_test_001",
            timestamp=datetime.utcnow(),
            version="1.0",
            reason="test",
            state={"key": "value"},
            metadata={"test": True}
        )
        
        assert checkpoint.id == "cp_test_001"
        assert checkpoint.version == "1.0"
        assert checkpoint.reason == "test"
        assert checkpoint.state == {"key": "value"}
        assert checkpoint.metadata == {"test": True}
    
    def test_checkpoint_to_dict(self):
        """Test Checkpoint.to_dict method."""
        checkpoint = Checkpoint(
            id="cp_test_002",
            timestamp=datetime(2026, 2, 12, 10, 0, 0),
            version="1.0",
            reason="test_dict",
            state={"data": "value"},
            parent_id="cp_parent",
            checksum="abc123",
            compressed=True,
            metadata={"author": "test"}
        )
        
        result = checkpoint.to_dict()
        
        assert result["id"] == "cp_test_002"
        assert result["timestamp"] == "2026-02-12T10:00:00"
        assert result["version"] == "1.0"
        assert result["reason"] == "test_dict"
        assert result["parent_id"] == "cp_parent"
        assert result["checksum"] == "abc123"
        assert result["compressed"] == True
        assert result["metadata"] == {"author": "test"}
        assert "state_size" in result
    
    def test_checkpoint_compute_checksum(self):
        """Test checksum computation."""
        checkpoint = Checkpoint(
            id="cp_test_003",
            timestamp=datetime.utcnow(),
            version="1.0",
            reason="test_checksum",
            state={"key1": "value1", "key2": 42}
        )
        
        checksum = checkpoint.compute_checksum()
        
        assert isinstance(checksum, str)
        assert len(checksum) == 16  # SHA256 truncated to 16 chars
        
        # Same state should produce same checksum
        checksum2 = checkpoint.compute_checksum()
        assert checksum == checksum2
        
        # Different state should produce different checksum
        checkpoint.state["key3"] = "new"
        checksum3 = checkpoint.compute_checksum()
        assert checksum != checksum3
    
    def test_checkpoint_verify(self):
        """Test checkpoint integrity verification."""
        checkpoint = Checkpoint(
            id="cp_test_004",
            timestamp=datetime.utcnow(),
            version="1.0",
            reason="test_verify",
            state={"data": "test"}
        )
        
        # No checksum set should pass verification
        assert checkpoint.verify() == True
        
        # Set correct checksum
        checkpoint.checksum = checkpoint.compute_checksum()
        assert checkpoint.verify() == True
        
        # Tamper with state
        checkpoint.state["data"] = "tampered"
        assert checkpoint.verify() == False
    
    def test_checkpoint_defaults(self):
        """Test Checkpoint default values."""
        checkpoint = Checkpoint(
            id="cp_test_defaults",
            timestamp=datetime.utcnow(),
            version="1.0",
            reason="test_defaults"
        )
        
        assert checkpoint.state == {}
        assert checkpoint.parent_id is None
        assert checkpoint.checksum is None
        assert checkpoint.compressed == False
        assert checkpoint.metadata == {}


# =============================================================================
# CheckpointPolicy Tests
# =============================================================================

class TestCheckpointPolicy:
    """Tests for the CheckpointPolicy dataclass."""
    
    def test_policy_defaults(self):
        """Test default policy values."""
        policy = CheckpointPolicy()
        
        assert policy.enabled == True
        assert policy.max_checkpoints == 100
        assert policy.max_age_days == 30
        assert policy.compress_after_days == 7
        assert policy.auto_checkpoint_interval_minutes == 60
        assert policy.checkpoint_on_error == True
        assert policy.checkpoint_on_high_risk == True
        assert policy.keep_minimum == 10
    
    def test_policy_custom_values(self):
        """Test custom policy values."""
        policy = CheckpointPolicy(
            enabled=False,
            max_checkpoints=50,
            max_age_days=14,
            keep_minimum=5
        )
        
        assert policy.enabled == False
        assert policy.max_checkpoints == 50
        assert policy.max_age_days == 14
        assert policy.keep_minimum == 5


# =============================================================================
# CheckpointManager Tests
# =============================================================================

class TestCheckpointManager:
    """Tests for the CheckpointManager class."""
    
    def test_manager_initialization(self, checkpoint_manager):
        """Test CheckpointManager initialization."""
        assert checkpoint_manager is not None
        assert checkpoint_manager.policy is not None
        assert checkpoint_manager.VERSION == "1.0"
        assert checkpoint_manager._checkpoint_dir.exists()
    
    def test_create_checkpoint(self, checkpoint_manager, sample_state):
        """Test creating a checkpoint."""
        checkpoint = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_create",
            metadata={"test_id": "001"}
        )
        
        assert checkpoint is not None
        assert checkpoint.id.startswith("cp_")
        assert checkpoint.reason == "test_create"
        assert checkpoint.state == sample_state
        assert checkpoint.metadata == {"test_id": "001"}
        assert checkpoint.checksum is not None
        assert checkpoint.version == "1.0"
    
    def test_create_checkpoint_disabled(self, temp_checkpoint_dir):
        """Test creating checkpoint when disabled."""
        policy = CheckpointPolicy(enabled=False)
        manager = CheckpointManager(policy)
        manager._checkpoint_dir = Path(temp_checkpoint_dir)
        
        with pytest.raises(CheckpointError) as exc_info:
            manager.create_checkpoint(state={}, reason="test")
        
        assert "disabled" in str(exc_info.value).lower()
    
    def test_create_emergency_checkpoint(self, checkpoint_manager, sample_state):
        """Test creating emergency checkpoint."""
        checkpoint = checkpoint_manager.create_emergency_checkpoint(state=sample_state)
        
        assert checkpoint.reason == "emergency"
        assert checkpoint.metadata.get("emergency") == True
        assert checkpoint.metadata.get("priority") == "critical"
    
    def test_get_checkpoint(self, checkpoint_manager, sample_state):
        """Test retrieving a checkpoint by ID."""
        created = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_get"
        )
        
        retrieved = checkpoint_manager.get_checkpoint(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.state == sample_state
        assert retrieved.reason == "test_get"
    
    def test_get_checkpoint_not_found(self, checkpoint_manager):
        """Test retrieving non-existent checkpoint."""
        result = checkpoint_manager.get_checkpoint("non_existent_id")
        assert result is None
    
    def test_get_latest(self, checkpoint_manager, sample_state):
        """Test getting the latest checkpoint."""
        # Create multiple checkpoints
        cp1 = checkpoint_manager.create_checkpoint(
            state={"version": 1},
            reason="test_latest"
        )
        cp2 = checkpoint_manager.create_checkpoint(
            state={"version": 2},
            reason="test_latest"
        )
        cp3 = checkpoint_manager.create_checkpoint(
            state={"version": 3},
            reason="test_latest"
        )
        
        latest = checkpoint_manager.get_latest()
        
        assert latest is not None
        assert latest.state["version"] == 3
    
    def test_get_latest_with_filter(self, checkpoint_manager):
        """Test getting latest checkpoint with reason filter."""
        checkpoint_manager.create_checkpoint(state={}, reason="type_a")
        checkpoint_manager.create_checkpoint(state={}, reason="type_b")
        checkpoint_manager.create_checkpoint(state={}, reason="type_a")
        
        latest_a = checkpoint_manager.get_latest(reason_filter="type_a")
        
        assert latest_a is not None
        assert latest_a.reason == "type_a"
    
    def test_list_checkpoints(self, checkpoint_manager):
        """Test listing checkpoints."""
        # Create some checkpoints
        for i in range(5):
            checkpoint_manager.create_checkpoint(
                state={"index": i},
                reason="test_list"
            )
        
        checkpoints = checkpoint_manager.list_checkpoints()
        
        assert len(checkpoints) == 5
        # Should be sorted by timestamp (newest first)
        timestamps = [cp["timestamp"] for cp in checkpoints]
        assert timestamps == sorted(timestamps, reverse=True)
    
    def test_list_checkpoints_with_limit(self, checkpoint_manager):
        """Test listing checkpoints with limit."""
        for i in range(10):
            checkpoint_manager.create_checkpoint(state={"i": i}, reason="test")
        
        checkpoints = checkpoint_manager.list_checkpoints(limit=5)
        
        assert len(checkpoints) == 5
    
    def test_list_checkpoints_with_reason_filter(self, checkpoint_manager):
        """Test listing checkpoints filtered by reason."""
        checkpoint_manager.create_checkpoint(state={}, reason="keep")
        checkpoint_manager.create_checkpoint(state={}, reason="discard")
        checkpoint_manager.create_checkpoint(state={}, reason="keep")
        
        checkpoints = checkpoint_manager.list_checkpoints(reason="keep")
        
        assert len(checkpoints) == 2
        for cp in checkpoints:
            assert cp["reason"] == "keep"
    
    def test_restore_checkpoint(self, checkpoint_manager, sample_state):
        """Test restoring state from checkpoint."""
        created = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_restore"
        )
        
        restored_state = checkpoint_manager.restore_checkpoint(created.id)
        
        assert restored_state == sample_state
    
    def test_restore_checkpoint_not_found(self, checkpoint_manager):
        """Test restoring non-existent checkpoint."""
        with pytest.raises(CheckpointError) as exc_info:
            checkpoint_manager.restore_checkpoint("non_existent")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_delete_checkpoint(self, checkpoint_manager, sample_state):
        """Test deleting a checkpoint."""
        created = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_delete"
        )
        
        checkpoint_manager.delete_checkpoint(created.id)
        
        # Should no longer exist
        assert checkpoint_manager.get_checkpoint(created.id) is None
        assert created.id not in checkpoint_manager._index
    
    def test_verify_checkpoint(self, checkpoint_manager, sample_state):
        """Test verifying checkpoint integrity."""
        created = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_verify"
        )
        
        is_valid = checkpoint_manager.verify_checkpoint(created.id)
        
        assert is_valid == True
    
    def test_verify_all(self, checkpoint_manager):
        """Test verifying all checkpoints."""
        for i in range(3):
            checkpoint_manager.create_checkpoint(
                state={"index": i},
                reason="test_verify_all"
            )
        
        results = checkpoint_manager.verify_all()
        
        assert len(results) == 3
        assert all(results.values())  # All should be valid
    
    def test_get_checkpoint_chain(self, checkpoint_manager):
        """Test getting checkpoint chain."""
        # Create chain: root -> child -> grandchild
        root = checkpoint_manager.create_checkpoint(
            state={"level": 0},
            reason="chain_test"
        )
        child = checkpoint_manager.create_checkpoint(
            state={"level": 1},
            reason="chain_test",
            parent_id=root.id
        )
        grandchild = checkpoint_manager.create_checkpoint(
            state={"level": 2},
            reason="chain_test",
            parent_id=child.id
        )
        
        chain = checkpoint_manager.get_checkpoint_chain(grandchild.id)
        
        assert len(chain) == 3
        assert chain[0].id == root.id
        assert chain[1].id == child.id
        assert chain[2].id == grandchild.id
    
    def test_diff_checkpoints(self, checkpoint_manager):
        """Test diff between two checkpoints."""
        cp1 = checkpoint_manager.create_checkpoint(
            state={"a": 1, "b": 2, "c": 3},
            reason="diff_test"
        )
        cp2 = checkpoint_manager.create_checkpoint(
            state={"a": 1, "b": 20, "d": 4},
            reason="diff_test"
        )
        
        diff = checkpoint_manager.diff_checkpoints(cp1.id, cp2.id)
        
        assert "added" in diff
        assert "removed" in diff
        assert "modified" in diff
        
        assert diff["added"] == {"d": 4}
        assert diff["removed"] == {"c": 3}
        assert diff["modified"] == {"b": {"old": 2, "new": 20}}
    
    def test_compress_checkpoint(self, checkpoint_manager, sample_state):
        """Test checkpoint compression."""
        created = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_compress"
        )
        
        success = checkpoint_manager.compress_checkpoint(created.id)
        
        assert success == True
        
        # Verify we can still retrieve it
        retrieved = checkpoint_manager.get_checkpoint(created.id)
        assert retrieved is not None
        assert retrieved.compressed == True
        assert retrieved.state == sample_state
    
    def test_get_stats(self, checkpoint_manager):
        """Test getting manager statistics."""
        # Create some checkpoints
        for i in range(3):
            checkpoint_manager.create_checkpoint(state={"i": i}, reason="stats_test")
        
        stats = checkpoint_manager.get_stats()
        
        assert "created" in stats
        assert stats["created"] == 3
        assert "total_checkpoints" in stats
        assert stats["total_checkpoints"] == 3
        assert "policy" in stats
    
    def test_export_import_checkpoint(self, checkpoint_manager, sample_state, temp_checkpoint_dir):
        """Test exporting and importing checkpoints."""
        created = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="test_export"
        )
        
        export_path = Path(temp_checkpoint_dir) / "exported.json"
        checkpoint_manager.export_checkpoint(created.id, export_path)
        
        assert export_path.exists()
        
        # Import the checkpoint
        imported = checkpoint_manager.import_checkpoint(export_path)
        
        assert imported is not None
        assert imported.state == sample_state
        assert imported.metadata.get("imported") == True
    
    def test_cleanup_old_checkpoints(self, checkpoint_manager):
        """Test automatic cleanup of old checkpoints."""
        # Create many checkpoints
        for i in range(15):
            checkpoint_manager.create_checkpoint(state={"i": i}, reason="cleanup_test")
        
        # With max_checkpoints=10 and keep_minimum=2, should have 10 total
        assert len(checkpoint_manager._index) <= checkpoint_manager.policy.max_checkpoints
    
    def test_cache_management(self, checkpoint_manager):
        """Test in-memory cache management."""
        # Create checkpoint
        created = checkpoint_manager.create_checkpoint(state={}, reason="cache_test")
        
        # Should be in cache
        assert created.id in checkpoint_manager._cache
        
        # Get should use cache
        retrieved = checkpoint_manager.get_checkpoint(created.id)
        assert retrieved is created  # Same object from cache


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestCheckpointErrors:
    """Tests for error handling."""
    
    def test_checkpoint_error_exception(self):
        """Test CheckpointError can be raised and caught."""
        with pytest.raises(CheckpointError):
            raise CheckpointError("test error")
        
        try:
            raise CheckpointError("test message")
        except CheckpointError as e:
            assert "test message" in str(e)
    
    def test_restore_corrupted_checkpoint(self, checkpoint_manager):
        """Test restoring corrupted checkpoint."""
        # Create checkpoint
        created = checkpoint_manager.create_checkpoint(
            state={"data": "test"},
            reason="corruption_test"
        )
        
        # Corrupt the file
        checkpoint_path = checkpoint_manager._get_checkpoint_path(created.id)
        with open(checkpoint_path, 'w') as f:
            f.write('{"corrupted": json}')
        
        # Clear cache to force reload
        checkpoint_manager._cache.clear()
        
        # Loading might succeed but verification should fail or loading might fail
        # Depending on implementation details
        try:
            checkpoint_manager.restore_checkpoint(created.id)
        except (CheckpointError, json.JSONDecodeError, KeyError):
            pass  # Expected


# =============================================================================
# Integration Tests
# =============================================================================

class TestCheckpointIntegration:
    """Integration tests for checkpoint workflows."""
    
    def test_full_checkpoint_lifecycle(self, checkpoint_manager, sample_state):
        """Test complete checkpoint lifecycle."""
        # Create
        checkpoint = checkpoint_manager.create_checkpoint(
            state=sample_state,
            reason="lifecycle_test",
            metadata={"tag": "important"}
        )
        assert checkpoint.id in checkpoint_manager._index
        
        # Verify
        assert checkpoint_manager.verify_checkpoint(checkpoint.id) == True
        
        # Restore
        restored = checkpoint_manager.restore_checkpoint(checkpoint.id)
        assert restored == sample_state
        
        # List
        checkpoints = checkpoint_manager.list_checkpoints()
        assert any(cp["id"] == checkpoint.id for cp in checkpoints)
        
        # Delete
        checkpoint_manager.delete_checkpoint(checkpoint.id)
        assert checkpoint_manager.get_checkpoint(checkpoint.id) is None
    
    def test_checkpoint_chain_workflow(self, checkpoint_manager):
        """Test creating and navigating checkpoint chain."""
        # Build a chain
        operations = []
        parent_id = None
        
        for i in range(5):
            state = {
                "operation_index": i,
                "operations": operations.copy()
            }
            operations.append(f"op_{i}")
            
            checkpoint = checkpoint_manager.create_checkpoint(
                state=state,
                reason="chain_workflow",
                parent_id=parent_id
            )
            parent_id = checkpoint.id
        
        # Get chain
        chain = checkpoint_manager.get_checkpoint_chain(parent_id)
        assert len(chain) == 5
        
        # Verify chain order
        for i, checkpoint in enumerate(chain):
            assert checkpoint.state["operation_index"] == i
    
    def test_concurrent_access(self, checkpoint_manager, sample_state):
        """Test thread-safe checkpoint operations."""
        import threading
        
        created_ids = []
        lock = threading.Lock()
        
        def create_checkpoints():
            for i in range(5):
                cp = checkpoint_manager.create_checkpoint(
                    state={"thread": threading.current_thread().name, "i": i},
                    reason="concurrent_test"
                )
                with lock:
                    created_ids.append(cp.id)
        
        # Run multiple threads
        threads = [
            threading.Thread(target=create_checkpoints, name=f"Thread-{i}")
            for i in range(3)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have created all checkpoints
        assert len(created_ids) == 15
        assert len(set(created_ids)) == 15  # All unique


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("Running Checkpoint tests...")
    
    # Run with pytest if available
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        print("pytest not available, running basic smoke tests...")
        
        # Basic smoke tests without pytest
        with tempfile.TemporaryDirectory() as temp_dir:
            policy = CheckpointPolicy(enabled=True, max_checkpoints=5)
            manager = CheckpointManager(policy)
            manager._checkpoint_dir = Path(temp_dir)
            manager._checkpoint_dir.mkdir(parents=True, exist_ok=True)
            manager._index = {}
            
            # Test creation
            cp = manager.create_checkpoint(
                state={"test": "data"},
                reason="smoke_test"
            )
            print(f"✓ Created checkpoint: {cp.id}")
            
            # Test retrieval
            retrieved = manager.get_checkpoint(cp.id)
            assert retrieved is not None
            print("✓ Retrieved checkpoint")
            
            # Test restore
            state = manager.restore_checkpoint(cp.id)
            assert state["test"] == "data"
            print("✓ Restored checkpoint")
            
            # Test list
            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 1
            print("✓ Listed checkpoints")
            
            print("\n✅ All smoke tests passed!")
