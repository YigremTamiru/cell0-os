"""
COL-Continuity Checkpoint Management

Automatic checkpoint creation and lifecycle management for Cell 0 OS.
Provides transparent checkpointing that doesn't disrupt user workflow.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from col.continuity.serializer import StateSerializer
from col.continuity.persistence import PersistenceBackend


class CheckpointType(Enum):
    """Types of checkpoints based on trigger mechanism."""
    AUTO = "auto"           # Automatic periodic checkpoint
    USER = "user"           # User-initiated checkpoint
    EVENT = "event"         # Event-triggered checkpoint
    SHUTDOWN = "shutdown"   # Graceful shutdown checkpoint
    CRITICAL = "critical"   # Critical operation checkpoint


class CheckpointStatus(Enum):
    """Status of a checkpoint."""
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    CORRUPTED = "corrupted"


@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint."""
    id: str
    timestamp: float
    type: CheckpointType
    status: CheckpointStatus
    parent_id: Optional[str] = None
    session_id: str = ""
    version: int = 1
    size_bytes: int = 0
    compressed_size_bytes: int = 0
    checksum: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type.value,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "session_id": self.session_id,
            "version": self.version,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "checksum": self.checksum,
            "tags": self.tags,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointMetadata:
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            type=CheckpointType(data["type"]),
            status=CheckpointStatus(data["status"]),
            parent_id=data.get("parent_id"),
            session_id=data.get("session_id", ""),
            version=data.get("version", 1),
            size_bytes=data.get("size_bytes", 0),
            compressed_size_bytes=data.get("compressed_size_bytes", 0),
            checksum=data.get("checksum", ""),
            tags=data.get("tags", []),
            description=data.get("description", ""),
        )


