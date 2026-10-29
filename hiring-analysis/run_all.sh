#!/usr/bin/env bash
# Rebuild everything: load data, run the three analysis modules, build both dashboards.
# Usage: hiring-analysis/run_all.sh   (reads HIRING_DATA_DIR from hiring-analysis/.env; defaults to synthetic data)
set -euo pipefail
cd "$(dirname "$0")"
python3 pipeline/loader.py
python3 analysis/funnel_structure.py &
python3 analysis/text_themes.py &
python3 analysis/interviewers.py &
wait
python3 dashboard/build_dashboard.py --mode local
python3 dashboard/build_dashboard.py --mode shareable
