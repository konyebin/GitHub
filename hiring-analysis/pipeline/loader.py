"""Load the redacted resumes and the two workbooks into one shared, tidy dataset.

Reads (paths come from hiring-analysis/.env or environment, never hardcoded):
  HIRING_DATA_DIR   folder holding screen_review.xlsx, assessment_center.xlsx and resumes/*.docx
  HIRING_OUT_DIR    where processed CSVs are written (default <DATA_DIR>/processed)

File names are matched loosely so the real files work too: any .xlsx whose name contains "screen" is the
screening workbook, any containing "score" or "assessment" is the assessment center workbook.

Writes to HIRING_OUT_DIR:
  candidates.csv       one row per candidate: funnel flags, outcomes, aggregate scores, proxy-risk fields
  scores_long.csv      candidate_id, exercise, competency, score
  exercises.csv        candidate_id, exercise, total, recommendation, assessor
  notes.csv            candidate_id, source, reviewer, text      (free-text notes, one row per note)
  resumes.csv          candidate_id, text                        (redaction tags stripped)
  audit_only.csv       candidate_id, country, salutation         (sensitive; never used as features)
  data_quality.json    warnings (blank cells, missing resumes, unmatched ids, example rows skipped)

Outcomes are past human decisions, not job performance.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import openpyxl
import pandas as pd
from docx import Document

TAG = re.compile(r"\[(NAME|EMAIL|PHONE|LINKEDIN)\]")
EXERCISES = ("Interview", "Role Play", "Presentation")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def clean(v):
    if isinstance(v, str):
        v = v.strip()
    return v


def find_header(ws, needle: str, max_rows: int = 30) -> int:
    for r in range(1, max_rows + 1):
        for c in ws[r]:
            if isinstance(c.value, str) and needle.lower() in c.value.lower():
                return r
    raise ValueError(f"header row containing {needle!r} not found")


def load_screen(path: Path, warnings: list) -> pd.DataFrame:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    hr = find_header(ws, "Person ID")
    headers = [clean(c.value) for c in ws[hr]]
    rows = []
    for r in ws.iter_rows(min_row=hr + 1, values_only=True):
        if all(v in (None, "") for v in r):
            continue
        rows.append(dict(zip(headers, r)))
    df = pd.DataFrame(rows)
    df = df[[c for c in df.columns if c]]

    def col(prefix: str) -> str:
        for c in df.columns:
            if str(c).lower().startswith(prefix.lower()):
                return c
        raise KeyError(prefix)

    out = pd.DataFrame({
        "candidate_id": df[col("Person ID")].astype(str).str.strip(),
        "proxy_graduation": df[col("Graduation")],
        "proxy_skills_tag": df[col("Skills")],
        "proxy_home_city": df[col("Home cities")],
        "screen_recruiter": df[col("Recruiter")],
        "screen_score_raw": df[col("Score")],
        "screen_passfail": df[col("Pass/Fail")],
        "screen_comments": df[col("Additional Comments")],
        "screen_notes": df[col("Notes")],
        "screen_invited": df[col("Recommended")],
        "screen_status": df[col("Status")],
    })
    out["screen_score"] = pd.to_numeric(out["screen_score_raw"], errors="coerce")
    out["reached_ti"] = out["screen_score"].notna()
    blanks = int(df.isna().sum().sum())
    if blanks:
        warnings.append(f"screening workbook has {blanks} blank cells (real data is expected to have none)")
    return out


def load_assessment(path: Path, warnings: list) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    hr = find_header(ws, "Candidate Name")
    headers = [clean(c.value) for c in ws[hr]]
    idx = {h: i for i, h in enumerate(headers) if h}
    cand_i = next(i for i, h in enumerate(headers) if h and h.lower().startswith("candidate name"))

    # Exercises appear in a fixed order; each has 4 competency columns, a total, a recommendation, comments.
    comp_cols: dict[str, list[int]] = {e: [] for e in EXERCISES}
    meta: dict[str, dict[str, int]] = {e: {} for e in EXERCISES}
    totals = [i for i, h in enumerate(headers) if h and h.lower().startswith("total -")]
    if len(totals) != 3:
        raise ValueError(f"expected 3 exercise TOTAL columns, found {len(totals)}")
    for ex, t in zip(EXERCISES, totals):
        comp_cols[ex] = list(range(t - 4, t))
        meta[ex] = {"total": t, "rec": t + 1, "notes": t + 2}
    names = {i: re.sub(r"^\d+\.\s*", "", headers[i]) for e in EXERCISES for i in comp_cols[e]}
    assessor_i = {e: next((i for i, h in enumerate(headers) if h and h.lower().startswith("assessor") and e.lower() in h.lower()), None)
                  for e in EXERCISES}
    decision_i = next(i for i, h in enumerate(headers) if h and "no hire" in h.lower())
    overall_notes_i = max(i for i, h in enumerate(headers) if h and h.lower().startswith("comments/notes"))
    overall_notes_i = overall_notes_i if overall_notes_i > decision_i else None
    total_i = next(i for i, h in enumerate(headers) if h and h.lower().startswith("total score"))
    country_i = next((i for i, h in enumerate(headers) if h and h.lower() == "country"), None)
    salut_i = next((i for i, h in enumerate(headers) if h and h.lower().startswith("salutation")), None)

    long_rows, ex_rows, note_rows, cand_rows, audit_rows = [], [], [], [], []
    blanks = 0
    for r in ws.iter_rows(min_row=hr + 1, values_only=True):
        cid = clean(r[cand_i])
        if cid in (None, ""):
            continue
        if str(cid).lower().startswith("example"):
            warnings.append(f"skipped example row {cid!r}")
            continue
        blanks += sum(1 for v in r if v in (None, ""))
        total_score = r[total_i]
        for ex in EXERCISES:
            scores = [r[i] for i in comp_cols[ex]]
            for i, s in zip(comp_cols[ex], scores):
                long_rows.append({"candidate_id": cid, "exercise": ex, "competency": names[i], "score": s})
            ex_rows.append({"candidate_id": cid, "exercise": ex, "total": r[meta[ex]["total"]],
                            "recommendation": r[meta[ex]["rec"]],
                            "assessor": r[assessor_i[ex]] if assessor_i[ex] is not None else None})
            note_rows.append({"candidate_id": cid, "source": ex, "reviewer": r[assessor_i[ex]] if assessor_i[ex] is not None else None,
                              "text": r[meta[ex]["notes"]]})
        if overall_notes_i is not None:
            note_rows.append({"candidate_id": cid, "source": "Overall", "reviewer": None, "text": r[overall_notes_i]})
        cand_rows.append({"candidate_id": cid, "ac_total": total_score, "decision": clean(r[decision_i])})
        audit_rows.append({"candidate_id": cid, "country": r[country_i] if country_i is not None else None,
                           "salutation": clean(r[salut_i]) if salut_i is not None else None})
    if blanks:
        warnings.append(f"assessment workbook has {blanks} blank cells (real data is expected to have none)")
    cands = pd.DataFrame(cand_rows)
    return cands, pd.DataFrame(long_rows), pd.DataFrame(ex_rows), pd.DataFrame(note_rows), pd.DataFrame(audit_rows)


def load_resumes(folder: Path) -> pd.DataFrame:
    rows = []
    for p in sorted(folder.glob("*.docx")):
        d = Document(p)
        parts = [para.text for para in d.paragraphs if para.text.strip()]
        for t in d.tables:
            for tr in t.rows:
                parts += [c.text for c in tr.cells if c.text.strip()]
        text = TAG.sub(" ", "\n".join(parts))
        rows.append({"candidate_id": p.stem, "text": re.sub(r"[ \t]+", " ", text).strip()})
    return pd.DataFrame(rows)


def build(data_dir: Path, out_dir: Path) -> dict:
    warnings: list[str] = []
    xlsx = list(data_dir.glob("*.xlsx"))
    screen_p = next(p for p in xlsx if "screen" in p.name.lower())
    ac_p = next(p for p in xlsx if any(k in p.name.lower() for k in ("score", "assessment")) and p != screen_p)
    screen = load_screen(screen_p, warnings)
    ac, long_df, ex_df, notes_df, audit = load_assessment(ac_p, warnings)
    resumes = load_resumes(data_dir / "resumes")

    screen["has_resume"] = screen["candidate_id"].isin(resumes["candidate_id"])
    cands = screen.merge(ac, on="candidate_id", how="outer", indicator=True)
    cands["in_screen"] = cands["_merge"].isin(["both", "left_only"])
    cands["attended_ac"] = cands["_merge"].isin(["both", "right_only"])
    unmatched = cands[cands["_merge"] == "right_only"]["candidate_id"].tolist()
    if unmatched:
        warnings.append(f"{len(unmatched)} assessment candidates have no screening row: {unmatched[:5]}")
    cands = cands.drop(columns="_merge")
    cands["has_resume"] = cands["candidate_id"].isin(resumes["candidate_id"])
    cands["hired"] = cands["decision"].eq("Hire")
    cands["ac_total"] = pd.to_numeric(cands["ac_total"], errors="coerce")
    cands["ac_pct"] = cands["ac_total"] / 48
    cands["interviewed"] = cands["reached_ti"].fillna(False)
    missing_resume = cands.loc[~cands["has_resume"], "candidate_id"].tolist()
    if missing_resume:
        warnings.append(f"{len(missing_resume)} candidates have no resume file")

    text_cols = ["screen_notes", "screen_comments"]
    ti_notes = cands[["candidate_id", "screen_recruiter", "screen_notes"]].rename(
        columns={"screen_recruiter": "reviewer", "screen_notes": "text"})
    ti_notes["source"] = "Technical interview"
    ti_notes = ti_notes[ti_notes["text"].notna() & ~ti_notes["text"].astype(str).str.upper().eq("N/A")]
    notes = pd.concat([ti_notes[["candidate_id", "source", "reviewer", "text"]], notes_df], ignore_index=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    cands.to_csv(out_dir / "candidates.csv", index=False)
    long_df.to_csv(out_dir / "scores_long.csv", index=False)
    ex_df.to_csv(out_dir / "exercises.csv", index=False)
    notes.to_csv(out_dir / "notes.csv", index=False)
    resumes.to_csv(out_dir / "resumes.csv", index=False)
    audit.to_csv(out_dir / "audit_only.csv", index=False)
    summary = {"n_candidates": int(len(cands)), "n_in_screen": int(cands["in_screen"].sum()),
               "n_reached_ti": int(cands["interviewed"].sum()), "n_attended_ac": int(cands["attended_ac"].sum()),
               "n_resumes": int(len(resumes)), "warnings": warnings}
    (out_dir / "data_quality.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    load_env(here / ".env")
    data_dir = Path(os.environ.get("HIRING_DATA_DIR", here / "data" / "synthetic"))
    out_dir = Path(os.environ.get("HIRING_OUT_DIR", data_dir / "processed"))
    print(json.dumps(build(data_dir, out_dir), indent=2))
