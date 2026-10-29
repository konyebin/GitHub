"""Tests for analysis/text_themes.py: schema validity, privacy rules and recovery of the planted subjective-language effect."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "tests"))

import text_themes as tt  # noqa: E402
from schema import validate  # noqa: E402

PROCESSED = ROOT / "data" / "synthetic" / "processed"
TRUTH = ROOT / "data" / "synthetic" / "_truth.json"
SECTIONS = ("resume_themes", "notes_themes")


def _ensure_data():
    if not (PROCESSED / "notes.csv").exists() or not TRUTH.exists():
        subprocess.run([sys.executable, str(ROOT / "synthetic" / "make_synthetic.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "loader.py")], check=True)


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    _ensure_data()
    out = tmp_path_factory.mktemp("results")
    tt.run(PROCESSED, out)
    return out


@pytest.fixture(scope="module")
def inputs():
    _ensure_data()
    return tt._load(PROCESSED)


def _path_of(summary: str):
    t = summary.lower()
    for key, name in (("end users", "help_desk"), ("internship", "intern"), ("self-study", "career_changer"),
                      ("bootcamp", "bootcamp"), ("several years", "experienced_se")):
        if key in t:
            return name
    return None


@pytest.fixture(scope="module")
def styled(inputs):
    notes = tt.note_ranks(inputs["notes"], inputs["candidates"], inputs["exercises"])
    si = tt.style_index(notes, np.random.default_rng(1))
    d = si["notes"].copy()
    truth = json.loads(TRUTH.read_text())["subjective_notes"]
    d["planted"] = [truth.get(f"{c}|{s}", {}).get("subjective", np.nan) for c, s in zip(d["candidate_id"], d["source"])]
    paths = dict(zip(inputs["resumes"]["candidate_id"].astype(str), inputs["resumes"]["text"].map(_path_of)))
    d["path"] = d["candidate_id"].map(paths)
    return d


def test_json_validates(results):
    for sec in SECTIONS:
        local = validate(results / "local" / f"{sec}.json")
        share = validate(results / "shareable" / f"{sec}.json", shareable=True)
        assert local["section"] == share["section"] == sec
        assert local["findings"] and share["findings"]
        for f in local["findings"]:
            assert f["evidence"].strip()


def test_shareable_has_no_candidate_ids_or_free_text(results, inputs):
    resume_lines = {ln.strip() for t in inputs["resumes"]["text"] for ln in str(t).splitlines() if len(ln.strip()) > 25}
    note_sents = {s.strip() for t in inputs["notes"]["text"].dropna() for s in re.split(r"(?<=[.;])\s+", str(t)) if len(s.strip()) > 25}
    for sec in SECTIONS:
        for sub in ("local", "shareable"):
            raw = (results / sub / f"{sec}.json").read_text()
            for line in resume_lines | note_sents:
                assert line not in raw, "free text leaked into output"
        raw = (results / "shareable" / f"{sec}.json").read_text()
        assert not re.search(r"candidate\s?\d+", raw, re.I), "candidate id in shareable output"


def test_small_groups_suppressed_in_shareable(results):
    for sec in SECTIONS:
        d = json.loads((results / "shareable" / f"{sec}.json").read_text())
        for c in d["charts"]:
            if c["type"] == "boxplot":
                for g in c["data"]["groups"]:
                    if g.get("suppressed"):
                        assert g["n"] is None and g["median"] is None
                    else:
                        assert g["n"] >= tt.MIN_GROUP
            if c["type"] == "table" and "suppressed" in c["data"]["columns"]:
                si = c["data"]["columns"].index("suppressed")
                for row in c["data"]["rows"]:
                    if row[si]:
                        assert not any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row)


def test_candidate_ids_only_in_local_discordance_table(results):
    d = json.loads((results / "local" / "notes_themes.json").read_text())
    tab = next(c for c in d["charts"] if c["id"] == "notes-discordant")
    assert all(re.match(r"candidate\d+", str(r[1])) for r in tab["data"]["rows"])
    s = json.loads((results / "shareable" / "notes_themes.json").read_text())
    assert "notes-discordant" not in {c["id"] for c in s["charts"]}


def test_no_resume_candidates_reported(results, inputs):
    c = inputs["candidates"]
    n_no = int((~tt._as_bool(c["has_resume"])).sum())
    d = json.loads((results / "local" / "resume_themes.json").read_text())
    assert d["meta"]["n_no_resume"] == n_no
    assert d["meta"]["n_resumes"] + n_no == d["meta"]["n_candidates"] == len(c)
    assert str(n_no) in d["findings"][0]["text"]
    assert any(ch["id"] == "resume-coverage" for ch in d["charts"])


def test_more_than_one_theme(results):
    r = json.loads((results / "local" / "resume_themes.json").read_text())
    assert r["meta"]["n_topics"] > 1
    topics = next(c for c in r["charts"] if c["id"] == "resume-topics")
    assert len(topics["data"]["rows"]) == r["meta"]["n_topics"]
    n = json.loads((results / "local" / "notes_themes.json").read_text())
    assert all(v["k"] > 1 for v in n["meta"]["topics"].values())


def test_hypothesis_and_proxy_checks_present(results):
    r = json.loads((results / "local" / "resume_themes.json").read_text())
    ids = {c["id"] for c in r["charts"]}
    assert {"resume-hypothesis", "resume-proxy-check", "resume-topic-outcome"} <= ids
    hyp = next(c for c in r["charts"] if c["id"] == "resume-hypothesis")["data"]
    assert {row[0] for row in hyp["rows"]} == {"Interview", "Role Play", "Presentation"}
    assert any("interviews favour" in f["text"] for f in r["findings"])


def test_topics_stay_off_proxy_tokens(inputs):
    """Proxy-shaped lines (employer/school/city/date) are held out of the topic vocabulary."""
    c = inputs["candidates"]
    cities = {tt._norm_city(x) for x in c["proxy_home_city"].dropna().unique()}
    rng = np.random.default_rng(0)
    texts = [tt.split_resume(t, cities)[0] for t in inputs["resumes"]["text"]]
    tp = tt.discover_topics(texts, rng)
    vocab = " ".join(tp["vocab"])
    for city in cities:
        assert city not in vocab


def test_planted_subjective_language_recovered(styled):
    """Planted: one assessor writes impression-style notes more often for career_changer and intern resumes than help_desk."""
    ex = styled[styled["source"].isin(tt.EXERCISES) & styled["planted"].notna() & styled["path"].notna()]
    flag_rate = ex.groupby("path")["planted"].mean()
    assert flag_rate["career_changer"] > flag_rate["help_desk"]
    assert flag_rate["intern"] > flag_rate["help_desk"]
    # the data-derived (cross-fitted, truth-blind) index must detect the planted notes ...
    auc = roc_auc_score(ex["planted"].astype(int), ex["subj_rate"])
    assert auc > 0.8
    # ... and reproduce the same ordering by resume path
    mean_s = ex.groupby("path")["subj_rate"].mean()
    assert mean_s["career_changer"] > mean_s["help_desk"]
    assert mean_s["intern"] > mean_s["help_desk"]


def test_style_does_not_track_score_like_rubric_language(styled):
    sub = styled[styled["source"].isin(tt.EXERCISES)]
    rho_s = abs(sub["subj_rate"].corr(sub["rank"], method="spearman"))
    rho_t = abs(sub["rubric_tone"].corr(sub["rank"], method="spearman"))
    assert rho_t > rho_s


def test_module_theme_table_shows_career_changer_theme_higher(results):
    """The module's own by-theme output: the career-changer-like theme has higher impression-style intensity than help-desk."""
    d = json.loads((results / "local" / "notes_themes.json").read_text())
    tab = next(c for c in d["charts"] if c["id"] == "notes-style-by-theme")["data"]["rows"]
    rows = [r for r in tab if r[0] == "AC exercises pooled"]
    career = next(r for r in rows if "self study" in r[1] or "career" in r[1] or "manager moving" in r[1])
    desk = next(r for r in rows if "users" in r[1])
    assert career[3] > desk[3]


