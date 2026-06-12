---
name: phone-to-phone-calls
description: |
  Run desk-phone call loops in camp0093 (admin 8845 ↔ User 10 9851) via Members API.
  Use for ring two phones, repeat call cycles, admin↔User 10 tests. Not WebRTC.
---

# Phone-to-Phone Calls (Cursor)

**Canonical skill:** [`wxops/.claude/skills/phone-to-phone-calls/SKILL.md`](~/Documents/GitHub/wxops/.claude/skills/phone-to-phone-calls/SKILL.md)

Read that file + `call-control` skill before acting. Prerequisites: wxops bootstrap rule, session context.

## Quick run

```bash
cd ~/Documents/GitHub/wxops
.venv/bin/python .claude/skills/phone-to-phone-calls/scripts/phone-call-loop.py --count 5 --delay 5
.venv/bin/python .claude/skills/phone-to-phone-calls/scripts/phone-call-loop.py --count 5 --reverse
```

Round-robin / rotating phone: see canonical skill § Round-robin caller.

## Verify before and after

Use `.cursor/skills/wxops-verification/SKILL.md` — both phones must be `connected`.
