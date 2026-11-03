"""The screening test workbook follows the layout copied from the real workbook, plus a Country column."""
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


def make_real(path: Path, headers, header_row=3, sheet="Review"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.cell(1, 1, "Candidate Screen Review - Updated 9.28")
    for i, h in enumerate(headers, 1):
        ws.cell(header_row, i, h)
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 11 + i
    ws.cell(header_row + 1, 1, "REAL PERSON ID 999")
    ws.freeze_panes = f"C{header_row + 1}"
    wb.save(path)


def test_layout_read_is_header_only(tmp_path):
    src = tmp_path / "real.xlsx"
    make_real(src, ["Person ID", "Name", "Home city", "Recruiter", "Score", "Status"])
    lay = sl.read_layout_from(src)
    assert lay["sheet_name"] == "Review" and lay["header_row"] == 3
    assert lay["headers"] == ["Person ID", "Name", "Home city", "Recruiter", "Score", "Status"]
    assert "REAL PERSON ID" not in str(lay)


def test_country_added_once_after_city():
    lay = sl.with_country({"headers": ["Person ID", "Home city", "Recruiter"], "widths": {}, "header_row": 1})
    assert lay["headers"] == ["Person ID", "Home city", "Country", "Recruiter"]
    assert sl.with_country(lay)["headers"] == lay["headers"]


def test_written_sheet_matches_layout_exactly(tmp_path, monkeypatch):
    import make_multisheet_testdata as mk
    src = tmp_path / "real.xlsx"
    make_real(src, ["Person ID", "Name", "Home city", "Recruiter", "Score", "Pass/Fail", "Notes", "Status", "Extra thing"])
    lay = sl.read_layout_from(src)
    lay_path = tmp_path / "layout.json"
    lay_path.write_text(__import__("json").dumps(lay))
    monkeypatch.setattr(sl, "LAYOUT_PATH", lay_path)
    out = tmp_path / "screen.xlsx"
    mk.build_screen({"AMER Oct 15": ["Ann Lee", "Bo Chan"]}, out, random.Random(1))
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Review"]
    ws = wb["Review"]
    headers = [c.value for c in ws[3] if c.value]
    assert headers == ["Person ID", "Name", "Home city", "Country", "Recruiter", "Score", "Pass/Fail", "Notes", "Status", "Extra thing"]
    assert ws.freeze_panes == "C4"
    assert all(ws.cell(r, 1).value for r in range(4, 4 + 8))

    warnings: list = []
    df = loader.load_screen(out, warnings)
    assert len(df) == 8 and df["candidate_id"].str.startswith("1042").all()
    assert df["screen_score"].notna().all()
    assert any("no column for" in w for w in warnings), "missing optional columns are reported, not fatal"


def test_default_testdata_has_only_known_columns_plus_country():
    wb = openpyxl.load_workbook(ROOT / "testdata" / "ASE_Candidate_Screen_Review_TEST_DATA.xlsx")
    ws = wb.worksheets[0]
    headers = [c.value for c in ws[1]]
    expected = sl.with_country(sl.load_layout())["headers"]
    assert headers == expected
    assert "Country" in headers
