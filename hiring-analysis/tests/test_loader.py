import re
import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import loader  # noqa: E402

SHEET = re.compile(r"^AMER [A-Z][a-z]{2} \d{1,2}$")
TESTDATA = ROOT / "testdata"
SYNTH = ROOT / "data" / "synthetic" / "assessment_center.xlsx"


def test_testdata_scores_workbook_has_six_cohort_sheets_and_screening_has_one():
    scores = openpyxl.load_workbook(TESTDATA / "FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx")
    assert len(scores.sheetnames) == 6 and all(SHEET.match(n) for n in scores.sheetnames)
    names = [scores[s].cell(r, 2).value for s in scores.sheetnames for r in range(11, 40) if scores[s].cell(r, 2).value]
    assert len(names) == len(set(names)) == 20
    assert all("salutation" not in str(c.value).lower() for s in scores.worksheets for c in s[9])
    assert len(openpyxl.load_workbook(TESTDATA / "ASE_Candidate_Screen_Review_TEST_DATA.xlsx").sheetnames) == 1


def test_loader_stacks_every_cohort_sheet_from_the_testdata_workbook():
    warnings: list = []
    cands, long_df, ex_df, notes_df, audit = loader.load_assessment(TESTDATA / "FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx", warnings)
    assert len(cands) == 20 and cands["cohort"].nunique() == 6
    assert len(long_df) == 20 * 12 and len(ex_df) == 20 * 3


def test_loader_skips_a_sheet_without_the_header_and_warns(tmp_path):
    wb = openpyxl.load_workbook(TESTDATA / "FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx")
    wb.create_sheet("Notes").append(["nothing to see"])
    p = tmp_path / "scores.xlsx"
    wb.save(p)
    warnings: list = []
    cands, *_ = loader.load_assessment(p, warnings)
    assert len(cands) == 20
    assert any("'Notes' skipped" in w for w in warnings)


@pytest.mark.skipif(not SYNTH.exists(), reason="synthetic data not generated")
def test_synthetic_assessment_workbook_is_multi_sheet():
    assert len(openpyxl.load_workbook(SYNTH).sheetnames) == 6
