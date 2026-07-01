#!/usr/bin/env python3
"""Entry point for the Check Back Intelligence Webex bot."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Back Intelligence Webex bot")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CHECKBACK_WEBHOOK_PORT", "5010")))
    args = parser.parse_args()

    if not os.environ.get("WEBEX_BOT_TOKEN"):
        print("ERROR: WEBEX_BOT_TOKEN not set (copy .env.example → .env or export it).")
        sys.exit(1)

    from .webex_bot import app, get_bot_person_id

    try:
        print(f"Bot person ID: {get_bot_person_id()}")
    except Exception as exc:
        print(f"WARNING: Could not fetch bot person ID: {exc}")

    print(f"\nCheck Back Webex bot on port {args.port}")
    print(f"Webhook: http://0.0.0.0:{args.port}/webhook")
    print(f"Health:  http://0.0.0.0:{args.port}/health\n")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
