#!/usr/bin/env python3
"""Compare dashboard in-memory snapshot (workbook + BIA merge via Node) vs exported xlsx."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
SNAPSHOT = DASH / ".dashboard_snapshot.json"


def run_dashboard_snapshot(workbook: Path) -> dict:
    js = r"""
const fs = require('fs');
const path = require('path');
const dash = process.argv[1];
const workbook = process.argv[2];
global.window = global;
global.document = { createElement: () => ({ style: {}, appendChild() {}, setAttribute() {} }) };
eval(fs.readFileSync(path.join(dash, 'vendor/xlsx.full.min.js'), 'utf8'));
eval(fs.readFileSync(path.join(dash, 'dashboard.bundle.js'), 'utf8'));
const buf = fs.readFileSync(workbook);
const parsed = SchemaDashboard.parseWorkbook(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
let rawData = parsed.json;
if (parsed.mode === 'checkback' && typeof BiaTemplate !== 'undefined') {
  rawData = BiaTemplate.mergePortfolioWithBia(rawData);
}
const allColumns = BiaTemplate.collectAllColumns(rawData);
const rows = rawData.map((row) => {
  const o = {};
  allColumns.forEach((c) => {
    if (c.startsWith('_')) return;
    const v = row[c];
    o[c] = v == null ? '' : (v instanceof Date ? v.toISOString().slice(0, 10) : v);
  });
  return o;
});
process.stdout.write(JSON.stringify({ mode: parsed.mode, columns: allColumns.filter(c => !c.startsWith('_')), rows }));
"""
    out = subprocess.run(
        ["node", "-e", js, str(DASH), str(workbook)],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(f"Node snapshot failed:\n{out.stderr}\n{out.stdout}")
    return json.loads(out.stdout)


def read_export_xlsx(path: Path) -> dict:
    js = r"""
const fs = require('fs');
const path = require('path');
const dash = process.argv[1];
const xlsxPath = process.argv[2];
eval(fs.readFileSync(path.join(dash, 'vendor/xlsx.full.min.js'), 'utf8'));
eval(fs.readFileSync(path.join(dash, 'dashboard.bundle.js'), 'utf8'));
const buf = fs.readFileSync(xlsxPath);
const wb = XLSX.read(buf, { type: 'buffer', cellDates: true });
const ws = wb.Sheets[wb.SheetNames[0]];
const headerRow = typeof SchemaDashboard !== 'undefined' ? (function(){
  const ref = XLSX.utils.decode_range(ws['!ref'] || 'A1');
  for (let r = ref.s.r; r <= Math.min(ref.s.r + 4, ref.e.r); r++) {
    for (let c = ref.s.c; c <= ref.e.c; c++) {
      const v = ws[XLSX.utils.encode_cell({ r, c })];
      if (v && String(v.v).trim() === 'Opportunity Name') return r;
    }
  }
  return 0;
})() : 0;
const rows = XLSX.utils.sheet_to_json(ws, { defval: '', range: headerRow });
const columns = rows.length ? Object.keys(rows[0]) : [];
process.stdout.write(JSON.stringify({ columns, rows }));
"""
    out = subprocess.run(
        ["node", "-e", js, str(DASH), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(f"Node read export failed:\n{out.stderr}\n{out.stdout}")
    return json.loads(out.stdout)


def norm_key(row: dict) -> str:
    name = str(row.get("Opportunity Name", "")).strip().lower()
    org = str(row.get("Customer org id", "")).strip().lower()
    return f"{name}|{org}"


def norm_val(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def diff_snapshots(current: dict, exported: dict) -> str:
    lines: list[str] = []
    cur_cols = set(current["columns"])
    exp_cols = set(exported["columns"])
    lines.append(f"Current dashboard rows: {len(current['rows'])} | Export rows: {len(exported['rows'])}")
    lines.append(f"Current columns: {len(cur_cols)} | Export columns: {len(exp_cols)}")

    only_cur = sorted(cur_cols - exp_cols)
    only_exp = sorted(exp_cols - cur_cols)
    if only_cur:
        lines.append(f"\nColumns only in dashboard ({len(only_cur)}):")
        for c in only_cur[:30]:
            lines.append(f"  - {c}")
        if len(only_cur) > 30:
            lines.append(f"  ... +{len(only_cur) - 30} more")
    if only_exp:
        lines.append(f"\nColumns only in export ({len(only_exp)}):")
        for c in only_exp[:30]:
            lines.append(f"  - {c}")
        if len(only_exp) > 30:
            lines.append(f"  ... +{len(only_exp) - 30} more")

    cur_map = {norm_key(r): r for r in current["rows"]}
    exp_map = {norm_key(r): r for r in exported["rows"]}
    common_cols = sorted(cur_cols & exp_cols)

    only_dashboard = sorted(set(cur_map) - set(exp_map))
    only_export = sorted(set(exp_map) - set(cur_map))
    if only_dashboard:
        lines.append(f"\nCustomers only in dashboard ({len(only_dashboard)}):")
        for k in only_dashboard[:15]:
            lines.append(f"  - {cur_map[k].get('Opportunity Name', k)}")
    if only_export:
        lines.append(f"\nCustomers only in export ({len(only_export)}):")
        for k in only_export[:15]:
            lines.append(f"  - {exp_map[k].get('Opportunity Name', k)}")

    value_diffs: list[tuple[str, str, str, str]] = []
    for key in sorted(set(cur_map) & set(exp_map)):
        cr, er = cur_map[key], exp_map[key]
        for col in common_cols:
            cv, ev = norm_val(cr.get(col)), norm_val(er.get(col))
            if cv != ev:
                name = str(cr.get("Opportunity Name", key))
                value_diffs.append((name, col, cv[:80], ev[:80]))

    lines.append(f"\nCell value differences (matched customers): {len(value_diffs)}")
    for name, col, cv, ev in value_diffs[:40]:
        lines.append(f"  {name} | {col}")
        lines.append(f"    dashboard: {cv!r}")
        lines.append(f"    export:    {ev!r}")
    if len(value_diffs) > 40:
        lines.append(f"  ... +{len(value_diffs) - 40} more differences")

    if not only_cur and not only_exp and not only_dashboard and not only_export and not value_diffs:
        lines.append("\n✓ Export matches current dashboard snapshot (rows, columns, values).")

    return "\n".join(lines)


def main() -> int:
    workbook = Path(sys.argv[1]) if len(sys.argv) > 1 else DASH / "check_back_default.xlsx"
    export_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not workbook.is_file():
        print(f"Workbook not found: {workbook}", file=sys.stderr)
        return 1

    print(f"Building dashboard snapshot from: {workbook}")
    current = run_dashboard_snapshot(workbook)
    SNAPSHOT.write_text(json.dumps(current, indent=2, default=str))

    if export_path is None:
        # Search common locations
        candidates = list(DASH.glob("*from_dashboard*.xlsx"))
        candidates += list(ROOT.glob("**/*from_dashboard*.xlsx"))
        candidates = [p for p in candidates if p.is_file()]
        if not candidates:
            print("No export file path given and no *from_dashboard*.xlsx found in project.")
            print(f"Snapshot saved to {SNAPSHOT} ({len(current['rows'])} rows, {len(current['columns'])} cols)")
            return 2
        export_path = candidates[0]

    if not export_path.is_file():
        print(f"Export not found: {export_path}", file=sys.stderr)
        return 1

    print(f"Reading export: {export_path}")
    exported = read_export_xlsx(export_path)
    report = diff_snapshots(current, exported)
    print(report)
    out_report = DASH / "export_diff_report.txt"
    out_report.write_text(report)
    print(f"\nReport written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
