"""
Cell 0 OS - Collective Intelligence
Swarm intelligence patterns for emergent behavior and decision making.
"""

import asyncio
import random
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import heapq


class DecisionType(Enum):
    """Types of collective decisions."""
    CONSENSUS = auto()
    VOTING = auto()
    AUCTION = auto()
    DELEGATION = auto()
    EMERGENT = auto()


class SwarmPattern(Enum):
    """Swarm intelligence patterns."""
    FLOCKING = auto()
    STIGMERGY = auto()
    DIVISION_OF_LABOR = auto()
    COLLECTIVE_MEMORY = auto()
    QUORUM_SENSING = auto()


@dataclass
class AgentBelief:
    """Agent's belief about some state."""
    topic: str
    value: Any
    confidence: float
    timestamp: float
    evidence: List[Dict] = field(default_factory=list)


@dataclass
class CollectiveDecision:
    """Result of collective decision making."""
    decision_id: str
    decision_type: DecisionType
    topic: str
    outcome: Any
    confidence: float
    participating_agents: Set[str]
    votes: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    execution_status: str = "pending"


@dataclass
class Pheromone:
    """Digital pheromone for stigmergy."""
    pheromone_id: str
    location: str
    intensity: float
    type: str
    created_at: float
    decay_rate: float = 0.1
    
    def current_intensity(self) -> float:
        """Get current intensity accounting for decay."""
        age = time.time() - self.created_at
        return self.intensity * (0.9 ** (age * self.decay_rate))


@dataclass
class ResourceClaim:
    """Claim on a shared resource."""
    claim_id: str
    agent_id: str
    resource_type: str
    amount: float
    priority: float
    claimed_at: float
    expires_at: float


class StigmergySpace:
    """
    Digital stigmergy environment.
    
    Agents communicate indirectly through environmental markers,
    similar to ant pheromone trails.
    """
    
    def __init__(self):
        self.pheromones: Dict[str, Pheromone] = {}
        self.locations: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.agent_trails: Dict[str, List[str]] = defaultdict(list)
        self.lock = asyncio.Lock()
        
    async def deposit(self, agent_id: str, location: str, pheromone_type: str,
                     intensity: float, decay_rate: float = 0.1):
        """Deposit pheromone at location."""
        async with self.lock:
            pheromone_id = f"{agent_id}:{location}:{time.time()}"
            
            pheromone = Pheromone(
                pheromone_id=pheromone_id,
                location=location,
                intensity=intensity,
                type=pheromone_type,
                created_at=time.time(),
                decay_rate=decay_rate
            )
            
            self.pheromones[pheromone_id] = pheromone
            self.locations[location][pheromone_id] = intensity
            self.agent_trails[agent_id].append(location)
            
    async def sense(self, location: str, pheromone_type: Optional[str] = None) -> float:
        """Sense pheromone intensity at location."""
        async with self.lock:
            total = 0.0
            
            for pid in list(self.locations.get(location, {}).keys()):
                pheromone = self.pheromones.get(pid)
                if not pheromone:
                    continue
                    
                current = pheromone.current_intensity()
                
                if current < 0.01:
                    # Remove expired
                    del self.pheromones[pid]
                    del self.locations[location][pid]
                elif pheromone_type is None or pheromone.type == pheromone_type:
                    total += current
                    
            return total
            
    async def get_gradient(self, agent_location: str, pheromone_type: str,
                          possible_moves: List[str]) -> Optional[str]:
        """
        Follow gradient of pheromone type.
        
        Returns best move based on sensed intensity.
        """
        intensities = []
        
        for move in possible_moves:
            intensity = await self.sense(move, pheromone_type)
            intensities.append((intensity, move))
            
        if not intensities:
            return None
            
        # Probabilistic selection based on intensity
        total = sum(i for i, _ in intensities)
        if total == 0:
            return random.choice(possible_moves)
            
        r = random.uniform(0, total)
        cumulative = 0
        
        for intensity, move in intensities:
            cumulative += intensity
            if r <= cumulative:
                return move
                
        return intensities[-1][1]
        
    async def evaporate(self):
        """Evaporate old pheromones."""
        async with self.lock:
            now = time.time()
            to_remove = []
            
            for pid, pheromone in self.pheromones.items():
                if pheromone.current_intensity() < 0.01:
                    to_remove.append(pid)
                    
            for pid in to_remove:
                pheromone = self.pheromones.pop(pid, None)
                if pheromone:
                    self.locations[pheromone.location].pop(pid, None)
                    
    def get_trail(self, agent_id: str) -> List[str]:
        """Get agent's recent trail."""
        return list(self.agent_trails.get(agent_id, []))


