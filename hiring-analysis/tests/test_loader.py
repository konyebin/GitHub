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
SYNTH = ROOT / "data" / "synthetic"


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
    assert len(cands) == 20 and cands["ac_day"].nunique() == 6
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


def _book(path, kind="scores"):
    return loader.workbook_kind(path)


# ----------------------------------------------------------------------------- cohorts

import shutil  # noqa: E402

import pandas as pd  # noqa: E402

SCORES = TESTDATA / "FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx"
SCREEN = TESTDATA / "ASE_Candidate_Screen_Review_TEST_DATA.xlsx"


def scores_copy(dest: Path, suffix: str = "") -> Path:
    """The test scores workbook, optionally with every candidate renamed so ids do not repeat across cohorts."""
    wb = openpyxl.load_workbook(SCORES)
    for ws in wb.worksheets:
        for r in range(11, ws.max_row + 1):
            if ws.cell(r, 2).value:
                ws.cell(r, 2).value = f"{ws.cell(r, 2).value}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dest)
    return dest


def test_parse_cohort_accepts_both_spellings():
    assert loader.parse_cohort("FY27Q3_AMER_ASE_Scores_TEST_DATA") == "AMER FY27Q3"
    assert loader.parse_cohort("AMER FY27Q1") == "AMER FY27Q1"
    assert loader.parse_cohort("amer fy28q1 screening") == "AMER FY28Q1"
    assert loader.parse_cohort("FY27Q2 Scores") == "FY27Q2"
    assert loader.parse_cohort("candidate12") is None


def test_ac_day_dates_take_their_year_from_the_cohort_quarter():
    w: list = []
    assert loader.parse_ac_date("AMER Oct 15", "AMER FY27Q1", 8, w) == "2026-10-15"
    assert loader.parse_ac_date("AMER Dec 9", "AMER FY27Q2", 8, w) == "2026-12-09"
    assert loader.parse_ac_date("AMER Mar 8", "AMER FY27Q3", 8, w) == "2027-03-08"
    assert loader.parse_ac_date("AMER Feb 3", "AMER FY27Q1", 1, w) == "2027-02-03"
    assert not w
    assert loader.parse_ac_date("AMER Jun 3", "AMER FY27Q1", 8, w) and any("outside" in x for x in w)
    w.clear()
    assert loader.parse_ac_date("Day one", "AMER FY27Q1", 8, w) is None and w


def test_cohort_comes_from_filename_else_folder_and_workbooks_are_found_by_content(tmp_path):
    data, out = tmp_path / "data", tmp_path / "out"
    scores_copy(data / "AMER FY27Q1" / "candidate5.xlsx")               # redacted name: folder gives the cohort
    shutil.copy(SCREEN, data / "AMER FY27Q1" / "candidate6.xlsx")
    scores_copy(data / "FY27Q2_AMER_ASE_Scores.xlsx", " II")             # filename gives the cohort
    summary = loader.build(data, out, min_cohort_ac=1)
    names = [c["name"] for c in summary["cohorts"]]
    assert names == ["AMER FY27Q1", "AMER FY27Q2"]
    assert [t["name"] for t in summary["targets"]] == ["All cohorts", "AMER FY27Q1", "AMER FY27Q2"]
    for t in ("All cohorts", "AMER FY27Q1", "AMER FY27Q2"):
        assert (out / t / "processed" / "candidates.csv").exists()
    pooled = pd.read_csv(out / "All cohorts" / "processed" / "candidates.csv")
    q1 = pd.read_csv(out / "AMER FY27Q1" / "processed" / "candidates.csv")
    assert set(pooled["cohort"]) == {"AMER FY27Q1", "AMER FY27Q2"} and set(q1["cohort"]) == {"AMER FY27Q1"}
    assert len(pooled) == len(q1) + (pooled["cohort"] == "AMER FY27Q2").sum()
    assert pooled["ac_date"].notna().sum() == 40 and set(pooled.dropna(subset=["ac_day"])["ac_day"]) <= set(openpyxl.load_workbook(SCORES).sheetnames)


def test_same_candidate_in_two_cohorts_stops_the_run(tmp_path):
    data = tmp_path / "data"
    scores_copy(data / "FY27Q1_AMER_Scores.xlsx")
    scores_copy(data / "FY27Q2_AMER_Scores.xlsx")
    with pytest.raises(ValueError, match="more than one cohort"):
        loader.build(data, tmp_path / "out")


def test_workbook_without_a_cohort_in_name_or_folder_is_an_error(tmp_path):
    data = tmp_path / "data"
    scores_copy(data / "candidate9.xlsx")
    with pytest.raises(ValueError, match="which cohort"):
        loader.build(data, tmp_path / "out")


def test_small_cohorts_are_pooled_but_not_analysed_alone_and_one_cohort_has_no_pooled_view(tmp_path):
    data = tmp_path / "data"
    scores_copy(data / "FY27Q1_AMER_Scores.xlsx")
    scores_copy(data / "FY27Q2_AMER_Scores.xlsx", " II")
    summary = loader.build(data, tmp_path / "out", min_cohort_ac=1000)
    assert [t["name"] for t in summary["targets"]] == ["All cohorts"]
    assert any("not analysed on its own" in w for w in summary["warnings"])
    solo = tmp_path / "solo"
    scores_copy(solo / "FY27Q1_AMER_Scores.xlsx")
    assert [t["name"] for t in loader.build(solo, tmp_path / "out2", min_cohort_ac=1000)["targets"]] == ["AMER FY27Q1"]


def test_interviewer_map_links_labels_per_cohort_and_for_all():
    df = pd.DataFrame({"cohort": ["AMER FY27Q1", "AMER FY27Q2", "AMER FY27Q2"], "assessor": ["Assessor 3", "Assessor 3", "Assessor 9"]})
    loader.apply_map(df, "assessor", {("AMER FY27Q2", "Assessor 3"): "Assessor 8", ("*", "Assessor 9"): "Assessor 1"})
    assert df["assessor"].tolist() == ["Assessor 3", "Assessor 8", "Assessor 1"]
