"""Ingest a customer source folder (PDFs + screenshots) into Check Back field maps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ingest.pdf_extractors import extract_pdf, load_config
from src.ingest.screenshot_ingest import ingest_images


def _merge_field_maps(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    """Prefer higher confidence when merging field maps."""
    rank = {"high": 3, "medium": 2, "low": 1}
    for field, meta in incoming.items():
        if field not in target:
            target[field] = meta
            continue
        cur = target[field]
        if not isinstance(cur, dict) or not isinstance(meta, dict):
            if meta:
                target[field] = meta
            continue
        if rank.get(meta.get("confidence", ""), 0) >= rank.get(cur.get("confidence", ""), 0):
            target[field] = meta


def ingest_folder(
    folder: str | Path,
    account_label: str | None = None,
) -> dict[str, Any]:
    """Extract all PDFs and images in one folder into a single Check Back field map."""
    folder = Path(folder)
    config = load_config()
    merged: dict[str, Any] = {}
    files_log: list[dict[str, Any]] = []

    for pdf in sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.PDF")):
        result = extract_pdf(pdf, config)
        files_log.append(result)
        _merge_field_maps(merged, result.get("fields", {}))

    _merge_field_maps(merged, ingest_images(folder))

    if account_label and "Opportunity Name" not in merged:
        merged["Opportunity Name"] = {
            "value": account_label,
            "confidence": "high",
            "source": "folder_label",
        }

    return {
        "account": account_label or folder.name,
        "source_folder": str(folder),
        "merged_fields": merged,
        "files": files_log,
    }


def discover_batches(sources_dir: str | Path, account_hint: str | None = None) -> list[tuple[str, Path]]:
    """
    One batch = one Check Back row.
    - Subfolders with PDFs/images → one row per subfolder (name = folder name).
    - Flat folder → one row (name = account_hint or folder name).
    """
    sources_dir = Path(sources_dir)
    batches: list[tuple[str, Path]] = []

    for sub in sorted(sources_dir.iterdir()):
        if not sub.is_dir():
            continue
        has_files = any(sub.glob("*.pdf")) or any(sub.glob("*.PDF")) or any(
            sub.glob(f"*{ext}") for ext in (".png", ".jpg", ".jpeg", ".webp")
        )
        if has_files:
            batches.append((sub.name, sub))

    if batches:
        return batches

    label = account_hint or sources_dir.name
    return [(label, sources_dir)]


def ingest_sources(
    sources_dir: str | Path,
    output_dir: str | Path,
    account_hint: str | None = None,
) -> list[dict[str, Any]]:
    """
    Ingest all customer batches under sources_dir.
    Writes per-batch JSON + combined customers.json to output_dir.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    for label, folder in discover_batches(sources_dir, account_hint):
        record = ingest_folder(folder, account_label=label if label != "." else account_hint)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in record["account"])[:80]
        (output_dir / f"{safe}_extracted.json").write_text(
            json.dumps(record, indent=2, default=str), encoding="utf-8"
        )
        records.append(record)

    (output_dir / "customers.json").write_text(
        json.dumps(records, indent=2, default=str), encoding="utf-8"
    )
    return records