class CheckpointManager:
    """
    Manages checkpoint lifecycle: creation, validation, retention, and cleanup.
    
    Features:
    - Automatic checkpoint scheduling
    - Transparent operation (no user interruption)
    - Configurable retention policies
    - Incremental checkpoint chains
    """
    
    def __init__(
        self,
        storage_path: Path | str = ".col/continuity",
        auto_interval_seconds: float = 300.0,  # 5 minutes
        max_checkpoints: int = 50,
        serializer: StateSerializer | None = None,
        backend: PersistenceBackend | None = None,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.auto_interval = auto_interval_seconds
        self.max_checkpoints = max_checkpoints
        
        self._serializer = serializer or StateSerializer()
        self._backend = backend or PersistenceBackend(self.storage_path / "data")
        
        self._checkpoints: dict[str, CheckpointMetadata] = {}
        self._current_session_id: str = self._generate_session_id()
        self._last_checkpoint_id: Optional[str] = None
        
        self._auto_task: Optional[asyncio.Task] = None
        self._running = False
        
        self._state_provider: Optional[Callable[[], Coroutine[Any, Any, dict[str, Any]]]] = None
        self._hooks: dict[str, list[Callable]] = {
            "pre_checkpoint": [],
            "post_checkpoint": [],
            "checkpoint_failed": [],
        }
        
        # Load existing checkpoint index
        self._load_index()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session identifier."""
        return hashlib.sha256(
            f"{time.time()}.{id(self)}.{asyncio.get_event_loop().time()}".encode()
        ).hexdigest()[:16]
    
    def _load_index(self) -> None:
        """Load checkpoint index from disk."""
        index_path = self.storage_path / "checkpoints.json"
        if index_path.exists():
            try:
                with open(index_path, "r") as f:
                    data = json.load(f)
                for cp_data in data.get("checkpoints", []):
                    meta = CheckpointMetadata.from_dict(cp_data)
                    self._checkpoints[meta.id] = meta
                self._last_checkpoint_id = data.get("last_checkpoint_id")
            except Exception as e:
                print(f"[COL-Continuity] Warning: Could not load checkpoint index: {e}")
    
    def _save_index(self) -> None:
        """Save checkpoint index to disk."""
        index_path = self.storage_path / "checkpoints.json"
        data = {
            "checkpoints": [cp.to_dict() for cp in self._checkpoints.values()],
            "last_checkpoint_id": self._last_checkpoint_id,
            "current_session_id": self._current_session_id,
        }
        with open(index_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_state_provider(
        self, 
        provider: Callable[[], Coroutine[Any, Any, dict[str, Any]]]
    ) -> None:
        """Register an async function that provides the current state."""
        self._state_provider = provider
    
    def on(self, event: str, callback: Callable) -> None:
        """Register a hook for checkpoint events."""
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    async def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to registered hooks."""
        for callback in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                print(f"[COL-Continuity] Hook error ({event}): {e}")
    
    async def create(
        self,
        checkpoint_type: CheckpointType = CheckpointType.USER,
        description: str = "",
        tags: list[str] | None = None,
        state: dict[str, Any] | None = None,
    ) -> CheckpointMetadata:
        """
        Create a new checkpoint.
        
        Args:
            checkpoint_type: Type of checkpoint
            description: Human-readable description
            tags: Optional tags for categorization
            state: Optional state to checkpoint (if None, uses state_provider)
        
        Returns:
            CheckpointMetadata for the created checkpoint
        """
        checkpoint_id = hashlib.sha256(
            f"{time.time()}.{self._current_session_id}".encode()
        ).hexdigest()[:16]
        
        metadata = CheckpointMetadata(
            id=checkpoint_id,
            timestamp=time.time(),
            type=checkpoint_type,
            status=CheckpointStatus.PENDING,
            parent_id=self._last_checkpoint_id,
            session_id=self._current_session_id,
            description=description,
            tags=tags or [],
        )
        
        await self._emit("pre_checkpoint", metadata)
        
        try:
            # Get state if not provided
            if state is None:
                if self._state_provider is None:
                    raise RuntimeError("No state provider registered")
                state = await self._state_provider()
            
            # Serialize state
            serialized = await self._serializer.serialize(state, parent_checkpoint=metadata.parent_id)
            metadata.size_bytes = serialized["size_bytes"]
            metadata.compressed_size_bytes = serialized["compressed_size_bytes"]
            metadata.checksum = serialized["checksum"]
            
            # Persist
            await self._backend.store(metadata.id, serialized)
            
            # Update metadata
            metadata.status = CheckpointStatus.COMPLETE
            self._checkpoints[metadata.id] = metadata
            self._last_checkpoint_id = metadata.id
            
            # Save index
            self._save_index()
            
            # Cleanup old checkpoints
            await self._cleanup_old_checkpoints()
            
            await self._emit("post_checkpoint", metadata)
            
            return metadata
            
        except Exception as e:
            metadata.status = CheckpointStatus.FAILED
            await self._emit("checkpoint_failed", metadata, e)
            raise
    
    async def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints based on retention policy."""
        if len(self._checkpoints) <= self.max_checkpoints:
            return
        
        # Sort by timestamp, keep most recent
        sorted_cps = sorted(
            self._checkpoints.values(),
            key=lambda cp: cp.timestamp,
            reverse=True
        )
        
        to_remove = sorted_cps[self.max_checkpoints:]
        
        # Never remove the most recent checkpoint from each session type
        # and keep at least one checkpoint per type
        protected_types = {CheckpointType.SHUTDOWN, CheckpointType.CRITICAL}
        
        for cp in to_remove:
            if cp.type in protected_types:
                # Check if this is the most recent of its type
                type_cps = [c for c in sorted_cps if c.type == cp.type]
                if cp.id == type_cps[0].id:
                    continue
            
            try:
                await self._backend.delete(cp.id)
                del self._checkpoints[cp.id]
            except Exception as e:
                print(f"[COL-Continuity] Cleanup error for {cp.id}: {e}")
        
        self._save_index()
    
    async def get(self, checkpoint_id: str) -> CheckpointMetadata:
        """Get checkpoint metadata by ID."""
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint {checkpoint_id} not found")
        return self._checkpoints[checkpoint_id]
    
    async def list_checkpoints(
        self,
        checkpoint_type: CheckpointType | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[CheckpointMetadata]:
        """List checkpoints with optional filtering."""
        results = list(self._checkpoints.values())
        
        if checkpoint_type:
            results = [cp for cp in results if cp.type == checkpoint_type]
        
        if session_id:
            results = [cp for cp in results if cp.session_id == session_id]
        
        if tags:
            results = [cp for cp in results if any(t in cp.tags for t in tags)]
        
        # Sort by timestamp descending
        results.sort(key=lambda cp: cp.timestamp, reverse=True)
        
        return results[:limit]
    
    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if checkpoint_id not in self._checkpoints:
            return False
        
        try:
            await self._backend.delete(checkpoint_id)
            del self._checkpoints[checkpoint_id]
            
            if self._last_checkpoint_id == checkpoint_id:
                # Update last checkpoint to previous one
                remaining = sorted(
                    self._checkpoints.values(),
                    key=lambda cp: cp.timestamp,
                    reverse=True
                )
                self._last_checkpoint_id = remaining[0].id if remaining else None
            
            self._save_index()
            return True
        except Exception as e:
            print(f"[COL-Continuity] Delete error: {e}")
            return False
    
    async def verify(self, checkpoint_id: str) -> bool:
        """Verify checkpoint integrity."""
        if checkpoint_id not in self._checkpoints:
            return False
        
        metadata = self._checkpoints[checkpoint_id]
        
        try:
            data = await self._backend.load(checkpoint_id)
            computed_checksum = hashlib.sha256(
                data.get("payload", b"")
            ).hexdigest()
            return computed_checksum == metadata.checksum
        except Exception:
            return False
    
    async def start_auto_checkpointing(self) -> None:
        """Start automatic checkpointing in the background."""
        if self._running:
            return
        
        self._running = True
        self._auto_task = asyncio.create_task(self._auto_checkpoint_loop())
    
    async def stop_auto_checkpointing(self) -> None:
        """Stop automatic checkpointing."""
        self._running = False
        if self._auto_task:
            self._auto_task.cancel()
            try:
                await self._auto_task
            except asyncio.CancelledError:
                pass
            self._auto_task = None
    
    async def _auto_checkpoint_loop(self) -> None:
        """Background loop for automatic checkpoints."""
        while self._running:
            try:
                await asyncio.sleep(self.auto_interval)
                
                if self._state_provider:
                    await self.create(
                        checkpoint_type=CheckpointType.AUTO,
                        description="Automatic periodic checkpoint"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[COL-Continuity] Auto-checkpoint error: {e}")
    
    async def shutdown_checkpoint(self) -> CheckpointMetadata:
        """Create a shutdown checkpoint (call before exiting)."""
        return await self.create(
            checkpoint_type=CheckpointType.SHUTDOWN,
            description="Session shutdown checkpoint"
        )
    
    def get_current_session_id(self) -> str:
        """Get the current session ID."""
        return self._current_session_id
    
    def get_last_checkpoint_id(self) -> Optional[str]:
        """Get the most recent checkpoint ID."""
        return self._last_checkpoint_id
    
    async def get_checkpoint_chain(self, checkpoint_id: str) -> list[CheckpointMetadata]:
        """Get the chain of checkpoints leading to the given checkpoint."""
        chain = []
        current_id = checkpoint_id
        
        while current_id and current_id in self._checkpoints:
            cp = self._checkpoints[current_id]
            chain.append(cp)
            current_id = cp.parent_id
        
        return list(reversed(chain))