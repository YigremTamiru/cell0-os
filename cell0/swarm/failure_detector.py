"""
Cell 0 OS - Failure Detector
Distributed failure detection with adaptive timeouts.
"""

import asyncio
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import statistics


class FailureSuspicion(Enum):
    """Levels of failure suspicion."""
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CONFIRMED = auto()


class FailureType(Enum):
    """Types of failures detected."""
    CRASH = auto()
    NETWORK_PARTITION = auto()
    SLOW_RESPONSE = auto()
    BYZANTINE = auto()
    RESOURCE_EXHAUSTION = auto()
    UNKNOWN = auto()


@dataclass
class HeartbeatSample:
    """Single heartbeat measurement."""
    timestamp: float
    latency_ms: float
    sequence_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentHeartbeatHistory:
    """Heartbeat history for an agent."""
    agent_id: str
    samples: List[HeartbeatSample] = field(default_factory=list)
    last_heard: float = field(default_factory=time.time)
    last_sent: float = field(default_factory=time.time)
    phi_score: float = 0.0
    suspicion_level: FailureSuspicion = FailureSuspicion.NONE
    confirmed_failed: bool = False


@dataclass
class FailureEvent:
    """Reported failure event."""
    agent_id: str
    failure_type: FailureType
    timestamp: float
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    reporters: Set[str] = field(default_factory=set)


