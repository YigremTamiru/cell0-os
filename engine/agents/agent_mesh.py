"""
Agent Mesh - Agent-to-agent communication and mesh networking.

Cell 0 OS - Multi-Agent Routing System
"""
from __future__ import annotations
import asyncio
import time
import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Callable, Coroutine, AsyncIterator
from collections import defaultdict
import uuid

from engine.agents.agent_registry import AgentRegistry, AgentInfo
from engine.agents.agent_session import AgentSession, SessionMessage
from engine.agents.agent_router import AgentRouter, RoutedMessage, RoutingStrategy


class MessagePattern(Enum):
    """Communication patterns between agents."""
    DIRECT = auto()          # One-to-one
    BROADCAST = auto()       # One-to-all
    MULTICAST = auto()       # One-to-group
    REQUEST_REPLY = auto()   # Request with expected reply
    PUBLISH_SUBSCRIBE = auto()  # Pub/sub pattern
    PIPELINE = auto()        # Chain of agents
    GATHER = auto()          # Collect from multiple agents
    SCATTER = auto()         # Distribute to multiple agents


@dataclass
class Subscription:
    """A pub/sub subscription."""
    subscription_id: str
    subscriber_id: str
    topic: str
    filter_fn: Optional[Callable[[Any], bool]] = None
    created_at: float = field(default_factory=time.time)
    
    def matches(self, message: Any) -> bool:
        """Check if message matches subscription."""
        if self.filter_fn:
            return self.filter_fn(message)
        return True


@dataclass
class MeshMessage:
    """A message in the agent mesh."""
    message_id: str
    pattern: MessagePattern
    source: str
    targets: list[str]  # Empty = broadcast
    payload: Any
    topic: Optional[str] = None
    reply_to: Optional[str] = None  # For request/reply
    timeout_ms: int = 30000
    timestamp: float = field(default_factory=time.time)
    headers: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    
    def create_reply(self, payload: Any) -> MeshMessage:
        """Create a reply message."""
        if not self.reply_to:
            raise ValueError("Cannot reply to message without reply_to")
        return MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.DIRECT,
            source=self.reply_to,
            targets=[self.source],
            payload=payload,
            topic=self.topic,
            headers={"in_reply_to": self.message_id}
        )


@dataclass
class PipelineStage:
    """A stage in an agent pipeline."""
    stage_id: str
    agent_id: str
    capability_required: Optional[str] = None
    condition: Optional[Callable[[Any], bool]] = None
    transform: Optional[Callable[[Any], Any]] = None
    timeout_ms: int = 30000


@dataclass
class Pipeline:
    """A processing pipeline of agent stages."""
    pipeline_id: str
    stages: list[PipelineStage] = field(default_factory=list)
    error_handler: Optional[str] = None  # Agent to handle errors
    
    def add_stage(self, stage: PipelineStage) -> None:
        """Add a stage to the pipeline."""
        self.stages.append(stage)
    
    async def execute(
        self,
        initial_payload: Any,
        mesh: AgentMesh
    ) -> tuple[bool, Any, list[str]]:
        """
        Execute the pipeline.
        
        Returns: (success, final_payload, path_taken)
        """
        current_payload = initial_payload
        path = []
        
        for stage in self.stages:
            # Check condition
            if stage.condition and not stage.condition(current_payload):
                continue
            
            # Apply transform
            if stage.transform:
                current_payload = stage.transform(current_payload)
            
            # Send to agent
            result = await mesh.request(
                source="pipeline",
                target=stage.agent_id,
                payload=current_payload,
                timeout_ms=stage.timeout_ms
            )
            
            if result is None:
                # Handle error
                if self.error_handler:
                    error_result = await mesh.request(
                        source="pipeline",
                        target=self.error_handler,
                        payload={"error": "stage_failed", "stage": stage.stage_id}
                    )
                return False, current_payload, path
            
            current_payload = result
            path.append(stage.agent_id)
        
        return True, current_payload, path


