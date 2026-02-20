# Cell 0 OS - Multi-Agent Routing System

A comprehensive multi-agent routing system for Cell 0 OS, inspired by OpenClaw's multi-agent architecture. This system enables intelligent message routing between specialized agents based on their capabilities.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent Coordinator                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Registry  │  │   Router    │  │  Sessions   │  │      Mesh       │  │
│  │  (who/what) │  │ (where/how) │  │ (isolated)  │  │  (comms layer)  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────────┘  │
│         │                │                │                                  │
│         └────────────────┴────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
    ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
    │  Web Agent  │          │  NLP Agent  │          │ Vision Agent│
    │ (scraping)  │          │ (analysis)  │          │ (detection) │
    └─────────────┘          └─────────────┘          └─────────────┘
```

## Components

### 1. Agent Registry (`engine/agents/agent_registry.py`)

Central registry for agent management and capability tracking.

**Features:**
- Agent registration/unregistration
- Capability-based discovery
- Health monitoring via heartbeats
- Load tracking
- Tag-based grouping

**Key Classes:**
- `AgentRegistry` - Main registry
- `AgentInfo` - Agent metadata
- `AgentCapability` - Capability advertisement
- `CapabilityRequirement` - Capability matching

**Example:**
```python
from engine.agents.agent_registry import AgentRegistry, AgentCapability

registry = AgentRegistry()

# Register agent with capabilities
caps = [
    AgentCapability(name="text_processing", version="2.0.0", priority=10),
    AgentCapability(name="sentiment_analysis", version="1.5.0")
]

agent = await registry.register(
    agent_id="nlp-agent-1",
    agent_type="nlp",
    capabilities=caps,
    tags={"production", "nlp"}
)

# Find agents by capability
agents = registry.find_agents_for_requirement(
    CapabilityRequirement(name="text_processing", min_version="2.0.0")
)
```

### 2. Agent Session (`engine/agents/agent_session.py`)

Per-agent session management providing isolation.

**Features:**
- Isolated memory/context per agent
- Message inbox/outbox
- Execution sandbox
- Resource tracking
- Concurrent task limiting

**Key Classes:**
- `AgentSession` - Individual agent session
- `SessionManager` - Manages all sessions
- `SessionMessage` - Message format
- `SessionContext` - Session state

**Example:**
```python
from engine.agents.agent_session import SessionManager

sessions = SessionManager()

# Create session for agent
session = await sessions.create_session("agent-1")

# Send message to agent
msg = SessionMessage(
    message_id="msg-1",
    session_id=session.session_id,
    source="user",
    target="agent-1",
    content="Hello!"
)
await session.receive(msg)

# Get next message
message = await session.get_next_message(timeout=5.0)
```

### 3. Agent Router (`engine/agents/agent_router.py`)

Message routing based on capabilities and load.

**Features:**
- Capability-based routing
- Multiple routing strategies
- Load balancing
- Custom routing rules
- TTL-based hop limiting

**Routing Strategies:**
- `ROUND_ROBIN` - Distribute evenly
- `LEAST_LOADED` - Route to least busy agent
- `CAPABILITY_PRIORITY` - Route by capability priority
- `RANDOM` - Random selection
- `STICKY` - Sticky sessions
- `BROADCAST` - Send to all matching

**Example:**
```python
from engine.agents.agent_router import AgentRouter, RoutingStrategy

router = AgentRouter(registry)

# Route by capability
message = RoutedMessage(
    source="user",
    content="Analyze this text",
    capability_requirement=CapabilityRequirement(name="sentiment_analysis")
)

result = await router.route(message, strategy=RoutingStrategy.LEAST_LOADED)
print(f"Routed to: {result.target_agents}")
```

### 4. Agent Mesh (`engine/agents/agent_mesh.py`)

Agent-to-agent communication layer.

**Features:**
- Direct messaging
- Broadcast/multicast
- Pub/sub pattern
- Request/reply
- Scatter/gather
- Pipeline processing

**Message Patterns:**
- `DIRECT` - One-to-one
- `BROADCAST` - One-to-all
- `MULTICAST` - One-to-group
- `REQUEST_REPLY` - Request with expected response
- `PUBLISH_SUBSCRIBE` - Topic-based messaging
- `PIPELINE` - Chain processing
- `GATHER` - Collect from multiple
- `SCATTER` - Distribute to multiple

**Example:**
```python
from engine.agents.agent_mesh import AgentMesh

mesh = AgentMesh(registry, router)

# Pub/Sub
subscription_id = mesh.subscribe("agent-1", "alerts")
await mesh.publish("system", "alerts", {"severity": "high"})

