#!/bin/bash
# Cell 0 OS - Dependency Verification Script
# Verifies all dependencies are correctly installed and configured

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# Logging
# ============================================================================
log_info() { echo -e "${BLUE}[CHECK]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Counters
CHECKS_PASSED=0
CHECKS_WARNED=0
CHECKS_FAILED=0

# ============================================================================
# System Checks
# ============================================================================
check_os() {
    log_info "Checking operating system..."
    
    case "$(uname -s)" in
        Darwin)
            log_ok "macOS detected: $(sw_vers -productVersion)"
            ((CHECKS_PASSED++)) || true
            ;;
        Linux)
            if [ -f /etc/os-release ]; then
                source /etc/os-release
                log_ok "Linux detected: $NAME $VERSION_ID"
                ((CHECKS_PASSED++)) || true
            else
                log_ok "Linux detected"
                ((CHECKS_PASSED++)) || true
            fi
            ;;
        *)
            log_warn "Unknown operating system"
            ((CHECKS_WARNED++)) || true
            ;;
    esac
}

check_architecture() {
    log_info "Checking architecture..."
    
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            log_ok "x86_64 architecture"
            ((CHECKS_PASSED++)) || true
            ;;
        arm64|aarch64)
            log_ok "ARM64 architecture"
            ((CHECKS_PASSED++)) || true
            ;;
        *)
            log_warn "Architecture $arch may not be fully supported"
            ((CHECKS_WARNED++)) || true
            ;;
    esac
}

# ============================================================================
# Python Checks
# ============================================================================
check_python() {
    log_info "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1)
        log_ok "Python found: $version"
        
        # Check version >= 3.9
        local major=$(python3 -c 'import sys; print(sys.version_info.major)')
        local minor=$(python3 -c 'import sys; print(sys.version_info.minor)')
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ]; then
            log_ok "Python version meets requirements (>= 3.9)"
            ((CHECKS_PASSED++)) || true
        else
            log_error "Python version $major.$minor is too old (need >= 3.9)"
            ((CHECKS_FAILED++)) || true
        fi
    else
        log_error "Python 3 not found"
        ((CHECKS_FAILED++)) || true
    fi
}

check_pip() {
    log_info "Checking pip..."
    
    if command -v pip3 &> /dev/null; then
        local version=$(pip3 --version | awk '{print $2}')
        log_ok "pip3 found: version $version"
        ((CHECKS_PASSED++)) || true
    else
        log_error "pip3 not found"
        ((CHECKS_FAILED++)) || true
    fi
}

check_venv() {
    log_info "Checking venv module..."
    
    if python3 -m venv --help > /dev/null 2>&1; then
        log_ok "venv module available"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "venv module not available (may need python3-venv package)"
        ((CHECKS_WARNED++)) || true
    fi
}

# ============================================================================
# Core Dependencies
# ============================================================================
check_git() {
    log_info "Checking git..."
    
    if command -v git &> /dev/null; then
        local version=$(git --version | awk '{print $3}')
        log_ok "git found: version $version"
        ((CHECKS_PASSED++)) || true
    else
        log_error "git not found"
        ((CHECKS_FAILED++)) || true
    fi
}

check_curl() {
    log_info "Checking curl..."
    
    if command -v curl &> /dev/null; then
        local version=$(curl --version | head -1 | awk '{print $2}')
        log_ok "curl found: $version"
        ((CHECKS_PASSED++)) || true
    else
        log_error "curl not found"
        ((CHECKS_FAILED++)) || true
    fi
}

check_rust() {
    log_info "Checking Rust (optional)..."
    
    if command -v rustc &> /dev/null; then
        local version=$(rustc --version)
        log_ok "Rust found: $version"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "Rust not found (only needed for building from source)"
        ((CHECKS_WARNED++)) || true
    fi
}

# ============================================================================
# Optional Dependencies
# ============================================================================
check_ollama() {
    log_info "Checking Ollama (optional)..."
    
    if command -v ollama &> /dev/null; then
        log_ok "Ollama found"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "Ollama not found (needed for local LLM inference)"
        ((CHECKS_WARNED++)) || true
    fi
}

check_redis() {
    log_info "Checking Redis (optional)..."
    
    if command -v redis-cli &> /dev/null; then
        log_ok "Redis client found"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "Redis not found (used for caching)"
        ((CHECKS_WARNED++)) || true
    fi
}

