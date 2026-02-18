#!/bin/bash
# Cell 0 OS - Interactive Installation Wizard
# 6-step guided installation with user-friendly prompts

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CELL0_VERSION="1.2.0"
INSTALL_DIR="${CELL0_INSTALL_DIR:-$HOME/.cell0}"
BIN_DIR="${CELL0_BIN_DIR:-$HOME/.local/bin}"
CONFIG_DIR="${CELL0_CONFIG_DIR:-$HOME/.config/cell0}"
GITHUB_REPO="cell0-os/cell0"

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Wizard state
CURRENT_STEP=0
TOTAL_STEPS=6
INSTALL_OPTIONS=()
SELECTED_MODEL=""
ENABLE_GPU=false
ENABLE_MONITORING=true
ENABLE_BACKUP=true
ADMIN_EMAIL=""

# ============================================================================
# UI Functions
# ============================================================================
print_header() {
    clear
    echo -e "${CYAN}"
    echo '    ____     __       ___       __  _______  ____  _____'
    echo '   / __/_ __/ /____  / _ \___ _/ / / ___/  |/  / |/ / _ \'
    echo '  / /__/ // / __/ _ \/ // / _ `/ / / /__/ /|_/ /    / // /'
    echo '  \___/\_,_/\__/\___/____/\_,_/_/  \___/_/  /_/_/|_/____/'
    echo -e "${NC}"
    echo -e "${BOLD}Interactive Installation Wizard v${CELL0_VERSION}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_step() {
    local step=$1
    local title=$2
    echo -e "\n${BOLD}Step $step of $TOTAL_STEPS: $title${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_progress() {
    local filled=$(( CURRENT_STEP * 20 / TOTAL_STEPS ))
    local empty=$(( 20 - filled ))
    local bar=$(printf '%*s' "$filled" '' | tr ' ' '█')
    local space=$(printf '%*s' "$empty" '' | tr ' ' '░')
    echo -e "${CYAN}[$bar$space] $(( CURRENT_STEP * 100 / TOTAL_STEPS ))%${NC}\n"
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local response
    
    while true; do
        read -rp "$prompt [Y/n]: " response
        response=${response:-$default}
        case "$response" in
            [Yy]*) return 0 ;;
            [Nn]*) return 1 ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

prompt_input() {
    local prompt="$1"
    local default="${2:-}"
    local required="${3:-false}"
    local response
    
    while true; do
        if [ -n "$default" ]; then
            read -rp "$prompt [$default]: " response
            response=${response:-$default}
        else
            read -rp "$prompt: " response
        fi
        
        if [ "$required" = true ] && [ -z "$response" ]; then
            log_error "This field is required."
        else
            echo "$response"
            return 0
        fi
    done
}

prompt_selection() {
    local prompt="$1"
    shift
    local options=("$@")
    local count=${#options[@]}
    
    echo -e "$prompt"
    for i in "${!options[@]}"; do
        echo "  $((i+1)). ${options[$i]}"
    done
    
    while true; do
        read -rp "Select option (1-$count): " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$count" ]; then
            echo "${options[$((choice-1))]}"
            return 0
        fi
        log_error "Invalid selection. Please choose 1-$count."
    done
}

wait_continue() {
    echo
    read -rp "Press Enter to continue..."
}

# ============================================================================
# Step 1: Welcome & Prerequisites
# ============================================================================
step_welcome() {
    CURRENT_STEP=1
    print_header
    print_progress
    print_step 1 "Welcome & System Check"
    
    echo "Welcome to the Cell 0 OS Installation Wizard!"
    echo
    echo "This wizard will guide you through installing Cell 0 OS"
    echo "with a customized configuration for your system."
    echo
    echo -e "${YELLOW}System Requirements:${NC}"
    echo "  • Python 3.9 or higher"
    echo "  • 2GB RAM minimum (4GB recommended)"
    echo "  • 5GB free disk space"
    echo "  • Internet connection for downloads"
    echo
    
    log_info "Checking your system..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        log_success "Python $PYTHON_VERSION found"
    else
        log_error "Python 3 not found. Please install Python 3.9+ first."
        exit 1
    fi
    
    # Check architecture
    local arch=$(uname -m)
    log_info "Architecture: $arch"
    
    # Check OS
    local os=$(uname -s)
    log_info "Operating System: $os"
    
    echo
    if prompt_yes_no "Continue with installation?"; then
        return 0
    else
        echo "Installation cancelled."
        exit 0
    fi
}

# ============================================================================
# Step 2: Installation Type
# ============================================================================
step_installation_type() {
    CURRENT_STEP=2
    print_header
    print_progress
    print_step 2 "Choose Installation Type"
    
    echo "Select your installation type:"
    echo
    
    local choice=$(prompt_selection "Available options:" \
        "Full Installation (Recommended) - All features" \
        "Minimal Installation - Core only" \
        "Development Setup - With dev tools" \
        "Server Setup - Optimized for servers" \
        "Custom Installation - Choose components")
    
    case "$choice" in
        "Full Installation"*)
            INSTALL_OPTIONS=("core" "gui" "monitoring" "backup" "integrations")
            log_success "Selected: Full Installation"
            ;;
        "Minimal Installation"*)
            INSTALL_OPTIONS=("core")
            log_success "Selected: Minimal Installation"
            ;;
        "Development Setup"*)
            INSTALL_OPTIONS=("core" "dev" "testing" "docs")
            log_success "Selected: Development Setup"
            ;;
        "Server Setup"*)
            INSTALL_OPTIONS=("core" "monitoring" "backup" "security")
            log_success "Selected: Server Setup"
            ;;
        "Custom Installation"*)
            step_custom_components
            ;;
    esac
    
    wait_continue
}