class AgentMesh:
    """
    Mesh networking layer for agent-to-agent communication.
    
    Provides:
    - Pub/sub messaging
    - Request/reply patterns
    - Pipeline processing
    - Scatter/gather operations
    - Group multicast
    """
    
    def __init__(self, registry: AgentRegistry, router: AgentRouter):
        self.registry = registry
        self.router = router
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._groups: dict[str, set[str]] = defaultdict(set)  # group -> agents
        self._pipelines: dict[str, Pipeline] = {}
        self._pending_replies: dict[str, asyncio.Future] = {}
        self._message_handlers: dict[MessagePattern, Callable] = {}
        self._lock = asyncio.Lock()
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Setup message pattern handlers."""
        self._message_handlers = {
            MessagePattern.DIRECT: self._handle_direct,
            MessagePattern.BROADCAST: self._handle_broadcast,
            MessagePattern.MULTICAST: self._handle_multicast,
            MessagePattern.REQUEST_REPLY: self._handle_request_reply,
            MessagePattern.PUBLISH_SUBSCRIBE: self._handle_publish_subscribe,
            MessagePattern.PIPELINE: self._handle_pipeline,
            MessagePattern.GATHER: self._handle_gather,
            MessagePattern.SCATTER: self._handle_scatter,
        }
    
    async def send(self, message: MeshMessage) -> dict[str, bool]:
        """
        Send a message using the appropriate pattern.
        
        Returns: {target_id: success}
        """
        handler = self._message_handlers.get(message.pattern)
        if not handler:
            raise ValueError(f"Unknown message pattern: {message.pattern}")
        
        return await handler(message)
    
    async def _handle_direct(self, message: MeshMessage) -> dict[str, bool]:
        """Handle direct one-to-one message."""
        results = {}
        for target in message.targets:
            routed = self._to_routed_message(message, [target])
            result = await self.router.route(routed)
            results[target] = result.success
        return results
    
    async def _handle_broadcast(self, message: MeshMessage) -> dict[str, bool]:
        """Handle broadcast to all agents."""
        routed = self._to_routed_message(message, [])
        routed.strategy = RoutingStrategy.BROADCAST
        result = await self.router.route(routed)
        return {agent: result.success for agent in result.target_agents}
    
    async def _handle_multicast(self, message: MeshMessage) -> dict[str, bool]:
        """Handle multicast to a group."""
        results = {}
        for group in message.targets:
            for agent_id in self._groups.get(group, set()):
                routed = self._to_routed_message(message, [agent_id])
                result = await self.router.route(routed)
                results[agent_id] = result.success
        return results
    
    async def _handle_request_reply(
        self,
        message: MeshMessage
    ) -> dict[str, bool]:
        """Handle request with expected reply."""
        results = {}
        
        for target in message.targets:
            # Create future for reply
            reply_future = asyncio.get_event_loop().create_future()
            
            async with self._lock:
                self._pending_replies[message.message_id] = reply_future
            
            # Send request
            routed = self._to_routed_message(message, [target])
            result = await self.router.route(routed)
            results[target] = result.success
            
            if result.success:
                # Wait for reply
                try:
                    await asyncio.wait_for(
                        reply_future,
                        timeout=message.timeout_ms / 1000
                    )
                except asyncio.TimeoutError:
                    results[target] = False
                finally:
                    async with self._lock:
                        self._pending_replies.pop(message.message_id, None)
        
        return results
    
    async def _handle_publish_subscribe(
        self,
        message: MeshMessage
    ) -> dict[str, bool]:
        """Handle pub/sub message."""
        results = {}
        
        if not message.topic:
            return results
        
        # Find subscribers
        subscribers = self._subscriptions.get(message.topic, [])
        
        for sub in subscribers:
            if sub.matches(message.payload):
                routed = self._to_routed_message(message, [sub.subscriber_id])
                result = await self.router.route(routed)
                results[sub.subscriber_id] = result.success
        
        return results
    
    async def _handle_pipeline(self, message: MeshMessage) -> dict[str, bool]:
        """Handle pipeline execution."""
        pipeline_id = message.headers.get("pipeline_id")
        if not pipeline_id or pipeline_id not in self._pipelines:
            return {}
        
        pipeline = self._pipelines[pipeline_id]
        success, final_payload, path = await pipeline.execute(
            message.payload,
            self
        )
        
        return {"pipeline": success, "path": path, "result": final_payload}
    
    async def _handle_gather(self, message: MeshMessage) -> dict[str, Any]:
        """Handle gather from multiple agents."""
        # Send to all targets and collect results
        tasks = []
        for target in message.targets:
            routed = self._to_routed_message(message, [target])
            tasks.append(self.router.route(routed))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        gathered = {}
        for target, result in zip(message.targets, results):
            if isinstance(result, Exception):
                gathered[target] = {"error": str(result)}
            else:
                gathered[target] = {
                    "success": result.success,
                    "data": result.target_agents
                }
        
        return gathered
    
    async def _handle_scatter(self, message: MeshMessage) -> dict[str, bool]:
        """Handle scatter (distribute work to multiple agents)."""
        results = {}
        
        if not isinstance(message.payload, list):
            message.payload = [message.payload]
        
        # Distribute items to targets
        items = message.payload
        targets = message.targets
        
        if not targets:
            return results
        
        # Round-robin distribution
        tasks = []
        for i, item in enumerate(items):
            target = targets[i % len(targets)]
            routed = self._to_routed_message(message, [target])
            routed.content = item
            tasks.append(self.router.route(routed))
        
        route_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(route_results):
            target = targets[i % len(targets)]
            if isinstance(result, Exception):
                results[f"{target}_{i}"] = False
            else:
                results[f"{target}_{i}"] = result.success
        
        return results
    
    def _to_routed_message(
        self,
        mesh_message: MeshMessage,
        targets: list[str]
    ) -> RoutedMessage:
        """Convert mesh message to routed message."""
        return RoutedMessage(
            message_id=mesh_message.message_id,
            source=mesh_message.source,
            content=mesh_message.payload,
            message_type=mesh_message.pattern.name,
            preferred_agents=targets,
            priority=mesh_message.priority,
            metadata={
                "mesh_headers": mesh_message.headers,
                "topic": mesh_message.topic,
                "reply_to": mesh_message.reply_to
            },
            correlation_id=mesh_message.headers.get("correlation_id")
        )
    
    # Public API
    
    async def publish(
        self,
        source: str,
        topic: str,
        payload: Any,
        headers: Optional[dict] = None
    ) -> dict[str, bool]:
        """Publish a message to a topic."""
        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.PUBLISH_SUBSCRIBE,
            source=source,
            targets=[],
            payload=payload,
            topic=topic,
            headers=headers or {}
        )
        return await self.send(message)
    
    async def request(
        self,
        source: str,
        target: str,
        payload: Any,
        timeout_ms: int = 30000,
        headers: Optional[dict] = None
    ) -> Optional[Any]:
        """Send a request and wait for reply."""
        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.REQUEST_REPLY,
            source=source,
            targets=[target],
            payload=payload,
            reply_to=source,
            timeout_ms=timeout_ms,
            headers=headers or {}
        )
        results = await self.send(message)
        # In real implementation, would return actual response
        return results.get(target)
    
    async def broadcast(
        self,
        source: str,
        payload: Any,
        headers: Optional[dict] = None
    ) -> dict[str, bool]:
        """Broadcast a message to all agents."""
        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.BROADCAST,
            source=source,
            targets=[],
            payload=payload,
            headers=headers or {}
        )
        return await self.send(message)
    
    async def multicast(
        self,
        source: str,
        groups: list[str],
        payload: Any,
        headers: Optional[dict] = None
    ) -> dict[str, bool]:
        """Multicast to agent groups."""
        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.MULTICAST,
            source=source,
            targets=groups,
            payload=payload,
            headers=headers or {}
        )
        return await self.send(message)
    
    async def gather(
        self,
        source: str,
        targets: list[str],
        payload: Any,
        timeout_ms: int = 30000,
        headers: Optional[dict] = None
    ) -> dict[str, Any]:
        """Gather responses from multiple agents."""
        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.GATHER,
            source=source,
            targets=targets,
            payload=payload,
            timeout_ms=timeout_ms,
            headers=headers or {}
        )
        return await self.send(message)
    
    async def scatter(
        self,
        source: str,
        targets: list[str],
        items: list[Any],
        headers: Optional[dict] = None
    ) -> dict[str, bool]:
        """Scatter items across multiple agents."""
        message = MeshMessage(
            message_id=str(uuid.uuid4()),
            pattern=MessagePattern.SCATTER,
            source=source,
            targets=targets,
            payload=items,
            headers=headers or {}
        )
        return await self.send(message)
    
    # Subscription management
    
    def subscribe(
        self,
        subscriber_id: str,
        topic: str,
        filter_fn: Optional[Callable[[Any], bool]] = None
    ) -> str:
        """Subscribe to a topic."""
        sub_id = str(uuid.uuid4())
        subscription = Subscription(
            subscription_id=sub_id,
            subscriber_id=subscriber_id,
            topic=topic,
            filter_fn=filter_fn
        )
        self._subscriptions[topic].append(subscription)
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        for topic, subs in self._subscriptions.items():
            for i, sub in enumerate(subs):
                if sub.subscription_id == subscription_id:
                    subs.pop(i)
                    return True
        return False
    
    # Group management
    
    def join_group(self, agent_id: str, group: str) -> None:
        """Add an agent to a group."""
        self._groups[group].add(agent_id)
    
    def leave_group(self, agent_id: str, group: str) -> None:
        """Remove an agent from a group."""
        self._groups[group].discard(agent_id)
    
    def get_group_members(self, group: str) -> set[str]:
        """Get all agents in a group."""
        return self._groups[group].copy()
    
    # Pipeline management
    
    def create_pipeline(self, pipeline_id: str) -> Pipeline:
        """Create a new pipeline."""
        pipeline = Pipeline(pipeline_id=pipeline_id)
        self._pipelines[pipeline_id] = pipeline
        return pipeline
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self._pipelines.get(pipeline_id)
    
    # Reply handling
    
    async def handle_reply(self, message_id: str, reply: Any) -> None:
        """Handle an incoming reply."""
        async with self._lock:
            future = self._pending_replies.get(message_id)
            if future and not future.done():
                future.set_result(reply)
    
    def get_stats(self) -> dict[str, Any]:
        """Get mesh statistics."""
        return {
            "subscriptions_by_topic": {
                topic: len(subs) for topic, subs in self._subscriptions.items()
            },
            "groups": {g: len(members) for g, members in self._groups.items()},
            "pipelines": len(self._pipelines),
            "pending_replies": len(self._pending_replies)
        }
