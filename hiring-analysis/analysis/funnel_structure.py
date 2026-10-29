"""Funnel and score-structure analysis (sections `funnel` and `structure`).

Reads candidates.csv, scores_long.csv and exercises.csv from `processed_dir` (never audit_only.csv, notes or resumes)
and writes results_dir/local/{funnel,structure}.json and results_dir/shareable/{funnel,structure}.json
(see analysis/CONTRACT.md).

Design choices, in the spirit of "no fixed cutoffs":
  * every comparison uses within-cohort percentile ranks (mid-rank, 0-100), AUC / rank-biserial effects, Spearman and Kendall;
  * the only groupings are ones the data supplies (screening invited yes/no, decision groups, k-means clusters whose k is
    chosen by silhouette against a permutation null);
  * "disagreement" lists are model based: a fitted logistic / ordinal logit model gives each candidate a probability for the
    observed outcome, and a candidate is flagged when that probability is lower than the 5th percentile of the same quantity
    in outcomes simulated from the fitted model (so about 5% of candidates would be flagged even by a perfect model);
  * uncertainty comes from bootstrap CIs and permutation p-values; scans use Benjamini-Hochberg correction.

Outcomes are past human decisions, not job performance. Later-stage scores exist only for people who passed earlier gates
and are never imputed.
"""

from __future__ import annotations

import json
import os
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import rankdata
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import adjusted_rand_score, silhouette_score
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

SEED = 20261029
N_BOOT = 1000
N_PERM = 2000
MIN_GROUP = 5
EXERCISES = ("Interview", "Role Play", "Presentation")
ABBR = {"Interview": "Int", "Role Play": "RP", "Presentation": "Pres"}
DECISIONS = ("No Hire", "Standby", "Hire")
EXERCISE_TOTAL_LABEL = {e: f"{e} total" for e in EXERCISES}

warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------------------------- generic helpers

def rng_for(k: int) -> np.random.Generator:
    return np.random.default_rng([SEED, k])


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    return o


def rd(x, nd: int = 3):
    if x is None:
        return None
    try:
        if not np.isfinite(x):
            return None
    except TypeError:
        return x
    return round(float(x), nd)


def pct_rank(s: pd.Series) -> pd.Series:
    """Within-cohort mid-rank percentile in (0, 1); NaNs are left out (never imputed)."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    r = rankdata(s.to_numpy(), method="average")
    return pd.Series((r - 0.5) / len(s), index=s.index)


def bh(pvals) -> np.ndarray:
    p = np.asarray(pvals, float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    if ok.sum():
        out[ok] = multipletests(p[ok], method="fdr_bh")[1]
    return out


def grade(checks: list[bool], n_min: int = 0) -> str:
    """robust = every independent check passes (2+ checks) and the smallest group has 10+; suggestive = at least two pass."""
    k = sum(bool(c) for c in checks)
    if len(checks) >= 2 and k == len(checks) and n_min >= 10:
        return "robust"
    if k >= 2:
        return "suggestive"
    return "weak"


def share_count(k: int) -> str:
    return str(k) if (k == 0 or k >= MIN_GROUP) else f"fewer than {MIN_GROUP}"


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    lo, hi = proportion_confint(k, n, method="wilson")
    return float(lo), float(hi)


def box_stats(name: str, values) -> dict:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    n = int(len(v))
    if n == 0:
        return {"name": name, "n": 0, "min": None, "q1": None, "median": None, "q3": None, "max": None}
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"name": name, "n": n, "min": rd(v.min(), 2), "q1": rd(q1, 2), "median": rd(med, 2), "q3": rd(q3, 2),
            "max": rd(v.max(), 2)}


def suppress_boxes(groups: list[dict]) -> list[dict]:
    out = []
    for g in groups:
        if g["n"] < MIN_GROUP:
            out.append({"name": g["name"], "n": None, "min": None, "q1": None, "median": None, "q3": None,
                        "max": None, "suppressed": True})
        else:
            out.append({**g, "suppressed": False})
    return out


def suppress_rows(rows: list[list], n_idx: int, keep: int, supp_idx: int) -> list[list]:
    """Rows are [labels..., numbers..., suppressed]. Small groups keep only their first `keep` label columns."""
    out = []
    for r in rows:
        n = r[n_idx]
        if n is not None and n < MIN_GROUP:
            out.append([v if i < keep else None for i, v in enumerate(r)])
            out[-1][supp_idx] = True
        else:
            out.append(list(r))
    return out


# ------------------------------------------------------------------------------------------------- output document

class Doc:
    def __init__(self, section: str, title: str, caveats: list[str]):
        self.section, self.title, self.caveats = section, title, caveats
        self.findings: list[dict] = []
        self.charts: list[dict] = []

    def finding(self, text, strength, evidence, share_text=None, share_evidence=None):
        assert strength in ("robust", "suggestive", "weak")
        self.findings.append({"text": text, "strength": strength, "evidence": evidence,
                              "_share_text": share_text, "_share_evidence": share_evidence})

    def chart(self, cid, ctype, title, data, subtitle=None, x_label=None, y_label=None, share=None, local_only=False):
        ch = {"id": cid, "type": ctype, "title": title, "data": data, "_share": share, "_local_only": local_only}
        if subtitle:
            ch["subtitle"] = subtitle
        if x_label:
            ch["x_label"] = x_label
        if y_label:
            ch["y_label"] = y_label
        self.charts.append(ch)

    def _render(self, shareable: bool) -> dict:
        findings = []
        for f in self.findings:
            t, e = f["text"], f["evidence"]
            if shareable:
                t = f["_share_text"] or t
                e = f["_share_evidence"] or e
            findings.append({"text": t, "strength": f["strength"], "evidence": e})
        charts = []
        for ch in self.charts:
            if shareable and ch["_local_only"]:
                continue
            data = ch["data"]
            if shareable:
                data = ch["_share"] if ch["_share"] is not None else default_share(ch["type"], data)
            out = {k: v for k, v in ch.items() if not k.startswith("_")}
            out["data"] = data
            charts.append(out)
        return {"section": self.section, "title": self.title, "caveats": self.caveats, "findings": findings,
                "charts": charts}

    def write(self, results_dir: Path, candidate_ids: set[str]) -> None:
        for kind in ("local", "shareable"):
            d = results_dir / kind
            d.mkdir(parents=True, exist_ok=True)
            doc = jsonable(self._render(kind == "shareable"))
            if kind == "shareable":
                assert_no_ids(doc, candidate_ids)
            (d / f"{self.section}.json").write_text(json.dumps(doc, indent=2, allow_nan=False))


def default_share(ctype: str, data: dict) -> dict:
    if ctype == "scatter":
        pts = data["points"]
        counts: dict = {}
        for p in pts:
            counts[p.get("group")] = counts.get(p.get("group"), 0) + 1
        keep = [p for p in pts if p.get("group") is None or counts[p.get("group")] >= MIN_GROUP]
        return {"points": [{**p, "label": None} for p in keep]}
    return data


def assert_no_ids(obj, ids: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert_no_ids(k, ids)
            assert_no_ids(v, ids)
    elif isinstance(obj, list):
        for v in obj:
            assert_no_ids(v, ids)
    elif isinstance(obj, str):
        assert obj not in ids and not any(re.search(rf"\b{re.escape(i)}\b", obj) for i in ids if len(i) > 3 and i in obj), \
            "candidate id leaked into shareable output"


# ---------------------------------------------------------------------------------------------- statistical helpers

def auc_test(pos, neg, rng, n_boot: int = N_BOOT, n_perm: int = N_PERM) -> dict | None:
    """P(random 'pos' member outranks random 'neg' member), ties half. Stratified bootstrap CI, permutation p, Mann-Whitney p."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    n1, n0 = len(pos), len(neg)
    if n1 < 2 or n0 < 2:
        return None
    denom = n1 * n0
    base = n1 * (n1 + 1) / 2
    ranks = rankdata(np.concatenate([pos, neg]))
    auc = (ranks[:n1].sum() - base) / denom
    boots = np.empty(n_boot)
    for b in range(n_boot):
        rk = rankdata(np.concatenate([rng.choice(pos, n1), rng.choice(neg, n0)]))
        boots[b] = (rk[:n1].sum() - base) / denom
    cnt = 0
    for _ in range(n_perm):
        idx = rng.permutation(n1 + n0)[:n1]
        if abs((ranks[idx].sum() - base) / denom - 0.5) >= abs(auc - 0.5) - 1e-12:
            cnt += 1
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p_mwu = stats.mannwhitneyu(pos, neg, alternative="two-sided").pvalue
    return {"auc": float(auc), "lo": float(lo), "hi": float(hi), "p_perm": (cnt + 1) / (n_perm + 1),
            "p_mwu": float(p_mwu), "n_pos": n1, "n_neg": n0, "boots": boots}


def cramers_v_corrected(table: np.ndarray) -> float:
    table = np.asarray(table, float)
    table = table[table.sum(axis=1) > 0][:, table.sum(axis=0) > 0]
    r, c = table.shape
    n = table.sum()
    if r < 2 or c < 2 or n < 2:
        return np.nan
    expected = np.outer(table.sum(1), table.sum(0)) / n
    phi2 = ((table - expected) ** 2 / expected).sum() / n
    phi2c = max(0.0, phi2 - (c - 1) * (r - 1) / (n - 1))
    rc = r - (r - 1) ** 2 / (n - 1)
    cc = c - (c - 1) ** 2 / (n - 1)
    den = min(cc - 1, rc - 1)
    return float(np.sqrt(phi2c / den)) if den > 0 else np.nan


def stat_v(x, y):
    r = int(x.max()) + 1
    return cramers_v_corrected(np.bincount(x * 2 + y, minlength=2 * r).reshape(r, 2))


