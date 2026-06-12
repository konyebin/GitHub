---
name: reassign-device-by-mac
description: |
  Delete and reprovision a Webex desk phone on a new user/workspace using the same MAC.
  Capture MAC and model before delete. Use when moving phones or error 25487.
---

# Reassign Device by MAC (Cursor)

**Canonical skill:** [`wxops/.claude/skills/reassign-device-by-mac/SKILL.md`](~/Documents/GitHub/wxops/.claude/skills/reassign-device-by-mac/SKILL.md)

Read that file + `manage-devices` before acting.

## Quick run

```bash
cd ~/Documents/GitHub/wxops
.venv/bin/python .claude/skills/reassign-device-by-mac/scripts/reassign-device.py \
  --mac 20CC274BEA67 \
  --email admin+10@ccbcamp0093.wbx.ai
```

`--dry-run` to preview. Append delete to `~/Documents/GitHub/devices_deleted.csv`.

## Verify

`wxcli devices list --mac <MAC> -o json` — correct `personId`. See wxops-verification skill.
