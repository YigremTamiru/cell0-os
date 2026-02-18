#!/bin/bash
# Cell 0 OS - Universal Installer
# Usage: curl -fsSL https://cell0.io/install.sh | bash
# Supports: macOS (Apple Silicon & Intel), Linux (Ubuntu/Debian/Fedora/Arch)

set -euo pipefail

# Version
CELL0_VERSION="1.2.0"
INSTALLER_VERSION="2.0.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
INSTALL_DIR="${CELL0_HOME:-$HOME/cell0}"
STATE_DIR="${CELL0_STATE_DIR:-$HOME/.cell0}"
USE_GPU="${CELL0_GPU:-auto}"
INSTALL_MODE="${CELL0_INSTALL_MODE:-full}"  # minimal, full, dev

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1" >&2; }
log_step() { echo -e "\n${BOLD}${CYAN}▶ $1${NC}"; }

# Print banner
print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     ██████╗███████╗██╗     ██╗         ██████╗ ███████╗  ║
    ║    ██╔════╝██╔════╝██║     ██║        ██╔═══██╗██╔════╝  ║
    ║    ██║     █████╗  ██║     ██║        ██║   ██║███████╗  ║
    ║    ██║     ██╔══╝  ██║     ██║        ██║   ██║╚════██║  ║
    ║    ╚██████╗███████╗███████╗███████╗██╗╚██████╔╝███████║  ║
    ║     ╚═════╝╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚══════╝  ║
    ║                                                          ║
    ║           Sovereign Edge Model Operating System          ║
    ╚══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo -e "  Version: ${BOLD}${CELL0_VERSION}${NC} | Installer: ${INSTALLER_VERSION}"
    echo -e "  Mode: ${BOLD}${INSTALL_MODE}${NC} | Target: ${INSTALL_DIR}"
    echo ""
}

# Detect system
detect_system() {
    OS=$(uname -s)
    ARCH=$(uname -m)
    
    case "$OS" in
        Darwin)
            PLATFORM="macos"
            if [[ "$ARCH" == "arm64" ]]; then
                PLATFORM="macos-arm64"
            fi
            ;;
        Linux)
            PLATFORM="linux"
            if [[ -f /etc/os-release ]]; then
                source /etc/os-release
                DISTRO="$ID"
                DISTRO_VERSION="$VERSION_ID"
            fi
            ;;
        *)
            log_error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    log_info "Detected: $OS $ARCH ($PLATFORM)"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking Prerequisites"
    
    local missing_deps=()
    
    # Essential tools
    command_exists curl || missing_deps+=("curl")
    command_exists git || missing_deps+=("git")
    
    # Python version check
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 9 ]]; then
            log_warn "Python 3.9+ required, found $PYTHON_VERSION"
            missing_deps+=("python3.11")
        else
            log_success "Python $PYTHON_VERSION found"
        fi
    else
        missing_deps+=("python3")
    fi
    
    # Optional: Rust for kernel builds
    if [[ "$INSTALL_MODE" == "dev" ]] && ! command_exists cargo; then
        log_warn "Rust not found (needed for kernel development)"
        INSTALL_RUST=1
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_warn "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
    
    log_success "All prerequisites satisfied"
    return 0
}

# Install dependencies based on platform
install_dependencies() {
    log_step "Installing Dependencies"
    
    case "$PLATFORM" in
        macos*|macos-arm64*)
            install_macos_deps
            ;;
        linux)
            case "$DISTRO" in
                ubuntu|debian)
                    install_apt_deps
                    ;;
                fedora|rhel|centos)
                    install_yum_deps
                    ;;
                arch|manjaro)
                    install_pacman_deps
                    ;;
                *)
                    log_error "Unsupported Linux distribution: $DISTRO"
                    exit 1
                    ;;
            esac
            ;;
    esac
    
    # Install Rust if needed
    if [[ "${INSTALL_RUST:-0}" == 1 ]]; then
        install_rust
    fi
}

