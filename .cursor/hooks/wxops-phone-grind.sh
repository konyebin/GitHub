#!/usr/bin/env bash
# stop hook: continue wxops phone-test grind until scratchpad contains DONE or max iterations.
set -euo pipefail

input=$(cat)
status=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
loop_count=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d.get('loop_count',0)))" 2>/dev/null || echo "0")

MAX_ITERATIONS=5
SCRATCHPAD=".cursor/scratchpad-wxops-phone.md"

if [[ "$status" != "completed" ]] || [[ "$loop_count" -ge "$MAX_ITERATIONS" ]]; then
  echo '{}'
  exit 0
fi

if [[ ! -f "$SCRATCHPAD" ]]; then
  echo '{}'
  exit 0
fi

if grep -q 'DONE' "$SCRATCHPAD" 2>/dev/null; then
  echo '{}'
  exit 0
fi

target=$(grep -E '^target:' "$SCRATCHPAD" 2>/dev/null | head -1 | cut -d: -f2- | xargs || echo "5")
delay=$(grep -E '^delay:' "$SCRATCHPAD" 2>/dev/null | head -1 | cut -d: -f2- | xargs || echo "5")

python3 -c "
import json
n = int('${loop_count}') + 1
m = int('${MAX_ITERATIONS}')
print(json.dumps({
  'followup_message': f'[Phone grind {n}/{m}] Run phone-call-loop.py --count {target} --delay {delay}. Update ${SCRATCHPAD} with DONE when all iterations succeed.'
}))
"
