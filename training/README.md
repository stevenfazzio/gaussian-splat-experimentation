# Training with OpenSplat

[OpenSplat](https://github.com/pierotofy/opensplat) is a C++ implementation of 3D Gaussian Splatting with Apple Metal GPU support.

## Quick Start

```bash
# Build OpenSplat (one-time setup)
./training/setup.sh

# Download sample dataset
./scripts/download-banana-dataset.sh

# Train (outputs to viewer/splats/)
./training/train.sh training/datasets/banana
```

Training the banana dataset at 2000 iterations takes ~12 minutes on Apple Silicon.

## Training Options

```bash
# More iterations = higher quality (but slower)
./training/train.sh training/datasets/banana -n 7000

# Train on a custom captured scene
./training/train.sh capture/scenes/my-scene -n 3000
```

Output `.ply` files are saved to `viewer/splats/` so you can view them immediately in the browser.

## Manual Build

If `setup.sh` doesn't work, you can build manually:

```bash
brew install cmake opencv pytorch libomp
brew link libomp --force

git clone https://github.com/pierotofy/opensplat.git training/opensplat
cd training/opensplat
mkdir build && cd build

# Find your libtorch path
TORCH_PATH=$(python3 -c "import torch; print(torch.utils.cmake_prefix_path)")

cmake -DCMAKE_PREFIX_PATH="$TORCH_PATH" -DGPU_RUNTIME=MPS ..
make -j$(sysctl -n hw.logicalcpu)
```

## Troubleshooting

**"libc10.dylib" blocked by macOS**
Go to System Settings > Privacy & Security and click "Allow Anyway". You may need to do this multiple times for different libraries.

**"libomp.dylib not found"**
```bash
brew link libomp --force
```

**Slow training**
Metal GPU acceleration is slower than NVIDIA CUDA but ~100x faster than CPU. For faster experiments, reduce iterations with `-n 1000`.

## Input Format

OpenSplat expects a directory with COLMAP output:

```
dataset/
├── images/          # Source photos
└── sparse/
    └── 0/
        ├── cameras.bin
        ├── images.bin
        └── points3D.bin
```

See [capture/README.md](../capture/README.md) for how to create this from your own photos.