class PhiAccrualFailureDetector:
    """
    Phi Accrual Failure Detector.
    
    Uses statistical analysis of heartbeat intervals to adaptively
    detect failures. The phi value represents the suspicion level.
    
    Based on "The Phi Accrual Failure Detector" by Hayashibara et al.
    """
    
    def __init__(self,
                 threshold: float = 8.0,
                 min_samples: int = 10,
                 max_samples: int = 1000,
                 heartbeat_interval: float = 1.0):
        self.threshold = threshold
        self.min_samples = min_samples
        self.max_samples = max_samples
        self.heartbeat_interval = heartbeat_interval
        
        # Agent histories
        self.histories: Dict[str, AgentHeartbeatHistory] = {}
        
        # Window size for sampling
        self.sample_window_size = 100
        
    def register_agent(self, agent_id: str):
        """Register agent for monitoring."""
        if agent_id not in self.histories:
            self.histories[agent_id] = AgentHeartbeatHistory(agent_id=agent_id)
            
    def unregister_agent(self, agent_id: str):
        """Unregister agent from monitoring."""
        self.histories.pop(agent_id, None)
        
    def heartbeat(self, agent_id: str, sequence_number: int,
                  metadata: Optional[Dict] = None):
        """Record heartbeat from agent."""
        now = time.time()
        
        if agent_id not in self.histories:
            self.register_agent(agent_id)
            
        history = self.histories[agent_id]
        
        # Calculate latency
        if history.last_sent > 0:
            latency_ms = (now - history.last_sent) * 1000
        else:
            latency_ms = self.heartbeat_interval * 1000
            
        # Create sample
        sample = HeartbeatSample(
            timestamp=now,
            latency_ms=latency_ms,
            sequence_number=sequence_number,
            metadata=metadata or {}
        )
        
        # Add to history
        history.samples.append(sample)
        if len(history.samples) > self.max_samples:
            history.samples = history.samples[-self.max_samples:]
            
        history.last_heard = now
        history.confirmed_failed = False
        
        # Update suspicion
        history.phi_score = 0.0
        history.suspicion_level = FailureSuspicion.NONE
        
    def send_heartbeat(self, agent_id: str):
        """Record that we sent a heartbeat to agent."""
        if agent_id in self.histories:
            self.histories[agent_id].last_sent = time.time()
            
    def phi(self, agent_id: str) -> float:
        """Calculate phi (suspicion level) for agent."""
        if agent_id not in self.histories:
            return float('inf')
            
        history = self.histories[agent_id]
        
        if len(history.samples) < self.min_samples:
            # Not enough samples, use conservative timeout
            time_since_last = time.time() - history.last_heard
            return time_since_last / (self.heartbeat_interval * 2)
            
        # Calculate phi using accrual formula
        time_since_last = time.time() - history.last_heard
        
        # Get recent samples for window
        window = history.samples[-self.sample_window_size:]
        intervals = []
        
        for i in range(1, len(window)):
            interval = window[i].timestamp - window[i-1].timestamp
            intervals.append(interval)
            
        if not intervals:
            return 0.0
            
        # Calculate statistics
        mean_interval = statistics.mean(intervals)
        
        if len(intervals) > 1:
            try:
                std_dev = statistics.stdev(intervals)
            except statistics.StatisticsError:
                std_dev = mean_interval * 0.1
        else:
            std_dev = mean_interval * 0.1
            
        # Ensure minimum variance
        std_dev = max(std_dev, mean_interval * 0.01)
        
        # Calculate phi
        if std_dev == 0:
            return float('inf') if time_since_last > mean_interval else 0.0
            
        # Phi formula: -log10(1 - F(time_since_last))
        # where F is the CDF of the normal distribution
        y = (time_since_last - mean_interval) / std_dev
        phi = -math.log10(math.erfc(y / math.sqrt(2)) / 2 + 1e-10)
        
        history.phi_score = phi
        
        # Update suspicion level
        if phi >= self.threshold:
            history.suspicion_level = FailureSuspicion.CONFIRMED
        elif phi >= self.threshold * 0.75:
            history.suspicion_level = FailureSuspicion.HIGH
        elif phi >= self.threshold * 0.5:
            history.suspicion_level = FailureSuspicion.MEDIUM
        elif phi >= self.threshold * 0.25:
            history.suspicion_level = FailureSuspicion.LOW
        else:
            history.suspicion_level = FailureSuspicion.NONE
            
        return phi
        
    def is_suspected(self, agent_id: str) -> bool:
        """Check if agent is suspected of failure."""
        return self.phi(agent_id) >= self.threshold
        
    def get_suspected_agents(self) -> List[str]:
        """Get all suspected agents."""
        return [aid for aid in self.histories if self.is_suspected(aid)]
        
    def get_stats(self, agent_id: str) -> Dict:
        """Get detection statistics for agent."""
        if agent_id not in self.histories:
            return {}
            
        history = self.histories[agent_id]
        samples = history.samples
        
        if len(samples) < 2:
            return {
                "agent_id": agent_id,
                "samples": len(samples),
                "phi": self.phi(agent_id),
                "suspicion": history.suspicion_level.name
            }
            
        intervals = [
            samples[i].timestamp - samples[i-1].timestamp
            for i in range(1, len(samples))
        ]
        latencies = [s.latency_ms for s in samples]
        
        return {
            "agent_id": agent_id,
            "samples": len(samples),
            "phi": self.phi(agent_id),
            "suspicion": history.suspicion_level.name,
            "mean_interval": statistics.mean(intervals),
            "std_dev_interval": statistics.stdev(intervals) if len(intervals) > 1 else 0,
            "mean_latency_ms": statistics.mean(latencies),
            "last_heard": history.last_heard,
            "time_since_last": time.time() - history.last_heard
        }


