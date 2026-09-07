#!/usr/bin/env bash
# Build hackathon demo hub + scenario dashboards for GitHub Pages.
set -euo pipefail

DEMO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

if [ -x "$HOME/Documents/GitHub/wxops/.venv/bin/python3" ]; then
  PYTHON="$HOME/Documents/GitHub/wxops/.venv/bin/python3"
fi

echo "Generating synthetic demo reports…"
"$PYTHON" "$DEMO/generate_demo_reports.py"

echo ""
echo "Published hub → $DEMO/index.html"
echo "Live URL: https://konyebin.github.io/GitHub/demos/misc-ops-report/index.html"
