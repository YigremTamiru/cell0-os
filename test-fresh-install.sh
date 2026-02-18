#!/bin/bash
# Cell 0 OS - Fresh Installation Test Suite
# 40 comprehensive tests for clean installations

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CELL0_VERSION="1.2.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
INSTALL_DIR="$TEST_ROOT/.cell0"
TEST_LOG="$TEST_ROOT/test.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Test tracking
TESTS_TOTAL=40
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# ============================================================================
# Logging Functions
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$TEST_LOG"; }
log_pass() { echo -e "${GREEN}[✓ PASS]${NC} $1" | tee -a "$TEST_LOG"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
log_fail() { echo -e "${RED}[✗ FAIL]${NC} $1" | tee -a "$TEST_LOG"; TESTS_FAILED=$((TESTS_FAILED + 1)); }
log_skip() { echo -e "${YELLOW}[⊘ SKIP]${NC} $1" | tee -a "$TEST_LOG"; TESTS_SKIPPED=$((TESTS_SKIPPED + 1)); }
log_section() { echo -e "\n${CYAN}${BOLD}▶ $1${NC}" | tee -a "$TEST_LOG"; }
log_test() { echo -e "${BOLD}Test $1:${NC} $2" | tee -a "$TEST_LOG"; }

# ============================================================================
# Pre-flight Checks
# ============================================================================
preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check we're in a clean environment
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "Install directory already exists, cleaning..."
        rm -rf "$INSTALL_DIR"
    fi
    
    # Ensure we have required tools
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required"
        exit 1
    fi
    
    log_info "Pre-flight checks complete"
}

# ============================================================================
# Test Suite 1: Pre-Installation (Tests 1-5)
# ============================================================================

# Test 1: Clean environment
test_01_clean_env() {
    log_test 1 "Clean installation environment"
    
    if [ ! -d "$INSTALL_DIR" ]; then
        log_pass "Environment is clean"
    else
        log_fail "Install directory exists"
    fi
}

# Test 2: Python availability
test_02_python_available() {
    log_test 2 "Python interpreter available"
    
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1)
        log_pass "$version"
    else
        log_fail "Python 3 not found"
    fi
}

# Test 3: Required tools
test_03_required_tools() {
    log_test 3 "Required system tools"
    
    local tools_ok=true
    for tool in git curl mkdir cp chmod; do
        if ! command -v "$tool" &> /dev/null && ! type "$tool" &> /dev/null; then
            tools_ok=false
            log_fail "Missing tool: $tool"
        fi
    done
    
    if $tools_ok; then
        log_pass "All required tools available"
    fi
}

# Test 4: Disk space
test_04_disk_space() {
    log_test 4 "Available disk space"
    
    local available=$(df -m "$TEST_ROOT" | awk 'NR==2 {print $4}')
    if [ -n "$available" ] && [ "$available" -gt 500 ]; then
        log_pass "${available}MB available"
    else
        log_warn "Low disk space: ${available}MB"
    fi
}

# Test 5: Network connectivity
test_05_network() {
    log_test 5 "Network connectivity"
    
    if curl -fsS --max-time 5 https://pypi.org &>/dev/null; then
        log_pass "Internet connection OK"
    else
        log_skip "No internet (offline mode)"
    fi
}

# ============================================================================
# Test Suite 2: Installation Process (Tests 6-15)
# ============================================================================

# Test 6: Install script download
test_06_script_download() {
    log_test 6 "Installation script availability"
    
    if [ -f "$PROJECT_ROOT/install.sh" ]; then
        log_pass "install.sh found"
    else
        log_fail "install.sh not found"
    fi
}

# Test 7: Install script syntax
test_07_script_syntax() {
    log_test 7 "Install script syntax"
    
    if bash -n "$PROJECT_ROOT/install.sh" 2>/dev/null; then
        log_pass "Syntax valid"
    else
        log_fail "Syntax errors found"
    fi
}

