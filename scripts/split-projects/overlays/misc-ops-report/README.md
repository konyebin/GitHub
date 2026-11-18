# Misc ops report demo

Three sample Webex Calling ops-report dashboards (healthy campus, contact-center pressure, global expansion) built from sanitized Control Hub-style CSVs. Sample data only.

Live: https://konyebin.github.io/misc-ops-report/

## Regenerate

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash prepare-github-pages.sh        # rewrites index.html and reports/
```

`generate_demo_reports.py` reads `data/<scenario>/*.csv` and writes `reports/<scenario>.html` plus the hub `index.html`. `create-demo-ops-report.py` sanitizes a real ops report into a demo using `ops-report-source.html`.

Real reports come from the separate `wxops` project; this repo has no runtime dependency on it.
