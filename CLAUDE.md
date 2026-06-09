# Claude Instructions — Root Workspace

> **This is the root CLAUDE.md for `~/Documents/GitHub/`.** All project-level CLAUDE.md files in this workspace inherit from here. Read this file first before reading any project-level CLAUDE.md. It defines shared utilities, global conventions, and authentication tools available to every project.

---

## Fresh Install Setup

When setting up this workspace on a new machine, complete these steps before using any project.

### 1. Python Environments

**Root venv** (`~/Documents/GitHub/.venv`) — Python 3.14, used for `webex_oauth.py` and root-level scripts:
```bash
cd ~/Documents/GitHub && python3 -m venv .venv
.venv/bin/pip install requests python-dotenv
```

**wxops venv** (`~/Documents/GitHub/wxops/.venv`) — Must use **Python 3.13** (not 3.14 — pydantic-core fails to build on 3.14):
```bash
cd ~/Documents/GitHub/wxops
python3.13 -m venv .venv
.venv/bin/pip install -e ".[mcp]"
```
The **`mcp`** optional extra installs MCP server deps (`mcp`, `httpx`, `pandas`, `python-dotenv`) and editable **wxcli**. For Cursor, **`/.cursor/mcp.json`** already registers the **wxops** stdio server (same `mcp_server.py`, **`envFile`** → root **`~/Documents/GitHub/.env`**).

### 2. Shell Alias for wxcli

Add to `~/.zshrc` (or `~/.bashrc`):
```bash
alias wxcli="$HOME/Documents/GitHub/wxops/.venv/bin/wxcli"
```

> Note: The old alias pointed to `~/wxops/.venv/bin/wxcli` (project was moved). Always use `~/Documents/GitHub/wxops/.venv/bin/wxcli`.

### 3. Webex OAuth Token

The `.env` file at `~/Documents/GitHub/.env` holds the shared OAuth token. Required keys:
```
WEBEX_CLIENT_ID=...
WEBEX_CLIENT_SECRET=...
WEBEX_SCOPES=spark:all spark:xapi_commands spark:xapi_statuses spark:calls_write spark:calls_read spark:webrtc_calling spark:applications_token spark:people_write spark:devices_write spark:devices_read spark:telephony_config_write spark:telephony_config_read spark:places_write spark:places_read spark:organizations_read spark:mcp spark:webhooks_read spark:webhooks_write spark:recordings_write spark:recordings_read spark-admin:messages_write spark-admin:messages_read spark-admin:calling_cdr_read spark-admin:recordings_write spark-admin:recordings_read spark-admin:reports_write spark-admin:reports_read spark-admin:people_write spark-admin:people_read spark-admin:licenses_read spark-admin:roles_read spark-admin:telephony_config_write spark-admin:telephony_config_read spark-admin:telephony_pstn_write spark-admin:telephony_pstn_read spark-admin:workspaces_write spark-admin:workspaces_read spark-admin:workspace_locations_write spark-admin:workspace_locations_read spark-admin:workspace_metrics_read spark-admin:places_write spark-admin:places_read spark-admin:locations_write spark-admin:locations_read spark-admin:devices_write spark-admin:devices_read spark-admin:organizations_write spark-admin:organizations_read spark-admin:resource_groups_read spark-admin:resource_group_memberships_write spark-admin:resource_group_memberships_read spark-admin:call_qualities_read spark-admin:calls_write spark-admin:calls_read spark-admin:broadworks_billing_reports_write spark-admin:broadworks_billing_reports_read spark-admin:broadworks_subscribers_write spark-admin:broadworks_subscribers_read spark-admin:broadworks_enterprises_write spark-admin:broadworks_enterprises_read spark-admin:wholesale_billing_reports_write spark-admin:wholesale_billing_reports_read spark-admin:wholesale_sub_partners_write spark-admin:wholesale_sub_partners_read spark-admin:wholesale_customers_write spark-admin:wholesale_customers_read spark-admin:wholesale_subscribers_write spark-admin:wholesale_subscribers_read spark-admin:wholesale_workspace_write spark-compliance:events_read spark-compliance:messages_write spark-compliance:messages_read spark-compliance:recordings_write spark-compliance:recordings_read spark-compliance:memberships_write spark-compliance:memberships_read spark-compliance:meetings_write spark-compliance:meetings_read spark-compliance:rooms_write spark-compliance:rooms_read spark-compliance:teams_read spark-compliance:team_memberships_write spark-compliance:team_memberships_read spark-compliance:webhooks_write spark-compliance:webhooks_read audit:events_read analytics:read_all identity:tokens_write identity:tokens_read identity:people_rw identity:people_read identity:groups_rw identity:groups_read identity:organizations_rw identity:organizations_read Identity:contact Identity:one_time_password identity:placeonetimepassword_create Identity:Config Identity:Organization meeting:admin_recordings_write meeting:admin_recordings_read meeting:admin_transcripts_read meeting:admin_participants_read meeting:admin_schedule_write meeting:admin_schedule_read meeting:admin_preferences_write meeting:admin_preferences_read meeting:admin_config_write meeting:admin_config_read application:webhooks_write application:webhooks_read wxc-dedicateduc:admin_perfmon_read webexsquare:admin cjp:config cjp:config_write cjp:config_read cjp:user cjp:task_write cjp:task_read cjds:admin_org_read cjds:admin_org_write cloud-contact-center:pod_conv
WEBEX_ACCESS_TOKEN=...
WEBEX_REFRESH_TOKEN=...
```

