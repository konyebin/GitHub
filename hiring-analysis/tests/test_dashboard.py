import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
sys.path.insert(0, str(ROOT / "pipeline"))
import build_dashboard  # noqa: E402

RESULTS = ROOT / "data" / "synthetic" / "processed" / "results"


def test_builds_both_modes_without_network_references(tmp_path):
    for mode in ("local", "shareable"):
        out = build_dashboard.build(RESULTS, mode, tmp_path / f"{mode}.html")
        html = out.read_text()
        assert "__PAYLOAD__" not in html
        assert not re.search(r"(src|href)=[\"']https?://", html), "dashboard must not load external resources"
        payload = re.search(r'id="payload" type="application/json">(.*?)</script>', html, re.S).group(1)
        data = json.loads(payload.replace("<\\/", "</"))
        assert data["mode"] == mode and data["sections"]


def test_shareable_has_no_candidate_ids(tmp_path):
    out = build_dashboard.build(RESULTS, "shareable", tmp_path / "s.html")
    assert not re.search(r"candidate\d+", out.read_text()), "candidate ids leaked into the shareable dashboard"
