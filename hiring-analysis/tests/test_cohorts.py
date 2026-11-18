"""Tests for the multi-cohort pipeline: cohorts section, per-cohort outputs, date-based drift, dashboard switcher."""
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("analysis", "tests", "pipeline", "dashboard", ""):
    sys.path.insert(0, str(ROOT / sub) if sub else str(ROOT))

import cohorts  # noqa: E402
import interviewers as iv  # noqa: E402
from schema import validate  # noqa: E402

SYNTH = ROOT / "data" / "synthetic"
POOLED = SYNTH / "processed" / "All cohorts" / "processed"
NAMES = ["AMER FY27Q1", "AMER FY27Q2", "AMER FY27Q3"]

pytestmark = pytest.mark.skipif(not (POOLED / "candidates.csv").exists(), reason="run pipeline/run_all.py on the synthetic data first")


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    out = tmp_path_factory.mktemp("cohort_results")
    cohorts.run(POOLED, out)
    return out


def test_cohorts_section_validates_in_both_copies(results):
    for kind in ("local", "shareable"):
        d = validate(results / kind / "cohorts.json", shareable=kind == "shareable", require_plain=True)
        assert d["section"] == "cohorts" and d["findings"]
        assert {c["id"] for c in d["charts"]} == {"cohort-funnel", "cohort-scores", "cohort-decisions", "cohort-summary", "cohort-reviewers"}


def test_every_cohort_appears_in_every_comparison(results):
    d = json.loads((results / "local" / "cohorts.json").read_text())
    charts = {c["id"]: c["data"] for c in d["charts"]}
    assert charts["cohort-funnel"]["labels"] == NAMES
    assert [g["name"] for g in charts["cohort-scores"]["groups"]] == NAMES
    assert [r[0] for r in charts["cohort-summary"]["rows"]] == NAMES
    assert charts["cohort-reviewers"]["columns"] == ["Reviewer"] + NAMES
    assert all(all(v > 0 for v in row[1:]) for row in charts["cohort-reviewers"]["rows"]), "synthetic reviewers work in every cohort"


def test_planted_cohort_trend_is_found(results):
    d = json.loads((results / "local" / "cohorts.json").read_text())
    top = [f for f in d["findings"] if "rose" in f["plain"]]
    assert top, "scores rise across cohorts (planted): " + str([f["plain"] for f in d["findings"]])
    reach = [f for f in d["findings"] if "reached the assessment center" in f["plain"]]
    assert reach and reach[0]["strength"] in ("robust", "suggestive")


def test_summary_counts_add_up_to_the_pooled_data(results):
    d = json.loads((results / "local" / "cohorts.json").read_text())
    rows = {c["id"]: c["data"]["rows"] for c in d["charts"] if c["id"] == "cohort-summary"}["cohort-summary"]
    pooled = pd.read_csv(POOLED / "candidates.csv")
    assert sum(r[1] for r in rows) == len(pooled)
    assert sum(r[3] for r in rows) == int(pooled["attended_ac"].sum())


def test_cohorts_section_is_deterministic(results, tmp_path):
    cohorts.run(POOLED, tmp_path)
    for kind in ("local", "shareable"):
        assert (tmp_path / kind / "cohorts.json").read_text() == (results / kind / "cohorts.json").read_text()


def test_no_candidate_ids_in_shareable_cohorts_section(results):
    assert not re.search(r"candidate\s*\d+", (results / "local" / "cohorts.json").read_text() + (results / "shareable" / "cohorts.json").read_text())


def test_drift_uses_real_assessment_dates_when_available(tmp_path):
    iv.run(POOLED, tmp_path)
    d = json.loads((tmp_path / "local" / "interviewers.json").read_text())
    assert "assessment date" in {c["id"]: c["title"] for c in d["charts"]}["drift-hbar"]


def test_same_reviewer_label_is_one_reviewer_across_cohorts():
    ex = pd.read_csv(POOLED / "exercises.csv")
    per = ex.dropna(subset=["assessor"]).groupby("assessor")["cohort"].nunique()
    assert (per == 3).all()


def test_cohort_folders_hold_only_their_own_candidates():
    pooled = pd.read_csv(POOLED / "candidates.csv")
    for name in NAMES:
        mine = pd.read_csv(SYNTH / "processed" / name / "processed" / "candidates.csv")
        assert set(mine["cohort"]) == {name}
        assert set(mine["candidate_id"]) == set(pooled.loc[pooled["cohort"] == name, "candidate_id"])
        res = pd.read_csv(SYNTH / "processed" / name / "processed" / "resumes.csv")
        assert set(res["candidate_id"]) <= set(mine["candidate_id"])


def test_dashboards_have_a_cohort_switcher_that_links_to_every_sibling():
    for target in ["All cohorts"] + NAMES:
        for mode in ("local", "shareable"):
            html = (SYNTH / "processed" / target / "dashboard" / f"dashboard_{mode}.html").read_text()
            payload = json.loads(re.search(r'id="payload" type="application/json">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
            nav = payload["cohorts"]
            assert nav["current"] == target and [o["name"] for o in nav["options"]] == ["All cohorts"] + NAMES
            for o in nav["options"]:
                assert (SYNTH / "processed" / target / "dashboard" / o["href"]).resolve().exists() or "%20" in o["href"]
            assert ("cohorts" in payload["sections"]) == (target == "All cohorts")


def test_end_to_end_run_writes_every_target(tmp_path, monkeypatch):
    import run_all
    monkeypatch.setenv("HIRING_OUT_DIR", str(tmp_path))
    monkeypatch.setenv("HIRING_DATA_DIR", str(SYNTH))
    result = run_all.main()
    assert result["targets"] == ["All cohorts"] + NAMES and not result["failed"]
    for t in result["targets"]:
        for mode in ("local", "shareable"):
            assert (tmp_path / t / "dashboard" / f"dashboard_{mode}.html").exists()
        assert (tmp_path / t / "results" / "shareable" / "funnel.json").exists()
    assert (tmp_path / "All cohorts" / "results" / "local" / "cohorts.json").exists()
    assert not (tmp_path / NAMES[0] / "results" / "local" / "cohorts.json").exists()