> **Scope rule:** `WEBEX_SCOPES` must exactly match the scopes enabled in the Webex Developer Portal — no more, no less. When adding a scope, only append; never remove existing ones unless the user explicitly says a scope is not in the portal (unofficial/unsupported). After any edit, verify the previous scopes are intact. Re-run `webex_oauth.py` after any scope change to get a token with the updated set.

Run the OAuth flow once to populate the tokens:
```bash
cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py
```

The token auto-refreshes silently on expiry. You only need to re-run `webex_oauth.py` if you add new scopes. Ensure all scopes above are enabled in the Webex Developer Portal under your OAuth integration before running.

### 4. wxcli Token Sync

After the OAuth flow, sync the token into wxcli's config so CLI commands work:
```python
# Run once after webex_oauth.py
import json, pathlib, re
env = {}
for line in pathlib.Path.home().joinpath("Documents/GitHub/.env").read_text().splitlines():
    if "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip("'\"")
cfg = pathlib.Path.home() / ".wxcli" / "config.json"
data = json.loads(cfg.read_text())
data["profiles"]["default"]["token"] = env["WEBEX_ACCESS_TOKEN"]
data["profiles"]["default"]["expires_at"] = None
cfg.write_text(json.dumps(data, indent=2))
```

Or simply run: `wxcli configure` and paste the token manually.

### 5. wxops Global MCP Server

Register the wxops MCP server globally so its tools are available in every Claude Code project:
```bash
claude mcp add --scope user wxops \
  /Users/konyebin/Documents/GitHub/wxops/.venv/bin/python \
  /Users/konyebin/Documents/GitHub/wxops/mcp_server.py
```

Equivalent using the **`wxops-mcp`** console entry (after `pip install -e ".[mcp]"`):
```bash
claude mcp add --scope user wxops \
  /Users/konyebin/Documents/GitHub/wxops/.venv/bin/wxops-mcp
```

Verify with: `claude mcp list` — wxops should show `✓ Connected`.

This exposes 5 tools to every Claude Code session: `wxops_fetch_report`, `wxops_list_reports`, `wxops_run_command`, `wxops_billing_context`, `wxops_analyze_csv`.

**Before using any wxops reporting tool** (CDR, reports, recordings), read these reference docs first — they contain the correct base URLs, API constraints, field names, and gotchas:
- `~/Documents/GitHub/wxops/docs/reference/reporting-analytics.md` — CDR base URL, report template IDs, 30-day retention, 12-hour window limit, gotchas
- `~/Documents/GitHub/wxops/.claude/skills/reporting/SKILL.md` — full workflow, CLI commands, 75 CDR recipes

