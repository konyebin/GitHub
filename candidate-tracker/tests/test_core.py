from pathlib import Path

import openpyxl
import pandas as pd

from tracker_core import HIRE, NO_HIRE, STANDBY, UNASSIGNED, build_workbook, duplicate_numbers, parse_workbook, suggest

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_template_has_only_example_row():
    res = parse_workbook(SAMPLES / "FY27Q3_AMER_ASE_Scores_template.xlsx")
    assert res.df.empty and res.skipped_examples == 1
    with_examples = parse_workbook(SAMPLES / "FY27Q3_AMER_ASE_Scores_template.xlsx", include_examples=True)
    row = with_examples.df.iloc[0]
    assert row["Total"] == 48 and row["Overall %"] == 1.0


def test_demo_parse_and_scores():
    df = parse_workbook(SAMPLES / "demo_candidates.xlsx").df
    assert len(df) == 14
    assert (df["Interview"] <= 16).all()
    assert not df.iloc[-1]["Complete"]
    assert df["Complete"].iloc[:-1].all()


def test_suggest_thresholds():
    assert suggest(0.9, True, 0.85, 0.7) == HIRE
    assert suggest(0.75, True, 0.85, 0.7) == STANDBY
    assert suggest(0.5, True, 0.85, 0.7) == NO_HIRE
    assert suggest(0.9, False, 0.85, 0.7) == "Incomplete"


def test_duplicates_case_insensitive():
    assert duplicate_numbers({"a": "E1", "b": "e1", "c": "", "d": ""}) == {"e1": ["a", "b"]}


def test_export_colours_and_sheets(tmp_path):
    df = parse_workbook(SAMPLES / "demo_candidates.xlsx").df
    df["Status"] = [HIRE, STANDBY, NO_HIRE] + [UNASSIGNED] * (len(df) - 3)
    df["Employee #"] = ["E100", "E100", ""] + [""] * (len(df) - 3)
    df["Re-evaluate On"] = None
    df["Decision Notes"] = ""
    data = build_workbook(df, [{"when": "now", "by": "me", "candidate": "x", "field": "Status", "old": "-", "new": "Hire"}], 0.85, 0.7)
    path = tmp_path / "out.xlsx"
    path.write_bytes(data)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["All Candidates", "By Status", "Employee Numbers", "Audit Log", "Summary"]
    ws = wb["All Candidates"]
    assert ws["A2"].fill.start_color.rgb.endswith("C6EFCE")
    assert ws["A3"].fill.start_color.rgb.endswith("FFEB9C")
    assert ws["A4"].fill.start_color.rgb.endswith("FFC7CE")
    emp = wb["Employee Numbers"]
    flags = [emp.cell(r, 4).value for r in range(2, emp.max_row + 1)]
    assert flags.count("DUPLICATE") == 2
