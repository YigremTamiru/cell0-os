# Cell 0 OS Installation Guide

Complete installation instructions for Cell 0 OS on all supported platforms.

## Quick Install (One-Liner)

```bash
curl -fsSL https://cell0.io/install.sh | bash
```

With options:
```bash
# Minimal installation (core only)
curl -fsSL https://cell0.io/install.sh | bash -s -- --minimal

# Development installation (with all dev tools)
curl -fsSL https://cell0.io/install.sh | bash -s -- --dev

# Specific version
curl -fsSL https://cell0.io/install.sh | bash -s -- --version=1.2.0
```

## Table of Contents

1. [System Requirements](#system-requirements)
2. [macOS Installation](#macos-installation)
3. [Linux Installation](#linux-installation)
4. [Docker Installation](#docker-installation)
5. [Package Managers](#package-managers)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Post-Installation](#post-installation)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB (32GB for larger models) |
| Storage | 10 GB | 50+ GB SSD |
| Python | 3.9+ | 3.11+ |
| GPU | Optional | NVIDIA RTX 3090/4090 or Apple Silicon |

### Supported Platforms

- **macOS**: 12.0+ (Monterey), Apple Silicon or Intel
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, Arch Linux
- **Docker**: Any platform with Docker 20.10+
- **Kubernetes**: K8s 1.24+, Helm 3.12+

---

## macOS Installation

### Option 1: Homebrew (Recommended)

```bash
# Add Cell 0 tap
brew tap cell0-os/cell0

# Install
brew install cell0

# Start service
brew services start cell0
```

### Option 2: Manual Installation

```bash
# Clone repository
git clone https://github.com/cell0-os/cell0.git ~/cell0
cd ~/cell0

# Install dependencies
brew install python@3.11 ollama

# Run setup
./setup.sh

# Start
./start.sh
```

### Option 3: Install Script

```bash
curl -fsSL https://cell0.io/install.sh | bash
```

---

## Linux Installation

### Ubuntu/Debian

#### Option 1: APT Repository

```bash
# Add Cell 0 repository
curl -fsSL https://cell0.io/apt/cell0.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cell0.gpg
echo "deb [signed-by=/usr/share/keyrings/cell0.gpg] https://apt.cell0.io stable main" | \
    sudo tee /etc/apt/sources.list.d/cell0.list

# Install
sudo apt update
sudo apt install cell0-os

# Start service
sudo systemctl enable --now cell0
```

#### Option 2: .deb Package

```bash
# Download and install
wget https://github.com/cell0-os/cell0/releases/download/v1.2.0/cell0-os_1.2.0_amd64.deb
sudo dpkg -i cell0-os_1.2.0_amd64.deb
sudo apt-get install -f  # Fix dependencies if needed
```

#### Option 3: Install Script

```bash
curl -fsSL https://cell0.io/install.sh | bash
```

### Fedora/RHEL/CentOS

```bash
# Install dependencies
sudo dnf install python3 python3-pip git curl

# Run install script
curl -fsSL https://cell0.io/install.sh | bash
```

### Arch Linux

```bash
# From AUR (when available)
yay -S cell0-os

# Or install script
curl -fsSL https://cell0.io/install.sh | bash
```

---

## Docker Installation

### Quick Start

```bash
# Clone repository
git clone https://github.com/cell0-os/cell0.git
cd cell0

# Start with docker-compose
docker-compose up -d

# Or use full stack
docker-compose -f docker-compose.full.yml up -d
```

### Docker Run

```bash
# Pull and run
docker run -d \
  --name cell0 \
  -p 18800:18800 \
  -p 18801:18801 \
  -p 18802:18802 \
  -v cell0-data:/data/cell0 \
  ghcr.io/cell0-os/cell0:latest
```

### With GPU Support (NVIDIA)

```bash
docker run -d \
  --name cell0 \
  --gpus all \
  -p 18800:18800 \
  -v cell0-data:/data/cell0 \
  ghcr.io/cell0-os/cell0:latest
```

### With Ollama

```bash
# Using provided compose
docker-compose up -d

# Or manually
docker network create cell0-net

docker run -d \
  --name ollama \
  --network cell0-net \
  -v ollama-data:/root/.ollama \
  ollama/ollama:latest

docker run -d \
  --name cell0 \
  --network cell0-net \
  -p 18800:18800 \
  -e OLLAMA_URL=http://ollama:11434 \
  ghcr.io/cell0-os/cell0:latest
```

---

## Package Managers

### Homebrew

```bash
brew install cell0-os
brew services start cell0-os
```

### APT (Debian/Ubuntu)

```bash
sudo apt install cell0-os
sudo systemctl enable --now cell0
```

### Snap (Ubuntu/Universal)

```bash
sudo snap install cell0
sudo snap connect cell0:home
```

### AUR (Arch Linux)

```bash
yay -S cell0-os
# or
paru -S cell0-os
```

---

## Kubernetes Deployment

### Using Helm

```bash
# Add Helm repository
helm repo add cell0 https://charts.cell0.io
helm repo update

# Install
helm install cell0 cell0/cell0 \
  --namespace cell0 \
  --create-namespace \
  --set replicaCount=1

# Upgrade
helm upgrade cell0 cell0/cell0 --namespace cell0
```

### Using Kubectl

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl get pods -n cell0
kubectl logs -f deployment/cell0 -n cell0
```

### Helm Configuration

```yaml
# values.yaml
replicaCount: 1

image:
  repository: ghcr.io/cell0-os/cell0
  tag: "1.2.0"

service:
  type: LoadBalancer
  port: 18800

ingress:
  enabled: true
  hosts:
    - host: cell0.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 2000m
    memory: 8Gi
  requests:
    cpu: 500m
    memory: 2Gi

persistence:
  enabled: true
  size: 50Gi

ollama:
  enabled: true
```

---

## Post-Installation

### Verify Installation

```bash
# Check service status
cell0ctl status

# Run diagnostics
cell0ctl doctor

# Test API
curl http://localhost:18800/health

# Test WebSocket
wscat -c ws://localhost:18801
```

### Configuration

```bash
# Edit configuration
cell0ctl config edit

# Set environment variables
export CELL0_ENV=production
export CELL0_LOG_LEVEL=info
export CELL0_PORT=18800
```

### First Run Setup

```bash
# Interactive setup wizard
cell0ctl setup

# Pull default models
ollama pull qwen2.5:7b

# Start services
cell0ctl start
```

### Service Management

**macOS:**
```bash
# Start
launchctl load ~/Library/LaunchAgents/io.cell0.daemon.plist

# Stop
launchctl unload ~/Library/LaunchAgents/io.cell0.daemon.plist

# Check status
launchctl list | grep cell0
```

**Linux (systemd):**
```bash
# Enable and start
systemctl --user enable cell0d
systemctl --user start cell0d

# Check status
systemctl --user status cell0d

# View logs
journalctl --user -u cell0d -f
```

**Docker:**
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

---

## Troubleshooting

### Installation Issues

**Python version too old:**
```bash
# Install Python 3.11
brew install python@3.11  # macOS
sudo apt install python3.11  # Ubuntu
```

**Permission denied:**
```bash
# Fix permissions
sudo chown -R $USER:$USER ~/.cell0
sudo chown -R $USER:$USER ~/cell0
```

**Port already in use:**
```bash
# Find and kill process
lsof -i :18800
kill -9 <PID>

# Or change port
export CELL0_PORT=18880
```

### Runtime Issues

**Ollama not found:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Or run in Docker
docker run -d -p 11434:11434 ollama/ollama
```

**Out of memory:**
```bash
# Use smaller models
ollama pull qwen2.5:3b

# Limit memory usage
export CELL0_MAX_AGENTS=2
```

**Import errors:**
```bash
# Reinstall dependencies
cd ~/cell0
source venv/bin/activate
pip install -e ".[dev]"
```

### Getting Help

- Documentation: https://docs.cell0.io
- GitHub Issues: https://github.com/cell0-os/cell0/issues
- Discord: https://discord.gg/cell0
- Email: support@cell0.io

---

## Uninstallation

### macOS

```bash
# Homebrew
brew uninstall cell0
brew untap cell0-os/cell0

# Manual
rm -rf ~/cell0
rm -rf ~/.cell0
rm ~/Library/LaunchAgents/io.cell0.daemon.plist
```

### Linux

```bash
# APT
sudo apt remove cell0-os
sudo apt autoremove

# Manual
rm -rf ~/cell0
rm -rf ~/.cell0
rm ~/.config/systemd/user/cell0d.service
```

### Docker

```bash
docker-compose down -v  # Remove volumes too
docker rmi ghcr.io/cell0-os/cell0
```

---

*Last updated: 2026-02-18*
*Version: 1.2.0*
