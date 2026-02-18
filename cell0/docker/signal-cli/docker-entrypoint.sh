#!/bin/bash
# Docker entrypoint script for signal-cli-rest-api
# Customized for Cell 0 OS

set -e

# Configuration
SIGNAL_CLI_CONFIG_DIR="/home/.local/share/signal-cli"
CELL0_DATA_DIR="/data/cell0-signal"
LOG_FILE="$CELL0_DATA_DIR/signal-cli.log"

# Ensure directories exist
mkdir -p "$SIGNAL_CLI_CONFIG_DIR"
mkdir -p "$CELL0_DATA_DIR/attachments"
mkdir -p "$CELL0_DATA_DIR/cache"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting Cell 0 OS Signal CLI..."

# Check environment variables
if [ -z "$SIGNAL_CLI_PHONE_NUMBER" ]; then
    log "WARNING: SIGNAL_CLI_PHONE_NUMBER not set. You'll need to register manually."
fi

# Wait for native mode if configured
if [ "$SIGNAL_CLI_MODE" = "native" ]; then
    log "Waiting for signal-cli native mode..."
    sleep 2
fi

# Check if account is registered
if [ -n "$SIGNAL_CLI_PHONE_NUMBER" ]; then
    ACCOUNT_FILE="$SIGNAL_CLI_CONFIG_DIR/data/$SIGNAL_CLI_PHONE_NUMBER"
    if [ ! -f "$ACCOUNT_FILE" ]; then
        log "Account $SIGNAL_CLI_PHONE_NUMBER not registered yet."
        log "Please register using the API or mount existing configuration."
    else
        log "Found existing account: $SIGNAL_CLI_PHONE_NUMBER"
    fi
fi

# Start the signal-cli-rest-api
log "Starting signal-cli-rest-api..."

# Pass through to original entrypoint
exec /entrypoint.sh "$@"
