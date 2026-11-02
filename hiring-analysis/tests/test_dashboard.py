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


def test_every_chart_has_a_description():
    template = (ROOT / "dashboard" / "template.html").read_text()
    described = set(re.findall(r"^'([^']+)':", template, re.M))
    missing = []
    for mode in ("local", "shareable"):
        for f in (RESULTS / mode).glob("*.json"):
            for c in json.loads(f.read_text()).get("charts", []):
                if c["id"] not in described and not c["id"].startswith("signal-scatter-"):
                    missing.append(c["id"])
    assert not missing, f"charts without a description: {missing}"


def test_every_chart_has_a_plain_title_and_findings_have_plain_text():
    template = (ROOT / "dashboard" / "template.html").read_text()
    block = template[template.index("const CHART_TITLE={"):template.index("function chartTitle")]
    titled = set(re.findall(r"^'([^']+)':", block, re.M))
    sys.path.insert(0, str(ROOT / "tests"))
    import plain_check
    for mode in ("local", "shareable"):
        for f in (RESULTS / mode).glob("*.json"):
            d = json.loads(f.read_text())
            for c in d["charts"]:
                assert c["id"] in titled or c["id"].startswith("signal-scatter-"), c["id"]
            for x in d["findings"]:
                assert x.get("plain") and not plain_check.problems(x["plain"]), (f.name, x.get("plain"))


def test_ask_endpoint_only_in_shareable(tmp_path):
    url = "https://ask.example/api"
    s = build_dashboard.build(RESULTS, "shareable", tmp_path / "s.html", url).read_text()
    loc = build_dashboard.build(RESULTS, "local", tmp_path / "l.html", url).read_text()
    assert url in s and url not in loc, "AI endpoint must be embedded in shareable mode only"
    plain = build_dashboard.build(RESULTS, "shareable", tmp_path / "p.html").read_text()
    payload = re.search(r'id="payload" type="application/json">(.*?)</script>', plain, re.S).group(1)
    assert "ask_endpoint" not in payload


def test_published_demo_is_shareable_only():
    published = ROOT.parent / "docs" / "public" / "demos" / "hiring-analysis"
    if not published.exists():
        return
    for page in published.glob("*.html"):
        assert page.name != "full.html", "local build must not be published"
        html = page.read_text()
        assert not re.search(r"candidate\d+", html), f"{page.name} contains candidate ids"
        payload = re.search(r'id="payload" type="application/json">(.*?)</script>', html, re.S)
        if payload:
            assert json.loads(payload.group(1).replace("<\\/", "</"))["mode"] == "shareable", f"{page.name} is not a shareable build"
