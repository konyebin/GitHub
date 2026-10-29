"""Resume and notes themes (sections `resume_themes` and `notes_themes`).

Everything is bottom-up and rank-based: TF-IDF + NMF topics (number of topics chosen from coherence and seed/subsample
stability), rank correlations with permutation p-values, bootstrap CIs and Benjamini-Hochberg correction. No fixed score
cutoffs, no external models, no free text in any output (top terms and aggregates only).

Outcomes are past human decisions, not job performance. Later-stage scores exist only for candidates who passed earlier
gates and are never imputed.

Run: python hiring-analysis/analysis/text_themes.py   (reads HIRING_OUT_DIR like pipeline/loader.py)
"""

from __future__ import annotations

import copy
import json
import os
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import RepeatedKFold
import statsmodels.api as sm

warnings.filterwarnings("ignore")

SEED = 20240607
N_PERM = 10000
N_BOOT = 1000
N_SUB = 300
MIN_GROUP = 5  # groups, terms and cells with fewer candidates/notes are never reported in the shareable copy
MIN_DOCS_FOR_TOPICS = 20
EXERCISES = ("Interview", "Role Play", "Presentation")
SOURCES = ("Technical interview", "Interview", "Role Play", "Presentation", "Overall")
DECISION_ORDER = {"No Hire": 0, "Standby": 1, "Hire": 2}
TOKEN = r"(?u)\b[a-z][a-z0-9+#]+\b"
_TOK = re.compile(TOKEN)
_SENT = re.compile(r"[.;!?\n|]+")


def _stop_words() -> frozenset:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    return ENGLISH_STOP_WORDS


def sentence_analyzer(text: str) -> list[str]:
    """Unigrams plus bigrams that never cross a sentence/line boundary; English stop words dropped."""
    sw = _stop_words()
    out: list[str] = []
    for sent in _SENT.split(str(text).lower()):
        toks = [t for t in _TOK.findall(sent) if t not in sw]
        out.extend(toks)
        out.extend(f"{a} {b}" for a, b in zip(toks, toks[1:]))
    return out


# --------------------------------------------------------------------------- generic statistics

def pct_rank(x) -> np.ndarray:
    """Within-cohort percentile rank in (0, 1); NaN stays NaN."""
    s = pd.Series(np.asarray(x, dtype=float))
    ok = s.notna()
    out = np.full(len(s), np.nan)
    if ok.sum():
        out[ok.values] = (stats.rankdata(s[ok].values) - 0.5) / ok.sum()
    return out


