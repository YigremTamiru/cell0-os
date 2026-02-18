"""
Cell 0 OS - Multi-Agent Routing System

A comprehensive multi-agent routing system with:
- Agent registry with capabilities
- Message routing based on agent capabilities
- Agent isolation (separate sessions)
- Agent-to-agent communication
- Load balancing across agents
- Agent health checking
- Dynamic agent registration
"""

from engine.agents.agent_registry import (
    AgentRegistry,
    AgentInfo,
    AgentCapability,
    CapabilityRequirement,
    AgentStatus
)

from engine.agents.agent_session import (
    AgentSession,
    SessionManager,
    SessionMessage,
    SessionContext,
    SessionState,
    get_current_agent_id
)

from engine.agents.agent_router import (
    AgentRouter,
    RoutedMessage,
    RoutingStrategy,
    RoutingResult,
    RouteRule,
    LoadBalancer
)

from engine.agents.agent_mesh import (
    AgentMesh,
    MeshMessage,
    MessagePattern,
    Pipeline,
    PipelineStage,
    Subscription
)

__all__ = [
    # Registry
    "AgentRegistry",
    "AgentInfo",
    "AgentCapability",
    "CapabilityRequirement",
    "AgentStatus",
    # Session
    "AgentSession",
    "SessionManager",
    "SessionMessage",
    "SessionContext",
    "SessionState",
    "get_current_agent_id",
    # Router
    "AgentRouter",
    "RoutedMessage",
    "RoutingStrategy",
    "RoutingResult",
    "RouteRule",
    "LoadBalancer",
    # Mesh
    "AgentMesh",
    "MeshMessage",
    "MessagePattern",
    "Pipeline",
    "PipelineStage",
    "Subscription",
]
