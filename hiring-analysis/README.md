# hiring-analysis

Themes and trends across redacted resumes, interview scores and notes, and assessment center scores and notes, with interviewer-level patterns, delivered as a local dashboard. Candidate data never goes in git.

See [CLAUDE.md](./CLAUDE.md) for the pipeline, the PII redactor contract and privacy rules.

## Run

```bash
pip install pandas numpy scipy scikit-learn statsmodels openpyxl python-docx pytest
python3 synthetic/make_synthetic.py   # fake data, once (3 cohorts)
./run_all.sh                          # loader, analyses, dashboards for every cohort and "All cohorts"
python3 -m pytest tests -q
```

Open `data/synthetic/processed/All cohorts/dashboard/dashboard_local.html` in a browser (each cohort has its own folder next to it, and the Cohort switcher in the header moves between them). Use `dashboard_shareable.html` for anything that leaves your machine.

### Data layout for several cohorts

```
HIRING_DATA_DIR/
  resumes/                 all redacted resumes, every cohort (the redactor's single output folder)
  AMER FY27Q1/             create by hand: this cohort's screening + scores workbooks
  AMER FY28Q1/
  interviewer_map.csv      optional: cohort,label,person to link reviewer labels that differ
```

A cohort is a hiring cycle; its name comes from the workbook filename (`FY27Q1_AMER_ASE_Scores...`) or, if the redactor renamed the file, from the folder. Each sheet of the scores workbook is one AC day (`AMER Oct 15`). To add a cohort, create its folder, drop in the two workbooks, add its resumes to `resumes/` and rerun `./run_all.sh`.
