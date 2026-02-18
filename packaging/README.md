# Cell 0 OS Package Building

This directory contains package definitions for various platforms.

## Directory Structure

```
packaging/
├── homebrew/          # Homebrew Formula
├── debian/           # Debian/Ubuntu .deb package
├── rpm/              # RHEL/CentOS/Fedora .rpm package
├── docker/           # Docker Compose configurations
├── arch/             # Arch Linux PKGBUILD
├── scripts/          # Build and test scripts
└── README.md         # This file
```

## Building Packages

### Homebrew

```bash
# Create tarball
tar czf cell0-1.2.0.tar.gz --exclude='.git' --exclude='venv' .

# Calculate SHA256
shasum -a 256 cell0-1.2.0.tar.gz

# Update formula with new SHA256
# Edit packaging/homebrew/cell0-os.rb

# Test formula
brew install --build-from-source ./packaging/homebrew/cell0-os.rb
brew test ./packaging/homebrew/cell0-os.rb
```

### Debian Package

```bash
# Install build dependencies
sudo apt-get install build-essential debhelper python3-all python3-setuptools

# Build package
cd packaging/debian
dpkg-buildpackage -us -uc -b

# Or using debuild
debuild -us -uc -b

# Install
cd ..
sudo dpkg -i cell0-os_1.2.0-1_all.deb
sudo apt-get install -f
```

### RPM Package

```bash
# Install build dependencies
sudo dnf install rpm-build rpmdevtools python3-devel

# Setup build tree
rpmdev-setuptree

# Copy spec file
cp packaging/rpm/cell0-os.spec ~/rpmbuild/SPECS/

# Copy source
tar czf ~/rpmbuild/SOURCES/cell0-1.2.0.tar.gz --exclude='.git' --exclude='venv' .

# Build
rpmbuild -ba ~/rpmbuild/SPECS/cell0-os.spec

# Install
sudo rpm -i ~/rpmbuild/RPMS/x86_64/cell0-os-1.2.0-1.x86_64.rpm
```

### Arch Linux

```bash
cd packaging/arch
makepkg -si
```

### Docker Image

```bash
# Build image
docker build -f cell0/docker/Dockerfile -t cell0-os:1.2.0 .

# Tag for registry
docker tag cell0-os:1.2.0 ghcr.io/cell0-os/cell0:1.2.0

# Push
docker push ghcr.io/cell0-os/cell0:1.2.0
```

## Testing Packages

### Automated Testing

```bash
# Run all package tests
./packaging/scripts/test_install.sh

# Run specific tests
./packaging/scripts/test_install.sh --test docker
./packaging/scripts/test_install.sh --test homebrew
```

### Manual Testing

**Fresh VM Test:**
```bash
# Create fresh VM or container
docker run -it --rm ubuntu:22.04 bash

# Install curl
apt-get update && apt-get install -y curl

# Run installer
curl -fsSL https://cell0.io/install.sh | bash

# Verify
cell0d --version
cell0ctl --version
```

**Upgrade Test:**
```bash
# Install old version
curl -fsSL https://cell0.io/install.sh | bash -s -- --version 1.1.0

# Upgrade
curl -fsSL https://cell0.io/install.sh | bash -s -- --version 1.2.0

# Verify
cell0d --version
```

## Release Process

1. **Update Version**
   - Update `CELL0_VERSION` in `install.sh`
   - Update version in `packaging/homebrew/cell0-os.rb`
   - Update version in `packaging/debian/changelog`
   - Update version in `packaging/rpm/cell0-os.spec`
   - Update version in `pyproject.toml`

2. **Create Tag**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

3. **Build Packages**
   - GitHub Actions will automatically build Docker images
   - Manually build platform packages (deb, rpm, etc.)

4. **Create Release**
   - Go to GitHub releases
   - Create new release from tag
   - Attach built packages

5. **Update Registry**
   - Push Homebrew formula to tap repository
   - Submit Arch AUR package
   - Update Docker Hub description

## CI/CD Integration

### GitHub Actions

Packages are automatically built in GitHub Actions:

- **Container Images:** `.github/workflows/container.yml`
- **Security Scans:** `.github/workflows/security.yml`
- **Tests:** `.github/workflows/tests.yml`

### Automated Publishing

```yaml
# .github/workflows/release.yml
name: Release Packages

on:
  push:
    tags:
      - 'v*'

jobs:
  build-packages:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Debian package
        run: |
          sudo apt-get install debhelper
          dpkg-buildpackage -us -uc -b
      
      - name: Upload to release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            ../cell0-os_*.deb
```

## Contributing Packages

To add support for a new platform:

1. Create directory: `packaging/<platform>/`
2. Add package definition files
3. Add test script: `packaging/scripts/test_<platform>.sh`
4. Update this README
5. Submit PR

## License

GPL-3.0 - See LICENSE file for details.
