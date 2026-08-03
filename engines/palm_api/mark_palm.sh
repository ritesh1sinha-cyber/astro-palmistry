#!/usr/bin/env bash
# Launch labelme to manually mark palm lines on an image.
# Usage: ./mark_palm.sh [image_path]

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${1:-$ROOT/data/uploads/01cec126c3c2.jpg}"
LABELS="$ROOT/data/palm_line_labels.txt"
OUT="$ROOT/data/markers"

mkdir -p "$OUT"

if [[ ! -f "$IMAGE" ]]; then
  echo "Image not found: $IMAGE" >&2
  exit 1
fi

echo "Opening labelme for: $IMAGE"
echo "Labels: heart_line, head_line, life_line, fate_line"
echo "Saved JSON will go to: $OUT"
echo ""
echo "How to mark curved lines:"
echo "  1. Pick a label from the list (e.g. heart_line)"
echo "  2. Menu: Create Polygons (or press P)"
echo "  3. Click points along the crease, double-click to finish"
echo "  4. Repeat for each line, then File -> Save"
echo ""

# Avoid OpenCV's Qt plugins breaking PyQt5 on Linux.
unset QT_QPA_PLATFORM_PLUGIN_PATH
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"
export QT_PLUGIN_PATH="$(python3 -c "import PyQt5, os; print(os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins'))")"

exec python3 -m labelme \
  --labels "$LABELS" \
  --output "$OUT" \
  "$IMAGE"
