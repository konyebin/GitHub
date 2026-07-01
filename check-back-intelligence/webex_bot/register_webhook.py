#!/usr/bin/env python3
"""Register the Webex webhook for the Check Back bot."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

WEBEX_API = "https://webexapis.com/v1"


def _headers() -> dict:
    token = os.environ.get("WEBEX_BOT_TOKEN", "")
    if not token:
        print("ERROR: WEBEX_BOT_TOKEN not set.")
        sys.exit(1)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def list_webhooks() -> list[dict]:
    r = requests.get(f"{WEBEX_API}/webhooks", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("items", [])


def create_webhook(target_url: str, secret: str | None = None) -> dict:
    payload = {
        "name": "Check Back Intelligence — messages",
        "targetUrl": target_url,
        "resource": "messages",
        "event": "created",
    }
    if secret:
        payload["secret"] = secret
    r = requests.post(f"{WEBEX_API}/webhooks", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def delete_webhook(webhook_id: str) -> None:
    r = requests.delete(f"{WEBEX_API}/webhooks/{webhook_id}", headers=_headers(), timeout=10)
    r.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Webex webhooks for Check Back bot")
    parser.add_argument("--url", help="Public webhook URL (https://…/webhook)")
    parser.add_argument("--secret", help="HMAC secret (defaults to WEBEX_WEBHOOK_SECRET)")
    parser.add_argument("--list", action="store_true", help="List webhooks")
    parser.add_argument("--delete-all", action="store_true", help="Delete all webhooks")
    args = parser.parse_args()

    if args.list or (not args.url and not args.delete_all):
        hooks = list_webhooks()
        if not hooks:
            print("No webhooks registered.")
        else:
            for h in hooks:
                print(f"  [{h['id'][:8]}…] {h['name']}\n    {h['targetUrl']}\n")
        return

    if args.delete_all:
        hooks = list_webhooks()
        for h in hooks:
            delete_webhook(h["id"])
            print(f"Deleted {h['id'][:8]}…")
        return

    if args.url:
        for h in list_webhooks():
            if h.get("targetUrl") == args.url:
                delete_webhook(h["id"])
        secret = args.secret or os.environ.get("WEBEX_WEBHOOK_SECRET")
        hook = create_webhook(args.url, secret)
        print(f"Registered webhook {hook['id']}\n  {hook['targetUrl']}")


if __name__ == "__main__":
    main()
