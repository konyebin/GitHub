"""
webex_oauth.py – Automates the Webex OAuth flow.

Usage:
    python webex_oauth.py

Set these in your .env before running:
    WEBEX_CLIENT_ID=...
    WEBEX_CLIENT_SECRET=...
    WEBEX_SCOPES=...   (optional, defaults shown below)

The script will:
  1. Open the Webex authorization page in your browser
  2. Start a local server on port 8080 to catch the redirect
  3. Exchange the code for tokens
  4. Write WEBEX_ACCESS_TOKEN and WEBEX_REFRESH_TOKEN into .env
"""

import os
import sys
import webbrowser
import threading
import urllib.parse
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────
CLIENT_ID     = os.environ.get("WEBEX_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("WEBEX_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8080/callback"
SCOPES        = os.environ.get(
    "WEBEX_SCOPES",
    "spark:all vidcast:recordings_read vidcast:playlists_read",
)
AUTH_URL      = "https://webexapis.com/v1/authorize"
TOKEN_URL     = "https://webexapis.com/v1/access_token"
ENV_FILE      = Path(__file__).parent / ".env"  # ~/Documents/GitHub/.env

# ── State ───────────────────────────────────────────────────────────────────
_state = secrets.token_urlsafe(16)
_result: dict = {}
_server_done = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "error" in params:
            _result["error"] = params["error"][0]
        elif "code" in params:
            if params.get("state", [""])[0] != _state:
                _result["error"] = "state_mismatch"
            else:
                _result["code"] = params["code"][0]

        body = b"<h2>You can close this tab and return to the terminal.</h2>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        _server_done.set()

    def log_message(self, *_):
        pass  # suppress default request logging


def _run_server():
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    server.timeout = 120
    while not _server_done.is_set():
        server.handle_request()
    server.server_close()


def _exchange_code(code: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_token(refresh_tok: str) -> dict:
    """Exchange a refresh token for a new access token and save to .env."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_tok,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    tokens = resp.json()
    _save_tokens(tokens)
    return tokens


def _save_tokens(tokens: dict):
    set_key(str(ENV_FILE), "WEBEX_ACCESS_TOKEN",  tokens["access_token"])
    set_key(str(ENV_FILE), "WEBEX_REFRESH_TOKEN", tokens["refresh_token"])
    print(f"  access_token  saved to {ENV_FILE.name}  (expires in {tokens.get('expires_in', '?')}s)")
    print(f"  refresh_token saved to {ENV_FILE.name}  (expires in {tokens.get('refresh_token_expires_in', '?')}s)")


def _auth_link() -> str:
    auth_params = urllib.parse.urlencode({
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPES,
        "state":         _state,
        "prompt":        "login",
    })
    return f"{AUTH_URL}?{auth_params}"


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit(
            "ERROR: Set WEBEX_CLIENT_ID and WEBEX_CLIENT_SECRET in your .env first."
        )

    no_browser = "--no-browser" in sys.argv or "--incognito" in sys.argv
    auth_link = _auth_link()

    print("Starting local callback server on http://localhost:8080 ...")
    t = threading.Thread(target=_run_server, daemon=True)
    t.start()

    print("Open this URL (use incognito for a different user):")
    print(f"  {auth_link}\n")
    if not no_browser:
        print("Opening browser for authorization...")
        webbrowser.open(auth_link)

    _server_done.wait(timeout=120)

    if "error" in _result:
        sys.exit(f"Authorization failed: {_result['error']}")
    if "code" not in _result:
        sys.exit("Timed out waiting for authorization.")

    print("Code received. Exchanging for tokens...")
    tokens = _exchange_code(_result["code"])
    _save_tokens(tokens)
    print("\nDone! You can now use WEBEX_ACCESS_TOKEN from your .env.")


if __name__ == "__main__":
    main()
