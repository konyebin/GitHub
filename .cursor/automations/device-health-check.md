# Cursor Automation draft: weekday device health check

Use the **Automations** editor (Agents Window → New Automation) or ask Cursor to open the editor with this draft.

## Name

`wxops-device-health-weekdays`

## Description

List disconnected Webex Calling phones in camp0093 and summarize owners for morning lab review.

## Trigger

- **Type:** Schedule
- **Cron:** `0 8 * * 1-5` (weekdays 8:00 AM, adjust timezone in editor)

## Repository

- **Repo:** `~/Documents/GitHub` (or your GitHub remote for this monorepo)
- **Branch:** `main`

## Tools / MCP

- **wxops** MCP (must be registered on [cursor.com dashboard](https://cursor.com) for cloud agents — project `mcp.json` stdio servers do not appear in Automations catalog)
- Alternative: no MCP — agent runs shell only:

```bash
~/Documents/GitHub/wxops/.venv/bin/wxcli devices list -o json
```

## Instructions (agent prompt)

```
Read .cursor/wxops-session-context.md for org context.

1. Run: wxcli devices list -o json (full path: ~/Documents/GitHub/wxops/.venv/bin/wxcli)
2. Filter type=phone. Group by connectionStatus.
3. For each disconnected phone: displayName, MAC, product, personId/workspaceId if present.
4. If all phones connected: say "All desk phones connected."
5. Do NOT modify org config — read-only health check.
6. Output concise markdown summary suitable for a Webex space post.

Verification: include count of connected vs disconnected phones.
```

## Optional: post to Webex space

Add a second action or extend prompt if **messaging** MCP or webhook is configured:

- Target space: `voicemail space` (see session context) or a dedicated `#lab-ops` space
- Use `wxcli` messaging commands per `messaging-spaces` skill — only if token has message write scopes

## To finish in editor

- [ ] Confirm schedule timezone
- [ ] Connect dashboard wxops MCP or approve shell-only mode
- [ ] Set notification destination (email / Slack / none)
- [ ] Test run once before enabling schedule

## Related: telephony_calls webhook automation

Separate automation (event-driven, not schedule):

1. Deploy HTTPS webhook receiver for `telephony_calls` (see `wxops/docs/reference/webhooks-events.md`)
2. Trigger Cursor Automation via **custom webhook** on `alerting` events
3. Prompt agent to post caller ID + called party to a Webex space

Draft webhook handler pattern lives in wxops `call-control` skill — implement when you have a public URL (ngrok or cloud).
