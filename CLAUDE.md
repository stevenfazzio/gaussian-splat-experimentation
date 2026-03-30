# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A macOS Apple Silicon project for learning 3D Gaussian Splatting. The pipeline goes: capture photos -> COLMAP sparse reconstruction -> OpenSplat training -> browser viewer.

## Key Commands

```bash
# One-time: build OpenSplat with Metal/MPS support
./training/setup.sh

# Download sample dataset (banana, from Google Drive via gdown)
./scripts/download-banana-dataset.sh

# Train a splat (outputs .ply to viewer/splats/)
./training/train.sh training/datasets/banana          # default 2000 iterations
./training/train.sh training/datasets/banana -n 7000   # more iterations

# Process your own photos with COLMAP
./capture/run-colmap.sh capture/scenes/my-scene

# Serve the viewer (python3 http.server, default port 8080)
./scripts/serve.sh
# Then open http://localhost:8080/viewer/

# Post-processing scripts
python3 scripts/scene-info.py <file.ply>                           # compute scene center -> scene-info.json
python3 scripts/align-splat.py <in.ply> <cameras.json> <out.ply>   # rotate to Y-up + recenter
```

## Architecture

**Three-stage pipeline:**

1. **Capture** (`capture/`): `run-colmap.sh` runs COLMAP feature extraction, matching, and sparse reconstruction. Input: `scenes/<name>/images/`. Output: `scenes/<name>/sparse/0/` (cameras.bin, images.bin, points3D.bin).

2. **Training** (`training/`): `train.sh` runs OpenSplat (C++ binary at `training/opensplat/build/opensplat`) with `KMP_DUPLICATE_LIB_OK=TRUE` to avoid libomp crashes. Outputs `.ply` directly to `viewer/splats/`. Automatically runs `scene-info.py` post-training to generate `scene-info.json`.

3. **Viewer** (`viewer/index.html`): Single HTML file, no build step. Uses Three.js + Spark (SplatMesh) via CDN import maps. Supports `.ply`, `.splat`, `.spz`, `.ksplat` via URL param (`?url=splats/file.ply`) or drag-and-drop. Loads `cameras.json` and `scene-info.json` from the same directory as the splat to auto-configure orbit target and camera up direction. Currently includes debug visualization (axis lines, camera position dots).

**Post-processing scripts** (`scripts/`):
- `scene-info.py`: Reads PLY vertex positions, computes trimmed-median center, writes `scene-info.json`.
- `align-splat.py`: Rotates PLY so scene up -> +Y, recenters to origin, transforms cameras.json alongside.

## Important Conventions

- Splat binary files (`.ply`, `.splat`, `.spz`, `.ksplat`) are gitignored. So are `training/datasets/*/`, `training/opensplat/`, and `capture/scenes/*/`.
- Training output always goes to `viewer/splats/` so it's immediately viewable.
- The viewer requires a local HTTP server (ES module imports don't work over `file://`).
- OpenSplat is built with `-DGPU_RUNTIME=MPS` for Metal acceleration.
- Python scripts require `numpy` (used by both `scene-info.py` and `align-splat.py`).
