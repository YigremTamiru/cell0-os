#!/bin/bash
# Health check script for Cell 0 OS container
# Returns 0 if healthy, 1 if unhealthy

set -e

# Configuration
HEALTH_PORT="${CELL0_PORT:-18800}"
HEALTH_HOST="${CELL0_HOST:-localhost}"
HEALTH_ENDPOINT="${CELL0_HEALTH_ENDPOINT:-/api/health}"
HEALTH_URL="http://${HEALTH_HOST}:${HEALTH_PORT}${HEALTH_ENDPOINT}"
TIMEOUT=5

# Check if the process is running
if ! pgrep -f "cell0d" > /dev/null; then
    echo "ERROR: Cell 0 daemon process not running"
    exit 1
fi

# Perform HTTP health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time "$TIMEOUT" \
    --connect-timeout "$TIMEOUT" \
    "$HEALTH_URL" 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "OK: Health check passed (HTTP $HTTP_STATUS)"
    exit 0
elif [ "$HTTP_STATUS" -eq 503 ]; then
    echo "WARNING: Service is starting up (HTTP $HTTP_STATUS)"
    exit 1
else
    echo "ERROR: Health check failed (HTTP $HTTP_STATUS)"
    exit 1
fi
