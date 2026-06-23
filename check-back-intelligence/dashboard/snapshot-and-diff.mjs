#!/usr/bin/env node
/**
 * Build dashboard in-memory snapshot (workbook + BIA merge) and optionally diff vs export xlsx.
 * Usage: node snapshot-and-diff.mjs [workbook] [export.xlsx]
 */
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dash = __dirname;
const workbook = path.resolve(process.argv[2] || path.join(dash, 'check_back_default.xlsx'));
const exportPath = process.argv[3] ? path.resolve(process.argv[3]) : null;

const files = [
  'vendor/xlsx.full.min.js',
  'schema.js',
  'checkback-charts.js',
  'bia-match-aliases.js',
  'bia-slides.js',
  'lib/namespace.js',
  'lib/constants.js',
  'lib/bia-sanitize.js',
  'lib/html-utils.js',
  'lib/note-parser.js',
  'lib/license-products.js',
  'lib/bia-slide-matcher.js',
  'lib/bia-workbook-mapper.js',
  'lib/bia-portfolio.js',
  'lib/bia-slide-merger.js',
  'lib/bia-slide-renderer.js',
  'bia-template.js',
  'account-insight.js',
  'panel-cache.js',
  'dashboard-export.js',
];

const ctx = { console, Buffer, fs, setTimeout, clearTimeout, path };
ctx.window = ctx;
ctx.document = { createElement: () => ({ style: {}, appendChild() {}, setAttribute() {} }) };
vm.createContext(ctx);

const bootstrap = `
${files.map((f) => fs.readFileSync(path.join(dash, f), 'utf8')).join('\n')}
XLSX.writeFile = function(wb, name) {
  const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
  fs.writeFileSync(name, buf);
};
function dashboardSnapshot(workbookPath) {
  const buf = fs.readFileSync(workbookPath);
  const parsed = SchemaDashboard.parseWorkbook(buf);
  let rawData = BiaTemplate.mergePortfolioWithBia(parsed.json);
  const allColumns = BiaTemplate.collectAllColumns(rawData);
  const cols = allColumns.filter((c) => !c.startsWith('_'));
  const rows = rawData.map((r) => {
    const o = {};
    cols.forEach((c) => {
      let v = r[c];
      if (v == null) v = '';
      else if (v instanceof Date) v = v.toISOString().slice(0, 10);
      o[c] = v;
    });
    return o;
  });
  return { mode: parsed.mode, wbRows: parsed.json.length, dashRows: rawData.length, columns: cols, rows };
}
function readExportXlsx(p) {
  const buf = fs.readFileSync(p);
  const wb = XLSX.read(buf, { type: 'buffer', cellDates: true });
  const ws = wb.Sheets[wb.SheetNames[0]];
  const ref = XLSX.utils.decode_range(ws['!ref'] || 'A1');
  let headerRow = 0;
  for (let r = ref.s.r; r <= Math.min(ref.s.r + 4, ref.e.r); r++) {
    for (let c = ref.s.c; c <= ref.e.c; c++) {
      const v = ws[XLSX.utils.encode_cell({ r, c })];
      if (v && String(v.v).trim() === 'Opportunity Name') { headerRow = r; break; }
    }
  }
  const rows = XLSX.utils.sheet_to_json(ws, { defval: '', range: headerRow });
  const columns = rows.length ? Object.keys(rows[0]) : [];
  return { columns, rows };
}
`;

vm.runInContext(bootstrap, ctx);

const snap = vm.runInContext(`dashboardSnapshot(${JSON.stringify(workbook)})`, ctx);
const snapshotPath = path.join(dash, '.dashboard_snapshot.json');
fs.writeFileSync(snapshotPath, JSON.stringify({ columns: snap.columns, rows: snap.rows }, null, 2));

console.log('=== Current dashboard snapshot ===');
console.log(`Workbook: ${workbook}`);
console.log(`Mode: ${snap.mode}`);
console.log(`Rows in workbook file: ${snap.wbRows}`);
console.log(`Rows after BIA merge (dashboard table): ${snap.dashRows}`);
console.log(`Columns: ${snap.columns.length}`);
console.log(`Snapshot: ${snapshotPath}`);

function normKey(row) {
  const name = String(row['Opportunity Name'] ?? '').trim().toLowerCase();
  const org = String(row['Customer org id'] ?? '').trim().toLowerCase();
  return `${name}|${org}`;
}
function normVal(v) {
  if (v == null) return '';
  if (typeof v === 'number' && Number.isFinite(v)) return String(v);
  return String(v).trim();
}

