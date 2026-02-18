#!/bin/bash
# Cell 0 OS - Post-Installation Configuration Script
# Configures Cell 0 OS after initial installation

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CELL0_VERSION="1.2.0"
INSTALL_DIR="${CELL0_HOME:-$HOME/.cell0}"
CONFIG_DIR="${CELL0_CONFIG_DIR:-$HOME/.config/cell0}"
DATA_DIR="${CELL0_DATA_DIR:-$HOME/.cell0/data}"
LOGS_DIR="${CELL0_LOGS_DIR:-$HOME/.cell0/logs}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================================
# Logging
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# ============================================================================
# Utility Functions
# ============================================================================
ensure_dir() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        log_success "Created directory: $dir"
    fi
}

backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$file" "$backup"
        log_info "Backed up to: $backup"
    fi
}

prompt_input() {
    local prompt="$1"
    local default="${2:-}"
    local secret="${3:-false}"
    local response
    
    if [ "$secret" = true ]; then
        read -rsp "$prompt: " response
        echo
    else
        if [ -n "$default" ]; then
            read -rp "$prompt [$default]: " response
            response=${response:-$default}
        else
            read -rp "$prompt: " response
        fi
    fi
    
    echo "$response"
}

# ============================================================================
# Step 1: Environment Configuration
# ============================================================================
setup_environment() {
    log_step "Setting up environment configuration"
    
    ensure_dir "$CONFIG_DIR"
    ensure_dir "$DATA_DIR"
    ensure_dir "$LOGS_DIR"
    
    # Create main config file
    local config_file="$CONFIG_DIR/cell0.conf"
    backup_file "$config_file"
    
    log_info "Creating main configuration..."
    
    cat > "$config_file" << EOF
# Cell 0 OS Configuration
# Version: $CELL0_VERSION
# Generated: $(date -Iseconds)

[core]
version = $CELL0_VERSION
install_dir = $INSTALL_DIR
data_dir = $DATA_DIR
logs_dir = $LOGS_DIR
config_dir = $CONFIG_DIR
environment = ${CELL0_ENV:-development}

[logging]
level = ${CELL0_LOG_LEVEL:-info}
format = json
max_size_mb = 100
max_files = 10

[server]
host = ${CELL0_HOST:-127.0.0.1}
port = ${CELL0_PORT:-8080}
workers = ${CELL0_WORKERS:-1}
timeout = 30

[security]
secret_key = $(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | xxd -p | tr -d '\n' | head -c 64)
jwt_algorithm = HS256
access_token_expire_minutes = 30
refresh_token_expire_days = 7

[database]
path = $DATA_DIR/cell0.db
backup_enabled = true
backup_interval_hours = 24
backup_retention_days = 7
EOF

    log_success "Configuration created: $config_file"
}

# ============================================================================
# Step 2: AI Provider Configuration
# ============================================================================
setup_ai_providers() {
    log_step "Configuring AI providers"
    
    local providers_file="$CONFIG_DIR/providers.conf"
    backup_file "$providers_file"
    
    log_info "Setting up AI provider configuration..."
    
    cat > "$providers_file" << 'EOF'
# AI Provider Configuration
# Add your API keys here (keep this file secure!)

[providers.openai]
enabled = false
api_key = 
base_url = https://api.openai.com/v1
model = gpt-4
temperature = 0.7
max_tokens = 4096

[providers.anthropic]
enabled = false
api_key = 
base_url = https://api.anthropic.com
model = claude-3-opus-20240229
temperature = 0.7
max_tokens = 4096

[providers.ollama]
enabled = false
base_url = http://localhost:11434
model = llama2
timeout = 300

[providers.local]
enabled = true
path = ${CELL0_HOME}/models
model = default.gguf
context_size = 4096
threads = 4
gpu_layers = 0
EOF

    # Set restrictive permissions
    chmod 600 "$providers_file"
    log_success "Provider configuration created: $providers_file"
    log_warn "Remember to update API keys in $providers_file"
}

# ============================================================================
# Step 3: Shell Integration
# ============================================================================
setup_shell_integration() {
    log_step "Setting up shell integration"
    
    local shell_rc=""
    local current_shell="${SHELL##*/}"
    
    case "$current_shell" in
        bash)
            shell_rc="$HOME/.bashrc"
            ;;
        zsh)
            shell_rc="$HOME/.zshrc"
            ;;
        fish)
            shell_rc="$HOME/.config/fish/config.fish"
            ;;
        *)
            shell_rc="$HOME/.bashrc"
            log_warn "Unknown shell, defaulting to bash"
            ;;
    esac
    
    log_info "Detected shell: $current_shell"
    log_info "Shell config: $shell_rc"
    
    # Check if already configured
    if [ -f "$shell_rc" ] && grep -q "CELL0_HOME" "$shell_rc" 2>/dev/null; then
        log_warn "Cell 0 already configured in $shell_rc"
        return 0
    fi
    
    # Add to shell rc
    local cell0_block="
