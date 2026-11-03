"""Screening workbook ("ASE Candidate Screen Review") template shared by every test-file generator.

`screen_template.xlsx` is a header-only copy of the real workbook: sheet name, header row, header text and order,
column widths, header and cell styles, freeze panes and filter are kept; every data value is removed. All generators
(`make_synthetic.py`, `make_multisheet_testdata.py`) load it, add a `Country` column after "Home cities", and fill
rows with fictional values, so their screening workbooks look exactly like the real one plus Country.

To refresh the template from a newer copy of the real workbook:
  python hiring-analysis/synthetic/screen_layout.py --source "<path to the workbook>"
  python hiring-analysis/synthetic/screen_layout.py --show

Requires: openpyxl
"""

from __future__ import annotations

import argparse
import re
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter as L

TEMPLATE = Path(__file__).with_name("screen_template.xlsx")
COUNTRY = "Country"
COUNTRY_WIDTH = 16
HEADER_PAT = re.compile(r"\s*(person\s*id|full\s*name)\s*$", re.I)

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
    ("slot", r"assessment\s*center\s*slot"),
    ("invite", r"phenom"),
    ("sharepoint", r"resume\s*added"),
    ("email", r"e-?mail"),
]


def field_of(header) -> str | None:
    h = str(header or "").strip().lower()
    for field, pat in FIELDS:
        if re.match(pat, h):
            return field
    return None


def header_row_of(ws, max_rows: int = 30) -> int:
    for r in range(1, min(ws.max_row, max_rows) + 1):
        if any(isinstance(c.value, str) and HEADER_PAT.match(c.value) for c in ws[r]):
            return r
    raise SystemExit(f"no 'Person ID' or 'Full name' header found in the first {max_rows} rows of sheet {ws.title!r}")


def make_template(source: Path, out: Path = TEMPLATE) -> Path:
    """Header-only copy of the real workbook's first sheet: styles stay, every data value goes."""
    wb = openpyxl.load_workbook(Path(source).expanduser())
    ws = wb.worksheets[0]
    for other in wb.worksheets[1:]:
        wb.remove(other)
    hr = header_row_of(ws)
    last = max(c.column for c in ws[hr] if c.value not in (None, ""))
    for r in range(hr + 1, ws.max_row + 1):
        for c in ws[r]:
            c.value = None
    if ws.max_row > hr + 1:
        ws.delete_rows(hr + 2, ws.max_row - hr - 1)
    if ws.max_column > last:
        ws.delete_cols(last + 1, ws.max_column - last)
    for k in [k for k in ws.column_dimensions if openpyxl.utils.column_index_from_string(k) > last]:
        del ws.column_dimensions[k]
    wb.save(out)
    return out


def layout_of(ws) -> dict:
    hr = header_row_of(ws)
    headers = [str(c.value) for c in ws[hr] if c.value not in (None, "")]
    return {"sheet_name": ws.title, "header_row": hr, "headers": headers,
            "freeze_panes": ws.freeze_panes, "filter": ws.auto_filter.ref}


def _add_country(ws, hr: int) -> None:
    headers = [c.value for c in ws[hr]]
    if any(field_of(h) == "country" for h in headers):
        return
    at = next((i + 1 for i, h in enumerate(headers, 0) if field_of(h) == "city"), len([h for h in headers if h])) + 1
    widths = {openpyxl.utils.column_index_from_string(k): d.width for k, d in ws.column_dimensions.items() if d.width}
    ws.insert_cols(at)
    for k in list(ws.column_dimensions):
        del ws.column_dimensions[k]
    for idx, w in widths.items():
        ws.column_dimensions[L(idx + 1 if idx >= at else idx)].width = w
    ws.column_dimensions[L(at)].width = COUNTRY_WIDTH
    model = at - 1
    for r in range(1, ws.max_row + 1):
        ws.cell(r, at)._style = copy(ws.cell(r, model)._style)
    ws.cell(hr, at, COUNTRY)
    if ws.freeze_panes:
        m = re.match(r"([A-Z]+)(\d+)", ws.freeze_panes)
        idx = openpyxl.utils.column_index_from_string(m.group(1))
        if idx > at:
            ws.freeze_panes = f"{L(idx + 1)}{m.group(2)}"
    if ws.auto_filter.ref:
        ws.auto_filter.ref = f"A{hr}:{L(ws.max_column)}{hr}"


def new_workbook(rows: list[dict], identify_by_id: bool = False, template: Path | None = None) -> openpyxl.Workbook:
    """Template plus Country, filled with rows keyed by field name (id, name, country, city, score, ...).

    The real workbook has no Person ID column, so the person is identified by Full name. With `identify_by_id`
    the Full name cell holds the row's id (candidateN), which is what the redactor leaves behind.
    """
    wb = openpyxl.load_workbook(template or TEMPLATE)
    ws = wb.worksheets[0]
    hr = header_row_of(ws)
    _add_country(ws, hr)
    headers = [c.value for c in ws[hr]]
    has_id = any(field_of(h) == "id" for h in headers)
    sample = {c: copy(ws.cell(hr + 1, c)._style) for c in range(1, len(headers) + 1)}
    for i, row in enumerate(rows, hr + 1):
        row = dict(row)
        if identify_by_id and not has_id:
            row["name"] = row["id"]
        for col, h in enumerate(headers, 1):
            f = field_of(h)
            if not h:
                continue
            cell = ws.cell(i, col, row.get(f, "Sample") if f else "Sample")
            cell._style = copy(sample[col])
    return wb


def describe(ws) -> str:
    lay = layout_of(ws)
    lines = [f"sheet {lay['sheet_name']!r}, header on row {lay['header_row']}, {len(lay['headers'])} columns, "
             f"freeze {lay['freeze_panes']}, filter {lay['filter']}"]
    lines += [f"  {L(i)}: {h!r} -> {field_of(h) or 'UNMAPPED'}" for i, h in enumerate(lay["headers"], 1)]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, help="the real screening workbook (data values are not kept)")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if a.source:
        make_template(a.source)
        print("Saved", TEMPLATE)
    ws = new_workbook([]).worksheets[0]
    print(describe(ws))
    bad = [h for h in layout_of(ws)["headers"] if field_of(h) is None]
    if bad:
        print("Headers the generators fill with 'Sample':", bad)


if __name__ == "__main__":
    main()
