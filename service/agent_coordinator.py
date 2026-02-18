"""
Agent Coordinator - Central coordinator service for the multi-agent system.

Cell 0 OS - Multi-Agent Routing System
"""
from __future__ import annotations
import asyncio
import time
import signal
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Coroutine
from collections import defaultdict
import uuid

from engine.agents.agent_registry import (
    AgentRegistry, AgentInfo, AgentCapability, CapabilityRequirement, AgentStatus
)
from engine.agents.agent_session import AgentSession, SessionManager, SessionMessage
from engine.agents.agent_router import AgentRouter, RoutedMessage, RoutingStrategy, RoutingResult
from engine.agents.agent_mesh import AgentMesh, MeshMessage, MessagePattern


@dataclass
class CoordinatorConfig:
    """Configuration for the agent coordinator."""
    heartbeat_interval_seconds: float = 30.0
    health_check_interval_seconds: float = 10.0
    stale_agent_timeout_seconds: float = 120.0
    max_concurrent_messages: int = 1000
    default_message_timeout_seconds: float = 30.0
    enable_auto_scaling: bool = False
    log_level: str = "INFO"


@dataclass
class SystemStats:
    """System-wide statistics."""
    total_agents: int = 0
    healthy_agents: int = 0
    total_sessions: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    avg_routing_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class AgentCoordinator:
    """
    Central coordinator for the multi-agent routing system.
    
    Responsibilities:
    1. Manage component lifecycle (registry, sessions, router, mesh)
    2. Health checking and monitoring
    3. Agent lifecycle management
    4. System-wide statistics and metrics
    5. Configuration management
    6. Graceful shutdown handling
    
    This is the main entry point for interacting with the agent system.
    """
    
    def __init__(self, config: Optional[CoordinatorConfig] = None):
        self.config = config or CoordinatorConfig()
        
        # Core components
        self.registry = AgentRegistry()
        self.sessions = SessionManager()
        self.router = AgentRouter(self.registry)
        self.mesh = AgentMesh(self.registry, self.router)
        
        # Lifecycle
        self._running = False
        self._tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        
        # Metrics
        self._stats = SystemStats()
        self._message_times: list[float] = []
        
        # Event callbacks
        self._event_callbacks: list[Callable[[str, Any], Coroutine]] = []
        
        # Setup router delivery callback
        self.router.on_deliver(self._on_message_deliver)
    
    async def start(self) -> None:
        """Start the coordinator and all services."""
        if self._running:
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Subscribe to registry events
        self.registry.subscribe(self._on_registry_event)
        
        # Start background tasks
        self._tasks.add(
            asyncio.create_task(self._health_check_loop())
        )
        self._tasks.add(
            asyncio.create_task(self._cleanup_loop())
        )
        self._tasks.add(
            asyncio.create_task(self._metrics_loop())
        )
        
        await self._notify_event("coordinator_started", {"config": self.config})
    
    async def stop(self, timeout: float = 30.0) -> None:
        """Gracefully stop the coordinator."""
        if not self._running:
            return
        
        self._running = False
        self._shutdown_event.set()
        
        # Cancel all background tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            done, pending = await asyncio.wait(
                self._tasks,
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED
            )
            
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._tasks.clear()
        
        # Shutdown all sessions
        for session in self.sessions.get_all_sessions():
            await self.sessions.destroy_session(session.session_id, timeout)
        
        await self._notify_event("coordinator_stopped", {})
    
    # Agent Management
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[AgentCapability],
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[set[str]] = None,
        create_session: bool = True
    ) -> AgentInfo:
        """
        Register a new agent with the system.
        
        Args:
            agent_id: Unique agent identifier
            agent_type: Type/category of agent
            capabilities: List of agent capabilities
            metadata: Optional metadata
            tags: Optional tags for grouping
            create_session: Whether to create a session for the agent
            
        Returns:
            AgentInfo for the registered agent
        """
        # Register with registry
        agent_info = await self.registry.register(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            metadata=metadata,
            tags=tags
        )
        
        # Create session if requested
        if create_session:
            await self.sessions.create_session(agent_id)
        
        await self._notify_event("agent_registered", {"agent_id": agent_id})
        return agent_info
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the system."""
        # Destroy session first
        session = self.sessions.get_session_for_agent(agent_id)
        if session:
            await self.sessions.destroy_session(session.session_id)
        
        # Unregister from registry
        result = await self.registry.unregister(agent_id)
        
        if result:
            await self._notify_event("agent_unregistered", {"agent_id": agent_id})
        
        return result is not None
    
    async def send_heartbeat(
        self,
        agent_id: str,
        load_score: Optional[float] = None
    ) -> bool:
        """Send heartbeat for an agent."""
        return await self.registry.update_heartbeat(agent_id, load_score)
    
    # Message Routing
    
    async def send_message(
        self,
        source: str,
        target: str,
        content: Any,
        message_type: str = "text",
        timeout: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> RoutingResult:
        """
        Send a direct message to a specific agent.
        """
        message = RoutedMessage(
            message_id=str(uuid.uuid4()),
            source=source,
            content=content,
            message_type=message_type,
            preferred_agents=[target],
            metadata=metadata or {}
        )
        
        start_time = time.time()
        result = await self.router.route(message)
        self._update_message_stats(time.time() - start_time, result.success)
        
        return result
    
    async def route_by_capability(
        self,
        source: str,
        content: Any,
        capability_name: str,
        strategy: Optional[RoutingStrategy] = None,
        min_version: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> RoutingResult:
        """
        Route a message to an agent with the required capability.
        """
        requirement = CapabilityRequirement(
            name=capability_name,
            min_version=min_version
        )
        
        message = RoutedMessage(
            message_id=str(uuid.uuid4()),
            source=source,
            content=content,
            capability_requirement=requirement,
            metadata=metadata or {}
        )
        
        start_time = time.time()
        result = await self.router.route(message, strategy)
        self._update_message_stats(time.time() - start_time, result.success)
        
        return result
    
    async def broadcast(
        self,
        source: str,
        content: Any,
        metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, bool]:
        """Broadcast a message to all agents."""
        return await self.mesh.broadcast(source, content, metadata)
    
    async def request_reply(
        self,
        source: str,
        target: str,
        content: Any,
        timeout: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Any]:
        """Send a request and wait for reply."""
        timeout_ms = int((timeout or self.config.default_message_timeout_seconds) * 1000)
        return await self.mesh.request(source, target, content, timeout_ms, metadata)
    
    # Pub/Sub
    
    def subscribe(
        self,
        subscriber_id: str,
        topic: str,
        filter_fn: Optional[Callable[[Any], bool]] = None
    ) -> str:
        """Subscribe to a topic."""
        return self.mesh.subscribe(subscriber_id, topic, filter_fn)
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        return self.mesh.unsubscribe(subscription_id)
    
    async def publish(
        self,
        source: str,
        topic: str,
        payload: Any,
        headers: Optional[dict[str, Any]] = None
    ) -> dict[str, bool]:
        """Publish to a topic."""
        return await self.mesh.publish(source, topic, payload, headers)
    
    # Group Management
    
    def join_group(self, agent_id: str, group: str) -> None:
        """Add an agent to a group."""
        self.mesh.join_group(agent_id, group)
    
    def leave_group(self, agent_id: str, group: str) -> None:
        """Remove an agent from a group."""
        self.mesh.leave_group(agent_id, group)
    
    # Capability-based Discovery
    
    def find_agents(
        self,
        capability_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        tag: Optional[str] = None,
        healthy_only: bool = True
    ) -> list[AgentInfo]:
        """
        Find agents matching criteria.
        """
        if capability_name:
            agents = self.registry.get_agents_by_capability(capability_name)
        elif agent_type:
            agents = self.registry.get_agents_by_type(agent_type)
        elif tag:
            agents = self.registry.get_agents_by_tag(tag)
        else:
            agents = self.registry.get_all_agents()
        
        if healthy_only:
            agents = [a for a in agents if a.is_healthy()]
        
        return agents
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        return self.registry.get_agent(agent_id)
    
    def get_agent_session(self, agent_id: str) -> Optional[AgentSession]:
        """Get the session for a specific agent."""
        return self.sessions.get_session_for_agent(agent_id)
    
    # Statistics and Health
    
    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "system": self._stats,
            "registry": self.registry.get_stats(),
            "sessions": self.sessions.get_stats(),
            "router": self.router.get_stats(),
            "mesh": self.mesh.get_stats()
        }
    
    def get_health(self) -> dict[str, Any]:
        """Get system health status."""
        registry_stats = self.registry.get_stats()
        
        healthy_ratio = (
            registry_stats["healthy_agents"] / max(registry_stats["total_agents"], 1)
        )
        
        status = "healthy"
        if healthy_ratio < 0.5:
            status = "critical"
        elif healthy_ratio < 0.8:
            status = "degraded"
        
        return {
            "status": status,
            "healthy_ratio": healthy_ratio,
            "agents": {
                "total": registry_stats["total_agents"],
                "healthy": registry_stats["healthy_agents"]
            },
            "is_running": self._running
        }
    
    # Event Handling
    
    def subscribe_to_events(
        self,
        callback: Callable[[str, Any], Coroutine]
    ) -> None:
        """Subscribe to system events."""
        self._event_callbacks.append(callback)
    
    def unsubscribe_from_events(
        self,
        callback: Callable[[str, Any], Coroutine]
    ) -> None:
        """Unsubscribe from system events."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    # Background Tasks
    
    async def _health_check_loop(self) -> None:
        """Periodic health checking."""
        while self._running:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.health_check_interval_seconds
                )
            except asyncio.TimeoutError:
                pass
            
            if not self._running:
                break
            
            # Check agent health
            for agent in self.registry.get_all_agents():
                if not agent.is_healthy():
                    await self._notify_event(
                        "agent_unhealthy",
                        {"agent_id": agent.agent_id}
                    )
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale agents."""
        while self._running:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.stale_agent_timeout_seconds
                )
            except asyncio.TimeoutError:
                pass
            
            if not self._running:
                break
            
            # Cleanup stale agents
            removed = await self.registry.cleanup_stale_agents(
                self.config.stale_agent_timeout_seconds
            )
            
            if removed:
                await self._notify_event(
                    "agents_cleaned_up",
                    {"removed": removed}
                )
    
    async def _metrics_loop(self) -> None:
        """Update system metrics."""
        while self._running:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=60.0  # Update every minute
                )
            except asyncio.TimeoutError:
                pass
            
            if not self._running:
                break
            
            # Update stats
            registry_stats = self.registry.get_stats()
            self._stats.total_agents = registry_stats["total_agents"]
            self._stats.healthy_agents = registry_stats["healthy_agents"]
            self._stats.total_sessions = len(self.sessions.get_all_sessions())
            
            if self._message_times:
                self._stats.avg_routing_time_ms = (
                    sum(self._message_times) / len(self._message_times) * 1000
                )
                self._message_times = []
    
    # Event Handlers
    
    async def _on_registry_event(
        self,
        agent_id: str,
        agent_info: AgentInfo,
        event_type: str
    ) -> None:
        """Handle registry events."""
        await self._notify_event(f"registry_{event_type}", {
            "agent_id": agent_id,
            "agent_type": agent_info.agent_type
        })
    
    async def _on_message_deliver(
        self,
        target_id: str,
        message: SessionMessage
    ) -> None:
        """Handle message delivery from router."""
        # Deliver to agent session
        session = self.sessions.get_session_for_agent(target_id)
        if session:
            await session.receive(message)
            await self.registry.increment_message_count(target_id)
    
    async def _notify_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Notify all event subscribers."""
        for callback in self._event_callbacks:
            try:
                await callback(event_type, data)
            except Exception:
                pass
    
    def _update_message_stats(self, elapsed: float, success: bool) -> None:
        """Update message processing statistics."""
        self._message_times.append(elapsed)
        if success:
            self._stats.messages_processed += 1
        else:
            self._stats.messages_failed += 1
    
    # Context manager support
    
    async def __aenter__(self) -> AgentCoordinator:
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
