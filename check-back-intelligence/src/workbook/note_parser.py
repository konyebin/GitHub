"""Parse Check Back note fields into structured PowerPoint-aligned columns."""

from __future__ import annotations

import re
from typing import Any

PROV_ENT_LICENSE_COL = "Provisioned/Entitled Lic Calling"

PROF_RE = re.compile(
    r"professional(?:\s+calling)?\s+(?:assigned\s+)?(\d[\d,]*)\s*/\s*(\d[\d,]*)",
    re.I,
)
STD_RE = re.compile(
    r"standard(?:\s+calling)?\s+(?:assigned\s+)?(\d[\d,]*)\s*/\s*(\d[\d,]*)",
    re.I,
)
WS_RE = re.compile(
    r"workspace(?:\s+calling)?\s+(?:assigned\s+)?(\d[\d,]*)\s*/\s*(\d[\d,]*)",
    re.I,
)
PL_RE = re.compile(r"\bPL[:\s]+(\d[\d,]*)\s*/\s*(\d[\d,]*)", re.I)
PROF_WS_SHORT_RE = re.compile(r"(\d[\d,]*)\s+workspace\s+(\d[\d,]*)", re.I)
AA_RE = re.compile(r"auto\s*attendant[:\s]*(\d+)", re.I)
HUNT_RE = re.compile(r"hunt\s*groups?[:\s]*(\d+)", re.I)
QUEUE_RE = re.compile(r"(?:basic\s*)?call\s*queues?[:\s]*(\d+|-)", re.I)
VL_RE = re.compile(r"virtual\s*lines?[:\s]*(\d+)", re.I)
TOTAL_CALLS_RE = re.compile(
    r"total\s*calls?[:\s]*([\d,.]+[KMkm]?)|([\d,.]+[KMkm]?)\s*calls\s+in\s+last",
    re.I,
)
EXT_CALLS_RE = re.compile(
    r"([\d,.]+[KMkm]?)\s*(?:out of|/)\s*([\d,.]+[KMkm]?)\s*calls",
    re.I,
)
ANSWERED_RE = re.compile(
    r"(?:answered\s*calls?|good\s*quality)[:\s]*([\d.]+)%|([\d.]+)%\s*answered",
    re.I,
)
ACTIVE_TREND_RE = re.compile(
    r"active\s*users?[^.;]{0,40}?(UP|DOWN)\s*([+-]?[\d.]+%?)",
    re.I,
)
CALL_TREND_RE = re.compile(
    r"call\s*volume[^.;]{0,40}?(UP|DOWN)\s*([+-]?[\d.]+%?)",
    re.I,
)
ACTIVE_PCT_RE = re.compile(r"(\d{1,3})%\s*of\s*provisioned", re.I)
SERVICE_LINES_RE = re.compile(
    r"(meetings?\s*:\s*\w+[^|]*\|[^|]*calling\s*:\s*\w+[^|]*(?:\|[^|]*wx\w+[^|]*)?)",
    re.I,
)
MEETINGS_USAGE_RE = re.compile(
    r"(\d+)\s*unique\s*hosts?[^;]*;?\s*(\d+)\s*total\s*meetings?",
    re.I,
)
MSG_USAGE_RE = re.compile(
    r"(\d+)\s*active\s*users?[^;]*;?\s*([\d,.]+[KMkm]?)\s*messages?\s*sent",
    re.I,
)
AAR_RE = re.compile(
    r"(?:\bAAR\b|\bARR\b|annual\s*recurring|total\s*recurring)[:\s\$]*([\d,.]+[KMkm]?|\d[\d,]*)",
    re.I,
)
TERM_MONTHS_RE = re.compile(r"\b(\d{2,3})\s*(?:\.\d+)?\s*months?\b", re.I)
COLLAB_AE_RE = re.compile(
    r"(?:collab\s*)?(?:ae/se|ae)[:\s]+([A-Za-z][A-Za-z\s/.'-]{2,60})",
    re.I,
)
BUSIEST_HOUR_RE = re.compile(
    r"busiest\s*hour[^0-9]*([\d,.]+[KMkm]?)|calls\s+in\s+busiest\s*hour[:\s]*([\d,.]+[KMkm]?)",
    re.I,
)

from .slide_layout import STRUCTURED_COLUMNS  # noqa: F401 — re-export


def _pair(val: re.Match | None) -> str:
    if not val:
        return ""
    return f"{val.group(1)}/{val.group(2)}"


def parse_prof_ws_shorthand(text: Any) -> dict[str, str] | None:
    """e.g. '1,265 workspace 335' → professional 1265, workspace 335."""
    m = PROF_WS_SHORT_RE.search(str(text or ""))
    if not m:
        return None
    return {
        "professional": m.group(1).replace(",", ""),
        "workspace": m.group(2).replace(",", ""),
    }


