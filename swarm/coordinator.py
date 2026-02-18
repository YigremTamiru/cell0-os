"""
Cell 0 OS - Swarm Coordinator
Manages 200 agents in a civilization-grade multi-agent system.
"""

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import heapq


class AgentState(Enum):
    """Agent lifecycle states."""
    DISCOVERING = auto()
    JOINING = auto()
    ACTIVE = auto()
    BUSY = auto()
    SUSPICIOUS = auto()
    FAILED = auto()
    EVICTED = auto()
    LEAVING = auto()


class AgentRole(Enum):
    """Agent specialization roles."""
    WORKER = auto()
    VALIDATOR = auto()
    COORDINATOR = auto()
    OBSERVER = auto()
    SPECIALIST = auto()


@dataclass
class AgentCapability:
    """Agent capability descriptor."""
    name: str
    version: str
    resources: Dict[str, float] = field(default_factory=dict)
    performance_score: float = 1.0
    specialization: Optional[str] = None


@dataclass
class AgentInfo:
    """Complete agent metadata."""
    agent_id: str
    host: str
    port: int
    role: AgentRole
    state: AgentState
    capabilities: List[AgentCapability] = field(default_factory=list)
    resources: Dict[str, float] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    joined_at: float = field(default_factory=time.time)
    task_count: int = 0
    success_rate: float = 1.0
    trust_score: float = 1.0
    reputation: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmMetrics:
    """Real-time swarm health metrics."""
    total_agents: int = 0
    active_agents: int = 0
    busy_agents: int = 0
    failed_agents: int = 0
    suspicious_agents: int = 0
    average_trust: float = 1.0
    consensus_rounds: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    network_latency_ms: float = 0.0
    last_updated: float = field(default_factory=time.time)