def bh(p) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    q = np.full(p.shape, np.nan)
    ok = ~np.isnan(p)
    if not ok.any():
        return q
    pv = p[ok]
    m = len(pv)
    order = np.argsort(pv)
    adj = pv[order] * m / (np.arange(m) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    res = np.empty(m)
    res[order] = np.minimum(adj, 1.0)
    q[ok] = res
    return q


def effect_label(r: float | None) -> str:
    if r is None or not np.isfinite(r):
        return "n/a"
    a = abs(r)
    return "negligible" if a < 0.1 else "small" if a < 0.3 else "moderate" if a < 0.5 else "large"


def _z(a: np.ndarray, axis=0) -> np.ndarray:
    a = a - a.mean(axis=axis, keepdims=True)
    sd = np.sqrt((a ** 2).sum(axis=axis, keepdims=True))
    sd[sd == 0] = np.nan
    return a / sd


def _perm_index(n: int, strata: np.ndarray | None, chunk: int, rng: np.random.Generator) -> np.ndarray:
    if strata is None:
        return rng.permuted(np.tile(np.arange(n), (chunk, 1)), axis=1)
    idx = np.zeros((chunk, n), dtype=int)
    for s in np.unique(strata):
        pos = np.where(strata == s)[0]
        idx[:, pos] = pos[rng.permuted(np.tile(np.arange(len(pos)), (chunk, 1)), axis=1)]
    return idx


def spearman_scan(X: np.ndarray, y: np.ndarray, rng: np.random.Generator, strata=None, n_perm: int = N_PERM):
    """Spearman rho of every column of X against y with two-sided permutation p-values (optionally stratified)."""
    n, m = X.shape
    Xz = _z(stats.rankdata(X, axis=0))
    yz = _z(stats.rankdata(y))
    rho = Xz.T @ yz
    exceed = np.zeros(m)
    done = 0
    absr = np.abs(np.nan_to_num(rho)) - 1e-12
    while done < n_perm:
        c = min(1000, n_perm - done)
        idx = _perm_index(n, strata, c, rng)
        rp = Xz.T @ yz[idx].T
        exceed += (np.abs(np.nan_to_num(rp)) >= absr[:, None]).sum(axis=1)
        done += c
    p = (1 + exceed) / (1 + n_perm)
    p[np.isnan(rho)] = np.nan
    return rho, p


def _boot_rho(x, y, rng, B=N_BOOT):
    n = len(x)
    idx = rng.integers(0, n, (B, n))
    xr, yr = stats.rankdata(x[idx], axis=1), stats.rankdata(y[idx], axis=1)
    return (_z(xr, 1) * _z(yr, 1)).sum(axis=1)


def _sub_sign_stability(x, y, rho, rng, B=N_SUB):
    n = len(x)
    k = max(4, int(round(0.8 * n)))
    idx = np.array([rng.choice(n, k, replace=False) for _ in range(B)])
    xr, yr = stats.rankdata(x[idx], axis=1), stats.rankdata(y[idx], axis=1)
    r = (_z(xr, 1) * _z(yr, 1)).sum(axis=1)
    r = r[np.isfinite(r)]
    return float(np.mean(np.sign(r) == np.sign(rho))) if len(r) and rho != 0 else 0.0


def strength_label(q, p, ci, second_p, stab) -> str:
    """robust = survives multiple-testing correction, a bootstrap CI that excludes 0, a second method and subsampling."""
    ci_ok = ci is not None and np.all(np.isfinite(ci)) and (ci[0] > 0 or ci[1] < 0)
    if q is not None and np.isfinite(q) and q < 0.05 and ci_ok and second_p < 0.05 and stab >= 0.9:
        return "robust"
    has_q = q is not None and np.isfinite(q)
    if ci_ok and ((has_q and q < 0.2) or (not has_q and p is not None and p < 0.05)):
        return "suggestive"
    return "weak"


def assoc(x, y, rng, strata=None, n_perm: int = N_PERM) -> dict | None:
    """Full association record for one pair: Spearman rho, permutation p, bootstrap CI, Kendall p, subsample stability."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    st = None if strata is None else np.asarray(strata)[ok]
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 8 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    rho, p = spearman_scan(x[:, None], y, rng, st, n_perm)
    rho, p = float(rho[0]), float(p[0])
    boot = _boot_rho(x, y, rng)
    boot = boot[np.isfinite(boot)]
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    tau_p = float(stats.kendalltau(x, y).pvalue)
    stab = _sub_sign_stability(x, y, rho, rng)
    return {"n": int(n), "rho": rho, "p": p, "ci": ci, "second_p": tau_p, "stab": stab, "effect": effect_label(rho)}


def _resid(a: np.ndarray, Z: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(Z, a, rcond=None)
    return a - Z @ beta


def partial_assoc(x, y, Zs, rng, n_perm: int = 5000) -> dict | None:
    """Partial Spearman of x and y given the columns of Zs (rank-transformed), Freedman-Lane permutation p,
    case-bootstrap CI (ranks recomputed per resample) and an HC3 rank-regression p-value as the second method."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    Zs = np.column_stack([np.asarray(z, float) for z in Zs])
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(Zs).all(axis=1)
    x, y, Zs = x[ok], y[ok], Zs[ok]
    n = len(x)
    if n < 12 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None

    def ranks(x_, y_, Z_):
        return stats.rankdata(x_), stats.rankdata(y_), np.column_stack([np.ones(len(x_))] + [stats.rankdata(Z_[:, j]) for j in range(Z_.shape[1])])

    xr, yr, Zr = ranks(x, y, Zs)
    ex, ey = _resid(xr, Zr), _resid(yr, Zr)
    rho = float(np.corrcoef(ex, ey)[0, 1])
    exz = ex / np.linalg.norm(ex)
    eyz = ey / np.linalg.norm(ey)
    exceed = 0
    done = 0
    while done < n_perm:
        c = min(1000, n_perm - done)
        idx = rng.permuted(np.tile(np.arange(n), (c, 1)), axis=1)
        rp = (eyz[idx] @ exz)
        exceed += int((np.abs(rp) >= abs(rho) - 1e-12).sum())
        done += c
    p = (1 + exceed) / (1 + n_perm)
    bs = []
    for _ in range(N_BOOT // 2):
        i = rng.integers(0, n, n)
        a, b, Z_ = ranks(x[i], y[i], Zs[i])
        ea, eb = _resid(a, Z_), _resid(b, Z_)
        d = np.linalg.norm(ea) * np.linalg.norm(eb)
        if d > 0:
            bs.append(float(ea @ eb / d))
    ci = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    ols_p = float(sm.OLS(yr, np.column_stack([xr, Zr])).fit(cov_type="HC3").pvalues[1])
    k = int(round(0.8 * n))
    signs = []
    for _ in range(150):
        i = rng.choice(n, k, replace=False)
        a, b, Z_ = ranks(x[i], y[i], Zs[i])
        ea, eb = _resid(a, Z_), _resid(b, Z_)
        d = np.linalg.norm(ea) * np.linalg.norm(eb)
        if d > 0:
            signs.append(np.sign(ea @ eb))
    stab = float(np.mean(np.array(signs) == np.sign(rho))) if signs and rho != 0 else 0.0
    return {"n": int(n), "rho": rho, "p": p, "ci": ci, "second_p": ols_p, "stab": stab, "effect": effect_label(rho)}


def omnibus_gain(X: np.ndarray, y: np.ndarray, Zs, rng, n_perm: int = 5000) -> dict | None:
    """Incremental R2 of all columns of X over Z in a rank regression, with a Freedman-Lane permutation p-value."""
    ok = np.isfinite(X).all(axis=1) & np.isfinite(y) & np.isfinite(np.column_stack(Zs)).all(axis=1)
    X, y = X[ok], y[ok]
    Z = np.column_stack([np.ones(len(y))] + [stats.rankdata(np.asarray(z, float)[ok]) for z in Zs])
    n = len(y)
    if n < 15:
        return None
    Xr = np.column_stack([stats.rankdata(X[:, j]) for j in range(X.shape[1])])
    Xr = Xr[:, np.ptp(Xr, axis=0) > 0]
    if Xr.shape[1] == 0:
        return None
    yr = stats.rankdata(y)
    F = np.column_stack([Z, Xr])
    Hz = Z @ np.linalg.pinv(Z)
    Hf = F @ np.linalg.pinv(F)
    fit = Hz @ yr
    res = yr - fit

    def gain(Y):
        tot = ((Y - Y.mean(axis=0)) ** 2).sum(axis=0)
        return (Y * (Hf @ Y)).sum(axis=0) / tot - (Y * (Hz @ Y)).sum(axis=0) / tot

    obs = float(gain(yr[:, None])[0])
    exceed, done = 0, 0
    while done < n_perm:
        c = min(1000, n_perm - done)
        idx = rng.permuted(np.tile(np.arange(n), (c, 1)), axis=1)
        Ys = fit[:, None] + res[idx].T
        exceed += int((gain(Ys) >= obs - 1e-12).sum())
        done += c
    return {"n": int(n), "delta_r2": obs, "p": (1 + exceed) / (1 + n_perm), "k": int(Xr.shape[1])}


def kw_assoc(x, groups, rng, n_perm: int = N_PERM) -> dict | None:
    """Kruskal-Wallis epsilon-squared of x across categories (groups with <MIN_GROUP members dropped) + permutation p."""
    x = np.asarray(x, float)
    g = pd.Series(groups).astype("object")
    ok = np.isfinite(x) & g.notna().values
    x, g = x[ok], g[ok].astype(str).to_numpy(dtype=object)
    vc = pd.Series(g).value_counts()
    keep = np.isin(g, np.array(vc[vc >= MIN_GROUP].index, dtype=object))
    x, g = x[keep], g[keep]
    levels = sorted(set(g))
    n = len(x)
    if len(levels) < 2 or n < 12 or np.ptp(x) == 0:
        return None
    G = (g[:, None] == np.array(levels, dtype=object)[None, :]).astype(float)
    ng = G.sum(0)
    r = stats.rankdata(x)

    def H(rr):
        s = rr @ G
        return 12.0 / (n * (n + 1)) * (s ** 2 / ng).sum(axis=-1) - 3 * (n + 1)

    h = float(H(r[None, :])[0])
    exceed, done = 0, 0
    while done < n_perm:
        c = min(2000, n_perm - done)
        idx = rng.permuted(np.tile(np.arange(n), (c, 1)), axis=1)
        exceed += int((H(r[idx]) >= h - 1e-9).sum())
        done += c
    return {"n": int(n), "groups": len(levels), "stat": h / (n - 1), "p": (1 + exceed) / (1 + n_perm)}


# --------------------------------------------------------------------------- topic models

def _npmi_coherence(Xbin: np.ndarray, H: np.ndarray, topn: int = 8) -> float:
    N = Xbin.shape[0]
    scores = []
    for h in H:
        top = np.argsort(h)[::-1][:topn]
        sub = Xbin[:, top]
        pi = sub.mean(0)
        co = (sub.T @ sub) / N
        vals = []
        for a in range(len(top)):
            for b in range(a + 1, len(top)):
                if co[a, b] <= 0:
                    vals.append(-1.0)
                else:
                    vals.append(np.log(co[a, b] / (pi[a] * pi[b])) / -np.log(co[a, b]) if co[a, b] < 1 else 1.0)
        scores.append(np.mean(vals))
    return float(np.mean(scores))


def _fit_nmf(X, k, seed):
    return NMF(n_components=k, init="random", random_state=seed, max_iter=600, tol=1e-4).fit(X)


def _best_fit(X, k, n_seeds=5):
    fits = [_fit_nmf(X, k, SEED + s) for s in range(n_seeds)]
    return min(fits, key=lambda m: m.reconstruction_err_)


def _matched_cosine(Ha, Hb) -> float:
    A = Ha / (np.linalg.norm(Ha, axis=1, keepdims=True) + 1e-12)
    B = Hb / (np.linalg.norm(Hb, axis=1, keepdims=True) + 1e-12)
    S = A @ B.T
    r, c = linear_sum_assignment(-S)
    return float(S[r, c].mean())


def dedupe_terms(terms: list[str]) -> list[str]:
    """Drop terms whose words are already covered by a higher-ranked term (e.g. a unigram inside a listed bigram)."""
    kept: list[str] = []
    covered: set[str] = set()
    for t in terms:
        words = set(t.split())
        if words <= covered:
            continue
        kept.append(t)
        covered |= words
    return kept


def discover_topics(texts: list[str], rng: np.random.Generator, min_df: int = MIN_GROUP, max_df: float = 0.8,
                    k_range: tuple[int, int] | None = None) -> dict | None:
    """TF-IDF + NMF. Number of topics = argmax of z(coherence) + z(subsample/seed stability) over candidate k."""
    vec = TfidfVectorizer(analyzer=sentence_analyzer, min_df=min_df, max_df=max_df, sublinear_tf=True)
    try:
        X = vec.fit_transform(texts)
    except ValueError:
        return None
    n, m = X.shape
    if n < MIN_DOCS_FOR_TOPICS or m < 6:
        return None
    vocab = np.array(vec.get_feature_names_out())
    Xbin = (X.toarray() > 0).astype(float)
    lo, hi = k_range or (2, max(2, min(8, n // 10, m // 3)))
    rows = []
    for k in range(lo, hi + 1):
        ref = _best_fit(X, k)
        coh = _npmi_coherence(Xbin, ref.components_)
        sims = []
        for b in range(8):
            idx = rng.choice(n, int(round(0.8 * n)), replace=False)
            sims.append(_matched_cosine(ref.components_, _fit_nmf(X[idx], k, SEED + 100 + b).components_))
        rows.append({"k": k, "coherence": coh, "stability": float(np.mean(sims)), "model": ref})
    zc = np.array([r["coherence"] for r in rows])
    zs = np.array([r["stability"] for r in rows])
    zscore = lambda a: (a - a.mean()) / a.std() if a.std() > 0 else np.zeros_like(a)
    comb = zscore(zc) + zscore(zs)
    best = int(np.argmax(comb))
    model = rows[best]["model"]
    W = model.transform(X)
    zero = W.sum(1) == 0
    share = np.where(zero[:, None], np.nan, W / np.where(zero, 1, W.sum(1))[:, None])
    top_terms = [dedupe_terms([vocab[j] for j in np.argsort(h)[::-1][:20]])[:8] for h in model.components_]
    return {"k": rows[best]["k"], "selection": [{k_: v for k_, v in r.items() if k_ != "model"} | {"score": float(c)}
                                                for r, c in zip(rows, comb)],
            "share": share, "H": model.components_, "vocab": vocab, "top_terms": top_terms,
            "labels": [f"T{i + 1}: " + ", ".join(t[:4]) for i, t in enumerate(top_terms)],
            "dominant": np.where(zero, -1, np.nanargmax(np.nan_to_num(share, nan=-1), axis=1)),
            "n_zero": int(zero.sum()), "stability": rows[best]["stability"], "coherence": rows[best]["coherence"],
            "n_docs": n, "n_terms": m}


# --------------------------------------------------------------------------- resumes

def _norm_city(c: str) -> str:
    return re.split(r",", str(c))[0].strip().lower()


def split_resume(text: str, city_names: set[str]) -> tuple[str, str]:
    """Separate proxy-shaped lines (dates, cities, 'Org Name, Place' lines) from the content lines.

    Employers, schools and cities are proxy-risk text; they are held out of the topic vocabulary and analysed separately.
    """
    clean, ent = [], []
    year = re.compile(r"\b(19|20)\d{2}\b")
    org = re.compile(r"^(?:[A-Z][\w&.'-]*\s+){1,5}[A-Z][\w&.'-]*\s*,")
    for line in str(text).splitlines():
        low = line.lower()
        is_ent = bool(year.search(line)) or bool(org.match(line.strip())) or any(c and c in low for c in city_names)
        (ent if is_ent else clean).append(line)
    return "\n".join(clean), "\n".join(ent)


def parse_grad(s) -> float:
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", str(s))
    if not m:
        m2 = re.search(r"(\d{4})", str(s))
        return float(m2.group(1)) if m2 else np.nan
    months = {k: i for i, k in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
    return int(m.group(2)) + months.get(m.group(1).lower(), 0) / 12.0


def _as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().eq("true")


def build_outcomes(cands: pd.DataFrame, ex: pd.DataFrame) -> pd.DataFrame:
    """One row per candidate with outcome measures. Ranks are within-cohort percentiles; NaN where the stage was not reached."""
    c = cands.copy()
    for col in ("reached_ti", "attended_ac", "has_resume"):
        c[col] = _as_bool(c[col])
    out = pd.DataFrame({"candidate_id": c["candidate_id"].astype(str)})
    out["reached_ti"] = c["reached_ti"].astype(float).values
    out["ti_rank"] = pct_rank(c["screen_score"].where(c["reached_ti"]))
    out["attended_ac"] = np.where(c["reached_ti"], c["attended_ac"].astype(float), np.nan)
    out["ac_rank"] = pct_rank(pd.to_numeric(c["ac_total"], errors="coerce").where(c["attended_ac"]))
    piv = ex.pivot_table(index="candidate_id", columns="exercise", values="total", aggfunc="first")
    piv.index = piv.index.astype(str)
    for e in EXERCISES:
        col = piv[e] if e in piv else pd.Series(dtype=float)
        out[f"rank_{e}"] = out["candidate_id"].map(pd.Series(pct_rank(col.reindex(piv.index)), index=piv.index))
    out["decision"] = c["decision"].map(DECISION_ORDER).astype(float).values
    out["has_resume"] = c["has_resume"].values
    out["grad"] = c["proxy_graduation"].map(parse_grad).values
    out["city"] = c["proxy_home_city"].values
    out["skills"] = c["proxy_skills_tag"].values
    return out


OUTCOMES = [("Reached TI", "reached_ti"), ("TI score rank", "ti_rank"), ("Attended AC (given TI)", "attended_ac"),
            ("AC total rank", "ac_rank"), ("Interview rank", "rank_Interview"), ("Role Play rank", "rank_Role Play"),
            ("Presentation rank", "rank_Presentation"), ("Decision (No Hire<Standby<Hire)", "decision")]


def _f(v, d=3):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), d)


def _assoc_rows(df, share, labels, rng, outcomes=OUTCOMES, prefix_ids=None):
    """Topic-share x outcome associations, BH-corrected across the whole family."""
    recs = []
    for t, lab in enumerate(labels):
        for oname, ocol in outcomes:
            a = assoc(share[:, t], df[ocol].values, rng)
            if a:
                recs.append({"topic": lab, "t": t, "outcome": oname, **a})
    q = bh([r["p"] for r in recs])
    for r, qq in zip(recs, q):
        r["q"] = float(qq)
        r["strength"] = strength_label(qq, r["p"], r["ci"], r["second_p"], r["stab"])
    return recs


def _rec_row(r, extra=()):
    return [*extra, r["n"], _f(r["rho"]), _f(r["ci"][0]), _f(r["ci"][1]), _f(r["p"], 4), _f(r["q"], 4), r["strength"], r["effect"]]


REC_COLS = ["n", "rho", "ci_low", "ci_high", "perm_p", "bh_q", "strength", "effect_size"]


def analyze_resumes(P: dict, rng: np.random.Generator) -> dict:
    cands, resumes, ex = P["candidates"], P["resumes"], P["exercises"]
    out = build_outcomes(cands, ex)
    R = resumes.copy()
    R["candidate_id"] = R["candidate_id"].astype(str)
    R = R[R["text"].notna() & R["text"].astype(str).str.strip().ne("")].drop_duplicates("candidate_id")
    df = out.merge(R, on="candidate_id", how="inner")
    n_cand, n_no = len(out), int((~out["has_resume"]).sum())
    res = {"n_candidates": n_cand, "n_no_resume": n_no, "n_resumes": len(df)}

    cities = {_norm_city(c) for c in out["city"].dropna().unique()}
    parts = [split_resume(t, cities) for t in df["text"]]
    df["clean"] = [p[0] for p in parts]
    df["entity"] = [p[1] for p in parts]

    cov_rows = []
    for name, mask in (("Has resume", out["has_resume"]), ("No resume", ~out["has_resume"])):
        sub = out[mask]
        cov_rows.append({"group": name, "n": int(len(sub)), "reached_ti": float(sub["reached_ti"].mean()) if len(sub) else None,
                         "attended_ac_of_all": float(sub["attended_ac"].fillna(0).mean()) if len(sub) else None,
                         "hired_of_all": float((sub["decision"] == 2).mean()) if len(sub) else None})
    res["coverage"] = cov_rows
    res["coverage_test"] = assoc(out["has_resume"].astype(float).values, out["reached_ti"].values, rng)

    topics = discover_topics(df["clean"].tolist(), rng)
    res["topics"] = topics
    res["df"] = df
    if topics is None:
        return res
    share, labels = topics["share"], topics["labels"]
    ok = np.isfinite(share).all(axis=1)
    res["assoc"] = _assoc_rows(df[ok].reset_index(drop=True), share[ok], labels, rng)
    res["ok"] = ok

    # Proxy check 1: do the (proxy-stripped) topics still carry home city / graduation / skills-tag information?
    prox = []
    dfo = df[ok].reset_index(drop=True)
    sh = share[ok]
    for t, lab in enumerate(labels):
        c = kw_assoc(sh[:, t], dfo["city"].values, rng)
        s = kw_assoc(sh[:, t], dfo["skills"].values, rng)
        g = assoc(sh[:, t], dfo["grad"].values, rng)
        prox.append({"topic": lab, "city": c, "skills": s, "grad": g})
    qs = bh([x[k]["p"] if x[k] else np.nan for x in prox for k in ("city", "skills")] +
            [x["grad"]["p"] if x["grad"] else np.nan for x in prox])
    nk = len(prox)
    for i, x in enumerate(prox):
        x["q_city"], x["q_skills"], x["q_grad"] = qs[2 * i], qs[2 * i + 1], qs[2 * nk + i]
    res["proxy"] = prox

    # Contrast: topics fitted on the FULL text (proxy lines kept) - does the city dominate when proxies are not stripped?
    full = discover_topics(df["text"].tolist(), rng)
    res["full"] = None
    if full is not None:
        fo = np.isfinite(full["share"]).all(axis=1)
        eps = [kw_assoc(full["share"][fo][:, t], df[fo]["city"].values, rng) for t in range(full["k"])]
        res["full"] = {"k": full["k"], "max_city_eps2": max([e["stat"] for e in eps if e] or [np.nan]),
                       "city_p_min": min([e["p"] for e in eps if e] or [np.nan])}

    # Proxy check 2: raw school/employer/city line content, topic-modelled separately, against outcomes.
    ent = discover_topics(df["entity"].tolist(), rng, max_df=0.95)
    res["entity"] = None
    if ent is not None:
        eo = np.isfinite(ent["share"]).all(axis=1)
        erecs = _assoc_rows(df[eo].reset_index(drop=True), ent["share"][eo], ent["labels"], rng)
        res["entity"] = {"topics": ent, "assoc": erecs}
    res["proxy_vs_outcome"] = _proxy_field_outcomes(df, rng)

    # Hypothesis: do interviews favour a resume type, AFTER controlling for Role Play and Presentation ranks?
    res["hyp"] = _hypothesis(df, share, ok, labels, topics["dominant"], rng)
    return res


def _proxy_field_outcomes(df, rng):
    rows = []
    for oname, ocol in OUTCOMES[:7]:
        c = kw_assoc(df[ocol].values, df["city"].values, rng)
        g = assoc(df["grad"].values, df[ocol].values, rng)
        rows.append({"outcome": oname, "city": c, "grad": g})
    qs = bh([r["city"]["p"] if r["city"] else np.nan for r in rows] + [r["grad"]["p"] if r["grad"] else np.nan for r in rows])
    for i, r in enumerate(rows):
        r["q_city"], r["q_grad"] = qs[i], qs[len(rows) + i]
    return rows


def _hypothesis(df, share, ok, labels, dominant, rng):
    d = df[ok].reset_index(drop=True)
    sh = share[ok]
    dom = dominant[ok]
    att = d[["rank_Interview", "rank_Role Play", "rank_Presentation"]].notna().all(axis=1).values
    targets = {"Interview": ("Role Play", "Presentation"), "Role Play": ("Interview", "Presentation"),
               "Presentation": ("Interview", "Role Play")}
    recs = []
    for tgt, ctrl in targets.items():
        for t, lab in enumerate(labels):
            a = partial_assoc(sh[att, t], d.loc[att, f"rank_{tgt}"].values, [d.loc[att, f"rank_{c}"].values for c in ctrl], rng)
            if a:
                recs.append({"target": tgt, "topic": lab, "t": t, **a})
    q = bh([r["p"] for r in recs])
    for r, qq in zip(recs, q):
        r["q"] = float(qq)
        r["strength"] = strength_label(qq, r["p"], r["ci"], r["second_p"], r["stab"])
    omni = {}
    for tgt, ctrl in targets.items():
        omni[tgt] = omnibus_gain(sh[att][:, :-1] if sh.shape[1] > 1 else sh[att], d.loc[att, f"rank_{tgt}"].values,
                                 [d.loc[att, f"rank_{c}"].values for c in ctrl], rng)
    # sensitivity: also control for graduation date rank (proxy field)
    sens = []
    for r in [r for r in recs if r["target"] == "Interview"]:
        a = partial_assoc(sh[att, r["t"]], d.loc[att, "rank_Interview"].values,
                          [d.loc[att, "rank_Role Play"].values, d.loc[att, "rank_Presentation"].values, d.loc[att, "grad"].values], rng, n_perm=2000)
        if a:
            sens.append({"topic": r["topic"], **a})
    # raw (uncontrolled) interview-rank association for contrast
    raw = [assoc(sh[att, t], d.loc[att, "rank_Interview"].values, rng, n_perm=2000) for t in range(len(labels))]
    boxes = []
    for t, lab in enumerate(labels):
        m = att & (dom == t)
        boxes.append({"topic": lab, "values": d.loc[m, "rank_Interview"].values, "n": int(m.sum())})
    return {"recs": recs, "omnibus": omni, "sens": sens, "raw": raw, "boxes": boxes, "n_att": int(att.sum()),
            "d": d, "sh": sh, "att": att, "dom": dom}


# --------------------------------------------------------------------------- notes

def note_ranks(notes: pd.DataFrame, cands: pd.DataFrame, ex: pd.DataFrame) -> pd.DataFrame:
    """Attach the within-cohort percentile rank of the instrument each note describes."""
    out = build_outcomes(cands, ex).set_index("candidate_id")
    n = notes.copy()
    n["candidate_id"] = n["candidate_id"].astype(str)
    n = n[n["text"].notna() & n["text"].astype(str).str.strip().ne("") & n["text"].astype(str).str.upper().ne("N/A")]
    col = {"Technical interview": "ti_rank", "Interview": "rank_Interview", "Role Play": "rank_Role Play",
           "Presentation": "rank_Presentation", "Overall": "ac_rank"}
    n["rank"] = [out[col[s]].get(c, np.nan) if s in col else np.nan for s, c in zip(n["source"], n["candidate_id"])]
    n["words"] = n["text"].astype(str).str.split().str.len()
    return n.reset_index(drop=True)


def term_scan(texts, y, rng, strata=None, min_df=MIN_GROUP, top=10):
    vec = CountVectorizer(analyzer=sentence_analyzer, min_df=min_df,
                          max_df=0.95, binary=True)
    try:
        X = vec.fit_transform(texts).toarray().astype(float)
    except ValueError:
        return None
    if X.shape[1] == 0:
        return None
    y = np.asarray(y, float)
    rho, p = spearman_scan(X, y, rng, strata)
    q = bh(p)
    terms = np.array(vec.get_feature_names_out())
    df_ = X.sum(0)
    order = np.argsort(rho)
    sel = list(order[::-1][:top]) + list(order[:top])
    rows = []
    for j in dict.fromkeys(sel):
        if not np.isfinite(rho[j]):
            continue
        a = assoc(X[:, j], y, rng, strata, n_perm=2000)
        if not a:
            continue
        a["p"] = float(p[j])
        rows.append({"term": terms[j], "n_notes": int(df_[j]), "direction": "higher rank" if rho[j] > 0 else "lower rank",
                     "rho": float(rho[j]), "ci": a["ci"], "p": float(p[j]), "q": float(q[j]), "n": a["n"],
                     "strength": strength_label(q[j], p[j], a["ci"], a["second_p"], a["stab"]), "effect": effect_label(rho[j])})
    return {"rows": rows, "n_terms": int(len(terms)), "min_q": float(np.nanmin(q)) if np.isfinite(q).any() else None}


def text_rank_model(texts, y, cand_ids, rng):
    """Cross-validated ridge on TF-IDF predicting the within-cohort rank from the note text only."""
    y = np.asarray(y, float)
    vec = TfidfVectorizer(analyzer=sentence_analyzer, min_df=MIN_GROUP,
                          max_df=0.95, sublinear_tf=True)
    try:
        X = vec.fit_transform(texts)
    except ValueError:
        return None
    n = len(y)
    if n < MIN_DOCS_FOR_TOPICS or X.shape[1] < 3:
        return None
    alphas = np.logspace(-1, 3, 9)
    cv = RepeatedKFold(n_splits=5, n_repeats=3, random_state=SEED)
    pred = np.zeros(n)
    cnt = np.zeros(n)
    used = []
    for tr, te in cv.split(X):
        m = RidgeCV(alphas=alphas).fit(X[tr], y[tr])
        used.append(m.alpha_)
        pred[te] += m.predict(X[te])
        cnt[te] += 1
    pred /= np.maximum(cnt, 1)
    rho = float(stats.spearmanr(pred, y).statistic)
    alpha = float(np.median(used))
    prng = np.random.default_rng(SEED + 7)
    cv1 = RepeatedKFold(n_splits=5, n_repeats=1, random_state=SEED)
    splits = list(cv1.split(X))

    def cv_rho(yy):
        pr = np.zeros(n)
        for tr, te in splits:
            pr[te] = Ridge(alpha=alpha).fit(X[tr], yy[tr]).predict(X[te])
        return stats.spearmanr(pr, yy).statistic

    perm = np.array([cv_rho(prng.permutation(y)) for _ in range(300)])
    p = float((1 + (perm >= rho).sum()) / (1 + len(perm)))
    idx = rng.integers(0, n, (N_BOOT, n))
    bs = np.array([stats.spearmanr(pred[i], y[i]).statistic for i in idx])
    ci = (float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5)))
    tau_p = float(stats.kendalltau(pred, y).pvalue)
    stab = float(np.mean(bs > 0)) if rho > 0 else float(np.mean(bs < 0))
    pr_rank = pct_rank(pred)
    gap = y - pr_rank
    return {"n": n, "rho": rho, "ci": ci, "p": p, "second_p": tau_p, "stab": stab, "alpha": alpha, "pred_rank": pr_rank, "gap": gap,
            "strength": strength_label(p, p, ci, tau_p, stab), "effect": effect_label(rho), "cand": list(cand_ids)}


def style_index(notes: pd.DataFrame, rng: np.random.Generator) -> dict | None:
    """Data-derived language style per note, cross-fitted by candidate.

    For every term, the signed rank association with the note's score rank is estimated on training folds only.
    q_t (BH-adjusted p, in [0,1]) is the term's *score-independence*: terms that co-vary with score rank get q near 0 and are
    rubric/evidence-style; terms that do not co-vary get q near 1 and are impression-style (or boilerplate). For a note with
    distinct terms t: independent intensity S = mean(idf_t * q_t) and rubric tone T = mean(idf_t * (1-q_t) * sign(rho_t)).
    idf weighting means rare, non-score-bearing wording counts more than ubiquitous boilerplate; averaging per term keeps the
    index from simply growing with note length.
    """
    d = notes[notes["rank"].notna()].reset_index(drop=True)
    if len(d) < 40:
        return None
    vec = CountVectorizer(analyzer=sentence_analyzer, min_df=MIN_GROUP,
                          max_df=0.95, binary=True)
    X = vec.fit_transform(d["text"].astype(str)).toarray().astype(float)
    terms = np.array(vec.get_feature_names_out())
    N = len(d)
    dfc = X.sum(0)
    idf = np.log(N / dfc)
    y = d["rank"].values
    ids = d["candidate_id"].unique()
    fold_of = dict(zip(rng.permutation(ids), np.arange(len(ids)) % 5))
    fold = d["candidate_id"].map(fold_of).values

    def weights(mask):
        Xt, yt = X[mask], y[mask]
        n = len(yt)
        Xz = _z(stats.rankdata(Xt, axis=0))
        yz = _z(stats.rankdata(yt))
        rho = np.nan_to_num(Xz.T @ yz)
        t = rho * np.sqrt((n - 2) / np.maximum(1e-12, 1 - rho ** 2))
        p = 2 * stats.t.sf(np.abs(t), n - 2)
        p[~np.isfinite(rho) | (Xt.std(0) == 0)] = 1.0
        return rho, bh(p)

    S = np.full(N, np.nan)
    T = np.full(N, np.nan)
    for f in range(5):
        te = fold == f
        rho, q = weights(~te)
        q = np.nan_to_num(q, nan=1.0)
        Xte = X[te]
        tot = Xte.sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            S[te] = (Xte @ (idf * q)) / tot
            T[te] = (Xte @ (idf * (1 - q) * np.sign(rho))) / tot
    rho_all, q_all = weights(np.ones(N, bool))
    q_all = np.nan_to_num(q_all, nan=1.0)
    d["subj_rate"], d["rubric_tone"] = S, T
    term_tab = pd.DataFrame({"term": terms, "n_notes": dfc.astype(int), "rho": rho_all, "q": q_all, "idf": idf})
    term_tab["indep_weight"] = term_tab["idf"] * term_tab["q"]
    term_tab["track_weight"] = term_tab["idf"] * (1 - term_tab["q"])
    return {"notes": d, "terms": term_tab}


def analyze_notes(P: dict, rng: np.random.Generator, resume_res: dict | None) -> dict:
    notes = note_ranks(P["notes"], P["candidates"], P["exercises"])
    res = {"notes": notes}
    res["length"] = {s: notes.loc[notes["source"] == s, "words"].values for s in SOURCES if (notes["source"] == s).any()}
    res["reviewers"] = notes.groupby(["source", "reviewer"], dropna=False).size().reset_index(name="n")

    res["len_rank"] = {}
    for s in SOURCES:
        sub = notes[(notes["source"] == s) & notes["rank"].notna()]
        res["len_rank"][s] = assoc(sub["words"].values, sub["rank"].values, rng) if len(sub) else None

    topics, terms, models = {}, {}, {}
    scopes = [(s, notes[(notes["source"] == s)]) for s in SOURCES] + [("All sources", notes)]
    for name, sub in scopes:
        sub = sub.reset_index(drop=True)
        if len(sub) < MIN_DOCS_FOR_TOPICS:
            continue
        strata = None if name != "All sources" else sub["source"].astype("category").cat.codes.values
        tp = discover_topics(sub["text"].astype(str).tolist(), rng, max_df=0.95)
        if tp is not None:
            ok = np.isfinite(tp["share"]).all(axis=1) & sub["rank"].notna().values
            recs = []
            for t, lab in enumerate(tp["labels"]):
                a = assoc(tp["share"][ok][:, t], sub.loc[ok, "rank"].values, rng, None if strata is None else strata[ok])
                if a:
                    recs.append({"topic": lab, "t": t, **a})
            q = bh([r["p"] for r in recs])
            for r, qq in zip(recs, q):
                r["q"] = float(qq)
                r["strength"] = strength_label(qq, r["p"], r["ci"], r["second_p"], r["stab"])
            tp["assoc"] = recs
            tp["n_dom"] = [int((tp["dominant"] == t).sum()) for t in range(tp["k"])]
            topics[name] = tp
        rk = sub[sub["rank"].notna()].reset_index(drop=True)
        if len(rk) >= MIN_DOCS_FOR_TOPICS:
            st = None if name != "All sources" else rk["source"].astype("category").cat.codes.values
            terms[name] = term_scan(rk["text"].astype(str).tolist(), rk["rank"].values, rng, st)
            if name != "All sources":
                models[name] = text_rank_model(rk["text"].astype(str).tolist(), rk["rank"].values, rk["candidate_id"].tolist(), rng)
    res["topics"], res["terms"], res["models"] = topics, terms, models

    si = style_index(notes, rng)
    res["style"] = si
    if si is not None:
        res.update(_style_analysis(si, resume_res, rng))
    return res


def _style_analysis(si, resume_res, rng):
    d = si["notes"]
    per_source = []
    for s in SOURCES:
        sub = d[d["source"] == s]
        sub = sub[sub["subj_rate"].notna() & sub["rubric_tone"].notna()]
        if len(sub) < 12:
            continue
        a_s = assoc(sub["subj_rate"].values, sub["rank"].values, rng, n_perm=3000)
        a_t = assoc(sub["rubric_tone"].values, sub["rank"].values, rng, n_perm=3000)
        n = len(sub)
        idx = rng.integers(0, n, (N_BOOT, n))
        sv, tv, rv = sub["subj_rate"].values, sub["rubric_tone"].values, sub["rank"].values
        diff = []
        for i in idx:
            rs = stats.spearmanr(sv[i], rv[i]).statistic
            rt = stats.spearmanr(tv[i], rv[i]).statistic
            diff.append(abs(rt) - abs(rs))
        diff = np.array(diff)
        ci = (float(np.nanpercentile(diff, 2.5)), float(np.nanpercentile(diff, 97.5)))
        obs = abs(a_t["rho"]) - abs(a_s["rho"]) if a_s and a_t else np.nan
        per_source.append({"source": s, "n": n, "mean_subj": float(sub["subj_rate"].mean()), "rho_subj": a_s, "rho_tone": a_t,
                           "diff": float(obs), "diff_ci": ci,
                           "strength": "suggestive" if ci[0] > 0 else "weak"})
    out = {"style_source": per_source}

    # language style by resume theme, conditioned on score rank
    out["style_theme"] = None
    if resume_res and resume_res.get("topics") is not None:
        rd, tp = resume_res["df"], resume_res["topics"]
        sh = pd.DataFrame(tp["share"], columns=range(tp["k"]))
        sh["candidate_id"] = rd["candidate_id"].values
        sh["dom"] = tp["dominant"]
        m = d.merge(sh, on="candidate_id", how="inner")
        m = m[m[0].notna()]
        recs, cells = [], []
        for s in list(SOURCES) + ["AC exercises pooled"]:
            if s == "AC exercises pooled":
                sub = m[m["source"].isin(EXERCISES)].groupby("candidate_id").agg(
                    subj_rate=("subj_rate", "mean"), rank=("rank", "mean"), dom=("dom", "first"),
                    **{str(t): (t, "first") for t in range(tp["k"])}).reset_index()
                sub.columns = [int(c) if str(c).isdigit() else c for c in sub.columns]
            else:
                sub = m[m["source"] == s]
            if len(sub) < 15:
                continue
            for t in range(tp["k"]):
                a = partial_assoc(sub[t].values, sub["subj_rate"].values, [sub["rank"].values], rng, n_perm=3000)
                if a:
                    recs.append({"source": s, "topic": tp["labels"][t], "t": t, **a})
            for t in range(tp["k"]):
                g = sub[sub["dom"] == t]["subj_rate"].dropna().values
                cells.append({"source": s, "topic": tp["labels"][t], "n": len(g),
                              "mean": float(g.mean()) if len(g) else None,
                              "ci": (float(np.percentile([rng.choice(g, len(g)).mean() for _ in range(500)], 2.5)),
                                     float(np.percentile([rng.choice(g, len(g)).mean() for _ in range(500)], 97.5))) if len(g) >= 2 else (None, None)})
        q = bh([r["p"] for r in recs])
        for r, qq in zip(recs, q):
            r["q"] = float(qq)
            r["strength"] = strength_label(qq, r["p"], r["ci"], r["second_p"], r["stab"])
        out["style_theme"] = {"recs": recs, "cells": cells, "merged": m}
    return out


# --------------------------------------------------------------------------- rendering

def _chart(id_, type_, title, data, x="", y="", subtitle=None):
    c = {"id": id_, "type": type_, "title": title, "x_label": x, "y_label": y, "data": data}
    if subtitle:
        c["subtitle"] = subtitle
    return c


def _table(id_, title, columns, rows, subtitle=None):
    return _chart(id_, "table", title, {"columns": columns, "rows": rows}, subtitle=subtitle)


def _supp(n) -> bool:
    return n is not None and n < MIN_GROUP


def _box(name, vals):
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    n = len(v)
    if n == 0:
        return {"name": name, "n": 0, "min": None, "q1": None, "median": None, "q3": None, "max": None, "suppressed": True}
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"name": name, "n": n, "min": _f(v.min()), "q1": _f(q1), "median": _f(med), "q3": _f(q3), "max": _f(v.max()),
            "suppressed": n < MIN_GROUP}


def _shareable_box(g):
    if g["suppressed"]:
        return {"name": g["name"], "n": None, "min": None, "q1": None, "median": None, "q3": None, "max": None, "suppressed": True}
    return g


def _find(text, strength, evidence):
    return {"text": text, "strength": strength, "evidence": evidence}


def _ev(r):
    return f"n={r['n']}, rho={r['rho']:+.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}], perm p={r['p']:.4f}" + (
        f", BH q={r['q']:.3f}" if "q" in r and np.isfinite(r["q"]) else "")


def render_resume(R: dict, shareable: bool) -> dict:
    caveats = [
        "Outcomes (reached TI, attended the assessment center, ranks, decision) are past human decisions; this describes what the process rewarded, not who would perform well.",
        "Later-stage ranks exist only for candidates who passed earlier gates, so those comparisons are range-restricted. Nothing is imputed.",
        "Topics come from short resumes with an unsupervised model; they are descriptive, and the number of topics was chosen from coherence and stability, not a fixed value.",
        "Employers, schools, cities and dates are held out of the topic vocabulary by line shape (dates, 'Org, Place' lines, known home cities). Resumes with different layouts may leak a few such tokens.",
        "Rank strength labels: robust needs BH q<0.05, a bootstrap CI excluding 0, a second method (Kendall or HC3 rank regression) at p<0.05 and sign stability >=90% under 80% subsampling.",
        "Effect-size words (negligible/small/moderate/large) are descriptive bands on |rho| (0.1/0.3/0.5), not decision cutoffs.",
        "Interview ranks include any assessor leniency; reviewer effects are analysed in the interviewers module and are not removed here.",
    ]
    doc = {"section": "resume_themes", "title": "Resume themes and what the process rewarded", "caveats": caveats,
           "findings": [], "charts": [], "meta": {"seed": SEED, "n_candidates": R["n_candidates"], "n_no_resume": None if (shareable and 0 < R["n_no_resume"] < MIN_GROUP) else R["n_no_resume"],
                                                  "n_resumes": R["n_resumes"]}}
    F, C = doc["findings"], doc["charts"]
    small = shareable and 0 < R["n_no_resume"] < MIN_GROUP
    no_txt = "fewer than 5" if small else str(R["n_no_resume"])
    F.append(_find(f"{no_txt} of {R['n_candidates']} candidates have no resume and are excluded from all resume-topic analyses; they are reported separately below.",
                   "robust", f"n={R['n_candidates']}, no resume={'<5' if small else R['n_no_resume']}, resumes analysed={R['n_resumes']}"))
    cov = R["coverage"]
    C.append(_table("resume-coverage", "Candidates with and without a resume",
                    ["group", "n", "share reached TI", "share attended AC (of group)", "share hired (of group)", "suppressed"],
                    [[c["group"], None if shareable and _supp(c["n"]) else c["n"],
                      None if shareable and _supp(c["n"]) else _f(c["reached_ti"]),
                      None if shareable and _supp(c["n"]) else _f(c["attended_ac_of_all"]),
                      None if shareable and _supp(c["n"]) else _f(c["hired_of_all"]), _supp(c["n"])] for c in cov]))
    ct = R.get("coverage_test")
    if ct and min(c["n"] for c in cov) >= MIN_GROUP:
        F.append(_find("Whether a candidate has a resume on file is associated with reaching TI only to the degree shown; missing resumes are not imputed.",
                       strength_label(ct["p"], ct["p"], ct["ci"], ct["second_p"], ct["stab"]),
                       f"n={ct['n']}, rho={ct['rho']:+.2f} [{ct['ci'][0]:+.2f}, {ct['ci'][1]:+.2f}], perm p={ct['p']:.4f}"))

    tp = R["topics"]
    if tp is None:
        F.append(_find("Too few resumes for a topic model.", "weak", f"n={R['n_resumes']}"))
        doc["meta"]["n_topics"] = 0
        return doc
    doc["meta"].update({"n_topics": tp["k"], "stability": _f(tp["stability"]), "coherence": _f(tp["coherence"])})
    F.append(_find(f"Bottom-up resume themes: {tp['k']} topics chosen from the data (coherence {tp['coherence']:.2f}, matched-topic stability {tp['stability']:.2f} across seeds/80% subsamples). Topics: " + "; ".join(tp["labels"]) + ".",
                   "robust" if tp["stability"] >= 0.9 else "suggestive" if tp["stability"] >= 0.75 else "weak",
                   f"n={tp['n_docs']} resumes, {tp['n_terms']} terms, k searched {tp['selection'][0]['k']}-{tp['selection'][-1]['k']}"))
    C.append(_chart("resume-k-selection", "bar", "Topic count selection", {
        "labels": [f"k={s['k']}" for s in tp["selection"]],
        "series": [{"name": "coherence (NPMI)", "values": [_f(s["coherence"]) for s in tp["selection"]]},
                   {"name": "stability (matched cosine)", "values": [_f(s["stability"]) for s in tp["selection"]]}]},
        x="candidate number of topics", y="score", subtitle="Chosen k maximises z(coherence) + z(stability)."))
    mean_share = np.nanmean(tp["share"], axis=0)
    trows = []
    for t, lab in enumerate(tp["labels"]):
        nd = int((tp["dominant"] == t).sum())
        s_ = shareable and _supp(nd)
        trows.append([lab, ", ".join(tp["top_terms"][t][:8]), None if s_ else nd, None if s_ else _f(mean_share[t]), s_])
    C.append(_table("resume-topics", "Resume themes (derived clusters = dominant topic)", ["topic", "top terms", "n (dominant)", "mean share", "suppressed"], trows))

    recs = R["assoc"]
    labs, onames = tp["labels"], [o for o, _ in OUTCOMES]
    mat = [[None for _ in onames] for _ in labs]
    for r in recs:
        mat[r["t"]][onames.index(r["outcome"])] = _f(r["rho"])
    C.append(_chart("resume-topic-outcome-heatmap", "heatmap", "Resume topic share vs outcome (Spearman rho)",
                    {"row_labels": labs, "col_labels": onames, "values": mat, "min": -1, "max": 1}))
    C.append(_table("resume-topic-outcome", "Topic share vs outcome with CIs and multiple-testing correction",
                    ["topic", "outcome", *REC_COLS], [_rec_row(r, (r["topic"], r["outcome"])) for r in recs],
                    subtitle="BH correction over every topic x outcome test; CI = 95% bootstrap."))
    ranked = sorted(recs, key=lambda r: -abs(r["rho"]))
    sig = [r for r in recs if r["strength"] != "weak"]
    if sig:
        for r in sorted(sig, key=lambda r: -abs(r["rho"]))[:4]:
            F.append(_find(f"Resume theme '{r['topic']}' share tracks {r['outcome']} ({r['effect']} effect, {'positive' if r['rho'] > 0 else 'negative'}): what the process rewarded.",
                           r["strength"], _ev(r)))
    elif ranked:
        r = ranked[0]
        F.append(_find(f"No resume theme is clearly associated with any process outcome; the largest is '{r['topic']}' vs {r['outcome']}.", "weak", _ev(r)))

    # hypothesis
    H = R["hyp"]
    hr = [r for r in H["recs"] if r["target"] == "Interview"]
    C.append(_table("resume-hypothesis", "Do interviews favour a resume type? Partial rank correlation controlling for the other two exercises",
                    ["target exercise", "topic", *REC_COLS], [_rec_row(r, (r["target"], r["topic"])) for r in H["recs"]],
                    subtitle=f"Assessment-center attendees with a resume and all three ranks (n={H['n_att']}); Interview is controlled for Role Play + Presentation ranks, and the other rows are contrasts."))
    om = H["omnibus"].get("Interview")
    if hr:
        best = max(hr, key=lambda r: abs(r["rho"]))
        txt = (f"Hypothesis 'interviews favour a certain resume type': after controlling for Role Play and Presentation ranks, the resume theme "
               f"'{best['topic']}' shows a {best['effect']} partial association with the Interview percentile rank "
               f"({'positive' if best['rho'] > 0 else 'negative'}) - what this process rewarded in interviews, range-restricted to AC attendees.")
        F.append(_find(txt, best["strength"], _ev(best)))
    if om:
        omstrength = "suggestive" if om["p"] < 0.05 else "weak"
        F.append(_find(f"All resume themes together add {om['delta_r2']:.3f} to R-squared of Interview rank beyond Role Play + Presentation ranks "
                       f"({'a detectable' if om['p'] < 0.05 else 'no detectable'} gain).", omstrength,
                       f"n={om['n']}, delta R2={om['delta_r2']:.3f}, Freedman-Lane perm p={om['p']:.4f}, {om['k']} topic columns"))
    contrast = {t: max([r for r in H["recs"] if r["target"] == t], key=lambda r: abs(r["rho"]), default=None) for t in ("Role Play", "Presentation")}
    C.append(_table("resume-hypothesis-contrast", "Largest partial association per exercise (is the Interview special?)",
                    ["exercise", "topic", *REC_COLS], [_rec_row(r, (t, r["topic"])) for t, r in
                                                       [("Interview", max(hr, key=lambda r: abs(r["rho"])) if hr else None), *contrast.items()] if r]))
    if H["sens"]:
        C.append(_table("resume-hypothesis-sensitivity", "Interview partial association also controlling for graduation date rank (proxy field)",
                        ["topic", "n", "rho", "ci_low", "ci_high", "perm_p", "effect_size"],
                        [[s["topic"], s["n"], _f(s["rho"]), _f(s["ci"][0]), _f(s["ci"][1]), _f(s["p"], 4), s["effect"]] for s in H["sens"]]))
    groups = []
    for b in H["boxes"]:
        g = _box(b["topic"], b["values"])
        groups.append(_shareable_box(g) if shareable else g)
    C.append(_chart("resume-interview-rank-by-theme", "boxplot", "Interview percentile rank by dominant resume theme (uncontrolled)",
                    {"groups": groups}, y="Interview percentile rank among AC attendees"))
    if hr:
        best = max(hr, key=lambda r: abs(r["rho"]))
        t = best["t"]
        d, sh, att = H["d"], H["sh"], H["att"]
        Z = np.column_stack([np.ones(att.sum()), stats.rankdata(d.loc[att, "rank_Role Play"]), stats.rankdata(d.loc[att, "rank_Presentation"])])
        ex_ = _resid(stats.rankdata(sh[att, t]), Z)
        ey_ = _resid(stats.rankdata(d.loc[att, "rank_Interview"]), Z)
        ids = d.loc[att, "candidate_id"].tolist()
        pts = [{"x": _f(a), "y": _f(b), "label": None if shareable else i, "group": tp["labels"][int(g)] if g >= 0 else None}
               for a, b, i, g in zip(ex_, ey_, ids, H["dom"][att])]
        C.append(_chart("resume-hypothesis-scatter", "scatter", f"Residual Interview rank vs residual share of {best['topic']}",
                        {"points": pts}, x="topic share rank (net of Role Play, Presentation)", y="Interview rank (net of Role Play, Presentation)"))

    # proxy check
    px = R["proxy"]
    prow = []
    for x in px:
        c, s, g = x["city"], x["skills"], x["grad"]
        prow.append([x["topic"], _f(c["stat"]) if c else None, _f(c["p"], 4) if c else None, _f(x["q_city"], 4) if c else None,
                     _f(s["stat"]) if s else None, _f(s["p"], 4) if s else None, _f(x["q_skills"], 4) if s else None,
                     _f(g["rho"]) if g else None, _f(g["p"], 4) if g else None, _f(x["q_grad"], 4) if g else None])
    C.append(_table("resume-proxy-check", "Bias check: do the (proxy-stripped) themes still track home city, skills tag or graduation date?",
                    ["topic", "city eps2", "city p", "city q", "skills-tag eps2", "skills p", "skills q", "graduation rho", "graduation p", "graduation q"], prow,
                    subtitle="eps2 = Kruskal-Wallis epsilon-squared (groups under 5 dropped); permutation p; BH q across all topic x proxy tests."))
    hit = [(x["topic"], k, x[f"q_{k}"], x[k]) for x in px for k in ("city", "skills", "grad") if x[k] and np.isfinite(x[f"q_{k}"]) and x[f"q_{k}"] < 0.1]
    if hit:
        t_, k_, q_, a_ = min(hit, key=lambda h: h[2])
        nm = {"city": "home city", "skills": "skills tag", "grad": "graduation date"}[k_]
        F.append(_find(f"Even with employer/school/city lines held out, theme '{t_}' still varies with {nm}: treat resume themes as potential proxy carriers.",
                       "suggestive", f"n={a_['n']}, {'eps2=%.3f' % a_['stat'] if 'stat' in a_ else 'rho=%+.2f' % a_['rho']}, perm p={a_['p']:.4f}, BH q={q_:.3f}"))
    else:
        F.append(_find("With employer/school/city lines held out, no resume theme is clearly tied to home city, skills tag or graduation date.", "weak",
                       f"n={len(R['df'])}, {len(px) * 3} topic x proxy tests, smallest BH q={np.nanmin([x[f'q_{k}'] for x in px for k in ('city', 'skills', 'grad')]):.3f}"))
    if R.get("full"):
        fu = R["full"]
        F.append(_find(f"For contrast, topics fitted on the full resume text (proxy lines kept) reach city epsilon-squared up to {fu['max_city_eps2']:.2f}, "
                       f"versus {np.nanmax([x['city']['stat'] for x in px if x['city']] or [np.nan]):.2f} after holding proxy lines out; this shows how much a topic model would otherwise lean on location.",
                       "suggestive" if fu["city_p_min"] < 0.05 else "weak", f"n={len(R['df'])}, k={fu['k']}, smallest perm p={fu['city_p_min']:.4f}"))
    ent = R.get("entity")
    if ent:
        et = ent["topics"]
        C.append(_table("resume-proxy-topics", "Topics built only from school/employer/city/date lines", ["topic", "top terms", "n (dominant)", "suppressed"],
                        [[lab if not shareable else f"P{i + 1}", "(withheld in shareable copy)" if shareable else ", ".join(et["top_terms"][i][:8]),
                          None if shareable and _supp(int((et["dominant"] == i).sum())) else int((et["dominant"] == i).sum()),
                          _supp(int((et["dominant"] == i).sum()))] for i, lab in enumerate(et["labels"])]))
        er = ent["assoc"]
        C.append(_table("resume-proxy-outcome", "Bias check: do proxy-line topics track outcomes?", ["topic", "outcome", *REC_COLS],
                        [_rec_row(r, (r["topic"] if not shareable else f"P{r['t'] + 1}", r["outcome"])) for r in er]))
        es = [r for r in er if r["strength"] != "weak"]
        if es:
            r = max(es, key=lambda r: abs(r["rho"]))
            F.append(_find(f"Proxy-line content (schools, employers, cities) is associated with {r['outcome']} ({r['effect']}); the process may be rewarding background rather than demonstrated skill. Review before using resumes in screening.",
                           r["strength"], _ev(r)))
        elif er:
            r = max(er, key=lambda r: abs(r["rho"]))
            F.append(_find("Proxy-line content (schools, employers, cities) shows no clear association with process outcomes.", "weak", _ev(r)))
    pv = R.get("proxy_vs_outcome")
    if pv:
        C.append(_table("resume-proxy-field-outcome", "Proxy fields vs outcomes directly",
                        ["outcome", "city eps2", "city p", "city q", "graduation rho", "graduation p", "graduation q"],
                        [[r["outcome"], _f(r["city"]["stat"]) if r["city"] else None, _f(r["city"]["p"], 4) if r["city"] else None,
                          _f(r["q_city"], 4) if r["city"] else None, _f(r["grad"]["rho"]) if r["grad"] else None,
                          _f(r["grad"]["p"], 4) if r["grad"] else None, _f(r["q_grad"], 4) if r["grad"] else None] for r in pv]))
    return doc


def _fmt_terms(ts):
    return ", ".join(ts)


def render_notes(N: dict, shareable: bool) -> dict:
    caveats = [
        "Notes describe past human judgements; they are compared with the scores those same reviewers gave, so agreement shows consistency, not validity.",
        "Overall notes contain the decision wording, so their text-to-rank link is partly built in.",
        "The style index is data-derived: terms that do not co-vary with score rank are 'score-independent' (impression-style wording and process boilerplate such as logistics remarks are not separable without a lexicon). It is cross-fitted by candidate; the rubric-versus-independent comparison is partly true by construction and the resume-theme comparison is the substantive check.",
        "Terms appearing in fewer than 5 notes are never analysed or shown. Groups under 5 are suppressed in the shareable copy; candidate ids appear only in the local copy.",
        "Rank = within-cohort percentile of the score each note describes (TI score for technical-interview notes, exercise total for exercise notes, assessment-center total for Overall); no fixed score cutoffs are used.",
        "Reviewer-level behaviour is analysed in the interviewers module; only note counts per reviewer are shown here.",
    ]
    doc = {"section": "notes_themes", "title": "Themes in reviewer notes and how they relate to scores", "caveats": caveats, "findings": [],
           "charts": [], "meta": {"seed": SEED, "n_notes": int(len(N["notes"]))}}
    F, C = doc["findings"], doc["charts"]
    notes = N["notes"]
    F.append(_find(f"{len(notes)} notes across {notes['source'].nunique()} sources were analysed (counts per source in the length chart).", "robust",
                   "n=%d notes, sources=%s" % (len(notes), ", ".join(f"{s}:{(notes['source'] == s).sum()}" for s in SOURCES if (notes['source'] == s).any()))))

    groups = [(_shareable_box(g) if shareable else g) for g in (_box(s, v) for s, v in N["length"].items())]
    C.append(_chart("notes-length", "boxplot", "Note length (words) by source", {"groups": groups}, y="words"))
    lr = [(s, a) for s, a in N["len_rank"].items() if a]
    C.append(_table("notes-length-rank", "Note length vs score rank (Spearman)", ["source", *REC_COLS[:5], "effect_size"],
                    [[s, a["n"], _f(a["rho"]), _f(a["ci"][0]), _f(a["ci"][1]), _f(a["p"], 4), a["effect"]] for s, a in lr]))
    rv = N["reviewers"]
    rows = []
    for _, r in rv.iterrows():
        sp = shareable and _supp(int(r["n"]))
        rows.append([r["source"], "unrecorded" if pd.isna(r["reviewer"]) else str(r["reviewer"]), None if sp else int(r["n"]), sp])
    C.append(_table("notes-reviewer-counts", "Notes per reviewer (counts only)", ["source", "reviewer", "n notes", "suppressed"], rows))

    # topics
    trows, tmeta = [], {}
    for name, tp in N["topics"].items():
        tmeta[name] = {"k": tp["k"], "stability": _f(tp["stability"])}
        by_t = {r["t"]: r for r in tp["assoc"]}
        for t, lab in enumerate(tp["labels"]):
            r = by_t.get(t)
            nd = tp["n_dom"][t]
            sp = shareable and _supp(nd)
            trows.append([name, lab, None if sp else nd] + ([_f(r["rho"]), _f(r["ci"][0]), _f(r["ci"][1]), _f(r["q"], 4), r["strength"]] if r and not sp
                                                          else [None] * 4 + ["weak" if not r else r["strength"]]) + [sp])
    doc["meta"]["topics"] = tmeta
    C.append(_table("notes-topics", "Note themes per source and overall (topic share vs score rank)",
                    ["scope", "topic", "n (dominant)", "rho with rank", "ci_low", "ci_high", "bh_q", "strength", "suppressed"], trows))
    for name, tp in N["topics"].items():
        sig = [r for r in tp["assoc"] if r["strength"] != "weak"]
        if sig:
            r = max(sig, key=lambda r: abs(r["rho"]))
            F.append(_find(f"{name} notes: theme '{r['topic']}' co-varies with score rank ({'higher' if r['rho'] > 0 else 'lower'} scores, {r['effect']}).", r["strength"], _ev(r)))
        else:
            F.append(_find(f"{name} notes: {tp['k']} themes found, none clearly tied to score rank.", "weak",
                           f"n={tp['n_docs']}, k={tp['k']}, stability={tp['stability']:.2f}"))

    # terms
    trs = []
    for name, tr in N["terms"].items():
        if not tr:
            continue
        for r in tr["rows"]:
            trs.append([name, r["direction"], r["term"], r["n_notes"], _f(r["rho"]), _f(r["ci"][0]), _f(r["ci"][1]), _f(r["q"], 4), r["strength"]])
        sig = [r for r in tr["rows"] if r["strength"] != "weak"]
        hi = [r["term"] for r in sorted([r for r in sig if r["rho"] > 0], key=lambda r: -r["rho"])[:5]]
        lo = [r["term"] for r in sorted([r for r in sig if r["rho"] < 0], key=lambda r: r["rho"])[:5]]
        if hi or lo:
            best = max(sig, key=lambda r: abs(r["rho"]))
            F.append(_find(f"{name}: wording linked to higher rank: {_fmt_terms(hi) or 'none'}; to lower rank: {_fmt_terms(lo) or 'none'}.",
                           best["strength"], f"n={best['n']}, {tr['n_terms']} terms scanned, top term rho={best['rho']:+.2f} [{best['ci'][0]:+.2f}, {best['ci'][1]:+.2f}], BH q={best['q']:.4f}"))
        else:
            F.append(_find(f"{name}: no term or bigram is reliably tied to score rank after correction.", "weak",
                           f"{tr['n_terms']} terms scanned, smallest BH q={tr['min_q']:.3f}"))
    C.append(_table("notes-rank-terms", "Terms and bigrams most associated with higher vs lower rank (continuous, no cutoff)",
                    ["scope", "direction", "term", "n notes with term", "rho", "ci_low", "ci_high", "bh_q", "strength"], trs,
                    subtitle="Top 10 each direction per scope; strength shows whether the association survives correction."))
    if "All sources" in N["terms"] and N["terms"]["All sources"]:
        rows_ = sorted(N["terms"]["All sources"]["rows"], key=lambda r: r["rho"])
        C.append(_chart("notes-rank-terms-bar", "hbar", "Terms vs rank, all sources (Spearman rho)",
                        {"labels": [r["term"] for r in rows_], "series": [{"name": "rho", "values": [_f(r["rho"]) for r in rows_]}]}, x="rho"))

    # note vs score consistency
    mrows, spts, dis = [], [], []
    for s, m in N["models"].items():
        if not m:
            continue
        mrows.append([s, m["n"], _f(m["rho"]), _f(m["ci"][0]), _f(m["ci"][1]), _f(m["p"], 4), m["strength"], m["effect"]])
        F.append(_find(f"{s}: a text-only cross-validated model recovers score rank with Spearman {m['rho']:+.2f}; notes {'agree' if m['rho'] > 0.3 else 'only weakly agree'} with the scores their authors gave.",
                       m["strength"], f"n={m['n']}, CV rho={m['rho']:+.2f} [{m['ci'][0]:+.2f}, {m['ci'][1]:+.2f}], perm p={m['p']:.4f}, ridge alpha={m['alpha']:.2g}"))
        order = np.argsort(-np.abs(m["gap"]))[:10]
        for i in order:
            dis.append([s, m["cand"][i], _f(m["pred_rank"][i]), _f(m["pred_rank"][i] + m["gap"][i]), _f(m["gap"][i])])
        for i in range(len(m["cand"])):
            spts.append({"x": _f(m["pred_rank"][i]), "y": _f(m["pred_rank"][i] + m["gap"][i]), "label": None if shareable else m["cand"][i], "group": s})
    C.append(_table("notes-consistency", "Note tone vs score rank (text-only cross-validated ridge on TF-IDF)",
                    ["source", "n", "CV rho", "ci_low", "ci_high", "perm_p", "strength", "effect_size"], mrows))
    if spts:
        C.append(_chart("notes-consistency-scatter", "scatter", "Predicted rank from note text vs actual score rank", {"points": spts},
                        x="rank implied by note text (out-of-fold)", y="actual score rank"))
    if dis and not shareable:
        C.append(_table("notes-discordant", "Candidates whose note tone disagrees most with their score rank (ids only; ranked, no cutoff)",
                        ["source", "candidate_id", "tone-implied rank", "score rank", "gap (score - tone)"], dis))
    elif dis:
        F.append(_find("A ranked list of candidates whose note tone disagrees with their score rank is available in the local copy only.", "weak", f"{len(dis)} listed across sources"))

    # style
    si = N.get("style")
    if si is not None:
        tt = si["terms"]
        ind = tt.sort_values("indep_weight", ascending=False).head(15)
        trk = tt.sort_values("track_weight", ascending=False).head(15)
        C.append(_table("notes-style-terms", "Data-derived language style terms", ["style", "term", "n notes", "rho with rank", "BH q"],
                        [["score-independent (impression-style / boilerplate)", r.term, int(r.n_notes), _f(r.rho), _f(r.q, 4)] for r in ind.itertuples()] +
                        [["score-tracking (rubric/evidence-style)", r.term, int(r.n_notes), _f(r.rho), _f(r.q, 4)] for r in trk.itertuples()]))
        srows = []
        for s in N["style_source"]:
            a_s, a_t = s["rho_subj"], s["rho_tone"]
            srows.append([s["source"], s["n"], _f(s["mean_subj"]), _f(a_s["rho"]), _f(a_t["rho"]), _f(s["diff"]), _f(s["diff_ci"][0]), _f(s["diff_ci"][1]), s["strength"]])
            F.append(_find(f"{s['source']}: score-independent wording intensity averages {s['mean_subj']:.2f}; it tracks score rank (rho {a_s['rho']:+.2f}) "
                           f"{'less' if s['diff'] > 0 else 'no less'} than rubric-style tone (rho {a_t['rho']:+.2f}).", s["strength"],
                           f"n={s['n']}, |rho_tone|-|rho_indep|={s['diff']:+.2f} [{s['diff_ci'][0]:+.2f}, {s['diff_ci'][1]:+.2f}]"))
        C.append(_table("notes-style-source", "Score-independent language intensity vs rubric tone, per source",
                        ["source", "n", "mean score-independent intensity", "rho(intensity, rank)", "rho(rubric tone, rank)", "|tone|-|intensity|", "ci_low", "ci_high", "strength"], srows))
        st = N.get("style_theme")
        if st:
            cr = []
            for c in st["cells"]:
                sp = shareable and _supp(c["n"])
                cr.append([c["source"], c["topic"], None if sp else c["n"], None if sp else _f(c["mean"]), None if sp else _f(c["ci"][0]),
                           None if sp else _f(c["ci"][1]), sp])
            C.append(_table("notes-style-by-theme", "Score-independent language intensity by dominant resume theme", ["source", "resume theme", "n", "mean intensity", "ci_low", "ci_high", "suppressed"], cr))
            labels = sorted({c["topic"] for c in st["cells"]})
            srcs = sorted({c["source"] for c in st["cells"]})
            C.append(_chart("notes-style-by-theme-bar", "bar", "Mean score-independent language intensity by resume theme",
                            {"labels": labels, "series": [{"name": s, "values": [next((None if (shareable and _supp(c["n"])) else _f(c["mean"]) for c in st["cells"]
                                                                                   if c["source"] == s and c["topic"] == lb), None) for lb in labels]} for s in srcs]}))
            recs = st["recs"]
            C.append(_table("notes-style-theme-bias", "Bias check: does language style differ by resume theme, conditioned on score rank? (partial Spearman)",
                            ["source", "resume theme", *REC_COLS], [_rec_row(r, (r["source"], r["topic"])) for r in recs]))
            sig = [r for r in recs if r["strength"] != "weak"]
            if sig:
                for r in sorted(sig, key=lambda r: -abs(r["rho"]))[:3]:
                    F.append(_find(f"Bias check: in {r['source']} notes, resume theme '{r['topic']}' goes with {'more' if r['rho'] > 0 else 'less'} score-independent (impression-style) wording at equal score rank ({r['effect']}).",
                                   r["strength"], _ev(r)))
            elif recs:
                r = max(recs, key=lambda r: abs(r["rho"]))
                F.append(_find("Bias check: no resume theme clearly goes with more impression-style wording once score rank is held fixed.", "weak", _ev(r)))
    return doc


def make_shareable(doc: dict) -> dict:
    d = copy.deepcopy(doc)
    for c in d["charts"]:
        if c["type"] == "scatter":
            for p in c["data"]["points"]:
                p["label"] = None
    return d


# --------------------------------------------------------------------------- entry points

def _load(processed_dir: Path) -> dict:
    p = Path(processed_dir)
    return {k: pd.read_csv(p / f"{k}.csv") for k in ("candidates", "exercises", "notes", "resumes")}


def run(processed_dir: Path, results_dir: Path) -> None:
    processed_dir, results_dir = Path(processed_dir), Path(results_dir)
    P = _load(processed_dir)
    rng = np.random.default_rng(SEED)
    R = analyze_resumes(P, rng)
    N = analyze_notes(P, np.random.default_rng(SEED + 1), R)
    for sub in ("local", "shareable"):
        (results_dir / sub).mkdir(parents=True, exist_ok=True)
    for name, render, res in (("resume_themes", render_resume, R), ("notes_themes", render_notes, N)):
        local = _clean(render(res, False))
        shareable = _clean(make_shareable(render(res, True)))
        (results_dir / "local" / f"{name}.json").write_text(json.dumps(local, indent=2))
        (results_dir / "shareable" / f"{name}.json").write_text(json.dumps(shareable, indent=2))


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, float):
        return None if not np.isfinite(o) else o
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


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
