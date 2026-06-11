# Workspace root setup

Shared OAuth, Python environments, and MCP registration for everything under `~/Documents/GitHub`.

## What it is

The repo root is the **workspace hub**: one git repository wrapping multiple projects, a shared **`.env`** for Webex tokens, **`webex_oauth.py`** for OAuth refresh, and **`.cursor/mcp.json`** for Cursor MCP servers (`wxops`, `roomos`).

## When to use it

- Run or refresh the **Webex OAuth** flow for any project that needs `WEBEX_ACCESS_TOKEN`
- Configure **Cursor** with workspace-root MCP (`envFile` → root `.env`)
- Sync tokens into **wxcli** after OAuth

## Stack and entry points

| Asset | Path |
|-------|------|
| Agent instructions | `~/Documents/GitHub/CLAUDE.md` |
| OAuth script | `~/Documents/GitHub/webex_oauth.py` |
| Secrets (never commit) | `~/Documents/GitHub/.env` |
| Root Python venv | `~/Documents/GitHub/.venv` (Python **3.14**) |
| Cursor MCP config | `~/Documents/GitHub/.cursor/mcp.json` |
| Deleted devices log | `~/Documents/GitHub/devices_deleted.csv` (append-only) |

## Prerequisites

| Need | Detail |
|------|--------|
| Python | **3.14** at repo root |
| Packages | `requests`, `python-dotenv` in root `.venv` |
| Webex app | [developer.webex.com](https://developer.webex.com) integration with redirect **`http://localhost:8080/callback`** |
| `.env` keys | `WEBEX_CLIENT_ID`, `WEBEX_CLIENT_SECRET`, `WEBEX_SCOPES`, `WEBEX_ACCESS_TOKEN`, `WEBEX_REFRESH_TOKEN` |

`WEBEX_SCOPES` must **exactly** match scopes enabled in the Developer Portal. When adding scopes, append only; re-run OAuth after changes.

## How to run

### Root venv and OAuth

```bash
cd ~/Documents/GitHub
python3 -m venv .venv
.venv/bin/pip install requests python-dotenv
.venv/bin/python webex_oauth.py
```

### wxcli token sync (after OAuth)

```bash
# Or: wxcli configure and paste token
```

See `CLAUDE.md` §4 for the one-shot Python snippet that copies the token into `~/.wxcli/config.json`.

### wxops MCP (Claude Code, optional)

```bash
claude mcp add --scope user wxops \
  ~/Documents/GitHub/wxops/.venv/bin/python \
  ~/Documents/GitHub/wxops/mcp_server.py
```

### Cursor MCP

Open the workspace at **`~/Documents/GitHub`**. `.cursor/mcp.json` registers:

- **wxops** — `wxops/.venv/bin/python` + `mcp_server.py`
- **roomos** — `node test/device-mcp-server/dist/index.js`

Both use `envFile`: `${workspaceFolder}/.env`.

## Runtime split (important)

| Target | Runtime |
|--------|---------|
| Root scripts | Python **3.14** |
| wxops | Python **3.13** only (not 3.14) |
| test/device-mcp-server | Node.js **18+** |

Details: [wxops](/projects/wxops), [device-mcp-server](/projects/device-mcp-server).

## Canonical docs

- `~/Documents/GitHub/CLAUDE.md` — full fresh-install and routing table
