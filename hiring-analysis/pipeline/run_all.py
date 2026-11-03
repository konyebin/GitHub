"""Run the whole pipeline: load every cohort, analyse "All cohorts" and each large-enough cohort, build the dashboards.

  python hiring-analysis/pipeline/run_all.py

Reads HIRING_DATA_DIR / HIRING_OUT_DIR (see settings.py). For each target ("All cohorts" and each analysed cohort) it writes
<out>/<target>/{processed,results,dashboard}. A cohort whose analysis fails is reported and left out; a failure in
"All cohorts" (or in the only cohort) stops the run. A summary is written to <out>/run_summary.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # the jobs already run in parallel; extra math threads only slow them down

import json
import sys
import time
import traceback
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "pipeline", "analysis", "dashboard"):
    sys.path.insert(0, str(ROOT / sub) if sub else str(ROOT))

import build_dashboard  # noqa: E402
import loader  # noqa: E402
from settings import ALL, load_settings  # noqa: E402

MODULES = ("funnel_structure", "text_themes", "interviewers")


def _job(module: str, processed: str, results: str) -> str | None:
    try:
        __import__(module).run(Path(processed), Path(results))
        return None
    except Exception:
        return traceback.format_exc(limit=6)


def main() -> dict:
    cfg = load_settings()
    out_dir = cfg["out_dir"]
    t0 = time.time()
    summary = loader.build(cfg["data_dir"], out_dir, cfg["fiscal_start_month"], cfg["min_cohort_ac"])
    targets = summary["targets"]
    multi = any(t["name"] == ALL for t in targets)
    print(f"loaded {len(summary['cohorts'])} cohort(s); analysing {[t['name'] for t in targets]}")

    errors: dict[str, str] = {}
    with ProcessPoolExecutor(max_workers=min(8, max(2, len(targets) * len(MODULES))), mp_context=multiprocessing.get_context("spawn")) as pool:
        jobs = {(t["name"], m): pool.submit(_job, m, str(Path(t["dir"]) / "processed"), str(Path(t["dir"]) / "results"))
                for t in targets for m in MODULES}
        for (name, module), fut in jobs.items():
            err = fut.result()
            if err:
                errors[f"{name}: {module}"] = err

    failed = {k.split(":")[0] for k in errors}
    must_work = ALL if multi else targets[0]["name"]
    if must_work in failed:
        for k, v in errors.items():
            if k.startswith(must_work):
                print(f"FAILED {k}\n{v}", file=sys.stderr)
        raise SystemExit(f"analysis of {must_work!r} failed; nothing was published")
    good = [t["name"] for t in targets if t["name"] not in failed]

    if multi:
        import cohorts
        pooled = out_dir / ALL
        cohorts.run(pooled / "processed", pooled / "results")

    for t in targets:
        if t["name"] not in good:
            continue
        for mode in ("local", "shareable"):
            nav = build_dashboard.cohort_nav(out_dir, t["name"], mode, good)
            build_dashboard.build(Path(t["dir"]) / "results", mode, Path(t["dir"]) / "dashboard" / f"dashboard_{mode}.html",
                                  cfg["ask_endpoint"], nav)
    result = {"targets": good, "failed": errors, "cohorts": summary["cohorts"], "warnings": summary["warnings"],
              "seconds": round(time.time() - t0)}
    (out_dir / "run_summary.json").write_text(json.dumps(result, indent=2))
    for k, v in errors.items():
        print(f"SKIPPED {k}\n{v}", file=sys.stderr)
    print(f"done in {result['seconds']}s: {good}")
    return result


if __name__ == "__main__":
    main()
