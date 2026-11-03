"""Layout of the screening workbook ("ASE Candidate Screen Review"), shared by every test-file generator.

The real workbook lives on the creator's Mac, so the generators cannot read it directly. Run this file once
with `--source` pointing at the real workbook. It copies only the layout (sheet name, header row, header text
and order, column widths, freeze panes, filter row). No data rows or cell values below the header are read,
so no personal data leaves the machine. The layout is saved to `screen_layout.json`, and every generator
(`make_synthetic.py`, `make_multisheet_testdata.py`) then writes workbooks with exactly those headers plus a
`Country` column.

  python hiring-analysis/synthetic/screen_layout.py --source "~/Downloads/ASE Candidate Screen Review - Updated 9.28 (1).xlsx"
  python hiring-analysis/synthetic/screen_layout.py --show

Requires: openpyxl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

LAYOUT_PATH = Path(__file__).with_name("screen_layout.json")

DEFAULT = {
    "sheet_name": "Screen",
    "header_row": 1,
    "headers": ["Person ID", "Full name", "Graduation Date or Expected Graduation Date", "Skills and Technologies",
                "Home cities", "Recruiter", "TI Date", "Confirmed Yes/No", "Score (Passing Score 21)",
                "Additional Comments", "Pass/Fail", "Notes (Summary of the TI call)",
                "Recommended to be Invited to Insight Day Yes/No", "Status"],
    "widths": {},
    "freeze_panes": None,
    "filter": False,
    "verified_against_real_file": False,
}

COUNTRY = "Country"
COUNTRY_AFTER = "Home cities"

FIELDS = [
    ("id", r"person\s*id"),
    ("country", r"country"),
    ("name", r"(full|candidate)?\s*name"),
    ("graduation", r"graduation"),
    ("skills", r"skills"),
    ("city", r"home\s*cit"),
    ("recruiter", r"recruiter"),
    ("ti_date", r"ti\s*date"),
    ("confirmed", r"confirmed"),
    ("score", r"score"),
    ("comments", r"additional\s*comments"),
    ("passfail", r"pass\s*/?\s*fail"),
    ("notes", r"notes"),
    ("recommended", r"recommended"),
    ("status", r"status"),
]


def field_of(header: str) -> str | None:
    h = str(header).strip().lower()
    for field, pat in FIELDS:
        if re.match(pat, h):
            return field
    return None


def load_layout() -> dict:
    if LAYOUT_PATH.exists():
        return {**DEFAULT, **json.loads(LAYOUT_PATH.read_text())}
    return dict(DEFAULT)


def with_country(layout: dict) -> dict:
    """Return the layout with a Country column added after "Home cities" (or at the end) unless one exists."""
    headers = list(layout["headers"])
    if any(field_of(h) == "country" for h in headers):
        return {**layout, "headers": headers}
    at = next((i + 1 for i, h in enumerate(headers) if field_of(h) == "city"), len(headers))
    headers.insert(at, COUNTRY)
    widths = {}
    for k, w in layout.get("widths", {}).items():
        idx = openpyxl.utils.column_index_from_string(k)
        widths[get_column_letter(idx + 1) if idx > at else k] = w
    return {**layout, "headers": headers, "widths": widths}


def read_layout_from(path: Path) -> dict:
    """Header-only read of the real workbook: first sheet, the row holding "Person ID", nothing below it."""
    wb = openpyxl.load_workbook(Path(path).expanduser(), read_only=False)
    ws = wb.worksheets[0]
    header_row = next((r for r in range(1, min(ws.max_row, 30) + 1)
                       if any(isinstance(c.value, str) and re.match(r"\s*person\s*id", c.value, re.I) for c in ws[r])), None)
    if header_row is None:
        raise SystemExit(f"no 'Person ID' header found in the first 30 rows of sheet {ws.title!r}")
    cells = list(ws[header_row])
    last = max(c.column for c in cells if c.value not in (None, ""))
    headers = [str(c.value) if c.value is not None else "" for c in cells[:last]]
    widths = {k: d.width for k, d in ws.column_dimensions.items() if d.width}
    return {"sheet_name": ws.title, "header_row": header_row, "headers": headers, "widths": widths,
            "freeze_panes": ws.freeze_panes, "filter": bool(ws.auto_filter.ref),
            "other_sheets": [s.title for s in wb.worksheets[1:]], "verified_against_real_file": True}


def unmapped(layout: dict) -> list[str]:
    return [h for h in layout["headers"] if h and field_of(h) is None]


def write_screen_sheet(ws, layout: dict, rows: list[dict]) -> None:
    """Write headers and rows; each row is a dict keyed by field name (id, name, country, ...)."""
    layout = with_country(layout)
    hr = layout["header_row"]
    for col, h in enumerate(layout["headers"], 1):
        ws.cell(hr, col, h or None)
    for i, row in enumerate(rows, hr + 1):
        for col, h in enumerate(layout["headers"], 1):
            f = field_of(h)
            ws.cell(i, col, row.get(f, "Sample") if f else "Sample")
    for k, w in layout.get("widths", {}).items():
        ws.column_dimensions[k].width = w
    if layout.get("freeze_panes"):
        ws.freeze_panes = layout["freeze_panes"]
    if layout.get("filter"):
        ws.auto_filter.ref = f"A{hr}:{get_column_letter(len(layout['headers']))}{hr}"


def describe(layout: dict) -> str:
    lines = [f"sheet {layout['sheet_name']!r}, header on row {layout['header_row']}, "
             f"{len(layout['headers'])} columns"]
    lines += [f"  {get_column_letter(i)}: {h!r}  -> {field_of(h) or 'UNMAPPED'}" for i, h in enumerate(layout["headers"], 1)]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, help="the real screening workbook (only its header row is read)")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if a.show or not a.source:
        print(describe(with_country(load_layout())))
        return
    old = load_layout()
    new = read_layout_from(a.source)
    LAYOUT_PATH.write_text(json.dumps(new, indent=2))
    print("Saved", LAYOUT_PATH)
    print(describe(new))
    gone = [h for h in old["headers"] if h not in new["headers"]]
    added = [h for h in new["headers"] if h not in old["headers"]]
    print("\nColumns the old test workbook had that the real one does not:", gone or "none")
    print("Columns the real workbook has that the old test workbook did not:", added or "none")
    if unmapped(new):
        print("Headers the loader does not know yet (written as 'Sample'):", unmapped(new))
    print("\nNow regenerate the test files:\n  python hiring-analysis/synthetic/make_multisheet_testdata.py --source <scores workbook>")


if __name__ == "__main__":
    main()
