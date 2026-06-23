#!/usr/bin/env bash
# Run the dashboard over HTTP (required for reliable script loading).
cd "$(dirname "$0")"
"$(dirname "$0")/sync-default-workbook.sh" 2>/dev/null || true

pick_port() {
  local p
  for p in "${PORT:-8765}" 8766 8767 8768 8769 8770 8780; do
    if ! lsof -Pi :"$p" -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "A server is already running on port 8765."
  echo "Open: http://127.0.0.1:8765/index.html"
  echo "After editing output/Check_Back_standardized.xlsx, run: ./sync-default-workbook.sh"
  echo "Then in the dashboard click Reload baseline or Reload spreadsheet."
  exit 0
fi

PORT="$(pick_port)" || { echo "No free port found (8765-8780). Stop other servers and retry."; exit 1; }
echo "Check Back dashboard: http://127.0.0.1:${PORT}/index.html"
exec python3 -m http.server "$PORT"
