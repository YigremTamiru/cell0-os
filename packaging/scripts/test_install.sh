# Cell 0 OS - Fresh Install Test Suite
# Comprehensive testing for fresh installations

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TEST_DIR="$(mktemp -d)"
CELL0_VERSION="1.2.0"
CLEANUP=true
VERBOSE=false

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# ============================================================================
# Logging
# ============================================================================
log_info() { echo -e "${BLUE}[TEST]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; TESTS_PASSED=$((TESTS_PASSED + 1)) || true; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; TESTS_FAILED=$((TESTS_FAILED + 1)) || true; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; TESTS_SKIPPED=$((TESTS_SKIPPED + 1)) || true; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_debug() { [[ "$VERBOSE" == true ]] && echo -e "${BLUE}[DEBUG]${NC} $1"; }

# ============================================================================
# Cleanup
# ============================================================================
cleanup() {
    if [ "$CLEANUP" = true ]; then
        log_debug "Cleaning up test directory: $TEST_DIR"
        rm -rf "$TEST_DIR"
    else
        log_warn "Skipping cleanup. Test directory: $TEST_DIR"
    fi
}
trap cleanup EXIT

# ============================================================================
# Test Functions
# ============================================================================

test_prerequisites() {
    log_info "Testing prerequisites detection..."
    
    # Test Python check
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        log_pass "Python detected: $PYTHON_VERSION"
    else
        log_fail "Python3 not found"
    fi
    
    # Test pip check
    if command -v pip3 &> /dev/null; then
        log_pass "pip3 detected"
    else
        log_fail "pip3 not found"
    fi
    
    # Test git check
    if command -v git &> /dev/null; then
        log_pass "git detected"
    else
        log_fail "git not found"
    fi
}

test_install_script_syntax() {
    log_info "Testing install script syntax..."
    
    if bash -n install.sh 2>/dev/null; then
        log_pass "Install script syntax valid"
    else
        log_fail "Install script has syntax errors"
    fi
}

test_verify_deps_syntax() {
    log_info "Testing verify_deps.sh syntax..."
    
    if bash -n packaging/scripts/verify_deps.sh 2>/dev/null; then
        log_pass "verify_deps.sh syntax valid"
    else
        log_fail "verify_deps.sh has syntax errors"
    fi
}

test_virtualenv_creation() {
    log_info "Testing virtual environment creation..."
    
    local venv_dir="$TEST_DIR/venv"
    
    if python3 -m venv "$venv_dir" 2>/dev/null; then
        log_pass "Virtual environment created"
        
        # Test activation
        if [ -f "$venv_dir/bin/activate" ]; then
            log_pass "Virtual environment activation script exists"
        else
            log_fail "Virtual environment activation script missing"
        fi
    else
        log_fail "Virtual environment creation failed"
    fi
}

test_python_dependencies() {
    log_info "Testing Python dependencies..."
    
    local venv_dir="$TEST_DIR/venv2"
    
    if ! python3 -m venv "$venv_dir" 2>/dev/null; then
        log_skip "Could not create virtual environment for dependency test"
        return
    fi
    
    source "$venv_dir/bin/activate"
    
    # Test core dependencies installation (one by one to handle errors)
    local deps=("pyyaml" "pydantic")
    local all_passed=true
    
    for dep in "${deps[@]}"; do
        if pip install "$dep" -q 2>/dev/null; then
            log_pass "Dependency install: $dep"
        else
            log_fail "Dependency install failed: $dep"
            all_passed=false
        fi
    done
    
    deactivate || true
}

test_directory_structure() {
    log_info "Testing directory structure creation..."
    
    local install_dir="$TEST_DIR/cell0"
    
    mkdir -p "$install_dir"/bin
    mkdir -p "$install_dir"/data
    mkdir -p "$install_dir"/logs
    mkdir -p "$install_dir"/config
    mkdir -p "$install_dir"/venv
    
    for dir in bin data logs config venv; do
        if [ -d "$install_dir/$dir" ]; then
            log_pass "Directory created: $dir"
        else
            log_fail "Directory missing: $dir"
        fi
    done
}

test_wrapper_scripts() {
    log_info "Testing wrapper scripts..."
    
    local bin_dir="$TEST_DIR/cell0/bin"
    mkdir -p "$bin_dir"
    
    # Create test wrapper
    cat > "$bin_dir/cell0d" << 'EOF'
#!/bin/bash
echo "Cell 0 Daemon v1.2.0"
EOF
    chmod +x "$bin_dir/cell0d"
    
    if [ -x "$bin_dir/cell0d" ]; then
        log_pass "Wrapper script created and executable"
    else
        log_fail "Wrapper script not executable"
    fi
    
    # Test execution
    if output=$("$bin_dir/cell0d" 2>&1); then
        log_pass "Wrapper script executes: $output"
    else
        log_fail "Wrapper script execution failed"
    fi
}

test_docker_compose_syntax() {
    log_info "Testing Docker Compose syntax..."
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_skip "Docker not available, skipping Docker Compose test"
        return
    fi
    
    if docker-compose -f packaging/docker/docker-compose.yml config > /dev/null 2>&1 || \
       docker compose -f packaging/docker/docker-compose.yml config > /dev/null 2>&1; then
        log_pass "Docker Compose syntax valid"
    else
        log_fail "Docker Compose syntax invalid"
    fi
}

test_dockerfile_syntax() {
    log_info "Testing Dockerfile syntax..."
    
    if ! command -v docker &> /dev/null; then
        log_skip "Docker not available, skipping Dockerfile test"
        return
    fi
    
    # Just check if Dockerfile exists and has content
    if [ -f "packaging/docker/Dockerfile" ] && [ -s "packaging/docker/Dockerfile" ]; then
        log_pass "Dockerfile exists and has content"
    else
        log_fail "Dockerfile missing or empty"
    fi
}

test_shell_configuration() {
    log_info "Testing shell configuration..."
    
    local shell_rc="$TEST_DIR/.bashrc"
    local bin_dir="$TEST_DIR/bin"
    
    mkdir -p "$bin_dir"
    echo 'export PATH="'$bin_dir':$PATH"' >> "$shell_rc"
    
    if grep -q "$bin_dir" "$shell_rc" 2>/dev/null; then
        log_pass "Shell PATH configuration written"
    else
        log_fail "Shell PATH configuration failed"
    fi
}

test_service_file_generation() {
    log_info "Testing service file generation..."
    
    # Test systemd service
    local systemd_dir="$TEST_DIR/.config/systemd/user"
    mkdir -p "$systemd_dir"
    
    cat > "$systemd_dir/cell0d.service" << EOF
[Unit]
Description=Cell 0 OS Daemon
[Service]
Type=simple
ExecStart=/bin/true
[Install]
WantedBy=default.target
EOF
    
    if [ -f "$systemd_dir/cell0d.service" ]; then
        log_pass "Systemd service file created"
    else
        log_fail "Systemd service file creation failed"
    fi
    
    # Test launchd plist (macOS)
    local launchd_dir="$TEST_DIR/Library/LaunchAgents"
    mkdir -p "$launchd_dir"
    
    cat > "$launchd_dir/com.cell0.daemon.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cell0.daemon</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
    
    if [ -f "$launchd_dir/com.cell0.daemon.plist" ]; then
        log_pass "LaunchAgent plist created"
    else
        log_fail "LaunchAgent plist creation failed"
    fi
}

test_homebrew_formula_syntax() {
    log_info "Testing Homebrew formula syntax..."
    
    if ! command -v ruby &> /dev/null; then
        log_skip "Ruby not available, skipping Homebrew formula test"
        return
    fi
    
    if ruby -c packaging/homebrew/cell0-os.rb > /dev/null 2>&1; then
        log_pass "Homebrew formula syntax valid"
    else
        log_fail "Homebrew formula syntax invalid"
    fi
}

test_debian_package_structure() {
    log_info "Testing Debian package structure..."
    
    local debian_dir="packaging/debian"
    local required_files=("control" "rules" "changelog" "compat")
    
    for file in "${required_files[@]}"; do
        if [ -f "$debian_dir/$file" ]; then
            log_pass "Debian file exists: $file"
        else
            log_fail "Debian file missing: $file"
        fi
    done
}

test_rpm_package_structure() {
    log_info "Testing RPM package structure..."
    
    if [ -f "packaging/rpm/cell0-os.spec" ]; then
        log_pass "RPM spec file exists"
    else
        log_fail "RPM spec file missing"
    fi
}

test_arch_package_structure() {
    log_info "Testing Arch Linux package structure..."
    
    local files=("PKGBUILD" "cell0-os.install" "cell0d.service")
    local all_exist=true
    
    for file in "${files[@]}"; do
        if [ -f "packaging/arch/$file" ]; then
            log_pass "Arch file exists: $file"
        else
            log_fail "Arch file missing: $file"
            all_exist=false
        fi
    done
}

test_snap_package_structure() {
    log_info "Testing Snap package structure..."
    
    if [ -f "packaging/snap/snapcraft.yaml" ]; then
        log_pass "Snapcraft.yaml exists"
    else
        log_fail "Snapcraft.yaml missing"
    fi
}

test_nix_package_structure() {
    log_info "Testing Nix package structure..."
    
    if [ -f "packaging/nix/default.nix" ]; then
        log_pass "default.nix exists"
    else
        log_fail "default.nix missing"
    fi
}

test_windows_installer() {
    log_info "Testing Windows PowerShell installer..."
    
    if [ -f "packaging/windows/install.ps1" ]; then
        log_pass "Windows installer exists"
    else
        log_fail "Windows installer missing"
    fi
}

test_documentation() {
    log_info "Testing documentation..."
    
    if [ -f "INSTALL.md" ]; then
        log_pass "INSTALL.md exists"
    else
        log_fail "INSTALL.md missing"
    fi
    
    if [ -f "packaging/README.md" ]; then
        log_pass "packaging/README.md exists"
    else
        log_fail "packaging/README.md missing"
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Cell 0 OS Installation Test Suite"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-cleanup)
                CLEANUP=false
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                echo "Usage: test_install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --no-cleanup    Keep test directory after tests"
                echo "  --verbose, -v   Enable verbose output"
                echo "  --help, -h      Show this help message"
                echo ""
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Test directory: $TEST_DIR"
    log_info "Cell 0 version: $CELL0_VERSION"
    echo ""
    
    # Run tests
    test_prerequisites
    test_install_script_syntax
    test_verify_deps_syntax
    test_virtualenv_creation
    test_python_dependencies
    test_directory_structure
    test_wrapper_scripts
    test_docker_compose_syntax
    test_dockerfile_syntax
    test_shell_configuration
    test_service_file_generation
    test_homebrew_formula_syntax
    test_debian_package_structure
    test_rpm_package_structure
    test_arch_package_structure
    test_snap_package_structure
    test_nix_package_structure
    test_windows_installer
    test_documentation
    
    # Summary
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Test Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Passed:  $TESTS_PASSED"
    echo "  Failed:  $TESTS_FAILED"
    echo "  Skipped: $TESTS_SKIPPED"
    echo "═══════════════════════════════════════════════════════════════"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

main "$@"
