# Gaussian Splat Experimentation

A hands-on project for learning and experimenting with [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) on macOS (Apple Silicon).

## Quickstart

**See a Gaussian splat in your browser in under 60 seconds:**

```bash
# Start a local server
./scripts/serve.sh

# Open the viewer
open http://localhost:8080/viewer/supersplat.html?url=splats/my-scene.ply
```

Drag and drop your own `.ply` or `.splat` files to view them.

## Project Structure

### 1. [Viewer](viewer/) — Browser-based splat viewers

Two viewers, no build tools required:

- **`supersplat.html`** — Production viewer using [SuperSplat](https://github.com/playcanvas/supersplat). Auto-computes orbit center and camera orientation. Orbit, fly, and walk modes. Best for sharing.
  ```
  http://localhost:8080/viewer/supersplat.html?url=splats/my-scene.ply
  ```
- **`index.html`** — Debug viewer using [Spark](https://sparkjs.dev/) and Three.js. Shows camera positions, axes, and gaze intersection. Useful for inspecting raw COLMAP output.
  ```
  http://localhost:8080/viewer/?url=splats/my-scene.ply
  ```

Both support drag-and-drop for `.ply`, `.splat`, `.spz`, and `.ksplat` files.

### 2. [Training](training/) — Train splats with OpenSplat
Build and run [OpenSplat](https://github.com/pierotofy/opensplat) with Metal GPU acceleration on Apple Silicon.

```bash
# One-time setup: install deps and build OpenSplat
./training/setup.sh

# Download sample dataset
./scripts/download-banana-dataset.sh

# Train (outputs to viewer/splats/ for immediate viewing)
# Automatically trims outlier gaussians after training
./training/train.sh training/datasets/banana
```

### 3. [Capture](capture/) — Create splats from your own photos
Capture photos of a real scene, process with COLMAP, and train with OpenSplat.

```bash
# Process photos with COLMAP
./capture/run-colmap.sh capture/scenes/my-scene

# Train on the result
./training/train.sh capture/scenes/my-scene
```

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- [Homebrew](https://brew.sh/)
- A modern web browser (Chrome, Safari, Firefox)

See [training/README.md](training/README.md) for OpenSplat build requirements.
See [capture/README.md](capture/README.md) for COLMAP setup.