# macOS dependencies
install_macos_deps() {
    if ! command_exists brew; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add to PATH for Apple Silicon
        if [[ "$PLATFORM" == "macos-arm64" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
    
    log_info "Installing packages via Homebrew..."
    
    local packages=("python@3.11" "git" "curl")
    
    if [[ "$INSTALL_MODE" == "full" ]]; then
        packages+=("redis" "ollama")
    fi
    
    if [[ "$INSTALL_MODE" == "dev" ]]; then
        packages+=("rust" "cargo")
    fi
    
    brew install "${packages[@]}" 2>/dev/null || brew upgrade "${packages[@]}" 2>/dev/null || true
    
    # Link Python 3.11 if not default
    if command_exists python3.11 && ! command_exists python3; then
        brew link python@3.11 --force 2>/dev/null || true
    fi
    
    log_success "macOS dependencies installed"
}

# Ubuntu/Debian dependencies
install_apt_deps() {
    log_info "Installing packages via apt..."
    
    sudo apt-get update
    
    local packages=(
        "python3.11" "python3.11-venv" "python3.11-dev" "python3-pip"
        "git" "curl" "wget" "build-essential"
    )
    
    if [[ "$INSTALL_MODE" == "full" ]]; then
        packages+=("redis-server")
    fi
    
    if [[ "$INSTALL_MODE" == "dev" ]]; then
        packages+=("rustc" "cargo")
    fi
    
    sudo apt-get install -y "${packages[@]}"
    
    # Install Ollama if not present
    if [[ "$INSTALL_MODE" == "full" ]] && ! command_exists ollama; then
        log_info "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    log_success "APT dependencies installed"
}

# Fedora/RHEL dependencies
install_yum_deps() {
    log_info "Installing packages via yum/dnf..."
    
    local packages=(
        "python3" "python3-pip" "python3-devel"
        "git" "curl" "wget" "gcc" "gcc-c++" "make"
    )
    
    if [[ "$INSTALL_MODE" == "full" ]]; then
        packages+=("redis")
    fi
    
    if [[ "$INSTALL_MODE" == "dev" ]]; then
        packages+=("rust" "cargo")
    fi
    
    if command_exists dnf; then
        sudo dnf install -y "${packages[@]}"
    else
        sudo yum install -y "${packages[@]}"
    fi
    
    # Install Ollama
    if [[ "$INSTALL_MODE" == "full" ]] && ! command_exists ollama; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    log_success "YUM dependencies installed"
}

# Arch Linux dependencies
install_pacman_deps() {
    log_info "Installing packages via pacman..."
    
    local packages=(
        "python" "python-pip" "python-virtualenv"
        "git" "curl" "wget" "base-devel"
    )
    
    if [[ "$INSTALL_MODE" == "full" ]]; then
        packages+=("redis")
    fi
    
    if [[ "$INSTALL_MODE" == "dev" ]]; then
        packages+=("rust")
    fi
    
    sudo pacman -S --noconfirm "${packages[@]}"
    
    # Install Ollama from AUR
    if [[ "$INSTALL_MODE" == "full" ]] && ! command_exists ollama; then
        log_info "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    log_success "Pacman dependencies installed"
}

# Install Rust
install_rust() {
    log_info "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    log_success "Rust installed"
}

# Clone or update repository
setup_repository() {
    log_step "Setting Up Cell 0 Repository"
    
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Cell 0 repository found. Updating..."
        cd "$INSTALL_DIR"
        git fetch origin
        git checkout "v${CELL0_VERSION}" 2>/dev/null || git checkout main
        git pull
    else
        log_info "Cloning Cell 0 repository..."
        if [[ -d "$INSTALL_DIR" ]]; then
            log_warn "Directory $INSTALL_DIR exists but is not a git repo"
            mv "$INSTALL_DIR" "${INSTALL_DIR}.backup.$(date +%s)"
        fi
        
        # Clone from GitHub
        git clone --depth 1 --branch "v${CELL0_VERSION}" \
            https://github.com/cell0-os/cell0.git "$INSTALL_DIR" 2>/dev/null || \
        git clone --depth 1 --branch main \
            https://github.com/cell0-os/cell0.git "$INSTALL_DIR"
        
        cd "$INSTALL_DIR"
    fi
    
    log_success "Repository ready at $INSTALL_DIR"
}

# Create Python virtual environment
setup_virtualenv() {
    log_step "Creating Python Virtual Environment"
    
    cd "$INSTALL_DIR"
    
    # Use Python 3.11 if available
    PYTHON_CMD=$(command -v python3.11 || command -v python3)
    
    if [[ ! -d "venv" ]]; then
        $PYTHON_CMD -m venv venv
    fi
    
    # Activate and upgrade pip
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    log_success "Virtual environment ready"
}

# Install Python dependencies
install_python_deps() {
    log_step "Installing Python Dependencies"
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Install based on mode
    case "$INSTALL_MODE" in
        minimal)
            pip install -e . --quiet
            ;;
        full)
            pip install -e ".[dev]" --quiet
            ;;
        dev)
            pip install -e ".[dev,test]" --quiet
            ;;
    esac
    
    log_success "Python dependencies installed"
}

