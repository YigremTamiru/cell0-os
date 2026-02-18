#!/bin/bash
# Cell 0 OS - One-Line Installer
# Usage: curl -fsSL https://cell0.local/install.sh | bash

set -e

echo "🧬 Cell 0 OS Installer"
echo "======================"

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo "Detected: $OS $ARCH"

# Check prerequisites
check_prereq() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 not found. Installing..."
        return 1
    fi
    echo "✅ $1 found"
    return 0
}

# Install based on OS
install_deps() {
    echo ""
    echo "Installing dependencies..."
    
    if [[ "$OS" == "Darwin" ]]; then
        # macOS
        if ! command -v brew &> /dev/null; then
            echo "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python@3.11 rust cargo node || true
        
    elif [[ "$OS" == "Linux" ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip rustc cargo nodejs npm
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS/Fedora
            sudo yum install -y python3 python3-pip rust cargo nodejs npm
        elif command -v pacman &> /dev/null; then
            # Arch
            sudo pacman -S --noconfirm python python-pip rust cargo nodejs npm
        fi
    fi
}

# Install Cell 0
install_cell0() {
    echo ""
    echo "Installing Cell 0 OS..."
    
    INSTALL_DIR="${HOME}/cell0"
    
    if [[ -d "$INSTALL_DIR" ]]; then
        echo "Cell 0 already installed at $INSTALL_DIR"
        echo "Updating..."
        cd "$INSTALL_DIR"
        git pull 2>/dev/null || echo "Using existing installation"
    else
        echo "Cloning Cell 0 OS..."
        git clone https://github.com/cell0-os/cell0.git "$INSTALL_DIR" 2>/dev/null || {
            echo "Creating fresh installation..."
            mkdir -p "$INSTALL_DIR"
        }
    fi
    
    cd "$INSTALL_DIR"
    
    # Install Python dependencies
    echo "Installing Python packages..."
    pip3 install --user -q fastapi uvicorn pyjwt websockets prometheus-client 2>/dev/null || \
    pip3 install --user --break-system-packages -q fastapi uvicorn pyjwt websockets prometheus-client
    
    # Build Rust kernel
    echo "Building Rust kernel..."
    cd kernel
    cargo build --release 2>/dev/null || cargo build
    cd ..
    
    # Create systemd service (Linux) or launchd plist (macOS)
    echo "Creating service..."
    if [[ "$OS" == "Linux" ]]; then
        mkdir -p ~/.config/systemd/user
        cat > ~/.config/systemd/user/cell0d.service << 'EOF'
[Unit]
Description=Cell 0 OS Daemon
After=network.target

[Service]
Type=simple
ExecStart=%h/cell0/cell0d.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
        systemctl --user daemon-reload
        systemctl --user enable cell0d
        
    elif [[ "$OS" == "Darwin" ]]; then
        mkdir -p ~/Library/LaunchAgents
        cat > ~/Library/LaunchAgents/com.cell0.daemon.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cell0.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>~/cell0/cell0d.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
    fi
    
    echo ""
    echo "✅ Cell 0 OS installed successfully!"
    echo ""
    echo "📍 Installation directory: $INSTALL_DIR"
    echo "🚀 Start daemon: cell0d start"
    echo "📊 Web UI: http://localhost:18800"
    echo "📡 WebSocket: ws://localhost:18801"
    echo "📈 Metrics: http://localhost:18802/metrics"
    echo ""
    echo "🧬 Welcome to Cell 0 OS. The glass has melted."
}

# Main
main() {
    check_prereq git || install_deps
    check_prereq python3 || install_deps
    check_prereq cargo || install_deps
    
    install_cell0
}

main "$@"