def apply_prof_ws_shorthand_from_cells(row: dict[str, Any], out: dict[str, Any]) -> None:
    for field in (
        PROV_ENT_LICENSE_COL,
        "Entitled Lic Calling",
        "Providioned Lic Calling",
    ):
        parsed = parse_prof_ws_shorthand(row.get(field))
        if not parsed:
            continue
        from_provisioned = field in (PROV_ENT_LICENSE_COL, "Providioned Lic Calling")
        prof_key = "Lic Professional (used/entitled)"
        ws_key = "Lic Workspace (used/entitled)"
        if from_provisioned or prof_key not in out:
            out[prof_key] = parsed["professional"]
        if from_provisioned or ws_key not in out:
            out[ws_key] = parsed["workspace"]


def _trend(val: re.Match | None) -> str:
    if not val:
        return ""
    return f"{val.group(1).upper()} {val.group(2)}"


def parse_notes_to_structured(
    analytics: str, features: str, addons: str = ""
) -> dict[str, Any]:
    """Conservative parse — only set fields with high-confidence patterns."""
    combined = " ".join(filter(None, [analytics, features, addons]))
    out: dict[str, Any] = {}

    for regex, key in [
        (PROF_RE, "Lic Professional (used/entitled)"),
        (STD_RE, "Lic Standard (used/entitled)"),
        (WS_RE, "Lic Workspace (used/entitled)"),
    ]:
        m = regex.search(combined)
        if m:
            out[key] = _pair(m)

    pl = PL_RE.search(combined)
    if pl and "Lic Professional (used/entitled)" not in out:
        out["Lic Professional (used/entitled)"] = _pair(pl)

    for regex, key in [
        (AA_RE, "Auto Attendant count"),
        (HUNT_RE, "Hunt Groups count"),
        (QUEUE_RE, "Call Queues count"),
        (VL_RE, "Virtual Lines count"),
    ]:
        m = regex.search(combined)
        if m:
            out[key] = m.group(1)

    if re.search(r"connected[- ]?uc", combined, re.I):
        out["Connected-UC (Y/N)"] = "Y"

    tc = TOTAL_CALLS_RE.search(combined)
    if tc:
        out["Total calls"] = (tc.group(1) or tc.group(2) or "").strip()

    ec = EXT_CALLS_RE.search(combined)
    if ec:
        out["External calls"] = f"{ec.group(1)} out of {ec.group(2)}"

    ans = ANSWERED_RE.search(combined)
    if ans:
        pct = ans.group(1) or ans.group(2)
        out["Answered calls %"] = f"{pct}%" if pct and not str(pct).endswith("%") else str(pct)

    bh = BUSIEST_HOUR_RE.search(combined)
    if bh:
        out["Calls busiest hour"] = (bh.group(1) or bh.group(2) or "").strip()

    at, ct = ACTIVE_TREND_RE.search(combined), CALL_TREND_RE.search(combined)
    if at:
        out["Trend active users 90d"] = _trend(at)
    if ct:
        out["Trend call volume 90d"] = _trend(ct)

    mu = MEETINGS_USAGE_RE.search(combined)
    if mu:
        out["Meetings usage"] = f"{mu.group(1)} unique hosts; {mu.group(2)} total meetings"
    elif re.search(r"\d+\s*total\s*meetings?", combined, re.I):
        m = re.search(r"(\d+)\s*total\s*meetings?", combined, re.I)
        if m:
            out["Meetings usage"] = f"{m.group(1)} total meetings"

    ms = MSG_USAGE_RE.search(combined)
    if ms:
        out["Messaging usage"] = f"{ms.group(1)} active users; {ms.group(2)} messages sent"

    sl = SERVICE_LINES_RE.search(combined)
    if sl:
        out["Service lines"] = sl.group(1).strip()[:120]

    aar = AAR_RE.search(combined)
    if aar:
        out["AAR $"] = aar.group(1).replace(",", "")

    ae = COLLAB_AE_RE.search(combined)
    if ae:
        name = ae.group(1).strip().split("\n")[0]
        if len(name) > 3 and not name.lower().startswith("the "):
            out["Collab AE/SE"] = name[:80]

    tm = TERM_MONTHS_RE.search(combined)
    if tm:
        out["Sub term (months)"] = tm.group(1)

    ap = ACTIVE_PCT_RE.search(combined)
    if ap:
        out["Active % of provisioned"] = f"{ap.group(1)}%"

    return out


def parse_notes_and_cells(
    analytics: str, features: str, addons: str = "", row: dict[str, Any] | None = None
) -> dict[str, Any]:
    out = parse_notes_to_structured(analytics, features, addons)
    if row:
        apply_prof_ws_shorthand_from_cells(row, out)
    return out


def compute_active_pct(provisioned: Any, active: Any) -> str:
    """Only when both fields look like plain license counts."""

    def _simple_max(val: Any) -> float | None:
        if val in (None, ""):
            return None
        s = str(val)
        if re.search(r"workspace|professional|standard|PL:|WxM|Agent", s, re.I):
            return None
        nums = re.findall(r"[\d,]+(?:\.\d+)?", s)
        vals: list[float] = []
        for n in nums:
            try:
                vals.append(float(n.replace(",", "")))
            except ValueError:
                continue
        if not vals or len(vals) > 2:
            return None
        return max(vals)

    p, a = _simple_max(provisioned), _simple_max(active)
    if p is None or a is None or p <= 0:
        return ""
    if a > p * 1.05:
        return ""
    return f"{round((a / p) * 100)}%"
