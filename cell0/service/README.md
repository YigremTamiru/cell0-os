# Cell 0 OS WebSocket Gateway

Production-ready WebSocket gateway for Cell 0 OS providing real-time control plane capabilities.

## Features

- **WebSocket Server** on port 18801 (separate from HTTP API on 18800)
- **Session Management** with presence tracking
- **Event Streaming** for agent events, system events, and channel events
- **JSON-RPC 2.0 Protocol** for commands
- **Token-based Authentication** with permission system
- **Multi-agent Routing** support
- **Message Routing** between agents and channels

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cell 0 OS Gateway                         │
├─────────────────────────────────────────────────────────────┤
│  WebSocket Server (Port 18801)                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  JSON-RPC Protocol Handler                            │  │
│  │  ├─ Method Registry                                   │  │
│  │  ├─ Request/Response Handling                         │  │
│  │  └─ Batch Request Support                             │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Authentication Manager                               │  │
│  │  ├─ Token Generation                                  │  │
│  │  ├─ Token Validation                                  │  │
│  │  └─ Permission System                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Presence Manager                                     │  │
│  │  ├─ Entity Registration                               │  │
│  │  ├─ Status Tracking                                   │  │
│  │  ├─ Session Management                                │  │
│  │  └─ Subscriptions                                     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Event Router                                         │  │
│  │  ├─ Channel Pub/Sub                                   │  │
│  │  ├─ Agent Routing                                     │  │
│  │  └─ Event Filtering                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Start the Gateway

```bash
python -m cell0.service.gateway_ws --host 0.0.0.0 --port 18801
```

### Connect and Authenticate

```javascript
const ws = new WebSocket('ws://localhost:18801');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    jsonrpc: '2.0',
    method: 'auth.authenticate',
    params: {
      token: 'your_token_here',
      entity_id: 'agent_001',
      entity_type: 'agent',
      capabilities: ['chat', 'task_execution']
    },
    id: '1'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

## JSON-RPC Methods

### Built-in Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `rpc.ping` | No | Ping the server |
| `rpc.echo` | No | Echo a message back |
| `rpc.listMethods` | No | List available methods |
| `rpc.getServerInfo` | No | Get server information |

### Authentication Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `auth.authenticate` | No | Authenticate with token |
| `auth.generateToken` | Yes | Generate new token |

### Session Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `session.getInfo` | Yes | Get current session info |

### Presence Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `presence.update` | Yes | Update presence status |
| `presence.get` | No | Get presence info |

### Channel Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `channel.subscribe` | Yes | Subscribe to channel |
| `channel.unsubscribe` | Yes | Unsubscribe from channel |
| `channel.publish` | Yes | Publish to channel |

### Agent Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `agent.send` | Yes | Send message to agent |
| `agent.list` | No | List online agents |

### Gateway Methods

| Method | Auth Required | Description |
|--------|---------------|-------------|
| `gateway.getStats` | Yes | Get gateway statistics |

## Protocol Examples

### Authentication

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "auth.authenticate",
  "params": {
    "token": "cell0_abc123_1234567890",
    "entity_id": "agent_001",
    "entity_type": "agent",
    "capabilities": ["chat", "task_execution"]
  },
  "id": "1"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "session_id": "sess_def456",
    "entity_id": "agent_001",
    "entity_type": "agent"
  },
  "id": "1"
}
```

### Update Presence

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "presence.update",
  "params": {
    "status": "busy",
    "activity": "processing_task"
  },
  "id": "2"
}
```

### Subscribe to Channel

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "channel.subscribe",
  "params": {
    "channel": "events"
  },
  "id": "3"
}
```

### Publish to Channel

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "channel.publish",
  "params": {
    "channel": "events",
    "message": {
      "type": "task_completed",
      "task_id": "task_123"
    }
  },
  "id": "4"
}
```

## Events

The gateway sends several types of events:

### Connection Welcome
```json
{
  "jsonrpc": "2.0",
  "method": "connection.welcome",
  "params": {
    "connection_id": "conn_abc123",
    "server_version": "cell0-1.0.0",
    "capabilities": ["jsonrpc_2.0", "event_streaming", "presence"]
  }
}
```

### Heartbeat
```json
{
  "jsonrpc": "2.0",
  "method": "heartbeat",
  "params": {
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

### Channel Message
```json
{
  "jsonrpc": "2.0",
  "method": "channel.message",
  "params": {
    "channel": "events",
    "message": {...},
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

## Running Tests

```bash
cd cell0
pytest tests/test_gateway_ws.py -v
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELL0_GATEWAY_HOST` | `0.0.0.0` | WebSocket bind host |
| `CELL0_GATEWAY_PORT` | `18801` | WebSocket port |
| `CELL0_HEARTBEAT_INTERVAL` | `30` | Heartbeat interval (seconds) |
| `CELL0_HEARTBEAT_TIMEOUT` | `60` | Connection timeout (seconds) |

### Programmatic Configuration

```python
from cell0.service.gateway_ws import WebSocketGateway

gateway = WebSocketGateway(
    host="0.0.0.0",
    port=18801,
    heartbeat_interval=30.0,
    heartbeat_timeout=60.0,
    max_message_size=10*1024*1024,
    enable_compression=True
)

await gateway.start()
```

## Integration with Cell 0 OS

The gateway integrates with other Cell 0 OS components:

- **Event Bus**: Forwards events to connected clients
- **Presence System**: Tracks agent/user online status
- **Authentication**: Validates tokens and manages permissions
- **Routing**: Routes messages between agents and channels

## License

Part of Cell 0 OS - The Internal Geometry Stack
