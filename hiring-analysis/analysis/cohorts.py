"""Cohort-over-cohort comparison (section `cohorts`), written only for the pooled "All cohorts" data.

Compares hiring cycles such as "AMER FY27Q1" and "AMER FY27Q2": how many candidates reach each stage, how assessment
center scores are spread, how decisions are split, and which reviewers worked in more than one cohort. Tests are rank
based or count based and carry sample sizes and uncertainty, like every other section.

Cohorts are different groups of people, often scored by different reviewers, so a difference between cohorts can reflect
who applied rather than a change in the process. Outcomes are past human decisions, not job performance.

Run: python hiring-analysis/analysis/cohorts.py   (reads HIRING_OUT_DIR; uses the "All cohorts" folder)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from funnel_structure import Doc, MIN_GROUP, as_bool, box_stats, rd, suppress_boxes  # noqa: E402

SEED = 20240611
N_BOOT = 1000
DECISIONS = ("Hire", "Standby", "No Hire")
STAGES = [("Screened", "in_screen"), ("Reached TI", "reached_ti"), ("Attended AC", "attended_ac"), ("Hired", "hired")]


def cohort_order(names) -> list[str]:
    def key(n: str):
        m = re.search(r"FY(\d{2})\s?Q([1-4])", n)
        return (int(m.group(1)), int(m.group(2)), n) if m else (99, 9, n)
    return sorted(set(names), key=key)


def _grade(p: float, excludes_zero: bool = True) -> str:
    if p < 0.01 and excludes_zero:
        return "robust"
    if p < 0.05:
        return "suggestive"
    return "weak"


def _boot_spearman_ci(x: np.ndarray, y: np.ndarray, rng) -> tuple[float, float]:
    out = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(x), len(x))
        if np.ptp(x[i]) > 0 and np.ptp(y[i]) > 0:
            out.append(stats.spearmanr(x[i], y[i])[0])
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out else (float("nan"), float("nan"))


def _pct(a: int, b: int) -> float:
    return 100.0 * a / b if b else float("nan")


def _words(p: float) -> str:
    return "larger than chance would usually give" if p < 0.05 else "small enough that chance could explain it"


def analyze(processed_dir: Path) -> Doc:
    processed_dir = Path(processed_dir)
    c = pd.read_csv(processed_dir / "candidates.csv")
    ex = pd.read_csv(processed_dir / "exercises.csv")
    for col in ("in_screen", "reached_ti", "attended_ac", "hired"):
        c[col] = as_bool(c[col])
    c["ac_pct"] = pd.to_numeric(c["ac_pct"], errors="coerce") * 100
    order = cohort_order(c["cohort"])
    big = [k for k in order if (c["cohort"] == k).sum() >= MIN_GROUP]

    doc = Doc("cohorts", "Cohort comparison", [
        "Each cohort is a different group of candidates, usually with some different reviewers. A difference between cohorts can reflect who applied "
        "or who scored them, so it is not by itself a change in the process.",
        "Reviewers are linked across cohorts by their label (or by interviewer_map.csv when one is provided). If a label was reused for different "
        "people, reviewer links across cohorts are wrong.",
        "Cohorts with fewer than 5 candidates in a group are hidden in the shareable copy."])
    rng = np.random.default_rng(SEED)

    # funnel shares per cohort
    rows, series = [], {name: [] for name, _ in STAGES}
    for k in order:
        sub = c[c["cohort"] == k]
        for name, col in STAGES:
            series[name].append(rd(_pct(int(sub[col].sum()), len(sub)), 1) if len(sub) >= MIN_GROUP else None)
    doc.chart("cohort-funnel", "bar", "Share of each cohort's candidates reaching each stage",
              {"labels": order, "series": [{"name": n, "values": v} for n, v in series.items()]},
              subtitle="Percent of the cohort's candidates in the screening data; cohorts under 5 candidates are hidden",
              x_label="Cohort", y_label="Percent of cohort")

    # AC score spread per cohort
    groups = [box_stats(k, c.loc[(c["cohort"] == k) & c["attended_ac"], "ac_pct"].dropna()) for k in order]
    doc.chart("cohort-scores", "boxplot", "Assessment center total score by cohort (percent of 48)",
              {"groups": groups}, subtitle="Each box covers the middle half of attendees in that cohort",
              share={"groups": suppress_boxes(groups)}, y_label="Total score (%)")

    # decisions
    dec = {d: [] for d in DECISIONS}
    for k in order:
        sub = c[(c["cohort"] == k) & c["attended_ac"] & c["decision"].isin(DECISIONS)]
        for d in DECISIONS:
            dec[d].append(rd(_pct(int((sub["decision"] == d).sum()), len(sub)), 1) if len(sub) >= MIN_GROUP else None)
    doc.chart("cohort-decisions", "bar", "Final decisions by cohort",
              {"labels": order, "series": [{"name": d, "values": v} for d, v in dec.items()]},
              subtitle="Percent of assessment center attendees with a recorded decision", x_label="Cohort", y_label="Percent of attendees")

    # summary table
    trows = []
    for k in order:
        sub = c[c["cohort"] == k]
        att = sub[sub["attended_ac"]]
        n_att = int(len(att))
        hide = len(sub) < MIN_GROUP
        med = None if n_att < MIN_GROUP else rd(float(att["ac_pct"].median()), 1)
        trows.append([k, int(len(sub)), int(sub["reached_ti"].sum()), n_att, int(sub["hired"].sum()), med, hide])
    share_rows = [[r[0]] + [None] * 5 + [True] if r[1] < MIN_GROUP else r for r in trows]
    doc.chart("cohort-summary", "table", "Cohort summary",
              {"columns": ["Cohort", "Candidates", "Reached TI", "Attended AC", "Hired", "Median AC total (%)", "Suppressed"], "rows": trows},
              share={"columns": ["Cohort", "Candidates", "Reached TI", "Attended AC", "Hired", "Median AC total (%)", "Suppressed"], "rows": share_rows})

    # reviewers across cohorts
    ex = ex.dropna(subset=["assessor"])
    ex["assessor"] = ex["assessor"].astype(str)
    cnt = ex.groupby(["assessor", "cohort"])["candidate_id"].nunique().unstack(fill_value=0).reindex(columns=order, fill_value=0)
    if len(cnt):
        cols = ["Reviewer"] + order
        raw = [[str(r)] + [int(v) for v in row] for r, row in zip(cnt.index, cnt.to_numpy())]
        hidden = [[row[0]] + [v if v >= MIN_GROUP else None for v in row[1:]] for row in raw]
        doc.chart("cohort-reviewers", "table", "Candidates scored by each reviewer, per cohort",
                  {"columns": cols, "rows": raw}, subtitle="Counts under 5 are hidden in the shareable copy",
                  share={"columns": cols, "rows": hidden})
        multi = int((cnt.gt(0).sum(axis=1) > 1).sum())
        doc.caveats.append(f"{multi} of {len(cnt)} assessment center reviewers appear in more than one cohort.")

    if len(big) < 2:
        doc.finding("Fewer than two cohorts have enough candidates to compare.", "weak", f"cohorts with >= {MIN_GROUP} candidates: {len(big)}",
                    "There are not enough cohorts with enough people to compare them yet.")
        return doc

    # (1) AC scores across cohorts
    att = c[c["attended_ac"] & c["ac_pct"].notna() & c["cohort"].isin(big)]
    groups_v = [att.loc[att["cohort"] == k, "ac_pct"].to_numpy() for k in big if (att["cohort"] == k).sum() >= MIN_GROUP]
    names_v = [k for k in big if (att["cohort"] == k).sum() >= MIN_GROUP]
    if len(groups_v) >= 2:
        H, p_kw = stats.kruskal(*groups_v)
        idx = att["cohort"].map({k: i for i, k in enumerate(names_v)})
        ok = idx.notna()
        x, y = idx[ok].to_numpy(float), att.loc[ok, "ac_pct"].to_numpy(float)
        rho, p_rho = stats.spearmanr(x, y)
        lo, hi = _boot_spearman_ci(x, y, rng)
        med = {k: float(np.median(g)) for k, g in zip(names_v, groups_v)}
        first, last = names_v[0], names_v[-1]
        rising = med[last] > med[first]
        grade = _grade(min(p_kw, p_rho), lo > 0 or hi < 0)
        if grade == "weak":
            plain = (f"Assessment center scores did not change reliably from one cohort to the next. The typical total was {med[first]:.0f}% in {first} "
                     f"and {med[last]:.0f}% in {last}, a gap that could be chance.")
        else:
            plain = (f"Assessment center scores {'rose' if rising else 'fell'} across cohorts: the typical total went from {med[first]:.0f}% in {first} "
                     f"to {med[last]:.0f}% in {last}. This could reflect who applied or who scored them, not only the process.")
        doc.finding(f"AC total score {'increases' if rho > 0 else 'decreases'} with cohort order (Spearman rho={rho:+.2f}); cohorts differ overall (Kruskal-Wallis p={p_kw:.3g}).",
                    grade, f"n={len(y)} attendees in {len(groups_v)} cohorts, rho={rho:+.2f} [{lo:+.2f}, {hi:+.2f}], p={p_rho:.3g}; Kruskal-Wallis H={H:.2f}, p={p_kw:.3g}",
                    plain)

    # (2) reaching the assessment center
    scr = c[c["in_screen"] & c["cohort"].isin(big)]
    tab = pd.crosstab(scr["cohort"], scr["attended_ac"]).reindex(big)
    if tab.shape == (len(big), 2) and (tab.sum(axis=1) > 0).all():
        chi, p_c, _, _ = stats.chi2_contingency(tab.to_numpy())
        rates = {k: _pct(int(tab.loc[k, True]), int(tab.loc[k].sum())) for k in big}
        hi_k, lo_k = max(rates, key=rates.get), min(rates, key=rates.get)
        doc.finding(f"Share of screened candidates who attended the AC differs by cohort (chi-square p={p_c:.3g}).",
                    _grade(p_c), f"n={int(tab.to_numpy().sum())} screened in {len(big)} cohorts, chi-square={chi:.2f}, p={p_c:.3g}",
                    f"The share of screened candidates who reached the assessment center ran from {rates[lo_k]:.0f}% in {lo_k} to {rates[hi_k]:.0f}% in {hi_k}. "
                    f"The gap is {_words(p_c)}.")

    # (3) decisions
    dd = c[c["attended_ac"] & c["decision"].isin(DECISIONS) & c["cohort"].isin(big)].copy()
    dd["hire"] = dd["decision"].eq("Hire")
    tab = pd.crosstab(dd["cohort"], dd["hire"]).reindex(big).dropna()
    if tab.shape[1] == 2 and tab.shape[0] >= 2:
        chi, p_h, _, _ = stats.chi2_contingency(tab.to_numpy())
        rates = {k: _pct(int(tab.loc[k, True]), int(tab.loc[k].sum())) for k in tab.index}
        hi_k, lo_k = max(rates, key=rates.get), min(rates, key=rates.get)
        doc.finding(f"Share of AC attendees given Hire differs by cohort (chi-square p={p_h:.3g}).",
                    _grade(p_h), f"n={int(tab.to_numpy().sum())} attendees in {tab.shape[0]} cohorts, chi-square={chi:.2f}, p={p_h:.3g}",
                    f"Among people who attended the assessment center, the share who got a Hire decision ran from {rates[lo_k]:.0f}% in {lo_k} to "
                    f"{rates[hi_k]:.0f}% in {hi_k}. The gap is {_words(p_h)}.")
    return doc


def run(processed_dir: Path, results_dir: Path) -> None:
    doc = analyze(processed_dir)
    cands = pd.read_csv(Path(processed_dir) / "candidates.csv")
    doc.write(Path(results_dir), set(cands["candidate_id"].astype(str)))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from settings import load_settings, resolve_target

    target = resolve_target(load_settings()["out_dir"], sys.argv[1] if len(sys.argv) > 1 else None)
    run(target / "processed", target / "results")
    print(f"wrote cohorts results to {target / 'results'}")
