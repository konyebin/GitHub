"""Extract Check Back fields from customer PDF exports."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "field_mapping.yaml"

ORG_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)
SUB_RE = re.compile(r"Sub\d+", re.I)
MONEY_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
DATE_RE = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4}")


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _extract_text(pdf_path: Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def _confidence(text_len: int, found: bool) -> str:
    if not found:
        return "low"
    if text_len < 100:
        return "low"
    return "high" if text_len > 500 else "medium"


def _match_extractor(filename: str, config: dict[str, Any]) -> str:
    for entry in config.get("pdf_patterns", []):
        if re.search(entry["pattern"], filename):
            return entry["extractor"]
    return "generic"


def extract_opportunity(text: str, fields: dict[str, Any]) -> None:
    m = re.search(r"(?i)(opportunity|account|customer)[:\s]+(.{3,80})", text)
    if m:
        fields["Opportunity Name"] = {"value": m.group(2).strip().split("\n")[0], "confidence": "medium"}
    amounts = MONEY_RE.findall(text)
    if amounts:
        fields["TCV $"] = {"value": amounts[0].replace("$", "").replace(",", ""), "confidence": "medium"}
    for label, key in [("partner", "Partner"), ("competitor", "Competitor"), ("closed", "Closed on (MM/YY)")]:
        m = re.search(rf"(?i){label}[:\s]+(.{{2,60}})", text)
        if m:
            fields[key] = {"value": m.group(1).strip().split("\n")[0], "confidence": "medium"}


def extract_subscription(text: str, fields: dict[str, Any]) -> None:
    subs = SUB_RE.findall(text)
    if subs:
        fields["Sub #"] = {"value": subs[0], "confidence": "high"}
    dates = DATE_RE.findall(text)
    if dates:
        fields["Sub start date (MM/DD/YYYY)"] = {"value": dates[0], "confidence": "medium"}
    m = re.search(r"(?i)(entitled|license|workspace)[:\s]+([\d,]+)", text)
    if m:
        fields["Entitled Lic Calling"] = {"value": m.group(2), "confidence": "medium"}


def extract_accountinfo(text: str, fields: dict[str, Any]) -> None:
    orgs = ORG_ID_RE.findall(text)
    if orgs:
        fields["Customer org id"] = {"value": orgs[0], "confidence": "high"}


def extract_calling(text: str, fields: dict[str, Any]) -> None:
    m = re.search(r"(?i)(active|registered)[:\s]+([\d,]+)", text)
    if m:
        fields["Active Lic Calling"] = {"value": m.group(2), "confidence": "medium"}
    tc = re.search(r"([\d,.]+[KMkm]?)\s*calls", text, re.I)
    if tc:
        fields["Total calls"] = {"value": tc.group(1), "confidence": "medium"}
    ec = re.search(
        r"([\d,.]+[KMkm]?)\s*(?:out of|/)\s*([\d,.]+[KMkm]?)\s*calls", text, re.I
    )
    if ec:
        fields["External calls"] = {
            "value": f"{ec.group(1)} out of {ec.group(2)}",
            "confidence": "medium",
        }
    ans = re.search(r"([\d.]+)%\s*answered", text, re.I)
    if ans:
        fields["Answered calls %"] = {"value": ans.group(1) + "%", "confidence": "medium"}
    usage = []
    for kw in ("calls", "minutes", "cdr", "usage", "consumption"):
        if kw in text.lower():
            usage.append(kw)
    if usage:
        snippet = text[:500].replace("\n", " ")
        fields["Notes from Calling Analytics"] = {
            "value": f"Usage keywords: {', '.join(usage)}. {snippet[:200]}...",
            "confidence": "low",
        }


def extract_devices(text: str, fields: dict[str, Any]) -> None:
    m = re.search(r"(?i)(device|phone|room|desk).{0,40}(\d+)", text)
    if m:
        fields["Add-ons included or not"] = {"value": f"Devices referenced: {m.group(0)[:80]}", "confidence": "low"}


def extract_collaboration(text: str, fields: dict[str, Any]) -> None:
    notes = []
    for kw in ("meeting", "messaging", "workspace", "webinar", "events"):
        if kw in text.lower():
            notes.append(kw)
    for pattern, key in [
        (r"auto\s*attendant[:\s]*(\d+)", "Auto Attendant count"),
        (r"hunt\s*groups?[:\s]*(\d+)", "Hunt Groups count"),
        (r"virtual\s*lines?[:\s]*(\d+)", "Virtual Lines count"),
    ]:
        m = re.search(pattern, text, re.I)
        if m:
            fields[key] = {"value": m.group(1), "confidence": "medium"}
    if re.search(r"connected[- ]?uc", text, re.I):
        fields["Connected-UC (Y/N)"] = {"value": "Y", "confidence": "medium"}
    prof = re.search(r"professional[^;,\n]*?(\d+)\s*/\s*(\d+)", text, re.I)
    if prof:
        fields["Lic Professional (used/entitled)"] = {
            "value": f"{prof.group(1)}/{prof.group(2)}",
            "confidence": "medium",
        }
    ws = re.search(r"workspace[^;,\n]*?(\d+)\s*/\s*(\d+)", text, re.I)
    if ws:
        fields["Lic Workspace (used/entitled)"] = {
            "value": f"{ws.group(1)}/{ws.group(2)}",
            "confidence": "medium",
        }
    if notes:
        fields["Notes from provisioned features"] = {
            "value": f"Features mentioned: {', '.join(notes)}",
            "confidence": "low",
        }


def extract_success_portal(text: str, fields: dict[str, Any]) -> None:
    for label, key in [
        ("engagement model", "CSM Engagement Model (linked)"),
        ("csm", "CSM name"),
    ]:
        m = re.search(rf"(?i){label}[:\s]+(.{{2,80}})", text)
        if m:
            fields[key] = {"value": m.group(1).strip().split("\n")[0], "confidence": "medium"}


def extract_summary(text: str, fields: dict[str, Any]) -> None:
    extract_opportunity(text, fields)
    extract_accountinfo(text, fields)


EXTRACTORS = {
    "opportunity": extract_opportunity,
    "subscription": extract_subscription,
    "accountinfo": extract_accountinfo,
    "calling": extract_calling,
    "devices": extract_devices,
    "collaboration": extract_collaboration,
    "success_portal": extract_success_portal,
    "summary": extract_summary,
    "generic": extract_summary,
}


def extract_pdf(pdf_path: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    path = Path(pdf_path)
    text = _extract_text(path)
    extractor_name = _match_extractor(path.name, config)
    fields: dict[str, Any] = {}
    fn = EXTRACTORS.get(extractor_name, EXTRACTORS["generic"])
    fn(text, fields)
    for k, v in list(fields.items()):
        if isinstance(v, dict) and "confidence" not in v:
            fields[k] = {"value": v, "confidence": _confidence(len(text), True)}
    return {
        "source_file": path.name,
        "extractor": extractor_name,
        "text_length": len(text),
        "fields": fields,
    }


def extract_folder(
    input_dir: str | Path,
    output_dir: str | Path,
    account_hint: str | None = None,
) -> dict[str, Any]:
    """Extract all PDFs; merge fields into one account record."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict[str, Any]] = {}
    per_file: list[dict[str, Any]] = []

    for pdf in sorted(input_dir.glob("*.pdf")):
        result = extract_pdf(pdf)
        per_file.append(result)
        out_path = output_dir / f"{pdf.stem}_extracted.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        for field, meta in result.get("fields", {}).items():
            if field not in merged or meta.get("confidence") == "high":
                merged[field] = meta

    if account_hint and "Opportunity Name" not in merged:
        merged["Opportunity Name"] = {"value": account_hint, "confidence": "high", "source": "cli"}

    summary = {"account": account_hint or "merged", "merged_fields": merged, "files": per_file}
    (output_dir / "merged_extracted.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    return summary
