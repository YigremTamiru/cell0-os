# Cell 0 OS - Scripts

This directory contains operational scripts for managing Cell 0 OS deployments.

## Scripts Overview

### cell0-doctor.py

Comprehensive diagnostic tool for health checking Cell 0 installations.

```bash
# Run all diagnostics
python scripts/cell0-doctor.py

# Quick check (no deep diagnostics)
python scripts/cell0-doctor.py --quick

# JSON output for automation
python scripts/cell0-doctor.py --json

# Attempt automatic fixes
python scripts/cell0-doctor.py --fix

# Verbose output
python scripts/cell0-doctor.py --verbose

# Save report to file
python scripts/cell0-doctor.py --report reports/health-$(date +%Y%m%d).json
```

**Exit Codes:**
- 0: All checks passed
- 1: Warnings present
- 2: Errors present
- 3: Critical failures

---

### backup.py

Automated backup system for Cell 0 data and configuration.

```bash
# Create standard backup
python scripts/backup.py

# Full backup with logs
python scripts/backup.py --full

# Configuration only
python scripts/backup.py --config-only

# Verify after backup
python scripts/backup.py --verify

# Encrypt backup
python scripts/backup.py --encrypt --password "secret"

# With retention policy
python scripts/backup.py --retention 30

# Custom output directory
python scripts/backup.py --output /mnt/backups/cell0

# Custom name
python scripts/backup.py --name pre-migration-backup

# Add description and tags
python scripts/backup.py --description "Before upgrade to v1.2" --tags "pre-upgrade,production"

# List existing backups
python scripts/backup.py --list
```

**Automated Backups:**

Add to crontab for scheduled backups:

```bash
# Daily backup at 2 AM, keep 30 days
0 2 * * * cd /opt/cell0 && python scripts/backup.py --retention 30 >> logs/backup.log 2>&1

# Weekly full backup on Sundays
0 3 * * 0 cd /opt/cell0 && python scripts/backup.py --full --retention 90 >> logs/backup.log 2>&1
```

---

### restore.py

Restore Cell 0 from backups.

```bash
# List backup contents
python scripts/restore.py backups/cell0_backup_20260101_120000.tar.gz --list

# Verify backup integrity
python scripts/restore.py backups/cell0_backup_*.tar.gz --verify-only

# Restore everything
python scripts/restore.py backups/cell0_backup_*.tar.gz --target /opt/cell0

# Restore configuration only
python scripts/restore.py backups/cell0_backup_*.tar.gz --configs-only

# Restore data only
python scripts/restore.py backups/cell0_backup_*.tar.gz --data-only

# Force overwrite existing files
python scripts/restore.py backups/cell0_backup_*.tar.gz --force

# Decrypt and restore
python scripts/restore.py backups/cell0_backup_*.tar.gz.enc --password

# Dry run (show what would be restored)
python scripts/restore.py backups/cell0_backup_*.tar.gz --dry-run
```

---

## Common Operational Workflows

### Pre-Deployment Check

```bash
# 1. Run diagnostics
python scripts/cell0-doctor.py --verbose

# 2. Create backup
python scripts/backup.py --full --verify

# 3. Verify backup
python scripts/restore.py backups/latest.tar.gz --verify-only
```

### Post-Deployment Verification

```bash
# 1. Check health
python scripts/cell0-doctor.py

# 2. Test API
curl http://localhost:18800/api/health

# 3. Check logs
tail -f logs/cell0.log
```

### Disaster Recovery

```bash
# 1. Stop services
./stop.sh

# 2. Restore from backup
python scripts/restore.py backups/latest.tar.gz --force

# 3. Start services
./start.sh

# 4. Verify
python scripts/cell0-doctor.py
```

### Scheduled Maintenance

```bash
#!/bin/bash
# maintenance.sh

echo "Starting maintenance..."

# Backup before maintenance
python scripts/backup.py --full

# Run diagnostics
python scripts/cell0-doctor.py

# Clean up old backups
python scripts/backup.py --retention 30

# Clear caches
rm -rf data/cache/*

echo "Maintenance complete"
```

---

## Integration with Monitoring

### Nagios/Icinga Check

```bash
#!/bin/bash
# check_cell0_health.sh

OUTPUT=$(python scripts/cell0-doctor.py --json)
STATUS=$(echo $OUTPUT | jq -r '.overall_status')

case $STATUS in
  pass)
    echo "OK: Cell 0 is healthy"
    exit 0
    ;;
  warn)
    echo "WARNING: Cell 0 has warnings"
    exit 1
    ;;
  error|critical)
    echo "CRITICAL: Cell 0 has errors"
    exit 2
    ;;
  *)
    echo "UNKNOWN: Unable to determine status"
    exit 3
    ;;
esac
```

### Prometheus Metrics

```python
# Add to your monitoring
from scripts.cell0_doctor import Cell0Doctor

doctor = Cell0Doctor(cell0_root="/opt/cell0")
report = doctor.run_all_checks()

# Export metrics
for check in report.checks:
    cell0_health_check{check=check.name, status=check.status.value} 1
```

---

## Troubleshooting

### Script fails with "Module not found"

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Or run with explicit python path
./venv/bin/python scripts/cell0-doctor.py
```

### Permission denied

```bash
# Make scripts executable
chmod +x scripts/*.py

# Or run with python
python scripts/cell0-doctor.py
```

### Backup fails due to disk space

```bash
# Check disk space
df -h

# Clean old backups
python scripts/backup.py --retention 7

# Use external storage
python scripts/backup.py --output /mnt/nas/cell0-backups
```

---

## Environment Variables

Scripts respect these environment variables:

- `CELL0_ROOT`: Path to Cell 0 installation (default: auto-detected)
- `CELL0_ENV`: Environment name (development/staging/production)
- `CELL0_LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

---

## Contributing

When adding new scripts:

1. Use consistent argument parsing (`argparse`)
2. Support `--verbose` flag
3. Return appropriate exit codes
4. Add documentation to this README
5. Include usage examples

---

*See also: [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)*
