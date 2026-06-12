#!/usr/bin/env bash
# Export Webex org devices to CSV for inventory / cross-org moves.
set -euo pipefail

OUT="${1:-$HOME/Documents/GitHub/devices_org_inventory.csv}"
WXCLI="$HOME/Documents/GitHub/wxops/.venv/bin/wxcli"

if [[ ! -x "$WXCLI" ]]; then
  echo "Missing wxcli at $WXCLI" >&2
  exit 1
fi

export OUT WXCLI
python3 <<'PY'
import csv
import json
import os
import subprocess
import sys

out_path = os.environ["OUT"]
wxcli = os.environ["WXCLI"]

def run(args):
    r = subprocess.run([wxcli, *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        sys.exit(r.returncode)
    return json.loads(r.stdout)

org_name = ""
try:
    me = run(["people", "me", "-o", "json"])
    org_name = (me.get("orgName") or me.get("organizationName") or "").strip()
except Exception:
    pass

devices = run(["devices", "list", "-o", "json"])
if isinstance(devices, dict):
    devices = devices.get("items", devices.get("devices", []))

rows = []
for d in devices:
    mac = (d.get("mac") or "").replace(":", "").upper()
    if not mac or len(mac) != 12:
        continue
    product = d.get("product") or d.get("model") or "unknown"
    status = d.get("connectionStatus") or "unknown"
    owner_email = ""
    owner_type = ""
    if d.get("personId"):
        owner_type = "person"
        owner_email = d.get("personEmail") or ""
    elif d.get("workspaceId"):
        owner_type = "workspace"
        owner_email = d.get("workspaceDisplayName") or d.get("displayName") or ""
    rows.append([product, mac, org_name, status, owner_email, owner_type])

rows.sort(key=lambda r: r[1])

with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["phone type", "mac address", "org", "status", "owner email", "owner type"])
    w.writerows(rows)

print(f"Wrote {len(rows)} devices to {out_path}")
PY