class CollectiveDecisionEngine:
    """
    Engine for collective decision making.
    
    Supports multiple decision mechanisms:
    - Consensus: Agreement-based
    - Voting: Majority/plurality voting
    - Auction: Market-based allocation
    - Delegation: Expert selection
    - Emergent: Self-organizing
    """
    
    def __init__(self, coordinator_id: str, total_agents: int = 200):
        self.coordinator_id = coordinator_id
        self.total_agents = total_agents
        
        # Decision tracking
        self.active_decisions: Dict[str, CollectiveDecision] = {}
        self.decision_history: List[CollectiveDecision] = []
        
        # Voting state
        self.vote_tallies: Dict[str, Dict[Any, int]] = defaultdict(lambda: defaultdict(int))
        self.agent_votes: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Delegation state
        self.expertise_scores: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Callbacks
        self.decision_callbacks: List[Callable[[CollectiveDecision], None]] = []
        
    def register_callback(self, callback: Callable[[CollectiveDecision], None]):
        """Register decision completion callback."""
        self.decision_callbacks.append(callback)
        
    async def propose_consensus(self, topic: str, proposal: Any,
                               timeout: float = 30.0) -> CollectiveDecision:
        """
        Propose a consensus decision.
        
        Agents signal acceptance or rejection.
        Requires supermajority (2/3) for acceptance.
        """
        decision_id = f"consensus:{topic}:{time.time()}"
        
        decision = CollectiveDecision(
            decision_id=decision_id,
            decision_type=DecisionType.CONSENSUS,
            topic=topic,
            outcome=None,
            confidence=0.0,
            participating_agents=set()
        )
        
        self.active_decisions[decision_id] = decision
        
        # Wait for votes (in practice, would collect from agents)
        await asyncio.sleep(timeout)
        
        # Determine outcome
        votes_for = self.vote_tallies[decision_id].get(True, 0)
        votes_against = self.vote_tallies[decision_id].get(False, 0)
        total = votes_for + votes_against
        
        if total > 0 and votes_for / total >= 0.67:
            decision.outcome = proposal
            decision.confidence = votes_for / total
        else:
            decision.outcome = None
            decision.confidence = votes_against / total if total > 0 else 0
            
        decision.execution_status = "completed"
        
        # Cleanup and notify
        del self.active_decisions[decision_id]
        self.decision_history.append(decision)
        await self._notify_decision(decision)
        
        return decision
        
    async def propose_vote(self, topic: str, options: List[Any],
                          voting_method: str = "plurality",
                          timeout: float = 30.0) -> CollectiveDecision:
        """
        Propose a voting decision.
        
        Methods:
        - plurality: Most votes wins
        - ranked: Preferential voting
        - approval: Multiple approvals allowed
        """
        decision_id = f"vote:{topic}:{time.time()}"
        
        decision = CollectiveDecision(
            decision_id=decision_id,
            decision_type=DecisionType.VOTING,
            topic=topic,
            outcome=None,
            confidence=0.0,
            participating_agents=set()
        )
        
        self.active_decisions[decision_id] = decision
        
        # Wait for votes
        await asyncio.sleep(timeout)
        
        # Determine outcome
        if voting_method == "plurality":
            tallies = self.vote_tallies[decision_id]
            if tallies:
                winner = max(tallies.items(), key=lambda x: x[1])
                total_votes = sum(tallies.values())
                decision.outcome = winner[0]
                decision.confidence = winner[1] / total_votes if total_votes > 0 else 0
        elif voting_method == "approval":
            tallies = self.vote_tallies[decision_id]
            if tallies:
                winner = max(tallies.items(), key=lambda x: x[1])
                decision.outcome = winner[0]
                decision.confidence = 1.0
                
        decision.execution_status = "completed"
        
        del self.active_decisions[decision_id]
        self.decision_history.append(decision)
        await self._notify_decision(decision)
        
        return decision
        
    async def conduct_auction(self, item: str, agents: List[str],
                             timeout: float = 10.0) -> CollectiveDecision:
        """
        Conduct auction for resource allocation.
        
        Agents bid with their capability to complete the task.
        """
        decision_id = f"auction:{item}:{time.time()}"
        
        decision = CollectiveDecision(
            decision_id=decision_id,
            decision_type=DecisionType.AUCTION,
            topic=item,
            outcome=None,
            confidence=0.0,
            participating_agents=set(agents)
        )
        
        self.active_decisions[decision_id] = decision
        
        # Wait for bids
        await asyncio.sleep(timeout)
        
        # Determine winner (highest bid)
        bids = self.vote_tallies[decision_id]
        if bids:
            winner = max(bids.items(), key=lambda x: x[1])
            decision.outcome = winner[0]
            decision.confidence = 1.0
            
        decision.execution_status = "completed"
        
        del self.active_decisions[decision_id]
        self.decision_history.append(decision)
        await self._notify_decision(decision)
        
        return decision
        
    async def delegate(self, task: str, required_expertise: List[str],
                      candidates: List[str]) -> CollectiveDecision:
        """
        Delegate task to most expert agent.
        
        Selects agent with highest combined expertise score.
        """
        decision_id = f"delegate:{task}:{time.time()}"
        
        # Score candidates
        scores = []
        for candidate in candidates:
            total_score = 0
            for expertise in required_expertise:
                total_score += self.expertise_scores[candidate].get(expertise, 0)
            scores.append((total_score, candidate))
            
        if not scores:
            decision = CollectiveDecision(
                decision_id=decision_id,
                decision_type=DecisionType.DELEGATION,
                topic=task,
                outcome=None,
                confidence=0.0,
                participating_agents=set(candidates)
            )
        else:
            scores.sort(reverse=True)
            winner = scores[0]
            
            decision = CollectiveDecision(
                decision_id=decision_id,
                decision_type=DecisionType.DELEGATION,
                topic=task,
                outcome=winner[1],
                confidence=min(winner[0] / len(required_expertise), 1.0),
                participating_agents=set(candidates),
                votes={candidate: score for score, candidate in scores}
            )
            
        decision.execution_status = "completed"
        self.decision_history.append(decision)
        await self._notify_decision(decision)
        
        return decision
        
    def submit_vote(self, decision_id: str, agent_id: str, vote: Any):
        """Submit vote for active decision."""
        if decision_id not in self.active_decisions:
            return False
            
        self.agent_votes[agent_id][decision_id] = vote
        self.vote_tallies[decision_id][vote] += 1
        self.active_decisions[decision_id].participating_agents.add(agent_id)
        
        return True
        
    def update_expertise(self, agent_id: str, expertise: str, score: float):
        """Update agent expertise score."""
        self.expertise_scores[agent_id][expertise] = score
        
    async def _notify_decision(self, decision: CollectiveDecision):
        """Notify decision callbacks."""
        for callback in self.decision_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(decision))
                else:
                    callback(decision)
            except Exception:
                pass
                
    def get_decision_stats(self) -> Dict:
        """Get decision statistics."""
        if not self.decision_history:
            return {"total_decisions": 0}
            
        by_type = defaultdict(int)
        for d in self.decision_history:
            by_type[d.decision_type.name] += 1
            
        return {
            "total_decisions": len(self.decision_history),
            "by_type": dict(by_type),
            "average_confidence": statistics.mean(
                d.confidence for d in self.decision_history
            ),
            "average_participation": statistics.mean(
                len(d.participating_agents) for d in self.decision_history
            )
        }


