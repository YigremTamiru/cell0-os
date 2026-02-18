#!/bin/bash
# Health check script for signal-cli-rest-api

HEALTH_ENDPOINT="http://localhost:8080/v1/health"

# Check if the API is responsive
if curl -fs "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
    exit 0
else
    # Check if signal-cli process is running
    if pgrep -f "signal-cli" > /dev/null 2>&1; then
        exit 0
    fi
    exit 1
fi