Key facts to know before any CDR call:
- CDR base URL: `https://analytics-calling.webexapis.com/v1/cdr_feed` — **NOT** `webexapis.com`
- EU orgs return HTTP 451 with the correct regional URL — always follow the redirect
- Max 12-hour window per CDR request; 30-day retention
- Use `wxops_fetch_report` for pre-built reports — do not manually queue via `/v1/reports` API
- Run at most **2 `wxops_fetch_report` calls in parallel** — more causes connection drops

### 6. Deleted Devices Log

`~/Documents/GitHub/devices_deleted.csv` — running log of all deleted Webex devices. Append to this file (do not overwrite) when deleting devices. Columns: `displayName, model, mac, serial, ip, connectionStatus, created, lastSeen, deviceId`.

---

## Requirements: root, wxops, and test/device-mcp-server

These three targets use **different runtimes**: root scripts use **Python 3.14**; **wxops** uses **Python 3.13** in its own venv (do not use 3.14 for wxops — pydantic-core build issues); **test/device-mcp-server** uses **Node.js 18+**. All can share the same Webex **access token** if your OAuth integration’s scopes cover each surface (Calling/admin for wxops; `spark:xapi_*` and device scopes for RoomOS MCP — align scopes in the Developer Portal with what you plan to call).

### Root (`~/Documents/GitHub`)

