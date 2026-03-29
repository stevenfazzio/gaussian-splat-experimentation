#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_DIR/viewer/splats"

echo "=== Downloading Sample Splat ==="
echo ""
echo "Downloading a pre-trained Gaussian splat for the viewer."
echo ""

mkdir -p "$DEST"

# Download a sample .spz file from Spark's assets
curl -L -o "$DEST/butterfly.spz" \
  "https://sparkjs.dev/assets/splats/butterfly.spz"

echo ""
echo "=== Download complete! ==="
echo "File: $DEST/butterfly.spz"
echo ""
echo "View it:"
echo "  ./scripts/serve.sh"
echo "  Open http://localhost:8080/viewer/?url=splats/butterfly.spz"
