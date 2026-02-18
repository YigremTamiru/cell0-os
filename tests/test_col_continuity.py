"""
Tests for COL-Continuity Module

Tests all components: checkpoint, serializer, persistence, restore, merger
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

# Import continuity module
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
)
from col.continuity.merger import (
    StateMerger,
    ConflictResolver,
    Conflict,
    ConflictType,
    MergeStrategy,
    MergeResult,
)


# =============================================================================
# Checkpoint Tests
# =============================================================================

class TestCheckpointManager:
    """Tests for CheckpointManager."""
    
    @pytest.fixture
    async def manager(self):
        """Create a temporary checkpoint manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(
                storage_path=tmpdir,
                auto_interval_seconds=1.0,
                max_checkpoints=10,
            )
            yield manager
            await manager.stop_auto_checkpointing()
    
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, manager):
        """Test creating a checkpoint."""
        # Register state provider
        test_state = {"key1": "value1", "key2": 42}
        manager.register_state_provider(lambda: asyncio.coroutine(lambda: test_state)())
        
        # Create checkpoint
        cp = await manager.create(
            checkpoint_type=CheckpointType.USER,
            description="Test checkpoint",
            tags=["test"],
            state=test_state,
        )
        
        assert cp.type == CheckpointType.USER
        assert cp.description == "Test checkpoint"
        assert cp.tags == ["test"]
        assert cp.status == CheckpointStatus.COMPLETE
        assert cp.size_bytes > 0
        assert cp.checksum != ""
        assert manager.get_last_checkpoint_id() == cp.id
    
    @pytest.mark.asyncio
    async def test_list_checkpoints(self, manager):
        """Test listing checkpoints."""
        # Create multiple checkpoints
        for i in range(3):
            await manager.create(
                checkpoint_type=CheckpointType.USER,
                description=f"Checkpoint {i}",
                state={"index": i},
            )
        
        # List all
        all_cps = await manager.list_checkpoints()
        assert len(all_cps) == 3
        
        # List by type
        user_cps = await manager.list_checkpoints(checkpoint_type=CheckpointType.USER)
        assert len(user_cps) == 3
    
    @pytest.mark.asyncio
    async def test_checkpoint_verification(self, manager):
        """Test checkpoint integrity verification."""
        cp = await manager.create(
            checkpoint_type=CheckpointType.USER,
            state={"data": "test"},
        )
        
        # Should pass
        assert await manager.verify(cp.id) is True
    
    @pytest.mark.asyncio
    async def test_checkpoint_chain(self, manager):
        """Test checkpoint chain functionality."""
        cp1 = await manager.create(state={"step": 1})
        cp2 = await manager.create(state={"step": 2})
        cp3 = await manager.create(state={"step": 3})
        
        # Get chain
        chain = await manager.get_checkpoint_chain(cp3.id)
        assert len(chain) == 3
        assert chain[0].id == cp1.id
        assert chain[1].id == cp2.id
        assert chain[2].id == cp3.id
    
    @pytest.mark.asyncio
    async def test_checkpoint_cleanup(self, manager):
        """Test old checkpoint cleanup."""
        manager.max_checkpoints = 3
        
        # Create more checkpoints than max
        for i in range(5):
            await manager.create(state={"index": i})
        
        # Should only have max_checkpoints remaining
        all_cps = await manager.list_checkpoints()
        assert len(all_cps) <= manager.max_checkpoints
    
    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, manager):
        """Test deleting a checkpoint."""
        cp = await manager.create(state={"data": "test"})
        
        # Delete
        success = await manager.delete(cp.id)
        assert success is True
        
        # Verify deleted
        assert await manager.exists(cp.id) is False


# =============================================================================
# Serializer Tests
# =============================================================================

