"""
Tests for the Multi-Agent Routing System

Cell 0 OS - Multi-Agent Routing System
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
import time

# Import the modules under test
import sys
sys.path.insert(0, '.')

from engine.agents.agent_registry import (
    AgentRegistry, AgentCapability, CapabilityRequirement,
    AgentInfo, AgentStatus
)
from engine.agents.agent_session import (
    AgentSession, SessionManager, SessionMessage,
    SessionState, get_current_agent_id
)
from engine.agents.agent_router import (
    AgentRouter, RoutedMessage, RoutingStrategy,
    RoutingResult, RouteRule, LoadBalancer
)
from engine.agents.agent_mesh import (
    AgentMesh, MeshMessage, MessagePattern,
    Pipeline, PipelineStage
)
from service.agent_coordinator import (
    AgentCoordinator, CoordinatorConfig
)


# =============================================================================
# Agent Registry Tests
# =============================================================================

class TestAgentRegistry:
    """Tests for the AgentRegistry class."""
    
    @pytest.fixture
    async def registry(self):
        """Create a fresh registry for testing."""
        return AgentRegistry()
    
    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test basic agent registration."""
        registry = AgentRegistry()
        
        caps = [
            AgentCapability(name="text_processing", version="1.0.0"),
            AgentCapability(name="summarization", version="2.0.0", priority=5)
        ]
        
        agent = await registry.register(
            agent_id="agent-1",
            agent_type="nlp",
            capabilities=caps,
            metadata={"model": "gpt-4"},
            tags={"production", "nlp"}
        )
        
        assert agent.agent_id == "agent-1"
        assert agent.agent_type == "nlp"
        assert len(agent.capabilities) == 2
        assert agent.status == AgentStatus.ACTIVE
        assert agent.metadata["model"] == "gpt-4"
        assert "production" in agent.tags
    
    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self):
        """Test that registering duplicate agent raises error."""
        registry = AgentRegistry()
        
        caps = [AgentCapability(name="test")]
        await registry.register("agent-1", "test", caps)
        
        with pytest.raises(ValueError, match="already registered"):
            await registry.register("agent-1", "test", caps)
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self):
        """Test agent unregistration."""
        registry = AgentRegistry()
        
        caps = [AgentCapability(name="test")]
        await registry.register("agent-1", "test", caps)
        
        agent = await registry.unregister("agent-1")
        assert agent is not None
        assert agent.agent_id == "agent-1"
        
        # Should be removed
        assert registry.get_agent("agent-1") is None
    
    @pytest.mark.asyncio
    async def test_find_agents_by_capability(self):
        """Test finding agents by capability."""
        registry = AgentRegistry()
        
        # Register agents with different capabilities
        await registry.register(
            "agent-1", "nlp",
            [AgentCapability(name="text_processing", priority=5)]
        )
        await registry.register(
            "agent-2", "vision",
            [AgentCapability(name="image_processing")]
        )
        await registry.register(
            "agent-3", "nlp",
            [AgentCapability(name="text_processing", priority=10)]
        )
        
        # Find by capability
        agents = registry.get_agents_by_capability("text_processing")
        assert len(agents) == 2
        
        # Should be sorted by priority (higher first)
        assert agents[0].agent_id == "agent-3"  # priority 10
        assert agents[1].agent_id == "agent-1"  # priority 5
    
    @pytest.mark.asyncio
    async def test_capability_matching(self):
        """Test capability requirement matching."""
        registry = AgentRegistry()
        
        await registry.register(
            "agent-1", "test",
            [AgentCapability(name="api", version="2.0.0", metadata={"region": "us"})]
        )
        
        # Should match
        req = CapabilityRequirement(name="api", min_version="1.0.0")
        agents = registry.find_agents_for_requirement(req)
        assert len(agents) == 1
        
        # Should not match (version too low)
        req2 = CapabilityRequirement(name="api", min_version="3.0.0")
        agents2 = registry.find_agents_for_requirement(req2)
        assert len(agents2) == 0
        
        # Should match with metadata
        req3 = CapabilityRequirement(
            name="api",
            required_metadata={"region": "us"}
        )
        agents3 = registry.find_agents_for_requirement(req3)
        assert len(agents3) == 1
    
    @pytest.mark.asyncio
    async def test_heartbeat_tracking(self):
        """Test heartbeat and health tracking."""
        registry = AgentRegistry()
        
        await registry.register("agent-1", "test", [AgentCapability(name="test")])
        
        # Should be healthy initially
        agent = registry.get_agent("agent-1")
        assert agent.is_healthy()
        
        # Update heartbeat with load
        await registry.update_heartbeat("agent-1", load_score=0.5)
        
        agent = registry.get_agent("agent-1")
        assert agent.load_score == 0.5
        assert agent.is_healthy()
    
    @pytest.mark.asyncio
    async def test_registry_stats(self):
        """Test registry statistics."""
        registry = AgentRegistry()
        
        await registry.register(
            "agent-1", "type-a",
            [AgentCapability(name="cap-1")],
            tags={"tag1"}
        )
        await registry.register(
            "agent-2", "type-b",
            [AgentCapability(name="cap-1"), AgentCapability(name="cap-2")],
            tags={"tag1", "tag2"}
        )
        
        stats = registry.get_stats()
        
        assert stats["total_agents"] == 2
        assert stats["by_type"]["type-a"] == 1
        assert stats["by_type"]["type-b"] == 1
        assert stats["by_capability"]["cap-1"] == 2
        assert stats["by_capability"]["cap-2"] == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_agents(self):
        """Test cleanup of stale agents."""
        registry = AgentRegistry()
        
        await registry.register("agent-1", "test", [AgentCapability(name="test")])
        
        # Manually set last heartbeat to be old
        agent = registry.get_agent("agent-1")
        agent.last_heartbeat = time.time() - 200  # 200 seconds ago
        
        # Cleanup
        removed = await registry.cleanup_stale_agents(max_age_seconds=120)
        
        assert "agent-1" in removed
        assert registry.get_agent("agent-1") is None


