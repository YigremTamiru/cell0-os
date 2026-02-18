# Cell 0 OS Load Testing Framework

Production-grade load testing using Locust for Cell 0 OS.

## Quick Start

### Install Dependencies

```bash
pip install locust websocket-client gevent
```

### Run Basic Load Test

```bash
cd /path/to/cell0
cell0/tests/load/locustfile.py benchmark
```

Or using Locust directly:

```bash
cd cell0/tests/load
locust -f locustfile.py Cell0User --host http://localhost:18800
```

Then open http://localhost:8089 in your browser.

## Test Scenarios

### 1. Standard Load Test (Cell0User)

Simulates realistic user behavior:
- Chat requests (70% of traffic)
- Health checks (15%)
- Model listing (10%)
- WebSocket connections (5%)

```bash
locust -f locustfile.py Cell0User -u 50 -r 5 -t 5m --headless
```

### 2. Sustained Load (SustainedLoadUser)

Tests system stability over time:
```bash
locust -f locustfile.py SustainedLoadUser -u 20 -r 2 -t 1h --headless
```

### 3. Burst Load (BurstLoadUser)

Simulates traffic spikes:
```bash
locust -f locustfile.py BurstLoadUser -u 200 -r 50 -t 2m --headless
```

### 4. Stress Test (StressTestUser)

Finds breaking points:
```bash
locust -f locustfile.py StressTestUser -u 500 -r 50 -t 10m --headless
```

### 5. Benchmark (BenchmarkChatUser)

Measures consistent chat performance:
```bash
locust -f locustfile.py BenchmarkChatUser -u 10 -r 1 -t 5m --headless
```

## Configuration

Edit `Cell0Config` in `locustfile.py`:

```python
class Cell0Config:
    HOST = "http://localhost:18800"  # API endpoint
    WS_HOST = "ws://localhost:18801"  # WebSocket endpoint
    
    # Test data
    SAMPLE_MESSAGES = [...]  # Messages for chat tests
    MODEL_IDS = [...]  # Models to test
```

## Metrics

The load test tracks:
- **Response times** (avg, p95, p99)
- **Throughput** (requests/second)
- **Error rates**
- **Chat latency** (time to first response)
- **WebSocket connect time**

## Output

Summary statistics are printed at test completion:

```
============================================================
CELL 0 LOAD TEST SUMMARY
============================================================
  chat_latency_avg_ms: 523.4
  chat_latency_p95_ms: 1250.8
  chat_latency_p99_ms: 2100.3
  ws_connect_avg_ms: 45.2
  total_errors: 3
  error_types: ['ConnectionError']
============================================================
```

## Advanced Usage

### Distributed Testing

Run master:
```bash
locust -f locustfile.py --master
```

Run workers:
```bash
locust -f locustfile.py --worker --master-host=192.168.1.100
```

### Custom Test Script

```python
from locustfile import Cell0User, Cell0Config

# Custom configuration
Cell0Config.HOST = "https://api.cell0.io"

# Run test
if __name__ == "__main__":
    import subprocess
    subprocess.run([
        "locust", "-f", "locustfile.py",
        "-u", "100", "-r", "10", "-t", "10m",
        "--headless", "--csv=cell0_results"
    ])
```

### CI/CD Integration

```yaml
# .github/workflows/load-test.yml
name: Load Test
on: [push]
jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install locust websocket-client gevent
      - name: Start Cell 0
        run: docker-compose up -d
      - name: Wait for service
        run: sleep 30
      - name: Run load test
        run: |
          cd cell0/tests/load
          locust -f locustfile.py Cell0User \
            -u 20 -r 2 -t 2m --headless \
            --host http://localhost:18800
```

## Interpreting Results

### Acceptable Performance

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Chat Latency (p50) | < 500ms | < 1s | > 2s |
| Chat Latency (p95) | < 1s | < 2s | > 5s |
| Health Check | < 50ms | < 100ms | > 200ms |
| Error Rate | < 0.1% | < 1% | > 5% |
| Throughput | > 10 rps | > 5 rps | < 2 rps |

### Common Bottlenecks

1. **High Chat Latency**: Model inference slow, consider:
   - GPU acceleration
   - Model quantization
   - Caching layer

2. **WebSocket Timeouts**: Connection pool exhausted, consider:
   - Increase connection limits
   - Implement connection pooling
   - Add load balancer

3. **High Error Rate**: Service overloaded, consider:
   - Rate limiting
   - Circuit breakers
   - Auto-scaling

## Troubleshooting

### Connection Refused
- Ensure Cell 0 is running on the configured host/port
- Check firewall settings

### WebSocket Failures
- Verify WebSocket endpoint is correct
- Check for proxy/firewall blocking WebSocket

### High Memory Usage
- Reduce number of users (-u flag)
- Increase wait times between requests
- Run distributed tests across multiple machines

## License

Part of Cell 0 OS - Production Readiness Suite