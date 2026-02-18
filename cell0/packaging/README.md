# Cell 0 OS Packaging Guide

This document describes how to build and distribute Cell 0 OS packages for various platforms.

## Overview

Cell 0 OS supports multiple distribution methods:

| Method | Platforms | Status |
|--------|-----------|--------|
| Homebrew Formula | macOS | Ready |
| APT Package | Debian/Ubuntu | Ready |
| Docker Image | All | Ready |
| Helm Chart | Kubernetes | Ready |
| Snap | Ubuntu/Universal | Planned |
| AUR | Arch Linux | Planned |
| MSI | Windows | Planned |

---

## Homebrew (macOS)

### Prerequisites

- macOS 10.14+
- Homebrew installed
- GitHub access

### Building

```bash
cd packaging/homebrew

# Generate SHA256 for the tarball
wget https://github.com/cell0-os/cell0/archive/refs/tags/v1.2.0.tar.gz
shasum -a 256 v1.2.0.tar.gz
# Update the SHA256 in cell0.rb

# Test formula locally
brew install --build-from-source ./cell0.rb

# Audit formula
brew audit --strict cell0.rb
```

### Publishing

1. Create a tap repository: `homebrew-cell0`
2. Push formula to the tap
3. Users can install via: `brew tap cell0-os/cell0 && brew install cell0`

### Automated Releases

```bash
# Update formula version
./scripts/update-homebrew.sh 1.2.0

# Submit to homebrew-core (for official inclusion)
brew bump-formula-pr cell0 --version=1.2.0
```

---

## APT (Debian/Ubuntu)

### Prerequisites

- Debian/Ubuntu system
- `dpkg-deb`, `dpkg-sig` tools
- GPG key for signing

### Building

```bash
cd packaging/debian

# Run build script
./build.sh

# Or manually
dpkg-deb --build build/deb/cell0-os_1.2.0_amd64

# Sign package
dpkg-sig -k YOUR-GPG-KEY -s builder cell0-os_1.2.0_amd64.deb
```

### Repository Setup

```bash
# Create repository structure
mkdir -p apt-repo/pool/main/apt-repo/dists/stable/main/binary-amd64

# Copy package
cp *.deb apt-repo/pool/main/

# Generate Packages file
cd apt-repo
dpkg-scanpackages pool/main /dev/null > dists/stable/main/binary-amd64/Packages
gzip -9c dists/stable/main/binary-amd64/Packages > dists/stable/main/binary-amd64/Packages.gz

# Generate Release file
cat > dists/stable/Release << EOF
Origin: Cell 0 OS
Label: Cell 0 OS Repository
Suite: stable
Codename: stable
Architectures: amd64 arm64
Components: main
Description: Cell 0 OS APT Repository
EOF

# Sign Release file
gpg --armor --detach-sign -o dists/stable/Release.gpg dists/stable/Release
gpg --clearsign -o dists/stable/InRelease dists/stable/Release
```

### Publishing to S3/CloudFront

```bash
# Sync to S3
aws s3 sync apt-repo/ s3://apt.cell0.io/ --acl public-read

# Invalidate CloudFront
cf-invalidate E1234567890ABC /*
```

---

## Docker

### Prerequisites

- Docker 20.10+
- Docker Buildx
- Registry access (GitHub Container Registry)

### Building

```bash
# Build locally
docker build -t cell0:latest -f docker/Dockerfile .

# Build for multiple platforms
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t cell0:latest .

# Use build script
cd packaging/docker
./build.sh
```

### Tagging Strategy

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `1.2.0` | Specific version |
| `1.2` | Latest patch in minor version |
| `dev` | Development build |
| `nightly` | Nightly build from main |

### Pushing

```bash
# Tag for registry
docker tag cell0:latest ghcr.io/cell0-os/cell0:1.2.0
docker tag cell0:latest ghcr.io/cell0-os/cell0:latest

# Push
docker push ghcr.io/cell0-os/cell0:1.2.0
docker push ghcr.io/cell0-os/cell0:latest
```

