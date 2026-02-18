# Cell 0 OS Installation Guide

Complete installation instructions for Cell 0 OS - Sovereign Edge Model Operating System.

## Quick Install (Recommended)

```bash
curl -fsSL https://cell0.io/install.sh | bash
```

Or with options:

```bash
curl -fsSL https://cell0.io/install.sh | bash -s -- --dir /opt/cell0 --version 1.2.0
```

## Platform-Specific Installation

### macOS

#### Homebrew (Recommended)

```bash
brew tap cell0-os/cell0
brew install cell0-os
brew services start cell0-os
```

#### Manual Install

```bash
git clone https://github.com/cell0-os/cell0.git ~/.cell0
cd ~/.cell0
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Linux

#### Debian/Ubuntu

```bash
# Download .deb package
wget https://github.com/cell0-os/cell0/releases/download/v1.2.0/cell0-os_1.2.0-1_amd64.deb
sudo dpkg -i cell0-os_1.2.0-1_amd64.deb
sudo apt-get install -f  # Fix any missing dependencies

# Start service
sudo systemctl enable --now cell0d
```

#### RHEL/CentOS/Fedora

```bash
# Using dnf (Fedora/RHEL 8+)
sudo dnf install https://github.com/cell0-os/cell0/releases/download/v1.2.0/cell0-os-1.2.0-1.x86_64.rpm

# Using yum (older systems)
sudo yum install https://github.com/cell0-os/cell0/releases/download/v1.2.0/cell0-os-1.2.0-1.x86_64.rpm

# Start service
sudo systemctl enable --now cell0d
```

#### Arch Linux

```bash
# Using AUR helper
yay -S cell0-os

# Or manually
git clone https://aur.archlinux.org/cell0-os.git
cd cell0-os
makepkg -si
```

### Docker

#### Quick Start

```bash
# Clone repository
git clone https://github.com/cell0-os/cell0.git
cd cell0

# Start with Docker Compose
docker-compose -f packaging/docker/docker-compose.yml up -d
```

#### Docker Run

```bash
docker run -d \
  --name cell0 \
  -p 18800:18800 \
  -p 18801:18801 \
  -p 18802:18802 \
  -v cell0-data:/app/data \
  ghcr.io/cell0-os/cell0:1.2.0
```

### Kubernetes

#### Using Helm

```bash
# Add Helm repository
helm repo add cell0 https://charts.cell0.io
helm repo update

# Install
helm install cell0 cell0/cell0 \
  --namespace cell0 \
  --create-namespace \
  --values helm/cell0/values.yaml
```

#### Using kubectl

```bash
kubectl apply -k cell0/k8s/
```

#### Using Kustomize

```bash
kubectl apply -k https://github.com/cell0-os/cell0/k8s/
```

## Prerequisites

### Required

- Python 3.9 or higher
- pip3
- git
- curl

### Optional

- Rust (for building from source)
- Ollama (for local LLM inference)
- Redis (for caching)
- Docker (for containerized deployment)
- kubectl (for Kubernetes deployment)
- Helm (for Kubernetes package management)

### Verify Prerequisites

```bash
curl -fsSL https://cell0.io/verify-deps.sh | bash
```

Or run locally:

```bash
./packaging/scripts/verify_deps.sh
```

## Post-Installation

### Start the Daemon

**macOS (Homebrew):**
```bash
brew services start cell0-os
```

**macOS (Manual):**
```bash
launchctl load ~/Library/LaunchAgents/com.cell0.daemon.plist
launchctl start com.cell0.daemon
```

**Linux (systemd):**
```bash
systemctl --user enable --now cell0d
# Or system-wide:
sudo systemctl enable --now cell0d
```

**Manual:**
```bash
cell0d start
```

### Verify Installation

```bash
# Check daemon status
cell0d status

# Check version
cell0ctl --version

# Test API
curl http://localhost:18800/api/health
```

### Access Web Interfaces

- **Web UI:** http://localhost:18800
- **WebSocket:** ws://localhost:18801
- **Metrics:** http://localhost:18802/metrics
- **API Documentation:** http://localhost:18800/docs

### Configure

Edit configuration file:

```bash
# User config
~/.cell0/config/config.yaml

# System config (macOS Homebrew)
/usr/local/etc/cell0/config.yaml

# System config (Linux package)
/etc/cell0/config.yaml
```

## Upgrade

### Homebrew

```bash
brew update
brew upgrade cell0-os
```

### Debian/Ubuntu

```bash
wget https://github.com/cell0-os/cell0/releases/download/v1.3.0/cell0-os_1.3.0-1_amd64.deb
sudo dpkg -i cell0-os_1.3.0-1_amd64.deb
```

### Docker

```bash
docker pull ghcr.io/cell0-os/cell0:latest
docker-compose up -d
```

### Universal Installer

```bash
curl -fsSL https://cell0.io/install.sh | bash -s -- --version 1.3.0
```

## Uninstall

### Homebrew

```bash
brew services stop cell0-os
brew uninstall cell0-os
brew untap cell0-os/cell0
```

### Debian/Ubuntu

```bash
sudo systemctl stop cell0d
sudo apt-get remove cell0-os
sudo apt-get purge cell0-os  # Remove config too
```

### Manual

```bash
# Stop daemon
cell0d stop

# Remove installation
rm -rf ~/.cell0

# Remove from PATH
# Edit ~/.bashrc or ~/.zshrc and remove Cell 0 entries
```

### Docker

```bash
docker-compose down -v  # Remove containers and volumes
docker rmi ghcr.io/cell0-os/cell0:1.2.0
```

## Troubleshooting

### Installation Issues

**Permission denied:**
```bash
chmod +x install.sh
./install.sh
```

**Python not found:**
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3 python3-pip python3-venv

# RHEL/CentOS/Fedora
sudo dnf install python3 python3-pip
```

**Port already in use:**
```bash
# Check what's using the port
lsof -i :18800

# Use different ports
export CELL0_PORT=18810
export CELL0_WS_PORT=18811
export CELL0_METRICS_PORT=18812
cell0d start
```

### Runtime Issues

**Daemon won't start:**
```bash
# Check logs
cell0d logs

# Or for systemd
journalctl --user -u cell0d -f

# Debug mode
cell0d start --log-level DEBUG
```

**API not responding:**
```bash
# Check if daemon is running
cell0d status

# Test with curl
curl -v http://localhost:18800/api/health
```

## Building from Source

```bash
# Clone repository
git clone https://github.com/cell0-os/cell0.git
cd cell0

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Build
python setup.py build

# Install
pip install -e .
```

## Testing Installation

```bash
# Run install tests
./packaging/scripts/test_install.sh

# Run full test suite
pytest tests/

# Run with coverage
pytest --cov=cell0 tests/
```

## Development Setup

```bash
# Clone
git clone https://github.com/cell0-os/cell0.git
cd cell0

# Setup dev environment
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Build docs
cd docs && make html
```

## Getting Help

- **Documentation:** https://docs.cell0.io
- **GitHub Issues:** https://github.com/cell0-os/cell0/issues
- **Discord:** https://discord.gg/cell0
- **Email:** support@cell0.io

## License

GPL-3.0 - See LICENSE file for details.
