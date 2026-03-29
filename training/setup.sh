#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENSPLAT_DIR="$SCRIPT_DIR/opensplat"

echo "=== OpenSplat Setup (macOS + Metal) ==="
echo ""

# Check for Xcode CLI tools
if ! xcode-select -p &>/dev/null; then
  echo "Xcode Command Line Tools not found. Installing..."
  xcode-select --install
  echo "Please re-run this script after installation completes."
  exit 1
fi
echo "[ok] Xcode CLI tools found"

# Check for Homebrew
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Install it from https://brew.sh"
  exit 1
fi
echo "[ok] Homebrew found"

# Install dependencies
echo ""
echo "Installing dependencies via Homebrew..."
brew install cmake opencv pytorch libomp 2>/dev/null || true
brew link libomp --force 2>/dev/null || true
echo "[ok] Dependencies installed"

# Clone OpenSplat
echo ""
if [ -d "$OPENSPLAT_DIR" ]; then
  echo "OpenSplat already cloned at $OPENSPLAT_DIR"
  cd "$OPENSPLAT_DIR" && git pull
else
  echo "Cloning OpenSplat..."
  git clone https://github.com/pierotofy/opensplat.git "$OPENSPLAT_DIR"
  cd "$OPENSPLAT_DIR"
fi
echo "[ok] OpenSplat source ready"

# Determine libtorch path
echo ""
echo "Finding libtorch path..."
TORCH_CMAKE_PATH=$(python3 -c "import torch; print(torch.utils.cmake_prefix_path)" 2>/dev/null || true)

if [ -z "$TORCH_CMAKE_PATH" ]; then
  # Fallback: check Homebrew pytorch
  TORCH_CMAKE_PATH="$(brew --prefix pytorch)/share/cmake"
  if [ ! -d "$TORCH_CMAKE_PATH" ]; then
    echo "Could not find libtorch. Make sure PyTorch is installed:"
    echo "  brew install pytorch"
    echo "  # or: pip3 install torch"
    exit 1
  fi
fi
echo "[ok] libtorch found at: $TORCH_CMAKE_PATH"

# Build
echo ""
echo "Building OpenSplat with Metal (MPS) support..."
mkdir -p "$OPENSPLAT_DIR/build"
cd "$OPENSPLAT_DIR/build"
cmake -DCMAKE_PREFIX_PATH="$TORCH_CMAKE_PATH" -DGPU_RUNTIME=MPS ..
make -j$(sysctl -n hw.logicalcpu)

# Verify
echo ""
if [ -f "$OPENSPLAT_DIR/build/opensplat" ]; then
  echo "=== Build successful! ==="
  echo "Binary: $OPENSPLAT_DIR/build/opensplat"
  echo ""
  echo "Next steps:"
  echo "  1. Download a dataset:  ./scripts/download-banana-dataset.sh"
  echo "  2. Train a splat:       ./training/train.sh training/datasets/banana"
else
  echo "Build failed. Check the output above for errors."
  echo ""
  echo "Common fixes:"
  echo "  - libc10.dylib blocked: System Settings > Privacy & Security > Allow"
  echo "  - libomp not found: brew link libomp --force"
  exit 1
fi
