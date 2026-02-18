# Cell 0 OS Helm Chart

## Prerequisites

- Kubernetes 1.24+
- Helm 3.12+
- (Optional) Prometheus Operator for monitoring
- (Optional) cert-manager for TLS certificates
- (Optional) ingress-nginx for ingress

## Installation

### Quick Start

```bash
# Add the Helm repository (when published)
helm repo add cell0 https://charts.cell0.io
helm repo update

# Install with default values
helm install cell0 cell0/cell0

# Install with production values
helm install cell0 cell0/cell0 -f values-production.yaml
```

### From Source

```bash
# Clone the repository
git clone https://github.com/cell0-os/cell0.git
cd cell0

# Install the chart
helm install cell0 ./helm/cell0

# Upgrade
helm upgrade cell0 ./helm/cell0
```

## Configuration

### Required Values

Before deploying to production, you must set the following secrets:

```bash
# Create a secret with your values
kubectl create secret generic cell0-secrets \
  --from-literal=CELL0_SECRET_KEY=$(openssl rand -base64 32) \
  --from-literal=BRAVE_API_KEY=your-brave-key \
  --from-literal=SENTRY_DSN=your-sentry-dsn

# Install referencing the existing secret
helm install cell0 ./helm/cell0 --set existingSecret=cell0-secrets
```

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.tag` | Image tag | `1.1.5` |
| `resources.limits.memory` | Memory limit | `8Gi` |
| `resources.limits.cpu` | CPU limit | `4000m` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `ingress.enabled` | Enable ingress | `false` |
| `persistence.size` | PVC size | `10Gi` |

### Production Configuration

For production deployments, use the provided `values-production.yaml`:

```bash
helm install cell0 ./helm/cell0 -f ./helm/cell0/values-production.yaml \
  --set ingress.hosts[0].host=cell0.yourdomain.com
```

## Uninstallation

```bash
helm uninstall cell0
```

## Dependencies

This chart includes optional dependencies:

- **Redis**: For caching and session storage
- **PostgreSQL**: For persistent data storage

To disable dependencies:

```bash
helm install cell0 ./helm/cell0 --set redis.enabled=false,postgresql.enabled=false
```

## Monitoring

### Prometheus ServiceMonitor

Enable Prometheus monitoring:

```bash
helm install cell0 ./helm/cell0 --set serviceMonitor.enabled=true
```

### Alerting Rules

Enable Prometheus alerting rules:

```bash
helm install cell0 ./helm/cell0 \
  --set prometheusRule.enabled=true \
  --set prometheusRule.rules[0].alert=CustomAlert
```

## Security

### Pod Security Standards

This chart is compatible with the `restricted` Pod Security Standard.

### Network Policies

Enable network policies for added security:

```bash
helm install cell0 ./helm/cell0 --set networkPolicy.enabled=true
```

## Troubleshooting

### Pod not starting

Check the pod status:

```bash
kubectl get pods -n cell0
kubectl describe pod -n cell0 -l app.kubernetes.io/name=cell0
kubectl logs -n cell0 -l app.kubernetes.io/name=cell0
```

### HPA not scaling

Check HPA status:

```bash
kubectl get hpa -n cell0
kubectl describe hpa -n cell0 cell0
```

## Upgrading

### To 1.1.5

```bash
helm upgrade cell0 ./helm/cell0 --set image.tag=1.1.5
```

## Development

### Lint the chart

```bash
helm lint ./helm/cell0
```

### Render templates

```bash
helm template cell0 ./helm/cell0
```

### Run tests

```bash
helm test cell0
```
