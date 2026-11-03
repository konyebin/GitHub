"""Load the redacted resumes and every cohort's workbooks into one shared, tidy dataset.

Reads (paths come from hiring-analysis/.env or environment via settings.py, never hardcoded):
  HIRING_DATA_DIR   parent folder. Workbooks may sit in one folder per cohort (for example "AMER FY27Q1/") or directly in
                    the parent. Resumes live in one shared resumes/ folder, so candidateN numbers stay unique.
  HIRING_OUT_DIR    where outputs are written (default <DATA_DIR>/processed)

A *cohort* is a hiring cycle such as "AMER FY27Q1". Its name comes from the workbook filename when it contains one
(FY27Q1_AMER_ASE_Scores..., AMER FY27Q1 ...), otherwise from the name of the folder the workbook sits in (the redactor
renames files to candidateN.xlsx, so the folder is the fallback). Workbooks are recognised by content, not filename:
a sheet with a "Full name" (or older "Person ID") header is screening data, a sheet with a "Candidate Name" header is assessment center scores.
Each sheet of a scores workbook is one *AC day* (for example "AMER Oct 15"); its date is worked out from the cohort's
fiscal quarter.

Optional data_dir/interviewer_map.csv (columns cohort,label,person; cohort may be blank for all cohorts) renames
reviewer labels so the same person is linked across cohorts. Without it, the same label means the same person.

Writes, for "All cohorts" and for each cohort, <out>/<name>/processed/:
  candidates.csv       one row per candidate: cohort, ac_day, ac_date, funnel flags, outcomes, aggregate scores, proxy-risk fields
  scores_long.csv      candidate_id, exercise, competency, score
  exercises.csv        candidate_id, exercise, total, recommendation, assessor
  notes.csv            candidate_id, source, reviewer, text      (free-text notes, one row per note)
  resumes.csv          candidate_id, text                        (redaction tags stripped)
  audit_only.csv       candidate_id, country, salutation         (sensitive; never used as features)
  data_quality.json    counts and warnings (blank cells, missing resumes, unmatched ids, skipped sheets)

A candidate id that appears in two cohorts stops the run: the redactor never reuses a number inside one output folder,
so this means resumes from different cohorts were redacted into different folders.

Outcomes are past human decisions, not job performance.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd
from docx import Document

ALL = "All cohorts"
TAG = re.compile(r"\[(NAME|EMAIL|PHONE|LINKEDIN)\]")
EXERCISES = ("Interview", "Role Play", "Presentation")
REGIONS = ("AMER", "EMEAR", "EMEA", "APJC", "APAC", "LATAM", "GLOBAL")
_FQ = re.compile(r"FY\s?(\d{2})\s?[ _-]?\s?Q([1-4])", re.I)
_REGION = re.compile(r"(?<![A-Za-z])(" + "|".join(REGIONS) + r")(?![A-Za-z])", re.I)
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
SKIP_DIRS = {"resumes", "processed"}
SCREEN_COLS = ["candidate_id", "proxy_graduation", "proxy_skills_tag", "proxy_home_city", "screen_recruiter",
               "screen_score_raw", "screen_passfail", "screen_comments", "screen_notes", "screen_invited",
               "screen_status", "screen_score", "reached_ti"]


def clean(v):
    if isinstance(v, str):
        v = v.strip()
    return v


def parse_cohort(text: str) -> str | None:
    """"FY27Q3_AMER_ASE_Scores" or "AMER FY27Q3" -> "AMER FY27Q3" (just "FY27Q3" when no region is present)."""
    m = _FQ.search(text or "")
    if not m:
        return None
    r = _REGION.search(text)
    label = f"FY{m.group(1)}Q{m.group(2)}"
    return f"{r.group(1).upper()} {label}" if r else label


def fiscal_window(cohort: str, fiscal_start_month: int) -> tuple[date, date] | None:
    m = _FQ.search(cohort or "")
    if not m:
        return None
    fy, q = 2000 + int(m.group(1)), int(m.group(2))
    start_year = fy if fiscal_start_month == 1 else fy - 1
    months = (fiscal_start_month - 1) + 3 * (q - 1)
    start = date(start_year + months // 12, months % 12 + 1, 1)
    end_m = months + 3
    return start, date(start_year + end_m // 12, end_m % 12 + 1, 1)


def parse_ac_date(sheet_name: str, cohort: str | None, fiscal_start_month: int, warnings: list):
    """Date of an AC day sheet such as "AMER Oct 15". The year comes from the cohort's fiscal quarter."""
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})\b", sheet_name)
    mon = MONTHS.index(m.group(1)[:3].lower()) + 1 if m and m.group(1)[:3].lower() in MONTHS else None
    win = fiscal_window(cohort, fiscal_start_month) if cohort else None
    if not m or mon is None or win is None:
        warnings.append(f"AC day sheet {sheet_name!r}: could not work out a date (needs a name like 'AMER Oct 15' and a cohort like 'AMER FY27Q1')")
        return None
    options = []
    for y in (win[0].year, win[0].year + 1):
        try:
            options.append(date(y, mon, int(m.group(2))))
        except ValueError:
            pass
    if not options:
        warnings.append(f"AC day sheet {sheet_name!r}: not a valid date")
        return None
    inside = [d for d in options if win[0] <= d < win[1]]
    if inside:
        return inside[0].isoformat()
    mid = win[0].toordinal() + (win[1].toordinal() - win[0].toordinal()) // 2
    best = min(options, key=lambda d: abs(d.toordinal() - mid))
    warnings.append(f"AC day sheet {sheet_name!r} falls outside {cohort}; dated {best.isoformat()}")
    return best.isoformat()


