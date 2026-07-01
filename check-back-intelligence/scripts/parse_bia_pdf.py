#!/usr/bin/env python3
"""Parse Lookback BIA PDF → dashboard/bia-slides.js (curated field extraction)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

PDF = Path(__file__).resolve().parent.parent / "samples" / "Lookback-BIA-Slide-Template.pdf"
if not PDF.exists():
    raise SystemExit(f"BIA template PDF not found: {PDF}")
OUT_JS = Path(__file__).resolve().parent.parent / "dashboard" / "bia-slides.js"
OUT_JSON = Path(__file__).resolve().parent.parent / "dashboard" / "data" / "bia-slides.json"


def _m(pat: str, text: str, flags: int = re.I) -> str:
    hit = re.search(pat, text, flags)
    return hit.group(1).strip() if hit else ""


def _clean_field(val: str) -> str:
    s = re.sub(r"\s+", " ", (val or "").strip())
    if re.search(r"External Calls|Licenses Active|@cisco\.com", s, re.I):
        return ""
    return s


def _parse_addons(text: str) -> dict[str, dict[str, str]]:
    """Extract P/T/U grid from slide text."""
    names = [
        "PSTN Cisco Calling Plans",
        "Customer Assist",
        "Attendant Console",
        "AI Receptionist",
        "AI Premium",
    ]
    out: dict[str, dict[str, str]] = {}
    for name in names:
        m = re.search(
            rf"{re.escape(name)}\s+([-\d][^\n]*?)(?:\n|Partner:|CSM Coverage|S&C \|)",
            text,
            re.I,
        )
        if not m:
            m = re.search(rf"{re.escape(name)}\s+([^\n]+)", text, re.I)
        if not m:
            continue
        raw = m.group(1).strip()
        # last three tokens are usually P T U
        parts = re.split(r"\s+", raw)
        if len(parts) >= 3:
            p, t, u = parts[-3], parts[-2], parts[-1]
        else:
            p, t, u = "-", "-", "-"
        out[name] = {"P": p, "T": t, "U": u}
    return out


def _parse_subscription_dates(term: str) -> str:
    if not term:
        return ""
    m = re.search(
        r"from\s+([\d/.\-]+)\s*(?:-\s*)?to\s+([\d/.\-]+)",
        term,
        re.I,
    )
    if not m:
        return ""
    return f"{m.group(1).strip()} to {m.group(2).strip()}"


def _notes(text: str) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    roles = (
        r"Renewals?\s+SE",
        r"CSM\s*/?\s*Acct\s+Team",
        r"CSM/\s*Acct\s+Team",
        r"Acct\s+Team",
        r"Insight",
        r"Note",
    )
    for role in roles:
        for m in re.finditer(
            rf"({role})\s+(.+?)(?=(?:{'|'.join(roles)})|Notes & Recommended|© 2025|Data gathered)",
            text,
            re.I | re.S,
        ):
            body = re.sub(r"\s+", " ", m.group(2)).strip()
            if len(body) > 25 and "Subscription Review" not in body:
                notes.append({"who": m.group(1).strip(), "text": body[:600]})
    return notes[:6]


def parse_customer_slide(text: str, page: int) -> dict | None:
    if "Business Insight and Analysis" not in text:
        return None
    if "ADD FROM HERE" in text:
        return None

    name = _m(r"^(.+?)\nData gathered", text, re.M | re.S)
    if not name:
        name = text.split("\n")[0].strip()
    name = re.sub(r"\s+", " ", name).strip()

    org = _m(r"Customer Org ID:\s*([a-f0-9-]{36})", text)
    platforms = _m(
        r"(Meetings:[^\n]+?)(?:\n|Customer Org ID:|Auto Attendant)", text, re.S
    ).replace("\n", " ")

    health = "Unknown"
    if re.search(r"\bUPSELL\b", text):
        health = "Upsell"
    elif re.search(r"\bGood\b", text):
        health = "Good"
    elif re.search(r"\bRisk\b", text):
        health = "Risk"

    sub = _m(r"Subscription:\s*([Sub\d,\s]+)", text)
    term = _m(r"Term:\s*([^\n]+)", text)
    tcv = _m(r"Total Contract Value:\s*([^\n]+)", text)
    aar = _m(r"Total Recurring Revenue \((?:AAR|ARR)\):\s*([^\n]+)", text)
    entitled = _m(r"Entitled Licenses:\s*([^\n]+)", text)
    if not entitled:
        entitled = _m(r"Entitled Licenses:\s*([^\n]+)", text)

    slide = {
        "page": page,
        "customerName": name,
        "orgId": org,
        "gatheredBy": _m(r"by\s+([A-Za-z][^\n]+?)(?:\n|Business)", text),
        "gatheredDate": _m(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
            text,
        ),
        "health": health,
        "platforms": platforms[:180],
        "subscription": {
            "sub": sub.split("Entitled")[0].strip() if sub else "",
            "term": term.split("Professional")[0].strip() if term else "",
            "tcv": tcv.split("Active")[0].strip() if tcv else "",
            "aar": _clean_field(aar.split("Numbers")[0] if aar else ""),
            "collabAe": _clean_field(_m(r"Collab AE/SE:\s*([^\n]+)", text).split("Segment")[0]),
            "segment": _clean_field(
                _m(r"Segment:\s*([^\n]+)", text).split("Location")[0].split("External")[0]
            ),
            "partner": _clean_field(
                _m(r"Partner:\s*([^\n]+)", text).split("External")[0].split("Meetings")[0]
            ),
            "csmModel": _clean_field(
                _m(r"CSM Coverage Model:\s*([^\n]+)", text).split("Meetings")[0]
            ),
            "links": "S&C | Success Portal",
        },
        "provisioning": {
            "orgId": org,
            "entitled": _m(r"Entitled Licenses:\s*([^\n]+)", text).split("Hunt")[0].strip(),
            "professional": _m(r"Professional:\s*([^|\n]+)", text),
            "standard": _m(r"Standard:\s*([^|\n]+)", text),
            "workspace": _m(r"Workspace:\s*([^|\n]+)", text),
            "activeUsers": _m(r"Active Users:\s*([^\n]+)", text).split("Virtual")[0].strip(),
            "externalCalls": _m(r"External Calls vs Total Calls:\s*([^\n]+)", text).split("Customer")[0].strip(),
            "meetings": _m(r"Meetings:\s*([^\n]+)", text).split("Messaging")[0].strip(),
            "messaging": _m(r"Messaging:\s*([^\n]+)", text).split("Provisioned")[0].strip(),
            "numbersAssigned": _m(r"Numbers Assigned / Provisioned:\s*([^\n]*)", text),
            "locations": _m(r"Location with Main Number / Voicemail portal:\s*([^\n]*)", text),
        },
        "features": {
            "autoAttendant": _m(r"Auto Attendant\s+(\d+|-)", text) or "—",
            "huntGroups": _m(r"Hunt Groups\s+(\d+|-)", text) or "—",
            "callQueues": _m(r"Basic Call Queues\s+(\d+|-)", text) or "—",
            "connectedUc": _m(r"Connected-UC\s+([YN\-]+|NA)", text) or "—",
            "virtualLines": _m(r"Virtual Lines\s+(\d+|-)", text) or "—",
        },
        "trends": [],
        "notes": _notes(text),
        "addons": _parse_addons(text),
        "subscriptionDates": _parse_subscription_dates(
            term.split("Professional")[0].strip() if term else ""
        ),
        "isTemplate": "TEMPLATE" in text or "Alamo Workforce" in name,
    }

    for label in ("Provisioned licenses", "Active users", "Call volume"):
        t = _m(rf"{label}\s+([^\n]+)", text)
        if t:
            slide["trends"].append(f"{label} {t}")

    return slide


def main() -> None:
    slides: list[dict] = []
    with pdfplumber.open(PDF) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            slide = parse_customer_slide(text, i)
            if slide:
                slides.append(slide)

    js = "/** Auto-generated from Lookback BIA Slide Template PDF — run scripts/parse_bia_pdf.py */\n"
    js += "const BIA_SLIDES = " + json.dumps(slides, indent=2) + ";\n"
    OUT_JS.write_text(js, encoding="utf-8")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(slides, indent=2), encoding="utf-8")
    print(f"Wrote {len(slides)} slides → {OUT_JS} and {OUT_JSON}")


if __name__ == "__main__":
    main()
