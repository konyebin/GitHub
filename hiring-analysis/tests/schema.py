"""Shared validator for analysis output JSON (see analysis/CONTRACT.md)."""
import json
from pathlib import Path

CHART_TYPES = {"bar", "hbar", "scatter", "heatmap", "table", "boxplot", "line"}
STRENGTH = {"robust", "suggestive", "weak"}


def validate(path: Path, shareable: bool = False) -> dict:
    d = json.loads(Path(path).read_text())
    assert {"section", "title", "caveats", "findings", "charts"} <= set(d), "missing top-level keys"
    for f in d["findings"]:
        assert {"text", "strength", "evidence"} <= set(f) and f["strength"] in STRENGTH
    ids = set()
    for c in d["charts"]:
        assert c["type"] in CHART_TYPES and c["id"] not in ids and "data" in c and "title" in c
        ids.add(c["id"])
        t, data = c["type"], c["data"]
        if t in ("bar", "hbar", "line"):
            assert "labels" in data and all(len(s["values"]) == len(data["labels"]) for s in data["series"])
        elif t == "scatter":
            assert "points" in data
            if shareable:
                assert all(p.get("label") in (None, "") for p in data["points"]), "candidate ids in shareable output"
        elif t == "heatmap":
            assert len(data["values"]) == len(data["row_labels"])
        elif t == "table":
            assert all(len(r) == len(data["columns"]) for r in data["rows"])
        elif t == "boxplot":
            assert "groups" in data
    return d
