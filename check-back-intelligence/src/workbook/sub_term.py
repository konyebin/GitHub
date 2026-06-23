"""Compute Sub Term (years in subscription + current year of term)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

SUB_TERM_COL = "Sub Term"
LEGACY_SUB_START_COL = "Sub start date (MM/DD/YYYY)"

DATE_TOKEN = (
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}-[A-Za-z]{3}-\d{4})"
)
DATE_RANGE_RE = re.compile(
    rf"{DATE_TOKEN}\s*(?:to|-|–)\s*{DATE_TOKEN}",
    re.I,
)
DATE_RANGE_COMMA_RE = re.compile(
    rf"{DATE_TOKEN}\s*,\s*{DATE_TOKEN}",
    re.I,
)
# e.g. 12/12/24-12/12/29 (no spaces around dash)
DATE_RANGE_DASH_RE = re.compile(
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*-\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.I,
)
DATE_TOKEN_FINDALL = re.compile(
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}-[A-Za-z]{3}-\d{4}",
    re.I,
)


def _parse_iso_date(s: str) -> date | None:
    s = s.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _to_date(val: Any) -> date | None:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return _parse_iso_date(str(val).split(" ")[0].strip())


def _extract_subscription_range(raw: str) -> tuple[date | None, date | None]:
    """
    Parse subscription full term as start → end.
    Accepts: start to end, start-end, start,end, start – end (same meaning).
    """
    text = str(raw or "").strip()
    if not text:
        return None, None

    for pattern in (DATE_RANGE_RE, DATE_RANGE_COMMA_RE, DATE_RANGE_DASH_RE):
        m = pattern.search(text)
        if not m:
            continue
        start = _parse_iso_date(m.group(1))
        end = _parse_iso_date(m.group(2))
        if start and end:
            if start <= end:
                return start, end
            return end, start

    tokens = DATE_TOKEN_FINDALL.findall(text)
    if len(tokens) >= 2:
        start = _parse_iso_date(tokens[0])
        end = _parse_iso_date(tokens[1])
        if start and end:
            if start <= end:
                return start, end
            return end, start

    return None, None


def _term_years(start: date, end: date) -> int:
    days = (end - start).days
    if days <= 0:
        return 1
    years = round(days / 365.25)
    return max(1, years)


def _current_year_of_term(start: date, end: date, as_of: date, total_years: int) -> int:
    if as_of < start:
        return 0
    if as_of > end:
        return total_years
    elapsed = (as_of - start).days / 365.25
    return min(total_years, max(1, int(elapsed) + 1))


def format_sub_term(start: date, end: date, as_of: date) -> str:
    total = _term_years(start, end)
    current = _current_year_of_term(start, end, as_of, total)
    as_of_s = as_of.strftime("%Y-%m-%d")
    if as_of < start:
        return f"{total}yr | pre-start (as of {as_of_s})"
    if as_of > end:
        return f"{total}yr | ended {end.strftime('%Y-%m-%d')} (as of {as_of_s})"
    return f"{total}yr | Year {current} of {total} (as of {as_of_s})"


def sub_term_from_text(text: str, as_of: date | None = None) -> tuple[str, bool]:
    """Return (Sub Term label, needs_review_red)."""
    as_of = as_of or date.today()
    raw = str(text or "").strip()
    if not raw:
        return "", False

    if "| Year" in raw and "of" in raw and "as of" in raw:
        return raw, False

    start, end = _extract_subscription_range(raw)
    if start and end:
        return format_sub_term(start, end, as_of), False

    lone = _parse_iso_date(raw.split(" ")[0].replace("00:00:00", "").strip())
    if lone:
        return raw, True

    return raw, True


def sub_term_from_values(
    sub_start_or_range: Any,
    sub_term_months: Any = None,
    as_of: date | None = None,
) -> tuple[str, bool]:
    as_of = as_of or date.today()
    text = str(sub_start_or_range or "").strip()
    if text:
        return sub_term_from_text(text, as_of)

    if sub_term_months not in (None, ""):
        try:
            months = int(float(str(sub_term_months).strip().replace("M", "").replace("m", "")))
            years = max(1, round(months / 12))
            return f"{years}yr | term months only (as of {as_of.strftime('%Y-%m-%d')})", True
        except (ValueError, TypeError):
            pass
    return "", False