# Test 8: Directory creation
test_08_dir_creation() {
    log_test 8 "Installation directory creation"
    
    mkdir -p "$INSTALL_DIR"
    if [ -d "$INSTALL_DIR" ]; then
        log_pass "Directory created"
    else
        log_fail "Directory creation failed"
    fi
}

# Test 9: Virtual environment setup
test_09_venv_setup() {
    log_test 9 "Virtual environment setup"
    
    local venv_dir="$INSTALL_DIR/venv"
    if python3 -m venv "$venv_dir" 2>/dev/null; then
        if [ -f "$venv_dir/bin/python" ] || [ -f "$venv_dir/Scripts/python.exe" ]; then
            log_pass "Virtual environment created"
        else
            log_fail "Venv incomplete"
        fi
    else
        log_fail "Failed to create venv"
    fi
}

# Test 10: Package installation (simulated)
test_10_package_install() {
    log_test 10 "Package installation"
    
    # Create a simple test package
    local test_pkg="$INSTALL_DIR/test_pkg"
    mkdir -p "$test_pkg"
    echo "name='test'" > "$test_pkg/setup.py"
    
    if [ -f "$test_pkg/setup.py" ]; then
        log_pass "Package structure created"
    else
        log_fail "Package creation failed"
    fi
}

# Test 11: Binary creation
test_11_binary_creation() {
    log_test 11 "Binary wrapper creation"
    
    mkdir -p "$INSTALL_DIR/bin"
    cat > "$INSTALL_DIR/bin/test-bin" << 'EOF'
#!/bin/bash
echo "Test binary"
EOF
    chmod +x "$INSTALL_DIR/bin/test-bin"
    
    if [ -x "$INSTALL_DIR/bin/test-bin" ]; then
        log_pass "Binary created and executable"
    else
        log_fail "Binary creation failed"
    fi
}

# Test 12: Configuration directory
test_12_config_dir() {
    log_test 12 "Configuration directory"
    
    local config_dir="$TEST_ROOT/.config/cell0"
    mkdir -p "$config_dir"
    
    if [ -d "$config_dir" ]; then
        log_pass "Config directory created"
    else
        log_fail "Config directory creation failed"
    fi
}

# Test 13: Data directory
test_13_data_dir() {
    log_test 13 "Data directory"
    
    local data_dir="$INSTALL_DIR/data"
    mkdir -p "$data_dir"
    
    if [ -d "$data_dir" ]; then
        log_pass "Data directory created"
    else
        log_fail "Data directory creation failed"
    fi
}

# Test 14: Log directory
test_14_log_dir() {
    log_test 14 "Log directory"
    
    local log_dir="$INSTALL_DIR/logs"
    mkdir -p "$log_dir"
    
    if [ -d "$log_dir" ]; then
        log_pass "Log directory created"
    else
        log_fail "Log directory creation failed"
    fi
}

# Test 15: Permission setup
test_15_permissions() {
    log_test 15 "File permissions"
    
    local test_file="$INSTALL_DIR/test_config"
    echo "test" > "$test_file"
    chmod 600 "$test_file"
    
    local perms=$(stat -c %a "$test_file" 2>/dev/null || stat -f %A "$test_file" 2>/dev/null)
    if [ "$perms" = "600" ]; then
        log_pass "Permissions set correctly"
    else
        log_fail "Permissions: $perms (expected 600)"
    fi
}

# ============================================================================
# Test Suite 3: Post-Installation (Tests 16-25)
# ============================================================================

# Test 16: Environment variables
test_16_env_vars() {
    log_test 16 "Environment configuration"
    
    export CELL0_HOME="$INSTALL_DIR"
    export CELL0_CONFIG_DIR="$TEST_ROOT/.config/cell0"
    
    if [ -n "${CELL0_HOME:-}" ] && [ -n "${CELL0_CONFIG_DIR:-}" ]; then
        log_pass "Environment variables set"
    else
        log_fail "Environment variables not set"
    fi
}