# ============================================================================
# Custom Component Selection
# ============================================================================
step_custom_components() {
    echo
    echo "Select components to install (space-separated numbers):"
    echo "  1. Core System (required)"
    echo "  2. GUI Interface"
    echo "  3. Monitoring & Alerts"
    echo "  4. Backup System"
    echo "  5. Third-party Integrations"
    echo "  6. Development Tools"
    echo "  7. Security Features"
    echo "  8. Documentation"
    
    read -rp "Enter choices: " choices
    
    INSTALL_OPTIONS=("core")
    for choice in $choices; do
        case $choice in
            2) INSTALL_OPTIONS+=("gui") ;;
            3) INSTALL_OPTIONS+=("monitoring") ;;
            4) INSTALL_OPTIONS+=("backup") ;;
            5) INSTALL_OPTIONS+=("integrations") ;;
            6) INSTALL_OPTIONS+=("dev") ;;
            7) INSTALL_OPTIONS+=("security") ;;
            8) INSTALL_OPTIONS+=("docs") ;;
        esac
    done
}

# ============================================================================
# Step 3: AI Model Configuration
# ============================================================================
step_model_config() {
    CURRENT_STEP=3
    print_header
    print_progress
    print_step 3 "AI Model Configuration"
    
    echo "Select your preferred AI model provider:"
    echo
    
    SELECTED_MODEL=$(prompt_selection "Available providers:" \
        "Local (Llama.cpp - runs on your machine)" \
        "OpenAI API (requires API key)" \
        "Anthropic Claude (requires API key)" \
        "Ollama (local models)" \
        "Custom Provider")
    
    log_success "Selected: $SELECTED_MODEL"
    
    # GPU configuration
    echo
    if prompt_yes_no "Enable GPU acceleration? (recommended if available)"; then
        ENABLE_GPU=true
        log_success "GPU acceleration enabled"
    else
        ENABLE_GPU=false
        log_info "Running in CPU mode"
    fi
    
    wait_continue
}

# ============================================================================
# Step 4: System Configuration
# ============================================================================
step_system_config() {
    CURRENT_STEP=4
    print_header
    print_progress
    print_step 4 "System Configuration"
    
    echo "Configure system settings:"
    echo
    
    # Installation directory
    INSTALL_DIR=$(prompt_input "Installation directory" "$HOME/.cell0")
    log_info "Install location: $INSTALL_DIR"
    
    # Bin directory
    BIN_DIR=$(prompt_input "Binary directory (for symlinks)" "$HOME/.local/bin")
    log_info "Binary location: $BIN_DIR"
    
    # Monitoring
    echo
    if prompt_yes_no "Enable system monitoring and health checks?" "y"; then
        ENABLE_MONITORING=true
        log_success "Monitoring enabled"
    else
        ENABLE_MONITORING=false
        log_info "Monitoring disabled"
    fi
    
    # Backup
    echo
    if prompt_yes_no "Enable automatic backups?" "y"; then
        ENABLE_BACKUP=true
        log_success "Backups enabled"
    else
        ENABLE_BACKUP=false
        log_info "Backups disabled"
    fi
    
    wait_continue
}

# ============================================================================
# Step 5: Security & Admin Setup
# ============================================================================
step_security_config() {
    CURRENT_STEP=5
    print_header
    print_progress
    print_step 5 "Security & Administrator Setup"
    
    echo "Configure security settings:"
    echo
    
    # Admin email
    ADMIN_EMAIL=$(prompt_input "Administrator email" "" true)
    log_info "Admin email: $ADMIN_EMAIL"
    
    # Service user
    echo
    if prompt_yes_no "Create dedicated service user? (recommended for servers)"; then
        CREATE_SERVICE_USER=true
        log_success "Service user will be created"
    else
        CREATE_SERVICE_USER=false
        log_info "Running as current user"
    fi
    
    # Firewall
    echo
    if command -v ufw &> /dev/null || command -v firewall-cmd &> /dev/null; then
        if prompt_yes_no "Configure firewall rules?"; then
            CONFIGURE_FIREWALL=true
            log_success "Firewall will be configured"
        else
            CONFIGURE_FIREWALL=false
        fi
    fi
    
    wait_continue
}

