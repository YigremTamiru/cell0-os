"""
Agent Registry - Central registry for agent management and capability tracking.

Cell 0 OS - Multi-Agent Routing System
"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional
from collections import defaultdict
import json
import hashlib


class AgentStatus(Enum):
    """Agent lifecycle states."""
    REGISTERING = auto()
    ACTIVE = auto()
    BUSY = auto()
    DEGRADED = auto()
    OFFLINE = auto()
    UNREGISTERING = auto()


@dataclass
class AgentCapability:
    """Represents a capability an agent can advertise."""
    name: str
    version: str = "1.0.0"
    priority: int = 0  # Higher = preferred for routing
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def matches(self, requirement: CapabilityRequirement) -> bool:
        """Check if this capability matches a requirement."""
        if self.name != requirement.name:
            return False
        if requirement.min_version and self.version < requirement.min_version:
            return False
        if requirement.required_metadata:
            for key, value in requirement.required_metadata.items():
                if self.metadata.get(key) != value:
                    return False
        return True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "priority": self.priority,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentCapability:
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {})
        )


@dataclass
class CapabilityRequirement:
    """Requirements for routing to an agent with specific capabilities."""
    name: str
    min_version: Optional[str] = None
    required_metadata: dict[str, Any] = field(default_factory=dict)
    preferred_agents: list[str] = field(default_factory=list)


@dataclass
class AgentInfo:
    """Complete information about a registered agent."""
    agent_id: str
    agent_type: str
    capabilities: list[AgentCapability] = field(default_factory=list)
    status: AgentStatus = AgentStatus.REGISTERING
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    load_score: float = 0.0  # 0.0 = idle, 1.0 = max load
    message_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    
    def get_capability(self, name: str) -> Optional[AgentCapability]:
        """Get a specific capability by name."""
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None
    
    def has_capability(self, requirement: CapabilityRequirement) -> bool:
        """Check if agent has a capability matching the requirement."""
        for cap in self.capabilities:
            if cap.matches(requirement):
                return True
        return False
    
    def is_healthy(self) -> bool:
        """Check if agent is healthy based on status and heartbeat."""
        if self.status in (AgentStatus.OFFLINE, AgentStatus.UNREGISTERING):
            return False
        # Check heartbeat timeout (60 seconds)
        if time.time() - self.last_heartbeat > 60:
            return False
        return True
    
    def compute_fingerprint(self) -> str:
        """Compute a unique fingerprint for this agent's capabilities."""
        cap_data = json.dumps(sorted([c.to_dict() for c in self.capabilities]), sort_keys=True)
        return hashlib.sha256(cap_data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "status": self.status.name,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "load_score": self.load_score,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "metadata": self.metadata,
            "tags": list(self.tags)
        }


