#!/bin/bash
# Cell 0 OS - Installation Verification Script
# Validates a Cell 0 OS installation

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CELL0_VERSION="1.2.0"
INSTALL_DIR="${CELL0_HOME:-$HOME/.cell0}"
CONFIG_DIR="${CELL0_CONFIG_DIR:-$HOME/.config/cell0}"
DATA_DIR="${CELL0_DATA_DIR:-$HOME/.cell0/data}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0

# ============================================================================
# Output Functions
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; TESTS_FAILED=$((TESTS_FAILED + 1)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; TESTS_WARNINGS=$((TESTS_WARNINGS + 1)); }
log_section() { echo -e "\n${CYAN}${BOLD}▶ $1${NC}"; }

# ============================================================================
# Test 1: Directory Structure
# ============================================================================
test_directories() {
    log_section "Testing Directory Structure"
    
    local dirs=(
        "$INSTALL_DIR"
        "$INSTALL_DIR/bin"
        "$INSTALL_DIR/venv"
        "$CONFIG_DIR"
        "$DATA_DIR"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_pass "Directory exists: $dir"
        else
            log_fail "Directory missing: $dir"
        fi
    done
}

# ============================================================================
# Test 2: Binary Files
# ============================================================================
test_binaries() {
    log_section "Testing Binary Files"
    
    local binaries=(
        "$INSTALL_DIR/bin/cell0ctl"
        "$INSTALL_DIR/bin/cell0d"
    )
    
    for binary in "${binaries[@]}"; do
        if [ -f "$binary" ]; then
            if [ -x "$binary" ]; then
                log_pass "Binary executable: $(basename $binary)"
            else
                log_warn "Binary not executable: $(basename $binary)"
            fi
        else
            log_fail "Binary missing: $(basename $binary)"
        fi
    done
}

# ============================================================================
# Test 3: Configuration Files
# ============================================================================
test_configuration() {
    log_section "Testing Configuration Files"
    
    local configs=(
        "$CONFIG_DIR/cell0.conf"
        "$CONFIG_DIR/providers.conf"
    )
    
    for config in "${configs[@]}"; do
        if [ -f "$config" ]; then
            log_pass "Config exists: $(basename $config)"
            
            # Check permissions
            local perms=$(stat -c %a "$config" 2>/dev/null || stat -f %A "$config" 2>/dev/null)
            if [ "${perms:-644}" = "600" ] || [ "${perms:-644}" = "644" ]; then
                log_pass "Config permissions OK: $(basename $config)"
            else
                log_warn "Config permissions: $perms (expected 600 or 644)"
            fi
        else
            log_fail "Config missing: $(basename $config)"
        fi
    done
}

# ============================================================================
# Test 4: Python Environment
# ============================================================================
test_python_env() {
    log_section "Testing Python Environment"
    
    local venv_python="$INSTALL_DIR/venv/bin/python"
    
    if [ -f "$venv_python" ]; then
        log_pass "Python interpreter exists"
        
        # Test Python version
        local py_version=$($venv_python --version 2>&1)
        log_info "Python version: $py_version"
        
        # Test pip
        if [ -f "$INSTALL_DIR/venv/bin/pip" ]; then
            log_pass "pip available"
        else
            log_fail "pip not found"
        fi
        
        # Test cell0 import
        if $venv_python -c "import cell0" 2>/dev/null; then
            log_pass "cell0 module importable"
        else
            log_warn "cell0 module not importable (may need activation)"
        fi
    else
        log_fail "Python interpreter missing"
    fi
}

# ============================================================================
# Test 5: Dependencies
# ============================================================================
test_dependencies() {
    log_section "Testing Dependencies"
    
    local venv_python="$INSTALL_DIR/venv/bin/python"
    
    if [ ! -f "$venv_python" ]; then
        log_fail "Cannot test dependencies - Python missing"
        return
    fi
    
    local deps=(
        "aiohttp"
        "pydantic"
        "typer"
        "rich"
        "websockets"
        "PyYAML"
    )
    
    for dep in "${deps[@]}"; do
        if $venv_python -c "import $dep" 2>/dev/null; then
            log_pass "Dependency: $dep"
        else
            log_fail "Missing dependency: $dep"
        fi
    done
}

# ============================================================================
# Test 6: Service Status
# ============================================================================
test_services() {
    log_section "Testing Services"
    
    local os=$(uname -s)
    
    case "$os" in
        Linux)
            if command -v systemctl &> /dev/null; then
                if systemctl --user is-active cell0d &>/dev/null; then
                    log_pass "cell0d service is running"
                else
                    log_warn "cell0d service not running (may not be enabled)"
                fi
                
                if systemctl --user is-enabled cell0d &>/dev/null; then
                    log_pass "cell0d service is enabled"
                else
                    log_warn "cell0d service not enabled"
                fi
            else
                log_warn "systemctl not available"
            fi
            ;;
        Darwin)
            if launchctl list | grep -q "io.cell0.cell0d"; then
                log_pass "cell0d service is loaded"
            else
                log_warn "cell0d service not loaded"
            fi
            ;;
        *)
            log_warn "Unknown OS: $os"
            ;;
    esac
}

# ============================================================================
# Test 7: Network Connectivity
# ============================================================================
test_network() {
    log_section "Testing Network Connectivity"
    
    # Check if Cell 0 is responding
    local api_url="${CELL0_URL:-http://localhost:8080}"
    
    if curl -fsS --max-time 5 "${api_url}/health" &>/dev/null; then
        log_pass "Cell 0 API responding at $api_url"
        
        # Get version info
        local version_info=$(curl -fsS --max-time 5 "${api_url}/version" 2>/dev/null || echo "unknown")
        log_info "Version info: $version_info"
    else
        log_warn "Cell 0 API not responding at $api_url (service may not be running)"
    fi
    
    # Test external connectivity
    if curl -fsS --max-time 5 https://github.com &>/dev/null; then
        log_pass "External connectivity OK"
    else
        log_warn "No external connectivity"
    fi
}

