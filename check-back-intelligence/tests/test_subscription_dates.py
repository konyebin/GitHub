"""Tests for subscription date derivation."""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.workbook.subscription_dates import (  # noqa: E402
    _add_months,
    _format_date,
    _parse_single_date,
    derive_subscription_dates,
)


def test_format_date():
    assert _format_date(None) == ""
    assert _format_date("") == ""
    assert _format_date(datetime(2025, 5, 22)) == "05/22/2025"
    assert _format_date("  22-May-2025  ") == "22-May-2025"


def test_parse_single_date():
    assert _parse_single_date("05/22/2025") == datetime(2025, 5, 22)
    assert _parse_single_date("22-May-2025") == datetime(2025, 5, 22)
    assert _parse_single_date("not-a-date") is None


def test_add_months():
    assert _add_months(datetime(2025, 5, 22), 60) == datetime(2030, 5, 22)
    assert _add_months(datetime(2025, 1, 31), 1) == datetime(2025, 2, 28)


def test_derive_subscription_dates_datetime():
    result = derive_subscription_dates(datetime(2025, 5, 22), 60)
    assert result == "05/22/2025 to 05/22/2030"

    assert derive_subscription_dates(datetime(2025, 5, 22), None) == "05/22/2025"


def test_derive_subscription_dates_existing_passthrough():
    existing = "28-Apr-2025 to 27-Apr-2030"
    result = derive_subscription_dates(
        datetime(2025, 5, 22), 60, existing_sub_dates=existing
    )
    assert result == existing


def test_derive_subscription_dates_string_start():
    result = derive_subscription_dates("05/22/2025", 60)
    assert result == "05/22/2025 to 05/22/2030"


def test_derive_subscription_dates_range_preserved():
    text = "28-Apr-2025 to 27-Apr-2030"
    assert derive_subscription_dates(text, 60) == text


def test_derive_subscription_dates_empty():
    assert derive_subscription_dates(None, 60) == ""
    assert derive_subscription_dates("", 60) == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all passed")
