# Cell 0 OS DevOps Infrastructure

This directory contains all DevOps and Kubernetes deployment infrastructure for Cell 0 OS.

## 📁 Directory Structure

```
.
├── docker/                     # Docker containerization
│   ├── Dockerfile             # Multi-stage production image
│   ├── docker-compose.yml     # Full production stack
│   └── healthcheck.sh         # Container health checks
│
├── k8s/                       # Kubernetes raw manifests
│   ├── namespace.yaml         # Namespace with security labels
│   ├── configmap.yaml         # Application configuration
│   ├── secrets.yaml           # Secrets template
│   ├── rbac.yaml              # Service account and RBAC
│   ├── pvc.yaml               # Persistent volume claim
│   ├── deployment.yaml        # Main application deployment
│   ├── service.yaml           # Service (ClusterIP + LoadBalancer)
│   ├── hpa.yaml               # Horizontal pod autoscaler
│   ├── pdb.yaml               # Pod disruption budget
│   ├── ingress.yaml           # Ingress with TLS
│   ├── servicemonitor.yaml    # Prometheus monitoring
│   ├── jobs.yaml              # Migration and utility jobs
│   └── kustomization.yaml     # Kustomize configuration
│
├── helm/                      # Helm chart
│   └── cell0/                 # Cell 0 OS Helm chart
│       ├── Chart.yaml         # Chart metadata
│       ├── values.yaml        # Default values
│       ├── values-production.yaml  # Production overrides
│       ├── README.md          # Chart documentation
│       └── templates/         # Helm templates
│
└── .github/workflows/         # CI/CD pipelines
    ├── container.yml          # Build, scan, and push images
    ├── deploy.yml             # Deploy to Kubernetes
    └── security.yml           # Security scanning
```

## 🐳 Docker

### Building the Image

```bash
# Build production image
docker build -f cell0/docker/Dockerfile -t cell0:latest .

# Build with specific target
docker build -f cell0/docker/Dockerfile --target production -t cell0:latest .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t cell0:latest .
```

### Running with Docker Compose

```bash
# Start full stack
cd cell0/docker
docker-compose up -d

# View logs
docker-compose logs -f cell0

# Scale cell0 service
docker-compose up -d --scale cell0=3
```

## ☸️ Kubernetes

### Using Raw Manifests

```bash
# Apply all manifests
kubectl apply -k cell0/k8s/

# Or apply individually
kubectl apply -f cell0/k8s/namespace.yaml
kubectl apply -f cell0/k8s/configmap.yaml
kubectl apply -f cell0/k8s/secrets.yaml
kubectl apply -f cell0/k8s/deployment.yaml
kubectl apply -f cell0/k8s/service.yaml
kubectl apply -f cell0/k8s/hpa.yaml
kubectl apply -f cell0/k8s/ingress.yaml
```

### Using Helm

```bash
# Install the chart
helm install cell0 ./helm/cell0

# Install with production values
helm install cell0 ./helm/cell0 -f ./helm/cell0/values-production.yaml

# Upgrade
helm upgrade cell0 ./helm/cell0

# Uninstall
helm uninstall cell0
```

## 🔒 Security

### Container Security

- Non-root user (UID 1000)
- Read-only root filesystem
- Security scanning with Trivy and Snyk
- Image signing with Cosign

### Kubernetes Security

- Pod Security Standards (restricted)
- Network policies
- RBAC with minimal permissions
- Secrets management

### CI/CD Security

- CodeQL analysis
- Dependency scanning
- Secret detection
- SAST with Semgrep
- Container scanning

## 📊 Monitoring

### Prometheus Metrics

- Application metrics on port 9090
- ServiceMonitor for Prometheus Operator
- Custom alert rules

### Health Checks

- Liveness probe: `/api/health/live`
- Readiness probe: `/api/health/ready`
- Startup probe: `/api/health/startup`

## 🚀 Deployment

### Environments

- **Staging**: Auto-deploy on push to `develop`
- **Production**: Deploy on tag push or manual trigger

### Rollback

```bash
# Rollback Helm deployment
helm rollback cell0 1

# Rollback Kubernetes deployment
kubectl rollout undo deployment/cell0 -n cell0
```

## 📋 Checklist for Production

- [ ] Update secrets in `secrets.yaml` or use external secret management
- [ ] Configure ingress hostnames
- [ ] Set up TLS certificates
- [ ] Configure resource limits based on workload
- [ ] Enable autoscaling thresholds
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategies
- [ ] Test disaster recovery procedures

## 🔧 Troubleshooting

### Container Issues

```bash
# Check container logs
docker logs cell0-os

# Execute into container
docker exec -it cell0-os /bin/sh

# Check health
curl http://localhost:18800/api/health
```

### Kubernetes Issues

```bash
# Check pod status
kubectl get pods -n cell0

# Describe pod
kubectl describe pod -n cell0 -l app.kubernetes.io/name=cell0

# View logs
kubectl logs -n cell0 -l app.kubernetes.io/name=cell0 --tail=100 -f

# Port forward for debugging
kubectl port-forward svc/cell0 18800:18800 -n cell0
```

### Helm Issues

```bash
# Debug template rendering
helm template cell0 ./helm/cell0 --debug

# Get release history
helm history cell0

# Lint chart
helm lint ./helm/cell0
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Cell 0 OS Documentation](../docs/)
