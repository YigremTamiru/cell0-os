# Cell 0 Deployment Guide

## Deployment Options

Cell 0 supports multiple deployment scenarios:

1. **Development**: Local installation on macOS/Linux
2. **Docker**: Containerized deployment
3. **Server**: Production Linux server
4. **Embedded**: Edge devices and IoT
5. **Cloud**: Kubernetes/Helm deployment

## Quick Reference

| Method | Best For | Setup Time | Complexity |
|--------|----------|------------|------------|
| Local | Development | 5 min | Low |
| Docker | Testing, CI/CD | 10 min | Low |
| Server | Production single-node | 30 min | Medium |
| K8s | Production multi-node | 1 hour | High |

## 1. Local Development Deployment

### macOS (Apple Silicon Optimized)

```bash
# 1. Install dependencies
brew install python@3.11 rust ollama

# 2. Clone repository
git clone https://github.com/cell0/cell0.git ~/cell0
cd ~/cell0

# 3. Run setup
./setup.sh

# 4. Start services
ollama serve &  # Terminal 1
./start.sh      # Terminal 2

# 5. Access
open http://localhost:18800
```

### Linux (Ubuntu/Debian)

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip rustc cargo curl

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 3. Clone and setup
git clone https://github.com/cell0/cell0.git ~/cell0
cd ~/cell0
./setup.sh

# 4. Start
sudo systemctl start ollama
./start.sh
```

## 2. Docker Deployment

### Single Container

```bash
# Build image
docker build -t cell0:latest -f docker/Dockerfile .

# Run with volume for persistence
docker run -d \
  --name cell0 \
  -p 18800:18800 \
  -p 11434:11434 \
  -v cell0_data:/data \
  --gpus all \
  cell0:latest
```

### Docker Compose (Recommended)

```yaml
# docker-compose.yml
version: '3.8'

services:
  cell0:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "18800:18800"
    volumes:
      - cell0_data:/data
      - ./config:/app/config:ro
    environment:
      - CELL0_ENV=production
      - CELL0_LOG_LEVEL=info
    depends_on:
      - ollama
    networks:
      - cell0_net
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - cell0_net
    restart: unless-stopped

volumes:
  cell0_data:
  ollama_data:

networks:
  cell0_net:
    driver: bridge
```

Run:
```bash
docker-compose up -d
```

### Docker with GPU Support

```bash
# NVIDIA GPUs
docker run -d \
  --name cell0 \
  --gpus all \
  -p 18800:18800 \
  -v cell0_data:/data \
  cell0:latest

# AMD GPUs
docker run -d \
  --name cell0 \
  --device /dev/kfd \
  --device /dev/dri \
  -p 18800:18800 \
  -v cell0_data:/data \
  cell0:latest
```

## 3. Production Server Deployment

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 32+ GB |
| Storage | 50 GB SSD | 200+ GB NVMe |
| GPU | Optional | NVIDIA RTX 4090 / A100 |
| Network | 100 Mbps | 1 Gbps |

### Ubuntu 22.04 LTS Setup

```bash
#!/bin/bash
# deploy/production-setup.sh

set -e

echo "=== Cell 0 Production Setup ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    python3-pip rustc cargo \
    nginx certbot python3-certbot-nginx \
    git curl wget htop vim \
    nvidia-driver-535  # If using NVIDIA GPU

# Create cell0 user
sudo useradd -r -s /bin/false cell0 || true
sudo mkdir -p /opt/cell0
sudo chown cell0:cell0 /opt/cell0

# Install Ollama
sudo -u cell0 curl -fsSL https://ollama.com/install.sh | sh

# Clone Cell 0
sudo -u cell0 git clone https://github.com/cell0/cell0.git /opt/cell0

# Setup Python environment
cd /opt/cell0
sudo -u cell0 python3.11 -m venv venv
sudo -u cell0 venv/bin/pip install -r service/requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/cell0.service > /dev/null <<EOF
[Unit]
Description=Cell 0 Sovereign OS
After=network.target ollama.service

[Service]
Type=simple
User=cell0
Group=cell0
WorkingDirectory=/opt/cell0
Environment=CELL0_ENV=production
Environment=CELL0_LOG_LEVEL=info
Environment=PYTHONPATH=/opt/cell0
ExecStart=/opt/cell0/venv/bin/python service/cell0d.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create Ollama service override for network access
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable cell0 ollama
sudo systemctl start ollama
sleep 5  # Wait for Ollama
sudo systemctl start cell0

