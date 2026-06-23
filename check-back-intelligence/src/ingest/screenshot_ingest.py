"""Collect screenshot/image evidence into Check Back note fields."""

from __future__ import annotations

from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def list_images(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


def ingest_images(folder: str | Path, target_notes: str = "Notes from Calling Analytics") -> dict[str, dict]:
    """
    Map screenshots into Check Back notes (filename list; OCR can extend later).
    Returns field dict compatible with merge pipeline.
    """
    images = list_images(folder)
    if not images:
        return {}

    names = ", ".join(p.name for p in images)
    body = f"Screenshot evidence ({len(images)}): {names}"
    return {
        target_notes: {"value": body, "confidence": "medium", "source": "screenshots"},
    }
