#!/usr/bin/env bash
# Start Check Back stack: static dashboard, Flask Webex bot, Cloudflare quick tunnels.
#
# Baseline workbook: output/Check_Back_standardized.xlsx (override with CHECK_BACK_XLSX)
# Bot token: WEBEX_BOT_TOKEN in project .env (see .env.example)
#
# Register webhook after start:
#   python3 -m webex_bot.register_webhook --url "$WEBHOOK_URL/webhook"

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DASHBOARD_PORT="${CHECKBACK_DASHBOARD_PORT:-8765}"
WEBHOOK_PORT="${CHECKBACK_WEBHOOK_PORT:-5010}"
STATE="$HOME/.check-back/bot-tunnel.json"
LOG_DIR="$HOME/.check-back/cloudflared"
PIDS="$HOME/.check-back/check-back-bot.pids"

mkdir -p "$LOG_DIR" "$(dirname "$STATE")"

if [[ -f "$PIDS" ]]; then
  echo "Stopping previous check-back-bot processes…"
  while read -r pid; do kill "$pid" 2>/dev/null || true; done < "$PIDS" || true
  rm -f "$PIDS"
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

echo "Syncing baseline workbook for dashboard auto-load…"
"$ROOT/dashboard/sync-default-workbook.sh"

echo "Starting dashboard HTTP server on :$DASHBOARD_PORT …"
python3 -m http.server "$DASHBOARD_PORT" --directory "$ROOT/dashboard" \
  >"$LOG_DIR/dashboard.log" 2>&1 &
echo $! >> "$PIDS"

echo "Starting Check Back Webex bot on :$WEBHOOK_PORT …"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m webex_bot.app --port "$WEBHOOK_PORT" \
  >"$LOG_DIR/webhook.log" 2>&1 &
echo $! >> "$PIDS"

sleep 2

start_quick_tunnel() {
  local name="$1"
  local port="$2"
  local log="$LOG_DIR/${name}.log"
  : > "$log"
  cloudflared tunnel --no-autoupdate --protocol http2 --url "http://127.0.0.1:${port}" >>"$log" 2>&1 &
  echo $! >> "$PIDS"
  local url=""
  for _ in $(seq 1 90); do
    url=$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$log" | tail -1 || true)
    if [[ -n "$url" ]]; then
      echo "$url"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: tunnel for $name did not start — see $log" >&2
  return 1
}

if [[ -n "${CLOUDFLARE_TUNNEL_CONFIG:-}" && -f "${CLOUDFLARE_TUNNEL_CONFIG}" ]]; then
  cloudflared tunnel --config "$CLOUDFLARE_TUNNEL_CONFIG" run >>"$LOG_DIR/named-tunnel.log" 2>&1 &
  echo $! >> "$PIDS"
  DASHBOARD_URL="${CHECKBACK_DASHBOARD_PUBLIC_URL:-}"
  WEBHOOK_URL="${CHECKBACK_WEBHOOK_PUBLIC_URL:-}"
  if [[ -z "$DASHBOARD_URL" || -z "$WEBHOOK_URL" ]]; then
    echo "Set CHECKBACK_DASHBOARD_PUBLIC_URL and CHECKBACK_WEBHOOK_PUBLIC_URL for named tunnel mode." >&2
    exit 1
  fi
else
  echo "Starting Cloudflare quick tunnel → dashboard…"
  DASHBOARD_URL="$(start_quick_tunnel dashboard "$DASHBOARD_PORT")"
  echo "Starting Cloudflare quick tunnel → webhook…"
  WEBHOOK_URL="$(start_quick_tunnel webhook "$WEBHOOK_PORT")"
fi

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

state = {
    "mode": "named" if "${CLOUDFLARE_TUNNEL_CONFIG:-}" else "quick",
    "dashboard_url": "${DASHBOARD_URL}",
    "webhook_url": "${WEBHOOK_URL}",
    "dashboard_port": int("${DASHBOARD_PORT}"),
    "webhook_port": int("${WEBHOOK_PORT}"),
    "baseline": "${ROOT}/output/Check_Back_standardized.xlsx",
    "updated_at": datetime.now(timezone.utc).isoformat(),
}
path = Path("${STATE}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(state, indent=2), encoding="utf-8")
print(f"Wrote {path}")
PY

echo ""
echo "════════════════════════════════════════════════════════════"
echo " Check Back Intelligence bot is running"
echo "════════════════════════════════════════════════════════════"
echo " Dashboard (share):  ${DASHBOARD_URL}/index.html"
echo " Webhook (register): ${WEBHOOK_URL}/webhook"
echo " Baseline xlsx:      ${ROOT}/output/Check_Back_standardized.xlsx"
echo ""
echo " Webex commands: dashboard | summary | refresh | help"
echo ""
echo " Register webhook:"
echo "   cd $ROOT && PYTHONPATH=$ROOT python3 -m webex_bot.register_webhook --url ${WEBHOOK_URL}/webhook"
echo ""
echo " Logs: $LOG_DIR/"
echo " Stop: kill \$(cat $PIDS)"
echo "════════════════════════════════════════════════════════════"

wait
