# wxops

<ClientOnly>
  <DemoPanel slug="wxops" />
</ClientOnly>

## What it is

**Webex Calling playbook** — programmatic administration of Webex Calling, devices, routing, contact center, reporting, and CUCM migration. Primary execution is **`wxcli`** (166 command groups from OpenAPI specs), with agents/skills for guided workflows and an MCP server for reports and passthrough CLI.

## When to use it

- Provision users, locations, licenses, devices, workspaces
- Configure call queues, auto attendants, hunt groups, routing, trunks
- Pull CDR / usage reports or analyse billing
- CUCM → Webex migration (`wxcli cucm` pipeline)
- Any task in the root routing table that points to **wxops**

## Stack and entry points

| Item | Path |
|------|------|
| Project context | `wxops/CLAUDE.md` |
| CLI entry | `wxops/.venv/bin/wxcli` |
| MCP server | `wxops/mcp_server.py` |
| OpenAPI specs | `wxops/specs/*.json` |
| Reference docs | `wxops/docs/reference/` |
| Agents | `wxops/.claude/agents/` |

## Prerequisites

| Need | Detail |
|------|--------|
| Python | **3.13** only — `python3.13 -m venv .venv` in `wxops/` |
| Install | `cd ~/Documents/GitHub/wxops && .venv/bin/pip install -e ".[mcp]"` |
| Token | Root `~/Documents/GitHub/.env` synced to `~/.wxcli/config.json` or `wxcli configure` |
| Shell alias | `alias wxcli="$HOME/Documents/GitHub/wxops/.venv/bin/wxcli"` |

## How to run

```bash
cd ~/Documents/GitHub/wxops
.venv/bin/wxcli whoami
.venv/bin/wxcli --help
```

**Agents (Claude Code):** `/agents` → **wxc-calling-builder** for builds; **billing-analyst** for invoices/CDR.

**MCP tools:** `wxops_list_reports`, `wxops_fetch_report`, `wxops_run_command`, `wxops_billing_context`, `wxops_analyze_csv`.

**Cursor:** workspace root `~/Documents/GitHub`; server **wxops** in `.cursor/mcp.json`.

## Reporting gotchas (summary)

- CDR base URL: `https://analytics-calling.webexapis.com/v1/cdr_feed`
- Max **12-hour** window per CDR request; **30-day** retention
- At most **2** parallel `wxops_fetch_report` calls

Full detail: `wxops/docs/reference/reporting-analytics.md` and `wxops/.claude/skills/reporting/SKILL.md`.

## Canonical docs

- `~/Documents/GitHub/wxops/CLAUDE.md`
- `~/Documents/GitHub/CLAUDE.md` — Requirements § wxops
