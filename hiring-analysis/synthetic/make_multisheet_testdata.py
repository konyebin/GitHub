"""Build un-redacted, multi-sheet TEST workbooks for exercising the PII redactor.

Everything is fictional. The score workbook is derived from FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx (the
candidate-tracker sample, one `TEMPLATE` sheet) by splitting its candidates into one sheet per assessment
center day. Two weeks of three AC days each gives six sheets named like `AMER Oct 15`. The screening
workbook stays a single sheet.

Outputs (hiring-analysis/testdata/, tracked because it holds only fake names):
  FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx          6 AC day sheets, source layout minus the Salutation column
  ASE_Candidate_Screen_Review_TEST_DATA.xlsx     1 sheet, headers/styles from synthetic/screen_template.xlsx (the real layout) plus Country

Run: python hiring-analysis/synthetic/make_multisheet_testdata.py --source path/to/FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx
Requires: openpyxl
"""

from __future__ import annotations

import argparse
import random
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
import openpyxl.utils

import screen_layout

OUT = Path(__file__).resolve().parents[1] / "testdata"
HEADER_ROW, FIRST_ROW = 9, 11


def ac_day_sheet_names(rng: random.Random, first_monday: date, region: str = "AMER") -> list[str]:
    days = []
    for week in range(2):
        monday = first_monday + timedelta(weeks=week)
        picked = sorted(rng.sample(range(5), 3))
        days += [monday + timedelta(days=d) for d in picked]
    return [f"{region} {d.strftime('%b')} {d.day}" for d in days]


def shift_row(value, old: int, new: int):
    if isinstance(value, str) and value.startswith("="):
        return re.sub(rf"(?<![0-9])([A-Z]{{1,2}}){old}(?![0-9])", rf"\g<1>{new}", value)
    return value


def drop_column(ws, col: int) -> None:
    """Delete a column and shift formula references, widths, freeze panes and the filter range left."""
    from openpyxl.utils import get_column_letter as L

    ref = re.compile(r"(^|[^A-Za-z0-9_])(\$?)([A-Z]{1,2})(\$?[0-9]+)(?![0-9(])")

    def fix(v):
        if isinstance(v, str) and v.startswith("="):
            return ref.sub(lambda m: m.group(1) + m.group(2) + (L(openpyxl.utils.column_index_from_string(m.group(3)) - 1)
                           if openpyxl.utils.column_index_from_string(m.group(3)) > col else m.group(3)) + m.group(4), v)
        return v

    widths = {k: d.width for k, d in ws.column_dimensions.items() if d.width}
    ws.delete_cols(col)
    for row in ws.iter_rows():
        for c in row:
            c.value = fix(c.value)
    for k, w in widths.items():
        idx = openpyxl.utils.column_index_from_string(k)
        if idx > col:
            ws.column_dimensions[L(idx - 1)].width = w
    if ws.freeze_panes:
        m = re.match(r"([A-Z]+)(\d+)", ws.freeze_panes)
        ws.freeze_panes = f"{L(openpyxl.utils.column_index_from_string(m.group(1)) - 1)}{m.group(2)}"
    ws.auto_filter.ref = f"A{HEADER_ROW}:{L(ws.max_column)}{HEADER_ROW}"


def build_scores(source: Path, sheets: list[str], out: Path) -> dict[str, int]:
    wb = openpyxl.load_workbook(source)
    template = wb.active
    last = max(r for r in range(FIRST_ROW, template.max_row + 1) if template.cell(r, 3).value)
    people = [[c.value for c in template[r]] for r in range(FIRST_ROW, last + 1)]

    base, extra = divmod(len(people), len(sheets))
    sizes = [base + (1 if i < extra else 0) for i in range(len(sheets))]
    counts: dict[str, int] = {}
    start = 0
    for name, size in zip(sheets, sizes):
        ws = wb.copy_worksheet(template)
        ws.title = name
        ws.freeze_panes = template.freeze_panes
        ws.auto_filter.ref = template.auto_filter.ref
        for r in range(FIRST_ROW, ws.max_row + 1):
            for c in ws[r]:
                c.value = None
        for offset, row in enumerate(people[start:start + size]):
            new_r = FIRST_ROW + offset
            old_r = FIRST_ROW + start + offset
            for col, v in enumerate(row, 1):
                ws.cell(new_r, col).value = shift_row(v, old_r, new_r)
        counts[name] = size
        start += size
    wb.remove(template)
    for ws in wb.worksheets:
        col = next(c.column for c in ws[HEADER_ROW] if isinstance(c.value, str) and c.value.strip().lower() == "salutation")
        drop_column(ws, col)
    wb.save(out)
    return counts


