"""Single place where this project reads its folder settings.

Order of precedence: real environment variables, then hiring-analysis/.env, then defaults.
`.env` supports ${VAR} references. Relative paths are resolved against hiring-analysis/.

  HIRING_BASE       optional base folder, so other paths can be written as ${HIRING_BASE}/...
  HIRING_DATA_DIR   folder holding the two workbooks and resumes/ (default: data/synthetic)
  HIRING_OUT_DIR    where processed CSVs, results and dashboards go (default: <DATA_DIR>/processed)
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


def load_settings() -> dict[str, Path]:
    file_vals = _read_env_file(ROOT / ".env")
    merged = {**file_vals, **{k: v for k, v in os.environ.items() if k.startswith("HIRING_")}}
    merged = {k: _expand(v, merged) for k, v in merged.items()}
    data_dir = _path(merged["HIRING_DATA_DIR"]) if merged.get("HIRING_DATA_DIR") else ROOT / "data" / "synthetic"
    out_dir = _path(merged["HIRING_OUT_DIR"]) if merged.get("HIRING_OUT_DIR") else data_dir / "processed"
    return {"data_dir": data_dir, "out_dir": out_dir}
