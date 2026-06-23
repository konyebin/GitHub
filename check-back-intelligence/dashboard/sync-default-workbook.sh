#!/usr/bin/env bash
# Copy the canonical Check Back workbook into dashboard/check_back_default.xlsx for auto-load.
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
SRC="${CHECK_BACK_XLSX:-$ROOT/output/Check_Back_standardized.xlsx}"
DEST="check_back_default.xlsx"

if [ ! -f "$SRC" ]; then
  echo "Baseline workbook not found: $SRC" >&2
  echo "Expected: output/Check_Back_standardized.xlsx (or set CHECK_BACK_XLSX)" >&2
  exit 1
fi

cp -f "$SRC" "$DEST"
echo "Synced baseline → $DEST"
echo "  from: $SRC"
echo "  size: $(wc -c < "$DEST" | tr -d ' ') bytes"