# ============================================================================
# Step 6: Review & Install
# ============================================================================
step_review_install() {
    CURRENT_STEP=6
    print_header
    print_progress
    print_step 6 "Review & Install"
    
    echo -e "${BOLD}Installation Summary:${NC}\n"
    
    echo "Configuration:"
    echo "  Installation Directory: $INSTALL_DIR"
    echo "  Binary Directory: $BIN_DIR"
    echo "  Components: ${INSTALL_OPTIONS[*]}"
    echo "  AI Provider: $SELECTED_MODEL"
    echo "  GPU Enabled: $ENABLE_GPU"
    echo "  Monitoring: $ENABLE_MONITORING"
    echo "  Backups: $ENABLE_BACKUP"
    echo "  Admin Email: $ADMIN_EMAIL"
    echo "  Service User: ${CREATE_SERVICE_USER:-false}"
    echo
    
    echo -e "${YELLOW}Ready to install Cell 0 OS v${CELL0_VERSION}${NC}"
    echo
    
    if prompt_yes_no "Start installation?"; then
        execute_installation
    else
        echo "Installation cancelled."
        exit 0
    fi
}

# ============================================================================
# Execute Installation
# ============================================================================
execute_installation() {
    echo
    log_info "Starting installation..."
    echo
    
    # Create directories
    log_info "Creating directories..."
    mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$CONFIG_DIR"
    
    # Save configuration
    save_configuration
    
    # Run main installer with our options
    log_info "Running installer..."
    
    export CELL0_INSTALL_DIR="$INSTALL_DIR"
    export CELL0_BIN_DIR="$BIN_DIR"
    export CELL0_ENABLE_GPU="$ENABLE_GPU"
    export CELL0_ENABLE_MONITORING="$ENABLE_MONITORING"
    export CELL0_ENABLE_BACKUP="$ENABLE_BACKUP"
    export CELL0_ADMIN_EMAIL="$ADMIN_EMAIL"
    
    if [ -f "./install.sh" ]; then
        bash ./install.sh --batch --components "${INSTALL_OPTIONS[*]}"
    else
        log_info "Downloading and running installer..."
        curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/main/install.sh" | \
            bash -s -- --batch --components "${INSTALL_OPTIONS[*]}"
    fi
    
    if [ $? -eq 0 ]; then
        echo
        log_success "Installation completed successfully!"
        show_post_install_info
    else
        log_error "Installation failed. Check the logs above."
        exit 1
    fi
}

# ============================================================================
# Save Configuration
# ============================================================================
save_configuration() {
    cat > "$CONFIG_DIR/install-wizard.conf" << EOF
# Cell 0 OS - Installation Configuration
# Generated by install-wizard.sh on $(date -Iseconds)

CELL0_VERSION="$CELL0_VERSION"
INSTALL_DIR="$INSTALL_DIR"
BIN_DIR="$BIN_DIR"
CONFIG_DIR="$CONFIG_DIR"
INSTALL_OPTIONS=(${INSTALL_OPTIONS[*]})
SELECTED_MODEL="$SELECTED_MODEL"
ENABLE_GPU="$ENABLE_GPU"
ENABLE_MONITORING="$ENABLE_MONITORING"
ENABLE_BACKUP="$ENABLE_BACKUP"
ADMIN_EMAIL="$ADMIN_EMAIL"
CREATE_SERVICE_USER="${CREATE_SERVICE_USER:-false}"
CONFIGURE_FIREWALL="${CONFIGURE_FIREWALL:-false}"
EOF
}

# ============================================================================
# Post-Install Information
# ============================================================================
show_post_install_info() {
    echo
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  ✓ Cell 0 OS installed successfully!${NC}"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    echo "Next steps:"
    echo "  1. Open a new terminal or run: source ~/.bashrc"
    echo "  2. Start Cell 0: cell0ctl start"
    echo "  3. Check status: cell0ctl status"
    echo "  4. View dashboard: http://localhost:8080"
    echo
    echo "Documentation: https://docs.cell0.io"
    echo "Support: https://github.com/${GITHUB_REPO}/issues"
    echo
    echo -e "${CYAN}Thank you for installing Cell 0 OS!${NC}"
    echo
}

# ============================================================================
# Main
# ============================================================================
main() {
    # Check for batch mode
    if [[ "${1:-}" == "--batch" ]]; then
        log_info "Batch mode - skipping wizard"
        execute_installation
        exit 0
    fi
    
    # Check terminal
    if [ ! -t 0 ]; then
        log_error "This wizard requires an interactive terminal."
        log_info "Use install.sh for non-interactive installation."
        exit 1
    fi
    
    # Run wizard steps
    step_welcome
    step_installation_type
    step_model_config
    step_system_config
    step_security_config
    step_review_install
}

# Run main
main "$@"