def stat_rank_biserial(x, y):
    ranks = rankdata(x)
    n1 = int(y.sum())
    n0 = len(y) - n1
    return abs(2 * ((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) - 1)


def stat_epsilon2(x, y):
    ranks = rankdata(y)
    n = len(y)
    r = int(x.max()) + 1
    cnt = np.bincount(x, minlength=r).astype(float)
    sums = np.bincount(x, weights=ranks, minlength=r)
    m = cnt > 0
    h = 12 / (n * (n + 1)) * np.sum(sums[m] ** 2 / cnt[m]) - 3 * (n + 1)
    return h / (n - 1)


def stat_abs_rho(x, y):
    rx, ry = rankdata(x), rankdata(y)
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return abs(float(np.corrcoef(rx, ry)[0, 1]))


def perm_p(stat_fn, x, y, rng, n_perm: int = N_PERM):
    obs = stat_fn(x, y)
    if not np.isfinite(obs):
        return obs, np.nan
    cnt = 0
    for _ in range(n_perm):
        s = stat_fn(x, rng.permutation(y))
        if np.isfinite(s) and s >= obs - 1e-12:
            cnt += 1
    return obs, (cnt + 1) / (n_perm + 1)


def spearman_matrix_from_ranks(r: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.corrcoef(r, rowvar=False)


def boot_spearman(M: np.ndarray, rng, n_boot: int = N_BOOT) -> np.ndarray:
    n = M.shape[0]
    out = np.empty((n_boot, M.shape[1], M.shape[1]))
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        out[b] = spearman_matrix_from_ranks(rankdata(M[idx], axis=0))
    return out


def surprise_flags(P: np.ndarray, y: np.ndarray, rng, n_sim: int = 500, q: float = 0.95):
    """Flag outcomes whose model probability is below what 95% of model-simulated outcomes would show."""
    n, k = P.shape
    ar = np.arange(n)
    s_obs = -np.log(np.clip(P[ar, y], 1e-12, 1))
    cum = np.cumsum(P, axis=1)
    sims = []
    for _ in range(n_sim):
        ys = np.minimum((rng.random(n)[:, None] > cum).sum(axis=1), k - 1)
        sims.append(-np.log(np.clip(P[ar, ys], 1e-12, 1)))
    thr = float(np.quantile(np.concatenate(sims), q))
    return s_obs, thr, s_obs > thr


def varimax(L: np.ndarray, q: int = 100, tol: float = 1e-7) -> np.ndarray:
    p, k = L.shape
    R = np.eye(k)
    d = 0.0
    for _ in range(q):
        Lr = L @ R
        u, s, vh = np.linalg.svd(L.T @ (Lr ** 3 - Lr @ np.diag(np.diag(Lr.T @ Lr)) / p))
        R = u @ vh
        d_old, d = d, s.sum()
        if d_old != 0 and d / d_old < 1 + tol:
            break
    return L @ R


def exercise_purity(rot: np.ndarray, ex_labels: np.ndarray) -> float:
    assign = np.abs(rot).argmax(axis=1)
    hit = 0
    for comp in np.unique(assign):
        labs = ex_labels[assign == comp]
        hit += pd.Series(labs).value_counts().iloc[0]
    return hit / len(ex_labels)


# -------------------------------------------------------------------------------------------------------- data loading

def load_data(processed_dir: Path):
    c = pd.read_csv(processed_dir / "candidates.csv")
    long = pd.read_csv(processed_dir / "scores_long.csv")
    ex = pd.read_csv(processed_dir / "exercises.csv")
    for col in ("in_screen", "reached_ti", "attended_ac", "hired", "has_resume"):
        c[col] = as_bool(c[col])
    c["candidate_id"] = c["candidate_id"].astype(str)
    long["candidate_id"] = long["candidate_id"].astype(str)
    ex["candidate_id"] = ex["candidate_id"].astype(str)
    c["invited"] = c["screen_invited"].astype(str).str.strip().str.lower().eq("yes")
    c["screen_score"] = pd.to_numeric(c["screen_score"], errors="coerce")
    c["ac_total"] = pd.to_numeric(c["ac_total"], errors="coerce")
    c["decision"] = c["decision"].where(c["decision"].isin(DECISIONS))
    return c, long, ex


# ================================================================================================== FUNNEL SECTION

def proxy_fields(c: pd.DataFrame) -> dict:
    year = c["proxy_graduation"].astype(str).str.extract(r"((?:19|20)\d{2})")[0].astype(float)
    skills = c["proxy_skills_tag"].fillna("(none listed)").astype(str)
    city = c["proxy_home_city"].fillna("(none listed)").astype(str)
    return {
        "Graduation year": ("ord", year),
        "Home city": ("cat", city),
        "Skills tag": ("cat", skills),
        "Has resume": ("cat", c["has_resume"].map({True: "has resume", False: "no resume"})),
    }


def proxy_scan(c: pd.DataFrame, ti_pct: pd.Series, ac_pct: pd.Series) -> pd.DataFrame:
    rng = rng_for(11)
    fields = proxy_fields(c)
    cid = c["candidate_id"]
    outcomes = [
        ("Reached TI (of all in screening)", c["in_screen"], c["reached_ti"].astype(int), "bin"),
        ("Invited after TI (of those who reached TI)", c["reached_ti"], c["invited"].astype(int), "bin"),
        ("Hired (of those who attended the AC)", c["attended_ac"], c["hired"].astype(int), "bin"),
        ("TI score rank (reached TI)", c["reached_ti"], cid.map(ti_pct), "cont"),
        ("AC total rank (attended AC)", c["attended_ac"], cid.map(ac_pct), "cont"),
    ]
    rows = []
    for fname, (ftype, fvals) in fields.items():
        for oname, cohort, y, ytype in outcomes:
            m = cohort & fvals.notna() & pd.Series(y).notna().to_numpy() if ytype == "cont" else cohort & fvals.notna()
            m = m.to_numpy()
            n = int(m.sum())
            yv = pd.Series(y).to_numpy()[m]
            xv = fvals[m]
            if n < 10 or (ytype == "bin" and (yv.sum() == 0 or yv.sum() == n)):
                rows.append({"field": fname, "outcome": oname, "n": n, "statistic": None, "stat": np.nan,
                             "p_perm": np.nan, "p_asym": np.nan})
                continue
            if ftype == "cat":
                codes = pd.factorize(xv)[0]
                if codes.max() < 1:
                    continue
                if ytype == "bin":
                    yi = yv.astype(int)
                    sname, fn = "Cramer's V (bias-corrected)", stat_v
                    table = np.bincount(codes * 2 + yi, minlength=2 * (codes.max() + 1)).reshape(-1, 2)
                    table = table[table.sum(axis=1) > 0]
                    p_asym = stats.chi2_contingency(table, correction=False)[1]
                    obs, pp = perm_p(fn, codes, yi, rng)
                else:
                    yf = yv.astype(float)
                    sname, fn = "Kruskal epsilon-squared", stat_epsilon2
                    p_asym = stats.kruskal(*[yf[codes == g] for g in np.unique(codes)]).pvalue
                    obs, pp = perm_p(fn, codes, yf, rng)
            else:
                xf = xv.to_numpy(float)
                if len(np.unique(xf)) < 2:
                    continue
                if ytype == "bin":
                    yi = yv.astype(int)
                    sname, fn = "Rank-biserial |r|", stat_rank_biserial
                    p_asym = stats.mannwhitneyu(xf[yi == 1], xf[yi == 0]).pvalue
                    obs, pp = perm_p(fn, xf, yi, rng)
                else:
                    yf = yv.astype(float)
                    sname, fn = "Spearman |rho|", stat_abs_rho
                    p_asym = stats.spearmanr(xf, yf).pvalue
                    obs, pp = perm_p(fn, xf, yf, rng)
            rows.append({"field": fname, "outcome": oname, "n": n, "statistic": sname, "stat": obs, "p_perm": pp,
                         "p_asym": float(p_asym)})
    df = pd.DataFrame(rows)
    df["q_bh"] = bh(df["p_perm"].to_numpy())
    strengths = []
    for _, r in df.iterrows():
        if not np.isfinite(r["p_perm"]):
            strengths.append(None)
            continue
        strengths.append(grade([r["q_bh"] < 0.05, r["p_perm"] < 0.01, r["p_asym"] < 0.05], int(r["n"])))
    df["strength"] = strengths
    return df


def build_funnel(c: pd.DataFrame) -> tuple[Doc, dict]:
    ti_pct = pct_rank(c.loc[c["reached_ti"], ["candidate_id", "screen_score"]].set_index("candidate_id")["screen_score"])
    att = c[c["attended_ac"] & c["decision"].notna() & c["ac_total"].notna()]
    ac_pct = pct_rank(att.set_index("candidate_id")["ac_total"])
    cid = c["candidate_id"]
    c = c.assign(ti_pct=cid.map(ti_pct) * 100, ac_pct=cid.map(ac_pct) * 100)

    n_scr = int(c["in_screen"].sum())
    n_ti = int((c["in_screen"] & c["reached_ti"]).sum())
    n_inv = int((c["reached_ti"] & c["invited"]).sum())
    n_att = int(c["attended_ac"].sum())
    dec_n = {d: int((c["decision"] == d).sum()) for d in DECISIONS}
    n_dec = sum(dec_n.values())

    doc = Doc("funnel", "Hiring funnel", [
        "Outcomes (reached TI, invited, attended, decision) are past human decisions, not measures of job performance; "
        "findings describe what the process rewarded.",
        "Later-stage scores exist only for candidates who passed earlier gates and are never imputed. Comparisons at the "
        "assessment-center stage are range-restricted to people who reached it.",
        "Percentile ranks are within-cohort mid-ranks (0-100): the TI rank is computed among everyone with a TI score and the "
        "AC rank among assessment-center attendees, so the two scales are not directly comparable levels.",
        "Proxy-risk fields (graduation year, home city, skills tag, resume on file) are checked as possible sources of bias, "
        "not as legitimate selection features. With small cells these tests have low power; a null result is not proof of "
        "no bias.",
        "Groups with fewer than 5 candidates are suppressed in the shareable copy; candidate ids appear only in the local copy.",
    ])

    # ---- stage counts and conversion
    stages = [("In screening", n_scr), ("Reached TI", n_ti), ("Invited / advanced", n_inv), ("Attended assessment center", n_att)]
    doc.chart("funnel-stages", "bar", "Candidates at each stage", {
        "labels": [s for s, _ in stages], "series": [{"name": "Candidates", "values": [n for _, n in stages]}],
        "suppressed": [n < MIN_GROUP for _, n in stages]},
        y_label="Candidates", share={
        "labels": [s for s, _ in stages],
        "series": [{"name": "Candidates", "values": [n if n >= MIN_GROUP else None for _, n in stages]}],
        "suppressed": [n < MIN_GROUP for _, n in stages]})
    dec_labels = [f"Decision: {d}" for d in DECISIONS[::-1]]
    dec_vals = [dec_n[d] for d in DECISIONS[::-1]]
    doc.chart("funnel-decisions", "bar", "Final decision groups (assessment-center attendees)", {
        "labels": dec_labels, "series": [{"name": "Candidates", "values": dec_vals}],
        "suppressed": [v < MIN_GROUP for v in dec_vals]}, y_label="Candidates", share={
        "labels": dec_labels, "series": [{"name": "Candidates", "values": [v if v >= MIN_GROUP else None for v in dec_vals]}],
        "suppressed": [v < MIN_GROUP for v in dec_vals]})

    gate_defs = [
        ("Screening -> reached TI", n_scr, n_ti),
        ("TI -> invited", n_ti, n_inv),
        ("Invited -> attended AC", n_inv, int((c["invited"] & c["attended_ac"]).sum())),
        ("AC -> Hire", n_dec, dec_n["Hire"]),
        ("AC -> Hire or Standby", n_dec, dec_n["Hire"] + dec_n["Standby"]),
    ]
    rng = rng_for(1)

    # ---- score-rank selection per gate (AUC of within-cohort percentile rank, no cutoff)
    ti_c = c[c["reached_ti"]]
    gate_auc: dict[str, dict | None] = {}
    gate_auc["TI -> invited"] = auc_test(ti_c.loc[ti_c["invited"], "ti_pct"], ti_c.loc[~ti_c["invited"], "ti_pct"], rng)
    inv_c = c[c["invited"] & c["reached_ti"]]
    gate_auc["Invited -> attended AC"] = auc_test(inv_c.loc[inv_c["attended_ac"], "ti_pct"],
                                                  inv_c.loc[~inv_c["attended_ac"], "ti_pct"], rng)
    gate_auc["AC -> Hire"] = auc_test(att.loc[att["decision"] == "Hire", "candidate_id"].map(ac_pct),
                                      att.loc[att["decision"] != "Hire", "candidate_id"].map(ac_pct), rng)
    gate_auc["AC -> Hire or Standby"] = auc_test(att.loc[att["decision"] != "No Hire", "candidate_id"].map(ac_pct),
                                                 att.loc[att["decision"] == "No Hire", "candidate_id"].map(ac_pct), rng)
    gate_auc["AC -> Hire (TI rank, range-restricted)"] = auc_test(
        att.loc[att["decision"] == "Hire", "candidate_id"].map(ti_pct),
        att.loc[att["decision"] != "Hire", "candidate_id"].map(ti_pct), rng)
    gate_auc["AC -> Hire or Standby (TI rank, range-restricted)"] = auc_test(
        att.loc[att["decision"] != "No Hire", "candidate_id"].map(ti_pct),
        att.loc[att["decision"] == "No Hire", "candidate_id"].map(ti_pct), rng)
    names = [k for k, v in gate_auc.items() if v is not None]
    qs = dict(zip(names, bh([gate_auc[k]["p_perm"] for k in names])))
    for k in names:
        g = gate_auc[k]
        g["q"] = qs[k]
        g["strength"] = grade([g["lo"] > 0.5 or g["hi"] < 0.5, g["q"] < 0.05, g["p_mwu"] < 0.05], min(g["n_pos"], g["n_neg"]))

    # ---- gate table
    gate_rows = []
    for name, at_risk, through in gate_defs:
        lo, hi = wilson(through, at_risk)
        score_key = name
        g = gate_auc.get(score_key)
        gate_rows.append([name, at_risk, through, rd(100 * through / at_risk if at_risk else np.nan, 1),
                          rd(100 * lo, 1), rd(100 * hi, 1),
                          rd(g["auc"]) if g else None, rd(g["lo"]) if g else None, rd(g["hi"]) if g else None,
                          rd(g["p_perm"], 4) if g else None, rd(g["q"], 4) if g else None, g["strength"] if g else None,
                          "TI percentile" if name.startswith(("TI", "Invited")) else ("AC total percentile" if g else "no score for non-reachers"),
                          False])
    for k in ("AC -> Hire (TI rank, range-restricted)", "AC -> Hire or Standby (TI rank, range-restricted)"):
        g = gate_auc[k]
        base = "AC -> Hire" if "or Standby" not in k else "AC -> Hire or Standby"
        at_risk, through = next((a, t) for n_, a, t in gate_defs if n_ == base)
        gate_rows.append([k, at_risk, through, rd(100 * through / at_risk, 1), None, None, rd(g["auc"]), rd(g["lo"]),
                          rd(g["hi"]), rd(g["p_perm"], 4), rd(g["q"], 4), g["strength"], "TI percentile (earlier stage)", False])
    gate_cols = ["Gate", "n at risk", "n through", "Conversion %", "Conv. CI low", "Conv. CI high", "Score-rank AUC",
                 "AUC CI low", "AUC CI high", "Perm. p", "BH q", "Strength", "Score used", "suppressed"]
    share_rows = []
    for r in gate_rows:
        small = r[1] < MIN_GROUP or r[2] < MIN_GROUP
        g = gate_auc.get(r[0])
        if g is not None and min(g["n_pos"], g["n_neg"]) < MIN_GROUP:
            small = True
        if small:
            share_rows.append([r[0]] + [None] * 12 + [True])
        else:
            share_rows.append(r)
    doc.chart("gate-table", "table", "Stage-to-stage conversion and how strongly each gate follows score rank",
              {"columns": gate_cols, "rows": gate_rows}, subtitle="AUC 0.5 = score rank unrelated to passing the gate; "
              "1.0 = everyone who passed outranks everyone who did not. No score cutoff is assumed.", share={"columns": gate_cols, "rows": share_rows})

    rank_names = [k for k in ("TI -> invited", "Invited -> attended AC", "AC -> Hire", "AC -> Hire or Standby")
                  if gate_auc[k] is not None]
    hb_labels = rank_names + [k for k in gate_auc if "range-restricted" in k and gate_auc[k] is not None]
    hb_vals = [rd(gate_auc[k]["auc"]) for k in hb_labels]
    doc.chart("gate-selection", "hbar", "Score-rank selectivity of each gate (AUC)", {
        "labels": hb_labels, "series": [{"name": "AUC of within-cohort percentile rank", "values": hb_vals}]},
        x_label="AUC (0.5 = no selection on score rank)")

    # ---- advance vs not on TI rank
    tadv = [("Not invited", ti_c.loc[~ti_c["invited"], "ti_pct"]), ("Invited", ti_c.loc[ti_c["invited"], "ti_pct"])]
    boxes = [box_stats(f"{n_}", v) for n_, v in tadv]
    doc.chart("ti-rank-by-advance", "boxplot", "TI percentile rank: invited vs not invited", {"groups": boxes},
              subtitle="Cohort = everyone with a TI score; overlap of the boxes shows how many invited candidates ranked below "
              "non-invited ones.", y_label="TI percentile rank (0-100)", share={"groups": suppress_boxes(boxes)})
    boxes = [box_stats(n_, ti_c.loc[ti_c["invited"] == flag, "screen_score"]) for n_, flag in (("Not invited", False), ("Invited", True))]
    doc.chart("ti-score-by-advance", "boxplot", "TI raw score: invited vs not invited", {"groups": boxes},
              y_label="TI score", share={"groups": suppress_boxes(boxes)})
    boxes = [box_stats(d, att.loc[att["decision"] == d, "candidate_id"].map(ti_pct) * 100) for d in DECISIONS]
    doc.chart("ti-rank-by-decision", "boxplot", "TI percentile rank by final decision (range-restricted to AC attendees)",
              {"groups": boxes}, y_label="TI percentile rank (0-100, among all with a TI score)", share={"groups": suppress_boxes(boxes)})

    # ---- findings: counts and narrowing
    conv = [(gate_defs[i][0], gate_defs[i][2] / gate_defs[i][1] if gate_defs[i][1] else np.nan, gate_defs[i][1], gate_defs[i][2])
            for i in range(3)]
    lost = [(n_, a - t, a, t) for n_, a, t in gate_defs[:3]]
    worst_rate = min((x for x in conv if np.isfinite(x[1])), key=lambda x: x[1])
    worst_abs = max(lost, key=lambda x: x[1])
    lo, hi = wilson(worst_rate[3], worst_rate[2])
    doc.finding(
        f"The process narrows most at '{worst_rate[0]}' (conversion {worst_rate[1]:.0%}); "
        + (f"that is also the largest absolute loss ({worst_abs[1]} candidates). " if worst_abs[0] == worst_rate[0] else
           f"the largest absolute loss is at '{worst_abs[0]}' ({worst_abs[1]} candidates). ")
        + f"Overall {n_scr} candidates in screening, {n_ti} reached TI, "
        f"{n_inv} were invited, {n_att} attended the assessment center, and {dec_n['Hire']} received Hire, "
        f"{dec_n['Standby']} Standby, {dec_n['No Hire']} No Hire.",
        "robust", f"n={n_scr}; conversion at narrowest gate {worst_rate[3]}/{worst_rate[2]} (Wilson 95% CI {lo:.0%}-{hi:.0%}); exact counts")

    # ---- findings: gate selectivity
    own = [k for k in rank_names]
    if len(own) >= 2:
        order = sorted(own, key=lambda k: gate_auc[k]["auc"], reverse=True)
        top, bot = order[0], order[-1]
        gt, gb = gate_auc[top], gate_auc[bot]
        diff = gt["boots"] - gb["boots"]
        dlo, dhi = np.percentile(diff, [2.5, 97.5])
        st = "robust" if (dlo > 0 and gt["strength"] == "robust") else ("suggestive" if dlo > 0 else "weak")
        doc.finding(
            f"On score rank, '{top}' is the most score-driven gate (AUC {gt['auc']:.2f}, CI {gt['lo']:.2f}-{gt['hi']:.2f}) and "
            f"'{bot}' the least (AUC {gb['auc']:.2f}, CI {gb['lo']:.2f}-{gb['hi']:.2f}). Gates are compared on the score each "
            "stage had in hand (TI rank for the TI and invitation gates, assessment-center rank for the decision gates); the "
            "assessment-center gates are range-restricted."
            + ("" if dlo > 0 else " The difference between these two gates is within sampling noise, so they cannot be ranked with confidence."),
            st, f"n={gt['n_pos'] + gt['n_neg']} vs {gb['n_pos'] + gb['n_neg']}; AUC difference {gt['auc'] - gb['auc']:.2f} "
                f"(bootstrap CI {dlo:.2f} to {dhi:.2f}); top gate perm. p={gt['p_perm']:.4f}, BH q={gt['q']:.4f}")
    g2 = gate_auc["TI -> invited"]
    if g2:
        doc.finding(
            f"Invited candidates had higher TI percentile ranks than non-invited ones (median {box_stats('i', tadv[1][1])['median']:.0f} vs "
            f"{box_stats('n', tadv[0][1])['median']:.0f}), but the distributions overlap: a random non-invited candidate outranked a random "
            f"invited one in {1 - g2['auc']:.0%} of pairs.",
            g2["strength"], f"n={g2['n_pos']} invited vs {g2['n_neg']} not; AUC {g2['auc']:.2f} (bootstrap CI {g2['lo']:.2f}-{g2['hi']:.2f}); "
                            f"perm. p={g2['p_perm']:.4f}, Mann-Whitney p={g2['p_mwu']:.2g}")
    if gate_auc["Invited -> attended AC"] is None:
        doc.finding("Everyone who was invited attended the assessment center in this data, so that gate shows no attrition and "
                    "cannot be compared on score rank.", "robust",
                    f"n={n_inv} invited, {gate_defs[2][2]} attended")

    # ---- screening alignment: Pass/Fail and Status vs TI score
    t = ti_c.copy()
    pf = t["screen_passfail"].astype(str).str.strip().str.title()
    pass_s = t.loc[pf == "Pass", "screen_score"].to_numpy(float)
    fail_s = t.loc[pf == "Fail", "screen_score"].to_numpy(float)
    rng2 = rng_for(2)
    auc_pf = auc_test(pass_s, fail_s, rng2)
    if auc_pf:
        auc_pf["strength"] = grade([auc_pf["lo"] > 0.5, auc_pf["p_perm"] < 0.05, auc_pf["p_mwu"] < 0.05],
                                   min(auc_pf["n_pos"], auc_pf["n_neg"]))
    inversions = int((fail_s[None, :] >= pass_s[:, None]).sum()) if len(pass_s) and len(fail_s) else 0
    pairs = len(pass_s) * len(fail_s)
    status_adv = c["screen_status"].astype(str).str.contains("Sent Assessment Center", case=False)
    status_withdrew = c["screen_status"].astype(str).str.contains("not interested", case=False)

    # model: probability of invitation given TI percentile (logistic); outliers via simulated fence
    X = (t["ti_pct"].to_numpy() / 100).reshape(-1, 1)
    yv = t["invited"].astype(int).to_numpy()
    lr = LogisticRegression(C=1e6, max_iter=2000).fit(X, yv)
    P = lr.predict_proba(X)
    s_obs, thr, flag = surprise_flags(P, yv, rng_for(3))
    t = t.assign(p_obs=P[np.arange(len(yv)), yv], surprise=s_obs, model_flag=flag)

    pf_inv = (pf == "Pass") & ~t["invited"] | (pf == "Fail") & t["invited"]
    status_mis = status_adv.loc[t.index] != t["invited"]
    no_ti_status = c["in_screen"] & ~c["reached_ti"] & status_adv
    sc = t["screen_score"].to_numpy(float)
    pf_arr = pf.to_numpy()
    inv_count = np.zeros(len(t), int)
    for i in range(len(t)):
        if pf_arr[i] == "Pass":
            inv_count[i] = int((fail_s >= sc[i]).sum())
        elif pf_arr[i] == "Fail":
            inv_count[i] = int((pass_s <= sc[i]).sum())
    t["pf_inverted"] = inv_count > 0

    reasons: dict[str, list[str]] = {}

    def add_reason(ids, text):
        for i in ids:
            reasons.setdefault(i, []).append(text)

    add_reason(t.loc[pf_inv, "candidate_id"], "Pass/Fail and invited disagree")
    add_reason(t.loc[status_mis & ~pf_inv, "candidate_id"], "Status and invited disagree")
    add_reason(t.loc[t["pf_inverted"], "candidate_id"], "Pass/Fail contradicted by TI score ordering")
    add_reason(t.loc[t["model_flag"], "candidate_id"], "Invitation unlikely given TI rank (model fence)")
    add_reason(c.loc[no_ti_status, "candidate_id"], "Status says instructions sent but no TI score and never attended")
    n_pf_inv = int(pf_inv.sum())
    n_status_mis = int(status_mis.sum())
    n_noti = int(no_ti_status.sum())
    n_model = int(t["model_flag"].sum())
    dis_ids = sorted(reasons)
    n_dis = len(dis_ids)
    cm = c.set_index("candidate_id")
    dis_rows = []
    for i in dis_ids:
        r = cm.loc[i]
        tr = t.set_index("candidate_id").loc[i] if i in set(t["candidate_id"]) else None
        dis_rows.append([i, rd(r["screen_score"], 1), rd(r["ti_pct"], 1), r["screen_passfail"] if isinstance(r["screen_passfail"], str) else None,
                         "Yes" if r["invited"] else ("No" if r["reached_ti"] else None), r["screen_status"] if isinstance(r["screen_status"], str) else None,
                         bool(r["attended_ac"]), rd(tr["p_obs"]) if tr is not None else None, "; ".join(reasons[i])])
    doc.chart("screen-disagreements", "table", "Screening records out of line with the TI score (local only)", {
        "columns": ["candidate_id", "TI score", "TI percentile", "Pass/Fail", "Invited", "Status", "Attended AC",
                    "Model P(observed invite outcome)", "Reason(s)"], "rows": dis_rows},
        subtitle="Includes disagreements between fields, and invitations unlikely under a logistic model of invitation on TI rank.",
        local_only=True)
    reason_counts = [
        ("Pass/Fail and invited disagree", n_pf_inv), ("Status and invited disagree", n_status_mis),
        ("Pass/Fail contradicted by TI score ordering", int(t["pf_inverted"].sum())),
        ("Invitation unlikely given TI rank (model fence)", n_model),
        ("Status says instructions sent but no TI score and never attended", n_noti),
        ("Any of the above (unique candidates)", n_dis),
    ]
    doc.chart("screen-agreement", "table", "How well Pass/Fail and Status line up with the TI score",
              {"columns": ["Check", "Candidates", "suppressed"], "rows": [[a, b, False] for a, b in reason_counts]},
              share={"columns": ["Check", "Candidates", "suppressed"],
                     "rows": [[a, (b if (b == 0 or b >= MIN_GROUP) else None), (0 < b < MIN_GROUP)] for a, b in reason_counts]})

    if auc_pf:
        lo_p = pass_s.min()
        hi_f = fail_s.max()
        sep = f"lowest Pass score {lo_p:.0f} vs highest Fail score {hi_f:.0f}"
        doc.finding(
            f"Screening Pass/Fail follows TI score closely (AUC {auc_pf['auc']:.2f}); {inversions} of {pairs} Pass/Fail pairs have the "
            f"Fail candidate scoring at or above the Pass candidate ({sep}). "
            + ("The two groups do not overlap, so the sheet behaves like a fixed TI score line even though the analysis imposes none."
               if inversions == 0 else "The groups overlap, so Pass/Fail is not a pure function of the TI score."),
            auc_pf["strength"], f"n={len(pass_s)} Pass, {len(fail_s)} Fail; AUC CI {auc_pf['lo']:.2f}-{auc_pf['hi']:.2f}; "
                                f"perm. p={auc_pf['p_perm']:.4f}")
    doc.finding(
        f"{n_dis} candidate(s) have a screening record that disagrees with the TI score or with another screening field "
        f"({n_pf_inv} where Pass/Fail and the invitation disagree, {n_model} where the invitation is unlikely under a model on TI rank, "
        f"{n_noti} whose Status says instructions were sent although no TI score exists and they never attended). Candidate ids are in the local copy only.",
        "suggestive", f"n={len(t)} with a TI score; model-fence threshold on -log P = {thr:.2f} (95th percentile of model-simulated outcomes)",
        share_text=f"{share_count(n_dis)} candidate(s) have a screening record that disagrees with the TI score or with another screening field; "
                   "details are in the local copy only.",
        share_evidence=f"n={len(t)} with a TI score; flagged by field disagreement or by a model-simulated 95% fence")

    # ---- proxy-risk scan
    scan = proxy_scan(c, ti_pct, ac_pct)
    scan_ok = scan[scan["stat"].notna()].copy().sort_values("p_perm")
    rows = [[r.field, r.outcome, int(r.n), r.statistic, rd(r.stat), rd(r.p_perm, 4), rd(r.q_bh, 4), rd(r.p_asym, 4), r.strength]
            for r in scan_ok.itertuples()]
    doc.chart("proxy-tests", "table", "Bias check: association of proxy-risk fields with advancing and score rank", {
        "columns": ["Proxy field", "Outcome (cohort)", "n", "Statistic", "Effect size", "Permutation p", "BH q (all tests)",
                    "Asymptotic p", "Strength"], "rows": rows},
        subtitle="Effect sizes are 0 = none. These are checks for possible bias, not selection features. BH correction applies across all tests shown.")
    if len(scan_ok):
        doc.chart("proxy-effects", "hbar", "Strength of proxy-field association (effect size)", {
            "labels": [f"{r.field}: {r.outcome.split(' (')[0]}" for r in scan_ok.head(12).itertuples()],
            "series": [{"name": "Effect size", "values": [rd(v) for v in scan_ok.head(12)["stat"]]}]},
            subtitle="Twelve strongest of the tests; see table for p-values and corrections.", x_label="Effect size (not comparable across statistics)")
    sig = scan_ok[scan_ok["strength"].isin(["robust", "suggestive"])]
    if len(sig):
        best = sig.iloc[0]
        doc.finding(
            f"Bias check: {len(sig)} of {len(scan_ok)} proxy-field tests show an association worth a closer look, the strongest being "
            f"{best.field} vs '{best.outcome}'. This is a flag for review, not evidence of discrimination.",
            best.strength, f"n={int(best.n)}; {best.statistic}={best.stat:.2f}; permutation p={best.p_perm:.4f}, BH q={best.q_bh:.3f}, asymptotic p={best.p_asym:.3f}")
    else:
        minq = scan_ok["q_bh"].min() if len(scan_ok) else np.nan
        doc.finding(
            f"Bias check: none of {len(scan_ok)} tests of the proxy-risk fields (graduation year, home city, skills tag, resume on file) against "
            f"reaching TI, invitation, hire or score rank survives multiple-testing correction. Small cells mean low power, so this does not rule out bias.",
            "weak", f"n={int(scan_ok['n'].min())}-{int(scan_ok['n'].max())} per test; smallest BH q={minq:.2f} across {len(scan_ok)} tests; "
                    f"permutation p-values with {N_PERM} permutations")

    # ---- proxy rate table at the TI -> invite gate
    fields = proxy_fields(c)
    prow = []
    for fname, (ftype, fvals) in fields.items():
        g = pd.DataFrame({"f": fvals, "inv": c["invited"], "ti": c["ti_pct"]})[c["reached_ti"] & fvals.notna()]
        if ftype == "ord":
            g["f"] = g["f"].astype(int).astype(str)
        for lab, sub in sorted(g.groupby("f"), key=lambda kv: kv[0]):
            n = len(sub)
            k = int(sub["inv"].sum())
            lo_, hi_ = wilson(k, n)
            prow.append([fname, str(lab), n, k, rd(100 * k / n, 1), rd(100 * lo_, 1), rd(100 * hi_, 1), rd(sub["ti"].median(), 1), False])
    pcols = ["Proxy field", "Group", "n (reached TI)", "n invited", "Invited %", "CI low", "CI high", "Median TI percentile", "suppressed"]
    doc.chart("proxy-rates", "table", "Invitation rate and TI rank by proxy-field group", {"columns": pcols, "rows": prow},
              subtitle="Compare invitation rate with median TI percentile: a group with a lower rate but similar rank is worth reviewing.",
              share={"columns": pcols, "rows": suppress_rows(prow, 2, 2, 8)})
    return doc, {"ti_pct": ti_pct, "ac_pct": ac_pct}


# ============================================================================================== STRUCTURE SECTION

def williams_perm(a, b, c, rng, n_perm: int = N_PERM):
    """Test rho(a,b) > rho(a,c) for dependent correlations (Williams t and exchange-permutation of b/c)."""
    n = len(a)
    ra, rb, rc = rankdata(a), rankdata(b), rankdata(c)

    def rho(x, y):
        return float(np.corrcoef(x, y)[0, 1])

    r12, r13, r23 = rho(ra, rb), rho(ra, rc), rho(rb, rc)
    d = r12 - r13
    detR = 1 - r12 ** 2 - r13 ** 2 - r23 ** 2 + 2 * r12 * r13 * r23
    rbar = (r12 + r13) / 2
    t = d * np.sqrt((n - 1) * (1 + r23) / (2 * (n - 1) / (n - 3) * detR + rbar ** 2 * (1 - r23) ** 3))
    p_w = 2 * stats.t.sf(abs(t), n - 3)
    cnt = 0
    for _ in range(n_perm):
        sw = rng.random(n) < 0.5
        b2 = np.where(sw, c, b)
        c2 = np.where(sw, b, c)
        dd = rho(ra, rankdata(b2)) - rho(ra, rankdata(c2))
        if abs(dd) >= abs(d) - 1e-12:
            cnt += 1
    return d, float(p_w), (cnt + 1) / (n_perm + 1)


def build_structure(c: pd.DataFrame, long: pd.DataFrame, ex: pd.DataFrame) -> Doc:
    cm = c.set_index("candidate_id")
    comp_wide = long.pivot_table(index="candidate_id", columns=["exercise", "competency"], values="score", aggfunc="first")
    comp_cols = [(e, k) for e in EXERCISES for k in sorted({k for ee, k in comp_wide.columns if ee == e})]
    comp_labels = [f"{k} [{ABBR[e]}]" for e, k in comp_cols]
    totals = ex.pivot_table(index="candidate_id", columns="exercise", values="total", aggfunc="first")[list(EXERCISES)]

    V = pd.DataFrame(index=cm.index)
    V["TI score"] = cm["screen_score"]
    for e in EXERCISES:
        V[EXERCISE_TOTAL_LABEL[e]] = totals[e].reindex(V.index)
    for (e, k), lab in zip(comp_cols, comp_labels):
        V[lab] = comp_wide[(e, k)].reindex(V.index)
    var_names = list(V.columns)
    A = V[V[[EXERCISE_TOTAL_LABEL[e] for e in EXERCISES]].notna().all(axis=1)]
    n_ac = len(A)
    ti_all = cm["screen_score"].dropna()
    sd_ratio = float(A["TI score"].std() / ti_all.std()) if n_ac > 1 and len(ti_all) > 1 else np.nan

    doc = Doc("structure", "Score structure and decision alignment", [
        "Assessment-center scores exist only for the candidates who passed the screening gates, so every correlation involving "
        f"them is range-restricted (TI scores among attendees have {sd_ratio:.0%} of the spread seen among all TI takers) and "
        "understates what a full applicant pool would show. Nothing is imputed.",
        "Scores are 1-4 per competency, so ties are heavy; Spearman correlations and mid-rank percentiles handle ties but have "
        "limited resolution. Percentile ranks are within-instrument and within-cohort.",
        "With a few dozen candidates, correlations and clusters are imprecise: read the bootstrap intervals, not the point values.",
        "The final decision was made by people who saw the exercise scores, so decision-versus-score agreement is partly circular; "
        "it shows how consistently the process followed the scores, not whether scores or decisions are right.",
        "Outcomes are past human decisions, not job performance. Clusters are derived from the data and described afterwards; "
        "they are not predefined categories. About 5% of candidates would be flagged by the model fence even if the process were "
        "perfectly consistent with the model.",
        "Groups with fewer than 5 candidates are suppressed in the shareable copy; candidate ids appear only in the local copy.",
    ])
    rng = rng_for(21)

    # ---- within-instrument percentile ranks
    inst_rows = []
    for name in var_names:
        s = V[name].dropna()
        if len(s) == 0:
            continue
        vc = s.value_counts(normalize=True)
        inst_rows.append([name, int(len(s)), rd(s.min(), 1), rd(s.median(), 1), rd(s.max(), 1), int(s.nunique()),
                          rd(100 * vc.iloc[0], 1), rd(100 * pct_rank(s).std(), 1), False])
    icols = ["Instrument", "n scored", "Min", "Median", "Max", "Distinct values", "% at most common value",
             "SD of percentile rank", "suppressed"]
    doc.chart("instrument-ranks", "table", "Instruments converted to within-instrument percentile ranks",
              {"columns": icols, "rows": inst_rows},
              subtitle="Each instrument is ranked only among the candidates who took it. A high share at one value means many ties and coarser ranks.",
              share={"columns": icols, "rows": suppress_rows(inst_rows, 1, 1, 8)})

    # ---- Spearman heatmap (pairwise complete) and bootstrap
    R = V.corr(method="spearman", min_periods=MIN_GROUP)
    npair = V.notna().astype(int).T @ V.notna().astype(int)
    doc.chart("spearman-heatmap", "heatmap", "Spearman rank correlations: TI score, exercise totals and competencies", {
        "row_labels": var_names, "col_labels": var_names,
        "values": [[rd(R.loc[a, b], 2) for b in var_names] for a in var_names], "min": -1, "max": 1},
        subtitle=f"Pairwise-complete rank correlations, n per pair {int(npair.to_numpy().min())}-{int(npair.to_numpy().max())}. "
                 "Competency labels show the exercise in brackets.")

    Mfull = V.dropna()
    Mnp = Mfull.to_numpy(float)
    boot = boot_spearman(Mnp, rng)
    idx = {n_: i for i, n_ in enumerate(var_names)}
    nfull = len(Mfull)

    pair_rows = []
    pairs_ex = [("TI score", EXERCISE_TOTAL_LABEL["Interview"]), ("TI score", EXERCISE_TOTAL_LABEL["Role Play"]),
                ("TI score", EXERCISE_TOTAL_LABEL["Presentation"]),
                (EXERCISE_TOTAL_LABEL["Interview"], EXERCISE_TOTAL_LABEL["Role Play"]),
                (EXERCISE_TOTAL_LABEL["Interview"], EXERCISE_TOTAL_LABEL["Presentation"]),
                (EXERCISE_TOTAL_LABEL["Role Play"], EXERCISE_TOTAL_LABEL["Presentation"])]
    for a, b in pairs_ex:
        lo, hi = np.percentile(boot[:, idx[a], idx[b]], [2.5, 97.5])
        pair_rows.append([f"{a} vs {b}", nfull, rd(R.loc[a, b], 3), rd(lo, 3), rd(hi, 3), False])
    pcols = ["Pair", "n", "Spearman rho", "CI low", "CI high", "suppressed"]
    doc.chart("exercise-rank-correlations", "table", "Rank agreement between TI score and the three exercises",
              {"columns": pcols, "rows": pair_rows}, subtitle="Bootstrap 95% CI over candidates; TI pairs are range-restricted.",
              share={"columns": pcols, "rows": suppress_rows(pair_rows, 1, 1, 5)})

    # exercise-pair comparisons
    I, RPl, P = (Mfull[EXERCISE_TOTAL_LABEL[e]].to_numpy(float) for e in EXERCISES)
    ii, ir, ip = (idx[EXERCISE_TOTAL_LABEL[e]] for e in EXERCISES)
    rho_ir = R.loc[EXERCISE_TOTAL_LABEL["Interview"], EXERCISE_TOTAL_LABEL["Role Play"]]
    rho_ip = R.loc[EXERCISE_TOTAL_LABEL["Interview"], EXERCISE_TOTAL_LABEL["Presentation"]]
    rho_rp = R.loc[EXERCISE_TOTAL_LABEL["Role Play"], EXERCISE_TOTAL_LABEL["Presentation"]]
    d1_boot = boot[:, ii, ir] - boot[:, ii, ip]
    d2_boot = boot[:, ii, ir] - boot[:, ir, ip]
    d1, pw1, pp1 = williams_perm(I, RPl, P, rng)
    d2, pw2, pp2 = williams_perm(RPl, I, P, rng)
    ci1 = np.percentile(d1_boot, [2.5, 97.5])
    ci2 = np.percentile(d2_boot, [2.5, 97.5])
    chk1 = [ci1[0] > 0, pw1 < 0.05, pp1 < 0.05]
    chk2 = [ci2[0] > 0, pw2 < 0.05, pp2 < 0.05]
    comb_boot = boot[:, ii, ir] - (boot[:, ii, ip] + boot[:, ir, ip]) / 2
    comb_ci = np.percentile(comb_boot, [2.5, 97.5])
    comb = rho_ir - (rho_ip + rho_rp) / 2
    strength = grade([comb_ci[0] > 0, min(pw1, pw2) < 0.05, min(pp1, pp2) < 0.05], nfull)
    doc.finding(
        f"Interview and Role Play ranks agree with each other (rho {rho_ir:.2f}) more than either agrees with Presentation "
        f"(Interview-Presentation {rho_ip:.2f}, Role Play-Presentation {rho_rp:.2f}), "
        + ("so Presentation reflects partly separate signal." if strength != "weak" else
           "which hints that Presentation reflects partly separate signal, but with this sample the gap is not statistically reliable."),
        strength,
        f"n={nfull}; Int-RP minus mean of the two Presentation pairs = {comb:.2f} (bootstrap CI {comb_ci[0]:.2f} to {comb_ci[1]:.2f}); "
        f"rho difference {d1:.2f} (CI {ci1[0]:.2f} to {ci1[1]:.2f}) and {d2:.2f} (CI {ci2[0]:.2f} to {ci2[1]:.2f}); "
        f"Williams p={pw1:.3g} / {pw2:.3g}; exchange-permutation p={pp1:.4f} / {pp2:.4f}")

    rho_ti = {e: R.loc["TI score", EXERCISE_TOTAL_LABEL[e]] for e in EXERCISES}
    ti_ci = {e: np.percentile(boot[:, idx["TI score"], idx[EXERCISE_TOTAL_LABEL[e]]], [2.5, 97.5]) for e in EXERCISES}
    best_e = max(EXERCISES, key=lambda e: abs(rho_ti[e]))
    doc.finding(
        "Technical-interview score is only weakly to moderately related to the exercise ranks among those who reached the assessment "
        f"center (strongest with {best_e}, rho {rho_ti[best_e]:.2f}); this is range-restricted because only people who passed screening have exercise scores.",
        grade([ti_ci[best_e][0] > 0 or ti_ci[best_e][1] < 0,
               stats.spearmanr(Mfull["TI score"], Mfull[EXERCISE_TOTAL_LABEL[best_e]]).pvalue < 0.05], nfull),
        f"n={nfull}; rho(TI, Int/RP/Pres) = {rho_ti['Interview']:.2f}/{rho_ti['Role Play']:.2f}/{rho_ti['Presentation']:.2f}; "
        f"CI for {best_e} {ti_ci[best_e][0]:.2f} to {ti_ci[best_e][1]:.2f}; TI spread among attendees = {sd_ratio:.0%} of spread among all TI takers")

    # ---- competency recurrence and shared-competency agreement
    ci_idx = {lab: idx[lab] for lab in comp_labels}
    name_of = dict(zip(comp_labels, comp_cols))
    within, shared, different = [], [], []
    shared_by_comp: dict[str, list[tuple[str, str]]] = {}
    for i_, a in enumerate(comp_labels):
        for b in comp_labels[i_ + 1:]:
            (ea, ka), (eb, kb) = name_of[a], name_of[b]
            if ea == eb:
                within.append((a, b))
            elif ka == kb:
                shared.append((a, b))
                shared_by_comp.setdefault(ka, []).append((a, b))
            else:
                different.append((a, b))

    def block(boot_arr, pairs_):
        ii_ = [ci_idx[a] for a, _ in pairs_]
        jj_ = [ci_idx[b] for _, b in pairs_]
        return np.nanmean(boot_arr[:, ii_, jj_], axis=1)

    def block_point(pairs_):
        return float(np.nanmean([R.loc[a, b] for a, b in pairs_]))

    rec_rows = []
    for k, exs in sorted({k: [e for e, kk in comp_cols if kk == k] for _, k in comp_cols}.items(), key=lambda kv: -len(kv[1])):
        rec_rows.append([k, len(exs), ", ".join(exs), False])
    doc.chart("competency-recurrence", "table", "Which competencies recur across exercises",
              {"columns": ["Competency", "Exercises scored in", "Which exercises", "suppressed"], "rows": rec_rows})

    blocks = [("Different competencies within one exercise", within), ("Same competency in different exercises", shared),
              ("Different competencies in different exercises", different)]
    brow = []
    bb = {}
    for nm, pr in blocks:
        if not pr:
            continue
        bt = block(boot, pr)
        lo, hi = np.percentile(bt, [2.5, 97.5])
        bb[nm] = bt
        brow.append([nm, len(pr), rd(block_point(pr), 3), rd(lo, 3), rd(hi, 3), False])
    doc.chart("correlation-blocks", "table", "Mean rank correlation by type of competency pair",
              {"columns": ["Pair type", "Pairs", "Mean Spearman rho", "CI low", "CI high", "suppressed"], "rows": brow},
              subtitle="Bootstrap CI over candidates. Same-exercise pairs share an assessor and a moment in time.")

    sh_rows, sh_labels, sh_vals = [], [], []
    for k, prs in shared_by_comp.items():
        for a, b in prs:
            lo, hi = np.percentile(boot[:, ci_idx[a], ci_idx[b]], [2.5, 97.5])
            ea, eb = name_of[a][0], name_of[b][0]
            sh_rows.append([k, f"{ea} vs {eb}", nfull, rd(R.loc[a, b], 3), rd(lo, 3), rd(hi, 3), False])
            sh_labels.append(f"{k}: {ABBR[ea]} vs {ABBR[eb]}")
            sh_vals.append(rd(R.loc[a, b], 3))
    doc.chart("shared-competency-agreement", "table", "Do shared competencies agree across exercises?",
              {"columns": ["Competency", "Exercises", "n", "Spearman rho", "CI low", "CI high", "suppressed"], "rows": sh_rows},
              share={"columns": ["Competency", "Exercises", "n", "Spearman rho", "CI low", "CI high", "suppressed"],
                     "rows": suppress_rows(sh_rows, 2, 2, 6)})
    doc.chart("shared-competency-bars", "hbar", "Cross-exercise rank agreement of shared competencies",
              {"labels": sh_labels, "series": [{"name": "Spearman rho", "values": sh_vals}]}, x_label="Spearman rho")
    if shared and different:
        diffb = bb["Same competency in different exercises"] - bb["Different competencies in different exercises"]
        dlo, dhi = np.percentile(diffb, [2.5, 97.5])
        pt = block_point(shared) - block_point(different)
        ep_pairs = [p_ for p_ in shared if name_of[p_[0]][1].startswith("Executive Presence")]
        ep_txt = ""
        if ep_pairs:
            ep_vals = [R.loc[a, b] for a, b in ep_pairs]
            ep_txt = f" Executive Presence & Communication, scored in all three exercises, has cross-exercise rho between {min(ep_vals):.2f} and {max(ep_vals):.2f}."
        wvs = block_point(within) - block_point(shared)
        wlo, whi = np.percentile(bb["Different competencies within one exercise"] - bb["Same competency in different exercises"], [2.5, 97.5])
        spearman_pvals = [stats.spearmanr(Mfull[a], Mfull[b]).pvalue for a, b in shared]
        doc.finding(
            f"Shared competencies agree across exercises more than unrelated competencies do (mean rho {block_point(shared):.2f} vs "
            f"{block_point(different):.2f}).{ep_txt} Agreement within a single exercise is higher still ({block_point(within):.2f}), "
            "which points to an exercise or assessor effect on top of the competency itself.",
            grade([dlo > 0, max(spearman_pvals) < 0.05, wlo > 0], len(shared)),
            f"n={nfull} candidates, {len(shared)} shared pairs; shared minus unrelated = {pt:.2f} (bootstrap CI {dlo:.2f} to {dhi:.2f}); "
            f"within-exercise minus shared = {wvs:.2f} (CI {wlo:.2f} to {whi:.2f}); all shared-pair Spearman p<{max(spearman_pvals):.2g}")

    # ---- PCA / factor structure of the 12 competencies
    comp_idx = [idx[l] for l in comp_labels]
    Rc = R.loc[comp_labels, comp_labels].to_numpy()
    ev, evec = np.linalg.eigh(Rc)
    order = np.argsort(ev)[::-1]
    ev, evec = ev[order], evec[:, order]
    p_ = len(comp_labels)
    share_obs = ev / p_
    ranks_c = rankdata(Mfull[comp_labels].to_numpy(float), axis=0)
    rng_pa = rng_for(22)
    null = np.empty((500, p_))
    for b in range(500):
        shuf = np.column_stack([rng_pa.permutation(ranks_c[:, j]) for j in range(p_)])
        null[b] = np.sort(np.linalg.eigvalsh(np.corrcoef(shuf, rowvar=False)))[::-1] / p_
    null95 = np.percentile(null, 95, axis=0)
    k_ret = 0
    for j in range(p_):
        if share_obs[j] > null95[j]:
            k_ret += 1
        else:
            break
    k_ret = max(k_ret, 1)
    k_show = max(k_ret, 2)
    boot_ev = np.sort(np.linalg.eigvalsh(boot[:, comp_idx][:, :, comp_idx]), axis=1)[:, ::-1] / p_
    ev_lo, ev_hi = np.percentile(boot_ev[:, :k_show], [2.5, 97.5], axis=0)
    npc = min(p_, max(6, k_show + 2))
    doc.chart("pca-variance", "bar", "Variance explained by principal components of the 12 competency ranks", {
        "labels": [f"PC{j + 1}" for j in range(npc)],
        "series": [{"name": "Share of variance (observed)", "values": [rd(v) for v in share_obs[:npc]]},
                   {"name": "Chance level (95th percentile of shuffled data)", "values": [rd(v) for v in null95[:npc]]}]},
        subtitle=f"Components above the chance line are kept (parallel analysis, 500 shuffles): {k_ret}.", y_label="Share of variance")
    L = evec[:, :k_show] * np.sqrt(np.clip(ev[:k_show], 0, None))
    L = L * np.where(L.sum(axis=0) < 0, -1, 1)
    Lr = varimax(L)
    Lr = Lr * np.where(Lr.sum(axis=0) < 0, -1, 1)
    lrows = []
    for j, (e, k) in enumerate(comp_cols):
        lrows.append([k, e] + [rd(L[j, m], 2) for m in range(k_show)] + [rd(Lr[j, m], 2) for m in range(k_show)])
    doc.chart("pca-loadings", "table", "Competency loadings (unrotated PCA and varimax-rotated)",
              {"columns": ["Competency", "Exercise"] + [f"PC{m + 1}" for m in range(k_show)] + [f"Rotated {m + 1}" for m in range(k_show)],
               "rows": lrows}, subtitle=f"{k_show} components shown; n={nfull}, computed on the rank-correlation matrix.")
    ex_arr = np.array([e for e, _ in comp_cols])
    pur = exercise_purity(Lr, ex_arr)
    rng_p = rng_for(23)
    null_pur = np.array([exercise_purity(Lr, rng_p.permutation(ex_arr)) for _ in range(N_PERM)])
    p_pur = (np.sum(null_pur >= pur - 1e-12) + 1) / (N_PERM + 1)
    pur_boot = []
    sub = boot[:, comp_idx][:, :, comp_idx]
    for b in range(300):
        eb_, vb = np.linalg.eigh(np.nan_to_num(sub[b]))
        ob = np.argsort(eb_)[::-1][:k_show]
        Lb = varimax(vb[:, ob] * np.sqrt(np.clip(eb_[ob], 0, None)))
        pur_boot.append(exercise_purity(Lb, ex_arr))
    plo, phi = np.percentile(pur_boot, [2.5, 97.5])
    doc.finding(
        f"The 12 competency scores are not 12 independent signals: {k_ret} component(s) rise above chance (first component "
        f"{share_obs[0]:.0%} of variance, bootstrap CI {ev_lo[0]:.0%}-{ev_hi[0]:.0%}). After rotation, {pur:.0%} of competencies load on a "
        f"component dominated by their own exercise, which is {'more' if p_pur < 0.05 else 'not clearly more'} than expected if exercise did not matter.",
        grade([k_ret >= 1, p_pur < 0.05, plo > np.mean(null_pur)], nfull),
        f"n={nfull}; exercise purity {pur:.2f} (bootstrap CI {plo:.2f}-{phi:.2f}) vs label-shuffle mean {null_pur.mean():.2f}, permutation p={p_pur:.4f}; "
        f"parallel analysis retains {k_ret}")

    # ---- divergence
    pr = V[[EXERCISE_TOTAL_LABEL[e] for e in EXERCISES]].dropna()
    ex_pct = pd.DataFrame({e: pct_rank(pr[EXERCISE_TOTAL_LABEL[e]]) * 100 for e in EXERCISES})
    gap = pd.DataFrame({e: ex_pct[e] - ex_pct[[o for o in EXERCISES if o != e]].mean(axis=1) for e in EXERCISES})
    mean_ir = (ex_pct["Interview"] + ex_pct["Role Play"]) / 2
    pres_gap = ex_pct["Presentation"] - mean_ir
    pts = [{"x": rd(mean_ir[i], 1), "y": rd(ex_pct.loc[i, "Presentation"], 1), "label": i,
            "group": "Presentation rank above Interview/Role Play" if pres_gap[i] > 0 else "Presentation rank at or below Interview/Role Play"}
           for i in ex_pct.index]
    rho_diag = stats.spearmanr(mean_ir, ex_pct["Presentation"])
    doc.chart("divergence-scatter", "scatter", "Presentation rank vs mean of Interview and Role Play rank",
              {"points": pts}, subtitle="Points on the diagonal rank the same on both. Ranks are percentiles within assessment-center attendees (n=" + str(len(ex_pct)) + ").",
              x_label="Mean of Interview and Role Play percentile rank", y_label="Presentation percentile rank")
    abs_gap = gap.abs()
    div_rows = []
    summ_rows = []
    boots_gap = {}
    rng_g = rng_for(24)
    n_g = len(gap)
    for e in EXERCISES:
        a = abs_gap[e].to_numpy()
        bs = np.array([a[rng_g.integers(0, n_g, n_g)].mean() for _ in range(N_BOOT)])
        boots_gap[e] = bs
        lo, hi = np.percentile(bs, [2.5, 97.5])
        summ_rows.append([e, n_g, rd(a.mean(), 1), rd(lo, 1), rd(hi, 1), rd(np.median(a), 1), False])
    doc.chart("divergence-by-exercise", "table", "How far each exercise's rank sits from the other two (percentile points)",
              {"columns": ["Exercise", "n", "Mean absolute rank gap", "CI low", "CI high", "Median absolute gap", "suppressed"], "rows": summ_rows},
              subtitle="Gap = exercise percentile rank minus mean percentile rank on the other two exercises.",
              share={"columns": ["Exercise", "n", "Mean absolute rank gap", "CI low", "CI high", "Median absolute gap", "suppressed"],
                     "rows": suppress_rows(summ_rows, 1, 1, 6)})
    maxgap = abs_gap.max(axis=1).sort_values(ascending=False)
    for i in maxgap.index[:10]:
        e = abs_gap.loc[i].idxmax()
        div_rows.append([i, e, rd(gap.loc[i, e], 1)] + [rd(ex_pct.loc[i, x], 1) for x in EXERCISES] +
                        [cm.loc[i, "decision"] if isinstance(cm.loc[i, "decision"], str) else None])
    doc.chart("divergent-candidates", "table", "Candidates whose rank on one exercise differs most from the others (local only)",
              {"columns": ["candidate_id", "Most divergent exercise", "Rank gap (points)", "Interview pct", "Role Play pct",
                           "Presentation pct", "Decision"], "rows": div_rows},
              subtitle="Ten largest gaps shown for review; this is a ranking of divergence, not a cutoff.", local_only=True)
    top_e = max(EXERCISES, key=lambda e: abs_gap[e].mean())
    others = [e for e in EXERCISES if e != top_e]
    dmean = boots_gap[top_e] - np.mean([boots_gap[o] for o in others], axis=0)
    dl, dh = np.percentile(dmean, [2.5, 97.5])
    perm_stat = abs_gap[top_e].mean() - np.mean([abs_gap[o].mean() for o in others])
    doc.finding(
        f"{top_e} is the exercise whose rank diverges most from the other two (mean absolute gap {abs_gap[top_e].mean():.1f} percentile points vs "
        f"{np.mean([abs_gap[o].mean() for o in others]):.1f} for the others). Presentation rank vs mean of Interview and Role Play rank has rho {rho_diag.statistic:.2f}; "
        "the most divergent candidates are listed in the local copy.",
        grade([dl > 0, rho_diag.pvalue < 0.05], n_g) if top_e == "Presentation" else "weak",
        f"n={n_g}; gap difference {perm_stat:.1f} points (bootstrap CI {dl:.1f} to {dh:.1f}); Presentation vs mean(Int, RP) rho={rho_diag.statistic:.2f}, p={rho_diag.pvalue:.2g}")

    # ---- clustering of rank profiles
    prof = pd.DataFrame({"TI": pct_rank(cm["screen_score"].reindex(pr.index)) * 100,
                         "Interview": ex_pct["Interview"], "Role Play": ex_pct["Role Play"], "Presentation": ex_pct["Presentation"]}).dropna()
    X = prof.to_numpy() / 100
    n_p = len(X)
    ks = list(range(2, min(6, n_p // MIN_GROUP) + 1))
    sil, models = {}, {}
    for k in ks:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)
        models[k] = km
        sil[k] = float(silhouette_score(X, km.labels_))
    rng_c = rng_for(25)
    null_best = []
    for _ in range(100):
        Xn = np.column_stack([rng_c.permutation(X[:, j]) for j in range(X.shape[1])])
        null_best.append(max(silhouette_score(Xn, KMeans(n_clusters=k, n_init=3, random_state=SEED).fit(Xn).labels_) for k in ks))
    null95_sil = float(np.percentile(null_best, 95))
    stab = {}
    for k in ks:
        aris = []
        for _ in range(100):
            ib = rng_c.integers(0, n_p, n_p)
            kb = KMeans(n_clusters=k, n_init=3, random_state=SEED).fit(X[ib])
            aris.append(adjusted_rand_score(models[k].labels_, kb.predict(X)))
        stab[k] = (float(np.mean(aris)), float(np.percentile(aris, 5)))
    k_best = max(sil, key=sil.get)
    doc.chart("cluster-selection", "line", "Choosing the number of rank-profile clusters", {
        "labels": [str(k) for k in ks],
        "series": [{"name": "Silhouette", "values": [rd(sil[k]) for k in ks]},
                   {"name": "Bootstrap stability (mean ARI)", "values": [rd(stab[k][0]) for k in ks]},
                   {"name": "Chance silhouette (95th pct of shuffled profiles)", "values": [rd(null95_sil)] * len(ks)}]},
        x_label="Number of clusters k", subtitle="k is picked by the highest silhouette; stability and the shuffled-data line tell how much to trust it.")
    lab = models[k_best].labels_
    overall = pd.Series(X.mean(axis=1), index=prof.index)
    cl_means = pd.DataFrame(X * 100, index=prof.index, columns=prof.columns).groupby(lab).mean()
    cl_order = cl_means.mean(axis=1).sort_values(ascending=False).index.tolist()
    name_map = {cid_: f"Cluster {j + 1}" for j, cid_ in enumerate(cl_order)}
    crow, hm_rows, hm_share = [], [], []
    for cid_ in cl_order:
        m = lab == cid_
        mm = cl_means.loc[cid_]
        dev = mm - mm.mean()
        desc = f"average rank {mm.mean():.0f}; relatively strongest on {dev.idxmax()}, weakest on {dev.idxmin()}"
        crow.append([name_map[cid_], int(m.sum())] + [rd(mm[c_], 1) for c_ in prof.columns] + [desc, False])
        hm_rows.append((f"{name_map[cid_]} (n={int(m.sum())})", [rd(mm[c_], 1) for c_ in prof.columns], int(m.sum())))
    ccols = ["Cluster", "n"] + [f"Mean {c_} percentile" for c_ in prof.columns] + ["Profile (described after the fact)", "suppressed"]
    doc.chart("cluster-profiles", "table", "Rank-profile clusters (derived from the data)",
              {"columns": ccols, "rows": crow},
              subtitle=f"k={k_best} chosen by silhouette over k={ks[0]}-{ks[-1]}; clusters are described by their mean percentile ranks, not predefined.",
              share={"columns": ccols, "rows": suppress_rows(crow, 1, 1, len(ccols) - 1)})
    doc.chart("cluster-heatmap", "heatmap", "Mean percentile rank by cluster", {
        "row_labels": [r[0] for r in hm_rows], "col_labels": list(prof.columns), "values": [r[1] for r in hm_rows], "min": 0, "max": 100},
        subtitle="All four ranks are percentiles within assessment-center attendees (TI included, so its spread is range-restricted).",
        share={"row_labels": [f"Cluster {j + 1}" for j in range(len(hm_rows))], "col_labels": list(prof.columns),
               "values": [r[1] if r[2] >= MIN_GROUP else [None] * len(prof.columns) for r in hm_rows], "min": 0, "max": 100})
    min_cl = min(int((lab == k_).sum()) for k_ in range(k_best))
    st_cl = grade([sil[k_best] > null95_sil, stab[k_best][0] >= 0.75], min_cl)
    if sil[k_best] <= null95_sil:
        txt = (f"Rank profiles do not form clearly separate groups: the best silhouette ({sil[k_best]:.2f} at k={k_best}) does not exceed what "
               f"shuffled profiles produce ({null95_sil:.2f}). The clusters shown are a descriptive partition of a continuum.")
    else:
        txt = (f"Rank profiles split into {k_best} data-derived clusters (silhouette {sil[k_best]:.2f} vs {null95_sil:.2f} for shuffled profiles). "
               + "; ".join(f"{name_map[c_]} (n={int((lab == c_).sum())}): {r[-2]}" for c_, r in zip(cl_order, crow)) + ".")
    doc.finding(txt, st_cl, f"n={n_p}; silhouette {sil[k_best]:.2f}, bootstrap stability ARI {stab[k_best][0]:.2f} (5th pct {stab[k_best][1]:.2f}), "
                            f"chance silhouette 95th pct {null95_sil:.2f}; smallest cluster n={min_cl}")

    # ---- decision vs score (no cutoffs)
    D = cm[cm["attended_ac"] & cm["decision"].notna() & cm["ac_total"].notna()].copy()
    D["pct"] = pct_rank(D["ac_total"]) * 100
    ycode = D["decision"].map({d: i for i, d in enumerate(DECISIONS)}).astype(int).to_numpy()
    grp = {d: D.loc[D["decision"] == d, "pct"].to_numpy() for d in DECISIONS}
    boxes = [box_stats(d, grp[d]) for d in DECISIONS]
    doc.chart("decision-score-overlap", "boxplot", "Assessment-center percentile rank by final decision",
              {"groups": boxes}, subtitle="Overlap between the boxes shows candidates whose decision differs from candidates with similar rank.",
              y_label="AC total percentile rank (0-100, within attendees)", share={"groups": suppress_boxes(boxes)})
    rng_d = rng_for(26)
    pair_defs = [("Hire", "Standby"), ("Standby", "No Hire"), ("Hire", "No Hire")]
    pres = {}
    for hi_d, lo_d in pair_defs:
        pres[(hi_d, lo_d)] = auc_test(grp[hi_d], grp[lo_d], rng_d)
    keys = [k_ for k_, v in pres.items() if v]
    qd = dict(zip(keys, bh([pres[k_]["p_perm"] for k_ in keys])))
    for k_ in keys:
        g = pres[k_]
        g["q"] = qd[k_]
        g["strength"] = grade([g["lo"] > 0.5, g["q"] < 0.05, g["p_mwu"] < 0.05], min(g["n_pos"], g["n_neg"]))
    arows = []
    for (hi_d, lo_d), g in pres.items():
        if g:
            arows.append([f"{hi_d} vs {lo_d}", g["n_pos"], g["n_neg"], rd(g["auc"]), rd(g["lo"]), rd(g["hi"]), rd(1 - g["auc"]),
                          rd(g["p_perm"], 4), rd(g["q"], 4), g["strength"], False])
        else:
            arows.append([f"{hi_d} vs {lo_d}", len(grp[hi_d]), len(grp[lo_d])] + [None] * 7 + [False])
    acols = ["Comparison", "n higher group", "n lower group", "AUC (higher-decision group outranks)", "CI low", "CI high",
             "Share of pairs in the wrong order", "Perm. p", "BH q", "Strength", "suppressed"]
    share_a = []
    for r in arows:
        if (r[1] is not None and r[1] < MIN_GROUP) or (r[2] is not None and r[2] < MIN_GROUP):
            share_a.append([r[0]] + [None] * 9 + [True])
        else:
            share_a.append(r)
    doc.chart("decision-overlap-table", "table", "How much decision groups overlap on score rank",
              {"columns": acols, "rows": arows}, share={"columns": acols, "rows": share_a})

    # concordance
    tau_obs = stats.kendalltau(D["pct"], ycode)
    tb = []
    n_d = len(D)
    pctv = D["pct"].to_numpy()
    for _ in range(N_BOOT):
        ib = rng_d.integers(0, n_d, n_d)
        if len(np.unique(ycode[ib])) < 2:
            continue
        tb.append(stats.kendalltau(pctv[ib], ycode[ib]).statistic)
    tlo, thi = np.percentile(tb, [2.5, 97.5])

    flag_rows: list = []
    flagged_ids: list[str] = []
    om_txt = ""
    try:
        Xo = (pctv / 100).reshape(-1, 1)
        res = OrderedModel(ycode, Xo, distr="logit").fit(method="bfgs", disp=False, maxiter=1000)
        Pm = np.asarray(res.model.predict(res.params, exog=Xo))
        coef = float(res.params[0])
        ci = np.asarray(res.conf_int())[0]
        p_coef = float(res.pvalues[0])
        s_obs, thr_d, fl = surprise_flags(Pm, ycode, rng_for(27))
        cum = np.cumsum(Pm, axis=1)
        ar = np.arange(n_d)
        psr = (cum[ar, ycode] - Pm[ar, ycode]) - (1 - cum[ar, ycode])
        med = {d: float(np.median(grp[d])) for d in DECISIONS}
        gap_med = pctv - np.array([med[d] for d in D["decision"]])
        sc_ = D["ac_total"].to_numpy(float)
        disc = np.zeros(n_d, int)
        for i in range(n_d):
            disc[i] = int(np.sum(((ycode[i] > ycode) & (sc_[i] < sc_)) | ((ycode[i] < ycode) & (sc_[i] > sc_))))
        D["surprise"], D["psr"], D["flag"], D["gap_med"], D["disc"], D["pobs"] = s_obs, psr, fl, gap_med, disc, Pm[ar, ycode]
        D["expected"] = [DECISIONS[j] for j in Pm.argmax(axis=1)]
        fl_df = D[D["flag"]].sort_values("surprise", ascending=False)
        flagged_ids = fl_df.index.tolist()
        for i, r in fl_df.iterrows():
            flag_rows.append([i, r["decision"], rd(r["ac_total"], 0), rd(r["pct"], 1), r["expected"], rd(r["pobs"]), rd(r["psr"]),
                              rd(r["gap_med"], 1), int(r["disc"]),
                              "decision higher than score rank suggests" if r["psr"] > 0 else "decision lower than score rank suggests"])
        or10 = np.exp(coef * 0.1)
        om_txt = (f"ordinal logit: each +10 percentile points multiplies the odds of a higher decision by {or10:.2f} "
                  f"(95% CI {np.exp(ci[0] * 0.1):.2f}-{np.exp(ci[1] * 0.1):.2f}, p={p_coef:.2g})")
        om_ok = p_coef < 0.05
    except Exception as exc:  # model failure must not silently produce flags
        om_ok = False
        thr_d = np.nan
        doc.caveats.append(f"Ordinal logit did not converge ({type(exc).__name__}); decision flags were not produced.")

    ok_pairs = [pres[k_] for k_ in keys]
    tau_checks = [tlo > 0, tau_obs.pvalue < 0.05, om_ok]
    doc.finding(
        f"Decisions follow assessment-center score rank (Kendall tau {tau_obs.statistic:.2f}) but the groups overlap: "
        + "; ".join(f"a random {a} candidate outranked a random {b} candidate in {pres[(a, b)]['auc']:.0%} of pairs" for a, b in pair_defs if pres[(a, b)])
        + ". No score cutoff is assumed; overlap is read from the full percentile distributions.",
        grade(tau_checks, min(len(g) for g in grp.values())),
        f"n={n_d} ({', '.join(f'{d} {len(grp[d])}' for d in DECISIONS)}); tau {tau_obs.statistic:.2f} (bootstrap CI {tlo:.2f} to {thi:.2f}, p={tau_obs.pvalue:.2g}); {om_txt}")
    if flag_rows or om_txt:
        nf = len(flagged_ids)
        doc.chart("decision-flags", "table", "Decisions far out of line with within-cohort score rank (local only)",
                  {"columns": ["candidate_id", "Decision", "AC total", "AC percentile", "Model-expected decision", "P(observed decision)",
                               "Probability-scale residual", "Rank gap to decision-group median", "Discordant pairs", "Direction"],
                   "rows": flag_rows},
                  subtitle="Flagged when the ordinal-logit probability of the observed decision is below the 95th percentile of model-simulated outcomes.",
                  local_only=True)
        n_pairs_cmp = 0
        n_disc_pairs = 0
        sc_ = D["ac_total"].to_numpy(float)
        for i in range(n_d):
            for j in range(i + 1, n_d):
                if ycode[i] != ycode[j] and sc_[i] != sc_[j]:
                    n_pairs_cmp += 1
                    if (ycode[i] - ycode[j]) * (sc_[i] - sc_[j]) < 0:
                        n_disc_pairs += 1
        doc.finding(
            f"{nf} candidate(s) have a decision far out of line with their within-cohort score rank (flagged by an ordinal-logit residual fence); "
            f"in total {n_disc_pairs} of {n_pairs_cmp} comparable candidate pairs are in the opposite order on decision and score. Candidate ids are in the local copy only.",
            "suggestive", f"n={n_d}; fence on -log P(observed) = {thr_d:.2f}; discordant pair share {n_disc_pairs / max(n_pairs_cmp, 1):.1%}; "
                          f"flags are single outliers, so strength is limited to suggestive",
            share_text=f"{share_count(nf)} candidate(s) have a decision far out of line with their within-cohort score rank; "
                       f"{n_disc_pairs} of {n_pairs_cmp} comparable candidate pairs are in the opposite order on decision and score. Ids are in the local copy only.",
            share_evidence=f"n={n_d}; model-simulated 95% fence; discordant pair share {n_disc_pairs / max(n_pairs_cmp, 1):.1%}")
    jit = np.random.default_rng([SEED, 28]).uniform(-0.15, 0.15, n_d)
    fl_set = set(flagged_ids)
    sp = [{"x": rd(pctv[i], 1), "y": rd(ycode[i] + jit[i], 2), "label": (D.index[i] if D.index[i] in fl_set else None),
           "group": D["decision"].iloc[i]} for i in range(n_d)]
    doc.chart("decision-vs-rank", "scatter", "Decision level vs assessment-center percentile rank",
              {"points": sp}, subtitle="Vertical axis: 0 = No Hire, 1 = Standby, 2 = Hire (jittered). Labels mark flagged candidates in the local copy.",
              x_label="AC total percentile rank (0-100)", y_label="Decision level (jittered)")
    return doc


# ------------------------------------------------------------------------------------------------------------- entry

def run(processed_dir: Path, results_dir: Path) -> None:
    processed_dir, results_dir = Path(processed_dir), Path(results_dir)
    c, long, ex = load_data(processed_dir)
    ids = set(c["candidate_id"]) | set(long["candidate_id"])
    funnel_doc, _ = build_funnel(c)
    funnel_doc.write(results_dir, ids)
    build_structure(c, long, ex).write(results_dir, ids)


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    _load_env(here / ".env")
    data_dir = Path(os.environ.get("HIRING_DATA_DIR", here / "data" / "synthetic"))
    out_dir = Path(os.environ.get("HIRING_OUT_DIR", data_dir / "processed"))
    run(out_dir, out_dir / "results")
    print(f"wrote {out_dir / 'results'}")
