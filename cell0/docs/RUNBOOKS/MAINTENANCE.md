# Cell 0 OS - Maintenance Runbook

## Overview

This runbook provides procedures for routine maintenance of Cell 0 OS production deployments.

**Maintenance Windows:**
- **Weekly**: Sundays 02:00-04:00 UTC
- **Monthly**: First Sunday of month
- **Emergency**: As needed

---

## Daily Maintenance

### Health Check

```bash
#!/bin/bash
# daily-health-check.sh

# Run diagnostics
python scripts/cell0-doctor.py --json > /tmp/health.json

# Check status
STATUS=$(jq -r '.overall_status' /tmp/health.json)

if [ "$STATUS" != "pass" ]; then
    echo "ALERT: Cell 0 health check failed with status: $STATUS"
    # Send notification
    mail -s "Cell 0 Health Check Alert" oncall@example.com < /tmp/health.json
fi

# Cleanup
rm /tmp/health.json
```

### Log Rotation

```bash
#!/bin/bash
# rotate-logs.sh

LOG_DIR="logs"
MAX_SIZE="100M"
RETENTION_DAYS=30

# Find and rotate large logs
find $LOG_DIR -name "*.log" -size +$MAX_SIZE -exec gzip {} \;

# Move to archive
mkdir -p $LOG_DIR/archive
find $LOG_DIR -name "*.gz" -mtime +1 -exec mv {} $LOG_DIR/archive/ \;

# Delete old archives
find $LOG_DIR/archive -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "Log rotation complete"
```

---

## Weekly Maintenance

### Full System Check

```bash
#!/bin/bash
# weekly-maintenance.sh

echo "=== Cell 0 Weekly Maintenance ==="

# 1. System health
python scripts/cell0-doctor.py --verbose --report reports/weekly-$(date +%Y%m%d).json

# 2. Update dependencies (test environment first)
# pip list --outdated

# 3. Clean temporary files
rm -rf data/temp/*
rm -rf data/cache/*

# 4. Verify backups
python scripts/backup.py --list

# 5. Check disk space
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | tr -d '%')
if [ $DISK_USAGE -gt 80 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# 6. Restart services (if needed)
# ./stop.sh && sleep 5 && ./start.sh

echo "=== Maintenance Complete ==="
```

### Backup Verification

```bash
#!/bin/bash
# verify-backups.sh

BACKUP_DIR="backups"

# List recent backups
echo "Recent backups:"
ls -lt $BACKUP_DIR/*.tar.gz 2>/dev/null | head -5

# Verify latest backup
LATEST=$(ls -t $BACKUP_DIR/*.tar.gz 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    echo "Verifying: $LATEST"
    python scripts/restore.py "$LATEST" --verify-only
    if [ $? -eq 0 ]; then
        echo "✅ Backup verification successful"
    else
        echo "❌ Backup verification FAILED"
    fi
fi
```

---

## Monthly Maintenance

### Dependency Updates

```bash
#!/bin/bash
# monthly-updates.sh

echo "=== Cell 0 Monthly Updates ==="

# 1. Create pre-update backup
python scripts/backup.py --full --name pre-monthly-update

# 2. Check for updates
echo "Checking for dependency updates..."
pip list --outdated

# 3. Update dependencies (staged approach)
# First, update in test environment
# Then update production if tests pass

# 4. Security updates (priority)
pip install --upgrade pip
# pip-audit --fix  # if available

# 5. Update system packages (if applicable)
# sudo apt update && sudo apt upgrade -y

echo "=== Updates Complete ==="
```

### Certificate Renewal

```bash
#!/bin/bash
# renew-certificates.sh

# If using Let's Encrypt
# certbot renew --quiet

# If using custom certificates
# Check expiration dates
openssl x509 -in certs/server.crt -noout -dates

# Renew if expiring within 30 days
DAYS_UNTIL_EXPIRY=$(openssl x509 -in certs/server.crt -noout -dates | grep notAfter | cut -d= -f2 | xargs -I {} date -d "{}" +%s)
CURRENT_DATE=$(date +%s)
DAYS_LEFT=$(( ($DAYS_UNTIL_EXPIRY - $CURRENT_DATE) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "Certificate expires in $DAYS_LEFT days - renewal needed"
    # Renewal procedure here
fi
```

### Capacity Planning Review

