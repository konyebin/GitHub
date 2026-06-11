# vidcastmcp

<ClientOnly>
  <DemoPanel slug="vidcastmcp" />
</ClientOnly>

## What it is

Connects Claude to the **hosted Webex Vidcast MCP** (`https://mcp.webexapis.com/mcp/vidcast`) via OAuth — search and retrieve Vidcast videos, playlists, recordings, and transcripts (~29 tools).

## When to use it

- Browse, search, or retrieve Vidcast recordings
- Meeting transcripts or recordings (Vidcast surface)
- Webex meeting schedules / content via Vidcast MCP

## Stack and entry points

| Item | Path |
|------|------|
| Project context | `vidcastmcp/.claude/CLAUDE.md` |
| Human README | `vidcastmcp/README.md` |
| MCP connect | `vidcastmcp/src/tools/mcp_connect.py` |
| OAuth | `vidcastmcp/src/tools/webex_oauth.py` |
| Config | `vidcastmcp/src/config.py` |

## Prerequisites

| Need | Detail |
|------|--------|
| Python | 3.9+ (project venv) |
| Packages | `requests`, `python-dotenv` |
| Secrets | `vidcastmcp/.env` (never commit) |
| OAuth scopes | `spark:mcp`, recordings, transcripts, schedules (see project CLAUDE.md) |

## How to run

```bash
cd ~/Documents/GitHub/vidcastmcp
.venv/bin/python src/tools/webex_oauth.py   # if tokens needed
.venv/bin/python src/tools/mcp_connect.py   # register MCP with Claude Code
```

Token lifecycle: access ~14 days; refresh 90 days (renews on use).

## Canonical docs

- `~/Documents/GitHub/vidcastmcp/.claude/CLAUDE.md`
- `~/Documents/GitHub/vidcastmcp/README.md`