check_docker() {
    log_info "Checking Docker (optional)..."
    
    if command -v docker &> /dev/null; then
        local version=$(docker --version)
        log_ok "Docker found: $version"
        ((CHECKS_PASSED++)) || true
        
        # Check if docker daemon is running
        if docker info > /dev/null 2>&1; then
            log_ok "Docker daemon is running"
            ((CHECKS_PASSED++)) || true
        else
            log_warn "Docker daemon not running"
            ((CHECKS_WARNED++)) || true
        fi
    else
        log_warn "Docker not found (optional, for containerized deployment)"
        ((CHECKS_WARNED++)) || true
    fi
}

check_kubectl() {
    log_info "Checking kubectl (optional)..."
    
    if command -v kubectl &> /dev/null; then
        local version=$(kubectl version --client -o yaml 2>/dev/null | grep gitVersion | head -1 | awk '{print $2}')
        log_ok "kubectl found: $version"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "kubectl not found (optional, for Kubernetes deployment)"
        ((CHECKS_WARNED++)) || true
    fi
}

check_helm() {
    log_info "Checking Helm (optional)..."
    
    if command -v helm &> /dev/null; then
        local version=$(helm version --short)
        log_ok "Helm found: $version"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "Helm not found (optional, for Kubernetes deployment)"
        ((CHECKS_WARNED++)) || true
    fi
}

# ============================================================================
# Network Checks
# ============================================================================
check_network() {
    log_info "Checking network connectivity..."
    
    if curl -fsSL --max-time 5 https://github.com > /dev/null 2>&1; then
        log_ok "Internet connectivity OK"
        ((CHECKS_PASSED++)) || true
    else
        log_warn "No internet connectivity (offline installation will be used)"
        ((CHECKS_WARNED++)) || true
    fi
}

check_ports() {
    log_info "Checking port availability..."
    
    local ports=(18800 18801 18802)
    
    for port in "${ports[@]}"; do
        if ! lsof -Pi :$port -sTCP:LISTEN -t > /dev/null 2>&1; then
            log_ok "Port $port is available"
            ((CHECKS_PASSED++)) || true
        else
            log_warn "Port $port is already in use"
            ((CHECKS_WARNED++)) || true
        fi
    done
}

# ============================================================================
# Python Package Checks
# ============================================================================
check_python_packages() {
    log_info "Checking Python packages (if installed)..."
    
    local packages=("fastapi" "uvicorn" "websockets" "aiohttp" "pyyaml" "pydantic")
    
    for pkg in "${packages[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            log_ok "Python package installed: $pkg"
            ((CHECKS_PASSED++)) || true
        else
            log_info "Python package not installed (will be installed): $pkg"
        fi
    done
}

# ============================================================================
# Cell 0 Specific Checks
# ============================================================================
check_cell0_installation() {
    log_info "Checking for existing Cell 0 installation..."
    
    if [ -d "$HOME/.cell0" ]; then
        log_warn "Existing Cell 0 installation found at ~/.cell0"
        ((CHECKS_WARNED++)) || true
    else
        log_ok "No existing Cell 0 installation"
        ((CHECKS_PASSED++)) || true
    fi
    
    if command -v cell0d &> /dev/null; then
        log_warn "cell0d already in PATH"
        ((CHECKS_WARNED++)) || true
    else
        log_ok "cell0d not in PATH"
        ((CHECKS_PASSED++)) || true
    fi
}

# ============================================================================
# Summary
# ============================================================================
print_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Dependency Verification Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ✓ Passed:  $CHECKS_PASSED"
    echo "  ⚠ Warned:  $CHECKS_WARNED"
    echo "  ✗ Failed:  $CHECKS_FAILED"
    echo "═══════════════════════════════════════════════════════════════"
    
    if [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${GREEN}System ready for Cell 0 installation!${NC}"
        
        if [ $CHECKS_WARNED -eq 0 ]; then
            echo -e "${GREEN}All optional dependencies also available.${NC}"
        else
            echo -e "${YELLOW}Some optional features may be unavailable (see warnings above).${NC}"
        fi
        
        echo ""
        echo "Install with:"
        echo "  curl -fsSL https://cell0.io/install.sh | bash"
        return 0
    else
        echo -e "${RED}Please resolve the failed checks before installing.${NC}"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Cell 0 OS Dependency Verification"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # System checks
    check_os
    check_architecture
    
    # Core dependencies
    check_python
    check_pip
    check_venv
    check_git
    check_curl
    
    # Optional build dependencies
    check_rust
    
    # Optional runtime dependencies
    check_ollama
    check_redis
    check_docker
    check_kubectl
    check_helm
    
    # Network and ports
    check_network
    check_ports
    
    # Python packages
    check_python_packages
    
    # Cell 0 specific
    check_cell0_installation
    
    # Summary
    print_summary
}

main "$@"
