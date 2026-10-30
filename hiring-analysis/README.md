# hiring-analysis

Themes and trends across redacted resumes, interview scores and notes, and assessment center scores and notes, with interviewer-level patterns, delivered as a local dashboard. Candidate data never goes in git.

See [CLAUDE.md](./CLAUDE.md) for the pipeline, the PII redactor contract and privacy rules.

## Run

```bash
pip install pandas numpy scipy scikit-learn statsmodels openpyxl python-docx pytest
python3 synthetic/make_synthetic.py   # fake data, once
./run_all.sh                          # loader, analyses, dashboards
python3 -m pytest tests -q
```

Open `data/synthetic/processed/dashboard/dashboard_local.html` in a browser. Use `dashboard_shareable.html` for anything that leaves your machine.
