#!/usr/bin/env python3
"""
Trim outlier gaussians from a Gaussian splat PLY file.

Applies three filters:
  1. Distance — remove gaussians far from the scene center
  2. Opacity  — remove near-transparent gaussians
  3. Scale    — remove abnormally large gaussians

Usage:
    python3 trim-splat.py <input.ply> [output.ply]

If output is omitted, overwrites the input file.
"""

import sys
import numpy as np


def read_ply(path):
    with open(path, 'rb') as f:
        header_lines = []
        properties = []
        num_vertices = 0
        while True:
            line = f.readline()
            header_lines.append(line)
            text = line.decode().strip()
            if text == 'end_header':
                break
            if text.startswith('element vertex'):
                num_vertices = int(text.split()[-1])
            if text.startswith('property float'):
                properties.append(text.split()[-1])

        data = np.frombuffer(
            f.read(num_vertices * len(properties) * 4),
            dtype=np.float32
        ).reshape(num_vertices, len(properties)).copy()

    return header_lines, properties, num_vertices, data


def write_ply(path, header_lines, orig_count, data):
    header = b''.join(header_lines).decode()
    header = header.replace(
        f'element vertex {orig_count}',
        f'element vertex {len(data)}'
    )
    with open(path, 'wb') as f:
        f.write(header.encode())
        f.write(data.tobytes())


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.ply> [output.ply]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path

    header_lines, properties, num_vertices, data = read_ply(input_path)

    xi = properties.index('x')
    yi = properties.index('y')
    zi = properties.index('z')
    positions = data[:, [xi, yi, zi]]

    keep = np.ones(num_vertices, dtype=bool)

    # --- 1. Distance filter ---
    # Trimmed median center, then keep gaussians within a generous radius
    median = np.median(positions, axis=0)
    dists = np.linalg.norm(positions - median, axis=1)
    inner_mask = dists <= np.percentile(dists, 50)
    center = np.median(positions[inner_mask], axis=0)
    dists_from_center = np.linalg.norm(positions - center, axis=1)

    # Keep up to 3x the 90th percentile distance (generous but catches far outliers)
    radius = np.percentile(dists_from_center, 90) * 3
    dist_mask = dists_from_center <= radius
    removed_dist = np.sum(~dist_mask & keep)
    keep &= dist_mask
    print(f"Distance filter: removed {removed_dist} gaussians (radius={radius:.3f})")

    # --- 2. Opacity filter ---
    if 'opacity' in properties:
        oi = properties.index('opacity')
        # OpenSplat stores opacity as logit (pre-sigmoid), so apply sigmoid
        raw_opacity = data[:, oi]
        opacity = 1.0 / (1.0 + np.exp(-raw_opacity))
        opacity_mask = opacity >= 0.05
        removed_opacity = np.sum(~opacity_mask & keep)
        keep &= opacity_mask
        print(f"Opacity filter:  removed {removed_opacity} gaussians (threshold=0.05)")
    else:
        print("Opacity filter:  skipped (no opacity property)")

    # --- 3. Scale filter ---
    scale_names = ['scale_0', 'scale_1', 'scale_2']
    if all(s in properties for s in scale_names):
        si = [properties.index(s) for s in scale_names]
        # OpenSplat stores scale as log(scale), so exponentiate
        scales = np.exp(data[:, si])
        max_scale = scales.max(axis=1)
        scale_threshold = np.percentile(max_scale[keep], 99) * 3
        scale_mask = max_scale <= scale_threshold
        removed_scale = np.sum(~scale_mask & keep)
        keep &= scale_mask
        print(f"Scale filter:    removed {removed_scale} gaussians (threshold={scale_threshold:.4f})")
    else:
        print("Scale filter:    skipped (no scale properties)")

    total_removed = num_vertices - np.sum(keep)
    print(f"\nTotal: {num_vertices} -> {np.sum(keep)} gaussians ({total_removed} removed, {100*total_removed/num_vertices:.1f}%)")

    write_ply(output_path, header_lines, num_vertices, data[keep])
    print(f"Wrote {output_path}")


if __name__ == '__main__':
    main()
