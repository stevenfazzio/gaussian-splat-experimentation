# Capturing Your Own Scenes

Turn real-world photos into Gaussian splats using COLMAP + OpenSplat.

## Requirements

```bash
brew install colmap
```

## Workflow

### 1. Take Photos

Capture 30-100 overlapping photos of your subject:

- **Walk around** the object/scene, covering all angles
- **Overlap 60-80%** between consecutive photos (each photo should share most of its view with the next)
- **Consistent lighting** -- avoid mixed indoor/outdoor lighting or flash
- **Sharp images** -- avoid motion blur
- **Avoid moving objects** -- people, cars, etc. will cause artifacts
- **Avoid reflective/transparent surfaces** -- mirrors, glass, and water confuse reconstruction

An iPhone or any modern phone camera works great.

### 2. Organize Photos

```bash
mkdir -p capture/scenes/my-scene/images
# Copy your photos into the images directory
cp ~/Photos/*.jpg capture/scenes/my-scene/images/
```

### 3. Run COLMAP

```bash
./capture/run-colmap.sh capture/scenes/my-scene
```

This extracts camera positions and a sparse point cloud from your photos. It may take several minutes depending on image count.

### 4. Train with OpenSplat

```bash
./training/train.sh capture/scenes/my-scene
```

### 5. View the Result

```bash
./scripts/serve.sh
# Open http://localhost:8080/viewer/?url=splats/my-scene.ply
```

## Tips for Good Results

| Tip | Why |
|-----|-----|
| More photos > fewer photos | Better coverage = fewer holes |
| Overlap heavily | COLMAP needs matching features between images |
| Consistent exposure | Varying brightness confuses color reconstruction |
| Start small | Try 30 photos of a simple object first |
| Avoid textureless surfaces | Plain white walls have no features to match |

## Scene Directory Structure

After COLMAP processing:

```
capture/scenes/my-scene/
├── images/          # Your original photos
├── database.db      # COLMAP feature database
└── sparse/
    └── 0/
        ├── cameras.bin    # Camera intrinsics
        ├── images.bin     # Camera poses
        └── points3D.bin   # Sparse point cloud
```

## Troubleshooting

**COLMAP fails to reconstruct**
- Check that images overlap sufficiently
- Try with fewer, higher-quality images
- Ensure the scene has enough visual texture

**Poor splat quality**
- Increase training iterations: `./training/train.sh capture/scenes/my-scene -n 7000`
- Add more photos from problem angles
- Ensure consistent lighting in photos