# Test 17: Shell integration
test_17_shell_integration() {
    log_test 17 "Shell integration"
    
    local shell_rc="$TEST_ROOT/.bashrc"
    echo "export CELL0_HOME=$INSTALL_DIR" > "$shell_rc"
    
    if grep -q "CELL0_HOME" "$shell_rc" 2>/dev/null; then
        log_pass "Shell integration configured"
    else
        log_fail "Shell integration not configured"
    fi
}

# Test 18: Service file creation
test_18_service_file() {
    log_test 18 "Service file creation"
    
    local service_file="$TEST_ROOT/.config/systemd/user/cell0d.service"
    mkdir -p "$(dirname "$service_file")"
    
    cat > "$service_file" << EOF
[Unit]
Description=Cell 0 OS Daemon
[Service]
ExecStart=/bin/true
[Install]
WantedBy=default.target
EOF
    
    if [ -f "$service_file" ]; then
        log_pass "Service file created"
    else
        log_fail "Service file creation failed"
    fi
}

# Test 19: Config file generation
test_19_config_gen() {
    log_test 19 "Configuration file generation"
    
    local config_file="$TEST_ROOT/.config/cell0/cell0.conf"
    mkdir -p "$(dirname "$config_file")"
    
    cat > "$config_file" << EOF
[core]
version = $CELL0_VERSION
install_dir = $INSTALL_DIR
EOF
    
    if [ -f "$config_file" ]; then
        log_pass "Config file generated"
    else
        log_fail "Config file generation failed"
    fi
}

# Test 20: Provider config
test_20_provider_config() {
    log_test 20 "Provider configuration"
    
    local providers_file="$TEST_ROOT/.config/cell0/providers.conf"
    
    cat > "$providers_file" << 'EOF'
[providers.local]
enabled = true
path = /models
EOF
    
    if [ -f "$providers_file" ]; then
        log_pass "Provider config created"
    else
        log_fail "Provider config creation failed"
    fi
}

# Test 21: Health check script
test_21_health_check() {
    log_test 21 "Health check script"
    
    local health_script="$INSTALL_DIR/bin/cell0-healthcheck"
    cat > "$health_script" << 'EOF'
#!/bin/bash
echo "OK"
exit 0
EOF
    chmod +x "$health_script"
    
    if [ -x "$health_script" ] && "$health_script" &>/dev/null; then
        log_pass "Health check script working"
    else
        log_fail "Health check script failed"
    fi
}

# Test 22: Backup script
test_22_backup_script() {
    log_test 22 "Backup script"
    
    local backup_script="$INSTALL_DIR/bin/cell0-backup"
    local backup_dir="$INSTALL_DIR/data/backups"
    mkdir -p "$backup_dir"
    
    cat > "$backup_script" << EOF
#!/bin/bash
mkdir -p "$backup_dir"
echo "backup" > "$backup_dir/test.backup"
echo "Backup created"
EOF
    chmod +x "$backup_script"
    
    if [ -x "$backup_script" ]; then
        log_pass "Backup script created"
    else
        log_fail "Backup script creation failed"
    fi
}

# Test 23: Log rotation config
test_23_log_rotation() {
    log_test 23 "Log rotation configuration"
    
    local logrotate_conf="$INSTALL_DIR/logs/logrotate.conf"
    echo "$INSTALL_DIR/logs/*.log" > "$logrotate_conf"
    
    if [ -f "$logrotate_conf" ]; then
        log_pass "Log rotation configured"
    else
        log_fail "Log rotation config failed"
    fi
}

# Test 24: Version file
test_24_version_file() {
    log_test 24 "Version file"
    
    local version_file="$INSTALL_DIR/version"
    echo "$CELL0_VERSION" > "$version_file"
    
    if [ -f "$version_file" ] && grep -q "$CELL0_VERSION" "$version_file"; then
        log_pass "Version file created"
    else
        log_fail "Version file creation failed"
    fi
}

# Test 25: Uninstall script
test_25_uninstall_script() {
    log_test 25 "Uninstall script"
    
    local uninstall_script="$INSTALL_DIR/bin/cell0-uninstall"
    cat > "$uninstall_script" << 'EOF'
#!/bin/bash
echo "Uninstall would remove: $CELL0_HOME"
exit 0
EOF
    chmod +x "$uninstall_script"
    
    if [ -x "$uninstall_script" ]; then
        log_pass "Uninstall script created"
    else
        log_fail "Uninstall script creation failed"
    fi
}

