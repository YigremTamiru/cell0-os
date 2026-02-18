"""
COL Checkpoint Manager - Cell 0 OS
State persistence and recovery system.
"""

import gzip
import hashlib
import json
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


class CheckpointError(Exception):
    """Error during checkpoint operations."""
    pass


@dataclass
class Checkpoint:
    """A COL state checkpoint."""
    id: str
    timestamp: datetime
    version: str
    reason: str
    state: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    checksum: Optional[str] = None
    compressed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert checkpoint to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'reason': self.reason,
            'parent_id': self.parent_id,
            'checksum': self.checksum,
            'compressed': self.compressed,
            'metadata': self.metadata,
            'state_size': len(json.dumps(self.state)) if self.state else 0
        }
    
    def compute_checksum(self) -> str:
        """Compute checksum of state data."""
        state_json = json.dumps(self.state, sort_keys=True, default=str)
        return hashlib.sha256(state_json.encode()).hexdigest()[:16]
    
    def verify(self) -> bool:
        """Verify checkpoint integrity."""
        if not self.checksum:
            return True
        return self.compute_checksum() == self.checksum


@dataclass
class CheckpointPolicy:
    """Policy for automatic checkpointing."""
    enabled: bool = True
    max_checkpoints: int = 100
    max_age_days: int = 30
    compress_after_days: int = 7
    auto_checkpoint_interval_minutes: int = 60
    checkpoint_on_error: bool = True
    checkpoint_on_high_risk: bool = True
    keep_minimum: int = 10


