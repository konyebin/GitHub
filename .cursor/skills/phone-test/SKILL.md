---
name: phone-test
description: Run phone-to-phone call loop (admin 8845 ↔ User 10 9851) with count and delay
disable-model-invocation: true
---

# Phone test

Run the camp0093 desk-phone loop. **Not WebRTC** — physical phones only.

## Parse user args

From the prompt after `/phone-test`:

- **count** — iterations (default `5`)
- **delay** — seconds connected before hangup (default `5`)
- **reverse** — if user says reverse / User 10 calls admin, add `--reverse`

## Steps

1. Read `.cursor/wxops-session-context.md` and `wxops/.claude/skills/phone-to-phone-calls/SKILL.md`.
2. Preflight: `wxcli devices list -o json` — confirm admin 8845 and User 10 9851 are `connected`.
3. Run:

```bash
cd ~/Documents/GitHub/wxops
.venv/bin/python .claude/skills/phone-to-phone-calls/scripts/phone-call-loop.py --count <N> --delay <SEC> [--reverse]
```

4. Report success count and exit code. If not all succeeded, do not claim done — run wxops-verification skill checks.
