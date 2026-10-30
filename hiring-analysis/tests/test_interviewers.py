"""Tests for analysis/interviewers.py: schema validity, suppression, determinism, planted-effect recovery."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "tests"))

import interviewers as iv  # noqa: E402
from schema import validate  # noqa: E402

PROCESSED = ROOT / "data" / "synthetic" / "processed"
TRUTH = ROOT / "data" / "synthetic" / "_truth.json"


@pytest.fixture(scope="session")
def processed():
    if not (PROCESSED / "candidates.csv").exists() or not TRUTH.exists():
        subprocess.run([sys.executable, str(ROOT / "synthetic" / "make_synthetic.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "loader.py")], check=True)
    return PROCESSED


@pytest.fixture(scope="session")
def results(processed, tmp_path_factory):
    out = tmp_path_factory.mktemp("results")
    iv.run(processed, out)
    return out


@pytest.fixture(scope="session")
def analysis(processed):
    return iv.analyze(processed)


def _paths(results):
    return results / "local" / "interviewers.json", results / "shareable" / "interviewers.json"


def test_schema_local_and_shareable(results):
    local, share = _paths(results)
    dl = validate(local, shareable=False)
    ds = validate(share, shareable=True)
    assert dl["section"] == ds["section"] == "interviewers"
    assert dl["findings"] and all(f["evidence"] for f in dl["findings"])
    assert {c["id"] for c in ds["charts"]} <= {c["id"] for c in dl["charts"]}
    assert any(c["type"] == "boxplot" for c in dl["charts"]) and any(c["type"] == "hbar" for c in dl["charts"])


def test_no_candidate_ids_in_shareable(results):
    local, share = _paths(results)
    assert re.search(r"candidate\d+", local.read_text())
    assert not re.search(r"candidate\s*\d+", share.read_text(), flags=re.I)


def test_deterministic(processed, results, tmp_path):
    iv.run(processed, tmp_path)
    for kind in ("local", "shareable"):
        assert (tmp_path / kind / "interviewers.json").read_text() == (results / kind / "interviewers.json").read_text()


def test_small_reviewer_suppressed_in_shareable(processed, tmp_path):
    work = tmp_path / "proc"
    work.mkdir()
    for f in processed.glob("*.csv"):
        (work / f.name).write_bytes(f.read_bytes())
    ex = pd.read_csv(work / "exercises.csv")
    idx = ex.index[ex["exercise"] == "Role Play"][:3]
    ex.loc[idx, "assessor"] = "Assessor 9"
    ex.to_csv(work / "exercises.csv", index=False)
    iv.run(work, tmp_path / "out")
    local = validate(tmp_path / "out" / "local" / "interviewers.json")
    share = validate(tmp_path / "out" / "shareable" / "interviewers.json", shareable=True)
    assert "Assessor 9" in json.dumps(local)
    box = [g for c in share["charts"] if c["type"] == "boxplot" for g in c["data"]["groups"] if g["name"].startswith("Assessor 9")]
    assert box and all(g["suppressed"] and g["median"] is None for g in box)
    table = next(c for c in share["charts"] if c["id"] == "deviation-table")["data"]["rows"]
    for row in table:
        if row[0] == "Assessor 9":
            assert row[3] is True and all(v is None for v in row[4:])
    assert not any("Assessor 9" in f["text"] for f in share["findings"])


def test_strength_labels_and_n_in_evidence(results):
    d = json.loads(_paths(results)[0].read_text())
    for f in d["findings"]:
        assert f["strength"] in {"robust", "suggestive", "weak"}
        assert re.search(r"n=\d+", f["evidence"])


def test_planted_assessor4_interview_leniency(analysis):
    dev = analysis["dev"]
    iview = dev[dev["role"] == "Interview"].set_index("reviewer")
    assert iview.loc["Assessor 4", "dev"] > 0
    assert iview.loc["Assessor 4", "ci_lo"] > 0
    others = iview.drop(index="Assessor 4")["dev"]
    assert iview.loc["Assessor 4", "dev"] > others.max()
    assert iview.loc["Assessor 4", "strength"] in {"robust", "suggestive"}
    others_nonint = dev[(dev["role"] != "Interview") & (dev["reviewer"] == "Assessor 4")]
    assert (others_nonint["strength"] == "weak").all()


def _resume_path(text: str) -> str:
    t = text.lower()
    for kw, p in (("operations manager", "career_changer"), ("internship", "intern"), ("bootcamp", "bootcamp"),
                  ("help desk professional", "help_desk"), ("systems engineer", "experienced_se")):
        if kw in t:
            return p
    return "other"


def test_planted_assessor5_subjective_language_by_resume_group(analysis, processed):
    res = pd.read_csv(processed / "resumes.csv")
    res["path"] = res["text"].map(_resume_path)
    ns = analysis["note_style"].merge(res[["candidate_id", "path"]], on="candidate_id")
    a5 = ns[ns["reviewer"] == "Assessor 5"]
    for col in ("share_A", "share_B"):
        hi = a5[a5["path"].isin(["career_changer", "intern"])][col].mean()
        lo = a5[a5["path"] == "help_desk"][col].mean()
        assert hi > lo
        assert hi > 2 * lo
    rest = ns[ns["reviewer"] != "Assessor 5"]
    gap5 = a5[a5["path"].isin(["career_changer", "intern"])]["share_A"].mean() - a5[a5["path"] == "help_desk"]["share_A"].mean()
    gap_rest = rest[rest["path"].isin(["career_changer", "intern"])]["share_A"].mean() - rest[rest["path"] == "help_desk"]["share_A"].mean()
    assert gap5 > gap_rest + 0.1
    style = analysis["style"]
    a = style[style["variant"] == "A"].set_index("reviewer")
    assert a["mean"].idxmax() == "Assessor 5" and a.loc["Assessor 5", "p_adj"] < 0.05
    bias = analysis["bias"]
    b5 = bias[(bias["reviewer"] == "Assessor 5") & (bias["outcome"] == "style")].iloc[0]
    assert b5["p_perm"] == bias[bias["outcome"] == "style"]["p_perm"].min()


def test_style_measure_tracks_planted_subjective_notes(analysis):
    truth = json.loads(TRUTH.read_text())["subjective_notes"]
    ns = analysis["note_style"].copy()
    ns["truth"] = [truth.get(f"{r.candidate_id}|{r.role}", {}).get("subjective") for r in ns.itertuples()]
    ns = ns.dropna(subset=["truth", "share_A"])
    pos, neg = ns[ns["truth"].astype(bool)]["share_A"], ns[~ns["truth"].astype(bool)]["share_A"]
    assert len(pos) >= 10 and pos.mean() > 3 * neg.mean()


def test_notes_agree_with_scores_and_exercises_agree(analysis):
    g = analysis["cons_global"]
    assert g["rho"] > 0.5 and g["lo"] > 0
    pairs = analysis["pairs"].set_index(["a", "b"])
    assert pairs.loc[("Interview", "Role Play"), "rho"] > 0.4
    assert pairs.loc[("Interview", "Role Play"), "rho"] > pairs.loc[("Interview", "Presentation"), "rho"] - 0.05
