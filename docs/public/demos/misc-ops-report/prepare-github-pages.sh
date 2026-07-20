#!/usr/bin/env bash
# Rebuild index.html from ops-report-source.html for GitHub Pages deploy.
set -euo pipefail

DEMO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

echo "Building misc ops report demo…"
"$PYTHON" "$DEMO/create-demo-ops-report.py" \
  --source "$DEMO/ops-report-source.html" \
  --dest "$DEMO/index.html"

echo "Published → $DEMO/index.html"
echo "Live URL: https://konyebin.github.io/GitHub/demos/misc-ops-report/index.html"