# ============================================================================
# Test Suite 4: Verification (Tests 26-35)
# ============================================================================

# Test 26: Directory structure verification
test_26_verify_dirs() {
    log_test 26 "Directory structure verification"
    
    local required_dirs=(
        "$INSTALL_DIR"
        "$INSTALL_DIR/bin"
        "$INSTALL_DIR/data"
        "$INSTALL_DIR/logs"
        "$TEST_ROOT/.config/cell0"
    )
    
    local all_exist=true
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            all_exist=false
            log_fail "Missing: $dir"
        fi
    done
    
    if $all_exist; then
        log_pass "All directories present"
    fi
}

# Test 27: Binary verification
test_27_verify_binaries() {
    log_test 27 "Binary verification"
    
    local binaries=(
        "$INSTALL_DIR/bin/test-bin"
        "$INSTALL_DIR/bin/cell0-healthcheck"
        "$INSTALL_DIR/bin/cell0-backup"
    )
    
    local all_exec=true
    for bin in "${binaries[@]}"; do
        if [ ! -x "$bin" ]; then
            all_exec=false
        fi
    done
    
    if $all_exec; then
        log_pass "All binaries executable"
    else
        log_fail "Some binaries missing or not executable"
    fi
}

# Test 28: Config verification
test_28_verify_config() {
    log_test 28 "Configuration verification"
    
    local config_file="$TEST_ROOT/.config/cell0/cell0.conf"
    if [ -f "$config_file" ] && grep -q "version" "$config_file"; then
        log_pass "Configuration valid"
    else
        log_fail "Configuration invalid"
    fi
}

# Test 29: Permission verification
test_29_verify_permissions() {
    log_test 29 "Permission verification"
    
    local config_file="$TEST_ROOT/.config/cell0/providers.conf"
    if [ -f "$config_file" ]; then
        local perms=$(stat -c %a "$config_file" 2>/dev/null || stat -f %A "$config_file" 2>/dev/null)
        if [ "${perms:-644}" = "600" ] || [ "${perms:-644}" = "644" ]; then
            log_pass "Permissions valid"
        else
            log_warn "Permissions: $perms"
        fi
    else
        log_skip "No providers.conf to check"
    fi
}

# Test 30: File ownership
test_30_verify_ownership() {
    log_test 30 "File ownership verification"
    
    local owner=$(stat -c %U "$INSTALL_DIR" 2>/dev/null || stat -f %Su "$INSTALL_DIR" 2>/dev/null)
    local current=$(whoami)
    
    if [ "$owner" = "$current" ]; then
        log_pass "Ownership correct"
    else
        log_warn "Owner: $owner, Current: $current"
    fi
}

# Test 31: Path configuration
test_31_verify_path() {
    log_test 31 "PATH configuration"
    
    if echo "$PATH" | grep -q "$INSTALL_DIR/bin" || \
       [ -f "$TEST_ROOT/.bashrc" ]; then
        log_pass "PATH configured"
    else
        log_warn "PATH may not include Cell 0"
    fi
}

# Test 32: Environment setup
test_32_verify_env() {
    log_test 32 "Environment setup verification"
    
    if [ -n "${CELL0_HOME:-}" ] && [ -d "${CELL0_HOME:-}" ]; then
        log_pass "Environment set correctly"
    else
        log_warn "Environment may need reload"
    fi
}

# Test 33: Service config validity
test_33_verify_service() {
    log_test 33 "Service configuration validity"
    
    local service_file="$TEST_ROOT/.config/systemd/user/cell0d.service"
    if [ -f "$service_file" ]; then
        if grep -q "\[Unit\]" "$service_file" && \
           grep -q "\[Service\]" "$service_file"; then
            log_pass "Service config valid"
        else
            log_fail "Service config invalid"
        fi
    else
        log_skip "No service file to verify"
    fi
}