# =============================================================================
# Agent Session Tests
# =============================================================================

class TestAgentSession:
    """Tests for the AgentSession class."""
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test session creation and shutdown."""
        session = AgentSession("agent-1", "session-1")
        
        assert session.state == SessionState.INITIALIZING
        
        await session.start()
        assert session.state == SessionState.ACTIVE
        
        await session.shutdown()
        assert session.state == SessionState.SHUTDOWN
    
    @pytest.mark.asyncio
    async def test_message_passing(self):
        """Test sending and receiving messages."""
        session = AgentSession("agent-1")
        await session.start()
        
        # Create and receive a message
        msg = SessionMessage(
            message_id="msg-1",
            session_id=session.session_id,
            source="user",
            target="agent-1",
            content="Hello!"
        )
        
        result = await session.receive(msg)
        assert result is True
        
        # Get the message back
        received = await session.get_next_message(timeout=1.0)
        assert received is not None
        assert received.message_id == "msg-1"
        assert received.content == "Hello!"
    
    @pytest.mark.asyncio
    async def test_session_memory(self):
        """Test session memory management."""
        session = AgentSession("agent-1")
        await session.start()
        
        session.update_memory("key1", "value1")
        session.update_memory("key2", {"nested": "data"})
        
        assert session.get_memory("key1") == "value1"
        assert session.get_memory("key2")["nested"] == "data"
        assert session.get_memory("nonexistent", "default") == "default"
        
        session.clear_memory()
        assert session.get_memory("key1") is None
    
    @pytest.mark.asyncio
    async def test_message_history(self):
        """Test message history tracking."""
        session = AgentSession("agent-1")
        await session.start()
        
        # Add messages to history
        session.context.add_to_history("user", "Hello")
        session.context.add_to_history("agent", "Hi there!")
        session.context.add_to_history("user", "How are you?")
        
        history = session.context.get_recent_history(n=2)
        assert len(history) == 2
        assert history[0]["role"] == "agent"
        assert history[1]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_concurrent_task_limit(self):
        """Test limiting concurrent tasks in session."""
        session = AgentSession("agent-1", max_concurrent_tasks=2)
        await session.start()
        
        async def slow_task():
            await asyncio.sleep(0.1)
            return "done"
        
        # Start multiple tasks
        task1 = session.execute(slow_task)
        task2 = session.execute(slow_task)
        task3 = session.execute(slow_task)  # Should wait for semaphore
        
        results = await asyncio.gather(task1, task2, task3)
        assert all(r == "done" for r in results)


class TestSessionManager:
    """Tests for the SessionManager class."""
    
    @pytest.mark.asyncio
    async def test_create_destroy_session(self):
        """Test session creation and destruction."""
        manager = SessionManager()
        
        session = await manager.create_session("agent-1")
        assert session.agent_id == "agent-1"
        assert session.state == SessionState.ACTIVE
        
        # Get session
        retrieved = manager.get_session_for_agent("agent-1")
        assert retrieved.session_id == session.session_id
        
        # Destroy
        result = await manager.destroy_session(session.session_id)
        assert result is True
        assert manager.get_session_for_agent("agent-1") is None
    
    @pytest.mark.asyncio
    async def test_duplicate_session_error(self):
        """Test that duplicate sessions raise error."""
        manager = SessionManager()
        
        await manager.create_session("agent-1")
        
        with pytest.raises(ValueError, match="already has an active session"):
            await manager.create_session("agent-1")
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting to all sessions."""
        manager = SessionManager()
        
        session1 = await manager.create_session("agent-1")
        session2 = await manager.create_session("agent-2")
        session3 = await manager.create_session("agent-3")
        
        delivered = await manager.broadcast(
            "system",
            {"type": "announcement"},
            exclude_self=False
        )
        
        assert len(delivered) == 3
        assert "agent-1" in delivered
        assert "agent-2" in delivered
        assert "agent-3" in delivered


