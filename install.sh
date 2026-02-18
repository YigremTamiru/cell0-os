#!/bin/bash
# Cell 0 OS - Universal Installer
# One-line install: curl -fsSL https://cell0.io/install.sh | bash
# Supports: macOS, Linux (Debian/Ubuntu, RHEL/CentOS/Fedora, Arch)

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CELL0_VERSION="1.2.0"
INSTALL_DIR="${CELL0_INSTALL_DIR:-$HOME/.cell0}"
BIN_DIR="${CELL0_BIN_DIR:-$HOME/.local/bin}"
GITHUB_REPO="cell0-os/cell0"
RELEASE_URL="https://github.com/${GITHUB_REPO}/releases/download/v${CELL0_VERSION}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================================================
# Platform Detection
# ============================================================================
detect_platform() {
    OS=$(uname -s)
    ARCH=$(uname -m)
    
    case "$OS" in
        Darwin)
            PLATFORM="darwin"
            PACKAGE_MANAGER="brew"
            ;;
        Linux)
            PLATFORM="linux"
            if command -v apt-get &> /dev/null; then
                PACKAGE_MANAGER="apt"
            elif command -v yum &> /dev/null; then
                PACKAGE_MANAGER="yum"
            elif command -v dnf &> /dev/null; then
                PACKAGE_MANAGER="dnf"
            elif command -v pacman &> /dev/null; then
                PACKAGE_MANAGER="pacman"
            elif command -v apk &> /dev/null; then
                PACKAGE_MANAGER="apk"
            else
                PACKAGE_MANAGER="unknown"
            fi
            ;;
        *)
            log_error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    case "$ARCH" in
        x86_64|amd64)
            ARCH="amd64"
            ;;
        arm64|aarch64)
            ARCH="arm64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    log_info "Detected: $OS ($PLATFORM) on $ARCH"
    log_info "Package manager: $PACKAGE_MANAGER"
}

# ============================================================================
# Check Prerequisites
# ============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Python (3.9+)
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            log_success "Python $PYTHON_VERSION"
        else
            log_warn "Python $PYTHON_VERSION found (3.9+ required)"
            missing_deps+=("python3")
        fi
    else
        missing_deps+=("python3")
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("pip3")
    else
        log_success "pip3"
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    else
        log_success "git"
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    else
        log_success "curl"
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warn "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
    
    return 0
}

# ============================================================================
# Install Dependencies
# ============================================================================
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case "$PACKAGE_MANAGER" in
        brew)
            if ! command -v brew &> /dev/null; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python@3.11 git curl || true
            ;;
        apt)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv git curl
            ;;
        yum)
            sudo yum install -y python3 python3-pip git curl
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip git curl
            ;;
        pacman)
            sudo pacman -S --noconfirm python python-pip git curl
            ;;
        apk)
            sudo apk add --no-cache python3 py3-pip git curl
            ;;
        *)
            log_error "Unknown package manager. Please install dependencies manually."
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed"
}

# ============================================================================
# Download and Install Cell 0
# ============================================================================
install_cell0() {
    log_info "Installing Cell 0 OS v${CELL0_VERSION}..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR" "$BIN_DIR"
    
    # Download pre-built binary or install from source
    local download_url="${RELEASE_URL}/cell0-${PLATFORM}-${ARCH}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    if curl -fsSL --head "$download_url" | grep -q "200 OK"; then
        log_info "Downloading pre-built binary..."
        curl -fsSL "$download_url" -o "$temp_dir/cell0.tar.gz"
        tar -xzf "$temp_dir/cell0.tar.gz" -C "$INSTALL_DIR"
        log_success "Pre-built binary installed"
    else
        log_info "Building from source..."
        install_from_source "$temp_dir"
    fi
    
    # Create symlinks
    ln -sf "$INSTALL_DIR/bin/cell0ctl" "$BIN_DIR/cell0ctl"
    ln -sf "$INSTALL_DIR/bin/cell0d" "$BIN_DIR/cell0d"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_success "Cell 0 OS installed to $INSTALL_DIR"
}

