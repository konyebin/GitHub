"""Write an ASE workbook with status colors plus a Legend sheet.

Full name, graduation date, home cities, skills, and notes stay uncolored.
Pass --names-file for a slice, or --all for the full sheet.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import openpyxl
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from rules import (
    COLORS,
    STATUS_CONFIRMED,
    STATUS_NOT_INTERESTED,
    STATUS_SENT,
    score_formulas,
    status_formulas,
)

STATUS_TEXT = {
    "Confirmed": STATUS_CONFIRMED,
    "Sent": STATUS_SENT,
    "Not interested": STATUS_NOT_INTERESTED,
}

NAME_COL = 2  # 1-based
SCORE_COL = 9
STATUS_COL = 14
KEEP_COLS = 14

HEADER_FILL = PatternFill(start_color="1C1915", end_color="1C1915", fill_type="solid")
HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
BODY_FONT = Font(name="Calibri", size=11, color="1C1915")
THIN = Border(
    left=Side(style="thin", color="E6E0D6"),
    right=Side(style="thin", color="E6E0D6"),
    top=Side(style="thin", color="E6E0D6"),
    bottom=Side(style="thin", color="E6E0D6"),
)
WRAP = Alignment(wrap_text=True, vertical="top")


def read_names(path: Path) -> list[str]:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.split("#", 1)[0].strip()
        if cleaned:
            names.append(cleaned)
    if not names:
        raise SystemExit(f"No names in {path}")
    return names


def load_rows(path: Path) -> tuple[list, list[tuple]]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    rows = list(sheet.iter_rows(min_col=1, max_col=KEEP_COLS, values_only=True))
    if not rows:
        raise SystemExit(f"No rows in {path}")
    header = list(rows[0])
    data = []
    for row in rows[1:]:
        values = tuple(row)
        if all(cell is None or str(cell).strip() == "" for cell in values):
            continue
        data.append(values)
    return header, data


def select_rows(data: list[tuple], names: list[str] | None) -> list[tuple]:
    if names is None:
        return data
    wanted = {name.casefold(): name for name in names}
    chosen = []
    found = set()
    for row in data:
        raw = row[NAME_COL - 1]
        key = "" if raw is None else str(raw).strip().casefold()
        if key in wanted:
            chosen.append(row)
            found.add(key)
    missing = [wanted[key] for key in wanted if key not in found]
    if missing:
        raise SystemExit("Names not found: " + ", ".join(missing))
    return chosen


def _fill_font(key: str):
    fill_hex, font_hex = COLORS[key]
    return (
        PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid"),
        Font(name="Calibri", color=font_hex, size=11),
    )


def _add_rules(sheet, formulas, column_letter: str, last_row: int) -> None:
    # Extra rows stay covered if someone pastes more candidates under the preview.
    target = f"{column_letter}2:{column_letter}{max(last_row, 200)}"
    for key, formula in formulas:
        fill, font = _fill_font(key)
        rule = FormulaRule(formula=[formula], fill=fill, font=font, stopIfTrue=True)
        sheet.conditional_formatting.add(target, rule)


def write_legend(workbook) -> None:
    sheet = workbook.create_sheet("Legend")
    sheet.sheet_properties.tabColor = "1C1915"
    sheet["A1"] = "ASE color legend"
    sheet["A1"].font = Font(name="Calibri", bold=True, size=16, color="1C1915")
    sheet["A2"] = (
        "Status and score are colored. Scores above 23 are green, and 21 through 23 are yellow. "
        "N/A scores are colored separately. Scores under 21, full name, graduation date, "
        "home cities, skills and technologies, and notes stay uncolored."
    )
    sheet["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.merge_cells("A2:D2")
    sheet.row_dimensions[2].height = 32

    headers = ("Swatch", "Column", "Label", "Rule")
    for index, text in enumerate(headers, start=1):
        cell = sheet.cell(4, index, text)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")

    rows = [
        ("Confirmed", "Status", "Confirmed availability", f'Exact text, after trimming spaces: "{STATUS_TEXT["Confirmed"]}"'),
        ("Sent", "Status", "Instructions sent", f'Exact text, after trimming spaces: "{STATUS_TEXT["Sent"]}"'),
        ("Not interested", "Status", "Not interested", f'Exact text: "{STATUS_TEXT["Not interested"]}"'),
        (None, "Status", "Blank", "No fill"),
        ("Passing", "Score", "Above 23", "Numeric score is greater than 23."),
        ("NearPass", "Score", "21 to 23", "Numeric score is 21, 22, or 23."),
        ("N/A", "Score", "N/A", "Cell is N/A or NA."),
        (None, "Score", "Under 21", "No fill"),
    ]
    for offset, (color_key, column, label, rule) in enumerate(rows):
        excel_row = 5 + offset
        swatch = sheet.cell(excel_row, 1, label if color_key else "")
        if color_key:
            fill, font = _fill_font(color_key)
            swatch.fill = fill
            swatch.font = font
        else:
            swatch.font = BODY_FONT
        sheet.cell(excel_row, 2, column).font = BODY_FONT
        sheet.cell(excel_row, 3, label).font = Font(name="Calibri", bold=True, size=11)
        rule_cell = sheet.cell(excel_row, 4, rule)
        rule_cell.font = BODY_FONT
        rule_cell.alignment = WRAP
        for col in range(1, 5):
            sheet.cell(excel_row, col).alignment = WRAP
            sheet.cell(excel_row, col).border = THIN
        sheet.row_dimensions[excel_row].height = 36

    sheet.column_dimensions["A"].width = 28
    sheet.column_dimensions["B"].width = 14
    sheet.column_dimensions["C"].width = 28
    sheet.column_dimensions["D"].width = 88
    sheet.row_dimensions[1].height = 24
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    sheet.sheet_view.showGridLines = False
    sheet.oddHeader.left.text = "ASE candidate screen legend"
    sheet.freeze_panes = "A5"


def write_colored(source: Path, output: Path, names: list[str] | None) -> int:
    header, data = load_rows(source)
    chosen = select_rows(data, names)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "ASE"

    for col, value in enumerate(header, start=1):
        cell = sheet.cell(1, col, value)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = THIN
    sheet.row_dimensions[1].height = 32
    sheet.auto_filter.ref = f"A1:{get_column_letter(KEEP_COLS)}{len(chosen) + 1}"
    sheet.freeze_panes = "A2"

    widths = {
        1: 14,
        2: 28,
        3: 28,
        4: 42,
        5: 26,
        6: 18,
        7: 14,
        8: 16,
        9: 16,
        10: 28,
        11: 12,
        12: 42,
        13: 18,
        14: 42,
    }
    for col, width in widths.items():
        sheet.column_dimensions[get_column_letter(col)].width = width

    for row_index, values in enumerate(chosen, start=2):
        for col in range(1, KEEP_COLS + 1):
            value = values[col - 1] if col - 1 < len(values) else None
            cell = sheet.cell(row_index, col, value)
            cell.font = BODY_FONT
            cell.alignment = WRAP
            cell.border = THIN
        sheet.row_dimensions[row_index].height = 48

    sheet.cell(1, SCORE_COL).comment = Comment(
        "Above 23 is green. 21 to 23 is yellow. N/A is gray. Scores under 21 are not colored.",
        "ASE screen",
    )
    sheet.cell(1, STATUS_COL).comment = Comment(
        "Color comes from the Legend sheet.",
        "ASE screen",
    )

    last = max(len(chosen) + 1, 200)
    _add_rules(sheet, score_formulas("I2"), "I", last)
    _add_rules(sheet, status_formulas("N2"), "N", last)
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_TABLOID
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_view.showGridLines = False
    sheet.oddHeader.left.text = "ASE candidate screen"
    sheet.oddFooter.right.text = "Page &P of &N"
    sheet.print_title_rows = "1:1"
    sheet.page_setup.horizontalCentered = True
    sheet.sheet_properties.pageSetUpPr.fitToPage = True

    write_legend(workbook)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    return len(chosen)


def main() -> None:
    parser = argparse.ArgumentParser(description="Color an ASE candidate workbook and add a legend.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--names-file", type=Path)
    mode.add_argument("--all", action="store_true")
    args = parser.parse_args()
    names = None if args.all else read_names(args.names_file)
    count = write_colored(args.workbook, args.output, names)
    print(f"Wrote {count} candidates to {args.output}")


if __name__ == "__main__":
    main()
