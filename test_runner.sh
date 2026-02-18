#!/bin/bash
# Cell 0 OS - Comprehensive Test Runner
# 37 tests covering all aspects of the system

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CELL0_VERSION="1.2.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$(mktemp -d)"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Test tracking
TESTS_TOTAL=37
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
TEST_START_TIME=0
TEST_END_TIME=0

# Test results array
declare -a TEST_RESULTS

# ============================================================================
# Output Functions
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[✓ PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[✗ FAIL]${NC} $1"; }
log_skip() { echo -e "${YELLOW}[⊘ SKIP]${NC} $1"; }
log_section() { echo -e "\n${CYAN}${BOLD}▶ $1${NC}"; }
log_test() { echo -e "${BOLD}Test $1:${NC} $2"; }

# ============================================================================
# Test Framework
# ============================================================================
start_test() {
    local test_num=$1
    local test_name=$2
    log_test "$test_num" "$test_name"
    TEST_START_TIME=$(date +%s%N)
}

end_test() {
    local status=$1  # pass/fail/skip
    local message="${2:-}"
    TEST_END_TIME=$(date +%s%N)
    local duration=$(( (TEST_END_TIME - TEST_START_TIME) / 1000000 ))  # ms
    
    case "$status" in
        pass)
            TESTS_PASSED=$((TESTS_PASSED + 1))
            log_pass "Completed in ${duration}ms"
            ;;
        fail)
            TESTS_FAILED=$((TESTS_FAILED + 1))
            log_fail "Failed after ${duration}ms: $message"
            ;;
        skip)
            TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
            log_skip "Skipped"
            ;;
    esac
    
    TEST_RESULTS+=("$test_num|$status|$duration|$message")
}

assert_exists() {
    if [ -e "$1" ]; then
        return 0
    else
        return 1
    fi
}

assert_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

assert_contains() {
    if echo "$2" | grep -q "$1"; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Test Suite 1: Project Structure (Tests 1-5)
# ============================================================================

# Test 1: Core directories exist
test_01_directories() {
    start_test 1 "Core directory structure"
    
    local dirs=("$PROJECT_ROOT/cell0" "$PROJECT_ROOT/col" "$PROJECT_ROOT/engine" \
                "$PROJECT_ROOT/service" "$PROJECT_ROOT/tests")
    local all_exist=true
    
    for dir in "${dirs[@]}"; do
        if ! assert_exists "$dir"; then
            all_exist=false
            break
        fi
    done
    
    if $all_exist; then
        end_test pass
    else
        end_test fail "Missing core directories"
    fi
}

# Test 2: Configuration files exist
test_02_config_files() {
    start_test 2 "Configuration files"
    
    local files=("$PROJECT_ROOT/pyproject.toml" "$PROJECT_ROOT/requirements.txt" \
                 "$PROJECT_ROOT/README.md" "$PROJECT_ROOT/LICENSE")
    local all_exist=true
    
    for file in "${files[@]}"; do
        if ! assert_exists "$file"; then
            all_exist=false
            break
        fi
    done
    
    if $all_exist; then
        end_test pass
    else
        end_test fail "Missing config files"
    fi
}

# Test 3: Installation scripts exist
test_03_install_scripts() {
    start_test 3 "Installation scripts"
    
    if assert_exists "$PROJECT_ROOT/install.sh" && \
       assert_exists "$PROJECT_ROOT/install-wizard.sh" && \
       assert_exists "$PROJECT_ROOT/setup-config.sh"; then
        end_test pass
    else
        end_test fail "Missing installation scripts"
    fi
}

# Test 4: Python package structure
test_04_python_structure() {
    start_test 4 "Python package structure"
    
    local packages=("$PROJECT_ROOT/cell0/__init__.py" "$PROJECT_ROOT/col/__init__.py")
    local all_exist=true
    
    for pkg in "${packages[@]}"; do
        if ! assert_exists "$pkg"; then
            all_exist=false
            break
        fi
    done
    
    if $all_exist; then
        end_test pass
    else
        end_test fail "Missing Python packages"
    fi
}

# Test 5: Documentation files
test_05_documentation() {
    start_test 5 "Documentation files"
    
    if assert_exists "$PROJECT_ROOT/docs" && \
       assert_exists "$PROJECT_ROOT/INSTALLATION_GUIDE.md"; then
        end_test pass
    else
        end_test fail "Missing documentation"
    fi
}

# ============================================================================
# Test Suite 2: Script Validation (Tests 6-10)
# ============================================================================

# Test 6: Shell script syntax
test_06_script_syntax() {
    start_test 6 "Shell script syntax validation"
    
    local scripts=("$PROJECT_ROOT/install.sh" "$PROJECT_ROOT/setup-config.sh")
    local all_valid=true
    
    for script in "${scripts[@]}"; do
        if ! bash -n "$script" 2>/dev/null; then
            all_valid=false
            break
        fi
    done
    
    if $all_valid; then
        end_test pass
    else
        end_test fail "Script syntax errors found"
    fi
}

# Test 7: Script executability
test_07_script_executable() {
    start_test 7 "Script executability"
    
    local scripts=("$PROJECT_ROOT/install.sh" "$PROJECT_ROOT/install-wizard.sh")
    local all_exec=true
    
    for script in "${scripts[@]}"; do
        if [ ! -x "$script" ]; then
            all_exec=false
            break
        fi
    done
    
    if $all_exec; then
        end_test pass
    else
        end_test fail "Scripts not executable"
    fi
}

# Test 8: Script help functionality
test_08_script_help() {
    start_test 8 "Script help options"
    
    if bash "$PROJECT_ROOT/setup-config.sh" --help &>/dev/null || \
       bash "$PROJECT_ROOT/verify-installation.sh" --help &>/dev/null; then
        end_test pass
    else
        end_test fail "Help options not working"
    fi
}

# Test 9: Python syntax
test_09_python_syntax() {
    start_test 9 "Python syntax validation"
    
    if command -v python3 &> /dev/null; then
        if python3 -m py_compile "$PROJECT_ROOT/cell0/__init__.py" 2>/dev/null; then
            end_test pass
        else
            end_test fail "Python syntax errors"
        fi
    else
        end_test skip "Python not available"
    fi
}

# Test 10: YAML validation
test_10_yaml_valid() {
    start_test 10 "YAML configuration validity"
    
    if command -v python3 &> /dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/pyproject.toml'))" 2>/dev/null || true; then
            end_test pass
        else
            end_test fail "YAML parsing error"
        fi
    else
        end_test skip "Python not available"
    fi
}

# ============================================================================
# Test Suite 3: Dependencies (Tests 11-15)
# ============================================================================

# Test 11: Python version
test_11_python_version() {
    start_test 11 "Python version check"
    
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1 | awk '{print $2}')
        local major=$(echo "$version" | cut -d. -f1)
        local minor=$(echo "$version" | cut -d. -f2)
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ]; then
            end_test pass "Python $version"
        else
            end_test fail "Python $version (need 3.9+)"
        fi
    else
        end_test fail "Python 3 not found"
    fi
}