| Need | Detail |
|------|--------|
| Python | **3.14** — `python3 -m venv .venv` at repo root |
| Packages | `.venv/bin/pip install requests python-dotenv` |
| Webex app | Integration at [developer.webex.com](https://developer.webex.com) with redirect **`http://localhost:8080/callback`** (must match `webex_oauth.py`) |
| Secrets | **`~/Documents/GitHub/.env`** — at minimum `WEBEX_CLIENT_ID`, `WEBEX_CLIENT_SECRET`, `WEBEX_SCOPES`, `WEBEX_ACCESS_TOKEN`, `WEBEX_REFRESH_TOKEN` (see §3 above for the full scope string used here) |
| Run OAuth | `cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py` (browser opens; local listener on port **8080**) |

### wxops (`~/Documents/GitHub/wxops`)

| Need | Detail |
|------|--------|
| Python | **3.13** only — `python3.13 -m venv .venv` inside `wxops/` |
| Install | `cd ~/Documents/GitHub/wxops && .venv/bin/pip install -e ".[mcp]"` (installs wxcli + MCP extras; Python **3.13** venv) |
| Token | Same root `.env` token synced into **`~/.wxcli/config.json`** (§4) **or** `wxcli configure` / paste token; must include scopes for the APIs you use |
| Shell | **`wxcli` alias** pointing at `~/Documents/GitHub/wxops/.venv/bin/wxcli` (§2) |
| Optional | **Claude Code** + global MCP registration (§5); **Cursor** → **`/.cursor/mcp.json`** server **`wxops`** |

### test/device-mcp-server (`~/Documents/GitHub/test/device-mcp-server`)

| Need | Detail |
|------|--------|
| Node.js | **18 or higher** |
| Install / build | `cd ~/Documents/GitHub/test/device-mcp-server && npm install && npm run build` |
| Token | **`WEBEX_ACCESS_TOKEN`** (and scopes) from **`~/Documents/GitHub/.env`** after **`~/Documents/GitHub/.venv/bin/python webex_oauth.py`** — same as the rest of the workspace; include xAPI + device read scopes (see `test/device-mcp-server/OAUTH_SETUP_GUIDE.md`). Optional: `node oauth-helper.js` in this folder only if you are not using root OAuth. |
| Devices | **Webex device IDs** for RoomOS endpoints you control; token must allow Cloud API / xAPI access as documented in `test/device-mcp-server/README.md` |
| Run | Default **stdio** when started as `node dist/index.js` (Cursor **roomos** MCP). For HTTP MCP: `TRANSPORT=http npm start` — **`PORT`** defaults to **3001** unless set. |
| **Cursor** | **`/.cursor/mcp.json`** registers **`roomos`** with **`envFile`** → **`${workspaceFolder}/.env`** (GitHub root). Run `npm run build` under `test/device-mcp-server` first; reload MCP after token changes. |

---

## Cross-Project Routing

**If you are in one project and cannot accomplish what the user is asking, check this table first before saying it cannot be done. Direct or switch the user to the correct project.**

| If the user wants to… | Go to project | How to get there |
|----------------------|---------------|-----------------|
| Add, remove, or configure a Webex device | `wxops` | `cd ~/Documents/GitHub/wxops && claude` |
| Provision or deprovision a Webex Calling user | `wxops` | `cd ~/Documents/GitHub/wxops && claude` |
| Set up a call queue, auto attendant, or hunt group | `wxops` | `cd ~/Documents/GitHub/wxops && claude` |
| Pull a CDR or usage report for a customer org | `wxops` | `cd ~/Documents/GitHub/wxops && claude` |
| Explain or estimate a Webex customer bill | `wxops` → billing-analyst agent | `cd ~/Documents/GitHub/wxops && claude` → `/agents` → billing-analyst |
| Configure call routing, trunks, or dial plans | `wxops` | `cd ~/Documents/GitHub/wxops && claude` |
| Migrate users from CUCM to Webex | `wxops` | `cd ~/Documents/GitHub/wxops && claude` → `/agents` → wxc-calling-builder |
| Manage Webex Calling licenses | `wxops` | `cd ~/Documents/GitHub/wxops && claude` |
| Browse, search, or retrieve Vidcast recordings | `vidcastmcp` | `cd ~/Documents/GitHub/vidcastmcp && claude` |
| Get meeting transcripts or recordings | `vidcastmcp` | `cd ~/Documents/GitHub/vidcastmcp && claude` |
| Search or access Webex meeting schedules | `vidcastmcp` | `cd ~/Documents/GitHub/vidcastmcp && claude` |
| Scrape or extract data from a website | `scrapeweb` | `cd ~/Documents/GitHub/scrapeweb && claude` |
| OCR a dashboard screenshot into Excel | `Lookback` | `cd ~/Documents/GitHub/Lookback && claude` |
| Discover what MCP servers are available on this machine | `my-orchestrator` | `cd ~/Documents/GitHub/my-orchestrator && claude` |
| Run the Webex OAuth flow to get a fresh token | Root GitHub folder | `cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py` |
| Control RoomOS devices via MCP (HTTP/stdio, token-based) | `test/device-mcp-server` | `cd ~/Documents/GitHub/test/device-mcp-server` — see README; requirements in **Requirements: root, wxops, and test/device-mcp-server** above |

Human-readable project pages (browser): run `cd ~/Documents/GitHub/docs && npm run docs:dev` — VitePress site with one page per top-level folder under `docs/projects/`.

### Routing Rules for Claude

1. **Never say "I can't do that" without checking this table first.** Another project in this workspace may already handle it.
2. **If you are mid-session in one project** and the user asks for something outside your scope, say: *"That's handled by the `[project]` project. Switch there with: `cd ~/Documents/GitHub/[project] && claude`"*
3. **wxops handles all Webex Calling administration.** If the task involves any Webex Calling feature — devices, users, numbers, routing, queues, reports, billing — wxops is the answer.
4. **vidcastmcp handles all Webex video content.** Recordings, transcripts, playlists, and meeting content live there.
5. **When in doubt**, run `ls ~/Documents/GitHub/` to see all available projects and check their CLAUDE.md for capabilities.

---

## Shared Utilities

### Webex OAuth — `~/Documents/GitHub/webex_oauth.py`

Automates the full Webex OAuth 2.0 flow for any project that needs a long-lived Webex access token.

**What it does:**
1. Opens the Webex authorization page in the browser
2. Starts a local server on `http://localhost:8080` to catch the redirect
3. Exchanges the authorization code for tokens
4. Writes `WEBEX_ACCESS_TOKEN` and `WEBEX_REFRESH_TOKEN` into `~/Documents/GitHub/.env`

**Setup (one time per project):**
```bash
# Add to ~/Documents/GitHub/.env
WEBEX_CLIENT_ID=...
WEBEX_CLIENT_SECRET=...
WEBEX_SCOPES=spark:all   # adjust per project
```

**Run:**
```bash
cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py
```

**Also exposes `refresh_token(refresh_tok)`** — call this programmatically to silently refresh an expired token without browser interaction.

**Default scopes (if WEBEX_SCOPES not set):** `spark:all vidcast:recordings_read vidcast:playlists_read`

**Shared Python environment:** `~/Documents/GitHub/.venv` (Python 3.14)
- Pre-installed: `requests`, `python-dotenv`
- Use for any script at the GitHub root level: `.venv/bin/python <script>.py`

**To use in a project:**
```python
import sys
sys.path.insert(0, "/Users/konyebin/Documents/GitHub")
from webex_oauth import refresh_token
```

> **Note for personal access tokens (12-hour expiry):** Use `wxcli configure` inside the wxops project instead of this OAuth flow. This file is for OAuth integrations with a client ID/secret that produce long-lived refresh tokens.

---

## General Behavior
- Lead responses with the executive summary (why first, then how/what).
- Use prose over bullet points unless the user asks for a list or structure genuinely requires it.
- No emojis unless the user uses them first.
- Keep tone warm but direct. No filler phrases ("Certainly!", "Great question!").
- For ambiguous multi-step tasks, ask one clarifying question before starting work.
- Save all final deliverables to `/Users/konyebin/CLAUDE/` and share via `computer://` links.

## Prompt Optimization

When asked to optimize a prompt, use the following approach:

You are a prompt optimization expert. Rewrite prompts to minimize token usage while preserving 100% of original intent, constraints, & required output quality.

Rules:
- Never remove requirements — only compress how they're expressed
- Prefer imperatives over explanations ("Return JSON" not "Please make sure to return output as JSON")
- Cut filler: pleasantries, redundant context, over-explanation
- Use symbols/abbreviations where unambiguous (e.g., "w/" "→" "e.g." "&")
- Collapse lists into comma-separated inline form unless order/structure matters
- Strip examples if the instruction is self-evident; keep 1 max if needed
- For RAG prompts: flag redundant/irrelevant context (mark it, don't auto-remove)
- Collapse repeated instructions into a single canonical statement
- Preserve all placeholders, variables, & format requirements exactly

Output format:
1. Optimized prompt (raw, ready to copy)
2. Token delta estimate (original → optimized, rough %)
3. What was changed (3 bullets max)
4. Any warnings (e.g., "removed an example — test output quality")

## New Project Structure

When asked to create a new project, scaffold the following layout under `/Users/konyebin/CLAUDE/<project-name>/`:

```
<project-name>/
├── CLAUDE.md              # Project-level context: what it is, stack, how to run/test, key conventions
├── src/                   # All source code
│   └── CLAUDE.md          # src-level context: code organization, shared patterns
├── docs/                  # Documentation
│   └── CLAUDE.md          # Doc conventions: format, audience, where things live
├── tests/                 # Tests mirroring src/ structure
│   └── CLAUDE.md          # Test conventions: frameworks, fixtures, how to run
└── README.md              # Human-facing project overview
```

**CLAUDE.md rules for new projects:**

- Root `/CLAUDE/CLAUDE.md` — already exists, global defaults, never repeat here
- Project-level `CLAUDE.md` — what the project is, tech stack, entry points, build/run/test commands, key dependencies, gotchas
- First-level subdirectory `CLAUDE.md` — one per direct child of the project root (src, docs, tests, etc.); covers what that directory owns and any conventions specific to it
- Deeper `CLAUDE.md` files — only when a subdirectory has genuinely distinct logic, data contracts, or conventions that differ from its parent (e.g. a migration subcommand with its own pipeline). Don't add them by default.
- Each CLAUDE.md should only contain what's *new or different* from its parent — Claude reads the full chain root → current directory

**On every new project, always create:**
1. The directory structure above (adapted to the project type)
2. A `CLAUDE.md` at the project root and in each first-level subdirectory only
3. A project-level `CLAUDE.md` with: purpose, stack, how to run, how to test, any non-obvious conventions
4. A `README.md` with a human-readable summary

Ask one clarifying question if the project type or stack is ambiguous before scaffolding.

## File & Code Conventions
- Prefer editing existing files over creating new ones.
- For new files <100 lines: write directly to `/Users/konyebin/CLAUDE/`.
- For larger files: build iteratively, section by section.
- Always read a file before editing it.
- When running shell commands, use absolute paths.
- Python: always use `--break-system-packages` with pip.
