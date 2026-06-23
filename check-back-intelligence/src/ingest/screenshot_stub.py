"""Backward-compatible alias; use screenshot_ingest via populate CLI."""

from __future__ import annotations

from pathlib import Path

from src.ingest.screenshot_ingest import ingest_images, list_images


def process_screenshot(image_path: str | Path) -> dict[str, str]:
    p = Path(image_path)
    return {
        "status": "ingested_as_filename",
        "file": p.name,
        "message": "Use: python -m src.cli populate --sources <folder>",
    }
