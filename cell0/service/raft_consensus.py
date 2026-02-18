"""
Cell0 Raft Consensus Service

Distributed consensus integration for multi-node Cell0 clusters.
Provides leader election and log replication using the Raft algorithm.
"""

import asyncio
import json
import logging
import time
import struct
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum, auto
from pathlib import Path

logger = logging.getLogger(__name__)


class RaftState(Enum):
    """Raft node states."""
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()


@dataclass
class RaftConfig:
    """Configuration for a Raft node."""
    node_id: int
    peers: List[int]  # List of peer node IDs
    host: str = "127.0.0.1"
    port: int = 19000
    election_timeout_min: float = 0.15  # 150ms
    election_timeout_max: float = 0.30  # 300ms
    heartbeat_interval: float = 0.05    # 50ms
    data_dir: Path = Path("/tmp/cell0_raft")


@dataclass
class LogEntry:
    """Single entry in the replicated log."""
    term: int
    index: int
    data: bytes
    entry_type: str = "command"
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        header = struct.pack(">III", self.term, self.index, len(self.data))
        type_bytes = self.entry_type.encode()
        type_len = struct.pack(">I", len(type_bytes))
        return header + type_len + type_bytes + self.data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LogEntry':
        """Deserialize from bytes."""
        term, index, data_len = struct.unpack(">III", data[:12])
        type_len = struct.unpack(">I", data[12:16])[0]
        entry_type = data[16:16+type_len].decode()
        entry_data = data[16+type_len:16+type_len+data_len]
        return cls(term, index, entry_data, entry_type)


@dataclass
class RaftStatus:
    """Node status information."""
    node_id: int
    state: str
    term: int
    leader_id: int
    commit_index: int
    last_applied: int
    log_size: int


