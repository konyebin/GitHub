# MCP expansion guide (Cursor)

Evaluation for Cloud Agents, Automations, and local IDE — **2026-06-12**.

## Current local config

[`mcp.json`](./mcp.json):

| Server | Transport | Tools (approx) | Status |
|--------|-----------|----------------|--------|
| **wxops** | stdio (`run-mcp-stdio.sh`) | 5 | Active — primary lab interface |
| **roomos** | stdio (device-mcp-server) | varies | Active — RoomOS xAPI |

**Practical limit:** ~40 MCP tools across all servers before agent tool selection degrades. You are well under budget (~5 + roomos).

## Not registered (candidates)

| Server | Project | Tools | Recommendation |
|--------|---------|-------|----------------|
| **vidcastmcp** | `vidcastmcp/` | ~29 | Add **only when** doing Vidcast/recording work in Cursor. Disable when on wxops-only sessions. |
| **my-orchestrator** | `my-orchestrator/` | 4 (ping, list, discover) | Low cost meta-server. Optional — helps discover dashboard MCPs; not needed for daily wxops. |

## Cloud Agents / Automations gap

**Project `mcp.json` servers are NOT eligible for Cursor Automations MCP actions.**

For scheduled device health or webhook-driven agents:

1. Register **wxops** (or a thin wrapper) on [cursor.com → MCP](https://cursor.com) dashboard (team or personal).
2. Or use **shell-only** automations calling `wxops/.venv/bin/wxcli` (see [automations/device-health-check.md](./automations/device-health-check.md)).
3. OAuth-protected MCP in cloud may need IDE testing first until cloud OAuth patches land.

### wxops dashboard registration checklist

- [ ] Same token/scopes as local `.env` (never commit secrets — use Cursor env vars in dashboard)
- [ ] Command: `~/Documents/GitHub/wxops/.venv/bin/wxops-mcp` or packaged HTTP wrapper if required by dashboard
- [ ] Verify Automations editor shows server under **GetAvailableMcpServers**
- [ ] Pin package versions — do not use `@latest` for npx MCP servers

## roomos + wxops together

Use both when:

- Phone shows `disconnected` in wxops but exists in org
- Need xAPI `Status` / `Diagnostics` beyond Cloud API

Preflight skill: `.cursor/skills/wxops-preflight/SKILL.md` § Disconnected desk phone.

## Security

- Read-only tokens where possible for inventory/report automations
- Review `.cursor/mcp.json` changes like infrastructure (PR review)
- Disable unused MCP tools in Cursor Settings → Tools & MCP

## Decision

**Keep current 2-server setup for daily IDE work.** Add vidcastmcp on demand. Register wxops on dashboard when first Automation is ready. Skip my-orchestrator unless you frequently forget which MCPs exist.
