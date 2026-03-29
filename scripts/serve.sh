#!/bin/bash
# Start a local HTTP server for the viewer.
# ES module imports require a server (file:// won't work).

PORT="${1:-8080}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Serving at http://localhost:$PORT"
echo "Open http://localhost:$PORT/viewer/ to view splats"
echo ""
python3 -m http.server "$PORT" --directory "$DIR"
