"""CLI for Check Back data prep pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKBOOK = PROJECT_ROOT / "output" / "Check_Back_standardized.xlsx"
DEFAULT_TEMPLATE = PROJECT_ROOT / "samples" / "check_back_template.xlsx"


def _cmd_populate(args: argparse.Namespace) -> int:
    """Primary flow: PDFs + screenshots → Check Back spreadsheet (for any customer)."""
    from src.ingest.sources import ingest_sources
    from src.workbook.merge_sources import build_workbook

    records = ingest_sources(args.sources, args.staging, account_hint=args.account)
    print(f"Ingested {len(records)} customer batch(es) → {args.staging}/customers.json")
    for r in records:
        print(f"  • {r['account']} ({len(r.get('files', []))} PDFs)")

    path = build_workbook(
        template_path=args.template,
        output_path=args.out,
        staging_dir=args.staging,
        install_base_path=args.install_base,
        account_filter=args.account_filter or args.account,
        ib_limit=args.ib_limit,
        mode=args.mode,
    )
    print(f"Check Back workbook → {path}")
    print("Upload this .xlsx in dashboard/index.html (dashboard does not read PDFs directly).")
    return 0


def _cmd_ingest_sources(args: argparse.Namespace) -> int:
    from src.ingest.sources import ingest_sources

    records = ingest_sources(args.input, args.out, account_hint=args.account)
    print(f"Ingested {len(records)} batch(es) → {args.out}/customers.json")
    return 0


def _cmd_extract_pdfs(args: argparse.Namespace) -> int:
    from src.ingest.sources import ingest_folder
    import json

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    record = ingest_folder(args.input, account_label=args.account)
    (out / "merged_extracted.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    (out / "customers.json").write_text(json.dumps([record], indent=2), encoding="utf-8")
    print(f"Extracted {len(record.get('files', []))} PDFs (+ images) → {args.out}/customers.json")
    return 0


def _cmd_map_install_base(args: argparse.Namespace) -> int:
    from src.ingest.install_base_mapper import map_workbook

    rows = map_workbook(args.input, args.out, args.gap_report)
    print(f"Mapped {len(rows)} rows → {args.out}")
    if args.gap_report:
        print(f"Gap report → {args.gap_report}")
    return 0


def _cmd_build_workbook(args: argparse.Namespace) -> int:
    from src.workbook.merge_sources import build_workbook

    path = build_workbook(
        template_path=args.template,
        output_path=args.out,
        staging_dir=args.staging,
        install_base_path=args.install_base,
        account_filter=args.account_filter or args.account,
        ib_limit=args.ib_limit,
        mode=args.mode,
    )
    print(f"Workbook written → {path}")
    return 0


def _cmd_upgrade_spreadsheet(args: argparse.Namespace) -> int:
    from src.workbook.upgrade_schema import upgrade_workbook

    result = upgrade_workbook(Path(args.input), backup=not args.no_backup)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_sync_workbook(args: argparse.Namespace) -> int:
    from src.workbook.sync_workbook import sync_workbook

    result = sync_workbook(
        Path(args.input),
        backup=not args.no_backup,
        ensure_columns=args.add_columns,
    )
    print(json.dumps(result, indent=2))
    mismatches = result.get("rebuild", {}).get("slide_mismatches_after_sync") or []
    if mismatches:
        print(f"Warning: {len(mismatches)} slide verification mismatch(es); workbook was still saved.", file=sys.stderr)
    return 0


def _cmd_rebuild_ppt_columns(args: argparse.Namespace) -> int:
    """Legacy alias for sync-workbook."""
    args.add_columns = getattr(args, "add_columns", False)
    return _cmd_sync_workbook(args)


def _cmd_sync_subscription_dates(args: argparse.Namespace) -> int:
    from src.workbook.subscription_dates import sync_subscription_dates

    result = sync_subscription_dates(Path(args.input))
    print(json.dumps(result, indent=2))
    return 0


def _cmd_export_panels(args: argparse.Namespace) -> int:
    from src.workbook.panel_cache import export_panels

    result = export_panels(
        Path(args.input),
        args.output,
        backup=not args.no_backup,
    )
    print(json.dumps(result, indent=2))
    return 0


def _cmd_import_panels(args: argparse.Namespace) -> int:
    from src.workbook.panel_cache import import_panels

    result = import_panels(
        Path(args.input),
        args.panel,
        backup=not args.no_backup,
    )
    print(json.dumps(result, indent=2))
    return 0


def _cmd_standardize_columns(args: argparse.Namespace) -> int:
    from datetime import datetime

    from src.workbook.column_standardize import standardize_workbook

    as_of = None
    if getattr(args, "as_of", None):
        as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    stats = standardize_workbook(args.input, args.output, as_of=as_of)
    print(json.dumps(stats, indent=2))
    print(f"Standardized workbook → {stats['output']}")
    if stats["cells_red"]:
        print(f"Red cells (needs review): {stats['cells_red']}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    from src.workbook.merge_sources import validate_workbook

    issues = validate_workbook(args.input)
    if args.out:
        Path(args.out).write_text(json.dumps(issues, indent=2), encoding="utf-8")
        print(f"Validation report → {args.out}")
    if not issues:
        print("No issues found.")
        return 0
    for i in issues:
        print(f"  Row {i['row']} ({i['account']}): {i['issue']}")
    return 1 if issues else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Back pipeline: PDFs/screenshots → spreadsheet → dashboard upload"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_pop = sub.add_parser(
        "populate",
        help="Ingest PDFs/screenshots from a folder and write Check Back xlsx (recommended)",
    )
    p_pop.add_argument(
        "--sources",
        "-s",
        required=True,
        help="Folder with customer PDFs and/or screenshots (.png, .jpg, …)",
    )
    p_pop.add_argument("--out", "-o", default="output/check_back_filled.xlsx")
    p_pop.add_argument("--staging", default="staging", help="JSON staging directory")
    p_pop.add_argument("--template", "-t", default="samples/check_back_template.xlsx")
    p_pop.add_argument(
        "--account",
        help="Account/opportunity label when sources are a flat folder (not subfolders)",
    )
    p_pop.add_argument(
        "--account-filter",
        help="Only include rows matching this name (install base + staged rows)",
    )
    p_pop.add_argument("--install-base", help="Optional install base xlsx to map extra fields")
    p_pop.add_argument("--ib-limit", type=int, default=None, help="Max install base rows")
    p_pop.add_argument(
        "--mode",
        choices=["fresh", "append"],
        default="fresh",
        help="fresh=only ingested rows; append=keep existing template rows",
    )
    p_pop.set_defaults(func=_cmd_populate)

    p_ing = sub.add_parser("ingest-sources", help="PDFs + images → staging/customers.json only")
    p_ing.add_argument("--input", "-i", required=True)
    p_ing.add_argument("--out", "-o", default="staging")
    p_ing.add_argument("--account", help="Account label for flat folder")
    p_ing.set_defaults(func=_cmd_ingest_sources)

    p_ext = sub.add_parser("extract-pdfs", help="Legacy alias for ingest-sources (one folder)")
    p_ext.add_argument("--input", "-i", required=True)
    p_ext.add_argument("--out", "-o", default="staging")
    p_ext.add_argument("--account", help="Account label")
    p_ext.set_defaults(func=_cmd_extract_pdfs)

    p_map = sub.add_parser("map-install-base", help="Map install base to Check Back rows JSON")
    p_map.add_argument("--input", "-i", required=True)
    p_map.add_argument("--out", "-o", default="staging/ib_rows.json")
    p_map.add_argument("--gap-report", "-g", default="staging/gap_report.csv")
    p_map.set_defaults(func=_cmd_map_install_base)

    p_build = sub.add_parser("build-workbook", help="Build xlsx from staging JSON")
    p_build.add_argument("--template", "-t", default="samples/check_back_template.xlsx")
    p_build.add_argument("--out", "-o", default="output/check_back_filled.xlsx")
    p_build.add_argument("--staging", "-p", default="staging")
    p_build.add_argument("--install-base", help="Optional install base xlsx")
    p_build.add_argument("--account", help="Alias for --account-filter")
    p_build.add_argument("--account-filter", help="Filter rows by opportunity name")
    p_build.add_argument("--ib-limit", type=int, default=None)
    p_build.add_argument("--mode", choices=["fresh", "append"], default="fresh")
    p_build.set_defaults(func=_cmd_build_workbook)

    p_up = sub.add_parser(
        "upgrade-spreadsheet",
        help="Add PowerPoint-aligned columns and backfill from existing notes",
    )
    p_up.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_WORKBOOK),
    )
    p_up.add_argument("--no-backup", action="store_true", help="Do not create .backup_* copy")
    p_up.set_defaults(func=_cmd_upgrade_spreadsheet)

    p_sync = sub.add_parser(
        "sync-workbook",
        help="All-in-one: slide columns, Salesforce URLs, subscription dates (recommended)",
    )
    p_sync.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_WORKBOOK),
    )
    p_sync.add_argument("--no-backup", action="store_true")
    p_sync.add_argument(
        "--add-columns",
        action="store_true",
        help="Also run upgrade-spreadsheet to add missing PowerPoint columns",
    )
    p_sync.set_defaults(func=_cmd_sync_workbook)

    p_rb = sub.add_parser(
        "rebuild-ppt-columns",
        help="Alias for sync-workbook",
    )
    p_rb.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_WORKBOOK),
    )
    p_rb.add_argument("--no-backup", action="store_true")
    p_rb.add_argument("--add-columns", action="store_true")
    p_rb.set_defaults(func=_cmd_rebuild_ppt_columns)

    p_sd = sub.add_parser(
        "sync-subscription-dates",
        help="Add/fill Subscription dates column from Sub start + term (or copy existing ranges)",
    )
    p_sd.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_WORKBOOK),
    )
    p_sd.set_defaults(func=_cmd_sync_subscription_dates)

    _default_xlsx = str(DEFAULT_WORKBOOK)

    p_ep = sub.add_parser(
        "export-panels",
        help="Export Subscription Review / Provisioning / Feature Use columns to a sidecar xlsx",
    )
    p_ep.add_argument("--input", "-i", default=_default_xlsx)
    p_ep.add_argument(
        "--output",
        "-o",
        help="Sidecar path (default: <workbook>_panels.xlsx next to main file)",
    )
    p_ep.add_argument("--no-backup", action="store_true")
    p_ep.set_defaults(func=_cmd_export_panels)

    p_ip = sub.add_parser(
        "import-panels",
        help="Merge sidecar panel xlsx back into the main Check Back workbook",
    )
    p_ip.add_argument("--input", "-i", default=_default_xlsx)
    p_ip.add_argument(
        "--panel",
        "-p",
        help="Sidecar path (default: <workbook>_panels.xlsx next to main file)",
    )
    p_ip.add_argument("--no-backup", action="store_true")
    p_ip.set_defaults(func=_cmd_import_panels)

    p_std = sub.add_parser(
        "standardize-columns",
        help="Normalize column values per config/column_standards.yaml; flag bad cells in red",
    )
    p_std.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_WORKBOOK),
    )
    p_std.add_argument(
        "--output",
        "-o",
        help="Output path (default: <workbook>_standardized.xlsx)",
    )
    p_std.add_argument(
        "--as-of",
        help="Reference date for Sub Term year calculation (YYYY-MM-DD, default: today)",
    )
    p_std.set_defaults(func=_cmd_standardize_columns)

    p_val = sub.add_parser("validate", help="Validate Check Back workbook")
    p_val.add_argument("--input", "-i", required=True)
    p_val.add_argument("--out", help="Write JSON report")
    p_val.set_defaults(func=_cmd_validate)

    args = parser.parse_args(argv)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
