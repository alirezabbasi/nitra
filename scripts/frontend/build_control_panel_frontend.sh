#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="$ROOT_DIR/services/control-panel/frontend/src"
DIST_DIR="$ROOT_DIR/services/control-panel/frontend/dist"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
cp -R "$SRC_DIR"/. "$DIST_DIR"/

echo "[frontend-build] control-panel frontend synced: src -> dist"
