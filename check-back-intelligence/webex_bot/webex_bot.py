"""
Flask webhook server for the Check Back Intelligence Webex bot.

Commands in Webex:
  help | dashboard | summary | portfolio | refresh | sync baseline
"""

from __future__ import annotations

import hashlib
import hmac
import os

import requests
from flask import Flask, abort, jsonify, request

from . import bot_service

app = Flask(__name__)
WEBEX_API = "https://webexapis.com/v1"
_BOT_PERSON_ID: str | None = None


def _bot_token() -> str:
    token = os.environ.get("WEBEX_BOT_TOKEN", "")
    if not token:
        raise EnvironmentError("WEBEX_BOT_TOKEN environment variable not set.")
    return token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_bot_token()}"}


def get_bot_person_id() -> str:
    global _BOT_PERSON_ID
    if _BOT_PERSON_ID is None:
        r = requests.get(f"{WEBEX_API}/people/me", headers=_headers(), timeout=10)
        r.raise_for_status()
        _BOT_PERSON_ID = r.json()["id"]
    return _BOT_PERSON_ID


def get_message(message_id: str) -> dict:
    r = requests.get(f"{WEBEX_API}/messages/{message_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def send_message(room_id: str, text: str, markdown: str | None = None) -> None:
    payload: dict = {"roomId": room_id}
    if markdown:
        payload["markdown"] = markdown
    else:
        payload["text"] = text
    requests.post(f"{WEBEX_API}/messages", headers=_headers(), json=payload, timeout=15)


def _verify_signature(raw_body: bytes) -> bool:
    secret = os.environ.get("WEBEX_WEBHOOK_SECRET", "")
    if not secret:
        return True
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest()
    received = request.headers.get("X-Spark-Signature", "")
    return hmac.compare_digest(expected, received)


def _parse_command(text: str) -> str | None:
    t = text.lower().strip()
    if t in ("help", "/help", "?", "commands"):
        return "help"
    if t in ("dashboard", "check back", "checkback", "/dashboard", "open dashboard"):
        return "dashboard"
    if t in ("summary", "portfolio", "kpi", "kpis", "/summary"):
        return "summary"
    if t in ("refresh", "sync", "sync baseline", "reload baseline", "update"):
        return "refresh"
    if "check back dashboard" in t or "check back" in t and "summary" not in t:
        return "dashboard"
    if "portfolio" in t or "summary" in t:
        return "summary"
    return None


def _dispatch(room_id: str, command: str) -> None:
    try:
        if command == "help":
            send_message(room_id, markdown=bot_service.help_markdown())
            return
        if command == "dashboard":
            reply = bot_service.dashboard_link_reply()
            send_message(room_id, markdown=reply.markdown)
            return
        if command == "summary":
            reply = bot_service.summary_reply()
            send_message(room_id, markdown=reply.markdown)
            return
        if command == "refresh":
            send_message(room_id, markdown="Syncing baseline workbook into the dashboard…")
            reply = bot_service.refresh_reply()
            send_message(room_id, markdown=reply.markdown)
    except Exception as exc:
        send_message(room_id, f"Check Back bot error: {exc}")
        print(f"[check-back-bot] {command} failed: {exc}")


@app.route("/webhook", methods=["GET"])
def webhook_validation():
    token = request.args.get("validationToken")
    if token:
        return token, 200
    return jsonify({"status": "ok", "endpoint": "webhook"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_body = request.get_data()
    if not _verify_signature(raw_body):
        abort(403, "Invalid signature")

    event = request.get_json(force=True)
    if event.get("resource") != "messages" or event.get("event") != "created":
        return jsonify({"status": "ignored"}), 200

    message_id = event.get("data", {}).get("id")
    if not message_id:
        return jsonify({"status": "no message id"}), 200

    try:
        msg = get_message(message_id)
    except Exception as exc:
        print(f"[check-back-bot] fetch message failed: {exc}")
        return jsonify({"status": "error fetching message"}), 200

    if msg.get("personId") == get_bot_person_id():
        return jsonify({"status": "self-message ignored"}), 200

    raw_text = (msg.get("text") or "").strip()
    if raw_text.lower().startswith("@"):
        raw_text = raw_text.split(" ", 1)[-1].strip()

    cmd = _parse_command(raw_text)
    if not cmd:
        send_message(
            msg["roomId"],
            markdown=(
                "Send **help** for Check Back commands, or **dashboard** for the portfolio link."
            ),
        )
        return jsonify({"status": "unknown-command"}), 200

    _dispatch(msg["roomId"], cmd)
    return jsonify({"status": cmd}), 200


@app.route("/health", methods=["GET"])
def health():
    from .bot_tunnel import dashboard_base_url, webhook_base_url

    return jsonify(
        {
            "status": "ok",
            "bot": "check-back-intelligence",
            "dashboard_tunnel": dashboard_base_url(),
            "webhook_tunnel": webhook_base_url(),
            "baseline": str(bot_service.BASELINE_XLSX),
        }
    ), 200
