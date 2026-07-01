#!/usr/bin/env bash
# Build static dashboard assets for GitHub Pages.
# Monorepo (default): docs/public/demos/check-back/ under parent GitHub repo
# Standalone: set CHECK_BACK_PAGES_DEST or auto-uses ./docs/ at project root
set -euo pipefail

DASH="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DASH/.." && pwd)"
MONOREPO_PAGES="$(cd "$DASH/../.." 2>/dev/null && pwd)/docs/public/demos/check-back"

if [ -n "${CHECK_BACK_PAGES_DEST:-}" ]; then
  DEST="$CHECK_BACK_PAGES_DEST"
elif [ -d "$(dirname "$MONOREPO_PAGES")" ]; then
  DEST="$MONOREPO_PAGES"
else
  DEST="$REPO_ROOT/docs"
fi

PYTHON="${PYTHON:-python3}"
if [ -x "$REPO_ROOT/.venv/bin/python3" ]; then
  PYTHON="$REPO_ROOT/.venv/bin/python3"
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
if [ "$DEST" = "$MONOREPO_PAGES" ]; then
  echo "Live URL (after push to main): https://konyebin.github.io/GitHub/demos/check-back/index.html"
else
  echo "Serve locally: python3 -m http.server 8765 --directory $DEST"
fi