class TestStateSerializer:
    """Tests for StateSerializer."""
    
    @pytest.fixture
    def serializer(self):
        """Create a state serializer."""
        return StateSerializer(
            format=SerializationFormat.JSON,
            compression=CompressionAlgorithm.ZLIB,
        )
    
    @pytest.mark.asyncio
    async def test_serialize_deserialize(self, serializer):
        """Test serialization and deserialization."""
        test_state = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
            "null": None,
        }
        
        # Serialize
        serialized = await serializer.serialize(test_state)
        
        assert "payload" in serialized
        assert serialized["format"] == "json"
        assert serialized["compression"] == "zlib"
        assert serialized["size_bytes"] > 0
        assert serialized["compressed_size_bytes"] > 0
        assert serialized["checksum"] != ""
        
        # Deserialize
        deserialized = await serializer.deserialize(serialized)
        
        assert deserialized == test_state
    
    @pytest.mark.asyncio
    async def test_differential_storage(self, serializer):
        """Test differential state storage."""
        base_state = {
            "stable": "value",
            "changing": "original",
            "counter": 0,
        }
        
        # First checkpoint (full)
        cp1 = await serializer.serialize(base_state)
        assert cp1["is_diff"] is False
        
        # Second checkpoint (small change)
        new_state = dict(base_state)
        new_state["changing"] = "modified"
        new_state["counter"] = 1
        
        cp2 = await serializer.serialize(
            new_state,
            parent_checkpoint="cp1",
        )
        
        # Should be diff if threshold is met
        assert "is_diff" in cp2
    
    @pytest.mark.asyncio
    async def test_compression_formats(self):
        """Test different compression formats."""
        test_state = {"data": "x" * 1000}  # Compressible data
        
        for compression in CompressionAlgorithm:
            serializer = StateSerializer(compression=compression)
            serialized = await serializer.serialize(test_state)
            deserialized = await serializer.deserialize(serialized)
            assert deserialized == test_state
    
    @pytest.mark.asyncio
    async def test_serialization_formats(self):
        """Test different serialization formats."""
        test_state = {"key": "value", "number": 42}
        
        for fmt in [SerializationFormat.JSON, SerializationFormat.PICKLE]:
            serializer = StateSerializer(format=fmt)
            serialized = await serializer.serialize(test_state)
            deserialized = await serializer.deserialize(serialized)
            assert deserialized == test_state


# =============================================================================
# Persistence Tests
# =============================================================================

class TestPersistenceBackends:
    """Tests for persistence backends."""
    
    @pytest.mark.asyncio
    async def test_filesystem_backend(self):
        """Test FileSystemBackend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = StorageConfig(path=Path(tmpdir))
            backend = FileSystemBackend(config)
            
            # Store
            test_data = {"key": "value", "number": 42}
            await backend.store("test_key", test_data)
            
            # Load
            loaded = await backend.load("test_key")
            assert loaded == test_data
            
            # Exists
            assert await backend.exists("test_key") is True
            assert await backend.exists("nonexistent") is False
            
            # List
            keys = await backend.list_keys()
            assert "test_key" in keys
            
            # Delete
            assert await backend.delete("test_key") is True
            assert await backend.exists("test_key") is False
    
    @pytest.mark.asyncio
    async def test_sqlite_backend(self):
        """Test SQLiteBackend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = StorageConfig(path=Path(tmpdir))
            backend = SQLiteBackend(config)
            
            # Store
            test_data = {"key": "value", "number": 42}
            await backend.store("test_key", test_data)
            
            # Load
            loaded = await backend.load("test_key")
            assert loaded == test_data
            
            # Stats
            stats = await backend.get_stats()
            assert stats["type"] == "sqlite"
            assert stats["record_count"] == 1
    
    @pytest.mark.asyncio
    async def test_hybrid_backend(self):
        """Test HybridBackend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = StorageConfig(path=Path(tmpdir))
            backend = HybridBackend(config)
            
            # Store small data
            small_data = {"key": "value"}
            await backend.store("small", small_data)
            
            # Store large data
            large_data = {"data": "x" * (backend.SIZE_THRESHOLD + 100)}
            await backend.store("large", large_data)
            
            # Load both
            assert await backend.load("small") == small_data
            assert await backend.load("large") == large_data
            
            # Stats
            stats = await backend.get_stats()
            assert stats["type"] == "hybrid"


# =============================================================================
# Restore Tests
# =============================================================================

class TestStateRestorer:
    """Tests for StateRestorer."""
    
    @pytest.fixture
    async def restorer_setup(self):
        """Create restorer with checkpoint manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(storage_path=tmpdir)
            restorer = StateRestorer(manager)
            yield manager, restorer
    
    @pytest.mark.asyncio
    async def test_restore_latest_no_checkpoint(self, restorer_setup):
        """Test restore when no checkpoints exist."""
        manager, restorer = restorer_setup
        
        result = await restorer.restore_latest()
        
        assert result.status == RestorationStatus.NO_CHECKPOINT
        assert result.checkpoint_id is None
    
    @pytest.mark.asyncio
    async def test_restore_from_checkpoint(self, restorer_setup):
        """Test restoring from a checkpoint."""
        manager, restorer = restorer_setup
        
        # Create checkpoint
        test_state = {"key1": "value1", "key2": 42}
        cp = await manager.create(state=test_state)
        
        # Restore
        result = await restorer.restore_from_checkpoint(cp.id)
        
        assert result.status == RestorationStatus.SUCCESS
        assert result.checkpoint_id == cp.id
        assert result.state == test_state
        assert "key1" in result.restored_keys
        assert "key2" in result.restored_keys
    
    @pytest.mark.asyncio
    async def test_restore_with_consumer(self, restorer_setup):
        """Test restore with state consumer callback."""
        manager, restorer = restorer_setup
        
        # Track received state
        received = {}
        
        async def consumer(key, value):
            received[key] = value
        
        restorer.register_state_consumer(consumer)
        
        # Create and restore
        test_state = {"a": 1, "b": 2}
        cp = await manager.create(state=test_state)
        result = await restorer.restore_from_checkpoint(cp.id)
        
        assert result.status == RestorationStatus.SUCCESS
        assert received == test_state
    
    @pytest.mark.asyncio
    async def test_restore_preview(self, restorer_setup):
        """Test restore preview."""
        manager, restorer = restorer_setup
        
        cp = await manager.create(state={"key": "value"})
        
        preview = await restorer.preview_restore(cp.id)
        
        assert preview["checkpoint_id"] == cp.id
        assert "size_bytes" in preview
        assert "format" in preview