# Build Rust kernel (if dev mode)
build_kernel() {
    if [[ "$INSTALL_MODE" == "dev" ]] && [[ -d "kernel" ]]; then
        log_step "Building Rust Kernel"
        
        cd "$INSTALL_DIR/kernel"
        cargo build --release 2>/dev/null || cargo build
        
        log_success "Kernel built"
    fi
}

# Create state directory
setup_state_dir() {
    log_step "Setting Up State Directory"
    
    mkdir -p "$STATE_DIR"/{data,logs,config,backups,temp}
    
    # Copy default configs if not present
    if [[ -d "$INSTALL_DIR/config" ]] && [[ ! -f "$STATE_DIR/config/cell0.yaml" ]]; then
        cp -r "$INSTALL_DIR/config/"* "$STATE_DIR/config/" 2>/dev/null || true
    fi
    
    log_success "State directory ready at $STATE_DIR"
}

# Create systemd service (Linux)
create_systemd_service() {
    if [[ "$PLATFORM" != linux* ]]; then
        return
    fi
    
    log_step "Creating Systemd Service"
    
    mkdir -p ~/.config/systemd/user
    
    cat > ~/.config/systemd/user/cell0d.service << EOF
[Unit]
Description=Cell 0 OS Daemon
Documentation=https://docs.cell0.io
After=network-online.target ollama.service redis.service
Wants=network-online.target

[Service]
Type=simple
Environment=CELL0_HOME=$INSTALL_DIR
Environment=CELL0_STATE_DIR=$STATE_DIR
Environment=CELL0_ENV=production
Environment=CELL0_LOG_LEVEL=INFO
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/cell0d.py
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cell0d

[Install]
WantedBy=default.target
EOF
    
    systemctl --user daemon-reload
    log_success "Systemd service created"
}

# Create launchd plist (macOS)
create_launchd_service() {
    if [[ "$PLATFORM" != macos* ]]; then
        return
    fi
    
    log_step "Creating LaunchAgent"
    
    mkdir -p ~/Library/LaunchAgents
    
    cat > ~/Library/LaunchAgents/io.cell0.daemon.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.cell0.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/venv/bin/python</string>
        <string>$INSTALL_DIR/cell0d.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>CELL0_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>CELL0_STATE_DIR</key>
        <string>$STATE_DIR</string>
        <key>CELL0_ENV</key>
        <string>production</string>
        <key>CELL0_LOG_LEVEL</key>
        <string>INFO</string>
        <key>PYTHONPATH</key>
        <string>$INSTALL_DIR</string>
        <key>PATH</key>
        <string>$INSTALL_DIR/venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$STATE_DIR/logs/cell0d.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$STATE_DIR/logs/cell0d.stderr.log</string>
</dict>
</plist>
EOF
    
    log_success "LaunchAgent created"
}

# Create shell integration
create_shell_integration() {
    log_step "Creating Shell Integration"
    
    local shell_rc
    if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        shell_rc="$HOME/.zshrc"
    else
        shell_rc="$HOME/.bashrc"
    fi
    
    # Add to PATH if not already present
    if ! grep -q "cell0/bin" "$shell_rc" 2>/dev/null; then
        cat >> "$shell_rc" << EOF

# Cell 0 OS
export CELL0_HOME="$INSTALL_DIR"
export CELL0_STATE_DIR="$STATE_DIR"
export PATH="\$CELL0_HOME/bin:\$PATH"
alias cell0='cell0ctl'
EOF
    fi
    
    # Create convenience bin directory
    mkdir -p "$INSTALL_DIR/bin"
    
    cat > "$INSTALL_DIR/bin/cell0" << 'EOF'
#!/bin/bash
exec cell0ctl "$@"
EOF
    chmod +x "$INSTALL_DIR/bin/cell0"
    
    log_success "Shell integration added to $shell_rc"
}