class RaftConsensusService:
    """
    Raft consensus service for distributed agreement.
    
    Features:
    - Leader election with randomized timeouts
    - Log replication to all peers
    - Persistent state storage
    - Integration with Rust kernel via IPC
    """
    
    def __init__(self, config: RaftConfig):
        self.config = config
        self.state = RaftState.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[int] = None
        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0
        self.leader_id = 0
        self.votes_received: List[int] = []
        
        # Network state
        self.peers: Dict[int, Dict[str, Any]] = {}
        self.running = False
        self.election_timer: Optional[asyncio.Task] = None
        self.heartbeat_timer: Optional[asyncio.Task] = None
        
        # Callbacks
        self.on_state_change: Optional[Callable] = None
        self.on_leader_elected: Optional[Callable] = None
        self.on_commit: Optional[Callable] = None
        
        # Ensure data directory exists
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persistent state
        self._load_state()
    
    def _load_state(self):
        """Load persistent state from disk."""
        state_file = self.config.data_dir / f"node_{self.config.node_id}_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                self.current_term = data.get('current_term', 0)
                self.voted_for = data.get('voted_for')
                self.commit_index = data.get('commit_index', 0)
                self.last_applied = data.get('last_applied', 0)
                logger.info(f"Loaded state: term={self.current_term}, log={len(self.log)} entries")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save persistent state to disk."""
        state_file = self.config.data_dir / f"node_{self.config.node_id}_state.json"
        try:
            data = {
                'current_term': self.current_term,
                'voted_for': self.voted_for,
                'commit_index': self.commit_index,
                'last_applied': self.last_applied,
            }
            with open(state_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _last_log_index(self) -> int:
        """Get the last log index."""
        return len(self.log)
    
    def _last_log_term(self) -> int:
        """Get the term of the last log entry."""
        if not self.log:
            return 0
        return self.log[-1].term
    
    async def start(self):
        """Start the Raft service."""
        if self.running:
            return
        
        self.running = True
        logger.info(f"Starting Raft node {self.config.node_id} on {self.config.host}:{self.config.port}")
        
        # Start election timer
        self.election_timer = asyncio.create_task(self._election_loop())
        
        # Start server for peer communication
        await self._start_server()
        
        logger.info("Raft service started")
    
    async def stop(self):
        """Stop the Raft service."""
        self.running = False
        
        if self.election_timer:
            self.election_timer.cancel()
            try:
                await self.election_timer
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
            try:
                await self.heartbeat_timer
            except asyncio.CancelledError:
                pass
        
        self._save_state()
        logger.info("Raft service stopped")
    
    async def _election_loop(self):
        """Main election timeout loop."""
        while self.running:
            if self.state == RaftState.LEADER:
                await asyncio.sleep(self.config.heartbeat_interval)
                continue
            
            # Randomized election timeout
            timeout = self.config.election_timeout_min + (
                (self.config.election_timeout_max - self.config.election_timeout_min) * 
                (time.time() % 1.0)  # Simple random
            )
            
            await asyncio.sleep(timeout)
            
            if self.running and self.state != RaftState.LEADER:
                await self._start_election()
    
    async def _start_election(self):
        """Start a new election."""
        self.state = RaftState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.config.node_id
        self.votes_received = [self.config.node_id]
        
        logger.info(f"Starting election for term {self.current_term}")
        
        # Request votes from all peers
        await self._broadcast_request_vote()
        
        # Check if we have majority
        if len(self.votes_received) >= self._quorum():
            await self._become_leader()
        
        self._save_state()
    
    async def _become_leader(self):
        """Transition to leader state."""
        old_state = self.state
        self.state = RaftState.LEADER
        self.leader_id = self.config.node_id
        
        logger.info(f"Became leader for term {self.current_term}")
        
        if self.on_state_change:
            await self._call_callback(self.on_state_change, old_state, self.state)
        
        if self.on_leader_elected:
            await self._call_callback(self.on_leader_elected, self.config.node_id, self.current_term)
        
        # Start heartbeat timer
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self.heartbeat_timer = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats as leader."""
        while self.running and self.state == RaftState.LEADER:
            await self._broadcast_append_entries()
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _broadcast_request_vote(self):
        """Send RequestVote RPCs to all peers."""
        message = {
            'type': 'request_vote',
            'term': self.current_term,
            'candidate_id': self.config.node_id,
            'last_log_index': self._last_log_index(),
            'last_log_term': self._last_log_term()
        }
        
        for peer_id in self.config.peers:
            asyncio.create_task(self._send_to_peer(peer_id, message))
    
    async def _broadcast_append_entries(self, entries: List[LogEntry] = None):
        """Send AppendEntries RPCs to all peers."""
        if entries is None:
            entries = []
        
        message = {
            'type': 'append_entries',
            'term': self.current_term,
            'leader_id': self.config.node_id,
            'prev_log_index': self._last_log_index(),
            'prev_log_term': self._last_log_term(),
            'entries': [e.to_bytes().hex() for e in entries],
            'leader_commit': self.commit_index
        }
        
        for peer_id in self.config.peers:
            asyncio.create_task(self._send_to_peer(peer_id, message))
    
    async def _send_to_peer(self, peer_id: int, message: dict):
        """Send a message to a peer."""
        # This would be implemented with actual network I/O
        # For now, just log it
        logger.debug(f"Send to peer {peer_id}: {message['type']}")
    
    async def _start_server(self):
        """Start the server for receiving peer messages."""
        # This would start a TCP server
        # Implementation depends on the network layer
        pass
    
    def _quorum(self) -> int:
        """Calculate quorum size (majority)."""
        cluster_size = len(self.config.peers) + 1
        return (cluster_size // 2) + 1
    
    async def _call_callback(self, callback: Callable, *args):
        """Safely call a callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    # RPC Handlers
    
    async def handle_request_vote(self, term: int, candidate_id: int, 
                                  last_log_index: int, last_log_term: int) -> dict:
        """Handle RequestVote RPC."""
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.state = RaftState.FOLLOWER
        
        vote_granted = False
        
        if term >= self.current_term:
            can_vote = self.voted_for is None or self.voted_for == candidate_id
            
            log_up_to_date = (
                last_log_term > self._last_log_term() or
                (last_log_term == self._last_log_term() and last_log_index >= self._last_log_index())
            )
            
            if can_vote and log_up_to_date:
                self.voted_for = candidate_id
                vote_granted = True
        
        self._save_state()
        
        return {
            'term': self.current_term,
            'vote_granted': vote_granted
        }
    
    async def handle_append_entries(self, term: int, leader_id: int,
                                    prev_log_index: int, prev_log_term: int,
                                    entries: List[bytes], leader_commit: int) -> dict:
        """Handle AppendEntries RPC."""
        if term < self.current_term:
            return {'term': self.current_term, 'success': False}
        
        self.leader_id = leader_id
        
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.state = RaftState.FOLLOWER
        elif self.state == RaftState.CANDIDATE:
            self.state = RaftState.FOLLOWER
        
        # Check log consistency
        if prev_log_index > 0:
            if prev_log_index > len(self.log):
                return {'term': self.current_term, 'success': False}
            
            if self.log[prev_log_index - 1].term != prev_log_term:
                # Delete conflicting entries
                self.log = self.log[:prev_log_index - 1]
                return {'term': self.current_term, 'success': False}
        
        # Append new entries
        for entry_data in entries:
            entry = LogEntry.from_bytes(entry_data)
            if entry.index <= len(self.log):
                if self.log[entry.index - 1].term != entry.term:
                    self.log = self.log[:entry.index - 1]
                    self.log.append(entry)
            else:
                self.log.append(entry)
        
        # Update commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))
            await self._apply_committed()
        
        self._save_state()
        
        return {'term': self.current_term, 'success': True}
    
    async def _apply_committed(self):
        """Apply committed entries to state machine."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            
            if self.on_commit:
                await self._call_callback(self.on_commit, entry)
    
    # Client API
    
    async def propose(self, data: bytes, entry_type: str = "command") -> Optional[LogEntry]:
        """Propose a command to the cluster."""
        if self.state != RaftState.LEADER:
            return None
        
        entry = LogEntry(
            term=self.current_term,
            index=self._last_log_index() + 1,
            data=data,
            entry_type=entry_type
        )
        
        self.log.append(entry)
        await self._broadcast_append_entries([entry])
        self._save_state()
        
        return entry
    
    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self.state == RaftState.LEADER
    
    def get_leader(self) -> Optional[int]:
        """Get the current leader ID."""
        return self.leader_id if self.leader_id != 0 else None
    
    def get_status(self) -> RaftStatus:
        """Get current node status."""
        return RaftStatus(
            node_id=self.config.node_id,
            state=self.state.name,
            term=self.current_term,
            leader_id=self.leader_id,
            commit_index=self.commit_index,
            last_applied=self.last_applied,
            log_size=len(self.log)
        )


# FastAPI integration
async def setup_raft_service(app: Any, node_id: int, peers: List[int]) -> RaftConsensusService:
    """Set up Raft consensus service for a FastAPI app."""
    config = RaftConfig(
        node_id=node_id,
        peers=peers
    )
    
    service = RaftConsensusService(config)
    
    @app.on_event("startup")
    async def start_raft():
        await service.start()
    
    @app.on_event("shutdown")
    async def stop_raft():
        await service.stop()
    
    # Add API endpoints
    @app.get("/raft/status")
    async def raft_status():
        return asdict(service.get_status())
    
    @app.post("/raft/propose")
    async def raft_propose(data: dict):
        if not service.is_leader():
            leader = service.get_leader()
            raise HTTPException(
                status_code=403,
                detail=f"Not leader. Current leader: {leader}"
            )
        
        entry = await service.propose(
            json.dumps(data).encode(),
            entry_type="command"
        )
        
        if entry is None:
            raise HTTPException(status_code=500, detail="Failed to propose")
        
        return {
            'success': True,
            'entry': {
                'term': entry.term,
                'index': entry.index
            }
        }
    
    return service