class CheckpointManager:
    """
    Manages COL state checkpoints.
    
    Features:
    - Automatic checkpoint creation
    - State compression and archival
    - Incremental checkpoints (parent-child chain)
    - Integrity verification
    - Cross-session state persistence
    - Recovery from checkpoints
    """
    
    VERSION = "1.0"
    
    def __init__(self, policy: Optional[CheckpointPolicy] = None):
        self.policy = policy or CheckpointPolicy()
        self._lock = threading.RLock()
        self._checkpoint_dir = Path.home() / ".openclaw" / "col" / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of recent checkpoints
        self._cache: Dict[str, Checkpoint] = {}
        self._cache_size = 10
        
        # Checkpoint chain (for incremental checkpoints)
        self._current_chain: Optional[str] = None
        
        # Statistics
        self._stats = {
            'created': 0,
            'restored': 0,
            'deleted': 0,
            'verified': 0,
            'corrupted': 0
        }
        
        # Load checkpoint index
        self._load_index()
        
        # Cleanup old checkpoints on init
        self._cleanup_old_checkpoints()
    
    def _get_index_path(self) -> Path:
        """Get path to checkpoint index."""
        return self._checkpoint_dir / "checkpoint_index.json"
    
    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """Get filesystem path for a checkpoint."""
        return self._checkpoint_dir / f"checkpoint_{checkpoint_id}.json"
    
    def _get_compressed_path(self, checkpoint_id: str) -> Path:
        """Get filesystem path for a compressed checkpoint."""
        return self._checkpoint_dir / f"checkpoint_{checkpoint_id}.json.gz"
    
    def _load_index(self):
        """Load checkpoint index from disk."""
        index_path = self._get_index_path()
        if not index_path.exists():
            self._index: Dict[str, Dict] = {}
            return
        
        try:
            with open(index_path) as f:
                self._index = json.load(f)
        except Exception:
            self._index = {}
    
    def _save_index(self):
        """Save checkpoint index to disk."""
        index_path = self._get_index_path()
        with open(index_path, 'w') as f:
            json.dump(self._index, f, indent=2)
    
    def create_checkpoint(
        self,
        state: Dict[str, Any],
        reason: str = "manual",
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Checkpoint:
        """
        Create a new checkpoint.
        
        Args:
            state: State data to checkpoint
            reason: Why this checkpoint was created
            parent_id: Parent checkpoint for incremental chain
            metadata: Additional metadata
        
        Returns:
            Created Checkpoint
        """
        if not self.policy.enabled:
            raise CheckpointError("Checkpointing is disabled")
        
        with self._lock:
            # Generate checkpoint ID
            checkpoint_id = f"cp_{int(time.time()*1000)}_{str(uuid.uuid4())[:8]}"
            
            # Create checkpoint
            checkpoint = Checkpoint(
                id=checkpoint_id,
                timestamp=datetime.utcnow(),
                version=self.VERSION,
                reason=reason,
                state=state,
                parent_id=parent_id or self._current_chain,
                metadata=metadata or {}
            )
            
            # Compute and store checksum
            checkpoint.checksum = checkpoint.compute_checksum()
            
            # Save to disk
            self._save_checkpoint(checkpoint)
            
            # Update index
            self._index[checkpoint_id] = checkpoint.to_dict()
            self._save_index()
            
            # Add to cache
            self._cache[checkpoint_id] = checkpoint
            self._trim_cache()
            
            # Update chain
            self._current_chain = checkpoint_id
            
            # Update stats
            self._stats['created'] += 1
            
            # Cleanup if needed
            self._cleanup_if_needed()
            
            return checkpoint
    
    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Save checkpoint to disk."""
        checkpoint_path = self._get_checkpoint_path(checkpoint.id)
        
        data = {
            'id': checkpoint.id,
            'timestamp': checkpoint.timestamp.isoformat(),
            'version': checkpoint.version,
            'reason': checkpoint.reason,
            'state': checkpoint.state,
            'parent_id': checkpoint.parent_id,
            'checksum': checkpoint.checksum,
            'compressed': False,
            'metadata': checkpoint.metadata
        }
        
        with open(checkpoint_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_emergency_checkpoint(self, state: Optional[Dict] = None) -> Checkpoint:
        """Create emergency checkpoint (high priority)."""
        return self.create_checkpoint(
            state=state or {},
            reason="emergency",
            metadata={'emergency': True, 'priority': 'critical'}
        )
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint by ID."""
        # Check cache first
        if checkpoint_id in self._cache:
            return self._cache[checkpoint_id]
        
        # Load from disk
        checkpoint_path = self._get_checkpoint_path(checkpoint_id)
        compressed_path = self._get_compressed_path(checkpoint_id)
        
        try:
            if checkpoint_path.exists():
                with open(checkpoint_path) as f:
                    data = json.load(f)
                compressed = False
            elif compressed_path.exists():
                with gzip.open(compressed_path, 'rt') as f:
                    data = json.load(f)
                compressed = True
            else:
                return None
            
            checkpoint = Checkpoint(
                id=data['id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                version=data['version'],
                reason=data['reason'],
                state=data.get('state', {}),
                parent_id=data.get('parent_id'),
                checksum=data.get('checksum'),
                compressed=compressed,
                metadata=data.get('metadata', {})
            )
            
            # Add to cache
            self._cache[checkpoint_id] = checkpoint
            
            return checkpoint
            
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint {checkpoint_id}: {e}")
    
    def get_latest(self, reason_filter: Optional[str] = None) -> Optional[Checkpoint]:
        """Get the most recent checkpoint."""
        if not self._index:
            return None
        
        # Sort by timestamp
        sorted_checkpoints = sorted(
            self._index.items(),
            key=lambda x: x[1]['timestamp'],
            reverse=True
        )
        
        for checkpoint_id, info in sorted_checkpoints:
            if reason_filter and info['reason'] != reason_filter:
                continue
            return self.get_checkpoint(checkpoint_id)
        
        return None
    
    def list_checkpoints(
        self,
        reason: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """List available checkpoints."""
        results = []
        
        for checkpoint_id, info in self._index.items():
            # Apply filters
            if reason and info['reason'] != reason:
                continue
            
            if since:
                checkpoint_time = datetime.fromisoformat(info['timestamp'])
                if checkpoint_time < since:
                    continue
            
            results.append(info)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return results[:limit]
    
    def restore_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Restore state from a checkpoint.
        
        Returns:
            The checkpointed state
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise CheckpointError(f"Checkpoint {checkpoint_id} not found")
        
        # Verify integrity
        if not checkpoint.verify():
            self._stats['corrupted'] += 1
            raise CheckpointError(f"Checkpoint {checkpoint_id} is corrupted")
        
        self._stats['restored'] += 1
        self._stats['verified'] += 1
        
        return checkpoint.state
    
    def delete_checkpoint(self, checkpoint_id: str):
        """Delete a checkpoint."""
        with self._lock:
            # Remove from cache
            self._cache.pop(checkpoint_id, None)
            
            # Remove files
            checkpoint_path = self._get_checkpoint_path(checkpoint_id)
            compressed_path = self._get_compressed_path(checkpoint_id)
            
            checkpoint_path.unlink(missing_ok=True)
            compressed_path.unlink(missing_ok=True)
            
            # Remove from index
            self._index.pop(checkpoint_id, None)
            self._save_index()
            
            self._stats['deleted'] += 1
    
    def compress_checkpoint(self, checkpoint_id: str) -> bool:
        """Compress a checkpoint to save space."""
        checkpoint_path = self._get_checkpoint_path(checkpoint_id)
        compressed_path = self._get_compressed_path(checkpoint_id)
        
        if not checkpoint_path.exists():
            return False
        
        try:
            with open(checkpoint_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed version
            checkpoint_path.unlink()
            
            # Update index
            if checkpoint_id in self._index:
                self._index[checkpoint_id]['compressed'] = True
                self._save_index()
            
            return True
        except Exception:
            return False
    
    def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """Verify checkpoint integrity."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False
        
        valid = checkpoint.verify()
        if valid:
            self._stats['verified'] += 1
        else:
            self._stats['corrupted'] += 1
        
        return valid
    
    def verify_all(self) -> Dict[str, bool]:
        """Verify all checkpoints."""
        results = {}
        for checkpoint_id in self._index:
            results[checkpoint_id] = self.verify_checkpoint(checkpoint_id)
        return results
    
    def get_checkpoint_chain(self, checkpoint_id: str) -> List[Checkpoint]:
        """Get chain of checkpoints from root to given checkpoint."""
        chain = []
        current_id = checkpoint_id
        
        while current_id:
            checkpoint = self.get_checkpoint(current_id)
            if not checkpoint:
                break
            chain.append(checkpoint)
            current_id = checkpoint.parent_id
        
        # Reverse to get root -> leaf order
        chain.reverse()
        return chain
    
    def diff_checkpoints(
        self,
        checkpoint_id_1: str,
        checkpoint_id_2: str
    ) -> Dict[str, Any]:
        """Calculate diff between two checkpoints."""
        cp1 = self.get_checkpoint(checkpoint_id_1)
        cp2 = self.get_checkpoint(checkpoint_id_2)
        
        if not cp1 or not cp2:
            raise CheckpointError("One or both checkpoints not found")
        
        return self._dict_diff(cp1.state, cp2.state)
    
    def _dict_diff(self, d1: Dict, d2: Dict) -> Dict[str, Any]:
        """Calculate difference between two dictionaries."""
        diff = {
            'added': {},
            'removed': {},
            'modified': {}
        }
        
        all_keys = set(d1.keys()) | set(d2.keys())
        
        for key in all_keys:
            if key not in d1:
                diff['added'][key] = d2[key]
            elif key not in d2:
                diff['removed'][key] = d1[key]
            elif d1[key] != d2[key]:
                diff['modified'][key] = {
                    'old': d1[key],
                    'new': d2[key]
                }
        
        return diff
    
    def _cleanup_if_needed(self):
        """Cleanup old checkpoints if over limit."""
        if len(self._index) <= self.policy.max_checkpoints:
            return
        
        # Sort by timestamp
        sorted_cps = sorted(
            self._index.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        # Delete oldest until under limit (keeping minimum)
        to_delete = len(self._index) - self.policy.max_checkpoints
        for checkpoint_id, _ in sorted_cps[:to_delete]:
            if len(self._index) <= self.policy.keep_minimum:
                break
            self.delete_checkpoint(checkpoint_id)
    
    def _cleanup_old_checkpoints(self):
        """Cleanup checkpoints based on age policy."""
        cutoff = datetime.utcnow() - timedelta(days=self.policy.max_age_days)
        compress_cutoff = datetime.utcnow() - timedelta(days=self.policy.compress_after_days)
        
        for checkpoint_id, info in list(self._index.items()):
            checkpoint_time = datetime.fromisoformat(info['timestamp'])
            
            # Delete old checkpoints
            if checkpoint_time < cutoff:
                if len(self._index) > self.policy.keep_minimum:
                    self.delete_checkpoint(checkpoint_id)
                    continue
            
            # Compress older checkpoints
            if checkpoint_time < compress_cutoff and not info.get('compressed'):
                self.compress_checkpoint(checkpoint_id)
    
    def _trim_cache(self):
        """Trim in-memory cache to size limit."""
        while len(self._cache) > self._cache_size:
            # Remove oldest
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get checkpoint manager statistics."""
        return {
            **self._stats,
            'total_checkpoints': len(self._index),
            'cached_checkpoints': len(self._cache),
            'checkpoint_dir_size_mb': self._get_directory_size(),
            'policy': {
                'max_checkpoints': self.policy.max_checkpoints,
                'max_age_days': self.policy.max_age_days,
                'auto_checkpoint': self.policy.enabled
            }
        }
    
    def _get_directory_size(self) -> float:
        """Get total size of checkpoint directory in MB."""
        total = 0
        for path in self._checkpoint_dir.rglob('*'):
            if path.is_file():
                total += path.stat().st_size
        return round(total / (1024 * 1024), 2)
    
    def export_checkpoint(self, checkpoint_id: str, export_path: Path):
        """Export checkpoint to external file."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise CheckpointError(f"Checkpoint {checkpoint_id} not found")
        
        with open(export_path, 'w') as f:
            json.dump({
                'checkpoint': checkpoint.to_dict(),
                'state': checkpoint.state
            }, f, indent=2, default=str)
    
    def import_checkpoint(self, import_path: Path) -> Checkpoint:
        """Import checkpoint from external file."""
        with open(import_path) as f:
            data = json.load(f)
        
        checkpoint_data = data.get('checkpoint', data)  # Handle both formats
        state = data.get('state', checkpoint_data.get('state', {}))
        
        # Create new checkpoint with imported data
        return self.create_checkpoint(
            state=state,
            reason=f"imported_from_{import_path.name}",
            metadata={'imported': True, 'original_id': checkpoint_data.get('id')}
        )