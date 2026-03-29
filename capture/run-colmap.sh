#!/bin/bash
set -e

SCENE=""

usage() {
  echo "Usage: $0 <scene-directory>"
  echo ""
  echo "Runs COLMAP to extract camera poses from photos."
  echo "The scene directory must contain an 'images/' subdirectory with your photos."
  echo ""
  echo "Example:"
  echo "  mkdir -p capture/scenes/my-scene/images"
  echo "  # Copy your photos into capture/scenes/my-scene/images/"
  echo "  $0 capture/scenes/my-scene"
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

SCENE="$1"

# Resolve relative paths
if [[ ! "$SCENE" = /* ]]; then
  SCENE="$(pwd)/$SCENE"
fi

# Validate
if ! command -v colmap &>/dev/null; then
  echo "COLMAP not found. Install it with:"
  echo "  brew install colmap"
  exit 1
fi

if [ ! -d "$SCENE/images" ]; then
  echo "No images/ directory found in $SCENE"
  echo "Create it and add your photos first:"
  echo "  mkdir -p $SCENE/images"
  exit 1
fi

IMAGE_COUNT=$(ls "$SCENE/images" | wc -l | tr -d ' ')
echo "=== COLMAP Processing ==="
echo "Scene:  $SCENE"
echo "Images: $IMAGE_COUNT"
echo ""

if [ "$IMAGE_COUNT" -lt 3 ]; then
  echo "Warning: COLMAP needs at least 3 images. More is better (30-100 recommended)."
fi

DB_PATH="$SCENE/database.db"
SPARSE_PATH="$SCENE/sparse"

# Step 1: Feature extraction
echo "[1/3] Extracting features..."
colmap feature_extractor \
  --database_path "$DB_PATH" \
  --image_path "$SCENE/images" \
  --ImageReader.camera_model OPENCV \
  --ImageReader.single_camera 1

# Step 2: Feature matching
echo ""
echo "[2/3] Matching features..."
if [ "$IMAGE_COUNT" -gt 500 ]; then
  echo "      (Using sequential matching for large image set)"
  colmap sequential_matcher --database_path "$DB_PATH"
else
  colmap exhaustive_matcher --database_path "$DB_PATH"
fi

# Step 3: Sparse reconstruction
echo ""
echo "[3/3] Running sparse reconstruction..."
mkdir -p "$SPARSE_PATH"
colmap mapper \
  --database_path "$DB_PATH" \
  --image_path "$SCENE/images" \
  --output_path "$SPARSE_PATH"

echo ""
echo "=== COLMAP complete! ==="
echo "Output: $SPARSE_PATH"
echo ""
echo "Next: train a Gaussian splat from this scene:"
echo "  ./training/train.sh $1"
