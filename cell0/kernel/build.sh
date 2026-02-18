#!/bin/bash
# Cell0 Kernel Build Script
# Builds the Cell0 kernel with proper target configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Cell0 Kernel Build Script"
echo "========================================"

# Default to std build
BUILD_MODE="${1:-debug}"
FEATURES="${2:-std}"

echo "Build mode: $BUILD_MODE"
echo "Features: $FEATURES"

# Parse arguments
CARGO_ARGS=""

if [ "$BUILD_MODE" == "release" ]; then
    CARGO_ARGS="--release"
    echo "Building in release mode..."
else
    echo "Building in debug mode..."
fi

# Handle features
if [ "$FEATURES" == "bare_metal" ]; then
    echo "Building for bare metal (no_std)..."
    cargo build --no-default-features --features alloc $CARGO_ARGS
elif [ "$FEATURES" == "std" ]; then
    echo "Building with std support..."
    cargo build $CARGO_ARGS
else
    echo "Unknown features: $FEATURES"
    echo "Usage: $0 [debug|release] [std|bare_metal]"
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"

# Show output location
if [ "$BUILD_MODE" == "release" ]; then
    echo "Library: target/release/libcell0_kernel.rlib"
    echo "Binary:  target/release/cell0"
else
    echo "Library: target/debug/libcell0_kernel.rlib"
    echo "Binary:  target/debug/cell0"
fi

# Run tests if in debug mode
if [ "$BUILD_MODE" == "debug" ] && [ "$FEATURES" == "std" ]; then
    echo ""
    echo "Running tests..."
    cargo test --lib
fi

echo ""
echo "To run the kernel:"
if [ "$BUILD_MODE" == "release" ]; then
    echo "  ./target/release/cell0"
else
    echo "  ./target/debug/cell0"
fi
