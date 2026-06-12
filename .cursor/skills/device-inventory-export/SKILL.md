---
name: device-inventory-export
description: |
  Export org device inventory to CSV (phone type, MAC, org, status, owner). Use when
  moving devices between orgs, auditing phones, or building a MAC transfer list.
---

# Device Inventory Export

## Output file

Default: `~/Documents/GitHub/devices_org_inventory.csv`

Columns: `phone type`, `mac address`, `org`, `status`, `owner email`, `owner type`

## Run

```bash
~/Documents/GitHub/.cursor/skills/device-inventory-export/scripts/export-devices-csv.sh
# Or custom path:
~/Documents/GitHub/.cursor/skills/device-inventory-export/scripts/export-devices-csv.sh /path/to/out.csv
```

Uses `wxcli devices list -o json` and `wxcli people me -o json` for org name. Skips rows without MAC.

## When user adds a device manually

Append one line to the CSV after provisioning:

```csv
Cisco 8851,d0ec35500e68,CC Bootcamp Sandbox ccbcamp0093.wbx.ai,connected,admin+1@...,person
```

## Reference

Lab inventory also tracked in `wxops-session-context.md` and `devices_deleted.csv` for deletes.
