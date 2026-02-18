# Cell 0 OS - Monitoring & Observability Stack

Production-ready monitoring and observability for Cell 0 OS.

## Quick Start

### Start the Monitoring Stack

```bash
cd cell0/monitoring

# Start Prometheus + Grafana + Loki
docker-compose -f docker-compose.monitoring.yml up -d

# Access the services:
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# AlertManager: http://localhost:9093
```

### Configure Cell 0 for Monitoring

```python
from engine.monitoring import configure_logging, get_logger
from service.monitoring_service import MonitoringService

# Configure structured logging
configure_logging(
    level="INFO",
    log_dir="/var/log/cell0",
    json_format=True,
)

# Start monitoring HTTP service
service = MonitoringService(host="0.0.0.0", port=18800)
await service.start()
```

## Components

### 1. Prometheus Metrics (`engine/monitoring/metrics.py`)

Comprehensive metrics collection:

**Agent Metrics:**
- `cell0_agents_active` - Number of active agents
- `cell0_agents_total` - Total agents created
- `cell0_agent_messages_total` - Messages processed by agents

**Inference Metrics:**
- `cell0_inference_requests_total` - Total inference requests
- `cell0_inference_latency_seconds` - Inference latency histogram
- `cell0_inference_tokens_total` - Tokens processed
- `cell0_inference_queue_size` - Current queue size

**API Metrics:**
- `cell0_api_requests_total` - Total API requests
- `cell0_api_request_duration_seconds` - Request duration

**WebSocket Metrics:**
- `cell0_websocket_connections_active` - Active connections
- `cell0_websocket_messages_total` - Messages sent/received

**Integration Metrics:**
- `cell0_ollama_requests_total` - Ollama API calls
- `cell0_signal_messages_total` - Signal messages

### 2. Structured Logging (`engine/monitoring/logging_config.py`)

JSON-formatted logs with trace correlation:

```python
from engine.monitoring import get_logger, trace_context

logger = get_logger("my_component")

# With trace context
with trace_context():
    logger.info("Processing request", extra={"request_id": "123"})

# Output:
# {
#   "timestamp": "2026-02-18T00:00:00.000Z",
#   "level": "INFO",
#   "logger": "cell0.my_component",
#   "message": "Processing request",
#   "trace_id": "abc123",
#   "request_id": "123",
#   "cell0": {"version": "1.1.5"}
# }
```

**Log Files:**
- `/var/log/cell0/cell0.json` - Main application logs
- `/var/log/cell0/cell0-error.json` - Error logs only
- `/var/log/cell0/cell0-audit.json` - Security audit logs

**Rotation:**
- 100MB per file
- 10 backup files retained

### 3. Health Checks (`engine/monitoring/health_checks.py`)

Kubernetes-ready health probes:

```python
from engine.monitoring import health_registry, setup_health_routes_aiohttp

# Run all health checks
report = await health_registry.run_all_checks()

# Setup HTTP routes
setup_health_routes_aiohttp(app)
```

**Endpoints:**
- `GET /api/health` - Basic health (fast)
- `GET /api/health/deep` - Comprehensive health check
- `GET /healthz` - K8s readiness probe
- `GET /livez` - K8s liveness probe
- `GET /readyz` - K8s readiness (alternative)

**Checks:**
- Ollama connectivity
- Signal status
- Disk space
- Memory usage
- CPU usage
- TPV store accessibility
- WebSocket gateway status

### 4. Grafana Dashboard

Pre-configured dashboard (`grafana/dashboards/cell0-overview.json`):

- System Overview (status, uptime, agents, connections)
- Inference Metrics (request rate, latency percentiles)
- API Performance (latency, status codes)
- Live Logs (Loki integration)

### 5. Alerting Rules

Prometheus alerts (`alerting/cell0-alerts.yml`):

**Critical:**
- Cell0Down - Instance is down
- OllamaUnavailable - Ollama service down
- HighErrorRate - >10% error rate
- DiskSpaceCritical - >95% disk usage
- MemoryCritical - >95% memory usage

**Warning:**
- HighInferenceLatency - p99 > 10s
- HighAPILatency - p99 > 2s
- DiskSpaceWarning - >80% disk usage
- WebSocketConnectionIssues

## Configuration

### Environment Variables

```bash
# Logging
export CELL0_LOG_LEVEL=INFO
export CELL0_LOG_DIR=/var/log/cell0
export CELL0_LOG_FORMAT=json
export CELL0_LOG_MAX_BYTES=104857600
export CELL0_LOG_BACKUP_COUNT=10

# Monitoring
export CELL0_AUTO_INIT_LOGGING=true

# Grafana
export GRAFANA_ADMIN_USER=admin
export GRAFANA_ADMIN_PASSWORD=changeme
export GRAFANA_ROOT_URL=http://localhost:3000

# AlertManager
export ALERTMANAGER_EXTERNAL_URL=http://localhost:9093
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export PAGERDUTY_SERVICE_KEY=...
export ALERT_EMAIL=admin@example.com
```

### Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "prometheus-client>=0.19.0",
    "python-json-logger>=2.0.7",
    "psutil>=5.9.0",  # For system metrics
]
```

## Integration Examples

### With WebSocket Gateway

```python
from service.gateway_ws import WebSocketGateway
from engine.monitoring import (
    record_websocket_connection,
    record_websocket_disconnection,
    record_websocket_message,
)

class InstrumentedGateway(WebSocketGateway):
    async def _handle_connection(self, websocket, path):
        record_websocket_connection("gateway", established=True)
        try:
            await super()._handle_connection(websocket, path)
        finally:
            record_websocket_disconnection("gateway")
    
    async def _send_message(self, conn, message):
        record_websocket_message("gateway", "sent", len(str(message)))
        await super()._send_message(conn, message)
```

### With Agent Coordinator

```python
from service.agent_coordinator import AgentCoordinator
from engine.monitoring import update_agent_count, timer, INFERENCE_LATENCY

class InstrumentedCoordinator(AgentCoordinator):
    async def register_agent(self, *args, **kwargs):
        result = await super().register_agent(*args, **kwargs)
        # Update active agent count
        agents = self.registry.get_all_agents()
        update_agent_count("all", len(agents))
        return result
    
    async def route_by_capability(self, *args, **kwargs):
        with timer(INFERENCE_LATENCY, {"model": "default"}):
            return await super().route_by_capability(*args, **kwargs)
```

### Custom Health Checks

```python
from engine.monitoring import health_registry, ComponentHealth, HealthStatus

async def check_my_service() -> ComponentHealth:
    start = time.time()
    try:
        # Check service health
        healthy = await ping_my_service()
        latency = (time.time() - start) * 1000
        
        if healthy:
            return ComponentHealth(
                name="my_service",
                status=HealthStatus.HEALTHY,
                message="Service responding",
                latency_ms=latency,
            )
        else:
            return ComponentHealth(
                name="my_service",
                status=HealthStatus.UNHEALTHY,
                message="Service not responding",
                latency_ms=latency,
            )
    except Exception as e:
        return ComponentHealth(
            name="my_service",
            status=HealthStatus.UNHEALTHY,
            message=f"Check failed: {e}",
        )

# Register the check
health_registry.register("my_service", check_my_service)
```

## Metrics Export

The metrics endpoint returns Prometheus format:

```
# HELP cell0_agents_active Number of currently active agents
# TYPE cell0_agents_active gauge
cell0_agents_active{agent_type="all"} 5

# HELP cell0_inference_requests_total Total inference requests
# TYPE cell0_inference_requests_total counter
cell0_inference_requests_total{model="qwen2.5:7b",status="success"} 42
```

## Troubleshooting

### No metrics appearing in Prometheus

1. Check Cell 0 is running: `curl http://localhost:18800/api/health`
2. Verify metrics endpoint: `curl http://localhost:18800/metrics`
3. Check Prometheus targets: http://localhost:9090/targets

### Logs not appearing in Loki

1. Check Promtail is running: `docker ps | grep promtail`
2. Verify log file exists: `ls -la /var/log/cell0/`
3. Check Promtail config: `docker logs cell0-promtail`

### Health checks failing

1. Test individual checks:
   ```python
   from engine.monitoring import check_ollama_health
   result = await check_ollama_health()
   print(result.to_dict())
   ```

2. Check Ollama is running: `curl http://localhost:11434/api/tags`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Cell 0 OS                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Agents    │  │   Inference  │  │    WebSocket     │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                   │              │
│         └────────────────┼───────────────────┘              │
│                          │                                  │
│              ┌───────────┴───────────┐                      │
│              │   Metrics Collection  │                      │
│              └───────────┬───────────┘                      │
│                          │                                  │
│  ┌───────────────────────┼───────────────────────┐          │
│  │                       │                       │          │
│  ▼                       ▼                       ▼          │
│ ┌─────────┐        ┌──────────┐          ┌──────────┐      │
│ │Prometheus│◄──────│ /metrics │          │  Health  │      │
│ └────┬────┘        └──────────┘          └────┬─────┘      │
│      │                                         │            │
│      │         ┌──────────────┐               │            │
│      └────────►│   Grafana    │◄──────────────┘            │
│                └──────────────┘                            │
│                      ▲                                     │
│                      │                                     │
│                ┌──────────┐                                │
│                │  Loki    │◄── JSON Logs                  │
│                └──────────┘                                │
└─────────────────────────────────────────────────────────────┘
```