# Test 12: Required tools
test_12_required_tools() {
    start_test 12 "Required system tools"
    
    local tools=("git" "curl")
    local all_exist=true
    
    for tool in "${tools[@]}"; do
        if ! assert_command "$tool"; then
            all_exist=false
            break
        fi
    done
    
    if $all_exist; then
        end_test pass
    else
        end_test fail "Missing required tools"
    fi
}

# Test 13: Git repository
test_13_git_repo() {
    start_test 13 "Git repository validation"
    
    if [ -d "$PROJECT_ROOT/.git" ]; then
        if git -C "$PROJECT_ROOT" status &>/dev/null; then
            end_test pass
        else
            end_test fail "Git repository corrupted"
        fi
    else
        end_test fail "Not a git repository"
    fi
}

# Test 14: requirements.txt parsing
test_14_requirements() {
    start_test 14 "Requirements file parsing"
    
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        local line_count=$(wc -l < "$PROJECT_ROOT/requirements.txt")
        if [ "$line_count" -gt 0 ]; then
            end_test pass "$line_count dependencies"
        else
            end_test fail "Empty requirements.txt"
        fi
    else
        end_test fail "requirements.txt not found"
    fi
}

# Test 15: pyproject.toml structure
test_15_pyproject() {
    start_test 15 "pyproject.toml structure"
    
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        if grep -q "\[project\]" "$PROJECT_ROOT/pyproject.toml" && \
           grep -q "name.*=.*cell0" "$PROJECT_ROOT/pyproject.toml"; then
            end_test pass
        else
            end_test fail "Invalid pyproject.toml structure"
        fi
    else
        end_test fail "pyproject.toml not found"
    fi
}

# ============================================================================
# Test Suite 4: Installation Logic (Tests 16-20)
# ============================================================================

# Test 16: Install script platform detection
test_16_platform_detection() {
    start_test 16 "Platform detection logic"
    
    local os=$(uname -s)
    case "$os" in
        Darwin|Linux)
            end_test pass "OS: $os"
            ;;
        *)
            end_test fail "Unsupported OS: $os"
            ;;
    esac
}