def build_screen(names_by_sheet: dict[str, list[str]], out: Path, rng: random.Random) -> None:
    cities = [("Seattle, WA", "USA"), ("Austin, TX", "USA"), ("Raleigh, NC", "USA"), ("Denver, CO", "USA"),
              ("Chicago, IL", "USA"), ("Toronto, ON, Canada", "CAN"), ("Mexico City, Mexico", "MEX")]
    skills = ["CCNA; Troubleshooting and root-cause analysis", "CompTIA A+; Active Directory", "Security+; Networking; Help desk",
              "CCNA (in progress); Python, Bash", "Cisco Networking Academy: CCNA; Linux"]
    recruiters = ["Marcus Bell", "Priya Natarajan", "Dana Whitfield"]
    advance = "Interview Schedule Sent and Candidate Confirmed Attendance/Receipt of Prep Materials"
    rows = []
    pid = 1042100

    def person(name: str, passed: bool) -> dict:
        nonlocal pid
        pid += rng.randint(3, 40)
        city, country = rng.choice(cities)
        first, last = name.lower().split()[0], name.lower().split()[-1]
        return {"id": pid, "name": name, "graduation": f"May 202{rng.choice([4, 5, 6])}", "skills": rng.choice(skills),
                "city": city, "country": country, "recruiter": rng.choice(recruiters),
                "ti_date": datetime(2026, 9, rng.randint(1, 26)), "confirmed": "Yes",
                "score": rng.randint(21, 31) if passed else rng.randint(10, 20),
                "comments": "No flags" if passed else "Needs follow-up on networking basics",
                "passfail": "Pass" if passed else "Fail",
                "notes": (f"{name} described a help desk escalation clearly and asked good questions about the role. "
                          "Language level: English (native).") if passed else
                         f"{name} struggled to go deeper than the first layer of the technology. Language level: English (native).",
                "recommended": "Yes" if passed else "No",
                "status": advance if passed else "Not moving forward after technical interview",
                "slot": f"Oct {rng.randint(5, 16)} - Slot {rng.randint(1, 8)}" if passed else "N/A",
                "invite": passed, "sharepoint": passed, "email": f"{first}.{last}@example.com"}

    for names in names_by_sheet.values():
        rows += [person(name, True) for name in names]
    rows += [person(rng.choice(["Blair Kent", "Dana Moss", "Eli Park", "Frankie Dunn", "Gray Holt", "Harper Lane"]), False)
             for _ in range(6)]
    screen_layout.new_workbook(rows).save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=15)
    ap.add_argument("--first-monday", default="2026-10-05")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    OUT.mkdir(exist_ok=True)

    sheets = ac_day_sheet_names(rng, date.fromisoformat(a.first_monday))
    scores_out = OUT / "FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx"
    counts = build_scores(a.source, sheets, scores_out)

    wb = openpyxl.load_workbook(scores_out)
    names = {ws.title: [ws.cell(r, 2).value for r in range(FIRST_ROW, ws.max_row + 1) if ws.cell(r, 2).value]
             for ws in wb}
    build_screen(names, OUT / "ASE_Candidate_Screen_Review_TEST_DATA.xlsx", rng)
    print(scores_out, counts)


if __name__ == "__main__":
    main()