class CollectiveMemory:
    """
    Shared memory system for the swarm.
    
    Agents contribute to and query collective knowledge.
    """
    
    def __init__(self):
        self.beliefs: Dict[str, List[AgentBelief]] = defaultdict(list)
        self.facts: Dict[str, Any] = {}
        self.confidence_threshold = 0.5
        self.lock = asyncio.Lock()
        
    async def contribute(self, agent_id: str, topic: str, value: Any,
                        confidence: float, evidence: Optional[List[Dict]] = None):
        """Contribute belief to collective memory."""
        async with self.lock:
            belief = AgentBelief(
                topic=topic,
                value=value,
                confidence=confidence,
                timestamp=time.time(),
                evidence=evidence or []
            )
            
            self.beliefs[topic].append(belief)
            
            # Update consensus fact if confidence is high enough
            await self._update_consensus_fact(topic)
            
    async def query(self, topic: str, min_confidence: Optional[float] = None) -> List[AgentBelief]:
        """Query collective memory for topic."""
        async with self.lock:
            beliefs = self.beliefs.get(topic, [])
            
            if min_confidence is not None:
                beliefs = [b for b in beliefs if b.confidence >= min_confidence]
                
            # Sort by confidence
            beliefs.sort(key=lambda b: b.confidence, reverse=True)
            
            return beliefs
            
    async def get_consensus(self, topic: str) -> Optional[Any]:
        """Get consensus value for topic."""
        async with self.lock:
            return self.facts.get(topic)
            
    async def _update_consensus_fact(self, topic: str):
        """Update consensus fact from beliefs."""
        beliefs = self.beliefs.get(topic, [])
        if not beliefs:
            return
            
        # Group by value
        value_confidence = defaultdict(list)
        for belief in beliefs:
            value_confidence[belief.value].append(belief.confidence)
            
        # Find most confident value
        best_value = None
        best_confidence = 0
        
        for value, confidences in value_confidence.items():
            avg_confidence = statistics.mean(confidences)
            if avg_confidence > best_confidence:
                best_confidence = avg_confidence
                best_value = value
                
        # Update if confident enough
        if best_confidence >= self.confidence_threshold:
            self.facts[topic] = best_value
            
    async def forget_old(self, max_age: float = 3600):
        """Remove old beliefs."""
        async with self.lock:
            now = time.time()
            
            for topic in list(self.beliefs.keys()):
                self.beliefs[topic] = [
                    b for b in self.beliefs[topic]
                    if now - b.timestamp < max_age
                ]