# ============================================================================
# Install from Source
# ============================================================================
install_from_source() {
    local temp_dir=$1
    
    # Clone repository
    log_info "Cloning repository..."
    git clone --depth 1 --branch "v${CELL0_VERSION}" \
        "https://github.com/${GITHUB_REPO}.git" "$temp_dir/cell0" 2>/dev/null || {
        log_warn "Could not clone repository, using local files..."
        cp -r . "$temp_dir/cell0"
    }
    
    cd "$temp_dir/cell0"
    
    # Create virtual environment
    log_info "Creating Python virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -e .
    
    # Copy source files
    cp -r cell0 "$INSTALL_DIR/"
    cp -r col "$INSTALL_DIR/" 2>/dev/null || true
    cp -r engine "$INSTALL_DIR/" 2>/dev/null || true
    cp -r service "$INSTALL_DIR/" 2>/dev/null || true
    
    # Create wrapper scripts
    create_wrapper_scripts
    
    deactivate
}

# ============================================================================
# Create Wrapper Scripts
# ============================================================================
create_wrapper_scripts() {
    mkdir -p "$INSTALL_DIR/bin"
    
    # cell0d wrapper
    cat > "$INSTALL_DIR/bin/cell0d" << 'EOF'
#!/bin/bash
source "${CELL0_HOME:-$HOME/.cell0}/venv/bin/activate"
export CELL0_HOME="${CELL0_HOME:-$HOME/.cell0}"
export CELL0_STATE_DIR="${CELL0_HOME}/data"
exec python -m cell0.cell0d "$@"
EOF
    chmod +x "$INSTALL_DIR/bin/cell0d"
    
    # cell0ctl wrapper
    cat > "$INSTALL_DIR/bin/cell0ctl" << 'EOF'
#!/bin/bash
source "${CELL0_HOME:-$HOME/.cell0}/venv/bin/activate"
export CELL0_HOME="${CELL0_HOME:-$HOME/.cell0}"
exec python -m cell0.cell0ctl "$@"
EOF
    chmod +x "$INSTALL_DIR/bin/cell0ctl"
}

# ============================================================================
# Create System Service
# ============================================================================
create_service() {
    log_info "Creating system service..."
    
    case "$PLATFORM" in
        darwin)
            create_launchd_service
            ;;
        linux)
            if command -v systemctl &> /dev/null; then
                create_systemd_service
            else
                log_warn "systemctl not found, skipping service creation"
            fi
            ;;
    esac
}

# ============================================================================
# Create systemd Service
# ============================================================================
create_systemd_service() {
    local service_file="$HOME/.config/systemd/user/cell0d.service"
    mkdir -p "$HOME/.config/systemd/user"
    
    cat > "$service_file" << EOF
[Unit]
Description=Cell 0 OS Daemon
Documentation=https://docs.cell0.io
After=network.target

[Service]
Type=simple
Environment=CELL0_HOME=$INSTALL_DIR
Environment=CELL0_STATE_DIR=$INSTALL_DIR/data
Environment=CELL0_LOG_LEVEL=INFO
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$INSTALL_DIR/bin/cell0d
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF
    
    systemctl --user daemon-reload
    log_success "Systemd user service created"
    log_info "Enable with: systemctl --user enable cell0d"
    log_info "Start with: systemctl --user start cell0d"
}

# ============================================================================
# Create launchd Service (macOS)
# ============================================================================
create_launchd_service() {
    local plist_file="$HOME/Library/LaunchAgents/com.cell0.daemon.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cell0.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/bin/cell0d</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>CELL0_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>CELL0_STATE_DIR</key>
        <string>$INSTALL_DIR/data</string>
        <key>PATH</key>
        <string>$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/cell0d.stdout</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/cell0d.stderr</string>
</dict>
</plist>
EOF
    
    log_success "LaunchAgent created"
    log_info "Load with: launchctl load $plist_file"
    log_info "Start with: launchctl start com.cell0.daemon"
}

