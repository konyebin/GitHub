#!/usr/bin/env bash
# Start local server (or reuse one on 8765) and open the dashboard in your browser.
cd "$(dirname "$0")"
"./sync-default-workbook.sh" 2>/dev/null || echo "Note: baseline not synced — run ./sync-default-workbook.sh or upload a workbook"

URL="http://127.0.0.1:8765/index.html"
PID="$(lsof -Pi :8765 -sTCP:LISTEN -t 2>/dev/null | head -1)"

if [ -n "$PID" ]; then
  echo "Using existing server on port 8765 (pid $PID)"
else
  PORT=8765
  for p in 8765 8766 8767 8768 8769; do
    if ! lsof -Pi :"$p" -sTCP:LISTEN -t >/dev/null 2>&1; then
      PORT=$p
      break
    fi
  done
  echo "Starting server on port $PORT..."
  python3 -m http.server "$PORT" >/dev/null 2>&1 &
  sleep 0.5
  URL="http://127.0.0.1:${PORT}/index.html"
fi

echo "Opening $URL"
if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
else
  echo "Open this URL in your browser: $URL"
fi
