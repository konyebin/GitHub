# Misc Ops Report

<ClientOnly>
  <DemoPanel slug="misc-ops-report" />
</ClientOnly>

## What it is

**Webex Calling Miscellaneous Operations Report** — a 9-section health-check dashboard built from Control Hub CSV exports. Three sample enterprises illustrate different operational profiles; hover the **i** icons on scorecards, sections, and table columns for metric definitions and sources.

## Live dashboard (GitHub Pages)

**[Open report hub — 3 scenarios](https://konyebin.github.io/GitHub/demos/misc-ops-report/index.html)**

| Scenario | Best for showing |
|----------|------------------|
| [Healthy Campus](https://konyebin.github.io/GitHub/demos/misc-ops-report/reports/healthy-campus.html) | Green scorecard, high volume |
| [Contact Center Under Pressure](https://konyebin.github.io/GitHub/demos/misc-ops-report/reports/contact-center-pressure.html) | Queue abandonment, staffing gaps |
| [Global Expansion](https://konyebin.github.io/GitHub/demos/misc-ops-report/reports/global-expansion.html) | International routing, recording signals |

Full methodology and downloadable source files are linked from each report footer.

## How to regenerate

```bash
bash ~/Documents/GitHub/docs/public/demos/misc-ops-report/prepare-github-pages.sh
git add docs/public/demos/misc-ops-report/
git push origin main
```

## Source code

Generator: `docs/public/demos/misc-ops-report/generate_demo_reports.py`  
Production pipeline: `wxops/report_bot/` (fetch CSVs → `generate_misc_report.py` → Webex bot delivery)
