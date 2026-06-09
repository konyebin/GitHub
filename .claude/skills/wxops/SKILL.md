---
name: wxops
description: |
  Navigate the Webex Calling Playbook project. Routes to the right agent,
  skill, or reference doc for any Webex Calling task — provisioning, migration,
  reporting, billing, devices, routing, call features, or debugging.
  Primary interface: /agents → wxc-calling-builder.
allowed-tools: Bash, Read, Glob
argument-hint: [task-description]
---

# wxops Skill — Webex Calling Playbook Router

Routes any Webex Calling task to the correct agent, skill, or reference doc.

**Project path:** `~/Documents/GitHub/wxops/`

---

## Start here

```
/agents → wxc-calling-builder    ← for most tasks (build, configure, migrate)
/agents → billing-analyst         ← for invoices, CDR analysis, usage reports
/wxc-calling-debug                ← for debugging a failing configuration
/reporting                        ← for CDR queries and report generation
/misc-report                      ← for the full 9-section ops health dashboard
```

**Do not run `wxcli` commands directly** — use the `wxc-calling-builder` agent, which manages the full workflow including authentication, planning, execution, and verification.

---

## Task routing table

| Task | Go to |
|---|---|
| Provision users, locations, licenses | `/agents` → wxc-calling-builder |
| Configure AA, CQ, hunt groups | `/agents` → wxc-calling-builder |
| Configure Customer Assist (CX Essentials) | `/agents` → wxc-calling-builder |
| Set up trunks, dial plans, PSTN routing | `/agents` → wxc-calling-builder |
| Manage devices (phones, DECT, workspaces) | `/agents` → wxc-calling-builder |
| Migrate from CUCM to Webex | `/agents` → wxc-calling-builder → "Run a CUCM migration" |
| Explain a customer invoice | `/agents` → billing-analyst |
| Analyse CDR / usage report | `/agents` → billing-analyst |
| Debug a failing config | `/wxc-calling-debug` |
| CDR queries (75+ recipes) | `/reporting` |
| Full ops health report (9 sections) | `/misc-report` |
| Manage user call settings | `/manage-call-settings` |
| Real-time call control / webhooks | `/call-control` |
| Recording compliance | `/reporting` or `/audit-compliance` |
| Manage messaging spaces / bots | `/messaging-spaces` or `/messaging-bots` |
| Video Mesh monitoring | `/video-mesh` |
| Contact Center provisioning | `/contact-center` |
| License audit / reclamation | `/manage-licensing` |
| SCIM / directory sync | `/manage-identity` |
| Teardown / cleanup | `/teardown` |

---

## wxcli — CLI execution layer

166 command groups, generated from 7 OpenAPI 3.0 specs.

```bash
wxcli --help                        # list all command groups
wxcli <group> --help                # commands in a group
wxcli <group> <command> --help      # options for a command
```

**Multi-org / partner admins:**
```bash
wxcli configure       # detects multi-org token, prompts for org selection
wxcli switch-org      # change active target org
wxcli whoami          # shows Target: line when org is set
```

**Batch cleanup:**
```bash
wxcli cleanup run --scope "LocationName" --dry-run
wxcli cleanup run --all --include-users --force
```

---

## MCP server tools (available in every session)

| Tool | Purpose |
|---|---|
| `wxops_list_reports` | List available Webex report templates |
| `wxops_fetch_report` | Download a report to /tmp/ CSV |
| `wxops_run_command` | Run any wxcli command |
| `wxops_billing_context` | Load billing reference context |
| `wxops_analyze_csv` | Analyze a downloaded CSV |

---

## CUCM migration pipeline

```bash
wxcli cucm init
wxcli cucm discover [--from-file cucm_export.xml]
wxcli cucm normalize
wxcli cucm map
wxcli cucm analyze
wxcli cucm decisions       # review + override migration decisions
wxcli cucm plan
wxcli cucm preflight
wxcli cucm export
# Then invoke /cucm-migrate to execute
```

Assessment only (no plan/execute needed):
```bash
wxcli cucm init → discover → normalize → map → analyze
wxcli cucm report --brand "Acme" --prepared-by "Your Name"
```

---

## Reference docs (wxops/docs/reference/)

| Doc | Covers |
|---|---|
| `reporting-analytics.md` | CDR base URL, field names, report template IDs, 30-day retention |
| `authentication.md` | Auth methods, tokens, scopes, OAuth flows, partner multi-org |
| `call-features-major.md` | Auto attendants, call queues, hunt groups |
| `call-routing.md` | Dial plans, trunks, route groups, PSTN |
| `devices-core.md` | Device CRUD, activation, telephony devices |
| `provisioning.md` | People, licenses, locations, org setup |

Full reference doc list is in `wxops/CLAUDE.md` §File Map.

---

## Key facts

- CDR base URL: `https://analytics-calling.webexapis.com/v1/cdr_feed` — **not** `webexapis.com`
- Max 12-hour window per CDR request; 30-day retention
- EU orgs return HTTP 451 — follow redirect to regional URL
- Run at most **2 `wxops_fetch_report` calls in parallel**
- `wxcli cleanup` deletes in 13 dependency-safe layers (reverse of creation order)
- 2535 CUCM migration tests passing
- All reference docs updated 2026-03-18 with Raw HTTP fallback sections

---

## Gotchas

- `call-controls` requires user-level OAuth (not admin token)
- `my-call-settings` requires calling-licensed user on the authenticated account
- Customer Assist queues are hidden from `call-queue list` — pass `--has-cx-essentials true`
- Contact Center commands require CC-scoped OAuth and region config
- Workspace `/telephony/config/` settings require Professional license
