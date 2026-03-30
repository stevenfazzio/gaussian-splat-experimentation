#!/usr/bin/env python3
"""Compute scene center from a Gaussian splat PLY and write scene-info.json."""

import sys
import json
import numpy as np


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input.ply>")
        sys.exit(1)

    ply_path = sys.argv[1]

    with open(ply_path, 'rb') as f:
        properties = []
        num_vertices = 0
        while True:
            line = f.readline().decode().strip()
            if line == 'end_header':
                break
            if line.startswith('element vertex'):
                num_vertices = int(line.split()[-1])
            if line.startswith('property float'):
                properties.append(line.split()[-1])

        xi, yi, zi = properties.index('x'), properties.index('y'), properties.index('z')
        data = np.frombuffer(f.read(num_vertices * len(properties) * 4),
                             dtype=np.float32).reshape(num_vertices, len(properties))
        positions = data[:, [xi, yi, zi]]

    # Trimmed median: compute median, then re-median using only the closest 50%
    median = np.median(positions, axis=0)
    dists = np.linalg.norm(positions - median, axis=1)
    mask = dists <= np.percentile(dists, 50)
    center = np.median(positions[mask], axis=0)

    import os
    out_path = os.path.join(os.path.dirname(ply_path), 'scene-info.json')
    info = {"center": center.tolist()}
    with open(out_path, 'w') as f:
        json.dump(info, f)

    print(f"Center: [{center[0]:.4f}, {center[1]:.4f}, {center[2]:.4f}]")
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()
