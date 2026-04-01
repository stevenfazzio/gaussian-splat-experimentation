#!/usr/bin/env python3
"""
UMAP dimensionality reduction on Gaussian Splat parameters.

Embeds non-positional Gaussian parameters (shape, appearance, or both)
into 2D using UMAP and produces an interactive Plotly HTML visualization.
Color by spatial position to reveal structure invisible in either space alone.

Usage:
    python3 umap-splat.py <input.ply>
    python3 umap-splat.py <input.ply> --features shape --color-by opacity
    python3 umap-splat.py <input.ply> --sample-size 50000 --output my_plot.html
    python3 umap-splat.py <input.ply> --linked          # side-by-side UMAP + 3D with linked selection

Dependencies:
    pip install umap-learn plotly
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    import umap
except ImportError:
    print("Error: umap-learn is required. Install with: pip install umap-learn")
    sys.exit(1)

try:
    import plotly.graph_objects as go
except ImportError:
    print("Error: plotly is required. Install with: pip install plotly")
    sys.exit(1)


# --- PLY field definitions ---

SHAPE_FIELDS = ['scale_0', 'scale_1', 'scale_2', 'rot_0', 'rot_1', 'rot_2', 'rot_3']
APPEARANCE_FIELDS = (
    ['f_dc_0', 'f_dc_1', 'f_dc_2']
    + [f'f_rest_{i}' for i in range(44)]
    + ['opacity']
)
POSITION_FIELDS = ['x', 'y', 'z']
ALL_REQUIRED = POSITION_FIELDS + SHAPE_FIELDS + APPEARANCE_FIELDS


def read_ply(path):
    """Parse a binary PLY file and return property names, index map, and data array."""
    with open(path, 'rb') as f:
        properties = []
        num_vertices = 0

        # Validate PLY magic
        magic = f.readline().decode().strip()
        if magic != 'ply':
            print(f"Error: {path} is not a PLY file")
            sys.exit(1)

        fmt = f.readline().decode().strip()
        if 'binary_little_endian' not in fmt:
            print(f"Error: expected binary_little_endian format, got: {fmt}")
            sys.exit(1)

        while True:
            line = f.readline().decode().strip()
            if line == 'end_header':
                break
            if line.startswith('element vertex'):
                num_vertices = int(line.split()[-1])
            if line.startswith('property float'):
                properties.append(line.split()[-1])

        data = np.frombuffer(
            f.read(num_vertices * len(properties) * 4),
            dtype=np.float32
        ).reshape(num_vertices, len(properties)).copy()

    prop_idx = {name: i for i, name in enumerate(properties)}
    return prop_idx, num_vertices, data


def cols(data, prop_idx, names):
    """Extract columns by property name."""
    return data[:, [prop_idx[n] for n in names]]


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def standardize_group(arr):
    """Z-score normalize treating the entire group as one distribution."""
    mean = arr.mean()
    std = arr.std()
    if std < 1e-10:
        return arr - mean
    return (arr - mean) / std


def extract_features(data, prop_idx, feature_group):
    """Extract and transform feature columns, return list of (name, array) groups."""
    groups = []

    if feature_group in ('shape', 'combined'):
        scales = np.exp(cols(data, prop_idx, ['scale_0', 'scale_1', 'scale_2']))
        rotations = cols(data, prop_idx, ['rot_0', 'rot_1', 'rot_2', 'rot_3'])
        groups.append(('shape', np.hstack([scales, rotations])))

    if feature_group in ('appearance', 'combined'):
        sh_dc = cols(data, prop_idx, ['f_dc_0', 'f_dc_1', 'f_dc_2'])
        sh_rest = cols(data, prop_idx, [f'f_rest_{i}' for i in range(44)])
        opacity = sigmoid(cols(data, prop_idx, ['opacity']))
        groups.append(('appearance', np.hstack([sh_dc, sh_rest, opacity])))

    return groups


def compute_colors(data, prop_idx, color_by):
    """Compute per-point colors. Returns (colors, colorscale, showscale, colorbar_title)."""
    if color_by == 'position':
        positions = cols(data, prop_idx, POSITION_FIELDS)
        mins = positions.min(axis=0)
        maxs = positions.max(axis=0)
        ranges = maxs - mins
        ranges[ranges < 1e-10] = 1.0
        normalized = (positions - mins) / ranges
        r = (normalized[:, 0] * 255).astype(np.uint8)
        g = (normalized[:, 1] * 255).astype(np.uint8)
        b = (normalized[:, 2] * 255).astype(np.uint8)
        colors = [f'rgb({r[i]},{g[i]},{b[i]})' for i in range(len(r))]
        return colors, None, False, None

    elif color_by == 'opacity':
        raw = cols(data, prop_idx, ['opacity']).ravel()
        values = sigmoid(raw)
        return values, 'Viridis', True, 'Opacity'

    elif color_by == 'scale':
        scales = np.exp(cols(data, prop_idx, ['scale_0', 'scale_1', 'scale_2']))
        values = scales.max(axis=1)
        return values, 'Viridis', True, 'Max Scale'


def build_hover_text(data, prop_idx):
    """Build compact hover strings for each point."""
    positions = cols(data, prop_idx, POSITION_FIELDS)
    opacity = sigmoid(cols(data, prop_idx, ['opacity']).ravel())
    scales = np.exp(cols(data, prop_idx, ['scale_0', 'scale_1', 'scale_2']))

    texts = []
    for i in range(len(data)):
        p = positions[i]
        s = scales[i]
        texts.append(
            f"pos: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})<br>"
            f"opacity: {opacity[i]:.3f}<br>"
            f"scale: ({s[0]:.4f}, {s[1]:.4f}, {s[2]:.4f})"
        )
    return texts


# Viridis colormap — 256 RGB tuples sampled from matplotlib's Viridis
VIRIDIS_LUT = None

def _viridis_lut():
    """Lazily build a 256-entry Viridis lookup table."""
    global VIRIDIS_LUT
    if VIRIDIS_LUT is not None:
        return VIRIDIS_LUT
    try:
        from matplotlib.cm import viridis
        VIRIDIS_LUT = np.array([viridis(i / 255.0)[:3] for i in range(256)])
    except ImportError:
        # Fallback: simple yellow-blue gradient
        t = np.linspace(0, 1, 256)
        VIRIDIS_LUT = np.column_stack([
            0.267 + 0.733 * t,       # R
            0.004 + 0.996 * t * 0.8,  # G
            0.329 * (1 - t) + 0.1,    # B
        ]).clip(0, 1)
    return VIRIDIS_LUT


def values_to_rgb_strings(values):
    """Map a numeric array to Viridis RGB strings."""
    lut = _viridis_lut()
    vmin, vmax = values.min(), values.max()
    if vmax - vmin < 1e-10:
        normalized = np.zeros_like(values)
    else:
        normalized = (values - vmin) / (vmax - vmin)
    indices = (normalized * 255).astype(int).clip(0, 255)
    rgb = (lut[indices] * 255).astype(np.uint8)
    return [f'rgb({rgb[i,0]},{rgb[i,1]},{rgb[i,2]})' for i in range(len(rgb))]


def compute_colors_rgb(data, prop_idx, color_by):
    """Compute per-point colors as RGB strings (for linked mode)."""
    if color_by == 'position':
        positions = cols(data, prop_idx, POSITION_FIELDS)
        mins = positions.min(axis=0)
        maxs = positions.max(axis=0)
        ranges = maxs - mins
        ranges[ranges < 1e-10] = 1.0
        normalized = (positions - mins) / ranges
        r = (normalized[:, 0] * 255).astype(np.uint8)
        g = (normalized[:, 1] * 255).astype(np.uint8)
        b = (normalized[:, 2] * 255).astype(np.uint8)
        return [f'rgb({r[i]},{g[i]},{b[i]})' for i in range(len(r))]
    elif color_by == 'opacity':
        raw = cols(data, prop_idx, ['opacity']).ravel()
        return values_to_rgb_strings(sigmoid(raw))
    elif color_by == 'scale':
        scales = np.exp(cols(data, prop_idx, ['scale_0', 'scale_1', 'scale_2']))
        return values_to_rgb_strings(scales.max(axis=1))


def build_linked_html(embedding, positions, colors, hover_text, title):
    """Build a self-contained HTML with linked UMAP 2D and 3D spatial plots."""
    umap_trace = {
        'x': embedding[:, 0].tolist(),
        'y': embedding[:, 1].tolist(),
        'mode': 'markers',
        'type': 'scattergl',
        'marker': {'size': 2, 'opacity': 0.6, 'color': colors},
        'hovertext': hover_text,
        'hoverinfo': 'text',
    }
    spatial_trace = {
        'x': positions[:, 0].tolist(),
        'y': positions[:, 1].tolist(),
        'z': positions[:, 2].tolist(),
        'mode': 'markers',
        'type': 'scatter3d',
        'marker': {'size': 1.5, 'opacity': 0.6, 'color': colors},
        'hovertext': hover_text,
        'hoverinfo': 'text',
    }
    umap_layout = {
        'title': title,
        'xaxis': {'title': 'UMAP 1'},
        'yaxis': {'title': 'UMAP 2'},
        'template': 'plotly_dark',
        'margin': {'t': 40, 'b': 40, 'l': 40, 'r': 10},
        'dragmode': 'lasso',
    }
    spatial_layout = {
        'title': '3D Spatial Positions',
        'scene': {
            'xaxis': {'title': 'X'},
            'yaxis': {'title': 'Y'},
            'zaxis': {'title': 'Z'},
        },
        'template': 'plotly_dark',
        'margin': {'t': 40, 'b': 10, 'l': 10, 'r': 10},
    }

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #111; color: #eee; font-family: sans-serif; overflow: hidden; }}
  #container {{ display: flex; width: 100vw; height: 100vh; }}
  #umap-plot, #spatial-plot {{ flex: 1; min-width: 0; }}
  #status {{ position: fixed; bottom: 8px; left: 50%; transform: translateX(-50%);
             background: rgba(0,0,0,0.7); padding: 4px 12px; border-radius: 4px;
             font-size: 13px; color: #aaa; z-index: 100; }}
</style>
</head>
<body>
<div id="container">
  <div id="umap-plot"></div>
  <div id="spatial-plot"></div>
</div>
<div id="status">Lasso/box select in either plot to highlight. Double-click to reset.</div>
<script>
const umapTrace = {json.dumps(umap_trace)};
const spatialTrace = {json.dumps(spatial_trace)};
const umapLayout = {json.dumps(umap_layout)};
const spatialLayout = {json.dumps(spatial_layout)};

const umapDiv = document.getElementById('umap-plot');
const spatialDiv = document.getElementById('spatial-plot');

Plotly.newPlot(umapDiv, [umapTrace], umapLayout, {{responsive: true, scrollZoom: true}});
Plotly.newPlot(spatialDiv, [spatialTrace], spatialLayout, {{responsive: true, scrollZoom: true}});

const originalColors = umapTrace.marker.color.slice();
const DIM_COLOR = 'rgba(60,60,60,0.12)';

function highlightPoints(selectedSet, sourceDiv, targetDiv) {{
  const n = originalColors.length;
  const srcColors = new Array(n);
  const tgtColors = new Array(n);
  for (let i = 0; i < n; i++) {{
    if (selectedSet.has(i)) {{
      srcColors[i] = originalColors[i];
      tgtColors[i] = originalColors[i];
    }} else {{
      srcColors[i] = DIM_COLOR;
      tgtColors[i] = DIM_COLOR;
    }}
  }}
  Plotly.restyle(sourceDiv, {{'marker.color': [srcColors], 'marker.opacity': [1]}}, [0]);
  Plotly.restyle(targetDiv, {{'marker.color': [tgtColors], 'marker.opacity': [1]}}, [0]);
  document.getElementById('status').textContent = selectedSet.size + ' points selected. Double-click to reset.';
}}

function resetAll() {{
  Plotly.restyle(umapDiv, {{'marker.color': [originalColors], 'marker.opacity': [0.6]}}, [0]);
  Plotly.restyle(spatialDiv, {{'marker.color': [originalColors], 'marker.opacity': [0.6]}}, [0]);
  document.getElementById('status').textContent = 'Lasso/box select in either plot to highlight. Double-click to reset.';
}}

umapDiv.on('plotly_selected', function(data) {{
  if (!data || !data.points.length) return;
  const sel = new Set(data.points.map(p => p.pointNumber));
  highlightPoints(sel, umapDiv, spatialDiv);
}});

spatialDiv.on('plotly_selected', function(data) {{
  if (!data || !data.points.length) return;
  const sel = new Set(data.points.map(p => p.pointNumber));
  highlightPoints(sel, spatialDiv, umapDiv);
}});

umapDiv.on('plotly_deselect', resetAll);
spatialDiv.on('plotly_deselect', resetAll);
</script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(
        description='UMAP embedding of Gaussian Splat parameters'
    )
    parser.add_argument('input', help='Input PLY file')
    parser.add_argument('--features', choices=['shape', 'appearance', 'combined'],
                        default='combined', help='Feature group to embed (default: combined)')
    parser.add_argument('--sample-size', type=int, default=150000,
                        help='Max points to subsample (default: 150000)')
    parser.add_argument('--output', help='Output HTML path (default: <input>_umap.html)')
    parser.add_argument('--color-by', choices=['position', 'opacity', 'scale'],
                        default='position', help='Color mapping (default: position)')
    parser.add_argument('--n-neighbors', type=int, default=15,
                        help='UMAP n_neighbors (default: 15)')
    parser.add_argument('--min-dist', type=float, default=0.1,
                        help='UMAP min_dist (default: 0.1)')
    parser.add_argument('--linked', action='store_true',
                        help='Side-by-side UMAP + 3D view with linked selection')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    # Lower default sample size for linked mode (Scatter3d is heavier)
    if args.linked and args.sample_size == 150000:
        args.sample_size = 75000

    suffix = '_umap_linked.html' if args.linked else '_umap.html'
    output_path = args.output or str(input_path.with_suffix('')) + suffix

    # 1. Read PLY
    print(f"Reading {input_path}...")
    t0 = time.time()
    prop_idx, num_vertices, data = read_ply(input_path)
    print(f"  {num_vertices} vertices, {len(prop_idx)} properties ({time.time()-t0:.1f}s)")

    # Validate required properties
    missing = [f for f in ALL_REQUIRED if f not in prop_idx]
    if missing:
        print(f"Error: missing required properties: {', '.join(missing)}")
        sys.exit(1)

    # 2. Subsample
    if num_vertices > args.sample_size:
        print(f"Subsampling {num_vertices} -> {args.sample_size}...")
        rng = np.random.default_rng(42)
        indices = rng.choice(num_vertices, size=args.sample_size, replace=False)
        data = data[indices]
    else:
        print(f"Using all {num_vertices} points (below sample size {args.sample_size})")

    n = len(data)

    # 3. Extract and preprocess features
    print(f"Extracting {args.features} features...")
    groups = extract_features(data, prop_idx, args.features)
    standardized = [standardize_group(arr) for _, arr in groups]
    features = np.hstack(standardized)
    print(f"  Feature matrix: {features.shape[0]} x {features.shape[1]}")

    # 4. UMAP
    print(f"Running UMAP (n_neighbors={args.n_neighbors}, min_dist={args.min_dist})...")
    t0 = time.time()
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        metric='euclidean',
        random_state=42,
        low_memory=True,
        n_jobs=1,
    )
    embedding = reducer.fit_transform(features)
    print(f"  Done ({time.time()-t0:.1f}s)")

    # 5. Colors and hover text
    print(f"Computing colors (color_by={args.color_by})...")
    hover_text = build_hover_text(data, prop_idx)
    title = f"UMAP — {args.features} features, {n:,} Gaussians, colored by {args.color_by}"

    # 6. Output
    if args.linked:
        colors_rgb = compute_colors_rgb(data, prop_idx, args.color_by)
        positions = cols(data, prop_idx, POSITION_FIELDS)
        print("Creating linked visualization...")
        html = build_linked_html(embedding, positions, colors_rgb, hover_text, title)
        with open(output_path, 'w') as f:
            f.write(html)
    else:
        colors, colorscale, showscale, colorbar_title = compute_colors(
            data, prop_idx, args.color_by
        )
        print("Creating visualization...")
        marker = dict(size=2, opacity=0.5, color=colors)
        if colorscale:
            marker['colorscale'] = colorscale
            marker['showscale'] = showscale
            if colorbar_title:
                marker['colorbar'] = dict(title=colorbar_title)

        fig = go.Figure(data=go.Scattergl(
            x=embedding[:, 0],
            y=embedding[:, 1],
            mode='markers',
            marker=marker,
            hovertext=hover_text,
            hoverinfo='text',
        ))
        fig.update_layout(
            title=title,
            xaxis_title="UMAP 1",
            yaxis_title="UMAP 2",
            width=1200,
            height=800,
            template='plotly_dark',
        )
        fig.write_html(output_path, include_plotlyjs=True)

    print(f"Saved to {output_path}")


if __name__ == '__main__':
    main()
