#!/bin/bash
# Docker build script for Cell 0 OS with multi-platform support

set -euo pipefail

VERSION="1.2.0"
REGISTRY="ghcr.io/cell0-os"
PLATFORMS="linux/amd64,linux/arm64"

echo "Building Cell 0 OS Docker images..."

# Ensure buildx is available
docker buildx create --use --name cell0-builder 2>/dev/null || docker buildx use cell0-builder

# Build main Cell 0 image (multi-platform)
echo "Building cell0:${VERSION}..."
docker buildx build \
    --platform "${PLATFORMS}" \
    -t "${REGISTRY}/cell0:${VERSION}" \
    -t "${REGISTRY}/cell0:latest" \
    -f docker/Dockerfile \
    --push \
    .

# Build kernel image
echo "Building cell0-kernel:${VERSION}..."
docker buildx build \
    --platform "${PLATFORMS}" \
    -t "${REGISTRY}/cell0-kernel:${VERSION}" \
    -t "${REGISTRY}/cell0-kernel:latest" \
    -f kernel/Dockerfile \
    --push \
    ./kernel

# Build development image
echo "Building cell0:dev..."
docker buildx build \
    --platform "${PLATFORMS}" \
    -t "${REGISTRY}/cell0:dev" \
    -f docker/Dockerfile.dev \
    --push \
    .

echo ""
echo "All images built successfully!"
echo ""
echo "Images:"
echo "  ${REGISTRY}/cell0:${VERSION}"
echo "  ${REGISTRY}/cell0-kernel:${VERSION}"
echo "  ${REGISTRY}/cell0:dev"
