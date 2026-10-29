"""Interviewer (reviewer) trends: leniency/severity, drift, note-vs-score consistency, language style, bias check.

Section `interviewers` (see analysis/CONTRACT.md). Reads only the processed CSVs; writes local/ and shareable/ JSON.

Key limitation, stated everywhere it matters: each candidate has ONE rater per exercise, so a reviewer's own scores cannot
separate a lenient reviewer from a stronger candidate pool. Instead each reviewer's deviation is measured against what
OTHER, independent signals predict for the same candidates (other exercises scored by different assessors, the technical
interview score; for recruiters, the later assessment-center rank). The reviewer effect is the residual, shrunk with an
empirical-Bayes random-intercept estimate and given bootstrap CIs and permutation p-values.

Flags are for review, not verdicts on individuals. Outcomes are past human decisions, not job performance.
"""

from __future__ import annotations

import json
import os
import sys
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import silhouette_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from statsmodels.stats.multitest import multipletests

SECTION = "interviewers"
SEED = 20240611
N_BOOT = 1000
N_PERM = 2000
N_BOOT_SMALL = 500
MIN_SHARE = 5
MIN_TREND = 8
MIN_BIAS = 10
AC = ("Interview", "Role Play", "Presentation")
TI = "Technical interview"
ROLES = AC + (TI,)


# ----------------------------------------------------------------------------- small helpers

def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer, int)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if o is None or isinstance(o, str):
        return o
    if o is pd.NA or o is pd.NaT:
        return None
    return str(o)


