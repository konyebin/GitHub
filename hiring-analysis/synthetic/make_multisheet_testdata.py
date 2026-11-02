"""Build un-redacted, multi-sheet TEST workbooks for exercising the PII redactor.

Everything is fictional. The score workbook is derived from FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx (the
candidate-tracker sample, one `TEMPLATE` sheet) by splitting its candidates into one sheet per assessment
center day. Two weeks of three AC days each gives six sheets named like `AMER Oct 15`. The screening
workbook stays a single sheet.

Outputs (hiring-analysis/testdata/, tracked because it holds only fake names):
  FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx          6 cohort sheets, same layout as the source on every sheet
  ASE_Candidate_Screen_Review_TEST_DATA.xlsx     1 sheet, columns as in the real screening workbook

Run: python hiring-analysis/synthetic/make_multisheet_testdata.py --source path/to/FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx
Requires: openpyxl
"""

from __future__ import annotations

import argparse
import random
import re
from datetime import date, timedelta
from pathlib import Path

import openpyxl

OUT = Path(__file__).resolve().parents[1] / "testdata"
HEADER_ROW, FIRST_ROW = 9, 11


def cohort_sheet_names(rng: random.Random, first_monday: date, region: str = "AMER") -> list[str]:
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
    wb.save(out)
    return counts


def build_screen(names_by_sheet: dict[str, list[str]], out: Path, rng: random.Random) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Screen"
    ws.append(["Person ID", "Full name", "Graduation Date or Expected Graduation Date", "Skills and Technologies",
               "Home cities", "Recruiter", "TI Date", "Confirmed Yes/No", "Score (Passing Score 21)",
               "Additional Comments", "Pass/Fail", "Notes (Summary of the TI call)",
               "Recommended to be Invited to Insight Day Yes/No", "Status"])
    cities = ["Seattle, WA", "Austin, TX", "Raleigh, NC", "Denver, CO", "Chicago, IL", "Toronto, ON", "Mexico City, MX"]
    skills = ["Former Intern", "Holds CCNA", "Studying for AWS", "Bachelor Computer Science", "Experience: help desk"]
    recruiters = ["Pat Morales", "Lee Brandt"]
    pid = 1042100
    for sheet, names in names_by_sheet.items():
        for name in names:
            pid += rng.randint(3, 40)
            score = rng.randint(21, 31)
            ws.append([pid, name, f"May 202{rng.choice([5, 6])}", rng.choice(skills), rng.choice(cities),
                       rng.choice(recruiters), f"Sep {rng.randint(8, 26)}, 2026", "Yes", score, "No flags", "Pass",
                       f"{name} described a help desk escalation clearly and asked good questions about the role.",
                       "Yes", "Sent Assessment Center Instructions and Candidate Confirmed Availability"])
    for _ in range(6):
        pid += rng.randint(3, 40)
        name = rng.choice(["Blair Kent", "Dana Moss", "Eli Park", "Frankie Dunn", "Gray Holt", "Harper Lane"]) + ""
        score = rng.randint(10, 20)
        ws.append([pid, name, "May 2026", rng.choice(skills), rng.choice(cities), rng.choice(recruiters),
                   f"Sep {rng.randint(8, 26)}, 2026", "Yes", score, "Needs follow-up on networking basics", "Fail",
                   f"{name} struggled to go deeper than the first layer of the technology.", "No",
                   "Did not advance after TI"])
    wb.save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=15)
    ap.add_argument("--first-monday", default="2026-10-05")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    OUT.mkdir(exist_ok=True)

    sheets = cohort_sheet_names(rng, date.fromisoformat(a.first_monday))
    scores_out = OUT / "FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx"
    counts = build_scores(a.source, sheets, scores_out)

    wb = openpyxl.load_workbook(scores_out)
    names = {ws.title: [ws.cell(r, 3).value for r in range(FIRST_ROW, ws.max_row + 1) if ws.cell(r, 3).value]
             for ws in wb}
    build_screen(names, OUT / "ASE_Candidate_Screen_Review_TEST_DATA.xlsx", rng)
    print(scores_out, counts)


if __name__ == "__main__":
    main()