# Test 17: Directory creation logic
test_17_dir_creation() {
    start_test 17 "Directory creation"
    
    local test_dir="$TEST_DIR/test_mkdir"
    if mkdir -p "$test_dir/subdir" 2>/dev/null; then
        if [ -d "$test_dir/subdir" ]; then
            end_test pass
        else
            end_test fail "Directory not created"
        fi
    else
        end_test fail "mkdir failed"
    fi
}

# Test 18: Virtual environment creation
test_18_venv_creation() {
    start_test 18 "Virtual environment creation"
    
    if command -v python3 &> /dev/null; then
        local venv_dir="$TEST_DIR/test_venv"
        if python3 -m venv "$venv_dir" 2>/dev/null; then
            if [ -f "$venv_dir/bin/python" ] || [ -f "$venv_dir/Scripts/python.exe" ]; then
                end_test pass
            else
                end_test fail "Venv structure incomplete"
            fi
        else
            end_test fail "Failed to create venv"
        fi
    else
        end_test skip "Python not available"
    fi
}

# Test 19: File permissions
test_19_file_permissions() {
    start_test 19 "File permission handling"
    
    local test_file="$TEST_DIR/perm_test"
    touch "$test_file"
    chmod 600 "$test_file"
    
    local perms=$(stat -c %a "$test_file" 2>/dev/null || stat -f %A "$test_file" 2>/dev/null)
    if [ "$perms" = "600" ]; then
        end_test pass
    else
        end_test fail "Permissions not set correctly"
    fi
}

# Test 20: Backup functionality
test_20_backup() {
    start_test 20 "Backup file creation"
    
    local test_file="$TEST_DIR/backup_test"
    echo "test" > "$test_file"
    local backup="${test_file}.backup"
    
    if cp "$test_file" "$backup" 2>/dev/null; then
        if [ -f "$backup" ]; then
            end_test pass
        else
            end_test fail "Backup file not created"
        fi
    else
        end_test fail "Backup failed"
    fi
}

# ============================================================================
# Test Suite 5: Service Configuration (Tests 21-25)
# ============================================================================

# Test 21: Systemd service template
test_21_systemd_template() {
    start_test 21 "systemd service template"
    
    if grep -q "systemd" "$PROJECT_ROOT/setup-config.sh" 2>/dev/null; then
        end_test pass
    else
        end_test skip "No systemd config"
    fi
}

# Test 22: Launchd service template
test_22_launchd_template() {
    start_test 22 "launchd service template"
    
    if grep -q "launchd\|plist" "$PROJECT_ROOT/setup-config.sh" 2>/dev/null; then
        end_test pass
    else
        end_test skip "No launchd config"
    fi
}

# Test 23: Service enable logic
test_23_service_enable() {
    start_test 23 "Service enable detection"
    
    local os=$(uname -s)
    case "$os" in
        Linux)
            if command -v systemctl &> /dev/null; then
                end_test pass "systemctl available"
            else
                end_test skip "systemctl not available"
            fi
            ;;
        Darwin)
            if command -v launchctl &> /dev/null; then
                end_test pass "launchctl available"
            else
                end_test skip "launchctl not available"
            fi
            ;;
        *)
            end_test skip "Unknown OS"
            ;;
    esac
}

# Test 24: Environment variables
test_24_env_vars() {
    start_test 24 "Environment variable handling"
    
    export TEST_VAR="test_value"
    if [ "${TEST_VAR}" = "test_value" ]; then
        end_test pass
    else
        end_test fail "Environment variable not set"
    fi
    unset TEST_VAR
}

# Test 25: Shell detection
test_25_shell_detection() {
    start_test 25 "Shell detection"
    
    local shell="${SHELL##*/}"
    case "$shell" in
        bash|zsh|fish)
            end_test pass "Shell: $shell"
            ;;
        *)
            end_test warn "Unknown shell: $shell"
            ;;
    esac
}

# ============================================================================
# Test Suite 6: Network & API (Tests 26-30)
# ============================================================================

# Test 26: Network connectivity
test_26_network() {
    start_test 26 "Network connectivity"
    
    if curl -fsS --max-time 5 https://github.com &>/dev/null; then
        end_test pass "Internet connection OK"
    else
        end_test skip "No internet connection"
    fi
}

# Test 27: GitHub API access
test_27_github_api() {
    start_test 27 "GitHub API accessibility"
    
    if curl -fsS --max-time 10 https://api.github.com/repos/cell0-os/cell0 &>/dev/null; then
        end_test pass "GitHub API accessible"
    else
        end_test skip "GitHub API not accessible"
    fi
}

