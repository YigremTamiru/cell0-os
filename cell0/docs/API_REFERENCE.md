# Cell 0 API Reference

## Base URL

```
Development: http://localhost:18800
Production:  https://your-cell0-instance.com
```

## Authentication

Currently, Cell 0 runs locally without authentication. For production deployments, add API key headers:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:18800/api/status
```

## Endpoints

### System

#### GET /api/status
Get current system status.

**Response:**
```json
{
  "version": "1.0.0-SOVEREIGN",
  "codename": "The Glass Melted",
  "uptime": 3600.5,
  "oc_status": "stable",
  "caps_epoch": 42,
  "active_model": "qwen2.5:7b",
  "mlx_ready": true,
  "agents_active": 3,
  "events_processed": 1024,
  "ollama_available": true,
  "ollama_error": null
}
```

**Fields:**
- `version`: Cell 0 version string
- `codename`: Release codename
- `uptime`: Seconds since daemon start
- `oc_status`: System status (`stable`, `warning`, `panic`)
- `caps_epoch`: Capability epoch counter
- `active_model`: Currently loaded LLM model
- `mlx_ready`: Whether MLX (Apple GPU) is available
- `agents_active`: Number of active agents
- `events_processed`: Total events processed
- `ollama_available`: Whether Ollama service is reachable
- `ollama_error`: Error message if Ollama unavailable

#### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T10:30:00Z"
}
```

#### POST /api/system/restart
Restart the Cell 0 daemon.

**Response:**
```json
{
  "success": true,
  "message": "Restarting Cell 0 daemon..."
}
```

### Chat

#### POST /api/chat
Send a chat message to the AI.

**Request:**
```json
{
  "message": "Hello, Cell 0",
  "model": "qwen2.5:7b",
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**Parameters:**
- `message` (required): User message text
- `model` (optional): Model to use (defaults to system default)
- `stream` (optional): Whether to stream response (default: false)
- `temperature` (optional): Sampling temperature 0.0-2.0 (default: 0.7)
- `max_tokens` (optional): Maximum tokens to generate (default: 2048)

**Response (non-streaming):**
```json
{
  "response": "Hello! I'm Cell 0, your sovereign computational companion.",
  "model": "qwen2.5:7b",
  "tokens_used": 42,
  "resonance_score": 0.95
}
```

**Response (streaming):**
Server-sent events with JSON data:
```
data: {"chunk": "Hello", "done": false}

data: {"chunk": "!", "done": false}

data: {"chunk": " I'm", "done": false}

data: {"chunk": " Cell 0", "done": true, "tokens_used": 42}
```

#### GET /api/chat/history
Get chat history.

**Query Parameters:**
- `limit`: Maximum messages to return (default: 50)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2026-02-11T10:00:00Z",
      "resonance_score": null
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help?",
      "timestamp": "2026-02-11T10:00:05Z",
      "resonance_score": 0.92
    }
  ],
  "total": 2
}
```

#### DELETE /api/chat/history
Clear chat history.

**Response:**
```json
{
  "success": true,
  "message": "Chat history cleared"
}
```

### Models

#### GET /api/models
List available AI models.

**Response:**
```json
{
  "models": [
    {
      "name": "qwen2.5:7b",
      "size": "4.7 GB",
      "family": "qwen",
      "parameters": "7B",
      "quantization": "Q4_K_M",
      "loaded": true
    },
    {
      "name": "qwen2.5:3b",
      "size": "1.9 GB",
      "family": "qwen",
      "parameters": "3B",
      "quantization": "Q4_K_M",
      "loaded": false
    }
  ]
}
```

#### POST /api/models/load
Load a model into memory.

**Request:**
```json
{
  "model": "qwen2.5:7b"
}
```

**Response:**
```json
{
  "success": true,
  "model": "qwen2.5:7b",
  "load_time_ms": 2500
}
```

#### POST /api/models/unload
Unload a model from memory.

**Request:**
```json
{
  "model": "qwen2.5:7b"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Model unloaded"
}
```

#### POST /api/models/pull
Download a model from Ollama registry.

**Request:**
```json
{
  "model": "llama3.2:3b"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Downloading llama3.2:3b...",
  "download_id": "dl_abc123"
}
```

### TPV (Thought-Preference-Value)

#### GET /api/tpv/profile
Get current TPV profile.

**Response:**
```json
{
  "total_entries": 150,
  "domains_covered": 12,
  "coherence_score": 0.94,
  "last_updated": "2026-02-11T09:00:00Z",
  "profile": {
    "identity": {
      "sovereign_name": "User",
      "preferred_language": "en"
    },
    "preferences": {
      "response_style": "concise",
      "technical_depth": "expert"
    }
  }
}
```

#### POST /api/tpv/update
Update TPV profile.

**Request:**
```json
{
  "section": "preferences",
  "key": "response_style",
  "value": "detailed"
}
```

**Response:**
```json
{
  "success": true,
  "coherence_score": 0.95,
  "message": "Profile updated"
}
```

#### GET /api/tpv/entries
List TPV entries.

**Query Parameters:**
- `domain`: Filter by domain (optional)
- `limit`: Maximum entries (default: 100)

**Response:**
```json
{
  "entries": [
    {
      "id": "tpv_001",
      "domain": "coding",
      "thought": "I prefer functional programming",
      "confidence": 0.9,
      "timestamp": "2026-02-11T08:00:00Z"
    }
  ],
  "total": 150
}
```

