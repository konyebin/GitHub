#!/usr/bin/env bash
# Build ops report demo hub + scenario dashboards for GitHub Pages.
set -euo pipefail

DEMO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

if [ -x "$DEMO/.venv/bin/python3" ]; then
  PYTHON="$DEMO/.venv/bin/python3"
fi

echo "Generating ops report demos…"
"$PYTHON" "$DEMO/generate_demo_reports.py"

echo ""
echo "Published hub → $DEMO/index.html"
echo "Live URL: https://konyebin.github.io/misc-ops-report/index.html"
