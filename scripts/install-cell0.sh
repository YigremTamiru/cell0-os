#!/usr/bin/env bash
# ─── Cell 0 OS Installer ────────────────────────────────────────────────────
#
# Remote install (from GitHub):
#   curl -fsSL https://raw.githubusercontent.com/YigremTamiru/cell0-os/main/scripts/install-cell0.sh | bash
#
# Local install (from cloned repo):
#   bash scripts/install-cell0.sh
#
# When you have a domain, update the URL:
#   curl -fsSL https://YOUR_DOMAIN/install.sh | bash
#
# Matches OpenClaw's installer flow:
# 1. Detect OS
# 2. Check prerequisites (Node ≥20, Git)
# 3. Install via npm (or local build)
# 4. Run onboarding wizard
#
# ────────────────────────────────────────────────────────────────────────────

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Banner
print_banner() {
    echo ""
    echo -e "  ${GREEN}${BOLD}🧬 Cell 0 OS Installer${RESET}"
    echo -e "  ${DIM}Intelligence at the edge. Privacy at the core.${RESET}"
    echo ""
}

# Status helpers
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
info() { echo -e "  ${CYAN}→${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET} $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; exit 1; }

# ─── Detect OS ─────────────────────────────────────────────────────────────

detect_os() {
    case "$(uname -s)" in
        Darwin)  OS="macos" ;;
        Linux)   OS="linux" ;;
        MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
        *)       fail "Unsupported OS: $(uname -s)" ;;
    esac
    ok "Detected: ${OS}"
}

# ─── Check Prerequisites ──────────────────────────────────────────────────

check_homebrew() {
    if [ "$OS" = "macos" ]; then
        if command -v brew &>/dev/null; then
            ok "Homebrew already installed"
        else
            info "Installing Homebrew…"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            ok "Homebrew installed"
        fi
    fi
}

check_node() {
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node -v | sed 's/v//')
        NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
        if [ "$NODE_MAJOR" -ge 20 ]; then
            ok "Node.js v${NODE_VERSION} found"
        else
            fail "Node.js ≥20 required (found v${NODE_VERSION}). Install: https://nodejs.org"
        fi
    else
        if [ "$OS" = "macos" ] && command -v brew &>/dev/null; then
            info "Installing Node.js via Homebrew…"
            brew install node
            ok "Node.js installed"
        elif [ "$OS" = "linux" ]; then
            info "Installing Node.js via NodeSource…"
            curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
            sudo apt-get install -y nodejs
            ok "Node.js installed"
        else
            fail "Node.js ≥20 required. Install: https://nodejs.org"
        fi
    fi
}

check_git() {
    if command -v git &>/dev/null; then
        ok "Git already installed"
    else
        if [ "$OS" = "macos" ] && command -v brew &>/dev/null; then
            brew install git
        elif [ "$OS" = "linux" ]; then
            sudo apt-get install -y git
        else
            fail "Git is required. Install: https://git-scm.com"
        fi
        ok "Git installed"
    fi
}

check_python() {
    if command -v python3 &>/dev/null; then
        PY_VERSION=$(python3 --version | awk '{print $2}')
        ok "Python ${PY_VERSION} found"
    else
        warn "Python 3 not found — needed for Cell 0 Python backend"
        info "Install Python 3.10+: https://python.org"
    fi
}

# ─── Install Cell 0 ───────────────────────────────────────────────────────

install_cell0() {
    # Check for existing installation
    if command -v cell0 &>/dev/null; then
        EXISTING_VERSION=$(cell0 --version 2>/dev/null || echo "unknown")
        info "Existing Cell 0 installation detected (${EXISTING_VERSION})"
    fi

    # Detect if we're running from a cloned repo
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"

    if [ -f "$REPO_ROOT/package.json" ] && grep -q '"cell0-os"' "$REPO_ROOT/package.json" 2>/dev/null; then
        info "Installing Cell 0 OS from local repo…"
        cd "$REPO_ROOT"
        npm install 2>/dev/null
        npx tsc 2>/dev/null
        npm link 2>/dev/null || sudo npm link
        ok "Cell 0 OS installed (local dev build)"
    else
        info "Installing Cell 0 OS from npm…"
        npm install -g cell0-os@latest 2>/dev/null || npm install -g cell0-os@latest
        ok "Cell 0 OS installed"
    fi
}

# ─── Post-Install ─────────────────────────────────────────────────────────

post_install() {
    CELL0_VERSION=$(cell0 --version 2>/dev/null || echo "1.2.0")

    echo ""
    echo -e "  ${GREEN}${BOLD}🧬 Cell 0 OS installed successfully (${CELL0_VERSION})!${RESET}"
    echo -e "  ${DIM}Your sovereign AI is ready.${RESET}"
    echo ""

    # ASCII art
    echo -e "${GREEN}"
    echo "  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄"
    echo "  ██░▄▄▀██░▄▄▄██░████░████░████░▄▄▄░██░▄▄▄░█████"
    echo "  ██░████░▄▄▄██░████░████░████░███░█░█░▪▪▪░█████"
    echo "  ██░▀▀▄██░▀▀▀██░▀▀░█░▀▀░█░▀▀░█░▀▀▀░█▀▄▀█░▀▀▀██"
    echo "  ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀"
    echo -e "${RESET}"
    echo -e "                 ${CYAN}🧬 CELL 0 🧬${RESET}"
    echo ""

    # Check if config exists
    if [ -f "$HOME/.cell0/cell0.json" ]; then
        info "Config already present; running doctor…"
        cell0 doctor || true
    fi

    # Run onboarding
    info "Starting onboarding wizard…"
    echo ""
    cell0 onboard --install-daemon
}

# ─── Main ──────────────────────────────────────────────────────────────────

main() {
    print_banner
    detect_os
    check_homebrew
    check_node
    check_git
    check_python
    install_cell0
    post_install
}

main "$@"
