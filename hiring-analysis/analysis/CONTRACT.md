# Analysis contract

Every analysis module lives in `hiring-analysis/analysis/<name>.py` and exposes
`run(processed_dir: Path, results_dir: Path) -> None`, plus a `__main__` that reads `HIRING_OUT_DIR` the way
`pipeline/loader.py` does. It reads only the CSVs below and writes JSON files to `results_dir`.
Run the pipeline first: `python hiring-analysis/pipeline/loader.py` (writes `data/synthetic/processed/`).

## Inputs (`processed_dir`)

- `candidates.csv`: candidate_id, in_screen, reached_ti, attended_ac, hired, has_resume, screen_score (TI score, NaN if none),
  screen_passfail, screen_invited, screen_status, screen_recruiter, ac_total (0-48), ac_pct, decision (Hire/Standby/No Hire, NaN if never in AC),
  proxy_graduation, proxy_skills_tag, proxy_home_city.
- `scores_long.csv`: candidate_id, exercise (Interview / Role Play / Presentation), competency, score (1-4).
- `exercises.csv`: candidate_id, exercise, total (0-16), recommendation (Yes/Standby/No), assessor.
- `notes.csv`: candidate_id, source (Technical interview / Interview / Role Play / Presentation / Overall), reviewer, text.
- `resumes.csv`: candidate_id, text (redaction tags already stripped).
- `audit_only.csv`: country, salutation. Never use these as features or in any analysis. Only the optional audit step may read them.

## Rules (all modules)

1. No fixed thresholds or cutoffs as the primary lens. Use within-cohort percentile ranks, rank correlations (Spearman / Kendall),
   ordinal or rank-based models, and continuous measures. Where a grouping is unavoidable (clusters, terciles for display), derive it
   from the data and say so.
2. Outcomes (reached TI, attended AC, hired, decision) are past human decisions, not job performance. Phrase findings as
   "what the process rewarded", never "what predicts success".
3. Selection effects: later-stage scores exist only for candidates who passed earlier gates. Do not impute them. Say when a
   comparison is range-restricted.
4. Never use `audit_only.csv`, a `Buddy` field, or `decision`/`hired` as a predictor of scores. `proxy_*` columns (graduation, home city,
   skills tag) are proxy-risk fields: analyze them as things to check for bias, not as legitimate selection features.
5. Small samples: report n for every estimate, give uncertainty (bootstrap CI or permutation p-value), correct for multiple comparisons
   when scanning many features, and label results `robust` (survives 2+ methods and resampling), `suggestive`, or `weak`.
6. Small groups: any group with fewer than 5 candidates gets `"suppressed": true` and its numbers are replaced with null in the
   `shareable` copy of the output (see schema). Keep the full numbers in the `local` copy.
7. No network access and no external model calls in analysis code. Use pandas, numpy, scipy, scikit-learn, statsmodels.
8. Do not hardcode candidate counts, names, or paths. Do not read `data/synthetic/_truth.json` in analysis code; it is only for tests.
9. Never print or log free-text notes or resume text. Output only aggregates, top terms, and candidate_ids.
10. Deterministic: fixed random seeds.

## Output schema (one JSON file per section, written twice)

Write `results_dir/local/<section>.json` (full) and `results_dir/shareable/<section>.json` (rule 6 applied, no candidate_ids
in any chart or table).

```json
{
  "section": "funnel",
  "title": "Hiring funnel",
  "caveats": ["plain-language limits of this analysis"],
  "findings": [
    {"text": "plain-language finding", "strength": "robust|suggestive|weak", "evidence": "n=..., stat, CI/p"}
  ],
  "charts": [
    {"id": "unique-id", "type": "bar|hbar|scatter|heatmap|table|boxplot|line",
     "title": "...", "subtitle": "optional", "x_label": "...", "y_label": "...", "data": { }}
  ]
}
```

`data` by chart type:

- `bar` / `hbar` / `line`: `{"labels": [..], "series": [{"name": "..", "values": [..]}]}` (null allowed for suppressed).
- `scatter`: `{"points": [{"x": 0.1, "y": 0.2, "label": "candidateN or null", "group": "optional"}]}`.
- `heatmap`: `{"row_labels": [..], "col_labels": [..], "values": [[..]], "min": -1, "max": 1}`.
- `table`: `{"columns": [..], "rows": [[..]]}`.
- `boxplot`: `{"groups": [{"name": "..", "n": 12, "min": 0, "q1": 0, "median": 0, "q3": 0, "max": 0}]}`.

Sections and owners: `funnel`, `structure` (analysis/funnel_structure.py); `resume_themes`, `notes_themes`
(analysis/text_themes.py); `interviewers` (analysis/interviewers.py).
Each module also ships a pytest file in `hiring-analysis/tests/` that checks (a) the JSON validates against this schema and
(b) the module recovers the planted effects in `data/synthetic/_truth.json` (the test may read the truth file).