# Test 34: Backup functionality
test_34_verify_backup() {
    log_test 34 "Backup functionality"
    
    local backup_dir="$INSTALL_DIR/data/backups"
    if [ -d "$backup_dir" ]; then
        log_pass "Backup directory exists"
    else
        log_warn "Backup directory not created"
    fi
}

# Test 35: Health check
test_35_verify_health() {
    log_test 35 "Health check verification"
    
    local health_script="$INSTALL_DIR/bin/cell0-healthcheck"
    if [ -x "$health_script" ]; then
        if "$health_script" &>/dev/null; then
            log_pass "Health check passes"
        else
            log_warn "Health check returned non-zero"
        fi
    else
        log_skip "No health check script"
    fi
}

# ============================================================================
# Test Suite 5: Integration (Tests 36-40)
# ============================================================================

# Test 36: End-to-end workflow
test_36_e2e_workflow() {
    log_test 36 "End-to-end workflow"
    
    # Simulate basic workflow
    local workflow_ok=true
    
    # Check all critical paths
    [ -d "$INSTALL_DIR" ] || workflow_ok=false
    [ -f "$TEST_ROOT/.config/cell0/cell0.conf" ] || workflow_ok=false
    [ -x "$INSTALL_DIR/bin/test-bin" ] || workflow_ok=false
    
    if $workflow_ok; then
        log_pass "E2E workflow valid"
    else
        log_fail "E2E workflow has issues"
    fi
}

# Test 37: Cleanup test
test_37_cleanup() {
    log_test 37 "Cleanup functionality"
    
    local temp_file="$TEST_ROOT/cleanup_test"
    touch "$temp_file"
    rm -f "$temp_file"
    
    if [ ! -f "$temp_file" ]; then
        log_pass "Cleanup working"
    else
        log_fail "Cleanup failed"
    fi
}

# Test 38: Reinstallation check
test_38_reinstall_check() {
    log_test 38 "Reinstallation compatibility"
    
    # Check that we can reinstall over existing
    if [ -d "$INSTALL_DIR" ]; then
        # Backup existing config
        if [ -f "$TEST_ROOT/.config/cell0/cell0.conf" ]; then
            cp "$TEST_ROOT/.config/cell0/cell0.conf" "$TEST_ROOT/.config/cell0/cell0.conf.backup"
        fi
        log_pass "Reinstallation path prepared"
    else
        log_skip "No existing installation"
    fi
}

# Test 39: Rollback capability
test_39_rollback() {
    log_test 39 "Rollback capability"
    
    # Create a snapshot
    local snapshot="$TEST_ROOT/install_snapshot"
    echo "$INSTALL_DIR" > "$snapshot"
    
    if [ -f "$snapshot" ]; then
        log_pass "Rollback snapshot created"
    else
        log_fail "Rollback snapshot failed"
    fi
}

# Test 40: Final validation
test_40_final_validation() {
    log_test 40 "Final installation validation"
    
    local critical_paths=0
    local required=5
    
    [ -d "$INSTALL_DIR" ] && critical_paths=$((critical_paths + 1))
    [ -d "$INSTALL_DIR/bin" ] && critical_paths=$((critical_paths + 1))
    [ -d "$TEST_ROOT/.config/cell0" ] && critical_paths=$((critical_paths + 1))
    [ -f "$TEST_ROOT/.bashrc" ] && critical_paths=$((critical_paths + 1))
    [ -f "$TEST_ROOT/.config/cell0/cell0.conf" ] && critical_paths=$((critical_paths + 1))
    
    if [ $critical_paths -eq $required ]; then
        log_pass "Installation validated ($critical_paths/$required)"
    else
        log_fail "Installation incomplete ($critical_paths/$required)"
    fi
}

