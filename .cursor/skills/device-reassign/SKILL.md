---
name: device-reassign
description: Reassign a desk phone to a new user by MAC (delete + recreate)
disable-model-invocation: true
---

# Device reassign

Move a phone to a new user/workspace by MAC. **Capture MAC before delete.**

## Parse user args

From the prompt after `/device-reassign`:

- **MAC** — 12 hex chars (with or without colons)
- **target** — user email or personId (or `--workspace-id` if workspace phone)

## Steps

1. Read `wxops/.claude/skills/reassign-device-by-mac/SKILL.md` + session context.
2. Normalize MAC to 12 uppercase hex.
3. Run (prefer script):

```bash
cd ~/Documents/GitHub/wxops
.venv/bin/python .claude/skills/reassign-device-by-mac/scripts/reassign-device.py \
  --mac <MAC> --email <EMAIL>
```

Or `--person-id` / `--workspace-id`. Use `--dry-run` if user asked to preview only.

4. Verify: `wxcli devices list --mac <MAC> -o json` — correct owner, `devices_deleted.csv` appended.