def _bh(p):
    p = np.asarray(p, dtype=float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    if ok.sum():
        out[ok] = multipletests(p[ok], method="fdr_bh")[1]
    return out


def _spear(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return np.nan
    return float(np.corrcoef(stats.rankdata(a), stats.rankdata(b))[0, 1])


def _boot_ci(fn, arrays, rng, B=N_BOOT_SMALL):
    n = len(arrays[0])
    vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        v = fn(*[a[idx] for a in arrays])
        if np.isfinite(v):
            vals.append(v)
    if len(vals) < B // 2:
        return np.nan, np.nan
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def _pct_rank(s: pd.Series) -> pd.Series:
    return pd.Series(stats.rankdata(s) / (len(s) + 1), index=s.index)


def _grade(n, ci_excludes_zero, p1_adj, p2_adj, p1_raw, min_n=8):
    if n is None or n < MIN_SHARE:
        return "weak"
    if ci_excludes_zero and p1_adj < 0.05 and p2_adj < 0.05 and n >= min_n:
        return "robust"
    if p1_adj < 0.10 or (ci_excludes_zero and p2_adj < 0.10):
        return "suggestive"
    return "weak"


# ----------------------------------------------------------------------------- data assembly

def _build_ratings(cands: pd.DataFrame, ex: pd.DataFrame, sl: pd.DataFrame) -> pd.DataFrame:
    ex = ex.dropna(subset=["assessor", "total"]).drop_duplicates(["candidate_id", "exercise"]).copy()
    comp = sl.groupby(["candidate_id", "exercise"])["score"].agg(
        comp_mean="mean", comp_sd=lambda s: float(np.std(s, ddof=0)), comp_equal=lambda s: float(s.nunique() == 1))
    ac = ex.rename(columns={"exercise": "role", "assessor": "reviewer", "total": "value"})[
        ["candidate_id", "role", "reviewer", "value"]]
    ac = ac.merge(comp, left_on=["candidate_id", "role"], right_index=True, how="left")
    t = cands[cands["screen_score"].notna() & cands["screen_recruiter"].notna()].drop_duplicates("candidate_id")
    ti = pd.DataFrame({"candidate_id": t["candidate_id"], "role": TI, "reviewer": t["screen_recruiter"],
                       "value": t["screen_score"], "comp_mean": np.nan, "comp_sd": np.nan, "comp_equal": np.nan})
    r = pd.concat([ac, ti], ignore_index=True)
    r["reviewer"] = r["reviewer"].astype(str).str.strip()
    r["value"] = pd.to_numeric(r["value"], errors="coerce")
    r = r.dropna(subset=["value"]).reset_index(drop=True)
    r["rank"] = r.groupby("role")["value"].transform(_pct_rank)
    num = r["candidate_id"].astype(str).str.extract(r"(\d+)\s*$")[0]
    r["order"] = pd.to_numeric(num, errors="coerce")
    return r


def _add_signal(r: pd.DataFrame, cands: pd.DataFrame) -> pd.DataFrame:
    """Independent signal per rating: mean percentile rank from OTHER instruments rated by a DIFFERENT reviewer."""
    rank_w = r.pivot(index="candidate_id", columns="role", values="rank")
    rev_w = r.pivot(index="candidate_id", columns="role", values="reviewer")
    ac_pct = pd.to_numeric(cands.drop_duplicates("candidate_id").set_index("candidate_id")["ac_pct"], errors="coerce").dropna()
    ac_rank = pd.Series(stats.rankdata(ac_pct) / (len(ac_pct) + 1), index=ac_pct.index) if len(ac_pct) else ac_pct
    sig, nsig = [], []
    for row in r.itertuples():
        parts = []
        if row.role in AC:
            for o in AC:
                if o != row.role and o in rank_w.columns:
                    v, rv = rank_w.at[row.candidate_id, o], rev_w.at[row.candidate_id, o]
                    if pd.notna(v) and rv != row.reviewer:
                        parts.append(float(v))
            if TI in rank_w.columns and pd.notna(rank_w.at[row.candidate_id, TI]):
                parts.append(float(rank_w.at[row.candidate_id, TI]))
        elif row.candidate_id in ac_rank.index:
            parts.append(float(ac_rank[row.candidate_id]))
        sig.append(np.mean(parts) if parts else np.nan)
        nsig.append(len(parts))
    r = r.copy()
    r["signal"] = sig
    r["n_signal"] = nsig
    return r


# ----------------------------------------------------------------------------- empirical-Bayes reviewer deviation

def _eb(y, x, g, k):
    """OLS of y on x, then random-intercept (one-way ANOVA moment) shrinkage of reviewer mean residuals."""
    X = np.c_[np.ones_like(x), x]
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    res = y - X @ beta
    n = np.bincount(g, minlength=k).astype(float)
    m = np.divide(np.bincount(g, weights=res, minlength=k), n, out=np.full(k, np.nan), where=n > 0)
    N, kk = len(y), int((n > 0).sum())
    ssw = float(np.sum((res - m[g]) ** 2))
    s2 = ssw / (N - kk) if N > kk else float(np.var(res))
    if kk > 1:
        msb = float(np.nansum(n * m ** 2) / (kk - 1))
        n0 = (N - np.sum(n ** 2) / N) / (kk - 1)
        tau2 = max(0.0, (msb - s2) / n0) if n0 > 0 else 0.0
    else:
        tau2 = 0.0
    icc = tau2 / (tau2 + s2) if (tau2 + s2) > 0 else 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        shrink = np.where(n > 0, tau2 / (tau2 + s2 / n), np.nan)
    return {"res": res, "beta": beta, "n": n, "raw": m, "dev": shrink * m, "shrink": shrink, "s2": s2, "tau2": tau2, "icc": icc}


def _perm_dev(res, g, k, rng, B=N_PERM):
    n = np.bincount(g, minlength=k).astype(float)
    N = len(res)
    sst = float(np.sum(res ** 2))
    kk = int((n > 0).sum())
    n0 = (N - np.sum(n ** 2) / N) / max(kk - 1, 1)
    ms = np.zeros((B, k))
    icc = np.zeros(B)
    for b in range(B):
        gp = rng.permutation(g)
        sm = np.bincount(gp, weights=res, minlength=k)
        m = np.divide(sm, n, out=np.zeros(k), where=n > 0)
        ssb = float(np.sum(n * m ** 2))
        s2 = max(sst - ssb, 1e-12) / max(N - kk, 1)
        tau2 = max(0.0, (ssb / max(kk - 1, 1) - s2) / n0) if n0 > 0 else 0.0
        ms[b], icc[b] = m, tau2 / (tau2 + s2)
    return ms, icc


def _mixed_icc(d: pd.DataFrame) -> float:
    import statsmodels.formula.api as smf
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.mixedlm("rank ~ signal", d, groups=d["reviewer"]).fit(reml=True)
        v = float(m.cov_re.iloc[0, 0])
        return v / (v + float(m.scale))
    except Exception:
        return float("nan")


def _role_model(d: pd.DataFrame, role: str, seed: int):
    revs = sorted(d["reviewer"].unique())
    k = len(revs)
    g = d["reviewer"].map({r: i for i, r in enumerate(revs)}).to_numpy()
    y, x = d["rank"].to_numpy(float), d["signal"].to_numpy(float)
    fit = _eb(y, x, g, k)
    rng = np.random.default_rng(seed)
    N = len(y)
    boot_dev = np.full((N_BOOT, k), np.nan)
    boot_raw = np.full((N_BOOT, k), np.nan)
    boot_icc = np.zeros(N_BOOT)
    for b in range(N_BOOT):
        idx = rng.integers(0, N, N)
        f = _eb(y[idx], x[idx], g[idx], k)
        boot_dev[b], boot_raw[b], boot_icc[b] = f["dev"], f["raw"], f["icc"]
    ms, icc_perm = _perm_dev(fit["res"], g, k, rng)
    # unadjusted share of rank variance (pool-confounded context)
    fit0 = _eb(y, np.zeros_like(x), g, k)
    res = fit["res"]
    rows = []
    for j, rv in enumerate(revs):
        mask = g == j
        n = int(mask.sum())
        p_perm = (1 + np.sum(np.abs(ms[:, j]) >= abs(fit["raw"][j]) - 1e-12)) / (N_PERM + 1)
        others = res[~mask]
        p_mw = float(stats.mannwhitneyu(res[mask], others, alternative="two-sided").pvalue) if n >= 3 and len(others) >= 3 else np.nan
        lo, hi = np.nanpercentile(boot_dev[:, j], [2.5, 97.5]) if np.isfinite(boot_dev[:, j]).sum() > N_BOOT // 2 else (np.nan, np.nan)
        rlo, rhi = np.nanpercentile(boot_raw[:, j], [2.5, 97.5]) if np.isfinite(boot_raw[:, j]).sum() > N_BOOT // 2 else (np.nan, np.nan)
        rows.append({"role": role, "reviewer": rv, "n": n, "raw": fit["raw"][j], "dev": fit["dev"][j], "shrink": fit["shrink"][j],
                     "ci_lo": lo, "ci_hi": hi, "raw_lo": rlo, "raw_hi": rhi, "p_perm": float(p_perm), "p_mw": p_mw,
                     "mean_signal": float(x[mask].mean())})
    d = d.copy()
    d["resid"] = res
    icc_p = (1 + np.sum(icc_perm >= fit["icc"] - 1e-12)) / (N_PERM + 1)
    var_row = {"role": role, "n": N, "k": k, "icc_adj": fit["icc"], "icc_unadj": fit0["icc"], "icc_mixed": _mixed_icc(d),
               "icc_ci_lo": float(np.percentile(boot_icc, 2.5)), "icc_ci_hi": float(np.percentile(boot_icc, 97.5)),
               "p_perm": float(icc_p), "slope": float(fit["beta"][1]), "sd_rank": float(np.std(y))}
    return rows, var_row, d


# ----------------------------------------------------------------------------- resume groups

def _resume_groups(resumes: pd.DataFrame):
    r = resumes.dropna(subset=["text"]).drop_duplicates("candidate_id").reset_index(drop=True)
    if len(r) < 20:
        return None, None
    tf = TfidfVectorizer(min_df=3, max_df=0.5, sublinear_tf=True, stop_words="english", ngram_range=(1, 2))
    X = tf.fit_transform(r["text"].astype(str))
    sil, labs = {}, {}
    for k in range(2, min(8, len(r) // 10) + 1):
        km = KMeans(k, n_init=10, random_state=SEED).fit(X)
        if np.bincount(km.labels_).min() < MIN_SHARE:
            continue
        sil[k], labs[k] = float(silhouette_score(X, km.labels_)), km
    if not sil:
        return None, None
    best = max(sil.values())
    k = min(kk for kk, s in sil.items() if s >= 0.9 * best)
    km = labs[k]
    order = np.argsort(-np.bincount(km.labels_), kind="stable")
    relabel = {int(old): i + 1 for i, old in enumerate(order)}
    r["group"] = [f"Resume group {relabel[int(l)]}" for l in km.labels_]
    terms = np.array(tf.get_feature_names_out())
    info = []
    for old in order:
        c = km.cluster_centers_[old]
        info.append({"group": f"Resume group {relabel[int(old)]}", "n": int((km.labels_ == old).sum()),
                     "top_terms": ", ".join(terms[np.argsort(-c)[:6]])})
    return r[["candidate_id", "group"]], {"k": k, "silhouette": sil, "groups": info}


# ----------------------------------------------------------------------------- notes: consistency and style

def _notes_frame(notes: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    n = notes[notes["source"].isin(ROLES) & notes["text"].notna()].copy()
    n["text"] = n["text"].astype(str)
    n = n[~n["text"].str.strip().str.upper().isin(["", "N/A"])]
    m = n.rename(columns={"source": "role"}).drop(columns="reviewer").merge(
        ratings[["candidate_id", "role", "reviewer", "rank", "order"]], on=["candidate_id", "role"], how="inner")
    return m.drop_duplicates(["candidate_id", "role"]).reset_index(drop=True)


def _consistency(nt: pd.DataFrame, seed: int):
    pipe = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True), Ridge(alpha=1.0))
    ng = nt["candidate_id"].nunique()
    cv = GroupKFold(n_splits=min(5, ng))
    pred = cross_val_predict(pipe, nt["text"], nt["rank"], groups=nt["candidate_id"], cv=cv)
    nt = nt.copy()
    nt["text_rank"] = pd.Series(pred, index=nt.index).groupby(nt["role"]).transform(_pct_rank)
    nt["gap"] = (nt["text_rank"] - nt["rank"]).abs()
    tert = lambda s: np.digitize(s, [1 / 3, 2 / 3])  # noqa: E731  (terciles of a percentile rank)
    nt["t_text"], nt["t_score"] = tert(nt["text_rank"]), tert(nt["rank"])
    nt["same"] = nt["t_text"] == nt["t_score"]
    nt["opposite"] = (nt["t_text"] - nt["t_score"]).abs() == 2
    rng = np.random.default_rng(seed)
    rho = _spear(nt["text_rank"], nt["rank"])
    tau = float(stats.kendalltau(nt["text_rank"], nt["rank"]).statistic)
    p_rho = float(stats.spearmanr(nt["text_rank"], nt["rank"]).pvalue)
    lo, hi = _boot_ci(_spear, [nt["text_rank"].to_numpy(), nt["rank"].to_numpy()], rng)
    glob = {"n": len(nt), "rho": rho, "tau": tau, "p": p_rho, "lo": lo, "hi": hi, "same": float(nt["same"].mean())}
    rows = []
    for rv, d in nt.groupby("reviewer"):
        others = nt.loc[nt["reviewer"] != rv, "gap"]
        p = float(stats.mannwhitneyu(d["gap"], others, alternative="two-sided").pvalue) if len(d) >= 3 else np.nan
        a, b = d["text_rank"].to_numpy(), d["rank"].to_numpy()
        l, h = _boot_ci(_spear, [a, b], rng) if len(d) >= MIN_SHARE else (np.nan, np.nan)
        rows.append({"reviewer": rv, "n": len(d), "rho": _spear(a, b), "lo": l, "hi": h, "gap": float(d["gap"].mean()),
                     "same": float(d["same"].mean()), "n_opp": int(d["opposite"].sum()), "p_mw": p,
                     "gap_others": float(others.mean())})
    cons = pd.DataFrame(rows)
    cons["p_adj"] = _bh(cons["p_mw"])
    return nt, cons, glob


def _lexicons(nt: pd.DataFrame):
    cv = CountVectorizer(binary=True, stop_words="english", min_df=MIN_SHARE)
    X = cv.fit_transform(nt["text"]).toarray().astype(float)
    terms = np.array(cv.get_feature_names_out())
    y = stats.rankdata(nt["rank"].to_numpy())
    n = len(y)
    keep = X.std(axis=0) > 0
    rho = np.full(X.shape[1], np.nan)
    for j in np.where(keep)[0]:
        rho[j] = np.corrcoef(stats.rankdata(X[:, j]), y)[0, 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = rho * np.sqrt((n - 2) / np.maximum(1 - rho ** 2, 1e-12))
    p = 2 * stats.t.sf(np.abs(t), n - 2)
    q = _bh(p)
    df = X.mean(axis=0)
    med = float(np.median(df[keep]))

    def make(q_ev, q_imp):
        ev = keep & (q < q_ev)
        imp = keep & (q >= q_imp) & (df <= med)
        return ev, imp

    out = {}
    for name, (qe, qi) in {"A": (0.05, 0.05), "B": (0.01, 0.25)}.items():
        ev, imp = make(qe, qi)
        e, i = X[:, ev].sum(axis=1), X[:, imp].sum(axis=1)
        share = np.divide(i, e + i, out=np.full(n, np.nan), where=(e + i) > 0)
        out[name] = {"share": share, "n_ev": int(ev.sum()), "n_imp": int(imp.sum()),
                     "ev_terms": terms[ev][np.argsort(-np.abs(rho[ev]))][:8].tolist(),
                     "imp_terms": terms[imp][np.argsort(-df[imp])][:8].tolist()}
    return out, {"n_terms": int(keep.sum()), "median_df": med}


def _style_by_reviewer(nt: pd.DataFrame, variants: dict, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for v, info in variants.items():
        s = pd.Series(info["share"], index=nt.index)
        for rv, d in nt.groupby("reviewer"):
            a = s.loc[d.index].dropna().to_numpy()
            b = s.loc[nt.index[(nt["reviewer"] != rv)]].dropna().to_numpy()
            if len(a) == 0:
                continue
            lo, hi = _boot_ci(lambda z: float(np.mean(z)), [a], rng) if len(a) >= MIN_SHARE else (np.nan, np.nan)
            p = float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue) if len(a) >= 3 and len(b) >= 3 else np.nan
            rows.append({"variant": v, "reviewer": rv, "n": int(len(a)), "n_all": int(len(d)), "mean": float(a.mean()),
                         "lo": lo, "hi": hi, "others": float(b.mean()) if len(b) else np.nan, "p_mw": p})
    out = pd.DataFrame(rows)
    out["p_adj"] = out.groupby("variant")["p_mw"].transform(lambda s: pd.Series(_bh(s), index=s.index))
    return out


# ----------------------------------------------------------------------------- bias check by resume group

def _group_test(df: pd.DataFrame, value: str, covar: str | None, seed: int):
    """Association of a reviewer's candidate-level outcome with resume group, conditional on score rank (if covar)."""
    d = df.dropna(subset=[value, "group"] + ([covar] if covar else [])).copy()
    d = d[d.groupby("group")["group"].transform("size") >= 2]
    if len(d) < MIN_BIAS or d["group"].nunique() < 2:
        return None
    y = d[value].to_numpy(float)
    if covar:
        X = np.c_[np.ones(len(d)), d[covar].to_numpy(float)]
        y = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    lab = d["group"].to_numpy()
    sst = float(np.sum((y - y.mean()) ** 2))
    if sst <= 0:
        return None

    def eta(l):
        return sum(len(y[l == u]) * (y[l == u].mean() - y.mean()) ** 2 for u in np.unique(l)) / sst

    obs = eta(lab)
    rng = np.random.default_rng(seed)
    perm = np.array([eta(rng.permutation(lab)) for _ in range(N_PERM)])
    p = float((1 + np.sum(perm >= obs - 1e-12)) / (N_PERM + 1))
    kw = float(stats.kruskal(*[y[lab == u] for u in np.unique(lab)]).pvalue)
    cells = {u: (int((lab == u).sum()), float(y[lab == u].mean())) for u in np.unique(lab)}
    return {"n": len(d), "k": len(cells), "eta": float(obs), "p_perm": p, "p_kw": kw, "cells": cells}


def _bias(nt, variants, ratings, groups, seed):
    if groups is None:
        return pd.DataFrame(), {}
    g = groups.set_index("candidate_id")["group"]
    rows, cells = [], {}
    sty = pd.Series(variants["A"]["share"], index=nt.index)
    base = nt.assign(share=sty.values, group=nt["candidate_id"].map(g))
    cand_style = base.dropna(subset=["group"]).groupby(["reviewer", "candidate_id"]).agg(
        share=("share", "mean"), rank=("rank", "mean"), group=("group", "first")).reset_index()
    rd = ratings.dropna(subset=["resid"]).assign(group=lambda x: x["candidate_id"].map(g)).dropna(subset=["group"])
    cand_dev = rd.groupby(["reviewer", "candidate_id"]).agg(resid=("resid", "mean"), group=("group", "first")).reset_index()
    for outcome, frame, value, covar in (("style", cand_style, "share", "rank"), ("deviation", cand_dev, "resid", None)):
        for rv, d in frame.groupby("reviewer"):
            res = _group_test(d, value, covar, seed + len(rows))
            if res is None:
                continue
            rows.append({"reviewer": rv, "outcome": outcome, "n": res["n"], "k": res["k"], "eta": res["eta"],
                         "p_perm": res["p_perm"], "p_kw": res["p_kw"]})
            for u, (c, m) in res["cells"].items():
                cells[(outcome, rv, u)] = (c, m)
    out = pd.DataFrame(rows)
    if len(out):
        out["p_adj"] = _bh(out["p_perm"])
        out["p_kw_adj"] = _bh(out["p_kw"])
    return out, cells


# ----------------------------------------------------------------------------- main analysis

def analyze(processed_dir: Path) -> dict:
    processed_dir = Path(processed_dir)
    cands = pd.read_csv(processed_dir / "candidates.csv")
    ex = pd.read_csv(processed_dir / "exercises.csv")
    sl = pd.read_csv(processed_dir / "scores_long.csv")
    notes = pd.read_csv(processed_dir / "notes.csv")
    resumes = pd.read_csv(processed_dir / "resumes.csv")

    ratings = _add_signal(_build_ratings(cands, ex, sl), cands)
    R: dict = {"ratings": ratings}
    R["rev_n"] = ratings.groupby("reviewer")["candidate_id"].nunique().to_dict()

    # (1) volume, spread, consistency
    vol = []
    for (rv, role), d in ratings.groupby(["reviewer", "role"]):
        q = np.percentile(d["rank"], [0, 25, 50, 75, 100])
        vol.append({"reviewer": rv, "role": role, "n": len(d), "min": q[0], "q1": q[1], "median": q[2], "q3": q[3], "max": q[4],
                    "sd": float(d["rank"].std(ddof=0)), "iqr": q[3] - q[1], "mean_comp": d["comp_mean"].mean(),
                    "comp_sd": d["comp_sd"].mean(), "halo": d["comp_equal"].mean()})
    R["vol"] = pd.DataFrame(vol).sort_values(["role", "reviewer"]).reset_index(drop=True)
    spread = []
    for role, d in ratings.groupby("role"):
        grp = [x["rank"].to_numpy() for _, x in d.groupby("reviewer") if len(x) >= 3]
        p = float(stats.fligner(*grp).pvalue) if len(grp) >= 2 else np.nan
        spread.append({"role": role, "k": len(grp), "n": int(sum(len(x) for x in grp)), "p": p})
    R["spread"] = pd.DataFrame(spread)

    # (2) deviation models
    dev_rows, var_rows, parts = [], [], []
    for i, role in enumerate(ROLES):
        d = ratings[(ratings["role"] == role) & ratings["signal"].notna()]
        if len(d) < 15 or d["reviewer"].nunique() < 2:
            continue
        rows, vrow, dd = _role_model(d, role, SEED + 10 * i)
        dev_rows += rows
        var_rows.append(vrow)
        parts.append(dd)
    dev = pd.DataFrame(dev_rows)
    var = pd.DataFrame(var_rows)
    if len(dev):
        dev["p_adj"] = _bh(dev["p_perm"])
        dev["p_mw_adj"] = _bh(dev["p_mw"])
        dev["strength"] = [_grade(r.n, bool(np.isfinite(r.ci_lo) and (r.ci_lo > 0 or r.ci_hi < 0)), r.p_adj, r.p_mw_adj, r.p_perm)
                           for r in dev.itertuples()]
    if len(var):
        var["p_adj"] = _bh(var["p_perm"])
    R["dev"], R["var"] = dev, var
    if parts:
        resid = pd.concat(parts)[["candidate_id", "role", "resid"]]
        ratings = ratings.merge(resid, on=["candidate_id", "role"], how="left")
    else:
        ratings["resid"] = np.nan
    R["ratings"] = ratings

    # (3) drift over candidate-number order
    drift = []
    rng = np.random.default_rng(SEED + 100)
    for (role, rv), d in ratings.dropna(subset=["resid", "order"]).groupby(["role", "reviewer"]):
        a, b = d["order"].to_numpy(float), d["resid"].to_numpy(float)
        row = {"role": role, "reviewer": rv, "n": len(d), "rho": np.nan, "lo": np.nan, "hi": np.nan, "tau": np.nan,
               "p_rho": np.nan, "p_tau": np.nan, "slope": np.nan}
        if len(d) >= MIN_TREND and np.ptp(a) > 0 and np.ptp(b) > 0:
            row["rho"], row["p_rho"] = [float(v) for v in stats.spearmanr(a, b)]
            row["tau"], row["p_tau"] = [float(v) for v in stats.kendalltau(a, b)]
            row["lo"], row["hi"] = _boot_ci(_spear, [a, b], rng)
            row["slope"] = float(stats.theilslopes(b, a)[0] * 100 * (np.ptp(a) / 2))  # rank points per half the observed span
        drift.append(row)
    drift = pd.DataFrame(drift)
    if len(drift):
        drift["p_adj"] = _bh(drift["p_rho"])
        drift["p_tau_adj"] = _bh(drift["p_tau"])
        drift["strength"] = [_grade(r.n, bool(np.isfinite(r.lo) and (r.lo > 0 or r.hi < 0)), r.p_adj, r.p_tau_adj, r.p_rho, 15)
                             if np.isfinite(r.rho) else "weak" for r in drift.itertuples()]
    R["drift"] = drift
    ro = ratings.dropna(subset=["resid", "order"])
    if len(ro) >= 12 and ro["order"].nunique() >= 3:
        ro = ro.assign(bin=pd.qcut(ro["order"].rank(method="first"), 3, labels=["Earlier third", "Middle third", "Later third"]))
        R["drift_bins"] = ro.groupby(["reviewer", "bin"], observed=True)["resid"].agg(["mean", "size"]).reset_index()
    else:
        R["drift_bins"] = pd.DataFrame(columns=["reviewer", "bin", "mean", "size"])

    # (4)(5) notes
    nt = _notes_frame(notes, ratings)
    R["nt"] = nt
    R["cons"], R["cons_global"], R["nt_cons"] = pd.DataFrame(), None, nt
    R["style"], R["lex"], R["lex_meta"], R["variants"] = pd.DataFrame(), None, None, None
    if len(nt) >= 30 and nt["candidate_id"].nunique() >= 10:
        nt_c, cons, glob = _consistency(nt, SEED + 200)
        R["nt_cons"], R["cons"], R["cons_global"] = nt_c, cons, glob
        variants, meta = _lexicons(nt)
        R["variants"], R["lex_meta"] = variants, meta
        R["style"] = _style_by_reviewer(nt, variants, SEED + 300)
        nt_style = nt.copy()
        nt_style["share_A"] = variants["A"]["share"]
        nt_style["share_B"] = variants["B"]["share"]
        R["note_style"] = nt_style[["candidate_id", "role", "reviewer", "rank", "share_A", "share_B"]]

    # (6) bias by resume group
    groups, ginfo = _resume_groups(resumes)
    R["groups"], R["group_info"] = groups, ginfo
    if R["variants"] is not None:
        R["bias"], R["bias_cells"] = _bias(nt, R["variants"], ratings, groups, SEED + 400)
    else:
        R["bias"], R["bias_cells"] = pd.DataFrame(), {}

    # (7) agreement
    rng = np.random.default_rng(SEED + 500)
    pairs = []
    rank_w = ratings.pivot(index="candidate_id", columns="role", values="rank")
    rev_w = ratings.pivot(index="candidate_id", columns="role", values="reviewer")
    for i, a in enumerate(AC):
        for b in AC[i + 1:]:
            if a in rank_w.columns and b in rank_w.columns:
                m = rank_w[[a, b]].dropna().join(rev_w[[a, b]].add_suffix("_rv"), how="left")
                same = int((m[f"{a}_rv"] == m[f"{b}_rv"]).sum())
                m = m[m[f"{a}_rv"] != m[f"{b}_rv"]]
                if len(m) >= MIN_SHARE:
                    x, y = m[a].to_numpy(), m[b].to_numpy()
                    lo, hi = _boot_ci(_spear, [x, y], rng)
                    pairs.append({"a": a, "b": b, "n": len(m), "same": same, "rho": _spear(x, y), "lo": lo, "hi": hi,
                                  "tau": float(stats.kendalltau(x, y).statistic), "p": float(stats.spearmanr(x, y).pvalue)})
    R["pairs"] = pd.DataFrame(pairs)
    conv = []
    for (role, rv), d in ratings.dropna(subset=["signal"]).groupby(["role", "reviewer"]):
        if role == TI:
            continue
        x, y = d["signal"].to_numpy(), d["rank"].to_numpy()
        lo, hi = _boot_ci(_spear, [x, y], rng) if len(d) >= MIN_SHARE else (np.nan, np.nan)
        conv.append({"role": role, "reviewer": rv, "n": len(d), "rho": _spear(x, y), "lo": lo, "hi": hi})
    R["conv"] = pd.DataFrame(conv)
    tir = []
    t = ratings[ratings["role"] == TI].merge(
        cands.drop_duplicates("candidate_id")[["candidate_id", "ac_pct"]], on="candidate_id").dropna(subset=["ac_pct"])
    t["ac_rank"] = _pct_rank(t["ac_pct"]) if len(t) else np.nan
    for rv, d in [("All recruiters", t)] + list(t.groupby("reviewer")):
        if len(d) >= MIN_SHARE:
            x, y = d["rank"].to_numpy(), d["ac_rank"].to_numpy()
            lo, hi = _boot_ci(_spear, [x, y], rng)
            tir.append({"reviewer": rv, "n": len(d), "rho": _spear(x, y), "lo": lo, "hi": hi,
                        "tau": float(stats.kendalltau(x, y).statistic), "p": float(stats.spearmanr(x, y).pvalue)})
    R["ti_ac"] = pd.DataFrame(tir)
    R["n_ti_total"] = int((ratings["role"] == TI).sum())
    return R


# ----------------------------------------------------------------------------- rendering

def _fmt(x, nd=3):
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{nd}f}"


def _render(R: dict, share: bool) -> dict:
    rev_n = R["rev_n"]

    def hide(rv, n=None):
        return share and (rev_n.get(rv, 0) < MIN_SHARE or (n is not None and n < MIN_SHARE))

    def val(rv, n, v, scale=1.0, nd=4):
        if hide(rv, n) or v is None or not np.isfinite(v):
            return None
        return round(float(v) * scale, nd)

    findings: list[dict] = []

    def add(text, strength, evidence, revs=()):
        if share and any(rev_n.get(r, 0) < MIN_SHARE for r in revs):
            return
        findings.append({"text": text, "strength": strength, "evidence": evidence})

    charts: list[dict] = []
    vol, dev, var, drift = R["vol"], R["dev"], R["var"], R["drift"]

    # (1) volume and distribution
    groups = []
    for r in vol.itertuples():
        h = hide(r.reviewer, r.n)
        groups.append({"name": f"{r.reviewer} | {r.role}", "n": int(r.n), "suppressed": h,
                       **{k: (None if h else round(float(getattr(r, k)) * 100, 1)) for k in ("min", "q1", "median", "q3", "max")}})
    charts.append({"id": "rank-boxplot", "type": "boxplot", "title": "Percentile rank of scores given, by reviewer and exercise",
                   "subtitle": "Percentile rank within the exercise across all rated candidates (0-100); groups under 5 are suppressed in the shareable copy",
                   "x_label": "Reviewer | exercise", "y_label": "Percentile rank", "data": {"groups": groups}})
    rows = []
    for r in vol.itertuples():
        h = hide(r.reviewer, r.n)
        rows.append([r.reviewer, r.role, int(r.n), h] + [None if h else (None if not np.isfinite(v) else round(float(v), 3))
                                                         for v in (r.median * 100, r.sd * 100, r.iqr * 100, r.mean_comp, r.comp_sd, r.halo)])
    charts.append({"id": "volume-table", "type": "table", "title": "Reviewer volume, spread and consistency",
                   "subtitle": "Spread = SD of percentile rank. Within-candidate competency SD and share of all-equal competency scores indicate halo/flat scoring (exercises only).",
                   "data": {"columns": ["Reviewer", "Exercise", "n rated", "Suppressed", "Median rank", "SD of rank", "IQR of rank",
                                        "Mean competency score (1-4)", "Mean within-candidate competency SD", "Share all-equal competencies"],
                            "rows": rows}})
    sp = R["spread"]
    charts.append({"id": "spread-table", "type": "table", "title": "Do reviewers differ in how widely they spread their scores?",
                   "subtitle": "Fligner-Killeen test of equal rank spread across reviewers (reviewers with at least 3 ratings)",
                   "data": {"columns": ["Exercise", "Reviewers", "n ratings", "p (equal spread)"],
                            "rows": [[r.role, int(r.k), int(r.n), None if not np.isfinite(r.p) else round(float(r.p), 4)] for r in sp.itertuples()]}})
    for _, r in sp.iterrows():
        if np.isfinite(r["p"]) and r["p"] < 0.10:
            add(f"Reviewers differ in how widely they spread {r['role']} scores (some use a narrower or wider range of the rank scale).",
                "suggestive" if r["p"] < 0.05 else "weak", f"n={int(r['n'])} ratings, {int(r['k'])} reviewers, Fligner-Killeen p={r['p']:.3f}")

    # (2) deviation
    if len(dev):
        lab = [f"{r.reviewer} | {r.role}" for r in dev.itertuples()]
        sup = [hide(r.reviewer, r.n) for r in dev.itertuples()]
        charts.append({"id": "deviation-hbar", "type": "hbar",
                       "title": "Reviewer deviation from what other signals predict (shrunken estimate with 95% bootstrap CI)",
                       "subtitle": "Percentile-rank points relative to the average reviewer in that exercise, after adjusting for independent signals. Positive = higher scores than other signals predict (possible leniency); negative = lower (possible severity). For review, not a verdict.",
                       "x_label": "Percentile-rank points", "y_label": "Reviewer | exercise",
                       "data": {"labels": lab, "suppressed": sup, "series": [
                           {"name": "Shrunken deviation", "values": [val(r.reviewer, r.n, r.dev, 100, 2) for r in dev.itertuples()]},
                           {"name": "CI lower", "values": [val(r.reviewer, r.n, r.ci_lo, 100, 2) for r in dev.itertuples()]},
                           {"name": "CI upper", "values": [val(r.reviewer, r.n, r.ci_hi, 100, 2) for r in dev.itertuples()]}]}})
        rows = []
        for r in dev.itertuples():
            h = hide(r.reviewer, r.n)
            rows.append([r.reviewer, r.role, int(r.n), h] + [None if h else (None if not np.isfinite(v) else round(float(v), 4)) for v in (
                r.raw * 100, r.dev * 100, r.shrink, r.ci_lo * 100, r.ci_hi * 100, r.p_perm, r.p_adj, r.p_mw_adj)] + [None if h else r.strength])
        charts.append({"id": "deviation-table", "type": "table", "title": "Reviewer deviation: all estimates",
                       "subtitle": "Raw = mean residual; shrunken = empirical-Bayes random-intercept estimate; p = permutation of reviewer labels; adj = Benjamini-Hochberg across all reviewer-exercise units; MW = rank-sum test of residuals vs other reviewers",
                       "data": {"columns": ["Reviewer", "Exercise", "n", "Suppressed", "Raw deviation (pts)", "Shrunken deviation (pts)", "Shrinkage factor",
                                            "CI lower (pts)", "CI upper (pts)", "Permutation p", "Adjusted p", "Rank-sum adjusted p", "Strength"], "rows": rows}})
    if len(var):
        rows = [[r.role, int(r.n), int(r.k)] + [None if not np.isfinite(v) else round(float(v), 4) for v in (
            r.icc_unadj, r.icc_adj, r.icc_ci_lo, r.icc_ci_hi, r.icc_mixed, r.p_perm, r.p_adj)] for r in var.itertuples()]
        charts.append({"id": "variance-table", "type": "table", "title": "Share of rank variance attributable to reviewer identity",
                       "subtitle": "Unadjusted share is confounded with candidate pool; adjusted share is after independent signals. Permutation p tests against shuffled reviewer labels.",
                       "data": {"columns": ["Exercise", "n", "Reviewers", "ICC unadjusted", "ICC adjusted", "ICC CI lower", "ICC CI upper",
                                            "ICC mixed model", "Permutation p", "Adjusted p"], "rows": rows}})
        for r in var.itertuples():
            ok_ci = np.isfinite(r.icc_ci_lo) and r.icc_ci_lo > 0
            mixed_ok = np.isfinite(r.icc_mixed) and r.icc_mixed > 0
            s = "robust" if (r.p_adj < 0.05 and ok_ci and mixed_ok) else "suggestive" if (r.p_perm < 0.05 or r.p_adj < 0.10) else "weak"
            add(f"For {r.role}, reviewer identity {'explains more rank variance than chance' if s != 'weak' else 'does not explain more rank variance than chance'} "
                f"after adjusting for independent signals.", s,
                f"n={int(r.n)}, {int(r.k)} reviewers, adjusted ICC={_fmt(r.icc_adj)} (unadjusted {_fmt(r.icc_unadj)}, mixed model {_fmt(r.icc_mixed)}), "
                f"permutation p={r.p_perm:.3f} (adj {r.p_adj:.3f}), bootstrap CI [{_fmt(r.icc_ci_lo)}, {_fmt(r.icc_ci_hi)}]")
    if len(dev):
        flagged = dev[dev["strength"] != "weak"]
        for r in flagged.sort_values("p_adj").itertuples():
            direction = "higher" if r.dev > 0 else "lower"
            add(f"{r.reviewer} gave {r.role} scores that are {direction} than other signals predict for the same candidates "
                f"(possible {'leniency' if r.dev > 0 else 'severity'}; for review, not a verdict).", r.strength,
                f"n={int(r.n)}, shrunken deviation={r.dev * 100:+.1f} percentile-rank points (raw {r.raw * 100:+.1f}), 95% CI [{r.ci_lo * 100:+.1f}, {r.ci_hi * 100:+.1f}], "
                f"permutation p adj={r.p_adj:.3f}, rank-sum p adj={r.p_mw_adj:.3f}", [r.reviewer])
        if flagged.empty:
            add("No reviewer-exercise deviates from independent signals by more than chance would produce.", "weak",
                f"n={int(dev['n'].sum())} ratings in {len(dev)} reviewer-exercise units, smallest adjusted permutation p={dev['p_adj'].min():.3f}")
    if len(dev):
        for role, d in R["ratings"].dropna(subset=["signal"]).groupby("role"):
            charts.append({"id": f"signal-scatter-{re.sub('[^a-z]+', '-', role.lower())}", "type": "scatter",
                           "title": f"{role}: independent signal vs rank given",
                           "subtitle": "Each point is one rated candidate; x = mean percentile rank from other instruments/reviewers, y = rank given by this exercise's reviewer",
                           "x_label": "Independent signal (percentile rank)", "y_label": "Rank given (percentile rank)",
                           "data": {"points": [{"x": round(float(p.signal), 4), "y": round(float(p.rank), 4),
                                                "label": None if share else str(p.candidate_id), "group": p.reviewer}
                                               for p in d.itertuples() if not hide(p.reviewer)]}})

    # (3) drift
    if len(drift):
        tested = drift[np.isfinite(drift["rho"])]
        charts.append({"id": "drift-hbar", "type": "hbar", "title": "Trend of reviewer deviation across candidate-number order (Spearman rho, 95% CI)",
                       "subtitle": "Candidate number is only a rough proxy for time order; units with fewer than 8 ratings are not tested",
                       "x_label": "Spearman rho (deviation vs candidate number)", "y_label": "Reviewer | exercise",
                       "data": {"labels": [f"{r.reviewer} | {r.role}" for r in tested.itertuples()],
                                "suppressed": [hide(r.reviewer, r.n) for r in tested.itertuples()],
                                "series": [{"name": "rho", "values": [val(r.reviewer, r.n, r.rho) for r in tested.itertuples()]},
                                           {"name": "CI lower", "values": [val(r.reviewer, r.n, r.lo) for r in tested.itertuples()]},
                                           {"name": "CI upper", "values": [val(r.reviewer, r.n, r.hi) for r in tested.itertuples()]}]}})
        rows = []
        for r in drift.itertuples():
            h = hide(r.reviewer, r.n)
            rows.append([r.reviewer, r.role, int(r.n), h] + [None if h else (None if not np.isfinite(v) else round(float(v), 4)) for v in (
                r.rho, r.lo, r.hi, r.tau, r.p_rho, r.p_adj, r.p_tau_adj)] + [None if h else r.strength])
        charts.append({"id": "drift-table", "type": "table", "title": "Drift tests per reviewer and exercise",
                       "data": {"columns": ["Reviewer", "Exercise", "n", "Suppressed", "Spearman rho", "CI lower", "CI upper", "Kendall tau",
                                            "p (Spearman)", "Adjusted p (Spearman)", "Adjusted p (Kendall)", "Strength"], "rows": rows}})
        flagged = drift[drift["strength"] != "weak"]
        for r in flagged.sort_values("p_adj").itertuples():
            add(f"{r.reviewer}'s {r.role} scores relative to other signals trend {'upward' if r.rho > 0 else 'downward'} with candidate number.", r.strength,
                f"n={int(r.n)}, Spearman rho={r.rho:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}], adjusted p={r.p_adj:.3f} (Kendall adjusted {r.p_tau_adj:.3f})", [r.reviewer])
        if flagged.empty and len(tested):
            add("No reviewer shows a trend in scoring across candidate-number order beyond chance (candidate number is a rough time proxy).", "weak",
                f"n={int(tested['n'].sum())} ratings in {len(tested)} units tested (>=8 each), smallest adjusted p={tested['p_adj'].min():.3f}")
    db = R["drift_bins"]
    if len(db):
        bins = ["Earlier third", "Middle third", "Later third"]
        series = []
        for rv in sorted(db["reviewer"].unique()):
            vals = []
            for b in bins:
                m = db[(db["reviewer"] == rv) & (db["bin"] == b)]
                vals.append(None if m.empty or (hide(rv, int(m["size"].iloc[0])) or (not share and int(m["size"].iloc[0]) < 2))
                            else round(float(m["mean"].iloc[0]) * 100, 2))
            series.append({"name": rv, "values": vals})
        charts.append({"id": "drift-line", "type": "line", "title": "Mean deviation by candidate-number third",
                       "subtitle": "Thirds of candidate number (data-derived, display only); percentile-rank points of residual vs independent signals, pooled over exercises",
                       "x_label": "Candidate-number third", "y_label": "Mean residual (pts)", "data": {"labels": bins, "series": series}})

    # (4) notes vs scores
    cons, glob, nt = R["cons"], R["cons_global"], R["nt_cons"]
    if glob is not None:
        rows = []
        for r in cons.itertuples():
            h = hide(r.reviewer, r.n)
            rows.append([r.reviewer, int(r.n), h] + [None if h else (None if not np.isfinite(v) else round(float(v), 4)) for v in (
                r.rho, r.lo, r.hi, r.same, r.gap, r.gap_others)] + [None if h else int(r.n_opp), None if h else (None if not np.isfinite(r.p_adj) else round(float(r.p_adj), 4))])
        charts.append({"id": "notes-consistency-table", "type": "table",
                       "title": "Do written notes agree with the scores each reviewer gave?",
                       "subtitle": "Cross-validated text-only model (TF-IDF + ridge, folds grouped by candidate) predicts the rank from the note alone. Agreement = note-implied and given rank fall in the same data-derived tercile; mismatch = opposite terciles.",
                       "data": {"columns": ["Reviewer", "n notes", "Suppressed", "Spearman rho (note vs score)", "CI lower", "CI upper", "Same-tercile agreement",
                                            "Mean rank gap", "Mean rank gap, other reviewers", "Opposite-tercile mismatches", "Gap vs others, adjusted p"], "rows": rows}})
        charts.append({"id": "notes-consistency-hbar", "type": "hbar", "title": "Agreement rate between note tone and score, per reviewer",
                       "x_label": "Share of notes in same tercile", "y_label": "Reviewer",
                       "data": {"labels": cons["reviewer"].tolist(), "suppressed": [hide(r.reviewer, r.n) for r in cons.itertuples()],
                                "series": [{"name": "Same-tercile agreement", "values": [val(r.reviewer, r.n, r.same) for r in cons.itertuples()]}]}})
        mm = nt[nt["opposite"]]
        if share:
            rows = [[r.reviewer, int(r.n_opp)] for r in cons.itertuples() if not hide(r.reviewer, r.n)]
            charts.append({"id": "notes-mismatches", "type": "table", "title": "Note-vs-score mismatches (counts only in the shareable copy)",
                           "data": {"columns": ["Reviewer", "Opposite-tercile mismatches"], "rows": rows}})
        else:
            rows = [[r.candidate_id, r.reviewer, r.role, round(float(r.rank), 3), round(float(r.text_rank), 3)] for r in mm.sort_values(["reviewer", "candidate_id"]).itertuples()]
            charts.append({"id": "notes-mismatches", "type": "table", "title": "Note-vs-score mismatches (candidate ids; local copy only)",
                           "subtitle": "Opposite terciles between the rank implied by the written note and the rank actually given; for human re-reading, not a verdict",
                           "data": {"columns": ["candidate_id", "Reviewer", "Source", "Rank given", "Rank implied by note"], "rows": rows}})
        s = "robust" if (glob["p"] < 0.01 and glob["lo"] > 0 and np.isfinite(glob["tau"]) and glob["tau"] > 0) else "suggestive" if glob["p"] < 0.05 else "weak"
        add("Across reviewers, the written tone of notes tracks the scores given (notes alone recover the rank order).", s,
            f"n={glob['n']} notes, cross-validated Spearman rho={glob['rho']:.2f} [{glob['lo']:.2f}, {glob['hi']:.2f}], Kendall tau={glob['tau']:.2f}, "
            f"same-tercile agreement={glob['same']:.2f}")
        for r in cons[cons["p_adj"] < 0.10].itertuples():
            worse = r.gap > r.gap_others
            add(f"{r.reviewer}'s written notes {'disagree more' if worse else 'agree more'} with their scores than other reviewers' notes do.",
                "suggestive" if r.p_adj < 0.05 else "weak",
                f"n={int(r.n)} notes, mean rank gap {r.gap:.2f} vs {r.gap_others:.2f} others, rank-sum adjusted p={r.p_adj:.3f}", [r.reviewer])

    # (5) language style
    style, variants, lm = R["style"], R["variants"], R["lex_meta"]
    if len(style):
        a = style[style["variant"] == "A"]
        charts.append({"id": "style-hbar", "type": "hbar", "title": "Share of subjective-style language in each reviewer's notes",
                       "subtitle": "Share = score-unanchored occasional terms / (those + score-anchored evidence terms), per note, averaged; 95% bootstrap CI",
                       "x_label": "Subjective-style share", "y_label": "Reviewer",
                       "data": {"labels": a["reviewer"].tolist(), "suppressed": [hide(r.reviewer, r.n) for r in a.itertuples()],
                                "series": [{"name": "Mean share", "values": [val(r.reviewer, r.n, r.mean) for r in a.itertuples()]},
                                           {"name": "CI lower", "values": [val(r.reviewer, r.n, r.lo) for r in a.itertuples()]},
                                           {"name": "CI upper", "values": [val(r.reviewer, r.n, r.hi) for r in a.itertuples()]},
                                           {"name": "Other reviewers", "values": [val(r.reviewer, r.n, r.others) for r in a.itertuples()]}]}})
        b = style[style["variant"] == "B"].set_index("reviewer")
        rows = []
        for r in a.itertuples():
            h = hide(r.reviewer, r.n)
            rb = b.loc[r.reviewer] if r.reviewer in b.index else None
            rows.append([r.reviewer, int(r.n_all), h] + [None if h else (None if not np.isfinite(v) else round(float(v), 4)) for v in (
                r.mean, r.lo, r.hi, r.others, r.p_adj, None if rb is None else rb["mean"], None if rb is None else rb["p_adj"])])
        charts.append({"id": "style-table", "type": "table", "title": "Language style per reviewer (two lexicon definitions)",
                       "subtitle": "Lexicon A and B differ in how strictly terms are called score-anchored vs score-unrelated; a finding is robust only if both agree.",
                       "data": {"columns": ["Reviewer", "n notes", "Suppressed", "Share (lexicon A)", "CI lower", "CI upper", "Share, other reviewers",
                                            "Rank-sum adjusted p (A)", "Share (lexicon B)", "Rank-sum adjusted p (B)"], "rows": rows}})
        charts.append({"id": "style-lexicon-table", "type": "table", "title": "Data-derived vocabulary behind the style measure",
                       "subtitle": "Evidence-style = terms whose use rises or falls with the score given (Spearman, BH-corrected). Subjective-style = occasional terms (below median document frequency) unrelated to the score. Top terms shown only.",
                       "data": {"columns": ["Lexicon", "Style", "n terms", "Top terms"],
                                "rows": [[v, "Evidence-style", i["n_ev"], ", ".join(i["ev_terms"])] for v, i in variants.items()]
                                + [[v, "Subjective-style", i["n_imp"], ", ".join(i["imp_terms"])] for v, i in variants.items()]}})
        for r in a.itertuples():
            rb = b.loc[r.reviewer] if r.reviewer in b.index else None
            if np.isfinite(r.p_adj) and r.p_adj < 0.10 and rb is not None:
                both = np.isfinite(rb["p_adj"]) and rb["p_adj"] < 0.10 and (rb["mean"] > rb["others"]) == (r.mean > r.others)
                s = "robust" if (r.p_adj < 0.05 and both and r.lo > r.others if r.mean > r.others else False) else "suggestive" if r.p_adj < 0.05 else "weak"
                add(f"{r.reviewer} uses {'more' if r.mean > r.others else 'less'} subjective-style (score-unrelated) language than other reviewers.", s,
                    f"n={int(r.n_all)} notes, share {r.mean:.3f} vs {r.others:.3f} others, rank-sum adjusted p={r.p_adj:.3f} (lexicon B {rb['p_adj']:.3f})", [r.reviewer])

    # (6) bias by resume group
    bias, gi = R["bias"], R["group_info"]
    if gi is not None:
        charts.append({"id": "resume-groups-table", "type": "table", "title": "Data-derived resume groups",
                       "subtitle": f"TF-IDF + KMeans on resumes; k={gi['k']} chosen as the smallest k with silhouette within 10% of the best (silhouette: "
                                   + ", ".join(f"k={k}:{v:.2f}" for k, v in sorted(gi['silhouette'].items())) + "). Top terms are cluster-centroid terms.",
                       "data": {"columns": ["Group", "n resumes", "Suppressed", "Top terms"],
                                "rows": [[g["group"], None if share and g["n"] < MIN_SHARE else g["n"], share and g["n"] < MIN_SHARE,
                                          None if share and g["n"] < MIN_SHARE else g["top_terms"]] for g in gi["groups"]]}})
    if len(bias):
        rows = []
        for r in bias.itertuples():
            h = hide(r.reviewer, r.n)
            s = _grade(r.n, True, r.p_adj, r.p_kw_adj, r.p_perm, 15)
            rows.append([r.reviewer, r.outcome, int(r.n), h] + [None if h else (None if not np.isfinite(v) else round(float(v), 4)) for v in (
                r.eta, r.p_perm, r.p_adj, r.p_kw_adj)] + [None if h else s])
        charts.append({"id": "bias-table", "type": "table", "title": "Does a reviewer's language style or score deviation differ by resume group?",
                       "subtitle": "Style: subjective-share vs resume group, conditional on the score rank given. Deviation: residual vs independent signals by resume group. eta = share of variance between groups; p = permutation of group labels over candidates; adjusted across all tests.",
                       "data": {"columns": ["Reviewer", "Outcome", "n candidates", "Suppressed", "Between-group variance share", "Permutation p",
                                            "Adjusted p", "Rank-based (Kruskal) adjusted p", "Strength"], "rows": rows}})
        for outcome in ("style", "deviation"):
            cells = {k: v for k, v in R["bias_cells"].items() if k[0] == outcome}
            revs = sorted({k[1] for k in cells})
            gl = [g["group"] for g in gi["groups"]]
            vals = []
            for rv in revs:
                row = []
                for g in gl:
                    c = cells.get((outcome, rv, g))
                    row.append(None if c is None or hide(rv, c[0]) or (not share and c[0] < 2) else round(c[1] * 100, 2))
                vals.append(row)
            if revs:
                flat = [abs(v) for row in vals for v in row if v is not None]
                m = max(flat) if flat else 1.0
                charts.append({"id": f"bias-heatmap-{outcome}", "type": "heatmap",
                               "title": f"{'Subjective-style share' if outcome == 'style' else 'Score deviation'}: mean {'rank-adjusted ' if outcome == 'style' else ''}residual by resume group",
                               "subtitle": "Percentage points; cells under 5 candidates suppressed in the shareable copy",
                               "data": {"row_labels": revs, "col_labels": gl, "values": vals, "min": -m, "max": m}})
        for r in bias.sort_values("p_adj").itertuples():
            if r.p_adj >= 0.10 and r.p_perm >= 0.05:
                continue
            s = _grade(r.n, True, r.p_adj, r.p_kw_adj, r.p_perm, 15)
            cells = {k[2]: v for k, v in R["bias_cells"].items() if k[0] == r.outcome and k[1] == r.reviewer}
            hi_g = max(cells, key=lambda k: cells[k][1]) if cells else "n/a"
            lo_g = min(cells, key=lambda k: cells[k][1]) if cells else "n/a"
            what = "subjective-style language share (given the score rank)" if r.outcome == "style" else "score deviation"
            add(f"{r.reviewer}'s {what} differs by resume group (highest in {hi_g}, lowest in {lo_g}); this is a flag for review, not evidence of intent.", s,
                f"n={int(r.n)} candidates, {int(r.k)} groups, variance share between groups={r.eta:.2f}, permutation p={r.p_perm:.3f} (adjusted {r.p_adj:.3f}), "
                f"Kruskal adjusted p={r.p_kw_adj:.3f}", [r.reviewer])
        if not any(f["text"].find("resume group") >= 0 for f in findings):
            add("No reviewer's language style or score deviation differs by resume group beyond chance.", "weak",
                f"n={int(bias['n'].sum())} candidate-reviewer pairs in {len(bias)} tests, smallest adjusted p={bias['p_adj'].min():.3f}")

    # (7) agreement
    pairs, conv, tia = R["pairs"], R["conv"], R["ti_ac"]
    if len(pairs):
        charts.append({"id": "agreement-pairs-table", "type": "table", "title": "Agreement between different assessors who scored the same candidate",
                       "subtitle": "Only candidates whose two exercises were scored by different assessors; rank correlations with bootstrap CI",
                       "data": {"columns": ["Exercise A", "Exercise B", "n candidates", "Same-assessor pairs excluded", "Spearman rho", "CI lower", "CI upper", "Kendall tau", "p"],
                                "rows": [[r.a, r.b, int(r.n), int(r.same)] + [round(float(v), 4) for v in (r.rho, r.lo, r.hi, r.tau, r.p)] for r in pairs.itertuples()]}})
        for r in pairs.itertuples():
            s = "robust" if (r.lo > 0 and r.p < 0.01 and r.tau > 0) else "suggestive" if r.p < 0.05 else "weak"
            add(f"{r.a} and {r.b} ranks agree across different assessors {'strongly' if r.rho >= 0.5 else 'moderately' if r.rho >= 0.3 else 'weakly'}.", s,
                f"n={int(r.n)} candidates, Spearman rho={r.rho:.2f} [{r.lo:.2f}, {r.hi:.2f}], Kendall tau={r.tau:.2f}, p={r.p:.3g}")
    if len(conv):
        charts.append({"id": "agreement-reviewer-hbar", "type": "hbar", "title": "Agreement of each reviewer's ranks with the independent signal (Spearman rho)",
                       "subtitle": "Low agreement can mean a noisy rater or a different construct; it cannot distinguish the two",
                       "x_label": "Spearman rho", "y_label": "Reviewer | exercise",
                       "data": {"labels": [f"{r.reviewer} | {r.role}" for r in conv.itertuples()], "suppressed": [hide(r.reviewer, r.n) for r in conv.itertuples()],
                                "series": [{"name": "rho", "values": [val(r.reviewer, r.n, r.rho) for r in conv.itertuples()]},
                                           {"name": "CI lower", "values": [val(r.reviewer, r.n, r.lo) for r in conv.itertuples()]},
                                           {"name": "CI upper", "values": [val(r.reviewer, r.n, r.hi) for r in conv.itertuples()]}]}})
    if len(tia):
        rows = []
        for r in tia.itertuples():
            h = r.reviewer != "All recruiters" and hide(r.reviewer, r.n)
            rows.append([r.reviewer, int(r.n), h] + [None if h else round(float(v), 4) for v in (r.rho, r.lo, r.hi, r.tau, r.p)])
        charts.append({"id": "agreement-ti-table", "type": "table", "title": "Technical-interview scores vs later assessment-center performance, by recruiter",
                       "subtitle": "Range-restricted: only candidates who passed the technical interview attended the assessment center. Past decisions, not job performance.",
                       "data": {"columns": ["Recruiter", "n candidates", "Suppressed", "Spearman rho", "CI lower", "CI upper", "Kendall tau", "p"], "rows": rows}})
        for r in tia.itertuples():
            if r.reviewer == "All recruiters":
                s = "robust" if (r.lo > 0 and r.p < 0.01 and r.tau > 0) else "suggestive" if r.p < 0.05 else "weak"
                add("Technical-interview scores agree with later assessment-center rank among candidates who advanced (range-restricted).", s,
                    f"n={int(r.n)}, Spearman rho={r.rho:.2f} [{r.lo:.2f}, {r.hi:.2f}], Kendall tau={r.tau:.2f}, p={r.p:.3g}")

    # (8) what was and was not testable
    testable = [
        ["Does a reviewer score higher/lower than other independent signals predict?", "Partly",
         "Yes as deviation from other exercises scored by different assessors and the technical-interview score; the estimate is shrunken and assumes those signals are unbiased."],
        ["Is a reviewer lenient, or did they simply see a stronger candidate pool?", "No",
         "Only one rater per candidate per exercise, so own scores cannot separate leniency from pool strength; only the deviation from other signals is estimable."],
        ["Do reviewers differ more than chance?", "Yes", "Permutation test of reviewer labels plus an ICC-style variance share, with multiple-testing correction."],
        ["Is a reviewer consistent over time?", "Roughly", "Candidate number is only a rough proxy for time order; real dates would be needed."],
        ["Do written notes match the scores?", "Yes", "Cross-validated text-only rank model; agreement is rank-based with data-derived terciles."],
        ["Is subjective language a bias?", "No", "Style share is measured and compared by resume group; it indicates a pattern to review, not intent or discrimination."],
        ["Do reviewers treat resume groups differently?", "Partly", "Tested conditional on score rank and on deviation, but groups are data-derived and small per reviewer."],
        ["Do two assessors agree on the same candidate?", "Yes", "Across different exercises only; it mixes rater noise with real differences between exercises."],
        ["Do recruiter scores predict later performance?", "Partly", "Only for candidates who advanced (range-restricted); outcomes are past decisions, not job performance."],
        ["Inter-rater reliability within one exercise", "No", "No candidate is rated twice in the same exercise."],
    ]
    charts.append({"id": "testability-table", "type": "table", "title": "What was and was not testable with one rater per candidate",
                   "data": {"columns": ["Question", "Testable?", "How it was handled or why not"], "rows": testable}})

    caveats = [
        "Each candidate is rated by one person per exercise, so reviewer leniency cannot be separated from candidate pool strength using that reviewer's scores alone.",
        "Reviewer deviation is measured against independent signals (other exercises scored by different assessors, the technical-interview score; for recruiters, the later assessment-center rank) and is shrunk toward zero.",
        "Deviations are relative to the average reviewer in each exercise, so one strongly lenient reviewer pulls the others slightly negative.",
        "The technical-interview signal is range-restricted: only candidates who passed earlier gates have later-stage scores, and none were imputed.",
        "Candidate number is a rough proxy for time order; trends may reflect candidate-pool changes rather than reviewer drift.",
        "Language-style vocabulary and resume groups are derived from the data and are heuristic; style findings are only robust when two lexicon definitions agree.",
        "Small reviewer-by-exercise groups give wide intervals; groups under 5 are suppressed in the shareable copy.",
        "Flags are for review, not verdicts on individuals. Outcomes are past human decisions, not job performance.",
    ]
    return {"section": SECTION, "title": "Interviewer and reviewer trends", "caveats": caveats, "findings": findings, "charts": charts}


def run(processed_dir: Path, results_dir: Path) -> None:
    R = analyze(Path(processed_dir))
    for kind, share in (("local", False), ("shareable", True)):
        out = Path(results_dir) / kind
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{SECTION}.json").write_text(json.dumps(_clean(_render(R, share)), indent=2))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from settings import load_settings

    out_dir = load_settings()["out_dir"]
    run(out_dir, out_dir / "results")
    print(f"wrote {SECTION} results to {out_dir / 'results'}")