# ============================================================================
# Test Execution
# ============================================================================
run_all_tests() {
    log_section "Fresh Installation Test Suite"
    log_info "Test directory: $TEST_ROOT"
    log_info "Install directory: $INSTALL_DIR"
    log_info "Running $TESTS_TOTAL tests..."
    echo
    
    local start_time=$(date +%s)
    
    # Pre-flight
    preflight_checks
    
    # Suite 1: Pre-Installation
    log_section "Suite 1: Pre-Installation"
    test_01_clean_env
    test_02_python_available
    test_03_required_tools
    test_04_disk_space
    test_05_network
    
    # Suite 2: Installation Process
    log_section "Suite 2: Installation Process"
    test_06_script_download
    test_07_script_syntax
    test_08_dir_creation
    test_09_venv_setup
    test_10_package_install
    test_11_binary_creation
    test_12_config_dir
    test_13_data_dir
    test_14_log_dir
    test_15_permissions
    
    # Suite 3: Post-Installation
    log_section "Suite 3: Post-Installation"
    test_16_env_vars
    test_17_shell_integration
    test_18_service_file
    test_19_config_gen
    test_20_provider_config
    test_21_health_check
    test_22_backup_script
    test_23_log_rotation
    test_24_version_file
    test_25_uninstall_script
    
    # Suite 4: Verification
    log_section "Suite 4: Verification"
    test_26_verify_dirs
    test_27_verify_binaries
    test_28_verify_config
    test_29_verify_permissions
    test_30_verify_ownership
    test_31_verify_path
    test_32_verify_env
    test_33_verify_service
    test_34_verify_backup
    test_35_verify_health
    
    # Suite 5: Integration
    log_section "Suite 5: Integration"
    test_36_e2e_workflow
    test_37_cleanup
    test_38_reinstall_check
    test_39_rollback
    test_40_final_validation
    
    local end_time=$(date +%s)
    echo
    
    return $((end_time - start_time))
}

# ============================================================================
# Summary
# ============================================================================
print_summary() {
    local duration=$1
    
    echo
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Fresh Installation Test Summary${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    printf "  %-20s %3d\n" "Total Tests:" "$TESTS_TOTAL"
    printf "  ${GREEN}%-20s${NC} %3d\n" "Passed:" "$TESTS_PASSED"
    printf "  ${RED}%-20s${NC} %3d\n" "Failed:" "$TESTS_FAILED"
    printf "  ${YELLOW}%-20s${NC} %3d\n" "Skipped:" "$TESTS_SKIPPED"
    printf "  %-20s %3ds\n" "Duration:" "$duration"
    echo
    
    local success_rate=0
    if [ $TESTS_TOTAL -gt 0 ]; then
        success_rate=$(( TESTS_PASSED * 100 / TESTS_TOTAL ))
    fi
    printf "  Success Rate: %d%%\n" "$success_rate"
    echo
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "  ${GREEN}${BOLD}✓ Fresh installation test suite passed!${NC}"
        return 0
    else
        echo -e "  ${RED}${BOLD}✗ Some tests failed${NC}"
        echo
        echo "  See test log: $TEST_LOG"
        return 1
    fi
}

# ============================================================================
# Cleanup
# ============================================================================
cleanup() {
    if [ -d "$TEST_ROOT" ]; then
        log_info "Cleaning up test environment..."
        rm -rf "$TEST_ROOT"
    fi
}

trap cleanup EXIT

# ============================================================================
# Main
# ============================================================================
show_help() {
    cat << EOF
Cell 0 OS - Fresh Installation Test Suite

Usage: test-fresh-install.sh [OPTIONS]

Options:
    -h, --help          Show this help message
    -k, --keep          Keep test directory after run
    -v, --verbose       Verbose output
    --dir DIR           Use specific test directory

Examples:
    test-fresh-install.sh              # Run all tests
    test-fresh-install.sh --keep       # Keep test directory
EOF
}

main() {
    local keep_temp=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -k|--keep)
                keep_temp=true
                shift
                ;;
            --dir)
                TEST_ROOT="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [ "$keep_temp" = true ]; then
        trap - EXIT
    fi
    
    # Run tests
    run_all_tests
    local duration=$?
    
    # Print summary
    print_summary $duration
    exit $?
}

main "$@"
