"""Tests for install base → Check Back mapping."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.install_base_mapper import (  # noqa: E402
    _first_number,
    _format_license,
    map_row,
)

MINIMAL_CONFIG = {
    "install_base_to_checkback": {
        "Account Name": "Opportunity Name",
        "Partner Name": "Partner",
        "Risk2_0_current": " (G/Y/R)",
        "Webex Calling MT Provisioned Seats": "Providioned Lic Calling",
        "Cloud Calling Billed Seats": "Entitled Lic Calling",
    },
    "risk_to_gyr": {"Low": "G", "High": "R", "Medium": "Y"},
    "review_flags": {},
    "check_back_columns": [],
}


def test_map_row_basic():
    ib = {
        "Account Name": "Test Corp",
        "Collab AOV": 50000,
        "Partner Name": "Partner X",
        "Subscription Ref Id": "Sub123",
        "CSM_NAME": "Jane Doe",
        "Risk2_0_current": "Low",
        "Webex Calling MT Provisioned Seats": 100,
        "Webex Calling DI Provisioned Seats": 50,
    }
    row, gaps = map_row(ib)
    assert row["Opportunity Name"] == "Test Corp"
    assert row["Partner"] == "Partner X"
    assert row[" (G/Y/R)"] == "G"


def test_risk_high_maps_red():
    ib = {"Account Name": "A", "Risk2_0_current": "High"}
    row, _ = map_row(ib)
    assert row[" (G/Y/R)"] == "R"


def test_first_number():
    assert _first_number(None) == 0.0
    assert _first_number("") == 0.0
    assert _first_number(50000) == 50000.0
    assert _first_number("1,234") == 1234.0
    assert _first_number("$50,000") == 50000.0
    assert _first_number("100 seats") == 100.0
    assert _first_number("abc") == 0.0


def test_format_license():
    assert _format_license(100, None) == "MT: 100"
    assert _format_license(None, 50) == "DI: 50"
    assert _format_license(100, 50) == "MT: 100 DI: 50"
    assert _format_license(None, None) == ""
    assert _format_license("$100", "50.9") == "MT: 100 DI: 50"


def test_map_row_license_mt_di():
    ib = {
        "Webex Calling MT Provisioned Seats": 100,
        "Webex Calling DI Provisioned Seats": 50,
    }
    row, _ = map_row(ib, MINIMAL_CONFIG)
    assert row["Providioned Lic Calling"] == "MT: 100 DI: 50"


def test_map_row_entitled_from_billed_seats():
    ib = {"Cloud Calling Billed Seats": 25}
    row, _ = map_row(ib, MINIMAL_CONFIG)
    assert row["Entitled Lic Calling"] == "25 workspace"


def test_map_row_entitled_fallback_total_billed():
    ib = {"Cloud Calling Billed Seats": "", "Total Billed Seats": 30}
    row, _ = map_row(ib, MINIMAL_CONFIG)
    assert row["Entitled Lic Calling"] == "30 workspace"


def test_map_row_risk_medium():
    ib = {"Risk2_0_current": "Medium"}
    row, _ = map_row(ib, MINIMAL_CONFIG)
    assert row[" (G/Y/R)"] == "Y"


def test_map_row_review_flag_gap():
    config = {
        **MINIMAL_CONFIG,
        "review_flags": {"Webex Calling MT Provisioned Seats": "verify"},
    }
    ib = {"Webex Calling MT Provisioned Seats": 100}
    _, gaps = map_row(ib, config)
    assert any(
        g["field"] == "Providioned Lic Calling" and g["confidence"] == "medium"
        for g in gaps
    )


def test_map_row_unmapped_column_gap():
    config = {
        **MINIMAL_CONFIG,
        "check_back_columns": ["Opportunity Name", "SL2"],
    }
    ib = {"Account Name": "A"}
    _, gaps = map_row(ib, config)
    assert any(g["field"] == "SL2" and g["confidence"] == "low" for g in gaps)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all passed")
