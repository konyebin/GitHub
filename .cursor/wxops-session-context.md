# wxops session context (living summary)

> **Purpose:** Catch-up doc for new Cursor chats. Read this **after** `CLAUDE.md` files and **before** acting on call/WebRTC/MCP tasks. Update when a session completes significant wxops work.

**Last updated:** 2026-06-12 (Cursor level-up: skills, hooks, automations draft)

---

## Cursor infrastructure (`.cursor/`)

| Path | Purpose |
|------|---------|
| `rules/wxops-bootstrap.mdc` | Mandatory reads + verification-before-done |
| `skills/phone-test`, `device-reassign` | Slash commands for lab ops |
| `skills/wxops-verification`, `wxops-preflight` | Verify + parallel preflight |
| `skills/device-inventory-export/` | CSV export script → `devices_org_inventory.csv` |
| `hooks.json` + `hooks/wxops-phone-grind.sh` | Phone loop grind until scratchpad `DONE` |
| `automations/device-health-check.md` | Draft for weekday disconnected-phone Automation |
| `mcp-expansion-guide.md` | When to add vidcastmcp / dashboard wxops for cloud |
| `BUGBOT.md` | PR review focus (secrets, MCP launcher) |
| `../AGENTS.md` | Cross-tool routing for all agents |

Phone grind scratchpad template: `.cursor/scratchpad-wxops-phone.md` with lines `target: 5`, `delay: 5`, then `DONE` when complete.

---

## What we built and fixed

### wxops MCP (Cursor chat)

- **Registered:** `~/Documents/GitHub/.cursor/mcp.json` and global `~/.cursor/mcp.json`
- **Launcher:** `wxops/scripts/run-mcp-stdio.sh` → `wxops-mcp` (stdio only)
- **Bug fixed:** Launcher must **not** `source` root `.env` — `WEBEX_SCOPES` has unquoted spaces → bash parse error → MCP crash. Python loads token via `report_bot.load_token()`.
- **Verify:** `wxops/scripts/verify-mcp-stdio.sh`
- **Tools:** `wxops_run_command`, `wxops_list_reports`, `wxops_fetch_report`, `wxops_billing_context`, `wxops_analyze_csv`

### OAuth / tokens

- Root OAuth: `~/Documents/GitHub/.env` (`WEBEX_ACCESS_TOKEN`, refresh, scopes)
- Run: `cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py`
- Sync to wxcli: `~/.wxcli/config.json`
- **Current token user:** **User 1** — `admin+1@ccbcamp0093.wbx.ai` (`/people/me` verified 200)
- **Note:** Refresh token health varies; re-run OAuth if 401s return.

### WebRTC caller (`wxops/webrtc-caller/`)

| File | Role |
|------|------|
| `server.js` | Express on **port 3456**; serves `/token` from root `.env` |
| `index.html` | User 1 browser client; `line.register()`; **auto-answers** `line:incoming_call` |
| `place-call.js` | Headless Chrome outbound dial: `node place-call.js <dest>` |
| `ring-user1.js` | Headless listen + User 10 `create-dial` → wait for Connected |

**Not in official wxops skill map** — ad-hoc tooling; still follow `call-control` + `manage-call-settings` skills for API behavior.

### User 1 call settings (required for WebRTC)

Per `docs/reference/person-call-settings-behavior.md`:

- **Calling behavior:** `CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL` (was `NATIVE_WEBEX_TEAMS_CALLING` → caused `inactive` on `line.register()`)
- **App services:** `browserClientEnabled: true` (already set)

```bash
wxcli user-settings show-calling-behavior <User1_personId>
wxcli user-settings update-calling-behavior <User1_personId> --behavior-type CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL
wxcli user-settings show <User1_personId>
```

CLI group is **`user-settings`** (not `user-call-settings`).

### Voicemail → space

- **Skill:** `wxops/.claude/skills/voicemail-to-space/SKILL.md`
- **Script:** `wxops/voicemail_to_space/send_to_space.py` (primary; headless XSI)
- **Space:** `"voicemail space"` — ID cached in `wxops/voicemail_to_space/.voicemail_space_id`
- **Group VM** (`vm group 1`, ext 8201): `GET /telephony/voiceMessages?lineOwnerId={groupId}` → **400** (unsupported); use user mailbox API.

