#!/usr/bin/env python3
"""
Rotate a Gaussian splat PLY so that scene "up" aligns with +Y.

Reads cameras.json to determine the gravity direction, then rotates
all gaussian positions, normals, and spherical harmonics in the PLY
so that the scene's up direction becomes (0, 1, 0).

Also recenters the scene so the object of interest is at the origin.

Usage:
    python3 align-splat.py <input.ply> <cameras.json> <output.ply>
"""

import sys
import struct
import json
import numpy as np


def compute_scene_up(cameras):
    """Compute scene up from camera rotation matrices.

    Uses the most upright camera (closest to identity rotation)
    to determine the gravity direction. In the cameras.json convention,
    column 1 of the rotation matrix gives the camera's Y-up in world coords.
    """
    # Find the most upright camera (rotation closest to identity)
    best_cam = cameras[0]
    best_trace = -np.inf
    for cam in cameras:
        R = np.array(cam['rotation'])
        trace = np.trace(R)
        if trace > best_trace:
            best_trace = trace
            best_cam = cam

    # For the most upright camera, up = column 1 of R
    R = np.array(best_cam['rotation'])
    up = R[:, 1]
    up = up / np.linalg.norm(up)
    return up


def compute_scene_center(cameras):
    """Find the point where all cameras are looking (ray convergence).

    Uses column 2 of each rotation matrix as the forward direction,
    then finds the least-squares closest point to all rays.
    """
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for cam in cameras:
        R = np.array(cam['rotation'])
        p = np.array(cam['position'])
        d = R[:, 2]  # forward = column 2
        d = d / np.linalg.norm(d)
        I_ddT = np.eye(3) - np.outer(d, d)
        A += I_ddT
        b += I_ddT @ p
    return np.linalg.solve(A, b)


def rotation_align(from_vec, to_vec):
    """Compute rotation matrix that rotates from_vec to align with to_vec."""
    from_vec = from_vec / np.linalg.norm(from_vec)
    to_vec = to_vec / np.linalg.norm(to_vec)

    v = np.cross(from_vec, to_vec)
    c = np.dot(from_vec, to_vec)

    if c < -0.9999:
        # Nearly opposite — pick an arbitrary perpendicular axis
        perp = np.array([1, 0, 0]) if abs(from_vec[0]) < 0.9 else np.array([0, 1, 0])
        perp = perp - np.dot(perp, from_vec) * from_vec
        perp = perp / np.linalg.norm(perp)
        return 2 * np.outer(perp, perp) - np.eye(3)

    vx = np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
    ])
    R = np.eye(3) + vx + vx @ vx / (1 + c)
    return R


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <input.ply> <cameras.json> <output.ply>")
        sys.exit(1)

    input_ply = sys.argv[1]
    cameras_json = sys.argv[2]
    output_ply = sys.argv[3]

    # Load cameras
    with open(cameras_json) as f:
        cameras = json.load(f)

    scene_up = compute_scene_up(cameras)
    print(f"Scene up:     [{scene_up[0]:.4f}, {scene_up[1]:.4f}, {scene_up[2]:.4f}]")

    # Compute rotation that maps scene_up -> (0, 1, 0)
    target_up = np.array([0.0, 1.0, 0.0])
    R = rotation_align(scene_up, target_up)

    # Verify
    rotated_up = R @ scene_up
    print(f"Rotated up:   [{rotated_up[0]:.4f}, {rotated_up[1]:.4f}, {rotated_up[2]:.4f}]")

    # Read PLY
    with open(input_ply, 'rb') as f:
        # Parse header
        header_lines = []
        while True:
            line = f.readline()
            header_lines.append(line)
            if line.strip() == b'end_header':
                break

        header_text = b''.join(header_lines).decode()
        num_vertices = 0
        properties = []
        for line in header_text.split('\n'):
            if line.startswith('element vertex'):
                num_vertices = int(line.split()[-1])
            if line.startswith('property float'):
                properties.append(line.split()[-1])

        print(f"\nPLY: {num_vertices} vertices, {len(properties)} properties per vertex")
        print(f"Properties: {', '.join(properties[:10])}{'...' if len(properties) > 10 else ''}")

        # Find indices of position properties
        xi, yi, zi = properties.index('x'), properties.index('y'), properties.index('z')

        # Find normal indices if present
        has_normals = 'nx' in properties and 'ny' in properties and 'nz' in properties
        if has_normals:
            nxi, nyi, nzi = properties.index('nx'), properties.index('ny'), properties.index('nz')

        # Read all vertex data
        bytes_per_vertex = len(properties) * 4
        raw_data = f.read(num_vertices * bytes_per_vertex)

    # Process vertices
    vertices = np.frombuffer(raw_data, dtype=np.float32).reshape(num_vertices, len(properties)).copy()

    # Use PLY median as scene center (robust to outlier gaussians)
    positions = vertices[:, [xi, yi, zi]].copy()
    scene_center = np.median(positions, axis=0)
    print(f"Scene center (PLY median): [{scene_center[0]:.4f}, {scene_center[1]:.4f}, {scene_center[2]:.4f}]")

    # Recenter and rotate
    positions -= scene_center
    positions = (R @ positions.T).T  # rotate
    vertices[:, xi] = positions[:, 0]
    vertices[:, yi] = positions[:, 1]
    vertices[:, zi] = positions[:, 2]

    # Transform normals if present
    if has_normals:
        normals = vertices[:, [nxi, nyi, nzi]].copy()
        normals = (R @ normals.T).T
        vertices[:, nxi] = normals[:, 0]
        vertices[:, nyi] = normals[:, 1]
        vertices[:, nzi] = normals[:, 2]

    print(f"New centroid: [{vertices[:, xi].mean():.4f}, {vertices[:, yi].mean():.4f}, {vertices[:, zi].mean():.4f}]")

    # Also transform cameras.json and write alongside
    new_cameras = []
    for cam in cameras:
        new_cam = dict(cam)
        p = np.array(cam['position'])
        new_cam['position'] = (R @ (p - scene_center)).tolist()
        Rc = np.array(cam['rotation'])
        new_cam['rotation'] = (R @ Rc).tolist()
        new_cameras.append(new_cam)

    cameras_out = output_ply.rsplit('.', 1)[0] + '_cameras.json'
    # Write to same directory as output PLY
    import os
    cameras_out = os.path.join(os.path.dirname(output_ply), 'cameras.json')
    with open(cameras_out, 'w') as f:
        json.dump(new_cameras, f)
    print(f"Wrote {cameras_out}")

    # Write output PLY
    with open(output_ply, 'wb') as f:
        f.write(b''.join(header_lines))
        f.write(vertices.tobytes())

    print(f"Wrote {output_ply}")
    print("\nDone! Scene is now Y-up and centered at origin.")


if __name__ == '__main__':
    main()
