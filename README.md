# Gaussian Splat Experimentation

A hands-on project for learning and experimenting with [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) on macOS (Apple Silicon).

## Quickstart

**See a Gaussian splat in your browser in under 60 seconds:**

```bash
# Start a local server
./scripts/serve.sh

# Open the viewer
open http://localhost:8080/viewer/
```

The viewer loads a demo scene automatically. Drag and drop your own `.ply` or `.splat` files to view them.

## Project Structure

### 1. [Viewer](viewer/) — Browser-based splat viewer
A single HTML file that renders Gaussian splats using [Spark](https://sparkjs.dev/) and Three.js. No build tools required.

- Orbit, pan, and zoom controls
- Drag-and-drop local files
- Load splats via URL parameter: `?url=splats/my-scene.ply`

### 2. [Training](training/) — Train splats with OpenSplat
Build and run [OpenSplat](https://github.com/pierotofy/opensplat) with Metal GPU acceleration on Apple Silicon.

```bash
# One-time setup: install deps and build OpenSplat
./training/setup.sh

# Download sample dataset
./scripts/download-banana-dataset.sh

# Train (outputs to viewer/splats/ for immediate viewing)
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
