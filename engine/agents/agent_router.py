"""
Agent Router - Message routing system based on capabilities and load.

Cell 0 OS - Multi-Agent Routing System
"""
from __future__ import annotations
import asyncio
import time
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Callable, Coroutine, AsyncIterator
from collections import defaultdict
import uuid

from engine.agents.agent_registry import (
    AgentRegistry, AgentCapability, CapabilityRequirement, AgentInfo
)
from engine.agents.agent_session import AgentSession, SessionMessage


class RoutingStrategy(Enum):
    """Strategies for routing messages to agents."""
    ROUND_ROBIN = auto()       # Distribute evenly across agents
    LEAST_LOADED = auto()      # Route to agent with lowest load
    CAPABILITY_PRIORITY = auto()  # Route by capability priority score
    RANDOM = auto()            # Random selection
    STICKY = auto()            # Sticky sessions by sender
    BROADCAST = auto()         # Send to all matching agents


@dataclass
class RouteRule:
    """A routing rule for directing messages."""
    rule_id: str
    priority: int = 0  # Higher = evaluated first
    capability_requirement: Optional[CapabilityRequirement] = None
    target_agents: Optional[list[str]] = None  # Specific agents
    target_tags: Optional[list[str]] = None    # Agents with tags
    strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def matches(self, message: RoutedMessage, agent: AgentInfo) -> bool:
        """Check if this rule matches a message and agent."""
        if not self.enabled:
            return False
        
        # Check capability requirement
        if self.capability_requirement:
            if not agent.has_capability(self.capability_requirement):
                return False
        
        # Check specific agents
        if self.target_agents and agent.agent_id not in self.target_agents:
            return False
        
        # Check tags
        if self.target_tags:
            if not any(tag in agent.tags for tag in self.target_tags):
                return False
        
        # Check metadata filters
        for key, value in self.metadata_filters.items():
            if agent.metadata.get(key) != value:
                return False
        
        return True