def test_deterministic_given_seed(inputs):
    cities = {tt._norm_city(x) for x in inputs["candidates"]["proxy_home_city"].dropna().unique()}
    texts = [tt.split_resume(t, cities)[0] for t in inputs["resumes"]["text"]]
    a = tt.discover_topics(texts, np.random.default_rng(3))
    b = tt.discover_topics(texts, np.random.default_rng(3))
    assert a["k"] == b["k"] and a["labels"] == b["labels"]
    x = np.random.default_rng(0).normal(size=60)
    y = x + np.random.default_rng(1).normal(size=60)
    r1 = tt.assoc(x, y, np.random.default_rng(5))
    r2 = tt.assoc(x, y, np.random.default_rng(5))
    assert r1 == r2


def test_statistics_helpers():
    rng = np.random.default_rng(0)
    x = rng.normal(size=80)
    y = x + rng.normal(size=80) * 0.5
    a = tt.assoc(x, y, rng, n_perm=1000)
    assert a["rho"] > 0.6 and a["ci"][0] > 0 and a["p"] < 0.01
    z = rng.normal(size=80)
    nul = tt.assoc(x, z, rng, n_perm=1000)
    assert nul["strength" if "strength" in nul else "effect"] in ("negligible", "small", "moderate", "large")
    q = tt.bh(np.array([0.001, 0.01, 0.2, 0.9]))
    assert np.all(np.diff(q) >= 0) and q[0] < 0.01
    # partial correlation removes a shared driver
    w = rng.normal(size=120)
    xx, yy = w + rng.normal(size=120) * 0.3, w + rng.normal(size=120) * 0.3
    assert abs(tt.partial_assoc(xx, yy, [w], rng, n_perm=500)["rho"]) < abs(tt.assoc(xx, yy, rng, n_perm=200)["rho"])


def test_small_group_helpers_suppress():
    g = tt._box("tiny", [0.1, 0.4, 0.7])
    assert g["suppressed"] and g["n"] == 3
    s = tt._shareable_box(g)
    assert s["n"] is None and s["median"] is None and s["suppressed"] is True
    assert not tt._shareable_box(tt._box("ok", np.linspace(0, 1, 9)))["suppressed"]