# ============================================================================
# Test 8: Permissions
# ============================================================================
test_permissions() {
    log_section "Testing Permissions"
    
    # Check install directory ownership
    local install_owner=$(stat -c %U "$INSTALL_DIR" 2>/dev/null || stat -f %Su "$INSTALL_DIR" 2>/dev/null)
    local current_user=$(whoami)
    
    if [ "$install_owner" = "$current_user" ]; then
        log_pass "Install directory owned by current user"
    else
        log_warn "Install directory owned by: $install_owner (current: $current_user)"
    fi
    
    # Check config permissions
    if [ -d "$CONFIG_DIR" ]; then
        local config_perms=$(stat -c %a "$CONFIG_DIR" 2>/dev/null || stat -f %A "$CONFIG_DIR" 2>/dev/null)
        if [ "${config_perms:-755}" = "700" ] || [ "${config_perms:-755}" = "755" ]; then
            log_pass "Config directory permissions OK"
        else
            log_warn "Config directory permissions: $config_perms"
        fi
    fi
}

# ============================================================================
# Test 9: Disk Space
# ============================================================================
test_disk_space() {
    log_section "Testing Disk Space"
    
    local available=$(df -m "$INSTALL_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    
    if [ -n "$available" ]; then
        log_info "Available space: ${available}MB"
        
        if [ "$available" -gt 1000 ]; then
            log_pass "Sufficient disk space"
        elif [ "$available" -gt 500 ]; then
            log_warn "Low disk space: ${available}MB"
        else
            log_fail "Critical disk space: ${available}MB"
        fi
    else
        log_warn "Could not determine disk space"
    fi
}

# ============================================================================
# Test 10: Shell Integration
# ============================================================================
test_shell_integration() {
    log_section "Testing Shell Integration"
    
    local current_shell="${SHELL##*/}"
    local shell_rc=""
    
    case "$current_shell" in
        bash) shell_rc="$HOME/.bashrc" ;;
        zsh) shell_rc="$HOME/.zshrc" ;;
        fish) shell_rc="$HOME/.config/fish/config.fish" ;;
        *) shell_rc="$HOME/.bashrc" ;;
    esac
    
    if [ -f "$shell_rc" ]; then
        if grep -q "CELL0_HOME" "$shell_rc" 2>/dev/null; then
            log_pass "Shell integration configured"
        else
            log_warn "Shell integration not found in $shell_rc"
        fi
    else
        log_warn "Shell config not found: $shell_rc"
    fi
    
    # Check PATH
    if echo "$PATH" | grep -q "$INSTALL_DIR/bin"; then
        log_pass "Cell 0 in PATH"
    else
        log_warn "Cell 0 not in current PATH"
    fi
}

# ============================================================================
# Summary
# ============================================================================
print_summary() {
    echo
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Verification Summary${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    
    local total=$((TESTS_PASSED + TESTS_FAILED + TESTS_WARNINGS))
    
    echo "  Total tests:  $total"
    echo -e "  ${GREEN}Passed:${NC}     $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC}     $TESTS_FAILED"
    echo -e "  ${YELLOW}Warnings:${NC}   $TESTS_WARNINGS"
    echo
    
    if [ $TESTS_FAILED -eq 0 ]; then
        if [ $TESTS_WARNINGS -eq 0 ]; then
            echo -e "  ${GREEN}${BOLD}✓ All tests passed!${NC}"
        else
            echo -e "  ${YELLOW}${BOLD}✓ Tests passed with warnings${NC}"
        fi
        return 0
    else
        echo -e "  ${RED}${BOLD}✗ Some tests failed${NC}"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================
show_help() {
    cat << EOF
Cell 0 OS - Installation Verification

Usage: verify-installation.sh [OPTIONS]

Options:
    -h, --help          Show this help message
    -q, --quick         Quick verification (basic tests only)
    -v, --verbose       Verbose output
    --dir DIR           Set installation directory
    --json              Output JSON format

Tests:
    - directories      Directory structure
    - binaries         Binary files
    - configuration    Config files
    - python           Python environment
    - dependencies     Required packages
    - services         System services
    - network          Network connectivity
    - permissions      File permissions
    - disk             Disk space
    - shell            Shell integration
EOF
}

main() {
    local quick_mode=false
    local verbose=false
    local json_output=false
    
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
            -v|--verbose)
                verbose=true
                shift
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --json)
                json_output=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [ "$json_output" = true ]; then
        # JSON output mode
        echo '{'
        echo '  "version": "'$CELL0_VERSION'",'
        echo '  "timestamp": "'$(date -Iseconds)'",'
        echo '  "install_dir": "'$INSTALL_DIR'",'
        echo '  "tests": {'
        echo '    "pending": "implement JSON output"'
        echo '  }'
        echo '}'
        exit 0
    fi
    
    echo -e "${CYAN}${BOLD}"
    echo 'Cell 0 OS - Installation Verification'
    echo "Version: $CELL0_VERSION"
    echo -e "${NC}"
    
    # Run tests
    test_directories
    test_binaries
    test_configuration
    test_python_env
    test_dependencies
    test_services
    test_network
    test_permissions
    test_disk_space
    test_shell_integration
    
    # Print summary
    print_summary
    exit $?
}

main "$@"