echo "=== Setup Complete ==="
echo "Cell 0 is running on http://localhost:18800"
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/cell0
server {
    listen 80;
    server_name cell0.yourdomain.com;
    
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cell0.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/cell0.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cell0.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:18800/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # API and static files
    location / {
        proxy_pass http://localhost:18800;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running inference
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/cell0 /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# SSL certificate
sudo certbot --nginx -d cell0.yourdomain.com
```

## 4. Kubernetes Deployment

### Helm Chart

```yaml
# helm/cell0/values.yaml
replicaCount: 1

image:
  repository: cell0/cell0
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 18800

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
  hosts:
    - host: cell0.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: cell0-tls
      hosts:
        - cell0.yourdomain.com

resources:
  limits:
    cpu: 4000m
    memory: 32Gi
    nvidia.com/gpu: 1
  requests:
    cpu: 1000m
    memory: 8Gi

persistence:
  enabled: true
  size: 100Gi
  storageClass: fast-ssd

ollama:
  enabled: true
  resources:
    limits:
      nvidia.com/gpu: 1
```

Deploy:
```bash
# Add Helm repo
helm repo add cell0 https://charts.cell0.io
helm repo update

# Install
helm install cell0 cell0/cell0 \
  --namespace cell0 \
  --create-namespace \
  --values values-production.yaml
```

### Raw Kubernetes Manifests

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell0

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cell0
  namespace: cell0
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cell0
  template:
    metadata:
      labels:
        app: cell0
    spec:
      containers:
      - name: cell0
        image: cell0/cell0:latest
        ports:
        - containerPort: 18800
        env:
        - name: CELL0_ENV
          value: "production"
        resources:
          limits:
            memory: "32Gi"
            cpu: "4000m"
            nvidia.com/gpu: 1
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: cell0-data

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: cell0
  namespace: cell0
spec:
  selector:
    app: cell0
  ports:
  - port: 80
    targetPort: 18800
  type: ClusterIP

---
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cell0-data
  namespace: cell0
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
```

Apply:
```bash
kubectl apply -f k8s/
```

## 5. Edge/IoT Deployment

### Raspberry Pi 5

```bash
# Optimized for ARM64, limited resources
# Use smaller models (3B instead of 7B)

# Install lightweight dependencies
sudo apt install -y python3-pip rustc

# Use Quantized models only
export OLLAMA_MODELS="qwen2.5:3b,phi3:mini"

# Run with limited workers
export CELL0_WORKERS=1
export CELL0_MAX_AGENTS=2

./start.sh
```

### NVIDIA Jetson

```bash
# Optimized for Jetson Orin
# Uses TensorRT acceleration

# Install JetPack dependencies
sudo apt install -y nvidia-jetpack python3-pip

# Build with Jetson optimizations
docker build -f docker/Dockerfile.jetson -t cell0:jetson .

# Run with GPU access
docker run --runtime nvidia -p 18800:18800 cell0:jetson
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELL0_ENV` | `development` | Environment mode |
| `CELL0_LOG_LEVEL` | `info` | Logging level |
| `CELL0_PORT` | `18800` | HTTP server port |
| `CELL0_HOST` | `0.0.0.0` | Bind address |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `CELL0_WORKERS` | `4` | Number of workers |
| `CELL0_MAX_AGENTS` | `10` | Max concurrent agents |
| `CELL0_DATA_DIR` | `~/.cell0` | Data directory |

### Configuration File

```yaml
# config/cell0.yaml
server:
  host: 0.0.0.0
  port: 18800
  workers: 4

logging:
  level: info
  format: json
  output: /var/log/cell0/cell0.log

ollama:
  url: http://localhost:11434
  default_model: qwen2.5:7b
  timeout: 120

inference:
  max_tokens: 4096
  temperature: 0.7
  top_p: 0.9

agents:
  max_concurrent: 10
  default_timeout: 300
  sandbox_enabled: true

security:
  api_key_required: false
  allowed_hosts:
    - localhost
    - cell0.yourdomain.com
  cors_origins:
    - https://cell0.yourdomain.com

tpV:
  max_entries: 10000
  auto_backup: true
  backup_interval: 86400
```

## Monitoring

### Prometheus Metrics

Cell 0 exposes metrics at `/metrics`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'cell0'
    static_configs:
      - targets: ['localhost:18800']
    metrics_path: /metrics
```

### Grafana Dashboard

Import `monitoring/grafana-dashboard.json` for pre-configured dashboards.

### Health Checks

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /api/health
    port: 18800
  initialDelaySeconds: 30
  periodSeconds: 10

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /api/health
    port: 18800
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Backup and Recovery

### Automated Backups

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backup/cell0/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup TPV profiles
cp -r ~/.cell0/tpv "$BACKUP_DIR/"

# Backup models (optional, can be re-downloaded)
# cp -r ~/.ollama "$BACKUP_DIR/"

# Backup config
cp -r ~/cell0/config "$BACKUP_DIR/"

# Create archive
tar czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Backup created: $BACKUP_DIR.tar.gz"
```

### Recovery

```bash
#!/bin/bash
# scripts/restore.sh

BACKUP_FILE="$1"

# Stop services
sudo systemctl stop cell0

# Restore data
tar xzf "$BACKUP_FILE" -C /

# Start services
sudo systemctl start cell0

echo "Restored from $BACKUP_FILE"
```

## Troubleshooting

### Common Issues

**Ollama Connection Failed**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama
```

**Out of Memory**
```bash
# Use smaller models
export OLLAMA_MODELS="qwen2.5:3b"

# Reduce workers
export CELL0_WORKERS=2
```

**Port Already in Use**
```bash
# Find process using port 18800
sudo lsof -i :18800

# Kill or reconfigure
```

## Security Hardening

### Firewall Rules

```bash
# UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 18800/tcp  # If not behind reverse proxy
sudo ufw enable

# Or iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 18800 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 18800 -j DROP
```

### Fail2ban

```ini
# /etc/fail2ban/jail.local
[cell0]
enabled = true
port = http,https
filter = cell0
logpath = /var/log/cell0/cell0.log
maxretry = 5
bantime = 3600
```

## Performance Tuning

### System Tuning

```bash
# Increase file descriptors
ulimit -n 65536

# Add to /etc/security/limits.conf
cell0 soft nofile 65536
cell0 hard nofile 65536

# Kernel parameters
# /etc/sysctl.conf
net.core.somaxconn = 65535
vm.swappiness = 10
```

### Model Optimization

```bash
# Use quantized models for faster inference
ollama pull qwen2.5:7b-q4_K_M

# Enable GPU offloading
export OLLAMA_GPU_LAYERS=35
```

## Support

For deployment assistance:
- Documentation: https://docs.cell0.io
- Discord: https://discord.gg/cell0
- Issues: https://github.com/cell0/cell0/issues
