#!/usr/bin/env bash
# Rebuild everything: load every cohort, run the analysis modules for "All cohorts" and each cohort, build the dashboards.
# Usage: hiring-analysis/run_all.sh   (reads HIRING_DATA_DIR from hiring-analysis/.env; defaults to synthetic data)
set -euo pipefail
cd "$(dirname "$0")"
python3 pipeline/run_all.py
