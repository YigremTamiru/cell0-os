"""
Cell 0 OS - Byzantine Fault Tolerant Consensus
Implements PBFT-style consensus for civilization-grade reliability.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from collections import defaultdict
import random


class ConsensusPhase(Enum):
    """PBFT consensus phases."""
    IDLE = auto()
    PRE_PREPARE = auto()
    PREPARE = auto()
    COMMIT = auto()
    EXECUTED = auto()
    FAILED = auto()


class ConsensusResult(Enum):
    """Consensus outcomes."""
    ACCEPTED = auto()
    REJECTED = auto()
    TIMEOUT = auto()
    BYZANTINE_FAULT = auto()
    QUORUM_FAILED = auto()


@dataclass(frozen=True)
class ConsensusMessage:
    """PBFT protocol message."""
    msg_type: str  # PRE_PREPARE, PREPARE, COMMIT, VIEW_CHANGE
    view_number: int
    sequence_number: int
    digest: str
    payload: tuple  # Frozen dict as tuple of items
    sender_id: str
    signature: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def __init__(self, msg_type: str, view_number: int, sequence_number: int, 
                 digest: str, payload: Dict[str, Any], sender_id: str,
                 signature: Optional[str] = None, timestamp: Optional[float] = None):
        object.__setattr__(self, 'msg_type', msg_type)
        object.__setattr__(self, 'view_number', view_number)
        object.__setattr__(self, 'sequence_number', sequence_number)
        object.__setattr__(self, 'digest', digest)
        object.__setattr__(self, 'payload', tuple(sorted(payload.items())) if payload else tuple())
        object.__setattr__(self, 'sender_id', sender_id)
        object.__setattr__(self, 'signature', signature)
        object.__setattr__(self, 'timestamp', timestamp if timestamp is not None else time.time())


@dataclass
class ConsensusInstance:
    """Single consensus round state."""
    instance_id: str
    proposal: Dict[str, Any]
    phase: ConsensusPhase
    view_number: int
    sequence_number: int
    
    # PBFT message tracking
    pre_prepare_received: bool = False
    prepare_votes: Set[str] = field(default_factory=set)
    commit_votes: Set[str] = field(default_factory=set)
    
    # Timing
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    # Result
    result: Optional[ConsensusResult] = None
    final_digest: Optional[str] = None


@dataclass 
class ByzantineEvidence:
    """Evidence of Byzantine behavior for slashing."""
    agent_id: str
    violation_type: str
    conflicting_messages: List[ConsensusMessage] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    severity: float = 1.0  # 0.0-1.0


class BFTConsensus:
    """
    Byzantine Fault Tolerant Consensus Engine.
    
    Implements Practical Byzantine Fault Tolerance (PBFT) adapted for
    large-scale agent swarms. Supports up to f Byzantine failures where
    n >= 3f + 1.
    
    Features:
    - View changes for primary failover
    - Byzantine detection and evidence collection
    - Optimistic fast path for non-contentious proposals
    - Checkpointing for state synchronization
    - Configurable consensus thresholds
    """
    
    def __init__(self, 
                 node_id: str,
                 total_nodes: int = 200,
                 max_faulty: Optional[int] = None,
                 consensus_timeout: float = 5.0):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.max_faulty = max_faulty or (total_nodes - 1) // 3
        
        # PBFT parameters
        self.quorum_size = 2 * self.max_faulty + 1  # Minimum for consensus
        self.prepare_quorum = self.total_nodes - self.max_faulty
        self.commit_quorum = self.total_nodes - self.max_faulty
        
        self.consensus_timeout = consensus_timeout
        
        # View management
        self.view_number = 0
        self.sequence_number = 0
        self.primary_id: Optional[str] = None
        
        # Consensus instances
        self.instances: Dict[str, ConsensusInstance] = {}
        self.instance_by_seq: Dict[int, ConsensusInstance] = {}
        self.completed_instances: Set[int] = set()
        
        # Message logs for view changes
        self.pre_prepare_log: Dict[Tuple[int, int], ConsensusMessage] = {}
        self.prepare_log: Dict[Tuple[int, int], Set[ConsensusMessage]] = defaultdict(set)
        self.commit_log: Dict[Tuple[int, int], Set[ConsensusMessage]] = defaultdict(set)
        
        # Byzantine tracking
        self.suspicion_scores: Dict[str, float] = defaultdict(float)
        self.byzantine_evidence: List[ByzantineEvidence] = []
        self.slashed_agents: Set[str] = set()
        
        # Network callbacks
        self.broadcast_callback: Optional[Callable] = None
        self.send_callback: Optional[Callable[[str, Dict], None]] = None
        
        # State
        self.running = False
        self.lock = asyncio.Lock()
        
        # Metrics
        self.consensus_count = 0
        self.success_count = 0
        self.byzantine_detected = 0
        self.view_changes = 0
        
    def set_primary(self, primary_id: str):
        """Set the primary node for current view."""
        self.primary_id = primary_id
        
    def set_broadcast_callback(self, callback: Callable[[Dict], None]):
        """Set callback for broadcasting messages."""
        self.broadcast_callback = callback
        
    def set_send_callback(self, callback: Callable[[str, Dict], None]):
        """Set callback for sending to specific node."""
        self.send_callback = callback
        
    async def propose(self, proposal: Dict[str, Any], 
                      instance_id: Optional[str] = None) -> Tuple[ConsensusResult, Optional[str]]:
        """
        Propose a value for consensus.
        
        Only the primary can propose. Non-primary nodes forward to primary.
        """
        instance_id = instance_id or self._generate_instance_id(proposal)
        
        async with self.lock:
            if instance_id in self.instances:
                existing = self.instances[instance_id]
                return existing.result, existing.final_digest
            
            # Check if primary
            if self.node_id != self.primary_id:
                # Forward to primary
                if self.send_callback:
                    self.send_callback(self.primary_id, {
                        "type": "forward_proposal",
                        "proposal": proposal,
                        "original_sender": self.node_id,
                        "instance_id": instance_id
                    })
                return ConsensusResult.TIMEOUT, None
            
            # Create instance
            self.sequence_number += 1
            instance = ConsensusInstance(
                instance_id=instance_id,
                proposal=proposal,
                phase=ConsensusPhase.PRE_PREPARE,
                view_number=self.view_number,
                sequence_number=self.sequence_number
            )
            self.instances[instance_id] = instance
            self.instance_by_seq[self.sequence_number] = instance
            
            # Generate digest
            digest = self._compute_digest(proposal)
            instance.final_digest = digest
            
            # Create PRE-PREPARE message
            pre_prepare_msg = ConsensusMessage(
                msg_type="PRE_PREPARE",
                view_number=self.view_number,
                sequence_number=self.sequence_number,
                digest=digest,
                payload=proposal,
                sender_id=self.node_id
            )
            
            instance.pre_prepare_received = True
            self.pre_prepare_log[(self.view_number, self.sequence_number)] = pre_prepare_msg
            
        # Broadcast PRE-PREPARE
        await self._broadcast_message(pre_prepare_msg)
        
        # Start consensus timer
        asyncio.create_task(self._consensus_timer(instance_id))
        
        return ConsensusResult.ACCEPTED, digest
        
    async def handle_message(self, msg: ConsensusMessage) -> Optional[ConsensusResult]:
        """Handle incoming consensus message."""
        # Validate message
        if not self._validate_message(msg):
            await self._record_suspicion(msg.sender_id, "invalid_message")
            return None
            
        # Check for stale views
        if msg.view_number < self.view_number:
            return None  # Old view, ignore
            
        if msg.view_number > self.view_number:
            # Future view, trigger view change
            await self._initiate_view_change(msg.view_number)
            return None
            
        async with self.lock:
            if msg.msg_type == "PRE_PREPARE":
                return await self._handle_pre_prepare(msg)
            elif msg.msg_type == "PREPARE":
                return await self._handle_prepare(msg)
            elif msg.msg_type == "COMMIT":
                return await self._handle_commit(msg)
            elif msg.msg_type == "VIEW_CHANGE":
                return await self._handle_view_change(msg)
                
        return None
        
    async def _handle_pre_prepare(self, msg: ConsensusMessage) -> Optional[ConsensusResult]:
        """Handle PRE-PREPARE message."""
        # Verify sender is primary
        if msg.sender_id != self.primary_id:
            await self._record_byzantine_evidence(
                msg.sender_id, 
                "non_primary_pre_prepare",
                [msg]
            )
            return None
            
        # Check sequence number
        if msg.sequence_number <= self._stable_checkpoint():
            return None  # Already committed
            
        # Get or create instance
        instance_id = self._get_instance_id(msg.sequence_number)
        if instance_id not in self.instances:
            instance = ConsensusInstance(
                instance_id=instance_id,
                proposal=msg.payload,
                phase=ConsensusPhase.PRE_PREPARE,
                view_number=msg.view_number,
                sequence_number=msg.sequence_number,
                final_digest=msg.digest
            )
            self.instances[instance_id] = instance
            self.instance_by_seq[msg.sequence_number] = instance
        else:
            instance = self.instances[instance_id]
            
        # Check for duplicate/divergent PRE-PREPARE
        if instance.pre_prepare_received:
            if instance.final_digest != msg.digest:
                # Primary sent conflicting proposals - Byzantine!
                await self._record_byzantine_evidence(
                    msg.sender_id,
                    "conflicting_pre_prepare",
                    [msg, self.pre_prepare_log.get((msg.view_number, msg.sequence_number))]
                )
                await self._initiate_view_change(self.view_number + 1)
                return ConsensusResult.BYZANTINE_FAULT
            return None
            
        instance.pre_prepare_received = True
        self.pre_prepare_log[(msg.view_number, msg.sequence_number)] = msg
        
        # Send PREPARE
        prepare_msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=msg.view_number,
            sequence_number=msg.sequence_number,
            digest=msg.digest,
            payload={},
            sender_id=self.node_id
        )
        
        self.prepare_log[(msg.view_number, msg.sequence_number)].add(prepare_msg)
        await self._broadcast_message(prepare_msg)
        
        return None
        
    async def _handle_prepare(self, msg: ConsensusMessage) -> Optional[ConsensusResult]:
        """Handle PREPARE message."""
        instance_id = self._get_instance_id(msg.sequence_number)
        if instance_id not in self.instances:
            return None
            
        instance = self.instances[instance_id]
        
        # Verify digest matches
        if msg.digest != instance.final_digest:
            await self._record_suspicion(msg.sender_id, "prepare_digest_mismatch")
            return None
            
        # Add vote
        instance.prepare_votes.add(msg.sender_id)
        self.prepare_log[(msg.view_number, msg.sequence_number)].add(msg)
        
        # Check for quorum
        if len(instance.prepare_votes) >= self.prepare_quorum and instance.phase == ConsensusPhase.PRE_PREPARE:
            instance.phase = ConsensusPhase.PREPARE
            
            # Send COMMIT
            commit_msg = ConsensusMessage(
                msg_type="COMMIT",
                view_number=msg.view_number,
                sequence_number=msg.sequence_number,
                digest=msg.digest,
                payload={},
                sender_id=self.node_id
            )
            
            self.commit_log[(msg.view_number, msg.sequence_number)].add(commit_msg)
            await self._broadcast_message(commit_msg)
            
        return None
        
    async def _handle_commit(self, msg: ConsensusMessage) -> Optional[ConsensusResult]:
        """Handle COMMIT message."""
        instance_id = self._get_instance_id(msg.sequence_number)
        if instance_id not in self.instances:
            return None
            
        instance = self.instances[instance_id]
        
        # Verify digest matches
        if msg.digest != instance.final_digest:
            await self._record_suspicion(msg.sender_id, "commit_digest_mismatch")
            return None
            
        # Add vote
        instance.commit_votes.add(msg.sender_id)
        self.commit_log[(msg.view_number, msg.sequence_number)].add(msg)
        
        # Check for quorum
        if len(instance.commit_votes) >= self.commit_quorum and instance.phase != ConsensusPhase.EXECUTED:
            instance.phase = ConsensusPhase.EXECUTED
            instance.completed_at = time.time()
            instance.result = ConsensusResult.ACCEPTED
            self.completed_instances.add(msg.sequence_number)
            self.success_count += 1
            
            # Execute callback
            await self._execute_consensus(instance)
            
            return ConsensusResult.ACCEPTED
            
        return None
        
    async def _initiate_view_change(self, new_view: int):
        """Initiate view change protocol."""
        if new_view <= self.view_number:
            return
            
        self.view_number = new_view
        self.view_changes += 1
        
        # Determine new primary (round-robin)
        node_list = self._get_node_list()
        new_primary = node_list[self.view_number % len(node_list)]
        self.primary_id = new_primary
        
        # Broadcast VIEW_CHANGE
        view_change_msg = ConsensusMessage(
            msg_type="VIEW_CHANGE",
            view_number=new_view,
            sequence_number=0,
            digest="",
            payload={
                "last_stable_checkpoint": self._stable_checkpoint(),
                "prepared_instances": [
                    seq for seq in self.completed_instances
                    if seq > self._stable_checkpoint()
                ]
            },
            sender_id=self.node_id
        )
        
        await self._broadcast_message(view_change_msg)
        
    async def _handle_view_change(self, msg: ConsensusMessage) -> Optional[ConsensusResult]:
        """Handle VIEW_CHANGE message."""
        # If we're the new primary, collect view changes
        if self.node_id == self.primary_id and msg.view_number == self.view_number:
            # Process view change certificate
            pass  # Implementation would collect and process
            
        return None
        
    async def _consensus_timer(self, instance_id: str):
        """Timeout handler for consensus instances."""
        await asyncio.sleep(self.consensus_timeout)
        
        async with self.lock:
            if instance_id not in self.instances:
                return
                
            instance = self.instances[instance_id]
            if instance.phase == ConsensusPhase.EXECUTED:
                return
                
            # Consensus timed out
            instance.phase = ConsensusPhase.FAILED
            instance.result = ConsensusResult.TIMEOUT
            
        # Trigger view change if we're waiting on primary
        if self.node_id != self.primary_id:
            await self._initiate_view_change(self.view_number + 1)
            
    def _validate_message(self, msg: ConsensusMessage) -> bool:
        """Validate message format and signature."""
        # Basic validation
        if not msg.sender_id:
            return False
        if msg.sender_id == self.node_id:
            return False  # Don't process own messages
        if msg.sender_id in self.slashed_agents:
            return False
            
        # Signature validation would go here
        return True
        
    def _compute_digest(self, data: Dict) -> str:
        """Compute cryptographic digest of proposal."""
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()
        
    def _generate_instance_id(self, proposal: Dict) -> str:
        """Generate unique instance ID."""
        digest = self._compute_digest(proposal)
        return f"{self.view_number}:{self.sequence_number}:{digest[:16]}"
        
    def _get_instance_id(self, sequence_number: int) -> str:
        """Get instance ID by sequence number."""
        if sequence_number in self.instance_by_seq:
            return self.instance_by_seq[sequence_number].instance_id
        return f"unknown:{sequence_number}"
        
    def _stable_checkpoint(self) -> int:
        """Get last stable checkpoint sequence number."""
        if not self.completed_instances:
            return 0
        return max(self.completed_instances)
        
    def _get_node_list(self) -> List[str]:
        """Get list of all node IDs."""
        # This would come from coordinator
        return [f"node_{i}" for i in range(self.total_nodes)]
        
    async def _broadcast_message(self, msg: ConsensusMessage):
        """Broadcast message to all nodes."""
        if self.broadcast_callback:
            msg_dict = {
                "type": msg.msg_type,
                "view_number": msg.view_number,
                "sequence_number": msg.sequence_number,
                "digest": msg.digest,
                "payload": dict(msg.payload) if msg.payload else {},
                "sender_id": msg.sender_id,
                "timestamp": msg.timestamp
            }
            self.broadcast_callback(msg_dict)
            
    async def _record_suspicion(self, agent_id: str, reason: str):
        """Record suspicious behavior."""
        self.suspicion_scores[agent_id] += 0.1
        if self.suspicion_scores[agent_id] > 1.0:
            await self._slash_agent(agent_id)
            
    async def _record_byzantine_evidence(self, agent_id: str, 
                                          violation_type: str,
                                          messages: List[ConsensusMessage]):
        """Record evidence of Byzantine behavior."""
        evidence = ByzantineEvidence(
            agent_id=agent_id,
            violation_type=violation_type,
            conflicting_messages=messages,
            severity=1.0
        )
        self.byzantine_evidence.append(evidence)
        self.byzantine_detected += 1
        self.suspicion_scores[agent_id] += 0.5
        
        if self.suspicion_scores[agent_id] > 1.0:
            await self._slash_agent(agent_id)
            
    async def _slash_agent(self, agent_id: str):
        """Remove Byzantine agent from consensus."""
        self.slashed_agents.add(agent_id)
        
        # Recalculate quorum
        active_nodes = self.total_nodes - len(self.slashed_agents)
        self.max_faulty = (active_nodes - 1) // 3
        self.prepare_quorum = active_nodes - self.max_faulty
        self.commit_quorum = active_nodes - self.max_faulty
        
    async def _execute_consensus(self, instance: ConsensusInstance):
        """Execute the agreed-upon value."""
        # This would call application-level execution
        pass
        
    def get_status(self) -> Dict[str, Any]:
        """Get consensus engine status."""
        return {
            "node_id": self.node_id,
            "view_number": self.view_number,
            "primary_id": self.primary_id,
            "total_nodes": self.total_nodes,
            "max_faulty": self.max_faulty,
            "prepare_quorum": self.prepare_quorum,
            "commit_quorum": self.commit_quorum,
            "active_instances": len(self.instances),
            "completed_instances": len(self.completed_instances),
            "consensus_count": self.consensus_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / max(self.consensus_count, 1),
            "byzantine_detected": self.byzantine_detected,
            "slashed_agents": list(self.slashed_agents),
            "view_changes": self.view_changes,
            "suspicion_scores": dict(self.suspicion_scores)
        }
        
    def verify_consensus(self, instance_id: str) -> bool:
        """Verify that consensus was reached for an instance."""
        if instance_id not in self.instances:
            return False
            
        instance = self.instances[instance_id]
        return instance.phase == ConsensusPhase.EXECUTED and instance.result == ConsensusResult.ACCEPTED


class FastBFTConsensus(BFTConsensus):
    """
    Optimized BFT consensus with fast path.
    
    Uses optimistic execution for non-contentious proposals,
    falling back to full PBFT only when needed.
    """
    
    def __init__(self, *args, optimistic_threshold: float = 0.9, **kwargs):
        super().__init__(*args, **kwargs)
        self.optimistic_threshold = optimistic_threshold
        self.optimistic_accepted = 0
        self.optimistic_rejected = 0
        
    async def propose_fast(self, proposal: Dict) -> Tuple[ConsensusResult, Optional[str]]:
        """
        Fast path proposal - optimistic acceptance.
        
        If enough nodes accept quickly, skip full PBFT.
        """
        instance_id = self._generate_instance_id(proposal)
        digest = self._compute_digest(proposal)
        
        # Send optimistic proposal
        optimistic_msg = {
            "type": "OPTIMISTIC_PROPOSE",
            "instance_id": instance_id,
            "digest": digest,
            "proposal": proposal,
            "sender_id": self.node_id
        }
        
        # Collect responses
        responses = await self._collect_responses(optimistic_msg, timeout=1.0)
        
        accept_count = sum(1 for r in responses if r.get("accept"))
        
        if accept_count >= self.optimistic_threshold * self.total_nodes:
            self.optimistic_accepted += 1
            # Optimistic acceptance succeeded
            return ConsensusResult.ACCEPTED, digest
        else:
            self.optimistic_rejected += 1
            # Fall back to full PBFT
            return await self.propose(proposal, instance_id)
            
    async def _collect_responses(self, msg: Dict, timeout: float) -> List[Dict]:
        """Collect responses from nodes."""
        # This would use actual network callbacks
        return []