def find_header(ws, needle: str, max_rows: int = 30) -> int:
    for r in range(1, max_rows + 1):
        for c in ws[r]:
            if isinstance(c.value, str) and needle.lower() in c.value.lower():
                return r
    raise ValueError(f"header row containing {needle!r} not found")


def workbook_kind(path: Path) -> str | None:
    """"screen" if any sheet has a Person ID or Full name header, "scores" if any has Candidate Name, otherwise None."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    kinds = set()
    for ws in wb.worksheets:
        text = [str(c).lower() for row in ws.iter_rows(min_row=1, max_row=30, values_only=True) for c in row if isinstance(c, str)]
        if any("person id" in t or t.strip() == "full name" for t in text):
            kinds.add("screen")
        if any("candidate name" in t for t in text):
            kinds.add("scores")
    wb.close()
    return "screen" if kinds == {"screen"} else "scores" if kinds == {"scores"} else None


def discover(data_dir: Path, out_dir: Path | None, warnings: list) -> dict[str, dict[str, list[Path]]]:
    """Group every workbook under data_dir (top level and one folder deep) by cohort and kind."""
    files = [p for p in data_dir.glob("*.xlsx")]
    for d in sorted(data_dir.iterdir()):
        if not d.is_dir() or d.name.lower() in SKIP_DIRS or d.name.startswith((".", "_")):
            continue
        if out_dir is not None and d.resolve() == out_dir.resolve():
            continue
        files += list(d.glob("*.xlsx"))
    groups: dict[str, dict[str, list[Path]]] = {}
    for p in sorted(files):
        if p.name.startswith("~$"):
            continue
        cohort = parse_cohort(p.stem)
        parent = parse_cohort(p.parent.name) if p.parent != data_dir else None
        if cohort and parent and cohort != parent:
            warnings.append(f"{p.name}: filename says {cohort} but its folder says {parent}; using the filename")
        cohort = cohort or parent
        kind = workbook_kind(p)
        if kind is None:
            warnings.append(f"{p.name}: not recognised as a screening workbook (Full name or Person ID header) or scores workbook (Candidate Name header); skipped")
            continue
        if cohort is None:
            raise ValueError(f"cannot tell which cohort {p.name!r} belongs to. Put it in a folder named like 'AMER FY27Q1' "
                             f"or include the cohort in the filename (for example FY27Q1_AMER_ASE_Scores.xlsx)")
        groups.setdefault(cohort, {"screen": [], "scores": []})[kind].append(p)
    if not groups:
        raise ValueError(f"no screening or scores workbooks found under {data_dir}")
    return dict(sorted(groups.items()))


def load_screen(path: Path, warnings: list) -> pd.DataFrame:
    wb = openpyxl.load_workbook(path, data_only=True)
    parts = []
    for ws in wb.worksheets:
        try:
            parts.append(_load_screen_sheet(ws, warnings))
        except ValueError as e:
            warnings.append(f"screening sheet {ws.title!r} skipped: {e}")
    if not parts:
        raise ValueError(f"no screening sheet with a Full name or Person ID header in {path.name}")
    return pd.concat(parts, ignore_index=True)


def _load_screen_sheet(ws, warnings: list) -> pd.DataFrame:
    hr = next((r for r in range(1, 31) for c in ws[r]
               if isinstance(c.value, str) and re.match(r"\s*(person\s*id|full\s*name)\s*$", c.value, re.I)), None)
    if hr is None:
        raise ValueError("header row containing 'Person ID' or 'Full name' not found")
    headers = [clean(c.value) for c in ws[hr]]
    rows = []
    for r in ws.iter_rows(min_row=hr + 1, values_only=True):
        if all(v in (None, "") for v in r):
            continue
        rows.append(dict(zip(headers, r)))
    df = pd.DataFrame(rows)
    df = df[[c for c in df.columns if c]]

    def col(pattern: str):
        for c in df.columns:
            if re.match(pattern, str(c).strip(), re.I):
                return c
        return None

    wanted = {
        "proxy_graduation": r"graduation", "proxy_skills_tag": r"skills", "proxy_home_city": r"home\s*cit",
        "screen_recruiter": r"recruiter", "screen_score_raw": r"score", "screen_passfail": r"pass\s*/?\s*fail",
        "screen_comments": r"additional\s*comments", "screen_notes": r"notes", "screen_invited": r"recommended",
        "screen_status": r"status",
    }
    id_col = col(r"person\s*id") or col(r"full\s*name")
    out = pd.DataFrame({"candidate_id": df[id_col].astype(str).str.strip()})
    absent = []
    for field, pat in wanted.items():
        c = col(pat)
        out[field] = df[c] if c is not None else None
        if c is None:
            absent.append(field)
    if absent:
        warnings.append(f"screening sheet {ws.title!r} has no column for: {', '.join(absent)} (those fields are left empty)")
    out["screen_score"] = pd.to_numeric(out["screen_score_raw"], errors="coerce")
    out["reached_ti"] = out["screen_score"].notna()
    blanks = int(df.isna().sum().sum())
    if blanks:
        warnings.append(f"screening sheet {ws.title!r} has {blanks} blank cells (real data is expected to have none)")
    return out


def load_assessment(path: Path, warnings: list, cohort: str | None = None, fiscal_start_month: int = 8
                    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read every AC day sheet (for example "AMER Oct 15") of a scores workbook and stack them.

    Sheets without a "Candidate Name" header are skipped with a warning. The sheet name is kept as `ac_day`.
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    parts = []
    for ws in wb.worksheets:
        try:
            parts.append(_load_assessment_sheet(ws, warnings, cohort, fiscal_start_month))
        except ValueError as e:
            warnings.append(f"assessment sheet {ws.title!r} skipped: {e}")
    if not parts:
        raise ValueError("no assessment sheet with a 'Candidate Name' header found")
    frames = [pd.concat([p[i] for p in parts], ignore_index=True) for i in range(5)]
    examples = [w for w in warnings if w.startswith("skipped example row")]
    if examples:
        warnings[:] = [w for w in warnings if w not in examples] + [f"skipped the template example row on {len(examples)} AC day sheets"]
    dup = frames[0]["candidate_id"][frames[0]["candidate_id"].duplicated()].tolist()
    if dup:
        warnings.append(f"{len(dup)} candidates appear on more than one AC day sheet: {dup[:5]}")
    return tuple(frames)


def _load_assessment_sheet(ws, warnings: list, cohort: str | None = None, fiscal_start_month: int = 8):
    ac_day = ws.title
    hr = find_header(ws, "Candidate Name")
    ac_date = parse_ac_date(ac_day, cohort, fiscal_start_month, warnings)
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
            warnings.append(f"skipped example row {cid!r} on sheet {ac_day!r}")
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
        cand_rows.append({"candidate_id": cid, "ac_total": total_score, "decision": clean(r[decision_i]), "ac_day": ac_day, "ac_date": ac_date})
        audit_rows.append({"candidate_id": cid, "country": r[country_i] if country_i is not None else None,
                           "salutation": clean(r[salut_i]) if salut_i is not None else None})
    if blanks:
        warnings.append(f"assessment sheet {ac_day!r} has {blanks} blank cells (real data is expected to have none)")
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
    return pd.DataFrame(rows, columns=["candidate_id", "text"])


def load_interviewer_map(data_dir: Path) -> dict[tuple[str, str], str]:
    p = data_dir / "interviewer_map.csv"
    if not p.exists():
        return {}
    m = pd.read_csv(p, dtype=str).fillna("")
    m.columns = [c.strip().lower() for c in m.columns]
    missing = {"cohort", "label", "person"} - set(m.columns)
    if missing:
        raise ValueError(f"interviewer_map.csv needs columns cohort,label,person (missing {sorted(missing)})")
    return {((parse_cohort(r.cohort) or r.cohort.strip() or "*"), r.label.strip()): r.person.strip() for r in m.itertuples()}


def apply_map(df: pd.DataFrame, col: str, mapping: dict) -> None:
    if not mapping or col not in df.columns or df.empty:
        return
    def one(row):
        v = row[col]
        if not isinstance(v, str):
            return v
        return mapping.get((row["cohort"], v.strip())) or mapping.get(("*", v.strip())) or v
    df[col] = df.apply(one, axis=1)


def _write(folder: Path, frames: dict, cands: pd.DataFrame, extra: dict) -> dict:
    ids = set(cands["candidate_id"])
    out = folder / "processed"
    out.mkdir(parents=True, exist_ok=True)
    cands.to_csv(out / "candidates.csv", index=False)
    for name in ("scores_long", "exercises", "notes", "resumes", "audit_only"):
        df = frames[name]
        df[df["candidate_id"].isin(ids)].to_csv(out / f"{name}.csv", index=False)
    summary = {"n_candidates": int(len(cands)), "n_in_screen": int(cands["in_screen"].sum()),
               "n_reached_ti": int(cands["interviewed"].sum()), "n_attended_ac": int(cands["attended_ac"].sum()),
               "n_resumes": int(frames["resumes"]["candidate_id"].isin(ids).sum()), **extra}
    (out / "data_quality.json").write_text(json.dumps(summary, indent=2))
    return summary


def build(data_dir: Path, out_dir: Path, fiscal_start_month: int = 8, min_cohort_ac: int = 30) -> dict:
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    global_warnings: list[str] = []
    groups = discover(data_dir, out_dir, global_warnings)
    resumes = load_resumes(data_dir / "resumes")
    mapping = load_interviewer_map(data_dir)

    per_cohort_warn: dict[str, list[str]] = {}
    cand_parts, long_parts, ex_parts, note_parts, audit_parts = [], [], [], [], []
    for cohort, files in groups.items():
        w: list[str] = []
        per_cohort_warn[cohort] = w
        if not files["screen"]:
            w.append("no screening workbook for this cohort; funnel stages before the assessment center are unavailable")
        if not files["scores"]:
            w.append("no scores workbook for this cohort")
        screens = [load_screen(p, w) for p in files["screen"]]
        screen = pd.concat(screens, ignore_index=True) if screens else pd.DataFrame(columns=SCREEN_COLS)
        if screen["candidate_id"].duplicated().any():
            w.append(f"{int(screen['candidate_id'].duplicated().sum())} duplicate Person IDs in the screening data")
            screen = screen.drop_duplicates("candidate_id")
        acs = [load_assessment(p, w, cohort, fiscal_start_month) for p in files["scores"]]
        if acs:
            ac, long_df, ex_df, notes_df, audit = (pd.concat([a[i] for a in acs], ignore_index=True) for i in range(5))
        else:
            ac = pd.DataFrame(columns=["candidate_id", "ac_total", "decision", "ac_day", "ac_date"])
            long_df, ex_df, notes_df, audit = (pd.DataFrame(columns=["candidate_id"]) for _ in range(4))
        merged = screen.merge(ac, on="candidate_id", how="outer", indicator=True)
        merged["in_screen"] = merged["_merge"].isin(["both", "left_only"])
        merged["attended_ac"] = merged["_merge"].isin(["both", "right_only"])
        unmatched = merged[merged["_merge"] == "right_only"]["candidate_id"].tolist()
        if unmatched and files["screen"]:
            w.append(f"{len(unmatched)} assessment candidates have no screening row: {unmatched[:5]}")
        merged = merged.drop(columns="_merge")
        merged.insert(1, "cohort", cohort)
        cand_parts.append(merged)
        for df in (ex_df, notes_df):
            df["cohort"] = cohort
        long_parts.append(long_df), ex_parts.append(ex_df), note_parts.append(notes_df), audit_parts.append(audit)

    cands = pd.concat(cand_parts, ignore_index=True)
    clash = cands.groupby("candidate_id")["cohort"].nunique()
    clash = clash[clash > 1]
    if len(clash):
        where = {c: sorted(cands.loc[cands["candidate_id"] == c, "cohort"].unique()) for c in clash.index[:5]}
        raise ValueError(
            f"{len(clash)} candidate ids appear in more than one cohort, for example {where}. Resumes from every cohort should go "
            f"through the same redactor output folder so each candidateN is used once. A person who applies in two cohorts must get "
            f"a new candidateN in the second one.")

    cands["has_resume"] = cands["candidate_id"].isin(resumes["candidate_id"])
    cands["hired"] = cands["decision"].eq("Hire")
    cands["ac_total"] = pd.to_numeric(cands["ac_total"], errors="coerce")
    cands["ac_pct"] = cands["ac_total"] / 48
    cands["interviewed"] = cands["reached_ti"].fillna(False).astype(bool)
    for flag in ("in_screen", "attended_ac"):
        cands[flag] = cands[flag].astype(bool)
    for cohort, sub in cands.groupby("cohort"):
        missing = sub.loc[~sub["has_resume"], "candidate_id"].tolist()
        if missing:
            per_cohort_warn[cohort].append(f"{len(missing)} candidates have no resume file")
    orphans = sorted(set(resumes["candidate_id"]) - set(cands["candidate_id"]))
    if orphans:
        global_warnings.append(f"{len(orphans)} resume files match no candidate in any workbook: {orphans[:5]}")

    long_df, ex_df, notes_df, audit = (pd.concat(p, ignore_index=True) for p in (long_parts, ex_parts, note_parts, audit_parts))
    ti_notes = cands[["candidate_id", "cohort", "screen_recruiter", "screen_notes"]].rename(
        columns={"screen_recruiter": "reviewer", "screen_notes": "text"})
    ti_notes["source"] = "Technical interview"
    ti_notes = ti_notes[ti_notes["text"].notna() & ~ti_notes["text"].astype(str).str.upper().eq("N/A")]
    notes = pd.concat([ti_notes[["candidate_id", "cohort", "source", "reviewer", "text"]], notes_df], ignore_index=True)
    apply_map(cands, "screen_recruiter", mapping)
    apply_map(ex_df, "assessor", mapping)
    apply_map(notes, "reviewer", mapping)
    notes = notes.drop(columns="cohort")
    if mapping:
        global_warnings.append(f"interviewer_map.csv applied ({len(mapping)} entries)")
    else:
        global_warnings.append("no interviewer_map.csv: the same reviewer label is treated as the same person in every cohort")

    frames = {"scores_long": long_df, "exercises": ex_df, "notes": notes, "resumes": resumes, "audit_only": audit}
    cohort_rows, targets = [], []
    for cohort in groups:
        sub = cands[cands["cohort"] == cohort]
        summary = _write(out_dir / cohort, frames, sub, {"cohort": cohort, "warnings": per_cohort_warn[cohort]})
        analyze = len(groups) == 1 or summary["n_attended_ac"] >= min_cohort_ac
        if not analyze:
            per_cohort_warn[cohort].append(
                f"only {summary['n_attended_ac']} AC attendees (fewer than {min_cohort_ac}): counted in '{ALL}' but not analysed on its own")
            summary["warnings"] = per_cohort_warn[cohort]
            (out_dir / cohort / "processed" / "data_quality.json").write_text(json.dumps(summary, indent=2))
        cohort_rows.append({"name": cohort, **{k: summary[k] for k in ("n_candidates", "n_in_screen", "n_reached_ti", "n_attended_ac", "n_resumes")},
                            "analyzed": analyze})
        if analyze:
            targets.append({"name": cohort, "dir": str(out_dir / cohort)})
    result = {"cohorts": cohort_rows, "targets": targets, "warnings": global_warnings + [f"{c}: {m}" for c, ms in per_cohort_warn.items() for m in ms]}
    if len(groups) > 1:
        pooled = _write(out_dir / ALL, frames, cands, {"cohorts": cohort_rows, "warnings": result["warnings"]})
        targets.insert(0, {"name": ALL, "dir": str(out_dir / ALL)})
        result.update({k: pooled[k] for k in ("n_candidates", "n_in_screen", "n_reached_ti", "n_attended_ac", "n_resumes")})
    else:
        only = cohort_rows[0]
        result.update({k: only[k] for k in ("n_candidates", "n_in_screen", "n_reached_ti", "n_attended_ac", "n_resumes")})
    result["targets"] = targets
    return result


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from settings import load_settings

    cfg = load_settings()
    print(json.dumps(build(cfg["data_dir"], cfg["out_dir"], cfg["fiscal_start_month"], cfg["min_cohort_ac"]), indent=2))
