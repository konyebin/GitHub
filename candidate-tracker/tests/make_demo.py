"""Build samples/demo_candidates.xlsx (fictional people) from the blank template."""

import random
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
wb = openpyxl.load_workbook(ROOT / "samples" / "FY27Q3_AMER_ASE_Scores_template.xlsx")
ws = wb.active
header = 9
people = [
    ("USA", "Avery Stone"), ("USA", "Jordan Blake"), ("CAN", "Morgan Ellis"), ("USA", "Riley Chen"),
    ("MEX", "Sam Ortega"), ("BRA", "Taylor Nunes"), ("USA", "Casey Brooks"), ("CAN", "Drew Patel"),
    ("USA", "Quinn Harper"), ("COL", "Reese Duarte"), ("USA", "Skyler Moon"), ("CAN", "Parker Lowe"),
    ("USA", "Jamie Fox"), ("ARG", "Alex Rivera"),
]
random.seed(7)
for i, (country, name) in enumerate(people, start=header + 2):
    ws.cell(i, 1, country)
    ws.cell(i, 2, "Mx.")
    ws.cell(i, 3, name)
    base = random.choice([2, 3, 3, 3, 4, 4])
    for first in (4, 11, 18):
        for k in range(4):
            if i == header + 15 and first == 18:
                continue
            ws.cell(i, first + k, max(1, min(4, base + random.choice([-1, 0, 0, 1]))))
    ws.cell(i, 10, "Strong communicator" if base == 4 else "")
    ws.cell(i, 28, "A. Buddy" if base == 4 else "")
wb.save(ROOT / "samples" / "demo_candidates.xlsx")
print("written")
