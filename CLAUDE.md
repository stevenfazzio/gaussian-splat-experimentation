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

# Analysis scripts (requires: pip install umap-learn plotly)
python3 scripts/umap-splat.py <file.ply>                            # UMAP embedding of splat parameters -> interactive HTML
python3 scripts/umap-splat.py <file.ply> --features shape           # embed shape only (scale+rotation)
python3 scripts/umap-splat.py <file.ply> --color-by opacity         # color by opacity instead of position
```

## Architecture

**Three-stage pipeline:**

1. **Capture** (`capture/`): `run-colmap.sh` runs COLMAP feature extraction, matching, and sparse reconstruction. Input: `scenes/<name>/images/`. Output: `scenes/<name>/sparse/0/` (cameras.bin, images.bin, points3D.bin).

2. **Training** (`training/`): `train.sh` runs OpenSplat (C++ binary at `training/opensplat/build/opensplat`) with `KMP_DUPLICATE_LIB_OK=TRUE` to avoid libomp crashes. Outputs `.ply` directly to `viewer/splats/`. Automatically runs `trim-splat.py` (outlier removal) and `scene-info.py` post-training.

3. **Viewer** (`viewer/`):
   - `index.html`: Redirects to `supersplat.html` with query params preserved.
   - `supersplat.html`: Viewer using PlayCanvas SuperSplat via CDN. Auto-computes orbit center and camera orientation from splat bounding box. Usage: `http://localhost:8080/viewer/?url=splats/my-scene.ply`. Also supports `?noui`, `?settings=<url>`.

**Analysis scripts** (`scripts/`):
- `umap-splat.py`: UMAP dimensionality reduction on non-positional Gaussian parameters. Embeds shape (scale+rotation), appearance (SH+opacity), or combined features into 2D. Outputs interactive Plotly HTML. Supports coloring by spatial position, opacity, or scale.

## Documentation

- `README.md`: User-facing project overview, quickstart, and structure. Keep in sync with changes to the pipeline or viewers.

## Important Conventions

- Splat binary files (`.ply`, `.splat`, `.spz`, `.ksplat`) are gitignored. So are `training/datasets/*/`, `training/opensplat/`, and `capture/scenes/*/`.
- Training output always goes to `viewer/splats/` so it's immediately viewable.
- The viewer requires a local HTTP server (ES module imports don't work over `file://`).
- OpenSplat is built with `-DGPU_RUNTIME=MPS` for Metal acceleration.
- Python scripts require `numpy`. Analysis scripts additionally require `umap-learn` and `plotly`.