```bash
#!/bin/bash
# capacity-review.sh

echo "=== Capacity Planning Review ==="

# 1. Resource usage trends
# CPU
echo "CPU Usage (last 30 days):"
# sar -u -f /var/log/sysstat/sa$(date +%d) | tail -10

# Memory
echo "Memory Usage:"
free -h

# Disk
echo "Disk Usage:"
df -h

# 2. Growth trends
# Compare current vs last month
echo "Data growth:"
du -sh data/

# 3. Backup storage
echo "Backup storage:"
du -sh backups/

# 4. Recommendations
echo "Recommendations:"
# Generate based on trends
```

---

## Quarterly Maintenance

### Security Audit

```bash
#!/bin/bash
# security-audit.sh

echo "=== Security Audit ==="

# 1. Check for vulnerabilities
echo "Checking dependencies for known vulnerabilities..."
# pip-audit  # if installed

# 2. Review access logs
echo "Reviewing access patterns..."
# awk '{print $1}' logs/access.log | sort | uniq -c | sort -rn | head -20

# 3. Verify file permissions
echo "Checking file permissions..."
find . -type f -perm /o+w -ls  # World-writable files

# 4. Check for secrets in logs
echo "Scanning logs for potential secrets..."
grep -rE "(password|secret|key|token)" logs/ || echo "No obvious secrets found"

# 5. Update security configurations
# Review and update firewall rules
# Review and update auth policies

echo "=== Audit Complete ==="
```

### Performance Benchmarking

```bash
#!/bin/bash
# performance-review.sh

echo "=== Performance Benchmarking ==="

# Run benchmarks
python benchmarks/latency_benchmark.py > reports/perf-$(date +%Y%m%d).json

# Compare with previous quarter
# Generate trend analysis

echo "Performance report generated"
```

---

## Cleanup Procedures

### Data Retention

```bash
#!/bin/bash
# data-cleanup.sh

# Retention policies
SESSION_RETENTION_DAYS=90
LOG_RETENTION_DAYS=365
BACKUP_RETENTION_DAYS=180

echo "Cleaning up old data..."

# Clean old sessions
find data/sessions -name "*.json" -mtime +$SESSION_RETENTION_DAYS -delete

# Clean old logs
find logs/archive -name "*.gz" -mtime +$LOG_RETENTION_DAYS -delete

# Clean old backups (keep automated retention from backup.py)
# Manual cleanup for extra safety
find backups -name "*.tar.gz" -mtime +$BACKUP_RETENTION_DAYS -delete

echo "Cleanup complete"
```

### Cache Clearing

```bash
#!/bin/bash
# clear-caches.sh

# Clear model cache (forces reload)
echo "Clearing model cache..."
rm -rf data/model_cache/*

# Clear search cache
echo "Clearing search cache..."
rm -rf data/search_cache/*

# Clear temporary files
echo "Clearing temporary files..."
rm -rf data/temp/*

echo "Caches cleared - services may need restart"
```

---

## Maintenance Schedule

| Frequency | Task | Duration | Window |
|-----------|------|----------|--------|
| Daily | Health check | 5 min | Automated |
| Daily | Log rotation | 10 min | 03:00 UTC |
| Weekly | Full system check | 30 min | Sunday 02:00 UTC |
| Weekly | Backup verification | 15 min | Sunday 03:00 UTC |
| Monthly | Dependency updates | 1 hour | First Sunday |
| Monthly | Certificate check | 15 min | First Sunday |
| Quarterly | Security audit | 2 hours | Scheduled |
| Quarterly | Performance review | 1 hour | Scheduled |

---

## Maintenance Checklist

### Before Maintenance

- [ ] Notify users of maintenance window
- [ ] Create backup
- [ ] Verify backup integrity
- [ ] Document current state

### During Maintenance

- [ ] Follow runbook procedures
- [ ] Monitor for issues
- [ ] Document any deviations

### After Maintenance

- [ ] Run health checks
- [ ] Verify all services operational
- [ ] Notify users of completion
- [ ] Update maintenance log

---

## Emergency Maintenance

For unscheduled maintenance:

1. **Assess urgency**
2. **Notify stakeholders**
3. **Execute minimal fix**
4. **Document in incident log**
5. **Schedule follow-up if needed**

---

*Runbook Version: 1.0*
*Last Updated: 2026-02-18*