class ResourceSharing:
    """
    Resource sharing and allocation system.
    
    Manages shared resources across the swarm.
    """
    
    def __init__(self):
        self.total_resources: Dict[str, float] = {}
        self.allocated_resources: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.claims: Dict[str, ResourceClaim] = {}
        self.usage_history: List[Dict] = []
        self.lock = asyncio.Lock()
        
    def register_resource(self, resource_type: str, total_amount: float):
        """Register a shared resource."""
        self.total_resources[resource_type] = total_amount
        
    async def claim(self, agent_id: str, resource_type: str,
                   amount: float, priority: float = 1.0,
                   duration: float = 3600) -> Optional[str]:
        """Claim a resource."""
        async with self.lock:
            if resource_type not in self.total_resources:
                return None
                
            total = self.total_resources[resource_type]
            allocated = sum(
                self.allocated_resources[resource_type].values()
            )
            
            if allocated + amount > total:
                # Not enough available, check if we can preempt
                available = total - allocated
                if available + self._can_preempt(resource_type, priority) < amount:
                    return None
                    
            claim_id = f"{agent_id}:{resource_type}:{time.time()}"
            
            claim = ResourceClaim(
                claim_id=claim_id,
                agent_id=agent_id,
                resource_type=resource_type,
                amount=amount,
                priority=priority,
                claimed_at=time.time(),
                expires_at=time.time() + duration
            )
            
            self.claims[claim_id] = claim
            self.allocated_resources[resource_type][claim_id] = amount
            
            return claim_id
            
    async def release(self, claim_id: str) -> bool:
        """Release a resource claim."""
        async with self.lock:
            if claim_id not in self.claims:
                return False
                
            claim = self.claims[claim_id]
            del self.allocated_resources[claim.resource_type][claim_id]
            del self.claims[claim_id]
            
            return True
            
    def _can_preempt(self, resource_type: str, priority: float) -> float:
        """Calculate how much can be preempted."""
        preemptable = 0
        
        for claim_id, amount in self.allocated_resources[resource_type].items():
            claim = self.claims.get(claim_id)
            if claim and claim.priority < priority:
                preemptable += amount
                
        return preemptable
        
    async def get_available(self, resource_type: str) -> float:
        """Get available amount of resource."""
        async with self.lock:
            total = self.total_resources.get(resource_type, 0)
            allocated = sum(self.allocated_resources[resource_type].values())
            return max(0, total - allocated)
            
    async def cleanup_expired(self):
        """Remove expired claims."""
        async with self.lock:
            now = time.time()
            expired = [
                cid for cid, claim in self.claims.items()
                if claim.expires_at < now
            ]
            
            for cid in expired:
                claim = self.claims.get(cid)
                if claim:
                    del self.allocated_resources[claim.resource_type][cid]
                    del self.claims[cid]


class CollectiveIntelligence:
    """
    Main collective intelligence orchestrator.
    
    Coordinates all swarm intelligence patterns.
    """
    
    def __init__(self, coordinator_id: str, total_agents: int = 200):
        self.coordinator_id = coordinator_id
        self.total_agents = total_agents
        
        # Subsystems
        self.stigmergy = StigmergySpace()
        self.decision_engine = CollectiveDecisionEngine(coordinator_id, total_agents)
        self.memory = CollectiveMemory()
        self.resources = ResourceSharing()
        
        # Pattern usage tracking
        self.pattern_usage: Dict[SwarmPattern, int] = defaultdict(int)
        
    async def start(self):
        """Start collective intelligence systems."""
        # Start maintenance loops
        asyncio.create_task(self._maintenance_loop())
        
    async def _maintenance_loop(self):
        """Periodic maintenance."""
        while True:
            await asyncio.sleep(60.0)
            
            # Evaporate pheromones
            await self.stigmergy.evaporate()
            
            # Forget old beliefs
            await self.memory.forget_old()
            
            # Clean up expired resource claims
            await self.resources.cleanup_expired()
            
    def get_status(self) -> Dict:
        """Get collective intelligence status."""
        return {
            "decisions": self.decision_engine.get_decision_stats(),
            "pheromones": len(self.stigmergy.pheromones),
            "beliefs": sum(len(b) for b in self.memory.beliefs.values()),
            "facts": len(self.memory.facts),
            "resource_claims": len(self.resources.claims),
            "pattern_usage": {p.name: c for p, c in self.pattern_usage.items()}
        }
