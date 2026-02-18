#!/bin/bash
# Signal Integration Setup Script for Cell 0 OS
# 
# This script helps you set up Signal messaging for Cell 0 OS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SIGNAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CELL0_DIR="$(dirname "$SIGNAL_DIR")"

log() {
    echo -e "${BLUE}[Signal Setup]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

error() {
    echo -e "${RED}[Error]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[Success]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        warn "Python 3 is not installed. Some features may not work."
    fi
    
    success "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    log "Setting up environment..."
    
    cd "$CELL0_DIR"
    
    # Check if .env.signal exists
    if [ -f ".env.signal" ]; then
        warn ".env.signal already exists. Backup created at .env.signal.backup"
        cp .env.signal .env.signal.backup
    fi
    
    # Copy example environment file
    cp .env.signal.example .env.signal
    
    success "Environment file created: .env.signal"
    log "Please edit .env.signal with your phone number and settings"
}

# Create directories
setup_directories() {
    log "Creating directories..."
    
    mkdir -p "$CELL0_DIR/data/signal/attachments"
    mkdir -p "$CELL0_DIR/data/signal/cache"
    mkdir -p "$CELL0_DIR/backups/signal"
    
    success "Directories created"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    cd "$CELL0_DIR"
    
    # Check if pip is available
    if command -v pip3 &> /dev/null; then
        pip3 install pyyaml aiohttp pytest pytest-asyncio || warn "Failed to install some dependencies"
    elif command -v pip &> /dev/null; then
        pip install pyyaml aiohttp pytest pytest-asyncio || warn "Failed to install some dependencies"
    else
        warn "pip not found. Please install Python dependencies manually:"
        echo "  pip3 install pyyaml aiohttp pytest pytest-asyncio"
    fi
    
    success "Python dependencies installed"
}

# Build Docker image
build_docker() {
    log "Building Signal CLI Docker image..."
    
    cd "$CELL0_DIR"
    
    docker-compose -f docker-compose.signal.yml build || error "Failed to build Docker image"
    
    success "Docker image built successfully"
}

# Start Signal CLI
start_signal_cli() {
    log "Starting Signal CLI..."
    
    cd "$CELL0_DIR"
    
    # Check if already running
    if docker ps | grep -q "cell0-signal-cli"; then
        warn "Signal CLI is already running"
        return
    fi
    
    docker-compose -f docker-compose.signal.yml up -d || error "Failed to start Signal CLI"
    
    success "Signal CLI started"
    log "Waiting for initialization..."
    sleep 5
    
    # Check health
    if curl -s http://localhost:8080/v1/health > /dev/null 2>&1; then
        success "Signal CLI is healthy"
    else
        warn "Signal CLI may not be ready yet. Check logs with: docker-compose -f docker-compose.signal.yml logs"
    fi
}

# Register phone number
register_phone() {
    log "Phone Registration"
    echo ""
    echo "Choose registration method:"
    echo "1) Register with SMS verification"
    echo "2) Link to existing Signal device"
    echo "3) Skip (configure manually later)"
    echo ""
    read -p "Enter choice [1-3]: " choice
    
    case $choice in
        1)
            register_with_sms
            ;;
        2)
            link_device
            ;;
        3)
            log "Skipping registration. You can register later using:"
            echo "  ./integrations/signal_setup.sh register"
            ;;
        *)
            warn "Invalid choice. Skipping registration."
            ;;
    esac
}

# Register with SMS
register_with_sms() {
    log "Registering with SMS..."
    
    # Get phone number from env
    PHONE=$(grep SIGNAL_CLI_PHONE_NUMBER .env.signal | cut -d'=' -f2)
    
    if [ -z "$PHONE" ] || [ "$PHONE" = "+1234567890" ]; then
        read -p "Enter your phone number (with country code, e.g., +1234567890): " PHONE
        # Update env file
        sed -i.bak "s/SIGNAL_CLI_PHONE_NUMBER=.*/SIGNAL_CLI_PHONE_NUMBER=$PHONE/" .env.signal
        rm -f .env.signal.bak
    fi
    
    log "Requesting verification code for $PHONE..."
    
    # Request verification code
    curl -X POST "http://localhost:8080/v1/register/$PHONE" || error "Failed to request verification code"
    
    echo ""
    read -p "Enter the verification code received via SMS: " code
    
    log "Verifying code..."
    curl -X POST "http://localhost:8080/v1/register/$PHONE/verify" \
        -H "Content-Type: application/json" \
        -d "{\"verification_code\": \"$code\"}" || error "Failed to verify code"
    
    success "Phone number registered successfully!"
}

