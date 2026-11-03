"""The screening test workbook is the real workbook's layout (header-only template) plus a Country column."""
import random
import sys
from pathlib import Path

import openpyxl
import openpyxl.utils
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "synthetic"))
sys.path.insert(0, str(ROOT))

import screen_layout as sl  # noqa: E402
from pipeline import loader  # noqa: E402

REAL_HEADERS = ["Full name", "Graduation Date or Expected Graduation Date", "Skills and Technologies", "Home cities", "Recruiter",
                "TI Date", "Confirmed Yes/No", "Score (Passing Score 21)", "Additional Comments (anything flagged over the TI's)",
                "Pass/Fail", "Notes (Summary of the TI call, Language level etc.)",
                "Recommended to be Invited to Insight Day Yes/No", "Status", "Assessment Center Slot",
                "Phenom Calendar Invite Sent", "Resume Added to Sharepoint", "Email"]


def make_real(path: Path, headers, header_row=3, sheet="Review"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.cell(1, 1, "Candidate Screen Review - Updated 9.28")
    for i, h in enumerate(headers, 1):
        ws.cell(header_row, i, h).font = openpyxl.styles.Font(bold=True)
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 11 + i
    ws.cell(header_row + 1, 1, "REAL PERSON 999")
    ws.cell(header_row + 1, 4, "Real City")
    ws.freeze_panes = f"B{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{openpyxl.utils.get_column_letter(len(headers))}{header_row}"
    wb.save(path)


def test_template_keeps_layout_but_no_data(tmp_path):
    src = tmp_path / "real.xlsx"
    make_real(src, REAL_HEADERS)
    out = sl.make_template(src, tmp_path / "t.xlsx")
    ws = openpyxl.load_workbook(out).worksheets[0]
    assert ws.title == "Review" and sl.header_row_of(ws) == 3
    assert sl.layout_of(ws)["headers"] == REAL_HEADERS
    assert "REAL" not in str([[c.value for c in r] for r in ws.iter_rows(min_row=4)])


def test_country_added_after_city_with_widths_and_filter(tmp_path):
    src = tmp_path / "real.xlsx"
    make_real(src, REAL_HEADERS)
    t = sl.make_template(src, tmp_path / "t.xlsx")
    ws = sl.new_workbook([], template=t).worksheets[0]
    headers = sl.layout_of(ws)["headers"]
    assert headers == REAL_HEADERS[:4] + ["Country"] + REAL_HEADERS[4:]
    assert ws.column_dimensions["F"].width == 11 + 5, "Recruiter keeps its width after the shift"
    assert ws.auto_filter.ref == f"A3:{openpyxl.utils.get_column_letter(len(headers))}3"
    assert ws.freeze_panes == "B4"


def test_workbook_built_from_template_matches_and_loads(tmp_path, monkeypatch):
    import make_multisheet_testdata as mk
    src = tmp_path / "real.xlsx"
    make_real(src, REAL_HEADERS + ["Extra thing"])
    monkeypatch.setattr(sl, "TEMPLATE", sl.make_template(src, tmp_path / "t.xlsx"))
    out = tmp_path / "screen.xlsx"
    mk.build_screen({"AMER Oct 15": ["Ann Lee", "Bo Chan"]}, out, random.Random(1))
    ws = openpyxl.load_workbook(out)["Review"]
    headers = [c.value for c in ws[3] if c.value]
    assert headers == REAL_HEADERS[:4] + ["Country"] + REAL_HEADERS[4:] + ["Extra thing"]
    assert ws.cell(4, 1).value == "Ann Lee" and ws.cell(4, 5).value in {"USA", "CAN", "MEX"}

    warnings: list = []
    df = loader.load_screen(out, warnings)
    assert len(df) == 8 and set(df["candidate_id"][:2]) == {"Ann Lee", "Bo Chan"}
    assert df["screen_score"].notna().all()
    assert loader.workbook_kind(out) == "screen"


def test_synthetic_style_rows_use_candidate_number_as_id():
    wb = sl.new_workbook([{"id": "candidate7", "name": "x", "score": 25}], identify_by_id=True)
    ws = wb.worksheets[0]
    assert ws.cell(2, 1).value == "candidate7"


def test_shipped_template_and_testdata_follow_real_layout():
    ws = openpyxl.load_workbook(ROOT / "testdata" / "ASE_Candidate_Screen_Review_TEST_DATA.xlsx").worksheets[0]
    assert ws.title == "ASE Candidate Feedback"
    headers = [c.value for c in ws[1] if c.value]
    assert headers == REAL_HEADERS[:4] + ["Country"] + REAL_HEADERS[4:]
    assert ws.freeze_panes == "B1"
    assert "Person ID" not in headers
