#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_DIR/training/datasets/banana"

if [ -d "$DEST" ] && [ "$(ls -A "$DEST" 2>/dev/null)" ]; then
  echo "Banana dataset already exists at $DEST"
  exit 0
fi

echo "=== Downloading Banana Dataset ==="
echo "This is a small COLMAP-processed dataset for testing OpenSplat."
echo ""

# Install gdown if needed (Google Drive CLI downloader)
if ! command -v gdown &>/dev/null; then
  echo "Installing gdown (Google Drive downloader)..."
  pip3 install --user gdown
fi

mkdir -p "$DEST"

# Google Drive file ID for the banana dataset
FILE_ID="1mUUZFDo2swd6CE5vwPPkjN63Hyf4XyEv"

echo "Downloading from Google Drive..."
cd "$REPO_DIR/training/datasets"
gdown "$FILE_ID" -O banana.zip

echo "Extracting..."
unzip -o banana.zip -d banana_tmp
# Move contents to the banana directory (handle nested folders)
if [ -d "banana_tmp/banana" ]; then
  mv banana_tmp/banana/* "$DEST/" 2>/dev/null || true
  rm -rf banana_tmp
elif [ -d "banana_tmp" ]; then
  mv banana_tmp/* "$DEST/" 2>/dev/null || true
  rm -rf banana_tmp
fi
rm -f banana.zip

echo ""
echo "=== Download complete! ==="
echo "Dataset: $DEST"
echo ""
echo "Next: ./training/train.sh training/datasets/banana"