class GossipFailureDetector:
    """
    Distributed failure detection using gossip.
    
    Each node gossips about who it has heard from recently,
    allowing distributed consensus on failures.
    """
    
    GOSSIP_INTERVAL = 1.0
    GOSSIP_FANOUT = 3
    SUSPECT_TIMEOUT = 5.0
    CONFIRM_TIMEOUT = 10.0
    
    def __init__(self, agent_id: str, all_agents: List[str]):
        self.agent_id = agent_id
        self.all_agents = set(all_agents)
        
        # Subjective states
        self.subjective_states: Dict[str, FailureSuspicion] = {}
        self.subjective_last_heard: Dict[str, float] = {}
        
        # Gossip state
        self.gossip_views: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Failure callbacks
        self.failure_callbacks: List[Callable[[FailureEvent], None]] = []
        
        # Running state
        self.running = False
        
    def register_callback(self, callback: Callable[[FailureEvent], None]):
        """Register failure detection callback."""
        self.failure_callbacks.append(callback)
        
    async def start(self):
        """Start gossip failure detector."""
        self.running = True
        asyncio.create_task(self._gossip_loop())
        asyncio.create_task(self._detection_loop())
        
    async def stop(self):
        """Stop gossip failure detector."""
        self.running = False
        
    def heartbeat_received(self, from_agent: str):
        """Record heartbeat from another agent."""
        now = time.time()
        self.subjective_last_heard[from_agent] = now
        self.subjective_states[from_agent] = FailureSuspicion.NONE
        
        # Update our gossip view
        for agent, last_heard in list(self.gossip_views.get(self.agent_id, {}).items()):
            if now - last_heard > self.CONFIRM_TIMEOUT:
                del self.gossip_views[self.agent_id][agent]
                
        self.gossip_views[self.agent_id][from_agent] = now
        
    async def _gossip_loop(self):
        """Main gossip loop."""
        while self.running:
            await asyncio.sleep(self.GOSSIP_INTERVAL)
            
            # Select gossip targets
            targets = self._select_gossip_targets()
            
            for target in targets:
                await self._send_gossip(target)
                
    def _select_gossip_targets(self) -> List[str]:
        """Select agents to gossip with."""
        # Exclude self and suspected failed agents
        candidates = [
            aid for aid in self.all_agents
            if aid != self.agent_id
            and self.subjective_states.get(aid) != FailureSuspicion.CONFIRMED
        ]
        
        if len(candidates) <= self.GOSSIP_FANOUT:
            return candidates
            
        # Prefer agents we haven't heard from recently
        candidates.sort(
            key=lambda aid: self.subjective_last_heard.get(aid, 0),
            reverse=True
        )
        
        # Include some random agents for coverage
        selected = candidates[:self.GOSSIP_FANOUT // 2]
        remaining = [c for c in candidates if c not in selected]
        selected.extend(random.sample(remaining, min(
            self.GOSSIP_FANOUT - len(selected),
            len(remaining)
        )))
        
        return selected
        
    async def _send_gossip(self, target: str):
        """Send gossip to target agent."""
        # Build gossip message
        gossip = {
            "sender": self.agent_id,
            "timestamp": time.time(),
            "heartbeat_view": dict(self.gossip_views.get(self.agent_id, {}))
        }
        
        # Would send actual message here
        await self._on_gossip_sent(target, gossip)
        
    async def _on_gossip_sent(self, target: str, gossip: Dict):
        """Handle gossip being sent (simulation)."""
        pass
        
    async def receive_gossip(self, from_agent: str, gossip: Dict):
        """Handle received gossip."""
        # Update our view with their information
        their_view = gossip.get("heartbeat_view", {})
        
        for agent_id, last_heard in their_view.items():
            if agent_id == self.agent_id:
                continue
                
            current = self.gossip_views.get(from_agent, {}).get(agent_id, 0)
            if last_heard > current:
                self.gossip_views[from_agent][agent_id] = last_heard
                
    async def _detection_loop(self):
        """Detect failures based on gossip."""
        while self.running:
            await asyncio.sleep(2.0)
            
            now = time.time()
            
            for agent_id in self.all_agents:
                if agent_id == self.agent_id:
                    continue
                    
                # Check if we've heard directly
                last_direct = self.subjective_last_heard.get(agent_id, 0)
                time_since_direct = now - last_direct
                
                # Check gossip reports
                indirect_reports = []
                for reporter, view in self.gossip_views.items():
                    if agent_id in view:
                        indirect_reports.append(view[agent_id])
                        
                # Determine suspicion level
                if time_since_direct < self.SUSPECT_TIMEOUT:
                    new_state = FailureSuspicion.NONE
                elif indirect_reports and max(indirect_reports) > now - self.SUSPECT_TIMEOUT:
                    new_state = FailureSuspicion.LOW  # Heard indirectly recently
                elif time_since_direct < self.CONFIRM_TIMEOUT:
                    new_state = FailureSuspicion.MEDIUM
                elif indirect_reports and max(indirect_reports) > now - self.CONFIRM_TIMEOUT:
                    new_state = FailureSuspicion.HIGH
                else:
                    new_state = FailureSuspicion.CONFIRMED
                    
                old_state = self.subjective_states.get(agent_id, FailureSuspicion.NONE)
                
                if new_state != old_state:
                    self.subjective_states[agent_id] = new_state
                    
                    # Notify if confirmed failed
                    if new_state == FailureSuspicion.CONFIRMED and old_state != FailureSuspicion.CONFIRMED:
                        await self._notify_failure(agent_id, FailureType.CRASH)
                        
    async def _notify_failure(self, agent_id: str, failure_type: FailureType):
        """Notify failure callbacks."""
        event = FailureEvent(
            agent_id=agent_id,
            failure_type=failure_type,
            timestamp=time.time(),
            confidence=1.0,
            reporters={self.agent_id}
        )
        
        for callback in self.failure_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception:
                pass
                
    def get_suspected_agents(self) -> List[str]:
        """Get all suspected agents."""
        return [
            aid for aid, state in self.subjective_states.items()
            if state in (FailureSuspicion.MEDIUM, FailureSuspicion.HIGH, FailureSuspicion.CONFIRMED)
        ]
        
    def get_confirmed_failed(self) -> List[str]:
        """Get confirmed failed agents."""
        return [
            aid for aid, state in self.subjective_states.items()
            if state == FailureSuspicion.CONFIRMED
        ]


class FailureRecovery:
    """
    Automatic failure recovery mechanisms.
    
    Handles task reassignment, state recovery, and agent replacement.
    """
    
    def __init__(self, coordinator_id: str):
        self.coordinator_id = coordinator_id
        
        # Recovery callbacks
        self.recovery_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Recovery state
        self.recovery_in_progress: Set[str] = set()
        self.recovery_history: List[Dict] = []
        
    def register_recovery_callback(self, failure_type: FailureType, 
                                   callback: Callable[[FailureEvent], None]):
        """Register callback for specific failure type."""
        self.recovery_callbacks[failure_type].append(callback)
        
    async def handle_failure(self, event: FailureEvent):
        """Handle detected failure."""
        if event.agent_id in self.recovery_in_progress:
            return
            
        self.recovery_in_progress.add(event.agent_id)
        
        start_time = time.time()
        success = False
        
        try:
            # Call type-specific handlers
            callbacks = self.recovery_callbacks.get(event.failure_type, [])
            
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                    success = True
                except Exception as e:
                    print(f"Recovery callback error: {e}")
                    
            # Default recovery actions
            await self._default_recovery(event)
            
        finally:
            self.recovery_in_progress.discard(event.agent_id)
            
            # Record recovery attempt
            self.recovery_history.append({
                "agent_id": event.agent_id,
                "failure_type": event.failure_type.name,
                "timestamp": start_time,
                "duration": time.time() - start_time,
                "success": success
            })
            
    async def _default_recovery(self, event: FailureEvent):
        """Default recovery actions."""
        if event.failure_type == FailureType.CRASH:
            # Remove from active set
            pass
        elif event.failure_type == FailureType.NETWORK_PARTITION:
            # Wait for partition to heal
            pass
        elif event.failure_type == FailureType.BYZANTINE:
            # Isolate agent
            pass
            
    async def recover_task(self, task_id: str, failed_agent: str,
                          available_agents: List[str]) -> Optional[str]:
        """Recover a task assigned to failed agent."""
        if not available_agents:
            return None
            
        # Select new agent (simple round-robin)
        new_agent = random.choice(available_agents)
        
        return new_agent
        
    def get_recovery_stats(self) -> Dict:
        """Get recovery statistics."""
        if not self.recovery_history:
            return {"total_recoveries": 0}
            
        return {
            "total_recoveries": len(self.recovery_history),
            "successful_recoveries": sum(1 for r in self.recovery_history if r["success"]),
            "average_recovery_time": statistics.mean(
                r["duration"] for r in self.recovery_history
            ),
            "by_type": defaultdict(int, {
                r["failure_type"]: sum(1 for x in self.recovery_history if x["failure_type"] == r["failure_type"])
                for r in self.recovery_history
            })
        }


class FailureDetectorService:
    """
    Unified failure detection service.
    
    Combines multiple detection mechanisms for robust failure detection.
    """
    
    def __init__(self, agent_id: str, all_agents: List[str]):
        self.agent_id = agent_id
        self.all_agents = all_agents
        
        # Detection mechanisms
        self.phi_detector = PhiAccrualFailureDetector()
        self.gossip_detector = GossipFailureDetector(agent_id, all_agents)
        self.recovery = FailureRecovery(agent_id)
        
        # Unified state
        self.failure_events: Dict[str, FailureEvent] = {}
        self.callbacks: List[Callable[[FailureEvent], None]] = []
        
        # Link components
        self.gossip_detector.register_callback(self._on_failure_detected)
        self.recovery.register_recovery_callback(FailureType.CRASH, self._on_failure_detected)
        
    def _on_failure_detected(self, event: FailureEvent):
        """Handle failure detection from any source."""
        self.failure_events[event.agent_id] = event
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception:
                pass
                
    def register_callback(self, callback: Callable[[FailureEvent], None]):
        """Register failure detection callback."""
        self.callbacks.append(callback)
        
    async def start(self):
        """Start failure detection service."""
        # Register all agents
        for agent_id in self.all_agents:
            self.phi_detector.register_agent(agent_id)
            
        # Start components
        await self.gossip_detector.start()
        asyncio.create_task(self._phi_monitoring_loop())
        
    async def stop(self):
        """Stop failure detection service."""
        await self.gossip_detector.stop()
        
    async def _phi_monitoring_loop(self):
        """Monitor phi scores."""
        while True:
            await asyncio.sleep(1.0)
            
            for agent_id in self.all_agents:
                if agent_id == self.agent_id:
                    continue
                    
                phi = self.phi_detector.phi(agent_id)
                
                if phi >= self.phi_detector.threshold:
                    event = FailureEvent(
                        agent_id=agent_id,
                        failure_type=FailureType.CRASH,
                        timestamp=time.time(),
                        confidence=min(phi / self.phi_detector.threshold, 1.0),
                        reporters={self.agent_id}
                    )
                    await self._on_failure_detected(event)
                    
    def heartbeat(self, from_agent: str):
        """Record heartbeat from agent."""
        self.phi_detector.heartbeat(from_agent, 0)
        self.gossip_detector.heartbeat_received(from_agent)
        
    async def handle_recovery(self, event: FailureEvent):
        """Handle failure recovery."""
        await self.recovery.handle_failure(event)
        
    def get_status(self) -> Dict:
        """Get detection service status."""
        return {
            "phi_detector": {
                "suspected_agents": self.phi_detector.get_suspected_agents(),
                "threshold": self.phi_detector.threshold
            },
            "gossip_detector": {
                "suspected_agents": self.gossip_detector.get_suspected_agents(),
                "confirmed_failed": self.gossip_detector.get_confirmed_failed()
            },
            "recovery": self.recovery.get_recovery_stats(),
            "detected_failures": len(self.failure_events)
        }
