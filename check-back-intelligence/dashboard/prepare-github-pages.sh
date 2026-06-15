#!/usr/bin/env bash
# Build static dashboard assets for GitHub Pages (docs/public/demos/check-back/).
set -euo pipefail

DASH="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DASH/../.." && pwd)"
DEST="$REPO_ROOT/docs/public/demos/check-back"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python3}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="${PYTHON:-python3}"
fi

echo "Building dashboard bundle…"
"$DASH/build-bundle.sh"

mkdir -p "$DEST"
echo "Creating sanitized demo workbook (no customer PII)…"
"$PYTHON" "$DASH/create-demo-workbook.py" "$DEST/check_back_default.xlsx"

cp "$DASH/index.html" "$DEST/index.html"
cp "$DASH/dashboard.bundle.js" "$DEST/dashboard.bundle.js"
mkdir -p "$DEST/vendor"
cp "$DASH/vendor/"*.js "$DEST/vendor/"

echo "Published Check Back dashboard → $DEST"
echo "Live URL (after push to main): https://konyebin.github.io/GitHub/demos/check-back/index.html"