# Cell 0 OS Configuration
export CELL0_HOME=\"$INSTALL_DIR\"
export CELL0_CONFIG_DIR=\"$CONFIG_DIR\"
export CELL0_DATA_DIR=\"$DATA_DIR\"
export CELL0_LOGS_DIR=\"$LOGS_DIR\"
export PATH=\"\$CELL0_HOME/bin:\$PATH\"

# Cell 0 aliases
alias c0='cell0ctl'
alias c0s='cell0ctl status'
alias c0l='cell0ctl logs'
alias c0c='cell0ctl config'
# End Cell 0 OS Configuration
"

    if [ "$current_shell" = "fish" ]; then
        ensure_dir "$HOME/.config/fish"
        echo "$cell0_block" | sed 's/export/set -x/g' >> "$shell_rc"
    else
        echo "$cell0_block" >> "$shell_rc"
    fi
    
    log_success "Shell integration added to $shell_rc"
    log_info "Run 'source $shell_rc' to apply changes"
}

# ============================================================================
# Step 4: Service Configuration
# ============================================================================
setup_services() {
    log_step "Setting up system services"
    
    local os=$(uname -s)
    
    case "$os" in
        Darwin)
            setup_launchd_service
            ;;
        Linux)
            setup_systemd_service
            ;;
        *)
            log_warn "Unsupported OS for service setup: $os"
            ;;
    esac
}

setup_systemd_service() {
    if ! command -v systemctl &> /dev/null; then
        log_warn "systemd not found, skipping service setup"
        return 0
    fi
    
    local service_file="$HOME/.config/systemd/user/cell0d.service"
    ensure_dir "$HOME/.config/systemd/user"
    
    cat > "$service_file" << EOF
[Unit]
Description=Cell 0 OS Daemon
Documentation=https://docs.cell0.io
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment=CELL0_HOME=$INSTALL_DIR
Environment=CELL0_CONFIG_DIR=$CONFIG_DIR
Environment=CELL0_DATA_DIR=$DATA_DIR
Environment=CELL0_LOGS_DIR=$LOGS_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m cell0.cell0d
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

    log_success "systemd service created: $service_file"
    log_info "Run 'systemctl --user enable cell0d' to enable"
}

setup_launchd_service() {
    local plist_file="$HOME/Library/LaunchAgents/io.cell0.cell0d.plist"
    ensure_dir "$HOME/Library/LaunchAgents"
    
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.cell0.cell0d</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/venv/bin/python</string>
        <string>-m</string>
        <string>cell0.cell0d</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>CELL0_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>CELL0_CONFIG_DIR</key>
        <string>$CONFIG_DIR</string>
        <key>CELL0_DATA_DIR</key>
        <string>$DATA_DIR</string>
        <key>CELL0_LOGS_DIR</key>
        <string>$LOGS_DIR</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOGS_DIR/cell0d.log</string>
    <key>StandardErrorPath</key>
    <string>$LOGS_DIR/cell0d.error.log</string>
</dict>
</plist>
EOF

    log_success "launchd service created: $plist_file"
    log_info "Run 'launchctl load $plist_file' to load"
}

# ============================================================================
# Step 5: Monitoring Setup
# ============================================================================
setup_monitoring() {
    log_step "Setting up monitoring"
    
    local monitoring_dir="$CONFIG_DIR/monitoring"
    ensure_dir "$monitoring_dir"
    
    # Prometheus config
    cat > "$monitoring_dir/prometheus.yml" << EOF
# Prometheus configuration for Cell 0 OS
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'cell0'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: /metrics
    scrape_interval: 10s
EOF

    # Health check script
    cat > "$INSTALL_DIR/bin/cell0-healthcheck" << 'EOF'
#!/bin/bash
# Cell 0 OS Health Check

CELL0_URL="${CELL0_URL:-http://localhost:8080}"
TIMEOUT=5

if curl -fsS --max-time $TIMEOUT "${CELL0_URL}/health" > /dev/null 2>&1; then
    echo "OK: Cell 0 is healthy"
    exit 0
else
    echo "ERROR: Cell 0 is not responding"
    exit 1
fi
EOF
    chmod +x "$INSTALL_DIR/bin/cell0-healthcheck"
    
    log_success "Monitoring configuration created"
}

