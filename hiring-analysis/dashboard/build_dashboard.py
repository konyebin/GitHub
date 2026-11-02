"""Build a single self-contained dashboard HTML from the analysis results.

  python hiring-analysis/dashboard/build_dashboard.py [--mode local|shareable] [--results DIR] [--out FILE]

Folders come from hiring-analysis/settings.py (reads .env). `local` embeds results/local (candidate ids
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

SECTIONS = ["funnel", "structure", "resume_themes", "notes_themes", "interviewers"]


def build(results_dir: Path, mode: str, out: Path, ask_endpoint: str | None = None) -> Path:
    folder = results_dir / mode
    sections = {}
    for name in SECTIONS:
        p = folder / f"{name}.json"
        if p.exists():
            sections[name] = json.loads(p.read_text())
    if not sections:
        raise SystemExit(f"no result files in {folder}; run the analysis modules first")
    payload = {"mode": mode, "built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "sections": sections}
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
    ap.add_argument("--results", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ask-endpoint", help="URL of the ask-worker; shareable mode only")
    a = ap.parse_args()
    cfg = load_settings()
    out_dir = cfg["out_dir"]
    results = a.results or out_dir / "results"
    out = a.out or out_dir / "dashboard" / f"dashboard_{a.mode}.html"
    print(build(results, a.mode, out, a.ask_endpoint or cfg["ask_endpoint"]))
