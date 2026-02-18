#!/bin/bash
# Build Debian package for Cell 0 OS

set -euo pipefail

VERSION="1.2.0"
PACKAGE_NAME="cell0-os"
ARCH="amd64"
MAINTAINER="Cell 0 Team <team@cell0.io>"
DESCRIPTION="Sovereign Edge Model Operating System"

# Build directory
BUILD_DIR="build/deb"
PKG_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building Debian package for Cell 0 OS ${VERSION}..."

# Clean previous builds
rm -rf "${BUILD_DIR}"
mkdir -p "${PKG_DIR}"

# Create directory structure
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/cell0"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/lib/systemd/system"
mkdir -p "${PKG_DIR}/etc/cell0"
mkdir -p "${PKG_DIR}/var/lib/cell0"
mkdir -p "${PKG_DIR}/var/log/cell0"

# Copy application files
cp -r cell0/ "${PKG_DIR}/opt/cell0/"
cp cell0d.py "${PKG_DIR}/opt/cell0/"
cp cell0ctl.py "${PKG_DIR}/opt/cell0/"
cp -r config/ "${PKG_DIR}/opt/cell0/"
cp -r scripts/ "${PKG_DIR}/opt/cell0/"
cp pyproject.toml "${PKG_DIR}/opt/cell0/"

# Create control file
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: misc
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.9), python3-pip, python3-venv, git, curl
Recommends: ollama, redis-server
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 Cell 0 OS is a sovereign edge model operating system that enables
 local AI inference with a focus on privacy, security, and control.
 .
 Features:
  - Local LLM inference via Ollama
  - WebSocket API for real-time communication
  - Prometheus metrics and health monitoring
  - Modular agent system
  - TPV (Twin Prime Vector) coherence tracking
EOF

# Create preinst script
cat > "${PKG_DIR}/DEBIAN/preinst" << 'EOF'
#!/bin/bash
set -e

# Create cell0 user if not exists
if ! id -u cell0 >/dev/null 2>&1; then
    useradd --system --home /var/lib/cell0 --shell /bin/false cell0
fi

exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/preinst"

# Create postinst script
cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Create Python virtual environment
if [ ! -d /opt/cell0/venv ]; then
    python3 -m venv /opt/cell0/venv
fi

# Install Python dependencies
/opt/cell0/venv/bin/pip install --upgrade pip
/opt/cell0/venv/bin/pip install /opt/cell0

# Set permissions
chown -R cell0:cell0 /opt/cell0
chown -R cell0:cell0 /var/lib/cell0
chown -R cell0:cell0 /var/log/cell0

# Reload systemd
systemctl daemon-reload

echo "Cell 0 OS installed successfully!"
echo "Start with: sudo systemctl start cell0"
echo "Enable on boot: sudo systemctl enable cell0"

exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# Create prerm script
cat > "${PKG_DIR}/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

# Stop service if running
systemctl stop cell0 2>/dev/null || true

exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/prerm"

# Create systemd service
cat > "${PKG_DIR}/lib/systemd/system/cell0.service" << 'EOF'
[Unit]
Description=Cell 0 OS Daemon
Documentation=https://docs.cell0.io
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=cell0
Group=cell0
WorkingDirectory=/opt/cell0
Environment=CELL0_HOME=/opt/cell0
Environment=CELL0_STATE_DIR=/var/lib/cell0
Environment=CELL0_ENV=production
Environment=CELL0_LOG_LEVEL=INFO
Environment=PYTHONPATH=/opt/cell0
Environment=PATH=/opt/cell0/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/cell0/venv/bin/python /opt/cell0/cell0d.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cell0

[Install]
WantedBy=multi-user.target
EOF

# Create symlinks for executables
ln -s /opt/cell0/venv/bin/cell0ctl "${PKG_DIR}/usr/bin/cell0ctl"
ln -s /opt/cell0/venv/bin/cell0d "${PKG_DIR}/usr/bin/cell0d"

# Build the package
dpkg-deb --build "${PKG_DIR}"

echo ""
echo "Package built: ${PKG_DIR}.deb"
echo "Install with: sudo dpkg -i ${PKG_DIR}.deb"
echo "Or: sudo apt install ./${PKG_DIR}.deb"