# ============================================================================
# Step 6: Backup Configuration
# ============================================================================
setup_backup() {
    log_step "Setting up backup configuration"
    
    local backup_dir="$DATA_DIR/backups"
    ensure_dir "$backup_dir"
    
    # Backup script
    cat > "$INSTALL_DIR/bin/cell0-backup" << EOF
#!/bin/bash
# Cell 0 OS Backup Script

BACKUP_DIR="$backup_dir"
DATA_DIR="$DATA_DIR"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/cell0_backup_\$TIMESTAMP.tar.gz"

# Create backup
tar -czf "\$BACKUP_FILE" -C "\$DATA_DIR" . 2>/dev/null

if [ \$? -eq 0 ]; then
    echo "Backup created: \$BACKUP_FILE"
    
    # Clean old backups (keep 7 days)
    find "\$BACKUP_DIR" -name "cell0_backup_*.tar.gz" -mtime +7 -delete
    
    exit 0
else
    echo "Backup failed"
    exit 1
fi
EOF
    chmod +x "$INSTALL_DIR/bin/cell0-backup"
    
    log_success "Backup script created: $INSTALL_DIR/bin/cell0-backup"
}

# ============================================================================
# Step 7: Verification
# ============================================================================
verify_setup() {
    log_step "Verifying setup"
    
    local errors=0
    
    # Check directories
    [ -d "$INSTALL_DIR" ] || { log_error "Install directory missing"; errors=$((errors+1)); }
    [ -d "$CONFIG_DIR" ] || { log_error "Config directory missing"; errors=$((errors+1)); }
    [ -d "$DATA_DIR" ] || { log_error "Data directory missing"; errors=$((errors+1)); }
    [ -d "$LOGS_DIR" ] || { log_error "Logs directory missing"; errors=$((errors+1)); }
    
    # Check config files
    [ -f "$CONFIG_DIR/cell0.conf" ] || { log_error "Main config missing"; errors=$((errors+1)); }
    [ -f "$CONFIG_DIR/providers.conf" ] || { log_error "Providers config missing"; errors=$((errors+1)); }
    
    # Check binaries
    [ -f "$INSTALL_DIR/bin/cell0ctl" ] || { log_error "cell0ctl missing"; errors=$((errors+1)); }
    [ -f "$INSTALL_DIR/bin/cell0d" ] || { log_error "cell0d missing"; errors=$((errors+1)); }
    
    if [ $errors -eq 0 ]; then
        log_success "All checks passed!"
        return 0
    else
        log_error "$errors verification errors found"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================
show_help() {
    cat << EOF
Cell 0 OS - Post-Installation Configuration

Usage: setup-config.sh [OPTIONS]

Options:
    -h, --help          Show this help message
    -q, --quick         Quick setup (skip prompts)
    -s, --shell-only    Only setup shell integration
    -v, --verify        Only run verification
    --dir DIR           Set installation directory
    --skip-services     Skip service configuration
    --skip-monitoring   Skip monitoring setup
    --skip-backup       Skip backup setup

Examples:
    setup-config.sh                    # Full interactive setup
    setup-config.sh --quick            # Quick setup
    setup-config.sh --shell-only       # Shell integration only
EOF
}

main() {
    local quick_mode=false
    local shell_only=false
    local verify_only=false
    local skip_services=false
    local skip_monitoring=false
    local skip_backup=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quick)
                quick_mode=true
                shift
                ;;
            -s|--shell-only)
                shell_only=true
                shift
                ;;
            -v|--verify)
                verify_only=true
                shift
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --skip-services)
                skip_services=true
                shift
                ;;
            --skip-monitoring)
                skip_monitoring=true
                shift
                ;;
            --skip-backup)
                skip_backup=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo -e "${CYAN}${BOLD}"
    echo 'Cell 0 OS - Post-Installation Configuration'
    echo -e "${NC}"
    
    if [ "$verify_only" = true ]; then
        verify_setup
        exit $?
    fi
    
    if [ "$shell_only" = true ]; then
        setup_shell_integration
        exit 0
    fi
    
    # Run setup steps
    setup_environment
    setup_ai_providers
    setup_shell_integration
    
    [ "$skip_services" = false ] && setup_services
    [ "$skip_monitoring" = false ] && setup_monitoring
    [ "$skip_backup" = false ] && setup_backup
    
    verify_setup
    
    echo
    log_success "Configuration complete!"
    echo
    echo "Next steps:"
    echo "  1. Source your shell configuration: source ~/.bashrc (or ~/.zshrc)"
    echo "  2. Edit $CONFIG_DIR/providers.conf to add API keys"
    echo "  3. Start Cell 0: cell0ctl start"
    echo
}

main "$@"