@dataclass
class RoutedMessage:
    """A message being routed through the system."""
    message_id: str
    source: str
    content: Any
    capability_requirement: Optional[CapabilityRequirement] = None
    preferred_agents: list[str] = field(default_factory=list)
    excluded_agents: list[str] = field(default_factory=list)
    message_type: str = "text"
    priority: int = 0  # Higher = processed first
    ttl: int = 3  # Time-to-live (hops)
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    routing_history: list[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if message has exceeded TTL."""
        return len(self.routing_history) >= self.ttl
    
    def add_hop(self, agent_id: str) -> None:
        """Record a routing hop."""
        self.routing_history.append(agent_id)
    
    def to_session_message(self, target: str) -> SessionMessage:
        """Convert to a session message."""
        return SessionMessage(
            message_id=self.message_id,
            session_id="",  # Set by session manager
            source=self.source,
            target=target,
            content=self.content,
            message_type=self.message_type,
            metadata=self.metadata,
            correlation_id=self.correlation_id
        )


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    success: bool
    target_agents: list[str] = field(default_factory=list)
    message_id: str = ""
    error: Optional[str] = None
    routing_time_ms: float = 0.0
    strategy_used: Optional[RoutingStrategy] = None


class LoadBalancer:
    """
    Load balancing strategies for agent selection.
    """
    
    def __init__(self):
        self._round_robin_counters: dict[str, int] = defaultdict(int)
        self._sticky_sessions: dict[str, str] = {}  # sender -> agent
        self._lock = asyncio.Lock()
    
    async def select(
        self,
        candidates: list[AgentInfo],
        strategy: RoutingStrategy,
        sender: str,
        capability_name: Optional[str] = None
    ) -> list[AgentInfo]:
        """
        Select agent(s) based on strategy.
        Returns list (may be empty or contain multiple for broadcast).
        """
        if not candidates:
            return []
        
        # Filter to healthy agents
        healthy = [a for a in candidates if a.is_healthy()]
        if not healthy:
            return []
        
        if strategy == RoutingStrategy.BROADCAST:
            return healthy
        
        if strategy == RoutingStrategy.STICKY:
            async with self._lock:
                sticky_agent_id = self._sticky_sessions.get(sender)
                if sticky_agent_id:
                    for agent in healthy:
                        if agent.agent_id == sticky_agent_id:
                            return [agent]
        
        if strategy == RoutingStrategy.LEAST_LOADED:
            # Sort by load score ascending
            return [min(healthy, key=lambda a: a.load_score)]
        
        if strategy == RoutingStrategy.CAPABILITY_PRIORITY:
            # Sort by capability priority descending, then load ascending
            def priority_key(a: AgentInfo):
                cap = a.get_capability(capability_name) if capability_name else None
                priority = cap.priority if cap else 0
                return (-priority, a.load_score)
            return [min(healthy, key=priority_key)]
        
        if strategy == RoutingStrategy.RANDOM:
            return [random.choice(healthy)]
        
        if strategy == RoutingStrategy.ROUND_ROBIN:
            async with self._lock:
                key = capability_name or "default"
                counter = self._round_robin_counters[key]
                self._round_robin_counters[key] = (counter + 1) % len(healthy)
                return [healthy[counter % len(healthy)]]
        
        # Default: return first healthy
        return [healthy[0]]
    
    def set_sticky(self, sender: str, agent_id: str) -> None:
        """Set sticky session for a sender."""
        self._sticky_sessions[sender] = agent_id
    
    def clear_sticky(self, sender: str) -> None:
        """Clear sticky session."""
        if sender in self._sticky_sessions:
            del self._sticky_sessions[sender]


class AgentRouter:
    """
    Routes messages to appropriate agents based on capabilities and load.
    
    The router is the central component that:
    1. Receives messages with routing requirements
    2. Finds agents matching capability requirements
    3. Applies load balancing strategies
    4. Delivers messages to agent sessions
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.load_balancer = LoadBalancer()
        self._rules: list[RouteRule] = []
        self._delivery_callbacks: list[Callable[[str, SessionMessage], Coroutine]] = []
        self._routing_stats = defaultdict(lambda: defaultdict(int))
        self._lock = asyncio.Lock()
    
    def add_rule(self, rule: RouteRule) -> None:
        """Add a routing rule. Rules are evaluated by priority (higher first)."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: -r.priority)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a routing rule by ID."""
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                self._rules.pop(i)
                return True
        return False
    
    async def route(
        self,
        message: RoutedMessage,
        strategy: Optional[RoutingStrategy] = None
    ) -> RoutingResult:
        """
        Route a message to appropriate agent(s).
        
        Args:
            message: The message to route
            strategy: Optional override for routing strategy
            
        Returns:
            RoutingResult with target agents and success status
        """
        start_time = time.time()
        
        # Check TTL
        if message.is_expired():
            return RoutingResult(
                success=False,
                message_id=message.message_id,
                error="Message TTL exceeded",
                routing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Find candidates
        candidates = await self._find_candidates(message)
        
        # Apply exclusion list
        candidates = [
            c for c in candidates
            if c.agent_id not in message.excluded_agents
        ]
        
        if not candidates:
            return RoutingResult(
                success=False,
                message_id=message.message_id,
                error="No available agents match requirements",
                routing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Determine strategy
        used_strategy = strategy or RoutingStrategy.LEAST_LOADED
        for rule in self._rules:
            if rule.matches(message, candidates[0]):
                used_strategy = rule.strategy
                break
        
        # Select target(s)
        targets = await self.load_balancer.select(
            candidates,
            used_strategy,
            message.source,
            message.capability_requirement.name if message.capability_requirement else None
        )
        
        if not targets:
            return RoutingResult(
                success=False,
                message_id=message.message_id,
                error="No healthy agents available",
                routing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Deliver to targets
        target_ids = [t.agent_id for t in targets]
        delivery_success = await self._deliver(message, target_ids)
        
        # Update stats
        async with self._lock:
            for tid in target_ids:
                self._routing_stats[tid]["messages_routed"] += 1
        
        return RoutingResult(
            success=delivery_success,
            target_agents=target_ids,
            message_id=message.message_id,
            routing_time_ms=(time.time() - start_time) * 1000,
            strategy_used=used_strategy
        )
    
    async def _find_candidates(
        self,
        message: RoutedMessage
    ) -> list[AgentInfo]:
        """Find candidate agents for a message."""
        candidates = []
        
        if message.capability_requirement:
            # Find by capability
            candidates = self.registry.find_agents_for_requirement(
                message.capability_requirement
            )
        elif message.preferred_agents:
            # Use preferred agents
            for agent_id in message.preferred_agents:
                agent = self.registry.get_agent(agent_id)
                if agent and agent.is_healthy():
                    candidates.append(agent)
        else:
            # Get all healthy agents
            candidates = self.registry.get_healthy_agents()
        
        return candidates
    
    async def _deliver(
        self,
        message: RoutedMessage,
        target_ids: list[str]
    ) -> bool:
        """Deliver message to target agent(s)."""
        success = False
        
        for target_id in target_ids:
            session_message = message.to_session_message(target_id)
            session_message.add_to_history = message.source  # Track hop
            
            for callback in self._delivery_callbacks:
                try:
                    await callback(target_id, session_message)
                    success = True
                except Exception:
                    pass
        
        return success
    
    def on_deliver(
        self,
        callback: Callable[[str, SessionMessage], Coroutine]
    ) -> None:
        """Register a delivery callback."""
        self._delivery_callbacks.append(callback)
    
    def create_message(
        self,
        source: str,
        content: Any,
        capability_name: Optional[str] = None,
        **kwargs
    ) -> RoutedMessage:
        """Helper to create a routed message."""
        req = None
        if capability_name:
            req = CapabilityRequirement(name=capability_name)
        
        return RoutedMessage(
            message_id=str(uuid.uuid4()),
            source=source,
            content=content,
            capability_requirement=req,
            **kwargs
        )
    
    def get_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        return {
            "routing_stats": dict(self._routing_stats),
            "active_rules": len(self._rules),
            "rules_by_priority": [r.rule_id for r in self._rules]
        }
    
    async def route_with_response(
        self,
        message: RoutedMessage,
        timeout: float = 30.0,
        strategy: Optional[RoutingStrategy] = None
    ) -> tuple[RoutingResult, Optional[SessionMessage]]:
        """
        Route a message and wait for a response.
        
        This is a convenience method for request/response patterns.
        """
        result = await self.route(message, strategy)
        
        if not result.success:
            return result, None
        
        # Response waiting would be implemented by the session manager
        # This is a placeholder for the pattern
        return result, None


class RouterMiddleware:
    """
    Middleware for processing messages before/after routing.
    """
    
    def __init__(self):
        self._pre_processors: list[Callable[[RoutedMessage], Coroutine]] = []
        self._post_processors: list[Callable[[RoutedMessage, RoutingResult], Coroutine]] = []
    
    def add_pre_processor(
        self,
        processor: Callable[[RoutedMessage], Coroutine]
    ) -> None:
        """Add a pre-routing processor."""
        self._pre_processors.append(processor)
    
    def add_post_processor(
        self,
        processor: Callable[[RoutedMessage, RoutingResult], Coroutine]
    ) -> None:
        """Add a post-routing processor."""
        self._post_processors.append(processor)
    
    async def pre_process(self, message: RoutedMessage) -> None:
        """Run pre-processors."""
        for processor in self._pre_processors:
            try:
                await processor(message)
            except Exception:
                pass
    
    async def post_process(
        self,
        message: RoutedMessage,
        result: RoutingResult
    ) -> None:
        """Run post-processors."""
        for processor in self._post_processors:
            try:
                await processor(message, result)
            except Exception:
                pass