### Agents

#### GET /api/agents
List active agents.

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_001",
      "name": "Code Assistant",
      "status": "active",
      "capabilities": ["coding", "debugging"],
      "resonance_score": 0.95
    }
  ]
}
```

#### POST /api/agents/spawn
Spawn a new agent.

**Request:**
```json
{
  "name": "Research Agent",
  "capabilities": ["research", "summarization"],
  "model": "qwen2.5:7b"
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": "agent_002",
  "status": "initializing"
}
```

#### POST /api/agents/{id}/send
Send message to an agent.

**Request:**
```json
{
  "message": "Research quantum computing"
}
```

**Response:**
```json
{
  "response": "I'll research quantum computing for you...",
  "task_id": "task_001"
}
```

#### DELETE /api/agents/{id}
Terminate an agent.

**Response:**
```json
{
  "success": true,
  "message": "Agent terminated"
}
```

### Inference

#### POST /api/inference/generate
Direct text generation (advanced).

**Request:**
```json
{
  "prompt": "Explain quantum computing",
  "model": "qwen2.5:7b",
  "system_prompt": "You are a helpful assistant.",
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 1024,
  "stream": false
}
```

**Response:**
```json
{
  "text": "Quantum computing is a form of computation...",
  "tokens_generated": 150,
  "tokens_per_second": 45.5,
  "model": "qwen2.5:7b"
}
```

#### POST /api/inference/embeddings
Generate text embeddings.

**Request:**
```json
{
  "text": "The quick brown fox",
  "model": "nomic-embed-text"
}
```

**Response:**
```json
{
  "embedding": [0.023, -0.045, 0.123, ...],
  "dimensions": 768
}
```

## WebSocket API

Connect to `ws://localhost:18800/ws` for real-time updates.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:18800/ws');

ws.onopen = () => {
  console.log('Connected to Cell 0');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Message Types

#### Client → Server

**Subscribe to events:**
```json
{
  "type": "subscribe",
  "channels": ["system", "chat", "agents"]
}
```

**Send chat message:**
```json
{
  "type": "chat",
  "message": "Hello!",
  "model": "qwen2.5:7b"
}
```

**Ping:**
```json
{
  "type": "ping",
  "timestamp": 1707657600000
}
```

#### Server → Client

**System status update:**
```json
{
  "type": "system.status",
  "data": {
    "uptime": 3600,
    "agents_active": 3,
    "oc_status": "stable"
  },
  "timestamp": "2026-02-11T10:30:00Z"
}
```

**Chat response (streaming):**
```json
{
  "type": "chat.chunk",
  "data": {
    "content": "Hello",
    "message_id": "msg_001",
    "done": false
  }
}
```

**Agent event:**
```json
{
  "type": "agent.event",
  "data": {
    "agent_id": "agent_001",
    "event": "task_complete",
    "result": "Research completed"
  }
}
```

**Error:**
```json
{
  "type": "error",
  "data": {
    "code": "MODEL_NOT_FOUND",
    "message": "Model 'unknown' not found"
  }
}
```

### WebSocket Example

```python
import asyncio
import websockets
import json

async def cell0_client():
    uri = "ws://localhost:18800/ws"
    
    async with websockets.connect(uri) as ws:
        # Subscribe to channels
        await ws.send(json.dumps({
            "type": "subscribe",
            "channels": ["system", "chat"]
        }))
        
        # Send chat message
        await ws.send(json.dumps({
            "type": "chat",
            "message": "Hello, Cell 0!"
        }))
        
        # Receive responses
        async for message in ws:
            data = json.loads(message)
            print(f"Received: {data}")
            
            if data.get("type") == "chat.chunk" and data["data"].get("done"):
                break

asyncio.run(cell0_client())
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `MODEL_NOT_FOUND` | 404 | Model not available |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `OLLAMA_ERROR` | 503 | Ollama service unavailable |
| `KERNEL_PANIC` | 503 | Kernel not responding |

## Rate Limiting

Default limits (configurable):
- 100 requests per minute per IP
- 10 concurrent WebSocket connections per IP
- 1000 tokens per minute for generation

Headers in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1707657660
```

## SDK Examples

### Python

```python
import httpx

class Cell0Client:
    def __init__(self, base_url="http://localhost:18800"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def chat(self, message, model=None):
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json={"message": message, "model": model}
        )
        return response.json()
    
    async def status(self):
        response = await self.client.get(
            f"{self.base_url}/api/status"
        )
        return response.json()

# Usage
client = Cell0Client()
status = await client.status()
response = await client.chat("Hello!")
```

### JavaScript

```javascript
class Cell0Client {
  constructor(baseUrl = 'http://localhost:18800') {
    this.baseUrl = baseUrl;
  }
  
  async status() {
    const response = await fetch(`${this.baseUrl}/api/status`);
    return response.json();
  }
  
  async chat(message, model) {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, model })
    });
    return response.json();
  }
}

// Usage
const client = new Cell0Client();
const status = await client.status();
const response = await client.chat('Hello!');
```

### curl

```bash
# Check status
curl http://localhost:18800/api/status

# Send chat message
curl -X POST http://localhost:18800/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# List models
curl http://localhost:18800/api/models

# Load model
curl -X POST http://localhost:18800/api/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:7b"}'
```
