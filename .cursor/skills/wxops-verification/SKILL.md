---
name: wxops-verification
description: |
  Verification checklist before claiming wxops/Webex Calling tasks succeed. Use before
  saying "done", after OAuth/MCP changes, WebRTC setup, phone loops, or device reassign.
---

# wxops Verification

Run applicable checks and **show output** before marking work complete.

## Always (wxops sessions)

```bash
~/Documents/GitHub/wxops/scripts/verify-mcp-stdio.sh
~/Documents/GitHub/wxops/.venv/bin/wxcli people me -o json
```

Confirm `/people/me` email is the user you intend (WebRTC identity = token user only).

## Phone-to-phone loop

```bash
~/Documents/GitHub/wxops/.venv/bin/wxcli devices list -o json
# Expect caller + callee phones: type phone, connectionStatus connected

cd ~/Documents/GitHub/wxops
.venv/bin/python .claude/skills/phone-to-phone-calls/scripts/phone-call-loop.py --count 1 --delay 3
echo "exit=$?"
```

Exit code must be 0.

## Device reassign by MAC

```bash
~/Documents/GitHub/wxops/.venv/bin/wxcli devices list --mac <MAC12HEX> -o json
# personId must match target; row appended to ~/Documents/GitHub/devices_deleted.csv on delete
```

## WebRTC (User 1 browser client)

```bash
~/Documents/GitHub/wxops/.venv/bin/wxcli user-settings show-calling-behavior <personId> -o json
# behaviorType: CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL
~/Documents/GitHub/wxops/.venv/bin/wxcli user-settings show <personId> -o json
# browserClientEnabled: true
```

## MCP smoke

Via wxops MCP `wxops_run_command`: `people me -o json` or `devices list -o json` — must return 200, not 401.

## On failure

Do not say "done". Report the failing check, fix root cause (often token refresh: `cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py`), re-run.