class TestTemporalCoherenceManager:
    """Tests for TemporalCoherenceManager."""
    
    def test_coherence_evaluation(self):
        """Test temporal coherence evaluation."""
        manager = TemporalCoherenceManager()
        
        from col.continuity.restore import TemporalCheckpoint
        
        # Recent checkpoint - high coherence
        recent = TemporalCheckpoint(
            timestamp=__import__("time").time() - 60,  # 1 minute ago
            checkpoint_id="cp1",
            session_id="session1",
            coherence_markers={},
        )
        score, warnings = manager.evaluate_coherence(recent)
        assert score > 0.8
        assert len(warnings) == 0
        
        # Old checkpoint - lower coherence
        old = TemporalCheckpoint(
            timestamp=__import__("time").time() - 86400 * 10,  # 10 days ago
            checkpoint_id="cp2",
            session_id="session2",
            coherence_markers={},
        )
        score, warnings = manager.evaluate_coherence(old)
        assert score < 0.8
        assert len(warnings) > 0
    
    def test_restore_order(self):
        """Test dependency-aware restore ordering."""
        manager = TemporalCoherenceManager()
        
        # Register dependencies
        manager.register_dependency("c", ["a", "b"])
        manager.register_dependency("b", ["a"])
        
        order = manager.get_restore_order(["c", "b", "a"])
        
        # a should come first, then b, then c
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")


# =============================================================================
# Merger Tests
# =============================================================================

class TestStateMerger:
    """Tests for StateMerger."""
    
    @pytest.fixture
    def merger(self):
        """Create a state merger."""
        return StateMerger()
    
    def test_merge_no_conflict(self, merger):
        """Test merging non-conflicting states."""
        source = {"key1": "value1"}
        target = {"key2": "value2"}
        
        result = merger.merge(source, target)
        
        assert result.success is True
        assert result.merged_state == {"key1": "value1", "key2": "value2"}
        assert len(result.conflicts) == 0
    
    def test_merge_with_conflict(self, merger):
        """Test merging with conflicts."""
        source = {"key": "source_value"}
        target = {"key": "target_value"}
        
        result = merger.merge(source, target)
        
        assert len(result.conflicts) == 1
        assert result.conflicts[0].conflict_type == ConflictType.KEY_MODIFIED_BOTH
    
    def test_merge_strategies(self, merger):
        """Test different merge strategies."""
        source = {"key": "source"}
        target = {"key": "target"}
        
        # Source wins
        result = merger.merge(source, target, default_strategy=MergeStrategy.SOURCE_WINS)
        assert result.merged_state["key"] == "source"
        
        # Target wins
        result = merger.merge(source, target, default_strategy=MergeStrategy.TARGET_WINS)
        assert result.merged_state["key"] == "target"
    
    def test_union_strategy(self, merger):
        """Test union merge strategy."""
        source = {"list": [1, 2, 3]}
        target = {"list": [2, 3, 4]}
        
        result = merger.merge(source, target, default_strategy=MergeStrategy.UNION)
        
        # Should combine lists without duplicates
        assert sorted(result.merged_state["list"]) == [1, 2, 3, 4]
    
    def test_parallel_session_merge(self, merger):
        """Test merging multiple parallel sessions."""
        sessions = [
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
            {"c": 5, "d": 6},
        ]
        
        result = merger.merge_parallel_sessions(sessions)
        
        assert "a" in result.merged_state
        assert "b" in result.merged_state
        assert "c" in result.merged_state
        assert "d" in result.merged_state


