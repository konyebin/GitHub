"""Build a single self-contained dashboard HTML from the analysis results.

  python hiring-analysis/dashboard/build_dashboard.py [--mode local|shareable] [--target "All cohorts"] [--results DIR] [--out FILE]

Folders come from hiring-analysis/settings.py (reads .env). One dashboard is built per target ("All cohorts" and each
analysed cohort); a cohort switcher in the header links between them using relative paths. `local` embeds results/local (candidate ids
included; keep on this machine). `shareable` embeds results/shareable (aggregates only, small groups suppressed, no ids)
and is the only mode that is safe to host. The HTML loads nothing external: all data and code are inlined. The one
optional exception is the Ask the data page, which only contacts an AI endpoint if --ask-endpoint (or HIRING_ASK_ENDPOINT)
is set, and only in shareable mode. Without it, Ask the data is a local search over the findings.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

SECTIONS = ["cohorts", "funnel", "structure", "resume_themes", "notes_themes", "interviewers"]


def cohort_nav(out_dir: Path, current: str, mode: str, names: list[str]) -> dict | None:
    """Header switcher: links to the sibling target dashboards (paths relative to this dashboard file)."""
    from urllib.parse import quote
    if len(names) < 2:
        return None
    return {"current": current, "options": [
        {"name": n, "href": f"../../{quote(n)}/dashboard/dashboard_{mode}.html"} for n in names]}


def build(results_dir: Path, mode: str, out: Path, ask_endpoint: str | None = None, nav: dict | None = None) -> Path:
    folder = results_dir / mode
    sections = {}
    for name in SECTIONS:
        p = folder / f"{name}.json"
        if p.exists():
            sections[name] = json.loads(p.read_text())
    if not sections:
        raise SystemExit(f"no result files in {folder}; run the analysis modules first")
    payload = {"mode": mode, "built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "sections": sections}
    if nav:
        payload["cohorts"] = nav
    if ask_endpoint and mode == "shareable":
        payload["ask_endpoint"] = ask_endpoint
    data = json.dumps(payload).replace("</", "<\\/")
    html = (HERE / "template.html").read_text().replace("__PAYLOAD__", data)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    from settings import load_settings

    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "shareable"], default="local")
    ap.add_argument("--target", help='folder name under HIRING_OUT_DIR, e.g. "All cohorts" or "AMER FY27Q1"')
    ap.add_argument("--results", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ask-endpoint", help="URL of the ask-worker; shareable mode only")
    a = ap.parse_args()
    cfg = load_settings()
    from settings import resolve_target, targets

    target = resolve_target(cfg["out_dir"], a.target)
    results = a.results or target / "results"
    out = a.out or target / "dashboard" / f"dashboard_{a.mode}.html"
    names = [n for n in targets(cfg["out_dir"]) if (cfg["out_dir"] / n / "results").is_dir()]
    nav = cohort_nav(cfg["out_dir"], target.name, a.mode, names)
    print(build(results, a.mode, out, a.ask_endpoint or cfg["ask_endpoint"], nav))
