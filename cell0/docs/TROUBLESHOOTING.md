# Cell 0 OS - Troubleshooting Guide

This guide provides systematic debugging procedures for resolving issues with Cell 0 OS deployments.

## Table of Contents

1. [Diagnostic Workflow](#diagnostic-workflow)
2. [System Health Checks](#system-health-checks)
3. [Common Issues](#common-issues)
4. [Log Analysis](#log-analysis)
5. [Performance Debugging](#performance-debugging)
6. [Network Issues](#network-issues)
7. [Recovery Procedures](#recovery-procedures)

---

## Diagnostic Workflow

When encountering issues, follow this systematic approach:

```
1. RUN DIAGNOSTICS
   └─> python scripts/cell0-doctor.py --verbose

2. CHECK SYSTEM HEALTH
   └─> Review CPU, Memory, Disk, Network

3. ANALYZE LOGS
   └─> tail -f logs/cell0.log

4. ISOLATE THE PROBLEM
   └─> Identify affected component

5. APPLY FIX
   └─> Follow specific troubleshooting steps

6. VERIFY RESOLUTION
   └─> Re-run diagnostics
```

---

## System Health Checks

### Quick Health Check

```bash
# Run comprehensive diagnostics
python scripts/cell0-doctor.py

# Check JSON output for automation
python scripts/cell0-doctor.py --json

# Attempt automatic fixes
python scripts/cell0-doctor.py --fix
```

### Manual Component Checks

#### 1. Python Environment

```bash
# Verify Python version
python --version  # Should be 3.9+

# Check virtual environment
which python
# Should show: /path/to/cell0/venv/bin/python

# Verify dependencies
pip list | grep -E "aiohttp|websockets|pydantic"
```

#### 2. Port Availability

```bash
# Check required ports
for port in 18800 18801 11434; do
  echo -n "Port $port: "
  nc -z localhost $port && echo "OPEN" || echo "CLOSED"
done

# Find what's using a port
lsof -i :18800
```

#### 3. Service Status

```bash
# Check if Cell 0 is running
pgrep -f cell0d

# Check Ollama
curl -s http://localhost:11434/api/tags | jq '.models | length'

# Check Signal CLI (if configured)
curl -s http://localhost:8080/v1/accounts
```

#### 4. Resource Usage

```bash
# Disk space
df -h .

# Memory
free -h  # Linux
vm_stat  # macOS

# CPU load
uptime

# Process monitoring
htop
```

---

## Common Issues

### Issue: Cell 0 Won't Start

**Symptoms:**
- Process exits immediately
- "Address already in use" error
- Import errors

**Diagnostic Steps:**

```bash
# 1. Check for existing processes
pkill -f cell0d
sleep 2

# 2. Verify port is free
lsof -i :18800 && echo "Port in use" || echo "Port free"

# 3. Test Python imports
python -c "from service.cell0d import main; print('OK')"

# 4. Check for syntax errors
python -m py_compile service/cell0d.py

# 5. Review startup logs
./start.sh 2>&1 | tee startup.log
```

**Common Fixes:**

```bash
# Port conflict - kill existing process
kill $(lsof -t -i:18800)

# Import error - reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Permission issue
chmod +x start.sh stop.sh
```

---

### Issue: Ollama Connection Failures

**Symptoms:**
- "Connection refused" errors
- Model loading timeouts
- Inference failures

**Diagnostic Steps:**

```bash
# 1. Verify Ollama is running
curl http://localhost:11434/api/tags

# 2. Check Ollama logs
# macOS:
cat ~/.ollama/logs/server.log

# Linux (systemd):
journalctl -u ollama -n 100

# Docker:
docker logs ollama

# 3. Test model availability
ollama list

# 4. Test simple inference
ollama run llama3.1 "Hello"
```

**Resolution Path:**

```
Is Ollama running?
├─ NO → Start Ollama: ollama serve
│
└─ YES → Is model available?
    ├─ NO → Pull model: ollama pull llama3.1
    │
    └─ YES → Check GPU/CPU resources
        ├─ Insufficient → Use smaller model or add resources
        └─ Sufficient → Check Ollama configuration
```

**Common Fixes:**

```bash
# Start Ollama (macOS)
ollama serve &

# Start Ollama (Linux systemd)
sudo systemctl start ollama
sudo systemctl enable ollama

# Pull default model
ollama pull qwen2.5:7b

# Check GPU support
ollama run llama3.1 --verbose  # Look for GPU info
```

---

### Issue: WebSocket Connection Problems

**Symptoms:**
- Client can't connect to ws://localhost:18801
- Frequent disconnections
- Message delivery failures

**Diagnostic Steps:**

```bash
# 1. Check WebSocket port
nc -zv localhost 18801

# 2. Test with wscat
npm install -g wscat
wscat -c ws://localhost:18801

# 3. Check gateway logs
grep -i websocket logs/cell0.log

# 4. Verify gateway is listening
lsof -i :18801
```

**Configuration Checks:**

```python
# Test WebSocket programmatically
import asyncio
import websockets

async def test():
    try:
        async with websockets.connect('ws://localhost:18801') as ws:
            print("Connected successfully")
            await ws.close()
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(test())
```

**Common Fixes:**

```bash
# Restart gateway service
pkill -f gateway_ws
python service/gateway_ws.py &

# Check firewall
sudo iptables -L | grep 18801

# Increase connection limits
ulimit -n 4096
```

---

### Issue: High Memory Usage

**Symptoms:**
- System slowing down
- OOM (Out of Memory) errors
- Swapping to disk

**Diagnostic Steps:**

```bash
# 1. Check memory usage
ps aux --sort=-%mem | head -20

# 2. Monitor over time
vmstat 1 10

# 3. Check Cell 0 specific usage
pmap $(pgrep -f cell0d) | tail -1

# 4. Identify large objects (Python)
python -c "
import sys
objs = []
for obj in gc.get_objects():
    try:
        size = sys.getsizeof(obj)
        if size > 1000000:  # > 1MB
            objs.append((type(obj).__name__, size))
    except:
        pass
for name, size in sorted(objs, key=lambda x: -x[1])[:10]:
    print(f'{name}: {size / 1024 / 1024:.2f} MB')
"
```

**Resolution Strategies:**

1. **Limit Model Concurrency:**
   ```bash
   export CELL0_MAX_CONCURRENT_MODELS=2
   ```

2. **Reduce Context Window:**
   ```bash
   export CELL0_MAX_CONTEXT_LENGTH=4096
   ```

3. **Use Smaller Models:**
   ```bash
   # Instead of 70B parameter models
   ollama pull llama3.1:8b
   ```

4. **Enable Model Unloading:**
   ```yaml
   # config/memory.yaml
   unload_inactive_models_after: 300  # seconds
   ```

---

### Issue: Slow Response Times

**Symptoms:**
- API responses taking > 10 seconds
- Timeout errors
- Degraded user experience

**Diagnostic Steps:**

```bash
# 1. Run latency benchmark
python benchmarks/latency_benchmark.py

# 2. Check GPU utilization
nvidia-smi  # NVIDIA
rocm-smi    # AMD

# 3. Profile specific request
time curl -X POST http://localhost:18800/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test","model":"llama3.1"}'

# 4. Check for blocking operations
python -m cProfile -o profile.stats service/cell0d.py
```

**Performance Tuning:**

```bash
# Enable GPU for Ollama
export OLLAMA_GPU_OVERHEAD=1

# Increase batch size
export CELL0_BATCH_SIZE=8

# Enable response streaming
export CELL0_STREAM_RESPONSES=true

# Use quantization
ollama pull qwen2.5:7b-q4_K_M  # 4-bit quantized
```

---

## Log Analysis

### Log File Locations

```
logs/
├── cell0.log           # Main application log
├── access.log          # HTTP access log
├── error.log           # Error-only log
├── audit.log           # Security audit log
└── websocket.log       # WebSocket gateway log
```

### Common Log Patterns

#### Error: `ConnectionRefusedError: [Errno 111]`
```
Cause: Ollama not running
Fix: Start Ollama service
```

#### Error: `Address already in use`
```
Cause: Port conflict
Fix: kill $(lsof -t -i:18800)
```

#### Error: `ModuleNotFoundError`
```
Cause: Missing Python dependency
Fix: pip install -r requirements.txt
```

#### Warning: `High memory usage detected`
```
Cause: Memory pressure
Fix: Reduce concurrent models or add RAM
```

### Log Analysis Tools

```bash
# Find errors in logs
grep -i "error\|exception\|failed" logs/cell0.log

# Track specific component
grep "agent_coordinator" logs/cell0.log | tail -50

# Real-time monitoring
tail -f logs/cell0.log | grep --line-buffered "ERROR"

# Analyze error frequency
grep -oP '\[\K[^\]]+' logs/cell0.log | sort | uniq -c | sort -rn
```

---

## Performance Debugging

### CPU Profiling

```bash
# Profile with py-spy
py-spy top -- python service/cell0d.py

# Generate flame graph
py-spy record -o profile.svg -- python service/cell0d.py

# Built-in cProfile
python -m cProfile -s cumulative service/cell0d.py
```

### Memory Profiling

```bash
# Memory tracking
python -m memory_profiler service/cell0d.py

# Heap analysis
pip install guppy3
python -c "from guppy import hpy; h = hpy(); print(h.heap())"

# Track memory over time
while true; do
  ps -o pid,ppid,%mem,rss,vsz,comm -p $(pgrep -f cell0d) | tail -1
  sleep 5
done
```

### Request Tracing

```python
# Add to your code for detailed tracing
import time
import functools

def trace(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__}: {elapsed:.3f}s")
        return result
    return wrapper
```

---

## Network Issues

### Connectivity Testing

```bash
# Test all endpoints
curl -s -o /dev/null -w "%{http_code}" http://localhost:18800/api/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/v1/accounts

# Check DNS resolution
nslookup api.ollama.ai

# Trace network path
traceroute api.ollama.ai
```

### Firewall Configuration

```bash
# List firewall rules (iptables)
sudo iptables -L -n | grep -E "18800|18801|11434"

# Add rules if needed
sudo iptables -A INPUT -p tcp --dport 18800 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 18801 -j ACCEPT

# Save rules (Ubuntu/Debian)
sudo iptables-save > /etc/iptables/rules.v4
```

### Proxy Configuration

```nginx
# Nginx reverse proxy example
server {
    listen 80;
    server_name cell0.example.com;
    
    location / {
        proxy_pass http://localhost:18800;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
    
    location /ws {
        proxy_pass http://localhost:18801;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Recovery Procedures

### Emergency Restart

```bash
#!/bin/bash
# emergency-restart.sh

echo "Emergency Cell 0 Restart"

# 1. Stop all processes
pkill -9 -f cell0d
pkill -9 -f gateway_ws
sleep 2

# 2. Clear temporary data
rm -rf data/temp/*
rm -rf data/cache/*

# 3. Verify ports are free
lsof -i :18800 && echo "WARNING: Port 18800 still in use"
lsof -i :18801 && echo "WARNING: Port 18801 still in use"

# 4. Start services
./start.sh

# 5. Verify startup
sleep 5
curl -s http://localhost:18800/api/health || echo "FAILED: Service not responding"
```

### Restore from Backup

```bash
# List available backups
python scripts/restore.py --list backups/cell0_backup_*.tar.gz

# Restore configuration only
python scripts/restore.py backups/cell0_backup_20260101_120000.tar.gz --configs-only

# Full restore (destructive)
python scripts/restore.py backups/cell0_backup_20260101_120000.tar.gz --force

# Decrypt and restore encrypted backup
python scripts/restore.py backups/cell0_backup_*.tar.gz.enc --password
```

### Data Recovery

```bash
# Recover from corrupted TPV store
# 1. Stop Cell 0
./stop.sh

# 2. Backup corrupted data
cp -r data/tpv data/tpv.corrupted.$(date +%s)

# 3. Attempt repair
python -c "
import json
from pathlib import Path

# Attempt to load and fix JSON files
for f in Path('data/tpv').glob('*.json'):
    try:
        data = json.loads(f.read_text())
        f.write_text(json.dumps(data, indent=2))
        print(f'Repaired: {f}')
    except json.JSONDecodeError as e:
        print(f'Corrupted: {f} - {e}')
"

# 4. Restart
./start.sh
```

---

## Getting Help

If issues persist after following this guide:

1. **Run diagnostics and save output:**
   ```bash
   python scripts/cell0-doctor.py --verbose --report diagnostic.json
   ```

2. **Collect logs:**
   ```bash
   tar -czf logs-$(date +%Y%m%d).tar.gz logs/
   ```

3. **Create issue report with:**
   - Diagnostic output
   - Relevant log excerpts
   - Steps to reproduce
   - Environment details (OS, Python version, Cell 0 version)

---

*For operational runbooks, see [RUNBOOKS/](RUNBOOKS/)*
