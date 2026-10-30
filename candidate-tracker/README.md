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

On the first screen the app lists the `.xlsx` files in your OneDrive folder
(`~/Library/CloudStorage/OneDrive-Cisco/CSAP LEarning` by default, newest first). Click **Open** on the one you want.
You can type a different folder in the box (it is remembered), set `TRACKER_DATA_DIR`, or upload a file from the sidebar.
Use **Choose another workbook** in the sidebar to switch. Candidates without a status in the workbook start **Unassigned**.

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

## Scoring, score bands and review flags

Scores are recomputed from the competency columns (4 items per section, max 4 each): Interview, Role Play and
Presentation are each out of 16, total out of 48.

Every candidate gets a **score band** from the overall percentage (sliders in the sidebar):

* Hire: 85% and up
* Maybe: 70% to just under 85% (maps to Standby for "Apply suggestions")
* No Hire: below 70%

A decision that disagrees with its band is flagged **Needs review**:

| Decision | Score band | Flag |
|----------|------------|------|
| Hire | No Hire range | High |
| Hire | Maybe range | Review |
| No Hire | Hire range | High |
| No Hire | Maybe range | Review |
| Standby | Hire or No Hire range | Review |
| Hire or No Hire | Incomplete scores | Review |

Flags show in the All Candidates table, on Board cards (orange outline), in the banner above the tabs, in the
Insights tab (including a score-vs-decision chart), and on the "Needs Review" sheet of the saved workbook. Adding a
note to the candidate marks the flag as "(note added)". Rows named `Example ...` are hidden unless you switch them on.

## Privacy

Candidate data stays on your machine. `tracker_state.json` and `*_tracked.xlsx` are git-ignored.
`samples/FY27Q3_AMER_ASE_Scores_TEST_DATA.xlsx` contains fictional names only (`python tests/make_demo.py` regenerates it).

## Test resumes

`samples/resumes/` holds 10 fictional resumes (.docx) for candidates in the test workbook, with strength loosely following
their scores. Regenerate with `pip install python-docx && python tests/make_resumes.py`.

## Tests

```bash
pip install pytest && python -m pytest tests -q
```