class SwarmCoordinator:
    """
    Civilization-grade coordinator for 200+ agents.
    
    Features:
    - Hierarchical cluster management
    - Dynamic load balancing
    - Trust and reputation systems
    - Resource allocation
    - Swarm-wide communication
    """
    
    MAX_AGENTS = 256  # Room for 200 + buffer
    CLUSTER_SIZE = 32  # Agents per cluster
    HEARTBEAT_TIMEOUT = 10.0  # seconds
    SUSPICION_THRESHOLD = 0.3
    
    def __init__(self, coordinator_id: Optional[str] = None, 
                 host: str = "0.0.0.0", port: int = 9000):
        self.coordinator_id = coordinator_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        
        # Agent registry
        self.agents: Dict[str, AgentInfo] = {}
        self.agent_by_address: Dict[Tuple[str, int], str] = {}
        
        # Cluster management
        self.clusters: Dict[int, Set[str]] = defaultdict(set)
        self.cluster_coordinators: Dict[int, str] = {}
        
        # State management
        self.state_lock = asyncio.Lock()
        self.running = False
        self.start_time = time.time()
        
        # Event system
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Metrics
        self.metrics = SwarmMetrics()
        self.metrics_history: List[SwarmMetrics] = []
        
        # Consensus integration
        self.consensus_callbacks: List[Callable] = []
        
        # Task tracking
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        
        # Reputation system
        self.reputation_history: Dict[str, List[float]] = defaultdict(list)
        self.behavioral_anomalies: Dict[str, List[Dict]] = defaultdict(list)
        
    async def start(self):
        """Initialize and start the coordinator."""
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_monitor())
        asyncio.create_task(self._metrics_collector())
        asyncio.create_task(self._cluster_rebalancer())
        asyncio.create_task(self._message_dispatcher())
        
        await self._emit_event("coordinator_started", {
            "coordinator_id": self.coordinator_id,
            "max_agents": self.MAX_AGENTS,
            "cluster_size": self.CLUSTER_SIZE
        })
        
    async def stop(self):
        """Gracefully shutdown the coordinator."""
        self.running = False
        
        async with self.state_lock:
            # Notify all agents
            for agent_id in list(self.agents.keys()):
                await self._send_agent_message(agent_id, {
                    "type": "coordinator_shutdown",
                    "timestamp": time.time()
                })
            
        await self._emit_event("coordinator_stopped", {
            "coordinator_id": self.coordinator_id,
            "uptime": time.time() - self.start_time
        })
        
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """Register a new agent in the swarm."""
        async with self.state_lock:
            if len(self.agents) >= self.MAX_AGENTS:
                return False
                
            if agent_info.agent_id in self.agents:
                return False
                
            # Check address collision
            addr = (agent_info.host, agent_info.port)
            if addr in self.agent_by_address:
                return False
            
            # Assign to cluster
            cluster_id = self._assign_cluster()
            self.clusters[cluster_id].add(agent_info.agent_id)
            
            # Store agent
            self.agents[agent_info.agent_id] = agent_info
            self.agent_by_address[addr] = agent_info.agent_id
            
            # Elect cluster coordinator if needed
            if cluster_id not in self.cluster_coordinators:
                self.cluster_coordinators[cluster_id] = agent_info.agent_id
                agent_info.role = AgentRole.COORDINATOR
            
            await self._emit_event("agent_joined", {
                "agent_id": agent_info.agent_id,
                "cluster_id": cluster_id,
                "total_agents": len(self.agents)
            })
            
            return True
            
    async def unregister_agent(self, agent_id: str, reason: str = "voluntary") -> bool:
        """Remove an agent from the swarm."""
        async with self.state_lock:
            if agent_id not in self.agents:
                return False
                
            agent = self.agents[agent_id]
            agent.state = AgentState.LEAVING
            
            # Remove from cluster
            cluster_id = self._get_agent_cluster(agent_id)
            if cluster_id is not None:
                self.clusters[cluster_id].discard(agent_id)
                
                # Re-elect cluster coordinator if needed
                if self.cluster_coordinators.get(cluster_id) == agent_id:
                    await self._reelect_cluster_coordinator(cluster_id)
            
            # Clean up
            addr = (agent.host, agent.port)
            del self.agent_by_address[addr]
            del self.agents[agent_id]
            
            await self._emit_event("agent_left", {
                "agent_id": agent_id,
                "reason": reason,
                "remaining_agents": len(self.agents)
            })
            
            return True
            
    async def update_agent_state(self, agent_id: str, new_state: AgentState, 
                                  metadata: Optional[Dict] = None):
        """Update agent state with validation."""
        async with self.state_lock:
            if agent_id not in self.agents:
                return False
                
            agent = self.agents[agent_id]
            old_state = agent.state
            agent.state = new_state
            agent.last_seen = time.time()
            
            if metadata:
                agent.metadata.update(metadata)
            
            await self._emit_event("agent_state_changed", {
                "agent_id": agent_id,
                "old_state": old_state.name,
                "new_state": new_state.name,
                "metadata": metadata
            })
            
            return True
            
    async def heartbeat(self, agent_id: str, metrics: Dict[str, Any]) -> Dict:
        """Process agent heartbeat."""
        async with self.state_lock:
            if agent_id not in self.agents:
                return {"status": "unknown_agent"}
                
            agent = self.agents[agent_id]
            agent.last_seen = time.time()
            
            # Update metrics
            if "resources" in metrics:
                agent.resources.update(metrics["resources"])
            if "task_count" in metrics:
                agent.task_count = metrics["task_count"]
            if "success_rate" in metrics:
                agent.success_rate = metrics["success_rate"]
            
            # Check for suspicious behavior
            await self._analyze_behavior(agent_id, metrics)
            
            return {
                "status": "ok",
                "cluster_id": self._get_agent_cluster(agent_id),
                "coordinator_id": self.coordinator_id,
                "swarm_size": len(self.agents)
            }
            
    def get_agents_by_state(self, state: AgentState) -> List[AgentInfo]:
        """Get all agents in a specific state."""
        return [a for a in self.agents.values() if a.state == state]
        
    def get_agents_by_role(self, role: AgentRole) -> List[AgentInfo]:
        """Get all agents with a specific role."""
        return [a for a in self.agents.values() if a.role == role]
        
    def get_agents_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """Get agents with specific capability."""
        result = []
        for agent in self.agents.values():
            for cap in agent.capabilities:
                if cap.name == capability_name:
                    result.append(agent)
                    break
        return result
        
    async def get_best_agent_for_task(self, task_requirements: Dict[str, Any],
                                       exclude_agents: Optional[Set[str]] = None) -> Optional[str]:
        """
        Find the best agent for a task using multi-factor scoring.
        
        Scoring factors:
        - Capability match
        - Current load
        - Trust score
        - Success rate
        - Network proximity
        """
        exclude = exclude_agents or set()
        candidates = []
        
        for agent_id, agent in self.agents.items():
            if agent_id in exclude:
                continue
            if agent.state != AgentState.ACTIVE:
                continue
                
            score = self._calculate_task_fit_score(agent, task_requirements)
            if score > 0:
                candidates.append((score, agent_id))
        
        if not candidates:
            return None
            
        # Return highest scored agent
        candidates.sort(reverse=True)
        return candidates[0][1]
        
    def _calculate_task_fit_score(self, agent: AgentInfo, 
                                   requirements: Dict[str, Any]) -> float:
        """Calculate how well an agent fits a task."""
        score = 0.0
        
        # Check capability requirements
        required_caps = requirements.get("capabilities", [])
        agent_cap_names = {c.name for c in agent.capabilities}
        
        if required_caps:
            match_count = sum(1 for c in required_caps if c in agent_cap_names)
            if match_count == 0:
                return 0.0
            score += (match_count / len(required_caps)) * 0.3
        else:
            score += 0.3
            
        # Load factor (prefer less busy agents)
        load_penalty = min(agent.task_count / 10, 1.0)
        score += (1.0 - load_penalty) * 0.2
        
        # Trust and reputation
        score += agent.trust_score * 0.25
        score += agent.reputation * 0.15
        
        # Success rate
        score += agent.success_rate * 0.1
        
        return score
        
    def _assign_cluster(self) -> int:
        """Assign new agent to least populated cluster."""
        cluster_sizes = [(len(agents), cid) for cid, agents in self.clusters.items()]
        cluster_sizes.append((0, len(self.clusters)))  # New cluster option
        
        cluster_sizes.sort()
        return cluster_sizes[0][1]
        
    def _get_agent_cluster(self, agent_id: str) -> Optional[int]:
        """Find which cluster an agent belongs to."""
        for cid, agents in self.clusters.items():
            if agent_id in agents:
                return cid
        return None
        
    async def _reelect_cluster_coordinator(self, cluster_id: int):
        """Elect new coordinator for a cluster."""
        candidates = [
            self.agents[aid] for aid in self.clusters[cluster_id]
            if aid in self.agents and self.agents[aid].state == AgentState.ACTIVE
        ]
        
        if not candidates:
            if cluster_id in self.cluster_coordinators:
                del self.cluster_coordinators[cluster_id]
            return
            
        # Choose agent with highest trust + reputation
        best = max(candidates, key=lambda a: a.trust_score + a.reputation)
        self.cluster_coordinators[cluster_id] = best.agent_id
        best.role = AgentRole.COORDINATOR
        
    async def _analyze_behavior(self, agent_id: str, metrics: Dict):
        """Detect suspicious behavior patterns."""
        agent = self.agents[agent_id]
        anomalies = []
        
        # Check for report inconsistencies
        if "success_rate" in metrics:
            reported_rate = metrics["success_rate"]
            if reported_rate > agent.success_rate + 0.3:
                anomalies.append({
                    "type": "suspicious_success_report",
                    "reported": reported_rate,
                    "expected": agent.success_rate
                })
        
        # Check for resource claim anomalies
        if "resources" in metrics:
            claimed = metrics["resources"].get("cpu", 0)
            if claimed > 1.0:  # Impossible claim
                anomalies.append({
                    "type": "impossible_resource_claim",
                    "resource": "cpu",
                    "claimed": claimed
                })
        
        if anomalies:
            self.behavioral_anomalies[agent_id].extend(anomalies)
            
            # Reduce trust if multiple anomalies
            if len(self.behavioral_anomalies[agent_id]) > 3:
                agent.trust_score = max(0.0, agent.trust_score - 0.1)
                if agent.trust_score < self.SUSPICION_THRESHOLD:
                    agent.state = AgentState.SUSPICIOUS
                    await self._emit_event("agent_suspicious", {
                        "agent_id": agent_id,
                        "anomalies": anomalies,
                        "trust_score": agent.trust_score
                    })
                    
    async def _heartbeat_monitor(self):
        """Monitor agent health via heartbeats."""
        while self.running:
            await asyncio.sleep(2.0)
            
            now = time.time()
            failed_agents = []
            
            async with self.state_lock:
                for agent_id, agent in list(self.agents.items()):
                    if agent.state in (AgentState.FAILED, AgentState.LEAVING):
                        continue
                        
                    last_seen_ago = now - agent.last_seen
                    
                    if last_seen_ago > self.HEARTBEAT_TIMEOUT * 3:
                        # Agent completely failed
                        agent.state = AgentState.FAILED
                        failed_agents.append(agent_id)
                    elif last_seen_ago > self.HEARTBEAT_TIMEOUT:
                        # Agent unresponsive
                        if agent.state != AgentState.SUSPICIOUS:
                            agent.state = AgentState.SUSPICIOUS
                            await self._emit_event("agent_unresponsive", {
                                "agent_id": agent_id,
                                "last_seen": last_seen_ago
                            })
            
            for agent_id in failed_agents:
                await self._emit_event("agent_failed", {"agent_id": agent_id})
                
    async def _metrics_collector(self):
        """Collect and aggregate swarm metrics."""
        while self.running:
            await asyncio.sleep(5.0)
            
            async with self.state_lock:
                self.metrics.total_agents = len(self.agents)
                self.metrics.active_agents = len(self.get_agents_by_state(AgentState.ACTIVE))
                self.metrics.busy_agents = len(self.get_agents_by_state(AgentState.BUSY))
                self.metrics.failed_agents = len(self.get_agents_by_state(AgentState.FAILED))
                self.metrics.suspicious_agents = len(self.get_agents_by_state(AgentState.SUSPICIOUS))
                
                if self.agents:
                    self.metrics.average_trust = sum(
                        a.trust_score for a in self.agents.values()
                    ) / len(self.agents)
                
                self.metrics.last_updated = time.time()
                
                # Keep history (last 1000 data points)
                self.metrics_history.append(self.metrics)
                if len(self.metrics_history) > 1000:
                    self.metrics_history.pop(0)
                    
    async def _cluster_rebalancer(self):
        """Periodically rebalance clusters."""
        while self.running:
            await asyncio.sleep(60.0)  # Every minute
            
            async with self.state_lock:
                # Find imbalanced clusters
                sizes = [(len(agents), cid) for cid, agents in self.clusters.items()]
                if not sizes:
                    continue
                    
                sizes.sort()
                smallest = sizes[0]
                largest = sizes[-1]
                
                # Rebalance if difference is too large
                if largest[0] - smallest[0] > 5:
                    # Move agents from largest to smallest
                    to_move = list(self.clusters[largest[1]])[:2]
                    for agent_id in to_move:
                        self.clusters[largest[1]].discard(agent_id)
                        self.clusters[smallest[1]].add(agent_id)
                        
                    await self._emit_event("clusters_rebalanced", {
                        "from_cluster": largest[1],
                        "to_cluster": smallest[1],
                        "agents_moved": len(to_move)
                    })
                    
    async def _message_dispatcher(self):
        """Dispatch messages to agents."""
        while self.running:
            try:
                msg = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self._dispatch_message(msg)
            except asyncio.TimeoutError:
                continue
                
    async def _dispatch_message(self, msg: Dict):
        """Send message to target agent(s)."""
        target = msg.get("target")
        
        if target == "broadcast":
            for agent_id in self.agents:
                await self._send_agent_message(agent_id, msg)
        elif target == "cluster":
            cluster_id = msg.get("cluster_id")
            for agent_id in self.clusters.get(cluster_id, []):
                await self._send_agent_message(agent_id, msg)
        elif target in self.agents:
            await self._send_agent_message(target, msg)
            
    async def _send_agent_message(self, agent_id: str, msg: Dict):
        """Send message to specific agent (override for transport)."""
        # This would integrate with actual transport layer
        pass
        
    async def _emit_event(self, event_type: str, data: Dict):
        """Emit event to registered handlers."""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event_type, data))
                else:
                    handler(event_type, data)
            except Exception as e:
                print(f"Event handler error: {e}")
                
    def on_event(self, event_type: str, handler: Callable):
        """Register event handler."""
        self.event_handlers[event_type].append(handler)
        
    def get_swarm_view(self) -> Dict:
        """Get complete swarm state view."""
        return {
            "coordinator_id": self.coordinator_id,
            "total_agents": len(self.agents),
            "clusters": len(self.clusters),
            "metrics": {
                "total": self.metrics.total_agents,
                "active": self.metrics.active_agents,
                "busy": self.metrics.busy_agents,
                "failed": self.metrics.failed_agents,
                "suspicious": self.metrics.suspicious_agents,
                "average_trust": self.metrics.average_trust
            },
            "agents": [
                {
                    "id": a.agent_id,
                    "state": a.state.name,
                    "role": a.role.name,
                    "trust": a.trust_score,
                    "tasks": a.task_count
                }
                for a in self.agents.values()
            ]
        }
        
    async def broadcast_consensus(self, proposal: Dict) -> List[str]:
        """Broadcast consensus proposal to all agents."""
        proposal["coordinator_id"] = self.coordinator_id
        proposal["timestamp"] = time.time()
        proposal["proposal_id"] = hashlib.sha256(
            json.dumps(proposal, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        confirmations = []
        
        for agent_id in list(self.agents.keys()):
            try:
                response = await self._send_consensus_request(agent_id, proposal)
                if response and response.get("accepted"):
                    confirmations.append(agent_id)
            except Exception:
                pass
                
        return confirmations
        
    async def _send_consensus_request(self, agent_id: str, proposal: Dict) -> Optional[Dict]:
        """Send consensus request to agent (override for transport)."""
        return {"accepted": True}
        
    async def submit_task(self, task: Dict, preferred_agents: Optional[List[str]] = None) -> Optional[str]:
        """Submit task for execution."""
        task_id = str(uuid.uuid4())
        task["task_id"] = task_id
        task["submitted_at"] = time.time()
        
        # Find agent
        if preferred_agents:
            for agent_id in preferred_agents:
                if agent_id in self.agents and self.agents[agent_id].state == AgentState.ACTIVE:
                    selected_agent = agent_id
                    break
            else:
                selected_agent = await self.get_best_agent_for_task(task)
        else:
            selected_agent = await self.get_best_agent_for_task(task)
        
        if not selected_agent:
            return None
            
        # Assign task
        async with self.state_lock:
            self.task_assignments[task_id] = selected_agent
            self.agents[selected_agent].state = AgentState.BUSY
            self.agents[selected_agent].task_count += 1
        
        await self._send_agent_message(selected_agent, {
            "type": "task_assignment",
            "task": task
        })
        
        return task_id
