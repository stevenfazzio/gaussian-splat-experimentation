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
python3 scripts/trim-splat.py <file.ply> [output.ply]               # remove outlier gaussians (distance+opacity+scale)
python3 scripts/scene-info.py <file.ply>                           # compute scene center -> scene-info.json
python3 scripts/align-splat.py <in.ply> <cameras.json> <out.ply>   # rotate to Y-up + recenter
```

## Architecture

**Three-stage pipeline:**

1. **Capture** (`capture/`): `run-colmap.sh` runs COLMAP feature extraction, matching, and sparse reconstruction. Input: `scenes/<name>/images/`. Output: `scenes/<name>/sparse/0/` (cameras.bin, images.bin, points3D.bin).

2. **Training** (`training/`): `train.sh` runs OpenSplat (C++ binary at `training/opensplat/build/opensplat`) with `KMP_DUPLICATE_LIB_OK=TRUE` to avoid libomp crashes. Outputs `.ply` directly to `viewer/splats/`. Automatically runs `trim-splat.py` (outlier removal) and `scene-info.py` post-training.

3. **Viewer** (`viewer/`):
   - `index.html`: Redirects to `supersplat.html` with query params preserved.
   - `supersplat.html`: Viewer using PlayCanvas SuperSplat via CDN. Auto-computes orbit center and camera orientation from splat bounding box. Usage: `http://localhost:8080/viewer/?url=splats/my-scene.ply`. Also supports `?noui`, `?settings=<url>`.

**Post-processing scripts** (`scripts/`):
- `trim-splat.py`: Removes outlier gaussians using distance, opacity, and scale filters. Run automatically by `train.sh`.
- `scene-info.py`: Reads PLY vertex positions, computes trimmed-median center, writes `scene-info.json`.
- `align-splat.py`: Rotates PLY so scene up -> +Y, recenters to origin, transforms cameras.json alongside.

## Documentation

- `README.md`: User-facing project overview, quickstart, and structure. Keep in sync with changes to the pipeline or viewers.

## Important Conventions

- Splat binary files (`.ply`, `.splat`, `.spz`, `.ksplat`) are gitignored. So are `training/datasets/*/`, `training/opensplat/`, and `capture/scenes/*/`.
- Training output always goes to `viewer/splats/` so it's immediately viewable.
- The viewer requires a local HTTP server (ES module imports don't work over `file://`).
- OpenSplat is built with `-DGPU_RUNTIME=MPS` for Metal acceleration.
- Python scripts require `numpy` (used by both `scene-info.py` and `align-splat.py`).