# Link to existing device
link_device() {
    log "Linking to existing device..."
    
    docker-compose -f docker-compose.signal.yml run --rm signal-cli-register link
    
    echo ""
    echo "Scan the QR code above with your Signal mobile app:"
    echo "  Settings → Linked Devices → Link New Device"
}

# Show status
show_status() {
    log "Signal Integration Status"
    echo ""
    
    # Check if container is running
    if docker ps | grep -q "cell0-signal-cli"; then
        success "Signal CLI container: RUNNING"
        
        # Check health
        if curl -s http://localhost:8080/v1/health > /dev/null 2>&1; then
            success "API Health: OK"
        else
            warn "API Health: Not responding"
        fi
        
        # Show registered accounts
        log "Registered accounts:"
        curl -s http://localhost:8080/v1/accounts 2>/dev/null || echo "  (none)"
    else
        error "Signal CLI container: NOT RUNNING"
    fi
    
    echo ""
    log "Configuration:"
    if [ -f ".env.signal" ]; then
        grep SIGNAL_CLI_PHONE_NUMBER .env.signal || echo "  Phone: Not set"
    fi
}

# Test connection
test_connection() {
    log "Testing Signal connection..."
    
    cd "$CELL0_DIR"
    
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from integrations.signal_bot import SignalBot
    import asyncio
    
    async def test():
        bot = SignalBot()
        try:
            await bot.start()
            print('✓ Successfully connected to Signal CLI')
            await bot.stop()
        except Exception as e:
            print(f'✗ Connection failed: {e}')
            sys.exit(1)
    
    asyncio.run(test())
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
" || error "Connection test failed"
    
    success "Connection test passed"
}

# Show help
show_help() {
    cat << EOF
Signal Integration Setup for Cell 0 OS

Usage: $0 [command]

Commands:
    setup       Full setup (prerequisites, environment, start)
    start       Start Signal CLI container
    stop        Stop Signal CLI container
    restart     Restart Signal CLI container
    register    Register a phone number
    link        Link to existing device
    status      Show current status
    test        Test the connection
    logs        Show container logs
    backup      Backup configuration
    clean       Remove all data (DANGEROUS)
    help        Show this help message

Quick Start:
    1. Run: $0 setup
    2. Edit .env.signal with your phone number
    3. Run: $0 register
    4. Test: $0 test

For more information, see integrations/SIGNAL_README.md
EOF
}

# Main function
main() {
    case "${1:-setup}" in
        setup)
            check_prerequisites
            setup_environment
            setup_directories
            install_python_deps
            build_docker
            start_signal_cli
            register_phone
            echo ""
            success "Setup complete!"
            echo ""
            log "Next steps:"
            echo "  1. Edit .env.signal with your settings"
            echo "  2. Test the connection: $0 test"
            echo "  3. See examples in: integrations/SIGNAL_README.md"
            ;;
        start)
            start_signal_cli
            ;;
        stop)
            cd "$CELL0_DIR"
            docker-compose -f docker-compose.signal.yml down
            success "Signal CLI stopped"
            ;;
        restart)
            cd "$CELL0_DIR"
            docker-compose -f docker-compose.signal.yml restart
            success "Signal CLI restarted"
            ;;
        register)
            register_phone
            ;;
        link)
            link_device
            ;;
        status)
            show_status
            ;;
        test)
            test_connection
            ;;
        logs)
            cd "$CELL0_DIR"
            docker-compose -f docker-compose.signal.yml logs -f
            ;;
        backup)
            cd "$CELL0_DIR"
            docker-compose -f docker-compose.signal.yml --profile backup run --rm signal-cli-backup
            ;;
        clean)
            read -p "This will DELETE all Signal data. Are you sure? [y/N] " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                cd "$CELL0_DIR"
                docker-compose -f docker-compose.signal.yml down -v
                rm -rf data/signal
                success "Signal data cleaned"
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $1. Run '$0 help' for usage."
            ;;
    esac
}

main "$@"