# =============================================================================
# Agent Router Tests
# =============================================================================

class TestAgentRouter:
    """Tests for the AgentRouter class."""
    
    @pytest.fixture
    def setup_router(self):
        """Create router with test agents."""
        registry = AgentRegistry()
        router = AgentRouter(registry)
        return registry, router
    
    @pytest.mark.asyncio
    async def test_route_to_specific_agent(self):
        """Test routing to a specific agent."""
        registry, router = self.setup_router()
        
        # Register agent
        await registry.register(
            "agent-1", "test",
            [AgentCapability(name="text_processing")]
        )
        
        # Create message
        message = RoutedMessage(
            message_id="msg-1",
            source="user",
            content="Hello",
            preferred_agents=["agent-1"]
        )
        
        # Route
        results = []
        async def capture_delivery(target, msg):
            results.append(target)
        
        router.on_deliver(capture_delivery)
        result = await router.route(message)
        
        assert result.success is True
        assert "agent-1" in result.target_agents
    
    @pytest.mark.asyncio
    async def test_route_by_capability(self):
        """Test routing by capability requirement."""
        registry, router = self.setup_router()
        
        # Register agents with different capabilities
        await registry.register(
            "agent-1", "test",
            [AgentCapability(name="text_processing", priority=5)]
        )
        await registry.register(
            "agent-2", "test",
            [AgentCapability(name="image_processing", priority=10)]
        )
        
        # Route to text_processing capability
        message = RoutedMessage(
            message_id="msg-1",
            source="user",
            content="Summarize this",
            capability_requirement=CapabilityRequirement(name="text_processing")
        )
        
        results = []
        async def capture_delivery(target, msg):
            results.append(target)
        
        router.on_deliver(capture_delivery)
        result = await router.route(message)
        
        assert result.success is True
        assert result.target_agents == ["agent-1"]
    
    @pytest.mark.asyncio
    async def test_load_balancing_least_loaded(self):
        """Test least-loaded routing strategy."""
        registry, router = self.setup_router()
        
        # Register agents with different loads
        await registry.register(
            "agent-1", "test",
            [AgentCapability(name="compute")]
        )
        await registry.update_heartbeat("agent-1", load_score=0.8)
        
        await registry.register(
            "agent-2", "test",
            [AgentCapability(name="compute")]
        )
        await registry.update_heartbeat("agent-2", load_score=0.2)
        
        # Route with least_loaded strategy
        message = RoutedMessage(
            message_id="msg-1",
            source="user",
            content="Compute task",
            capability_requirement=CapabilityRequirement(name="compute")
        )
        
        targets = []
        async def capture_delivery(target, msg):
            targets.append(target)
        
        router.on_deliver(capture_delivery)
        result = await router.route(message, strategy=RoutingStrategy.LEAST_LOADED)
        
        assert result.success is True
        # Should route to agent-2 (lower load)
        assert result.target_agents == ["agent-2"]
    
    @pytest.mark.asyncio
    async def test_routing_rules(self):
        """Test custom routing rules."""
        registry, router = self.setup_router()
        
        await registry.register(
            "agent-1", "test",
            [AgentCapability(name="premium_feature")],
            tags={"premium"}
        )
        await registry.register(
            "agent-2", "test",
            [AgentCapability(name="standard_feature")]
        )
        
        # Add routing rule
        rule = RouteRule(
            rule_id="premium-rule",
            priority=10,
            target_tags=["premium"],
            strategy=RoutingStrategy.CAPABILITY_PRIORITY
        )
        router.add_rule(rule)
        
        message = RoutedMessage(
            message_id="msg-1",
            source="user",
            content="Do premium thing",
            capability_requirement=CapabilityRequirement(name="premium_feature")
        )
        
        targets = []
        async def capture_delivery(target, msg):
            targets.append(target)
        
        router.on_deliver(capture_delivery)
        result = await router.route(message)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test message TTL expiration."""
        registry, router = self.setup_router()
        
        # Create message with exhausted TTL
        message = RoutedMessage(
            message_id="msg-1",
            source="user",
            content="Hello",
            ttl=1
        )
        message.add_hop("agent-a")
        
        result = await router.route(message)
        
        assert result.success is False
        assert "TTL exceeded" in result.error


class TestLoadBalancer:
    """Tests for the LoadBalancer class."""
    
    @pytest.mark.asyncio
    async def test_round_robin(self):
        """Test round-robin selection."""
        lb = LoadBalancer()
        
        agents = [
            MagicMock(agent_id=f"agent-{i}", load_score=0.5, is_healthy=lambda: True)
            for i in range(3)
        ]
        
        # Select multiple times
        selections = []
        for _ in range(6):
            selected = await lb.select(agents, RoutingStrategy.ROUND_ROBIN, "user")
            selections.append(selected[0].agent_id if selected else None)
        
        # Should cycle through agents
        assert selections[0] == "agent-0"
        assert selections[1] == "agent-1"
        assert selections[2] == "agent-2"
        assert selections[3] == "agent-0"  # Wrap around
    
    @pytest.mark.asyncio
    async def test_sticky_session(self):
        """Test sticky session routing."""
        lb = LoadBalancer()
        
        agents = [
            MagicMock(agent_id="agent-1", load_score=0.5, is_healthy=lambda: True),
            MagicMock(agent_id="agent-2", load_score=0.5, is_healthy=lambda: True)
        ]
        
        # Set sticky session
        lb.set_sticky("user-1", "agent-2")
        
        selected = await lb.select(agents, RoutingStrategy.STICKY, "user-1")
        assert selected[0].agent_id == "agent-2"
        
        # New user should get different agent
        selected2 = await lb.select(agents, RoutingStrategy.STICKY, "user-2")
        # Without sticky set, should fall back to first
        assert selected2[0].agent_id == "agent-1"


# =============================================================================
# Agent Mesh Tests
# =============================================================================

class TestAgentMesh:
    """Tests for the AgentMesh class."""
    
    @pytest.fixture
    def setup_mesh(self):
        """Create mesh with test agents."""
        registry = AgentRegistry()
        router = AgentRouter(registry)
        mesh = AgentMesh(registry, router)
        return registry, router, mesh
    
    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        """Test pub/sub messaging."""
        registry, router, mesh = self.setup_mesh()
        
        # Register agents
        await registry.register("agent-1", "test", [AgentCapability(name="test")])
        await registry.register("agent-2", "test", [AgentCapability(name="test")])
        
        # Subscribe agent-1 to topic
        sub_id = mesh.subscribe("agent-1", "alerts")
        
        # Publish message
        delivered = await mesh.publish("system", "alerts", {"severity": "high"})
        
        # agent-1 should receive (delivery mock would be called)
        # Note: Actual delivery verification requires more setup
    
    @pytest.mark.asyncio
    async def test_group_multicast(self):
        """Test multicast to groups."""
        registry, router, mesh = self.setup_mesh()
        
        # Register agents and add to group
        await registry.register("agent-1", "test", [AgentCapability(name="test")])
        await registry.register("agent-2", "test", [AgentCapability(name="test")])
        await registry.register("agent-3", "test", [AgentCapability(name="test")])
        
        mesh.join_group("agent-1", "workers")
        mesh.join_group("agent-2", "workers")
        # agent-3 not in group
        
        # Multicast to group
        delivered = await mesh.multicast(
            "system",
            ["workers"],
            {"task": "process_data"}
        )
        
        # Should only deliver to agents in group
        assert "agent-1" in delivered or "agent-2" in delivered
        assert "agent-3" not in delivered
    
    @pytest.mark.asyncio
    async def test_scatter_gather(self):
        """Test scatter/gather operations."""
        registry, router, mesh = self.setup_mesh()
        
        # Register agents
        await registry.register("agent-1", "test", [AgentCapability(name="compute")])
        await registry.register("agent-2", "test", [AgentCapability(name="compute")])
        
        # Scatter items
        items = ["task-1", "task-2", "task-3", "task-4"]
        results = await mesh.scatter(
            "system",
            ["agent-1", "agent-2"],
            items
        )
        
        # Should have distributed tasks
        assert len(results) == 4
    
    def test_pipeline_creation(self):
        """Test pipeline creation and configuration."""
        registry = AgentRegistry()
        router = AgentRouter(registry)
        mesh = AgentMesh(registry, router)
        
        pipeline = mesh.create_pipeline("data-pipeline")
        
        stage1 = PipelineStage(
            stage_id="extract",
            agent_id="agent-1",
            capability_required="extract_data"
        )
        stage2 = PipelineStage(
            stage_id="transform",
            agent_id="agent-2",
            capability_required="transform_data"
        )
        
        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)
        
        assert len(pipeline.stages) == 2
        assert pipeline.stages[0].stage_id == "extract"


# =============================================================================
# Agent Coordinator Tests
# =============================================================================

class TestAgentCoordinator:
    """Tests for the AgentCoordinator class."""
    
    @pytest.mark.asyncio
    async def test_coordinator_lifecycle(self):
        """Test coordinator start/stop."""
        config = CoordinatorConfig(
            heartbeat_interval_seconds=1.0,
            health_check_interval_seconds=1.0
        )
        
        coordinator = AgentCoordinator(config)
        
        # Start
        await coordinator.start()
        assert coordinator._running is True
        
        # Stop
        await coordinator.stop()
        assert coordinator._running is False
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test coordinator as async context manager."""
        async with AgentCoordinator() as coordinator:
            assert coordinator._running is True
        
        assert coordinator._running is False
    
    @pytest.mark.asyncio
    async def test_agent_registration_flow(self):
        """Test full agent registration flow."""
        coordinator = AgentCoordinator()
        await coordinator.start()
        
        try:
            # Register agent
            agent = await coordinator.register_agent(
                agent_id="test-agent",
                agent_type="test",
                capabilities=[AgentCapability(name="test_capability")],
                tags={"test"}
            )
            
            assert agent.agent_id == "test-agent"
            
            # Verify session created
            session = coordinator.get_agent_session("test-agent")
            assert session is not None
            
            # Send heartbeat
            result = await coordinator.send_heartbeat("test-agent", load_score=0.3)
            assert result is True
            
            # Find agent
            found = coordinator.find_agents(capability_name="test_capability")
            assert len(found) == 1
            assert found[0].agent_id == "test-agent"
            
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_message_routing_flow(self):
        """Test full message routing flow."""
        coordinator = AgentCoordinator()
        await coordinator.start()
        
        try:
            # Register sender and receiver
            await coordinator.register_agent(
                "sender", "test", [AgentCapability(name="send")]
            )
            await coordinator.register_agent(
                "receiver", "test",
                [AgentCapability(name="receive")]
            )
            
            # Route by capability
            result = await coordinator.route_by_capability(
                source="sender",
                content="Hello!",
                capability_name="receive"
            )
            
            # Note: Without actual session processing, success depends on delivery callback
            
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_system_health(self):
        """Test health check functionality."""
        coordinator = AgentCoordinator()
        await coordinator.start()
        
        try:
            # No agents - should be healthy (no agents = 100% healthy)
            health = coordinator.get_health()
            assert health["status"] in ["healthy", "degraded"]
            
            # Add healthy agent
            await coordinator.register_agent(
                "healthy-agent", "test",
                [AgentCapability(name="test")]
            )
            
            health = coordinator.get_health()
            assert health["healthy_ratio"] == 1.0
            
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_event_subscriptions(self):
        """Test event subscription system."""
        coordinator = AgentCoordinator()
        
        events = []
        async def event_handler(event_type, data):
            events.append((event_type, data))
        
        coordinator.subscribe_to_events(event_handler)
        
        await coordinator.start()
        
        try:
            # Register agent - should trigger event
            await coordinator.register_agent(
                "event-agent", "test", [AgentCapability(name="test")]
            )
            
            # Give time for event
            await asyncio.sleep(0.1)
            
            # Should have received coordinator_started and agent_registered events
            event_types = [e[0] for e in events]
            assert "coordinator_started" in event_types
            assert "agent_registered" in event_types
            
        finally:
            await coordinator.stop()


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full system."""
    
    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """Test complete message flow through the system."""
        coordinator = AgentCoordinator()
        await coordinator.start()
        
        try:
            # Create a text processing pipeline
            await coordinator.register_agent(
                "preprocessor", "text",
                [AgentCapability(name="preprocess", version="1.0.0")],
                tags={"text-pipeline"}
            )
            await coordinator.register_agent(
                "analyzer", "text",
                [AgentCapability(name="analyze", version="2.0.0")],
                tags={"text-pipeline"}
            )
            await coordinator.register_agent(
                "formatter", "text",
                [AgentCapability(name="format", version="1.5.0")],
                tags={"text-pipeline"}
            )
            
            # Join agents to processing group
            coordinator.join_group("preprocessor", "text-pipeline")
            coordinator.join_group("analyzer", "text-pipeline")
            coordinator.join_group("formatter", "text-pipeline")
            
            # Verify all agents found
            agents = coordinator.find_agents(tag="text-pipeline")
            assert len(agents) == 3
            
            # Test broadcast to group
            results = await coordinator.broadcast(
                "system",
                {"command": "status_check"}
            )
            
            # Test pub/sub
            sub_id = coordinator.subscribe("analyzer", "new-documents")
            
            delivered = await coordinator.publish(
                "preprocessor",
                "new-documents",
                {"doc_id": "123", "text": "Hello world"}
            )
            
            # Cleanup
            coordinator.unsubscribe(sub_id)
            
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_load_balancing_with_multiple_agents(self):
        """Test load balancing across multiple agents."""
        coordinator = AgentCoordinator()
        await coordinator.start()
        
        try:
            # Register multiple agents with same capability
            for i in range(5):
                await coordinator.register_agent(
                    f"worker-{i}", "compute",
                    [AgentCapability(name="compute_task", priority=i)],
                    tags={"workers"}
                )
                # Set varying loads
                await coordinator.send_heartbeat(
                    f"worker-{i}",
                    load_score=0.1 * i
                )
            
            # Route multiple messages
            targets = []
            for i in range(10):
                result = await coordinator.route_by_capability(
                    source="client",
                    content={"task": f"job-{i}"},
                    capability_name="compute_task",
                    strategy=RoutingStrategy.LEAST_LOADED
                )
                targets.extend(result.target_agents)
            
            # worker-0 should get most messages (lowest load)
            assert targets.count("worker-0") >= 2
            
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_agent_failure_recovery(self):
        """Test system behavior when agent fails."""
        coordinator = AgentCoordinator()
        await coordinator.start()
        
        try:
            # Register redundant agents
            await coordinator.register_agent(
                "primary", "service",
                [AgentCapability(name="critical_task")]
            )
            await coordinator.register_agent(
                "backup", "service",
                [AgentCapability(name="critical_task")]
            )
            
            # Verify both available
            agents = coordinator.find_agents(capability_name="critical_task")
            assert len(agents) == 2
            
            # Simulate primary going offline
            primary = coordinator.get_agent("primary")
            primary.last_heartbeat = time.time() - 200  # Stale
            
            # Only backup should be healthy
            healthy = coordinator.find_agents(
                capability_name="critical_task",
                healthy_only=True
            )
            assert len(healthy) == 1
            assert healthy[0].agent_id == "backup"
            
        finally:
            await coordinator.stop()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
