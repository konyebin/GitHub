# AGENTS.md — cross-tool instructions

Instructions for AI coding agents (Cursor, Claude Code, Codex, Copilot) working in `~/Documents/GitHub/`.

## Start here

1. **[CLAUDE.md](./CLAUDE.md)** — OAuth, tokens, MCP, Python versions, cross-project routing table.
2. **Project CLAUDE.md** — e.g. [wxops/CLAUDE.md](./wxops/CLAUDE.md) for Webex Calling.
3. **Cursor-specific:** [.cursor/wxops-session-context.md](./.cursor/wxops-session-context.md) + [.cursor/rules/](./.cursor/rules/).

## Project routing (short)

| Need | Project | Entry |
|------|---------|--------|
| Webex Calling admin, CDR, devices, calls | `wxops/` | wxops MCP or `wxcli` |
| RoomOS xAPI / device control | `test/device-mcp-server/` | roomos MCP |
| Vidcast recordings / transcripts | `vidcastmcp/` | vidcast MCP |
| Check Back customer workbooks | `check-back-intelligence/` | `python -m src.cli` |
| Docs site / demos | `docs/` | `npm run docs:dev` |
| MCP server discovery | `my-orchestrator/` | orchestrator MCP |

Full table: [CLAUDE.md § Cross-Project Routing](./CLAUDE.md).

## Cursor skills (this repo)

| Skill | Trigger |
|-------|---------|
| `phone-test` | `/phone-test` — desk phone loop |
| `device-reassign` | `/device-reassign` — MAC-based move |
| `phone-to-phone-calls` | Ring/test two desk phones |
| `reassign-device-by-mac` | Delete + recreate phone |
| `device-inventory-export` | CSV of org devices |
| `wxops-verification` | Before claiming wxops work done |
| `wxops-preflight` | Parallel preflight with `/multitask` |

Canonical wxops procedures: `wxops/.claude/skills/*/SKILL.md`.

## Safety

- Never commit `.env`, tokens, or customer PII.
- wxops venv: **Python 3.13** only (`wxops/.venv`).
- Root OAuth scripts: **Python 3.14** (`~/Documents/GitHub/.venv`).