# Run post-install checks
run_postinstall_checks() {
    log_step "Running Post-Installation Checks"
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Test imports
    if python -c "import cell0" 2>/dev/null; then
        log_success "Cell 0 module imports correctly"
    else
        log_warn "Cell 0 module import test failed"
    fi
    
    # Test cell0ctl
    if "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/cell0ctl.py" --version 2>/dev/null; then
        log_success "cell0ctl CLI is functional"
    else
        log_warn "cell0ctl test failed"
    fi
    
    # Run cell0-doctor if available
    if [[ -f "$INSTALL_DIR/scripts/cell0-doctor.py" ]]; then
        log_info "Running system diagnostics..."
        python "$INSTALL_DIR/scripts/cell0-doctor.py" --quick || true
    fi
}

# Print completion message
print_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║        Cell 0 OS Successfully Installed! 🧬                ║${NC}"
    echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "  ${BOLD}State Directory:${NC} $STATE_DIR"
    echo -e "  ${BOLD}Virtual Environment:${NC} $INSTALL_DIR/venv"
    echo ""
    echo -e "  ${BOLD}Quick Start:${NC}"
    echo -e "    ${CYAN}cell0ctl start${NC}          # Start the daemon"
    echo -e "    ${CYAN}cell0ctl status${NC}         # Check system status"
    echo -e "    ${CYAN}cell0ctl doctor${NC}         # Run diagnostics"
    echo ""
    echo -e "  ${BOLD}Web Interface:${NC}"
    echo -e "    HTTP API:   http://localhost:18800"
    echo -e "    WebSocket:  ws://localhost:18801"
    echo -e "    Metrics:    http://localhost:18802/metrics"
    echo ""
    echo -e "  ${BOLD}Documentation:${NC}"
    echo -e "    https://docs.cell0.io"
    echo -e "    https://github.com/cell0-os/cell0"
    echo ""
    
    if [[ "$PLATFORM" == macos* ]]; then
        echo -e "  ${YELLOW}To load the LaunchAgent, run:${NC}"
        echo -e "    ${CYAN}launchctl load ~/Library/LaunchAgents/io.cell0.daemon.plist${NC}"
        echo ""
    elif [[ "$PLATFORM" == linux* ]]; then
        echo -e "  ${YELLOW}To enable and start the service, run:${NC}"
        echo -e "    ${CYAN}systemctl --user enable cell0d${NC}"
        echo -e "    ${CYAN}systemctl --user start cell0d${NC}"
        echo ""
    fi
    
    echo -e "  ${YELLOW}Reload your shell or run:${NC} source ~/.bashrc (or ~/.zshrc)"
    echo ""
    echo -e "  ${BOLD}${GREEN}The glass has melted. Welcome to Cell 0 OS.${NC}"
    echo ""
}

# Cleanup on error
cleanup() {
    if [[ $? -ne 0 ]]; then
        echo ""
        log_error "Installation failed. Check the output above for details."
        log_info "For help, visit https://github.com/cell0-os/cell0/issues"
        
        # Restore backup if exists
        if [[ -d "${INSTALL_DIR}.backup"* ]]; then
            log_info "A backup of your previous installation may exist at:"
            ls -d "${INSTALL_DIR}.backup"* 2>/dev/null || true
        fi
    fi
}

trap cleanup EXIT

# Main installation flow
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --minimal)
                INSTALL_MODE="minimal"
                shift
                ;;
            --dev)
                INSTALL_MODE="dev"
                shift
                ;;
            --full)
                INSTALL_MODE="full"
                shift
                ;;
            --version=*)
                CELL0_VERSION="${1#*=}"
                shift
                ;;
            --dir=*)
                INSTALL_DIR="${1#*=}"
                shift
                ;;
            -h|--help)
                echo "Cell 0 OS Installer"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --minimal     Minimal installation (core only)"
                echo "  --full        Full installation with all features (default)"
                echo "  --dev         Development mode with all tools"
                echo "  --version=X.X.X  Install specific version"
                echo "  --dir=PATH    Custom installation directory"
                echo "  -h, --help    Show this help"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    print_banner
    detect_system
    
    if ! check_prerequisites; then
        log_info "Installing missing dependencies..."
        install_dependencies
    fi
    
    setup_repository
    setup_virtualenv
    install_python_deps
    build_kernel
    setup_state_dir
    create_systemd_service
    create_launchd_service
    create_shell_integration
    run_postinstall_checks
    
    print_completion
}

main "$@"
