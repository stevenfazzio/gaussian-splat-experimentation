#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OPENSPLAT="$SCRIPT_DIR/opensplat/build/opensplat"
OUTPUT_DIR="$REPO_DIR/viewer/splats"

# Defaults
ITERATIONS=2000
DATASET=""

usage() {
  echo "Usage: $0 <dataset-path> [-n iterations]"
  echo ""
  echo "  dataset-path   Path to a COLMAP/OpenSfM dataset directory"
  echo "  -n iterations  Number of training iterations (default: 2000)"
  echo ""
  echo "Examples:"
  echo "  $0 training/datasets/banana"
  echo "  $0 training/datasets/banana -n 7000"
  echo "  $0 capture/scenes/my-scene -n 3000"
}

# Parse arguments
if [ $# -lt 1 ]; then
  usage
  exit 1
fi

DATASET="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    -n) ITERATIONS="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

# Resolve dataset path
if [[ ! "$DATASET" = /* ]]; then
  DATASET="$REPO_DIR/$DATASET"
fi

# Validate
if [ ! -f "$OPENSPLAT" ]; then
  echo "OpenSplat not found at $OPENSPLAT"
  echo "Run ./training/setup.sh first."
  exit 1
fi

if [ ! -d "$DATASET" ]; then
  echo "Dataset not found: $DATASET"
  exit 1
fi

# Generate output filename from dataset name
DATASET_NAME=$(basename "$DATASET")
OUTPUT_FILE="$OUTPUT_DIR/${DATASET_NAME}.ply"

echo "=== OpenSplat Training ==="
echo "Dataset:    $DATASET"
echo "Iterations: $ITERATIONS"
echo "Output:     $OUTPUT_FILE"
echo ""

mkdir -p "$OUTPUT_DIR"

"$OPENSPLAT" "$DATASET" \
  -n "$ITERATIONS" \
  -o "$OUTPUT_FILE"

echo ""
echo "=== Training complete! ==="
echo "Output: $OUTPUT_FILE"
echo ""
echo "View your splat:"
echo "  ./scripts/serve.sh"
echo "  Open http://localhost:8080/viewer/?url=splats/${DATASET_NAME}.ply"
