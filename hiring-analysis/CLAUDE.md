# hiring-analysis

Shared context for the hiring data themes and trends project. A separate Cursor chat (local, on the user's Mac) owns the PII redactor; this chat owns the analysis and dashboard. Keep this file current so both chats describe the same pipeline.

## Pipeline

1. **Redact (other chat, local).** `pii-redactor` turns originals into `candidateN` files. Runs fully offline.
2. **Analyze and dashboard (this chat).** Reads only redacted `candidateN` files plus the outcome and score sheets.

## PII redactor (owned by the other chat)

- Lives at `~/Documents/GitHub/pii-redactor/` on the user's Mac. It is NOT in this repo yet (see "Bringing the code here").
- Python 3.13, spaCy (English plus multilingual NER), about 400k first and last name dictionary, bundled school, company and place lists.
- Replaces PII with tags: `[NAME]`, `[EMAIL]`, `[PHONE]`, `[LINKEDIN]`.
- Locations (cities, states, countries, street addresses) and schools are deliberately NOT redacted. Treat them as proxy-risk features in the analysis.
- Inputs: `.docx`, `.pptx`, `.pdf`, `.txt`, `.md`, `.xlsx` (all sheets). Old `.doc`, `.ppt`, `.xls` are skipped.
- Output naming: `candidateN.<ext>`, N is the lowest unused number in the output folder, shared across types. `.docx` for Word, PDF and text (rebuilt from text, so layout is simplified); `.pptx` and `.xlsx` keep their type.
- Input and output folders come from a git-ignored `.env` (`PII_REDACTOR_INPUT`, `PII_REDACTOR_OUT`, base folder in OneDrive CSAP). Do not hardcode paths.
- It writes no report or log of what was removed and keeps no link from `candidateN` back to the source file. Only an allowlist of phrases to never redact is stored.
- Known quirks: over-redacts single words (example: a sheet named `Data` is treated as a name and renamed); takes the capitalized word before or after a name; the same file run twice gets a new number.

## What this implies for the analysis

- Candidate and interviewer identity must be tied to outcomes before redaction by the user. Interviewers appear only as `[NAME]` in outputs, so interviewer labels (Interviewer 1, 2, ...) must come from the user's own mapping or sheet columns.
- `candidateN` numbering is not stable across reruns. Join on the number in filenames and sheets only if the user confirms the mapping is fixed.
- Because schools and locations remain, check them as proxies for protected traits and consider excluding them from resume theme features.
- Tag tokens like `[NAME]` should be stripped or ignored in text models so they don't become themes.

## Observed data layout (synthetic TEST_DATA copies from branch `cursor/candidate-tracker-ui-076c`)

- `FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx` (candidate-tracker sample) has one sheet (`TEMPLATE`); real workbooks have one sheet per assessment center day (AC day) named like `AMER Oct 15`; the loader reads every sheet and stores the sheet name as `ac_day` and its date as `ac_date`. The *cohort* is the hiring cycle (`AMER FY27Q3`) and comes from the workbook filename, or from the folder name when the redactor has renamed the file. Each sheet: header on row 9, one row per candidate (about 20 rows). Columns: Country, (Salutation was removed from the redactor test and synthetic workbooks; the loader still accepts it if present), Candidate Name, then three exercises, then totals and decision.
  - Interview, Role Play and Presentation each have 4 competencies scored 1-4 (max 16 per exercise), a per-exercise recommendation (Yes / Standby / No) and a comment. Total is out of 48.
  - Competency sets differ by exercise. "Executive Presence & Communication" appears in all three; "Coachability" in Role Play and Presentation.
  - Totals and Overall % are formulas. Final decision column is Hire / Standby / No Hire and is sometimes blank. A sheet header describes score bands at 85%, 70%, 65% and 50%, which the analysis will not use as cutoffs.
  - The repo copy of the test workbook has a `Buddy` column filled for Hire rows and for blank-Decision high scorers (never Standby or No Hire), which leaks the outcome. The user has since deleted it from their OneDrive copy, and the synthetic data omits it. If it reappears in real data, exclude it from any predictive step. Blanks in the test files are placeholders to be filled with test data. The user confirms real data will have no blank cells, so synthetic data has none. Still have the loader report any blank it finds (as a data-quality warning) rather than silently treating it as not-hired.
  - The test workbook has no interviewer or assessor column. Real data has manually redacted reviewer names; the test data will get sample reviewer names.
  - Comments are a short pick-list of phrases in the test data; real notes are free text and longer.
  - `Salutation` (Mr./Ms./Mx.) and `Country` are sensitive fields (gender and national-origin proxies). Never use as features; hold for post-hoc adverse-impact checks only.
- `ASE_Candidate_Screen_Review_TEST_DATA.xlsx` is the resume screening stage. The file itself has not been received (local OneDrive path only), but the real sheet's columns are known from the earlier "Ase candidate dashboard" chat and branch `cursor/ase-screen-preview-f19a`: Person ID, Full name, Graduation Date or Expected Graduation Date, Skills and Technologies (hand-typed tags such as Former Intern, certification, degree), Home cities, Recruiter, TI Date, Confirmed Yes/No, Score (Passing Score 21), Additional Comments, Pass/Fail, Notes (summary of the TI call, language level), Recommended to be Invited to Insight Day Yes/No, Status (Sent Assessment Center Instructions / ... and Candidate Confirmed Availability / Not interested in the role). TI is the technical interview before the assessment center; many rows are N/A for score because they never reached it. Recruiter is the screening-stage reviewer. Graduation date, home city and skills tags are proxy-risk fields (age, location, background).
- Confirmed by the user: the three exercises (Interview, Role Play, Presentation) together are the assessment center. Reviewer (interviewer/assessor) names were redacted manually; use sample names (Reviewer 1, 2, ...) when building synthetic test data. Outcomes are decided live and recorded manually (Decision column and the screening file). Written notes are free text and may be long, so text themes need real language analysis, not phrase counting.
- Resumes: one `.docx` per candidate, about one page (header with name, city, phone, email; summary; experience; education; certifications; skills). 11 resumes versus about 20 score rows, so some candidates have no resume.
- Join risk: the redactor turns every name into `[NAME]`, so the `Candidate Name` column and resume filenames stop being unique. IDs must be assigned to the score rows and resumes BEFORE redaction, and the redactor's `candidateN` numbering must not be assumed to match.

## Synthetic dataset

`synthetic/make_synthetic.py` writes a fake, redacted-style dataset (150 candidates, resumes, a screening sheet with the real 14 columns, and an assessment center workbook that mirrors the real TEMPLATE layout: header on row 9, an Example 1 row, no Buddy column, no blank cells) to the git-ignored `data/synthetic/`. It plants known effects (a lenient interviewer, a reviewer whose subjective language tracks resume path, exercise divergence, decision/score disagreement) and records them in `data/synthetic/_truth.json` so the pipeline can be checked against ground truth. The assessor columns and note length are assumptions to be replaced by the real layout. Notes are about 50 words; real notes will be longer.

## Analysis plan

See the plan in the chat (themes, trends, interviewer-level patterns, dashboard). Summary: rank-based comparisons (no fixed thresholds), within-instrument percentiles, funnel analysis including rejected candidates, bottom-up resume and notes themes, interviewer deviation from other signals, robustness checks, optional adverse-impact audit if an audit key exists. Outcomes (screened, interviewed, assessment center, hired) are past human decisions, not job performance.

## Privacy rules

- This repo is public. Never commit candidate files, scores, notes, outputs, the `.env`, or the redactor's `redacted files/` folder, even if redacted.
- All candidate data lives under `hiring-analysis/data/` (git-ignored) or outside the repo.
- Dashboard is local first; build it so an aggregate-only mode (with small-group suppression) can be hosted later.
- Do not use the public GitHub Pages skill for candidate-level data.

## Bringing the code here

The redactor code is only on the user's Mac. To move it into this repo, the user commits `pii-redactor/` (code, tests with fake data, docs, bundled lists) and pushes a branch. `.env`, `redacted files/` contents and any real files stay out. Once it is on a branch, merge or copy it under `pii-redactor/` here and update this file.

## Status

- Pipeline, four analysis modules and the dashboard are built and tested (62 tests) against the synthetic data. Run everything with `hiring-analysis/run_all.sh`.
- Dashboard: `data/<set>/processed/<target>/dashboard/dashboard_local.html` (target = "All cohorts" or a cohort) (candidate ids, keep local) and `dashboard_shareable.html` (aggregates only, groups under 5 suppressed, no ids, no external requests; the only hostable one).
- Not yet run on real data: copy `.env.example` to `.env` (this project's own settings file; `settings.py` reads it, with `${VAR}` and relative-path support; no paths are hardcoded and it shares nothing with the Webex tooling elsewhere in the repo), set `HIRING_BASE` / `HIRING_DATA_DIR` to a folder containing the two real workbooks and a `resumes/` folder, then run `run_all.sh`. Expect to adjust the loader to the real layout (role column, assessor and reviewer columns, screening N/A conventions).
- Dashboard UI: Cisco-branded (inline Cisco logo, Cisco blue palette), single-page app with hash routing and View Transitions. Horizontal tabs: Overview, How to read this, Legend and glossary, Ask the data. Vertical tabs: Funnel, Score structure, Resume themes, Notes themes, Interviewer trends, and Cohort trends (pooled view only). A Cohort switcher in the header links between cohort dashboards. Light and dark themes and four page transitions (Glide, Liquid reveal, Rise, None) under Appearance, saved in localStorage. Design previews live in `dashboard/ui-samples/`.
- Ask the data page: always works as a local search over the findings. With `HIRING_ASK_ENDPOINT` set (shareable build only) it sends the question plus aggregate findings to `ask-worker/` (Cloudflare Workers AI) and shows an AI answer with its source findings. Not yet deployed or run against live Workers AI. This is the one optional network call the dashboard can make.
- Redactor: working locally in the other chat, not yet in this repo.

## Redactor test files (multi-sheet)

`testdata/` holds un-redacted fictional inputs for testing the redactor: `FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx` with 6 AC day sheets (two weeks, three AC days each, `AMER Oct 5` ... `AMER Oct 16`) and `ASE_Candidate_Screen_Review_TEST_DATA.xlsx` with 1 sheet. Rebuild with `synthetic/make_multisheet_testdata.py --source <original scores workbook>`. Totals are formulas without cached values (openpyxl writes none); Excel recalculates on open, but run them through the redactor, not the loader, unless saved from Excel first. Synthetic data from `make_synthetic.py` is multi-sheet and multi-cohort too.

## Multiple cohorts (hiring cycles)

- Terms: **cohort** = hiring cycle such as `AMER FY27Q1` (name in the workbook filenames); **AC day** = one sheet of the scores workbook (`AMER Oct 15`).
- Input layout (`HIRING_DATA_DIR`): one folder per cohort holding that cohort's screening and scores workbooks, plus one shared `resumes/` folder. The user creates cohort folders by hand. The loader (`pipeline/loader.py`) recognises workbooks by content (Person ID header = screening, Candidate Name header = scores), takes the cohort from the filename first and the folder name second (the redactor renames files to `candidateN.xlsx`), and errors clearly if neither names a cohort.
- Identity: all resumes go through the redactor's single output folder, so `candidateN` is unique across cohorts. A person who applies in two cohorts gets a new number and counts as two people. A candidate id found in two cohorts stops the run with a message.
- Reviewers: the same label is the same person across cohorts. Optional `HIRING_DATA_DIR/interviewer_map.csv` (cohort, label, person; blank cohort = all) overrides it.
- AC day dates: sheet names carry no year, so the loader places each date inside the cohort's fiscal quarter (`HIRING_FISCAL_START_MONTH`, default 8). Interviewer drift uses these dates (falls back to candidate number when absent).
- Outputs (`HIRING_OUT_DIR`): `All cohorts/` (pooled; only when there are 2+ cohorts) and one folder per cohort with at least `HIRING_MIN_COHORT_AC` (default 30) AC attendees, each holding `processed/`, `results/`, `dashboard/`. Smaller cohorts still count in the pooled view. Pooled results also have the `cohorts` section (`analysis/cohorts.py`, shown as Cohort trends). Each dashboard has a cohort switcher that links to its siblings by relative path. `run_summary.json` lists what ran and what failed.
- Run: `pipeline/run_all.py` (or `run_all.sh`). Targets are analysed in parallel (spawned processes, single-threaded math). A failed cohort is skipped and reported; a failed pooled run stops everything.
- Adding a cohort: create `<out cohort name>` folder in the data dir, drop in the two workbooks, put its redacted resumes in the shared `resumes/`, rerun.
