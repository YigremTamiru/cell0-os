# Cell 0 OS - Incident Response Runbook

## Overview

This runbook provides procedures for responding to incidents in Cell 0 OS production deployments.

**Severity Levels:**
- **P0 (Critical)**: Service down, data loss, security breach
- **P1 (High)**: Major functionality impaired
- **P2 (Medium)**: Minor functionality impaired
- **P3 (Low)**: Cosmetic issues, feature requests

---

## Incident Response Workflow

```
1. DETECT
   └─> Alert received or issue reported

2. ACKNOWLEDGE
   └─> Confirm incident and assign owner

3. ASSESS
   └─> Determine severity and impact

4. RESPOND
   └─> Follow specific runbook for incident type

5. RESOLVE
   └─> Fix issue and verify resolution

6. POST-INCIDENT
   └─> Document and review
```

---

## P0 - Service Down

### Symptoms
- HTTP API not responding
- WebSocket connections failing
- All agents offline

### Immediate Actions

```bash
# 1. Check if process is running
pgrep -f cell0d || echo "PROCESS DOWN"

# 2. Check system resources
python scripts/cell0-doctor.py --quick

# 3. Check logs for crash
 tail -n 50 logs/error.log

# 4. Attempt restart
./stop.sh && sleep 2 && ./start.sh

# 5. Verify recovery
curl -s http://localhost:18800/api/health
```

### If Restart Fails

```bash
# 1. Emergency mode - start minimal services
python service/cell0d.py --minimal

# 2. Check for port conflicts
lsof -i :18800

# 3. Clear locks and temp files
rm -f data/*.lock
rm -rf data/temp/*

# 4. Restore from backup if needed
python scripts/restore.py backups/latest.tar.gz --configs-only
```

---

## P0 - Data Corruption

### Symptoms
- TPV store errors
- Agent state corruption
- Configuration files invalid

### Recovery Procedure

```bash
# 1. Stop services
./stop.sh

# 2. Backup current (corrupted) state
cp -r data data.corrupted.$(date +%s)

# 3. Identify last known good backup
ls -t backups/*.tar.gz | head -5

# 4. Restore from backup
python scripts/restore.py backups/cell0_backup_YYYYMMDD_HHMMSS.tar.gz --verify

# 5. Start services
./start.sh

# 6. Verify data integrity
python scripts/cell0-doctor.py --verbose
```

---

## P1 - Ollama Connection Lost

### Symptoms
- Inference requests failing
- "Connection refused" errors
- Model loading timeouts

### Response

```bash
# 1. Check Ollama status
curl -s http://localhost:11434/api/tags > /dev/null && echo "UP" || echo "DOWN"

# 2. If down, restart Ollama
# macOS:
ollama serve &

# Linux:
sudo systemctl restart ollama

# Docker:
docker restart ollama

# 3. Verify models are available
ollama list

# 4. Test inference
ollama run llama3.1 "test"

# 5. Clear Cell 0 model cache
rm -rf data/model_cache/*
```

---

## P1 - High Memory Usage

### Symptoms
- OOM errors
- System becoming unresponsive
- Memory usage > 90%

### Response

```bash
# 1. Identify memory hogs
ps aux --sort=-%mem | head -10

# 2. Check Cell 0 memory usage
pmap $(pgrep -f cell0d) | tail -1

# 3. Reduce concurrent operations
# Edit config to lower limits
cat > config/emergency_limits.yaml << EOF
max_concurrent_models: 1
max_context_length: 2048
max_workers: 2
EOF

# 4. Restart with limits
./stop.sh && ./start.sh

# 5. Monitor recovery
watch -n 2 'free -h'
```

---

## P1 - WebSocket Connection Issues

### Symptoms
- Clients disconnecting frequently
- Real-time features not working
- Gateway timeout errors

### Response

```bash
# 1. Check WebSocket port
nc -zv localhost 18801

# 2. Check connection count
ss -tan | grep :18801 | wc -l

# 3. Restart gateway
pkill -f gateway_ws
sleep 2
python service/gateway_ws.py &

# 4. Verify
wscat -c ws://localhost:18801
```

---

## P2 - Slow Response Times

### Symptoms
- API latency > 5 seconds
- Timeout errors increasing
- User complaints about slowness

### Response

```bash
# 1. Check resource usage
python scripts/cell0-doctor.py

# 2. Check GPU utilization
nvidia-smi  # or rocm-smi

# 3. Review recent changes
git log --oneline -10

# 4. Enable performance logging
export CELL0_LOG_LEVEL=debug
export CELL0_PROFILE=true

# 5. Restart with profiling
./stop.sh && ./start.sh

# 6. Monitor for 5 minutes
# Review logs for bottlenecks
```

---

## Communication Template

### Initial Notification

```
Subject: [INCIDENT] Cell 0 <Severity> - <Brief Description>

Time: <TIMESTAMP>
Severity: <P0/P1/P2/P3>
Impact: <Who/what is affected>
Status: Investigating

Description:
<Detailed description of the issue>

Actions Taken:
- <Step 1>
- <Step 2>

Next Update: <TIME + 15 minutes>
```

### Resolution Notification

```
Subject: [RESOLVED] Cell 0 - <Brief Description>

Time Resolved: <TIMESTAMP>
Duration: <X minutes>

Summary:
<What happened and how it was fixed>

Root Cause (Preliminary):
<Initial assessment>

Post-Incident Review:
Scheduled for <DATE>
```

---

## Post-Incident Tasks

1. **Document the incident:**
   - Timeline of events
   - Actions taken
   - Resolution steps

2. **Update runbooks:**
   - Add new procedures if needed
   - Improve existing steps

3. **Schedule retrospective:**
   - Within 48 hours for P0/P1
   - Within 1 week for P2/P3

4. **Implement preventive measures:**
   - Add monitoring/alerting
   - Improve automation

---

## Escalation Matrix

| Severity | Response Time | Resolution Target | Escalate To |
|----------|--------------|-------------------|-------------|
| P0 | 5 minutes | 1 hour | Engineering Lead |
| P1 | 15 minutes | 4 hours | Senior Engineer |
| P2 | 1 hour | 24 hours | Team Lead |
| P3 | 4 hours | 1 week | Product Owner |

---

*Runbook Version: 1.0*
*Last Updated: 2026-02-18*