class TestConflictResolver:
    """Tests for ConflictResolver."""
    
    def test_resolve_source_wins(self):
        """Test source wins resolution."""
        resolver = ConflictResolver()
        
        conflict = Conflict(
            key="test",
            conflict_type=ConflictType.KEY_MODIFIED_BOTH,
            source_value="source",
            target_value="target",
        )
        
        result = resolver.resolve(conflict, MergeStrategy.SOURCE_WINS)
        assert result == "source"
    
    def test_resolve_with_timestamps(self):
        """Test timestamp-based resolution."""
        import time
        resolver = ConflictResolver()
        
        conflict = Conflict(
            key="test",
            conflict_type=ConflictType.KEY_MODIFIED_BOTH,
            source_value="newer",
            target_value="older",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100,
        )
        
        result = resolver.resolve(conflict, MergeStrategy.TIMESTAMP)
        assert result == "newer"
    
    def test_custom_resolver(self):
        """Test custom conflict resolver."""
        resolver = ConflictResolver()
        
        def custom_resolver(conflict):
            return f"custom_{conflict.source_value}_{conflict.target_value}"
        
        resolver.register_custom_resolver("test", custom_resolver)
        
        conflict = Conflict(
            key="test_key",
            conflict_type=ConflictType.KEY_MODIFIED_BOTH,
            source_value="a",
            target_value="b",
        )
        
        result = resolver.resolve(conflict)
        assert result == "custom_a_b"


# =============================================================================
# Integration Tests
# =============================================================================

class TestContinuityIntegration:
    """Integration tests for the full continuity system."""
    
    @pytest.mark.asyncio
    async def test_full_checkpoint_restore_cycle(self):
        """Test full checkpoint and restore cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            manager = CheckpointManager(storage_path=tmpdir)
            restorer = StateRestorer(manager)
            
            # Create state
            original_state = {
                "session_data": {
                    "user_preferences": {"theme": "dark"},
                    "open_files": ["/path/to/file1", "/path/to/file2"],
                },
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ],
            }
            
            # Create checkpoint
            cp = await manager.create(
                checkpoint_type=CheckpointType.USER,
                description="Full session state",
                state=original_state,
            )
            
            # Restore
            result = await restorer.restore_from_checkpoint(cp.id)
            
            assert result.status == RestorationStatus.SUCCESS
            assert result.state == original_state
            assert result.coherence_score > 0.5
    
    @pytest.mark.asyncio
    async def test_differential_checkpoint_chain(self):
        """Test differential checkpoints in a chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(storage_path=tmpdir)
            
            # Initial full state
            state = {"counter": 0, "data": "initial"}
            cp1 = await manager.create(state=state)
            
            # Modify and create diff checkpoint
            state["counter"] = 1
            cp2 = await manager.create(state=state)
            
            # Modify again
            state["data"] = "modified"
            cp3 = await manager.create(state=state)
            
            # Restore chain
            restorer = StateRestorer(manager)
            results = await restorer.restore_chain(cp1.id, cp3.id)
            
            assert len(results) == 3
            # Final state should have all modifications
            final_state = results[-1].state
            assert final_state["counter"] == 1
            assert final_state["data"] == "modified"
    
    @pytest.mark.asyncio
    async def test_parallel_session_merge(self):
        """Test merging parallel session states."""
        # Simulate two parallel sessions diverging from a common base
        base_state = {
            "shared_data": "common",
            "counter": 0,
        }
        
        session_a = dict(base_state)
        session_a["session_a_data"] = "A"
        session_a["counter"] = 1
        
        session_b = dict(base_state)
        session_b["session_b_data"] = "B"
        session_b["counter"] = 2
        
        # Merge
        merger = StateMerger()
        result = merger.merge(session_a, session_b, base_state)
        
        # Should have both session-specific data
        assert result.merged_state["session_a_data"] == "A"
        assert result.merged_state["session_b_data"] == "B"
        # Counter should have conflict
        assert len(result.conflicts) >= 1
    
    @pytest.mark.asyncio
    async def test_end_to_end_continuity(self):
        """Test end-to-end continuity workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create initial session and checkpoint
            manager1 = CheckpointManager(storage_path=tmpdir)
            
            session_state = {
                "memory": {"last_topic": "python"},
                "context": {"project": "test"},
            }
            
            await manager1.create(
                checkpoint_type=CheckpointType.SHUTDOWN,
                state=session_state,
            )
            
            # 2. Simulate session restart - new manager
            manager2 = CheckpointManager(storage_path=tmpdir)
            restorer = StateRestorer(manager2)
            
            # 3. Restore state
            result = await restorer.restore_latest()
            
            assert result.status == RestorationStatus.SUCCESS
            assert result.state["memory"]["last_topic"] == "python"
            assert result.state["context"]["project"] == "test"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])