# ============================================================================
# Configure Shell
# ============================================================================
configure_shell() {
    log_info "Configuring shell..."
    
    local shell_rc=""
    case "$SHELL" in
        */bash)
            shell_rc="$HOME/.bashrc"
            ;;
        */zsh)
            shell_rc="$HOME/.zshrc"
            ;;
        */fish)
            shell_rc="$HOME/.config/fish/config.fish"
            ;;
        *)
            shell_rc="$HOME/.profile"
            ;;
    esac
    
    # Add to PATH if not already there
    if ! grep -q "$BIN_DIR" "$shell_rc" 2>/dev/null; then
        echo "" >> "$shell_rc"
        echo "# Cell 0 OS" >> "$shell_rc"
        echo 'export PATH="'$BIN_DIR':$PATH"' >> "$shell_rc"
        log_success "Added $BIN_DIR to PATH in $shell_rc"
        log_info "Run: source $shell_rc"
    fi
    
    # Create environment file
    cat > "$INSTALL_DIR/env" << EOF
export CELL0_HOME=$INSTALL_DIR
export CELL0_STATE_DIR=$INSTALL_DIR/data
export CELL0_CONFIG_DIR=$INSTALL_DIR/config
export PATH="$BIN_DIR:\$PATH"
EOF
}

# ============================================================================
# Verify Installation
# ============================================================================
verify_installation() {
    log_info "Verifying installation..."
    
    # Check binaries exist
    if [ ! -f "$INSTALL_DIR/bin/cell0d" ]; then
        log_error "cell0d binary not found"
        return 1
    fi
    
    if [ ! -f "$INSTALL_DIR/bin/cell0ctl" ]; then
        log_error "cell0ctl binary not found"
        return 1
    fi
    
    # Check virtual environment
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        log_error "Virtual environment not found"
        return 1
    fi
    
    # Test import
    if ! "$INSTALL_DIR/venv/bin/python" -c "import cell0" 2>/dev/null; then
        log_warn "Cell 0 module import test failed"
    fi
    
    log_success "Installation verified"
    return 0
}

# ============================================================================
# Print Summary
# ============================================================================
print_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🧬 Cell 0 OS v${CELL0_VERSION} installed successfully!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  Installation directory: $INSTALL_DIR"
    echo "  Binary directory:       $BIN_DIR"
    echo "  Data directory:         $INSTALL_DIR/data"
    echo "  Config directory:       $INSTALL_DIR/config"
    echo "  Log directory:          $INSTALL_DIR/logs"
    echo ""
    echo "  Commands:"
    echo "    cell0d start          # Start the daemon"
    echo "    cell0d status         # Check daemon status"
    echo "    cell0ctl --help       # CLI help"
    echo ""
    echo "  Web interfaces:"
    echo "    Web UI:    http://localhost:18800"
    echo "    WebSocket: ws://localhost:18801"
    echo "    Metrics:   http://localhost:18802/metrics"
    echo ""
    echo "  Documentation: https://docs.cell0.io"
    echo "  GitHub:        https://github.com/cell0-os/cell0"
    echo ""
    echo "  🌊 The glass has melted."
    echo "═══════════════════════════════════════════════════════════════"
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo "🧬 Cell 0 OS Installer v${CELL0_VERSION}"
    echo "======================================"
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                CELL0_VERSION="$2"
                shift 2
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --bin-dir)
                BIN_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --version VERSION    Install specific version (default: $CELL0_VERSION)"
                echo "  --dir PATH           Installation directory (default: ~/.cell0)"
                echo "  --bin-dir PATH       Binary directory (default: ~/.local/bin)"
                echo "  --help, -h           Show this help message"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Run installation steps
    detect_platform
    
    if ! check_prerequisites; then
        install_dependencies
    fi
    
    install_cell0
    create_service
    configure_shell
    verify_installation
    print_summary
}

main "$@"