### Multi-Stage Dockerfile

See `docker/Dockerfile` for:
- Stage 1: Builder (compiles dependencies)
- Stage 2: Production (minimal runtime image)
- Multi-platform support (amd64, arm64)

---

## Helm Chart

### Prerequisites

- Helm 3.12+
- Kubernetes cluster (for testing)
- Chart repository (GitHub Pages or ChartMuseum)

### Building

```bash
cd helm/cell0

# Lint chart
helm lint .

# Package chart
helm package . --destination ../../helm-repo

# Index repository
helm repo index ../../helm-repo --url https://charts.cell0.io
```

### Chart Structure

```
helm/cell0/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values
├── values-production.yaml  # Production overrides
├── README.md           # Chart documentation
├── templates/
│   ├── _helpers.tpl    # Template helpers
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── sa.yaml
│   └── NOTES.txt
└── crds/               # Custom Resource Definitions
```

### Publishing

```bash
# Update chart version
helm package helm/cell0

# Update index
helm repo index . --merge index.yaml

# Push to GitHub Pages
git add .
git commit -m "Release chart v1.2.0"
git push
```

---

## Release Checklist

### Pre-Release

- [ ] All tests passing
- [ ] Version bumped in:
  - `pyproject.toml`
  - `cell0/__init__.py`
  - `Cargo.toml` (kernel)
  - Documentation
- [ ] CHANGELOG.md updated
- [ ] Git tag created: `git tag -a v1.2.0 -m "Release 1.2.0"`

### Build Phase

- [ ] Docker images built and pushed
- [ ] Homebrew formula updated
- [ ] APT packages built and uploaded
- [ ] Helm chart packaged and indexed
- [ ] GitHub release created with artifacts

### Post-Release

- [ ] Installation tested on fresh systems
- [ ] Documentation updated
- [ ] Announcement published
- [ ] Docker Hub description updated

---

## Automated CI/CD

### GitHub Actions Workflow

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Build Docker images
      - name: Build Docker
        run: |
          docker buildx build --push \
            -t ghcr.io/cell0-os/cell0:${{ github.ref_name }} \
            -t ghcr.io/cell0-os/cell0:latest \
            .
      
      # Build APT package
      - name: Build APT
        run: |
          cd packaging/debian
          ./build.sh
      
      # Build Homebrew formula
      - name: Update Homebrew
        run: |
          ./scripts/update-homebrew.sh ${{ github.ref_name }}
      
      # Create GitHub release
      - name: Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            packaging/debian/*.deb
            helm-repo/*.tgz
```

---

## Testing Packages

### Docker Test

```bash
# Test fresh install
docker run --rm -it ubuntu:22.04 bash -c "
  apt-get update && apt-get install -y curl
  curl -fsSL https://cell0.io/install.sh | bash
  cell0ctl status
"
```

### VM Test

```bash
# Using Vagrant
cd tests/vagrant
vagrant up ubuntu2204
vagrant ssh ubuntu2204 -c "curl -fsSL https://cell0.io/install.sh | bash"
```

### Kubernetes Test

```bash
# Test Helm chart
kind create cluster
helm install cell0 ./helm/cell0 --namespace cell0 --create-namespace
kubectl wait --for=condition=ready pod -l app=cell0 -n cell0 --timeout=120s
```

---

## Troubleshooting

### Common Issues

**Docker build fails on ARM64:**
```bash
# Ensure buildx is using QEMU
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

**APT package dependencies:**
```bash
# Check dependencies
dpkg-deb -I cell0-os_1.2.0_amd64.deb | grep Depends
# Fix with: apt-get install -f
```

**Homebrew formula fails:**
```bash
# Debug build
brew install --debug --verbose ./cell0.rb
```

---

*For questions or issues, contact: team@cell0.io*
