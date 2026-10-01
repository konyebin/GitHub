"""Shared color rules for the ASE candidate sheet and the local dashboard."""

from __future__ import annotations

import re
from urllib.parse import quote

# Fill, then font. Light fills keep the sheet readable.
COLORS = {
    "Former Intern": ("D6E2F5", "1B3A4B"),
    "Studying": ("D0E2FF", "003A70"),
    "Certification": ("C3F0E4", "0B6E4F"),
    "Degree": ("E4D8F8", "4C1D95"),
    "Experience": ("FDE7C7", "8A4B08"),
    "N/A": ("E7E5E4", "44403C"),
    "Confirmed": ("C6EFCE", "006100"),
    "Sent": ("FFE2B8", "7A4E00"),
    "Not interested": ("FFC7CE", "9C0006"),
    "Passing": ("C6EFCE", "006100"),
    "NearPass": ("FFF3A0", "6B5300"),
}

PASSING_SCORE = 21

SKILL_PRIORITY = (
    "Former Intern",
    "Studying",
    "Certification",
    "Degree",
    "Experience",
    "N/A",
)

CERT_NEEDLES = (
    "Holds",
    "CCNA",
    "AWS",
    "Security+",
    "Security +",
    "Cisco",
    "Practitioner",
    "Practioner",
    "Solutions Architect",
    "IBM",
    "Salesforce",
    "belt",
)
DEGREE_NEEDLES = (
    "Bachelor",
    "B.S",
    "Masters",
    "Computer Science",
    "Computer Engineering",
)
EXPERIENCE_NEEDLES = ("intern", "internship", "currently")

STATUS_CONFIRMED = "Sent Assessment Center Instructions and Candidate Confirmed Availability"
STATUS_SENT = "Sent Assessment Center Instructions"
STATUS_NOT_INTERESTED = "Not interested in the role"

STATUS_LABELS = {
    "Confirmed": STATUS_CONFIRMED,
    "Sent": STATUS_SENT,
    "Not interested": STATUS_NOT_INTERESTED,
    "Blank": "Blank (no fill)",
}

MONTHS = {
    "jan": "Jan",
    "january": "Jan",
    "feb": "Feb",
    "february": "Feb",
    "mar": "Mar",
    "march": "Mar",
    "apr": "Apr",
    "april": "Apr",
    "may": "May",
    "jun": "Jun",
    "june": "Jun",
    "jul": "Jul",
    "july": "Jul",
    "aug": "Aug",
    "august": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "september": "Sep",
    "oct": "Oct",
    "october": "Oct",
    "nov": "Nov",
    "november": "Nov",
    "dec": "Dec",
    "december": "Dec",
}

_TERM = re.compile(r"([A-Za-z]+)\s+(\d{4})")


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.lower() in text for needle in needles)


def skill_tags(value) -> list[str]:
    """Every matching skill tag, in legend order. The sheet uses only the first."""
    raw = "" if value is None else str(value).strip()
    if not raw:
        return []
    low = raw.lower()
    tags: list[str] = []
    if "former intern" in low:
        tags.append("Former Intern")
    if "studying" in low:
        tags.append("Studying")
    if _contains_any(low, CERT_NEEDLES):
        tags.append("Certification")
    if _contains_any(low, DEGREE_NEEDLES):
        tags.append("Degree")
    experience_text = low.replace("former intern", "")
    if _contains_any(experience_text, EXPERIENCE_NEEDLES):
        tags.append("Experience")
    if raw.upper() in {"N/A", "NA"}:
        tags.append("N/A")
    return tags


def primary_skill(value) -> str | None:
    tags = skill_tags(value)
    return tags[0] if tags else None


def status_key(value) -> str:
    text = "" if value is None else str(value).strip()
    if text == STATUS_CONFIRMED:
        return "Confirmed"
    if text == STATUS_SENT:
        return "Sent"
    if text == STATUS_NOT_INTERESTED:
        return "Not interested"
    if not text:
        return "Blank"
    return "Other"


def graduation_term(value) -> str:
    text = "" if value is None else str(value).strip()
    match = _TERM.search(text)
    if not match:
        return text or "Unknown"
    month = MONTHS.get(match.group(1).lower())
    if not month:
        return text
    return f"{month} {match.group(2)}"


def _or_search(cell: str, needles: tuple[str, ...]) -> str:
    parts = [f'ISNUMBER(SEARCH("{needle}",{cell}))' for needle in needles]
    return "OR(" + ",".join(parts) + ")"


def skill_formulas(cell: str = "D2") -> list[tuple[str, str]]:
    """First match wins. Callers must set stopIfTrue on each rule."""
    return [
        ("Former Intern", f'ISNUMBER(SEARCH("Former Intern",{cell}))'),
        ("Studying", f'ISNUMBER(SEARCH("studying",{cell}))'),
        ("Certification", _or_search(cell, CERT_NEEDLES)),
        ("Degree", _or_search(cell, DEGREE_NEEDLES)),
        ("Experience", _or_search(cell, EXPERIENCE_NEEDLES)),
        ("N/A", f'OR(TRIM({cell})="N/A",TRIM({cell})="NA")'),
    ]


def status_formulas(cell: str = "N2") -> list[tuple[str, str]]:
    return [
        ("Confirmed", f'TRIM({cell})="{STATUS_CONFIRMED}"'),
        ("Sent", f'TRIM({cell})="{STATUS_SENT}"'),
        ("Not interested", f'TRIM({cell})="{STATUS_NOT_INTERESTED}"'),
    ]


def score_key(value) -> str:
    """Above 23 is green. 21 through 23 is yellow. N/A is gray. Under 21 is plain."""
    if value is None:
        return "Blank"
    if isinstance(value, bool):
        return "Other"
    text = str(value).strip()
    if not text:
        return "Blank"
    if text.upper() in {"N/A", "NA"}:
        return "N/A"
    try:
        number = float(value) if isinstance(value, (int, float)) else float(text)
    except ValueError:
        return "Other"
    if number > 23:
        return "Passing"
    if number >= PASSING_SCORE:
        return "NearPass"
    return "Below"


def score_display(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).strip()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def score_formulas(cell: str = "I2") -> list[tuple[str, str]]:
    """N/A first, then 21–23, then anything above 23."""
    text = f'TRIM({cell}&"")'
    number = f"IFERROR(VALUE({cell}),-1)"
    return [
        ("N/A", f'OR(UPPER({text})="N/A",UPPER({text})="NA")'),
        ("NearPass", f"AND({number}>={PASSING_SCORE},{number}<=23)"),
        ("Passing", f"{number}>23"),
    ]


def linkedin_search_url(name, _city=None) -> str:
    """People search for this name only. Does not guess a single profile."""
    text = "" if name is None else str(name).strip()
    if not text:
        return ""
    return "https://www.linkedin.com/search/results/people/?keywords=" + quote(text)
