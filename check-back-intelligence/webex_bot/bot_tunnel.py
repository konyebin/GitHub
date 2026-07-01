"""Cloudflare Tunnel state for the Check Back Webex bot."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

TUNNEL_STATE_PATH = Path.home() / ".check-back" / "bot-tunnel.json"
TRYCF_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)


def load_tunnel_state() -> dict:
    if not TUNNEL_STATE_PATH.exists():
        return {}
    try:
        return json.loads(TUNNEL_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_tunnel_state(state: dict) -> None:
    TUNNEL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    TUNNEL_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def dashboard_base_url() -> str | None:
    url = (load_tunnel_state().get("dashboard_url") or "").rstrip("/")
    return url or None


def webhook_base_url() -> str | None:
    url = (load_tunnel_state().get("webhook_url") or "").rstrip("/")
    return url or None


def build_dashboard_link(*, account: str | None = None) -> str:
    base = dashboard_base_url()
    if not base:
        raise RuntimeError(
            f"No dashboard tunnel URL in {TUNNEL_STATE_PATH}. "
            "Run webex_bot/run-check-back-bot.sh first."
        )
    if account:
        from urllib.parse import quote

        return f"{base}/index.html?account={quote(account)}"
    return f"{base}/index.html"