# Request/Reply
response = await mesh.request(
    source="agent-1",
    target="agent-2",
    payload={"query": "status"},
    timeout_ms=5000
)

# Scatter/Gather
tasks = ["task1", "task2", "task3"]
results = await mesh.scatter("scheduler", ["worker-1", "worker-2"], tasks)
```

### 5. Agent Coordinator (`service/agent_coordinator.py`)

Central coordinator service.

**Features:**
- Unified API for all operations
- Health monitoring
- Automatic cleanup
- Event subscriptions
- Statistics/metrics

**Example:**
```python
from service.agent_coordinator import AgentCoordinator

async with AgentCoordinator() as coordinator:
    # Register agent
    await coordinator.register_agent(
        agent_id="my-agent",
        agent_type="service",
        capabilities=[AgentCapability(name="compute")]
    )
    
    # Route message
    result = await coordinator.route_by_capability(
        source="user",
        content="Process this",
        capability_name="compute"
    )
    
    # Get health
    health = coordinator.get_health()
    print(f"System status: {health['status']}")
```

## Usage Examples

### Basic Agent Setup

```python
import asyncio
from service.agent_coordinator import AgentCoordinator
from engine.agents.agent_registry import AgentCapability

async def main():
    coordinator = AgentCoordinator()
    await coordinator.start()
    
    # Register specialized agents
    await coordinator.register_agent(
        "web-scraper",
        "data-collection",
        [AgentCapability("web_scraping", version="2.0.0")]
    )
    
    await coordinator.register_agent(
        "analyzer",
        "nlp",
        [AgentCapability("sentiment_analysis", version="3.0.0")]
    )
    
    await coordinator.register_agent(
        "formatter",
        "output",
        [AgentCapability("pdf_generation", version="1.0.0")]
    )
    
    # Route work to capable agent
    result = await coordinator.route_by_capability(
        source="user",
        content={"text": "This product is amazing!"},
        capability_name="sentiment_analysis"
    )
    
    print(f"Routed to: {result.target_agents}")
    
    await coordinator.stop()

asyncio.run(main())
```

### Load Balancing

```python
# Register multiple workers
for i in range(5):
    await coordinator.register_agent(
        f"worker-{i}",
        "compute",
        [AgentCapability("batch_processing")]
    )
    # Simulate load
    await coordinator.send_heartbeat(f"worker-{i}", load_score=0.1 * i)

# Route with load balancing
result = await coordinator.route_by_capability(
    source="scheduler",
    content={"task": "heavy_job"},
    capability_name="batch_processing",
    strategy=RoutingStrategy.LEAST_LOADED
)
```

### Pub/Sub Messaging

```python
# Subscribe to topics
coordinator.subscribe("analyzer", "new-documents")
coordinator.subscribe("formatter", "analysis-complete")

# Publish message
delivered = await coordinator.publish(
    source="web-scraper",
    topic="new-documents",
    payload={"url": "https://example.com", "content": "..."}
)
```

### Group Management

```python
# Create groups
coordinator.join_group("agent-1", "data-pipeline")
coordinator.join_group("agent-2", "data-pipeline")
coordinator.join_group("agent-3", "data-pipeline")

# Multicast to group
results = await coordinator.mesh.multicast(
    source="coordinator",
    groups=["data-pipeline"],
    payload={"command": "start_batch"}
)
```

## Testing

Run the comprehensive test suite:

```bash
python -m pytest tests/test_agent_routing.py -v
```

Run the demo:

```bash
python examples/demo_agent_system.py
```

## Directory Structure

```
.
├── engine/
│   └── agents/
│       ├── __init__.py
│       ├── agent_registry.py    # Agent registration & capabilities
│       ├── agent_session.py     # Per-agent sessions
│       ├── agent_router.py      # Message routing
│       └── agent_mesh.py        # Agent communication
├── service/
│   ├── __init__.py
│   └── agent_coordinator.py     # Central coordinator
├── tests/
│   ├── __init__.py
│   └── test_agent_routing.py    # Comprehensive tests
├── examples/
│   └── demo_agent_system.py     # Usage examples
└── README.md
```

## Design Principles

1. **Capability-Based Routing**: Agents advertise capabilities, messages specify requirements
2. **Agent Isolation**: Each agent has its own session with isolated memory
3. **Load Balancing**: Multiple strategies for distributing work
4. **Health Monitoring**: Heartbeats and automatic cleanup
5. **Flexible Communication**: Support for multiple messaging patterns
6. **Dynamic Registration**: Agents can join/leave at runtime
