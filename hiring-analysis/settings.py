"""Single place where this project reads its folder settings.

Order of precedence: real environment variables, then hiring-analysis/.env, then defaults.
`.env` supports ${VAR} references. Relative paths are resolved against hiring-analysis/.

  HIRING_BASE       optional base folder, so other paths can be written as ${HIRING_BASE}/...
  HIRING_DATA_DIR   parent folder: one folder per cohort (for example "AMER FY27Q1") holding that cohort's screening and
                    scores workbooks, plus a shared resumes/ folder (default: data/synthetic)
  HIRING_OUT_DIR    where outputs go, one folder per cohort plus "All cohorts", each with processed/, results/ and
                    dashboard/ (default: <DATA_DIR>/processed)
  HIRING_FISCAL_START_MONTH  month the fiscal year starts, 1-12 (default 8). Used to put a year on AC day sheet names
  HIRING_MIN_COHORT_AC       smallest number of AC attendees for a cohort to get its own analysis (default 30)
  HIRING_ASK_ENDPOINT  optional URL of the ask-worker. Only the shareable dashboard uses it; empty means search-only Ask the data
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip("'\"")
    return values


def _expand(value: str, lookup: dict[str, str]) -> str:
    return _REF.sub(lambda m: lookup.get(m.group(1), os.environ.get(m.group(1), "")), value)


def _path(value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (ROOT / p).resolve()


def load_settings() -> dict:
    file_vals = _read_env_file(ROOT / ".env")
    merged = {**file_vals, **{k: v for k, v in os.environ.items() if k.startswith("HIRING_")}}
    merged = {k: _expand(v, merged) for k, v in merged.items()}
    data_dir = _path(merged["HIRING_DATA_DIR"]) if merged.get("HIRING_DATA_DIR") else ROOT / "data" / "synthetic"
    out_dir = _path(merged["HIRING_OUT_DIR"]) if merged.get("HIRING_OUT_DIR") else data_dir / "processed"
    return {"data_dir": data_dir, "out_dir": out_dir, "ask_endpoint": merged.get("HIRING_ASK_ENDPOINT") or None,
            "fiscal_start_month": int(merged.get("HIRING_FISCAL_START_MONTH") or 8),
            "min_cohort_ac": int(merged.get("HIRING_MIN_COHORT_AC") or 30)}


ALL = "All cohorts"


def targets(out_dir: Path) -> list[str]:
    """Output folders written by the pipeline: every cohort that has results plus "All cohorts"."""
    return sorted((p.name for p in out_dir.iterdir() if (p / "processed").is_dir()), key=lambda n: (n != ALL, n)) if out_dir.exists() else []


def resolve_target(out_dir: Path, name: str | None = None) -> Path:
    """Folder for one target. Without a name: "All cohorts" if present, otherwise the only cohort."""
    if name:
        return out_dir / name
    found = targets(out_dir)
    if not found:
        raise SystemExit(f"nothing found in {out_dir}; run pipeline/run_all.py first")
    return out_dir / found[0]
