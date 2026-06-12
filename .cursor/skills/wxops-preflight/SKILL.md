---
name: wxops-preflight
description: |
  Parallel preflight before wxops phone/device/call tasks. Use with /multitask or
  "build in parallel" for independent read-only checks. Pair with /worktree for
  overlapping file edits.
---

# wxops Preflight (parallel)

Use **`/multitask`** in the Agents Window for independent checks. Do **not** parallelize steps with data dependencies (e.g. reassign phone then call — sequential).

## Standard preflight (fan-out)

Ask:

```
/multitask:
1. wxcli devices list -o json — summarize connected phones and owners
2. wxcli people me -o json — confirm token user email
3. Run ~/Documents/GitHub/wxops/scripts/verify-mcp-stdio.sh
```

## Before phone loop

```
/multitask:
1. devices list — admin 8845 + User 10 9851 connected?
2. call-controls list-calls for admin and User 10 — any stuck calls?
3. verify-mcp-stdio.sh
```

## Before device reassign

```
/multitask:
1. devices list --mac <MAC> -o json — full record capture
2. people list --email <target> -o json — target has calling license
3. Tail devices_deleted.csv last 3 rows — audit continuity
```

## Disconnected desk phone (roomos + wxops)

```
/multitask:
1. wxops: wxcli devices list --mac <MAC> -o json
2. wxops: wxcli device-settings list <callingDeviceId> -o json
3. Plan roomos xAPI status query if device ID known (roomos MCP)
```

Synthesize one diagnosis plan before edits.

## /worktree + /multitask

When parallel agents **edit the same files** (e.g. multiple location call queues in one JSON config):

1. `/worktree` — isolate branches per task
2. `/multitask` — implement independent location configs
3. Merge worktrees manually or via agent merge step

Read-only fan-out: `/multitask` alone is enough.

## Build in parallel from Plan Mode

On an approved plan with independent steps: click **Build in Parallel** (or ask agent to multitask plan steps that do not depend on each other).