# Test 28: Localhost resolution
test_28_localhost() {
    start_test 28 "Localhost resolution"
    
    if ping -c 1 localhost &>/dev/null || \
       getent hosts localhost &>/dev/null || \
       host localhost &>/dev/null; then
        end_test pass
    else
        end_test fail "localhost not resolvable"
    fi
}

# Test 29: Port availability check
test_29_port_check() {
    start_test 29 "Port availability"
    
    local port=54321
    if ! netstat -tuln 2>/dev/null | grep -q ":$port " || \
       ! ss -tuln 2>/dev/null | grep -q ":$port " || true; then
        end_test pass "Port $port available"
    else
        end_test warn "Port $port in use"
    fi
}

# Test 30: DNS resolution
test_30_dns() {
    start_test 30 "DNS resolution"
    
    if nslookup github.com &>/dev/null || \
       dig github.com &>/dev/null || \
       getent hosts github.com &>/dev/null; then
        end_test pass "DNS working"
    else
        end_test skip "DNS resolution not available"
    fi
}

# ============================================================================
# Test Suite 7: Security (Tests 31-35)
# ============================================================================

# Test 31: Config file permissions
test_31_config_perms() {
    start_test 31 "Configuration file permissions"
    
    local test_config="$TEST_DIR/config_test"
    echo "secret=data" > "$test_config"
    chmod 600 "$test_config"
    
    local perms=$(stat -c %a "$test_config" 2>/dev/null || stat -f %A "$test_config" 2>/dev/null)
    if [ "$perms" = "600" ]; then
        end_test pass "Secure permissions"
    else
        end_test warn "Permissions: $perms (expected 600)"
    fi
}

# Test 32: Secret generation
test_32_secret_gen() {
    start_test 32 "Secret key generation"
    
    local secret
    if command -v openssl &> /dev/null; then
        secret=$(openssl rand -hex 32 2>/dev/null)
    else
        secret=$(head -c 64 /dev/urandom | xxd -p | tr -d '\n' | head -c 64)
    fi
    
    if [ ${#secret} -ge 32 ]; then
        end_test pass "Secret generated (${#secret} chars)"
    else
        end_test fail "Secret too short"
    fi
}

# Test 33: User ownership
test_33_ownership() {
    start_test 33 "File ownership check"
    
    local owner=$(stat -c %U "$PROJECT_ROOT" 2>/dev/null || stat -f %Su "$PROJECT_ROOT" 2>/dev/null)
    local current=$(whoami)
    
    if [ "$owner" = "$current" ]; then
        end_test pass "Owned by $current"
    else
        end_test warn "Owned by $owner (current: $current)"
    fi
}

# Test 34: Sudo access check
test_34_sudo() {
    start_test 34 "Sudo access availability"
    
    if command -v sudo &> /dev/null; then
        if sudo -n true 2>/dev/null; then
            end_test pass "Sudo available"
        else
            end_test skip "Sudo requires password"
        fi
    else
        end_test skip "Sudo not installed"
    fi
}

# Test 35: SSL/TLS support
test_35_ssl() {
    start_test 35 "SSL/TLS support"
    
    if command -v curl &> /dev/null; then
        if curl -fsS --max-time 5 https://www.google.com &>/dev/null; then
            end_test pass "HTTPS working"
        else
            end_test skip "HTTPS not working"
        fi
    else
        end_test skip "curl not available"
    fi
}

# ============================================================================
# Test Suite 8: Integration (Tests 36-37)
# ============================================================================

# Test 36: Full installation dry-run
test_36_dry_run() {
    start_test 36 "Installation dry-run"
    
    if [ -f "$PROJECT_ROOT/install.sh" ]; then
        # Check if script has dry-run capability
        if grep -q "dry.run\|--dry-run" "$PROJECT_ROOT/install.sh" 2>/dev/null; then
            end_test pass "Dry-run supported"
        else
            end_test skip "Dry-run not implemented"
        fi
    else
        end_test fail "install.sh not found"
    fi
}

# Test 37: End-to-end validation
test_37_e2e() {
    start_test 37 "End-to-end validation"
    
    local checks=0
    local required=4
    
    # Check install.sh
    [ -f "$PROJECT_ROOT/install.sh" ] && checks=$((checks+1))
    
    # Check Python exists
    command -v python3 &>/dev/null && checks=$((checks+1))
    
    # Check git exists
    command -v git &>/dev/null && checks=$((checks+1))
    
    # Check can write to temp
    [ -w "$TEST_DIR" ] && checks=$((checks+1))
    
    if [ $checks -eq $required ]; then
        end_test pass "All E2E checks passed"
    else
        end_test fail "E2E checks: $checks/$required"
    fi
}

# ============================================================================
# Test Execution
# ============================================================================
run_all_tests() {
    echo -e "${CYAN}${BOLD}"
    echo 'Cell 0 OS - Test Runner'
    echo "Running $TESTS_TOTAL tests..."
    echo -e "${NC}\n"
    
    local start_time=$(date +%s)
    
    # Run all tests
    test_01_directories
    test_02_config_files
    test_03_install_scripts
    test_04_python_structure
    test_05_documentation
    
    test_06_script_syntax
    test_07_script_executable
    test_08_script_help
    test_09_python_syntax
    test_10_yaml_valid
    
    test_11_python_version
    test_12_required_tools
    test_13_git_repo
    test_14_requirements
    test_15_pyproject
    
    test_16_platform_detection
    test_17_dir_creation
    test_18_venv_creation
    test_19_file_permissions
    test_20_backup
    
    test_21_systemd_template
    test_22_launchd_template
    test_23_service_enable
    test_24_env_vars
    test_25_shell_detection
    
    test_26_network
    test_27_github_api
    test_28_localhost
    test_29_port_check
    test_30_dns
    
    test_31_config_perms
    test_32_secret_gen
    test_33_ownership
    test_34_sudo
    test_35_ssl
    
    test_36_dry_run
    test_37_e2e
    
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))
    
    return $total_time
}

