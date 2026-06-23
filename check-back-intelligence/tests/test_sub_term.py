"""Sub Term parsing from subscription date ranges."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.workbook.sub_term import format_sub_term, sub_term_from_text  # noqa: E402


def test_comma_separated_range():
    text = "9/8/2025, 12/15/2028"
    as_of = date(2026, 6, 22)
    label, red = sub_term_from_text(text, as_of)
    assert not red
    assert "3yr" in label
    assert "Year 1 of 3" in label
    assert "2026-06-22" in label


def test_dash_range_no_spaces():
    text = "9/8/2025-12/15/2028"
    as_of = date(2026, 6, 22)
    label, red = sub_term_from_text(text, as_of)
    assert not red
    assert "Year 1 of 3" in label


def test_to_separator():
    start = date(2025, 9, 8)
    end = date(2028, 12, 15)
    label, red = sub_term_from_text(f"{start:%m/%d/%Y} to {end:%m/%d/%Y}", date(2026, 6, 22))
    assert not red
    assert label == format_sub_term(start, end, date(2026, 6, 22))


def test_idempotent_when_already_formatted():
    existing = "3yr | Year 1 of 3 (as of 2026-06-22)"
    label, red = sub_term_from_text(existing, date(2026, 6, 22))
    assert label == existing
    assert not red


if __name__ == "__main__":
    test_comma_separated_range()
    test_dash_range_no_spaces()
    test_to_separator()
    test_idempotent_when_already_formatted()
    print("test_sub_term.py: all passed")