class AgentRegistry:
    """
    Central registry for agent registration, capability tracking, and discovery.
    
    This is the authoritative source of agent information in the system.
    """
    
    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}
        self._capability_index: dict[str, set[str]] = defaultdict(set)
        self._type_index: dict[str, set[str]] = defaultdict(set)
        self._tag_index: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._callbacks: list[Callable[[str, AgentInfo, str], Coroutine]] = []  # agent_id, info, event_type
        
    async def register(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[AgentCapability],
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[set[str]] = None
    ) -> AgentInfo:
        """
        Register a new agent with the system.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/category of agent
            capabilities: List of capabilities this agent provides
            metadata: Optional metadata dictionary
            tags: Optional set of tags for grouping
            
        Returns:
            AgentInfo object for the registered agent
        """
        async with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent {agent_id} already registered")
            
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=capabilities,
                status=AgentStatus.ACTIVE,
                metadata=metadata or {},
                tags=tags or set()
            )
            
            self._agents[agent_id] = agent_info
            
            # Index by capabilities
            for cap in capabilities:
                self._capability_index[cap.name].add(agent_id)
            
            # Index by type
            self._type_index[agent_type].add(agent_id)
            
            # Index by tags
            for tag in agent_info.tags:
                self._tag_index[tag].add(agent_id)
            
            await self._notify_callbacks(agent_id, agent_info, "registered")
            return agent_info
    
    async def unregister(self, agent_id: str) -> Optional[AgentInfo]:
        """Unregister an agent from the system."""
        async with self._lock:
            agent_info = self._agents.pop(agent_id, None)
            if not agent_info:
                return None
            
            agent_info.status = AgentStatus.UNREGISTERING
            
            # Remove from indexes
            for cap in agent_info.capabilities:
                self._capability_index[cap.name].discard(agent_id)
            
            self._type_index[agent_info.agent_type].discard(agent_id)
            
            for tag in agent_info.tags:
                self._tag_index[tag].discard(agent_id)
            
            await self._notify_callbacks(agent_id, agent_info, "unregistered")
            return agent_info
    
    async def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Update an agent's status."""
        async with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id].status = status
            await self._notify_callbacks(agent_id, self._agents[agent_id], "status_changed")
            return True
    
    async def update_heartbeat(self, agent_id: str, load_score: Optional[float] = None) -> bool:
        """Update agent heartbeat and optional load score."""
        async with self._lock:
            if agent_id not in self._agents:
                return False
            agent = self._agents[agent_id]
            agent.last_heartbeat = time.time()
            if load_score is not None:
                agent.load_score = max(0.0, min(1.0, load_score))
            return True
    
    async def increment_message_count(self, agent_id: str, error: bool = False) -> bool:
        """Increment message count and optionally error count."""
        async with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id].message_count += 1
            if error:
                self._agents[agent_id].error_count += 1
            return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        return self._agents.get(agent_id)
    
    def get_agents_by_capability(self, capability_name: str) -> list[AgentInfo]:
        """Get all agents with a specific capability."""
        agent_ids = self._capability_index.get(capability_name, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def get_agents_by_type(self, agent_type: str) -> list[AgentInfo]:
        """Get all agents of a specific type."""
        agent_ids = self._type_index.get(agent_type, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def get_agents_by_tag(self, tag: str) -> list[AgentInfo]:
        """Get all agents with a specific tag."""
        agent_ids = self._tag_index.get(tag, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def find_agents_for_requirement(self, requirement: CapabilityRequirement) -> list[AgentInfo]:
        """
        Find all agents that can satisfy a capability requirement.
        Results are sorted by capability priority and load score.
        """
        candidates = []
        for agent_id in self._capability_index.get(requirement.name, set()):
            agent = self._agents.get(agent_id)
            if agent and agent.has_capability(requirement) and agent.is_healthy():
                candidates.append(agent)
        
        # Sort by: preferred agents first, then by capability priority (desc), then by load (asc)
        def sort_key(agent: AgentInfo) -> tuple:
            cap = agent.get_capability(requirement.name)
            priority = cap.priority if cap else 0
            is_preferred = agent.agent_id in requirement.preferred_agents
            return (not is_preferred, -priority, agent.load_score)
        
        return sorted(candidates, key=sort_key)
    
    def get_all_agents(self) -> list[AgentInfo]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def get_healthy_agents(self) -> list[AgentInfo]:
        """Get all healthy agents."""
        return [agent for agent in self._agents.values() if agent.is_healthy()]
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total = len(self._agents)
        healthy = sum(1 for a in self._agents.values() if a.is_healthy())
        by_status = defaultdict(int)
        for agent in self._agents.values():
            by_status[agent.status.name] += 1
        
        return {
            "total_agents": total,
            "healthy_agents": healthy,
            "by_status": dict(by_status),
            "by_type": {t: len(ids) for t, ids in self._type_index.items()},
            "by_capability": {c: len(ids) for c, ids in self._capability_index.items()},
            "total_messages": sum(a.message_count for a in self._agents.values()),
            "total_errors": sum(a.error_count for a in self._agents.values())
        }
    
    def subscribe(self, callback: Callable[[str, AgentInfo, str], Coroutine]) -> None:
        """Subscribe to registry events."""
        self._callbacks.append(callback)
    
    def unsubscribe(self, callback: Callable[[str, AgentInfo, str], Coroutine]) -> None:
        """Unsubscribe from registry events."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def _notify_callbacks(self, agent_id: str, agent_info: AgentInfo, event: str) -> None:
        """Notify all subscribers of an event."""
        for callback in self._callbacks:
            try:
                await callback(agent_id, agent_info, event)
            except Exception:
                # Don't let callback errors break the registry
                pass
    
    async def cleanup_stale_agents(self, max_age_seconds: float = 120.0) -> list[str]:
        """Remove agents that haven't sent heartbeats within the timeout."""
        removed = []
        async with self._lock:
            now = time.time()
            stale_ids = [
                agent_id for agent_id, agent in self._agents.items()
                if now - agent.last_heartbeat > max_age_seconds
            ]
        
        for agent_id in stale_ids:
            await self.unregister(agent_id)
            removed.append(agent_id)
        
        return removed
