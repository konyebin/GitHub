# ASE Candidate Tracker

A local, dark-theme (Cisco blue) Streamlit app for tracking hire / standby / no-hire decisions from the
`FY27Q3_AMER_ASE_Scores - 1sheet.xlsx` workbook, assigning employee numbers to hires, and saving everything
back to a colour-coded Excel file.

## Run on a Mac

```bash
cd candidate-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Upload the scores workbook in the sidebar. Candidates start **Unassigned**.

## Tabs

| Tab | What it does |
|-----|--------------|
| All Candidates | Every candidate in one table. Rows are green (Hire), yellow (Standby), red (No Hire). Change status, re-evaluation date and notes inline. |
| Board | One column per status (plus Unassigned). Move a candidate with the buttons on their card. |
| Employee Numbers | Hires only. Type or paste an employee number. Duplicates are flagged. Numbers are kept if a candidate leaves Hire. |
| Insights & Log | Decision split, score distribution, section averages, standby re-evaluation queue, and the audit log. |

## Saving

* **Save to Excel** writes `<uploaded name>_tracked.xlsx` into the same folder as `app.py`.
* **Download .xlsx** gives the same file through the browser.
* The workbook has the sheets All Candidates, By Status, Employee Numbers, Audit Log and Summary, with the same
  green / yellow / red scheme as the UI.
* Every change is also autosaved to `tracker_state.json` next to `app.py`, so a browser refresh or re-upload keeps
  your decisions (matched by candidate name).

## Scoring

Scores are recomputed from the competency columns (4 items per section, max 4 each): Interview, Role Play and
Presentation are each out of 16, total out of 48. The suggested status uses sidebar thresholds, defaulting to
85% for Hire and 70% for Standby (from the legend in the source sheet). Suggestions are advisory only.
Rows named `Example ...` are hidden unless you switch them on.

## Privacy

Candidate data stays on your machine. `tracker_state.json` and `*_tracked.xlsx` are git-ignored.
`samples/demo_candidates.xlsx` contains fictional names only (`python tests/make_demo.py` regenerates it).

## Tests

```bash
pip install pytest && python -m pytest tests -q
```
