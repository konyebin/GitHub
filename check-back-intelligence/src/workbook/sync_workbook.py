"""One-shot workbook sync: slide columns, Salesforce URLs, subscription dates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .powerpoint_backfill import rebuild_powerpoint_columns
from .subscription_dates import sync_subscription_dates


def sync_workbook(
    path: str | Path,
    *,
    backup: bool = True,
    ensure_columns: bool = False,
) -> dict[str, Any]:
    """Run spreadsheet maintenance steps in order."""
    path = Path(path)
    result: dict[str, Any] = {"path": str(path)}

    if ensure_columns:
        from .upgrade_schema import upgrade_workbook

        result["upgrade_schema"] = upgrade_workbook(path, backup=backup)
        backup = False

    result["rebuild"] = rebuild_powerpoint_columns(
        path, backup=backup, ensure_columns=ensure_columns
    )
    result["subscription_dates"] = sync_subscription_dates(path)
    return result
