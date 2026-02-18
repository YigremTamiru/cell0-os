"""
COL-Continuity State Restoration

Handles restoration of session state with temporal coherence maintenance.
Ensures sessions resume seamlessly from checkpoints.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from col.continuity.checkpoint import CheckpointManager, CheckpointMetadata, CheckpointStatus
from col.continuity.serializer import StateSerializer
from col.continuity.persistence import PersistenceBackend


class RestorationStatus(Enum):
    """Status of state restoration."""
    SUCCESS = "success"
    PARTIAL = "partial"     # Some state restored, some failed
    FAILED = "failed"
    NO_CHECKPOINT = "no_checkpoint"
    CORRUPTED = "corrupted"


class TemporalCoherenceError(Exception):
    """Raised when temporal coherence cannot be maintained."""
    pass


@dataclass
class RestorationResult:
    """Result of a restoration operation."""
    status: RestorationStatus
    checkpoint_id: Optional[str]
    state: dict[str, Any]
    restored_keys: list[str]
    failed_keys: list[str]
    coherence_score: float  # 0.0 to 1.0
    temporal_gap_seconds: float
    warnings: list[str]
    metadata: dict[str, Any]


@dataclass
class TemporalCheckpoint:
    """Represents a point in the session timeline."""
    timestamp: float
    checkpoint_id: str
    session_id: str
    coherence_markers: dict[str, Any]


class TemporalCoherenceManager:
    """
    Maintains temporal coherence across session restarts.
    
    Tracks:
    - Time progression
    - State dependencies
    - External system states
    - In-flight operations
    """
    
    def __init__(self):
        self._checkpoints: list[TemporalCheckpoint] = []
        self._coherence_threshold = 0.8
        self._max_temporal_gap = 86400 * 7  # 7 days
        self._dependency_graph: dict[str, set[str]] = {}
    
    def register_checkpoint(
        self,
        checkpoint_id: str,
        session_id: str,
        coherence_markers: dict[str, Any],
    ) -> TemporalCheckpoint:
        """Register a checkpoint for coherence tracking."""
        checkpoint = TemporalCheckpoint(
            timestamp=time.time(),
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            coherence_markers=coherence_markers,
        )
        self._checkpoints.append(checkpoint)
        return checkpoint
    
    def evaluate_coherence(
        self,
        target_checkpoint: TemporalCheckpoint,
        current_time: float | None = None,
    ) -> tuple[float, list[str]]:
        """
        Evaluate temporal coherence for restoring to a checkpoint.
        
        Returns:
            Tuple of (coherence_score, warnings)
        """
        if current_time is None:
            current_time = time.time()
        
        warnings = []
        score = 1.0
        
        # Check temporal gap
        gap = current_time - target_checkpoint.timestamp
        if gap > self._max_temporal_gap:
            score -= 0.3
            warnings.append(f"Large temporal gap: {gap / 86400:.1f} days")
        elif gap > 86400:  # 1 day
            score -= 0.1
            warnings.append(f"Temporal gap: {gap / 3600:.1f} hours")
        
        # Check coherence markers
        markers = target_checkpoint.coherence_markers
        
        # Time-based markers
        if "expected_time" in markers:
            expected = markers["expected_time"]
            drift = abs(current_time - expected)
            if drift > 60:  # 1 minute
                score -= 0.1
                warnings.append(f"Time drift: {drift:.0f} seconds")
        
        # External dependency markers
        if "external_deps" in markers:
            # Would check external system states here
            pass
        
        return max(0.0, score), warnings
    
    def register_dependency(self, key: str, depends_on: list[str]) -> None:
        """Register state key dependencies."""
        if key not in self._dependency_graph:
            self._dependency_graph[key] = set()
        self._dependency_graph[key].update(depends_on)
    
    def get_restore_order(self, keys: list[str]) -> list[str]:
        """
        Get optimal restoration order based on dependencies.
        
        Uses topological sort to ensure dependencies are restored first.
        """
        # Simple dependency-aware ordering
        restored = set()
        order = []
        remaining = set(keys)
        
        while remaining:
            # Find keys with all dependencies satisfied
            ready = {
                k for k in remaining
                if k not in self._dependency_graph or
                self._dependency_graph[k].issubset(restored)
            }
            
            if not ready:
                # Circular dependency or missing dependency, just add remaining
                order.extend(sorted(remaining))
                break
            
            for key in sorted(ready):
                order.append(key)
                restored.add(key)
                remaining.remove(key)
        
        return order


class StateRestorer:
    """
    Restores session state from checkpoints.
    
    Features:
    - Full and partial restoration
    - Temporal coherence validation
    - State dependency resolution
    - Graceful degradation
    """
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        serializer: StateSerializer | None = None,
        backend: PersistenceBackend | None = None,
    ):
        self._checkpoint_manager = checkpoint_manager
        self._serializer = serializer or StateSerializer()
        self._backend = backend or checkpoint_manager._backend
        self._coherence_manager = TemporalCoherenceManager()
        
        self._state_consumer: Optional[
            Callable[[str, Any], Coroutine[Any, Any, None]]
        ] = None
        self._validation_hooks: dict[str, Callable[[Any], bool]] = {}
    
    def register_state_consumer(
        self,
        consumer: Callable[[str, Any], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Register a callback for restored state items.
        
        The callback receives (key, value) pairs as they are restored.
        """
        self._state_consumer = consumer
    
    def register_validation_hook(self, key: str, validator: Callable[[Any], bool]) -> None:
        """Register a validation function for a specific state key."""
        self._validation_hooks[key] = validator
    
    async def restore_latest(
        self,
        require_coherence: bool = True,
    ) -> RestorationResult:
        """
        Restore from the most recent checkpoint.
        
        Args:
            require_coherence: Fail if coherence score is too low
        
        Returns:
            RestorationResult with details
        """
        # Find latest checkpoint
        checkpoints = await self._checkpoint_manager.list_checkpoints(limit=1)
        
        if not checkpoints:
            return RestorationResult(
                status=RestorationStatus.NO_CHECKPOINT,
                checkpoint_id=None,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=0.0,
                temporal_gap_seconds=0.0,
                warnings=["No checkpoints found"],
                metadata={},
            )
        
        return await self.restore_from_checkpoint(checkpoints[0].id, require_coherence)
    
    async def restore_from_checkpoint(
        self,
        checkpoint_id: str,
        require_coherence: bool = True,
    ) -> RestorationResult:
        """
        Restore state from a specific checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to restore from
            require_coherence: Fail if coherence score is too low
        
        Returns:
            RestorationResult with details
        """
        warnings = []
        metadata: dict[str, Any] = {}
        
        try:
            # Get checkpoint metadata
            checkpoint = await self._checkpoint_manager.get(checkpoint_id)
        except KeyError:
            return RestorationResult(
                status=RestorationStatus.NO_CHECKPOINT,
                checkpoint_id=checkpoint_id,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=0.0,
                temporal_gap_seconds=0.0,
                warnings=[f"Checkpoint {checkpoint_id} not found"],
                metadata={},
            )
        
        # Verify checkpoint integrity
        if checkpoint.status != CheckpointStatus.COMPLETE:
            return RestorationResult(
                status=RestorationStatus.CORRUPTED,
                checkpoint_id=checkpoint_id,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=0.0,
                temporal_gap_seconds=0.0,
                warnings=[f"Checkpoint status: {checkpoint.status.value}"],
                metadata={},
            )
        
        is_valid = await self._checkpoint_manager.verify(checkpoint_id)
        if not is_valid:
            return RestorationResult(
                status=RestorationStatus.CORRUPTED,
                checkpoint_id=checkpoint_id,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=0.0,
                temporal_gap_seconds=0.0,
                warnings=["Checkpoint integrity check failed"],
                metadata={},
            )
        
        # Calculate temporal gap
        temporal_gap = time.time() - checkpoint.timestamp
        
        # Evaluate coherence
        temporal_checkpoint = TemporalCheckpoint(
            timestamp=checkpoint.timestamp,
            checkpoint_id=checkpoint.id,
            session_id=checkpoint.session_id,
            coherence_markers={},
        )
        coherence_score, coherence_warnings = self._coherence_manager.evaluate_coherence(
            temporal_checkpoint
        )
        warnings.extend(coherence_warnings)
        
        if require_coherence and coherence_score < 0.5:
            return RestorationResult(
                status=RestorationStatus.FAILED,
                checkpoint_id=checkpoint_id,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=coherence_score,
                temporal_gap_seconds=temporal_gap,
                warnings=warnings + ["Coherence check failed"],
                metadata={"checkpoint": checkpoint.to_dict()},
            )
        
        # Load checkpoint data
        try:
            serialized = await self._backend.load(checkpoint_id)
        except Exception as e:
            return RestorationResult(
                status=RestorationStatus.FAILED,
                checkpoint_id=checkpoint_id,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=coherence_score,
                temporal_gap_seconds=temporal_gap,
                warnings=warnings + [f"Failed to load checkpoint data: {e}"],
                metadata={},
            )
        
        # Handle differential checkpoint
        base_state = {}
        if serialized.get("is_diff") and serialized.get("base_checkpoint_id"):
            try:
                base_serialized = await self._backend.load(serialized["base_checkpoint_id"])
                base_state = await self._serializer.deserialize(base_serialized)
            except Exception as e:
                warnings.append(f"Could not load base checkpoint: {e}")
        
        # Deserialize state
        try:
            state = await self._serializer.deserialize(serialized, base_state)
        except Exception as e:
            return RestorationResult(
                status=RestorationStatus.CORRUPTED,
                checkpoint_id=checkpoint_id,
                state={},
                restored_keys=[],
                failed_keys=[],
                coherence_score=coherence_score,
                temporal_gap_seconds=temporal_gap,
                warnings=warnings + [f"Deserialization failed: {e}"],
                metadata={},
            )
        
        # Restore individual state items
        restored_keys = []
        failed_keys = []
        
        # Get optimal restore order
        restore_order = self._coherence_manager.get_restore_order(list(state.keys()))
        
        for key in restore_order:
            value = state[key]
            
            # Validate if hook registered
            if key in self._validation_hooks:
                if not self._validation_hooks[key](value):
                    warnings.append(f"Validation failed for key: {key}")
                    failed_keys.append(key)
                    continue
            
            # Send to consumer if registered
            if self._state_consumer:
                try:
                    await self._state_consumer(key, value)
                    restored_keys.append(key)
                except Exception as e:
                    warnings.append(f"Failed to restore {key}: {e}")
                    failed_keys.append(key)
            else:
                restored_keys.append(key)
        
        # Determine status
        if not restored_keys:
            status = RestorationStatus.FAILED
        elif failed_keys:
            status = RestorationStatus.PARTIAL
        else:
            status = RestorationStatus.SUCCESS
        
        metadata = {
            "checkpoint": checkpoint.to_dict(),
            "coherence_score": coherence_score,
            "temporal_gap_seconds": temporal_gap,
        }
        
        return RestorationResult(
            status=status,
            checkpoint_id=checkpoint_id,
            state=state,
            restored_keys=restored_keys,
            failed_keys=failed_keys,
            coherence_score=coherence_score,
            temporal_gap_seconds=temporal_gap,
            warnings=warnings,
            metadata=metadata,
        )
    
    async def restore_chain(
        self,
        from_checkpoint_id: str,
        to_checkpoint_id: str | None = None,
    ) -> list[RestorationResult]:
        """
        Restore a chain of checkpoints in sequence.
        
        Useful for replaying session history.
        """
        # Get checkpoint chain
        chain = await self._checkpoint_manager.get_checkpoint_chain(from_checkpoint_id)
        
        if to_checkpoint_id:
            # Truncate chain at target
            target_indices = [
                i for i, cp in enumerate(chain) 
                if cp.id == to_checkpoint_id
            ]
            if target_indices:
                chain = chain[:target_indices[0] + 1]
        
        results = []
        accumulated_state: dict[str, Any] = {}
        
        for checkpoint in chain:
            result = await self.restore_from_checkpoint(
                checkpoint.id,
                require_coherence=False,
            )
            results.append(result)
            
            if result.status in (RestorationStatus.SUCCESS, RestorationStatus.PARTIAL):
                accumulated_state.update(result.state)
        
        return results
    
    async def preview_restore(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        """
        Preview what would be restored without actually restoring.
        
        Returns metadata about the checkpoint contents.
        """
        try:
            checkpoint = await self._checkpoint_manager.get(checkpoint_id)
        except KeyError:
            return {"error": "Checkpoint not found"}
        
        try:
            serialized = await self._backend.load(checkpoint_id)
            
            # Get state keys without full deserialization
            state_preview = {
                "checkpoint_id": checkpoint_id,
                "timestamp": checkpoint.timestamp,
                "type": checkpoint.type.value,
                "size_bytes": checkpoint.size_bytes,
                "compressed_size_bytes": checkpoint.compressed_size_bytes,
                "is_diff": serialized.get("is_diff", False),
                "base_checkpoint_id": serialized.get("base_checkpoint_id"),
                "format": serialized.get("format"),
                "compression": serialized.get("compression"),
            }
            
            return state_preview
            
        except Exception as e:
            return {"error": f"Failed to preview: {e}"}
    
    def get_coherence_manager(self) -> TemporalCoherenceManager:
        """Get the temporal coherence manager."""
        return self._coherence_manager