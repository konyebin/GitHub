"""Tests for Check Back note field parsing."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.workbook.note_parser import (  # noqa: E402
    apply_prof_ws_shorthand_from_cells,
    compute_active_pct,
    parse_notes_and_cells,
    parse_notes_to_structured,
    parse_prof_ws_shorthand,
)


def test_parse_prof_ws_shorthand():
    assert parse_prof_ws_shorthand("1,265 workspace 335") == {
        "professional": "1265",
        "workspace": "335",
    }
    assert parse_prof_ws_shorthand("") is None
    assert parse_prof_ws_shorthand("no match") is None


def test_apply_prof_ws_shorthand_from_cells():
    out: dict = {}
    apply_prof_ws_shorthand_from_cells(
        {"Entitled Lic Calling": "1,700 workspace 708"}, out
    )
    assert out["Lic Professional (used/entitled)"] == "1700"
    assert out["Lic Workspace (used/entitled)"] == "708"

    out2 = {"Lic Professional (used/entitled)": "999/1000"}
    apply_prof_ws_shorthand_from_cells(
        {"Entitled Lic Calling": "1,700 workspace 708"}, out2
    )
    assert out2["Lic Professional (used/entitled)"] == "999/1000"
    assert out2["Lic Workspace (used/entitled)"] == "708"

    out3 = {
        "Lic Professional (used/entitled)": "999/1000",
        "Lic Workspace (used/entitled)": "1/2",
    }
    apply_prof_ws_shorthand_from_cells(
        {"Providioned Lic Calling": "1,265 workspace 335"}, out3
    )
    assert out3["Lic Professional (used/entitled)"] == "1265"
    assert out3["Lic Workspace (used/entitled)"] == "335"


def test_parse_notes_license_pairs():
    out = parse_notes_to_structured(
        "professional calling assigned 850 / 1,200", "", ""
    )
    assert out["Lic Professional (used/entitled)"] == "850/1,200"


def test_parse_notes_feature_counts():
    out = parse_notes_to_structured(
        "",
        "auto attendant: 152; hunt groups: 3; basic call queues: 10; virtual lines: 5",
        "",
    )
    assert out["Auto Attendant count"] == "152"
    assert out["Hunt Groups count"] == "3"
    assert out["Call Queues count"] == "10"
    assert out["Virtual Lines count"] == "5"


def test_parse_notes_call_metrics():
    out = parse_notes_to_structured(
        "1.1M calls in last 90 days; 89.6% answered; busiest hour 12.5K calls",
        "",
        "",
    )
    assert out["Total calls"] == "1.1M"
    assert out["Answered calls %"] == "89.6%"
    assert out["Calls busiest hour"] == "12.5K"


def test_parse_notes_connected_uc():
    out = parse_notes_to_structured("", "customer uses Connected-UC", "")
    assert out["Connected-UC (Y/N)"] == "Y"


def test_parse_notes_empty():
    assert parse_notes_to_structured("", "", "") == {}


def test_compute_active_pct():
    assert compute_active_pct(100, 65) == "65%"
    assert compute_active_pct("1,000", "750") == "75%"
    assert compute_active_pct("1,265 workspace 335", 500) == ""
    assert compute_active_pct(100, 106) == ""
    assert compute_active_pct(0, 50) == ""


def test_parse_notes_and_cells_integration():
    out = parse_notes_and_cells(
        "professional 100/200",
        "",
        "",
        row={"Providioned Lic Calling": "1,265 workspace 335"},
    )
    assert out["Lic Professional (used/entitled)"] == "1265"
    assert out["Lic Workspace (used/entitled)"] == "335"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all passed")