function diff(current, exported, label) {
  const curCols = new Set(current.columns);
  const expCols = new Set(exported.columns);
  console.log(`\n=== Diff vs ${label} ===`);
  console.log(`Dashboard rows: ${current.rows.length} | Export rows: ${exported.rows.length}`);
  console.log(`Dashboard cols: ${curCols.size} | Export cols: ${expCols.size}`);

  const onlyCur = [...curCols].filter((c) => !expCols.has(c)).sort();
  const onlyExp = [...expCols].filter((c) => !curCols.has(c)).sort();
  if (onlyCur.length) {
    console.log(`Columns only in dashboard (${onlyCur.length}):`, onlyCur.slice(0, 20).join(', '), onlyCur.length > 20 ? '...' : '');
  }
  if (onlyExp.length) {
    console.log(`Columns only in export (${onlyExp.length}):`, onlyExp.slice(0, 20).join(', '), onlyExp.length > 20 ? '...' : '');
  }

  const curMap = Object.fromEntries(current.rows.map((r) => [normKey(r), r]));
  const expMap = Object.fromEntries(exported.rows.map((r) => [normKey(r), r]));
  const onlyDash = Object.keys(curMap).filter((k) => !expMap[k]);
  const onlyExpRows = Object.keys(expMap).filter((k) => !curMap[k]);
  if (onlyDash.length) console.log(`Customers only in dashboard (${onlyDash.length}):`, onlyDash.slice(0, 10).map((k) => curMap[k]['Opportunity Name']));
  if (onlyExpRows.length) console.log(`Customers only in export (${onlyExpRows.length}):`, onlyExpRows.slice(0, 10).map((k) => expMap[k]['Opportunity Name']));

  const commonCols = [...curCols].filter((c) => expCols.has(c));
  const diffs = [];
  for (const key of Object.keys(curMap)) {
    if (!expMap[key]) continue;
    const cr = curMap[key];
    const er = expMap[key];
    for (const col of commonCols) {
      const cv = normVal(cr[col]);
      const ev = normVal(er[col]);
      if (cv !== ev) diffs.push({ name: cr['Opportunity Name'], col, cv, ev });
    }
  }
  console.log(`Cell value differences: ${diffs.length}`);
  diffs.slice(0, 25).forEach((d) => {
    console.log(`  ${d.name} | ${d.col}`);
    console.log(`    dashboard: ${d.cv}`);
    console.log(`    export:    ${d.ev}`);
  });
  if (diffs.length > 25) console.log(`  ... +${diffs.length - 25} more`);

  if (!onlyCur.length && !onlyExp.length && !onlyDash.length && !onlyExpRows.length && !diffs.length) {
    console.log('✓ Perfect match');
  }
  return { onlyCur, onlyExp, onlyDash, onlyExpRows, diffs };
}

// Round-trip: write export from snapshot and re-read
const syntheticExport = path.join(dash, 'check_back_default_from_dashboard.xlsx');
vm.runInContext(`
  const snap = dashboardSnapshot(${JSON.stringify(workbook)});
  const ws = XLSX.utils.json_to_sheet(snap.rows, { header: snap.columns });
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Customer Data');
  XLSX.writeFile(wb, ${JSON.stringify(syntheticExport)});
`, ctx);
const synthetic = vm.runInContext(`readExportXlsx(${JSON.stringify(syntheticExport)})`, ctx);
diff({ columns: snap.columns, rows: snap.rows }, synthetic, 'synthetic round-trip export');

// Raw workbook (no BIA merge) for reference
const rawOnly = vm.runInContext(`
  (function() {
    const buf = fs.readFileSync(${JSON.stringify(workbook)});
    const parsed = SchemaDashboard.parseWorkbook(buf);
    const cols = Object.keys(parsed.json[0] || {});
    return { columns: cols, rows: parsed.json };
  })()
`, ctx);
diff({ columns: snap.columns, rows: snap.rows }, rawOnly, 'raw workbook file (no BIA merge)');

let exportFile = exportPath;
if (!exportFile) {
  const candidates = fs.readdirSync(dash).filter((f) => f.includes('from_dashboard') && f.endsWith('.xlsx'));
  if (candidates.length) exportFile = path.join(dash, candidates[0]);
}
if (exportFile && fs.existsSync(exportFile)) {
  const exported = vm.runInContext(`readExportXlsx(${JSON.stringify(exportFile)})`, ctx);
  diff({ columns: snap.columns, rows: snap.rows }, exported, exportFile);
} else {
  console.log('\n=== User export file ===');
  console.log('No *from_dashboard*.xlsx found in dashboard folder.');
  console.log('Copy your downloaded export here or run:');
  console.log(`  node snapshot-and-diff.mjs "${workbook}" /path/to/your_export.xlsx`);
}
