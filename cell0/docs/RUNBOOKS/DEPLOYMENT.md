# Cell 0 OS - Deployment Runbook

## Overview

This runbook provides step-by-step procedures for deploying Cell 0 OS in production environments.

**Prerequisites:**
- System administrator access
- Understanding of Cell 0 architecture
- Access to target infrastructure

---

## Deployment Types

### 1. Fresh Installation

```bash
# 1. System preparation
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# or
brew update  # macOS

# 2. Install dependencies
./setup.sh

# 3. Run diagnostics
python scripts/cell0-doctor.py --verbose

# 4. Configure environment
cp .env.example .env
# Edit .env with production values

# 5. Start services
./start.sh

# 6. Verify deployment
curl http://localhost:18800/api/health
```

### 2. Upgrade Deployment

```bash
# 1. Pre-upgrade backup
python scripts/backup.py --full --verify

# 2. Stop services gracefully
./stop.sh

# 3. Update code
git fetch origin
git checkout v1.x.x  # New version

# 4. Update dependencies
pip install -r requirements.txt --upgrade

# 5. Run migrations (if any)
python scripts/migrate.py

# 6. Start services
./start.sh

# 7. Verify upgrade
python scripts/cell0-doctor.py
```

### 3. Rollback Procedure

```bash
# 1. Stop current version
./stop.sh

# 2. Restore from backup
python scripts/restore.py backups/cell0_backup_*.tar.gz --force

# 3. Checkout previous version
git checkout v1.x.x-1  # Previous version

# 4. Restore dependencies
pip install -r requirements.txt

# 5. Start services
./start.sh

# 6. Verify rollback
python scripts/cell0-doctor.py
```

---

## Environment-Specific Procedures

### Docker Deployment

```bash
# Build image
docker build -t cell0:v1.2.0 .

# Run with compose
docker-compose -f docker-compose.yml up -d

# Verify
docker-compose ps
docker logs -f cell0
```

### Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -l app=cell0
kubectl logs -f deployment/cell0

# Port forward for testing
kubectl port-forward svc/cell0 18800:18800
```

---

## Health Verification

After deployment, verify:

```bash
# 1. Run diagnostics
python scripts/cell0-doctor.py

# 2. Check API health
curl http://localhost:18800/api/health

# 3. Test WebSocket
wscat -c ws://localhost:18801

# 4. Verify Ollama connection
curl http://localhost:11434/api/tags

# 5. Test inference
curl -X POST http://localhost:18800/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","stream":false}'
```

---

## Post-Deployment Tasks

1. **Monitor logs:**
   ```bash
   tail -f logs/cell0.log
   ```

2. **Set up monitoring:**
   - Configure Prometheus metrics endpoint
   - Set up alerts for health checks

3. **Schedule backups:**
   ```bash
   # Add to crontab
   0 2 * * * cd /opt/cell0 && python scripts/backup.py --retention 30
   ```

4. **Document changes:**
   - Update deployment records
   - Notify team of new version

---

## Emergency Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | oncall@example.com | +1-555-0100 |
| Infrastructure Lead | infra@example.com | +1-555-0101 |
| Security Team | security@example.com | +1-555-0102 |

---

*Runbook Version: 1.0*
*Last Updated: 2026-02-18*