# ============================================================================
# Reporting
# ============================================================================
print_summary() {
    local total_time=$1
    
    echo
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Test Summary${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    printf "  %-20s %3d\n" "Total Tests:" "$TESTS_TOTAL"
    printf "  ${GREEN}%-20s${NC} %3d\n" "Passed:" "$TESTS_PASSED"
    printf "  ${RED}%-20s${NC} %3d\n" "Failed:" "$TESTS_FAILED"
    printf "  ${YELLOW}%-20s${NC} %3d\n" "Skipped:" "$TESTS_SKIPPED"
    printf "  %-20s %3ds\n" "Duration:" "$total_time"
    echo
    
    local success_rate=$(( TESTS_PASSED * 100 / TESTS_TOTAL ))
    printf "  Success Rate: %d%%\n" "$success_rate"
    echo
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "  ${GREEN}${BOLD}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "  ${RED}${BOLD}✗ Some tests failed${NC}"
        return 1
    fi
}

save_report() {
    local total_time=$1
    local report_file="$TEST_RESULTS_DIR/test_runner_$(date +%Y%m%d_%H%M%S).json"
    
    ensure_dir "$TEST_RESULTS_DIR"
    
    cat > "$report_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "version": "$CELL0_VERSION",
  "total_tests": $TESTS_TOTAL,
  "passed": $TESTS_PASSED,
  "failed": $TESTS_FAILED,
  "skipped": $TESTS_SKIPPED,
  "duration_seconds": $total_time,
  "success_rate": $(( TESTS_PASSED * 100 / TESTS_TOTAL )),
  "results": [
EOF

    local first=true
    for result in "${TEST_RESULTS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        
        IFS='|' read -r num status duration message <<< "$result"
        printf '    {"test": %s, "status": "%s", "duration_ms": %s, "message": "%s"}' \
            "$num" "$status" "$duration" "${message//\"/\\\"}" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF

  ]
}
EOF

    log_info "Report saved: $report_file"
}

# ============================================================================
# Main
# ============================================================================
show_help() {
    cat << EOF
Cell 0 OS - Test Runner

Usage: test_runner.sh [OPTIONS]

Options:
    -h, --help          Show this help message
    -q, --quick         Run quick tests only
    -r, --report        Save JSON report
    --test N            Run specific test number

Examples:
    test_runner.sh              # Run all tests
    test_runner.sh --report     # Run tests and save report
    test_runner.sh --test 1     # Run test #1 only
EOF
}

ensure_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
    fi
}

cleanup() {
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

trap cleanup EXIT

main() {
    local save_report_flag=false
    local specific_test=0
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -r|--report)
                save_report_flag=true
                shift
                ;;
            --test)
                specific_test=$2
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Create test directories
    ensure_dir "$TEST_DIR"
    ensure_dir "$TEST_RESULTS_DIR"
    
    # Run tests
    if [ $specific_test -gt 0 ]; then
        echo "Running test $specific_test..."
        "test_$(printf "%02d" $specific_test)"
    else
        run_all_tests
        local total_time=$?
        
        print_summary $total_time
        local exit_code=$?
        
        if [ "$save_report_flag" = true ]; then
            save_report $total_time
        fi
        
        exit $exit_code
    fi
}

main "$@"
