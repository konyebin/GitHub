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

- `FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx`, one sheet (`TEMPLATE`), header on row 9, one row per candidate (about 20 rows). Columns: Country, Salutation, Candidate Name, then three exercises, then totals and decision.
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

`synthetic/make_synthetic.py` writes a fake, redacted-style dataset (60 candidates, resumes, a screening sheet with the real 14 columns, and an assessment center workbook that mirrors the real TEMPLATE layout: header on row 9, an Example 1 row, no Buddy column, no blank cells) to the git-ignored `data/synthetic/`. It plants known effects (a lenient interviewer, a reviewer whose subjective language tracks resume path, exercise divergence, decision/score disagreement) and records them in `data/synthetic/_truth.json` so the pipeline can be checked against ground truth. The assessor columns and note length are assumptions to be replaced by the real layout. Notes are about 50 words; real notes will be longer.

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

- Analysis: waiting on sample redacted files (resume, interview, assessment center, outcome sheet) and rubric/scale examples.
- Redactor: working locally in the other chat, not yet in this repo.
