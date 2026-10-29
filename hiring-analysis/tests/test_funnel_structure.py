"""Tests for analysis/funnel_structure.py: schema validity, privacy rules, determinism and recovery of planted effects."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "analysis"))

import funnel_structure as fs  # noqa: E402
from schema import validate  # noqa: E402

PROCESSED = ROOT / "data" / "synthetic" / "processed"
TRUTH = ROOT / "data" / "synthetic" / "_truth.json"
SECTIONS = ("funnel", "structure")


def ensure_data() -> None:
    if not (PROCESSED / "candidates.csv").exists():
        if not (ROOT / "data" / "synthetic" / "assessment_center.xlsx").exists():
            subprocess.run([sys.executable, str(ROOT / "synthetic" / "make_synthetic.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "loader.py")], check=True)


@pytest.fixture(scope="module")
def results(tmp_path_factory) -> Path:
    ensure_data()
    out = tmp_path_factory.mktemp("results")
    fs.run(PROCESSED, out)
    return out


def chart(doc: dict, cid: str) -> dict:
    return next(c for c in doc["charts"] if c["id"] == cid)


def load(results: Path, kind: str, section: str) -> dict:
    return json.loads((results / kind / f"{section}.json").read_text())


def test_json_validates(results):
    for section in SECTIONS:
        for kind in ("local", "shareable"):
            path = results / kind / f"{section}.json"
            d = validate(path, shareable=(kind == "shareable"))
            assert d["section"] == section
            assert d["findings"] and d["charts"] and d["caveats"]
            for f in d["findings"]:
                assert f["evidence"].strip()


def test_every_finding_has_n_and_strength(results):
    for section in SECTIONS:
        for f in load(results, "local", section)["findings"]:
            assert "n=" in f["evidence"], f
            assert f["strength"] in ("robust", "suggestive", "weak")


def test_shareable_has_no_candidate_ids_or_local_only_tables(results):
    ids = set(pd.read_csv(PROCESSED / "candidates.csv")["candidate_id"].astype(str))
    for section in SECTIONS:
        raw = (results / "shareable" / f"{section}.json").read_text()
        d = json.loads(raw)
        assert not any(f'"{i}"' in raw for i in ids)
        for c in d["charts"]:
            if c["type"] == "table":
                assert "candidate_id" not in c["data"]["columns"]
    local_ids = {c["id"] for c in load(results, "local", "funnel")["charts"]}
    share_ids = {c["id"] for c in load(results, "shareable", "funnel")["charts"]}
    assert "screen-disagreements" in local_ids and "screen-disagreements" not in share_ids
    assert "decision-flags" in {c["id"] for c in load(results, "local", "structure")["charts"]}
    assert "decision-flags" not in {c["id"] for c in load(results, "shareable", "structure")["charts"]}
    assert "divergent-candidates" not in {c["id"] for c in load(results, "shareable", "structure")["charts"]}


def test_expected_charts_present(results):
    f = load(results, "local", "funnel")
    s = load(results, "local", "structure")
    fids = {c["id"] for c in f["charts"]}
    sids = {c["id"] for c in s["charts"]}
    assert {"funnel-stages", "gate-table", "ti-rank-by-advance", "proxy-tests", "screen-disagreements"} <= fids
    assert {"spearman-heatmap", "pca-variance", "pca-loadings", "divergence-scatter", "divergent-candidates",
            "cluster-profiles", "decision-score-overlap", "decision-flags"} <= sids
    hm = chart(s, "spearman-heatmap")["data"]
    assert len(hm["row_labels"]) == 16  # TI + 3 exercise totals + 12 competencies
    assert chart(s, "pca-loadings")["data"]["rows"].__len__() == 12


def test_deterministic(results, tmp_path):
    fs.run(PROCESSED, tmp_path)
    for section in SECTIONS:
        for kind in ("local", "shareable"):
            assert (tmp_path / kind / f"{section}.json").read_bytes() == (results / kind / f"{section}.json").read_bytes()


def test_funnel_counts_match_data(results):
    c = pd.read_csv(PROCESSED / "candidates.csv")
    d = load(results, "local", "funnel")
    vals = chart(d, "funnel-stages")["data"]["series"][0]["values"]
    assert vals[0] == len(c)
    assert vals[1] == int(c["reached_ti"].sum())
    assert vals[3] == int(c["attended_ac"].sum())


def test_planted_interview_roleplay_agree_more_than_presentation(results):
    d = load(results, "local", "structure")
    rows = {r[0]: r for r in chart(d, "exercise-rank-correlations")["data"]["rows"]}
    ir = rows["Interview total vs Role Play total"][2]
    ip = rows["Interview total vs Presentation total"][2]
    rp = rows["Role Play total vs Presentation total"][2]
    assert ir > ip and ir > rp
    # independent recomputation straight from the CSVs
    ex = pd.read_csv(PROCESSED / "exercises.csv").pivot(index="candidate_id", columns="exercise", values="total")
    corr = ex.corr(method="spearman")
    assert corr.loc["Interview", "Role Play"] > corr.loc["Interview", "Presentation"]
    assert corr.loc["Interview", "Role Play"] > corr.loc["Role Play", "Presentation"]
    assert abs(corr.loc["Interview", "Role Play"] - ir) < 1e-3
    finding = d["findings"][0]
    assert "Interview and Role Play" in finding["text"]
    assert TRUTH.exists() and "Interview and Role Play ranks agree" in json.loads(TRUTH.read_text())["planted"]


def test_planted_decision_score_disagreements_detected(results):
    c = pd.read_csv(PROCESSED / "candidates.csv").set_index("candidate_id")
    att = c[c["decision"].notna()]
    d = load(results, "local", "structure")
    flags = chart(d, "decision-flags")["data"]
    cols = flags["columns"]
    assert flags["rows"], "no decision-vs-score disagreement detected"
    for row in flags["rows"]:
        rec = dict(zip(cols, row))
        cid = rec["candidate_id"]
        assert cid in att.index
        assert rec["Discordant pairs"] >= 1
        dec, tot = att.loc[cid, "decision"], att.loc[cid, "ac_total"]
        others = att[att.index != cid]
        if dec == "Hire":
            assert tot < others.loc[others["decision"] != "Hire", "ac_total"].max()
        elif dec == "No Hire":
            assert tot > others.loc[others["decision"] != "No Hire", "ac_total"].min()
        else:
            assert (tot < others.loc[others["decision"] == "Hire", "ac_total"].max()) or \
                   (tot > others.loc[others["decision"] == "No Hire", "ac_total"].min())
    # decision groups overlap on score rank but are still ordered
    tbl = chart(d, "decision-overlap-table")["data"]
    hire_nohire = next(r for r in tbl["rows"] if r[0] == "Hire vs No Hire")
    hire_standby = next(r for r in tbl["rows"] if r[0] == "Hire vs Standby")
    assert hire_nohire[3] > 0.5 and hire_standby[6] > 0  # some pairs are in the wrong order


def test_planted_screening_disagreements_detected(results):
    c = pd.read_csv(PROCESSED / "candidates.csv")
    inv = c["screen_invited"].astype(str).str.lower().eq("yes")
    against = c[(c["screen_passfail"].eq("Pass") & c["reached_ti"] & ~inv) | (c["screen_passfail"].eq("Fail") & inv)]
    assert len(against) > 0
    d = load(results, "local", "funnel")
    tbl = chart(d, "screen-disagreements")["data"]
    listed = {r[0] for r in tbl["rows"]}
    assert set(against["candidate_id"]) <= listed
    agree = {r[0]: r[1] for r in chart(d, "screen-agreement")["data"]["rows"]}
    assert agree["Pass/Fail and invited disagree"] == len(against)


def test_small_groups_suppressed_in_shareable(tmp_path):
    ensure_data()
    proc = tmp_path / "processed"
    shutil.copytree(PROCESSED, proc, ignore=shutil.ignore_patterns("results"))
    c = pd.read_csv(proc / "candidates.csv")
    standby = c.index[c["decision"] == "Standby"].tolist()
    c.loc[standby[3:], "decision"] = "No Hire"  # leave 3 Standby candidates
    c.to_csv(proc / "candidates.csv", index=False)
    out = tmp_path / "out"
    fs.run(proc, out)
    for kind in ("local", "shareable"):
        validate(out / kind / "structure.json", shareable=(kind == "shareable"))
    loc = load(out, "local", "structure")
    sh = load(out, "shareable", "structure")
    lb = {g["name"]: g for g in chart(loc, "decision-score-overlap")["data"]["groups"]}
    sb = {g["name"]: g for g in chart(sh, "decision-score-overlap")["data"]["groups"]}
    assert lb["Standby"]["n"] == 3
    assert sb["Standby"]["suppressed"] is True and sb["Standby"]["n"] is None and sb["Standby"]["median"] is None
    assert sb["Hire"]["suppressed"] is False and sb["Hire"]["n"] >= 5
    tbl = chart(sh, "decision-overlap-table")["data"]
    for r in tbl["rows"]:
        if "Standby" in r[0]:
            assert r[-1] is True and r[3] is None
    scat = chart(sh, "decision-vs-rank")["data"]["points"]
    assert all(p["group"] != "Standby" for p in scat)


def test_helpers():
    s = pd.Series([10, 20, 20, 30], index=list("abcd"))
    p = fs.pct_rank(s)
    assert p["a"] < p["b"] == p["c"] < p["d"] and 0 < p.min() and p.max() < 1
    assert fs.share_count(3) == "fewer than 5" and fs.share_count(7) == "7" and fs.share_count(0) == "0"
    boxes = fs.suppress_boxes([fs.box_stats("x", [1, 2, 3]), fs.box_stats("y", range(10))])
    assert boxes[0]["suppressed"] and boxes[0]["median"] is None and not boxes[1]["suppressed"]
    assert fs.grade([True, True, True], 20) == "robust"
    assert fs.grade([True, True, False], 20) == "suggestive"
    assert fs.grade([True, False, False], 20) == "weak"
