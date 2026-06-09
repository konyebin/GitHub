---
name: vidcastmcp
description: |
  Connect Claude Code to the Webex Vidcast MCP server via OAuth, giving Claude
  access to 29 tools for searching, browsing, and retrieving Vidcast videos,
  playlists, recordings, and transcripts.
allowed-tools: Bash, Read, Edit
argument-hint: [connect|refresh-token]
---

# Vidcast MCP Skill

Registers the Webex Vidcast MCP server with Claude Code via OAuth token.

**Project path:** `~/Documents/GitHub/vidcastmcp/`

---

## Quick-start

```bash
cd ~/Documents/GitHub/vidcastmcp

# Connect (validates token + registers MCP server with Claude Code)
.venv/bin/python src/tools/mcp_connect.py

# Re-run OAuth flow (token expired or first-time setup)
.venv/bin/python src/tools/webex_oauth.py
```

---

## MCP server

| Item | Detail |
|---|---|
| URL | `https://mcp.webexapis.com/mcp/vidcast` |
| Transport | HTTP |
| Auth | `Authorization: Bearer <access_token>` |
| Tools | 29 tools for videos, playlists, recordings, transcripts |

---

## Key files

| File | Purpose |
|---|---|
| `src/tools/mcp_connect.py` | Validates token + registers MCP server with Claude Code |
| `src/tools/webex_oauth.py` | Browser-based OAuth flow, saves tokens to `.env` |
| `src/config.py` | Loads all env vars |
| `.env` | Credentials and tokens — never commit |

---

## OAuth scopes required

```
spark:mcp
spark:recordings_read
meeting:recordings_read
meeting:transcripts_read
meeting:schedules_read
```

---

## Token lifecycle

| Token | Lifetime |
|---|---|
| Access token | ~14 days |
| Refresh token | 90 days (renews on each use) |

When the access token expires, run `mcp_connect.py` again — it will use the refresh token automatically. If the refresh token is also expired (>90 days unused), re-run `webex_oauth.py` to do a full browser OAuth flow.

---

## Setup (first time)

```bash
cd ~/Documents/GitHub/vidcastmcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # or pip install requests python-dotenv

# Add to .env:
WEBEX_CLIENT_ID=...
WEBEX_CLIENT_SECRET=...

# Run OAuth
.venv/bin/python src/tools/webex_oauth.py

# Register MCP server
.venv/bin/python src/tools/mcp_connect.py
```

---

## Gotchas

- The root `~/Documents/GitHub/.env` access token will not work here — Vidcast needs the scopes above which may not be in the root token's scope set. If you have all scopes in the root token (including `spark:mcp`), you can symlink `.env` to the root `.env` instead of running a separate OAuth flow.
- After running `mcp_connect.py`, reload Claude Code (restart or `/mcp` reload) to pick up the new server registration.
- The 29 Vidcast tools are read-only — searches, listings, and downloads only; no create/delete.