---

## Key IDs (camp0093 lab)

| Entity | Email / name | Extension | personId |
|--------|----------------|-----------|----------|
| **User 1** | `admin+1@ccbcamp0093.wbx.ai` | 3664 / +19844803664 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9mODdiZjJiYS1mYTgwLTRiMjItYmQ2Yi1iNTQ4Njk5NjJlMjY` |
| **User 10** | `admin+10@ccbcamp0093.wbx.ai` | 3653 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS85MDhhMmVjNC02YTQ5LTRkY2QtYjlhMS01NzY2ZGQ3MDIxYjE` |
| **admin** | `admin@ccbcamp0093.wbx.ai` | 9976 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hM2ZkYzlhYi1mZGUxLTRiMmYtYTNjZS0wY2UzNTE3YmJlNmI` |
| **VM group 1** | — | 8201 | `Y2lzY29zcGFyazovL3VzL1ZPSUNFTUFJTF9HUk9VUC9jN2EyZjZlMy00OWM3LTQ2NTgtODBmMC0xMjhhNWU2MTA3NDk` |

---

## Lessons learned (don't repeat)

### WebRTC identity

- WebRTC client = **token user only**. Cannot place calls as User 10 while token is User 1.
- `localhost:3456` registers **User 1's browser endpoint** — not a separate dialable number.
- **User 1 dialing 3664 from WebRTC** = self-call → times out / no useful connect.
- **Working ring + answer pattern:** User 1 WebRTC **listening** + **User 10** rings via Members API:

```bash
wxcli call-controls create-dial <User10_personId> --destination 3664
```

### Call control

- User-level `/telephony/calls/dial` needs **user-level** token with `spark:calls_read` + `spark:calls_write`.
- Admin initiating on behalf of users: **Members API** `create-dial` with `spark-admin:calls_*`.
- WebRTC scope: `spark:webrtc_calling`.

### Phone-to-phone loop (admin 8845 ↔ User 10 9851)

**Skill:** `wxops/.claude/skills/phone-to-phone-calls/SKILL.md`  
**Script:** `wxops/.claude/skills/phone-to-phone-calls/scripts/phone-call-loop.py`

| User | Ext | personId |
|------|-----|----------|
| admin | 9976 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hM2ZkYzlhYi1mZGUxLTRiMmYtYTNjZS0wY2UzNTE3YmJlNmI` |
| User 10 | 3653 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS85MDhhMmVjNC02YTQ5LTRkY2QtYjlhMS01NzY2ZGQ3MDIxYjE` |

Flow: `create-dial` (admin → 3653, admin endpoint) → answer first leg if `alerting` → answer User 10 when `alerting` → hold 5s → `create-hangup-members` on admin. Poll `list-calls` between steps. Verified 5/5 cycles.

### Device reassignment by MAC

**Skill:** `wxops/.claude/skills/reassign-device-by-mac/SKILL.md`  
**Script:** `wxops/.claude/skills/reassign-device-by-mac/scripts/reassign-device.py`

Primary owner cannot change in place (error **25487**) → capture MAC + `product` model, append `devices_deleted.csv`, delete, `devices create` same MAC on new `personId`, `apply-changes-for`. Example: 9851 MAC `20CC274BEA67` admin → User 10.

### Reporting (from root CLAUDE.md)

- CDR: `https://analytics-calling.webexapis.com/v1/cdr_feed`
- Max 12-hour window; 30-day retention; max **2** parallel `wxops_fetch_report`.

---

## Open / next steps

- [ ] Confirm `ring-user1.js` end-to-end: User 1 headless listener → User 10 dial → **Connected** in status log
- [ ] Re-run OAuth if refresh token invalid; verify silent refresh
- [ ] Voicemail test: leave VM on User 1 → `send_to_space.py --latest`
- [ ] Optional: document `webrtc-caller/` in `wxops/CLAUDE.md` file map
- [ ] Telephony webhooks idea (deferred): `call-control` skill + `webhooks-events.md`

---

## How to update this file

After any session that changes tokens, IDs, scripts, or fixes a gotcha: append or edit the relevant section and bump **Last updated**.
