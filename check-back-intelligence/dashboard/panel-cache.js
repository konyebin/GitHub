/**
 * Subscription Review / Provisioning / Feature Use sidecar xlsx (mirrors src/workbook/panel_cache.py).
 */
const PanelCache = (function () {
  const MATCH_KEYS = ['Opportunity Name', 'Customer org id'];

  const PANEL_COLUMN_LIST = [
    ['Opportunity Name', 'Keys'],
    ['Customer org id', 'Keys'],
    ['Sub #', 'Subscription Review'],
    ['TCV $', 'Subscription Review'],
    ['AAR $', 'Subscription Review'],
    ['Partner', 'Subscription Review'],
    ['SL2', 'Subscription Review'],
    ['Collab AE/SE', 'Subscription Review'],
    ['Platforms', 'Subscription Review'],
    ['Service lines', 'Subscription Review'],
    ['Sub term (months)', 'Subscription Review'],
    ['Subscription dates', 'Subscription Review'],
    ['Trend active users 90d', 'Subscription Review'],
    ['Trend call volume 90d', 'Subscription Review'],
    ['Salesforce URL', 'Subscription Review'],
    ['Provisioned/Entitled Lic Calling', 'Provisioning & Usage'],
    ['Entitled Lic Calling', 'Provisioning & Usage'],
    ['Providioned Lic Calling', 'Provisioning & Usage'],
    ['Active Lic Calling', 'Provisioning & Usage'],
    ['Notes from Calling Analytics', 'Provisioning & Usage'],
    ['Notes from provisioned features', 'Provisioning & Usage'],
    ['Lic Professional (used/entitled)', 'Provisioning & Usage'],
    ['Lic Standard (used/entitled)', 'Provisioning & Usage'],
    ['Lic Workspace (used/entitled)', 'Provisioning & Usage'],
    ['Active % of provisioned', 'Provisioning & Usage'],
    ['External calls', 'Provisioning & Usage'],
    ['Meetings usage', 'Provisioning & Usage'],
    ['Messaging usage', 'Provisioning & Usage'],
    ['Total calls', 'Provisioning & Usage'],
    ['Answered calls %', 'Provisioning & Usage'],
    ['Calls busiest hour', 'Provisioning & Usage'],
    ['Add-ons included or not', 'Feature Use & Add-ons'],
    ['Auto Attendant count', 'Feature Use & Add-ons'],
    ['Hunt Groups count', 'Feature Use & Add-ons'],
    ['Call Queues count', 'Feature Use & Add-ons'],
    ['Connected-UC (Y/N)', 'Feature Use & Add-ons'],
    ['Virtual Lines count', 'Feature Use & Add-ons'],
  ];

  const PANEL_FIELDS = PANEL_COLUMN_LIST.map(([name]) => name).filter((n) => !MATCH_KEYS.includes(n));

  function norm(s) {
    return String(s ?? '').trim().toLowerCase();
  }

  function rowKey(row) {
    return norm(row['Opportunity Name']) + '|' + norm(row['Customer org id']);
  }

  function detectHeaderRow(ws) {
    const ref = XLSX.utils.decode_range(ws['!ref'] || 'A1');
    for (let r = ref.s.r; r <= Math.min(ref.s.r + 4, ref.e.r); r++) {
      for (let c = ref.s.c; c <= ref.e.c; c++) {
        const v = ws[XLSX.utils.encode_cell({ r, c })];
        if (v && String(v.v).trim() === 'Opportunity Name') return r;
      }
    }
    return 1;
  }

  function sheetToRows(wb) {
    const ws = wb.Sheets[wb.SheetNames[0]];
    const headerRow = detectHeaderRow(ws);
    const json = XLSX.utils.sheet_to_json(ws, { defval: '', range: headerRow });
    return json.filter((row) => Object.values(row).some((v) => String(v).trim() !== ''));
  }

  function rowsToAoA(rows) {
    const sections = [];
    const headers = [];
    const seen = new Set();
    PANEL_COLUMN_LIST.forEach(([name, section]) => {
      sections.push(seen.has(section) ? '' : section);
      seen.add(section);
      headers.push(name);
    });
    const body = rows.map((row) => PANEL_COLUMN_LIST.map(([name]) => row[name] ?? ''));
    return [sections, headers, ...body];
  }

  function exportFilenameFromDisplay(displayName) {
    const base = String(displayName || 'check_back').replace(/\.xlsx?$/i, '');
    return base + '_panels.xlsx';
  }

  function exportFromRows(rows, displayName) {
    if (typeof XLSX === 'undefined') throw new Error('Spreadsheet library not loaded');
    if (!rows || !rows.length) throw new Error('No customer rows to export');
    const outRows = rows.map((src) => {
      const o = {};
      PANEL_COLUMN_LIST.forEach(([name]) => {
        o[name] = src[name] ?? '';
      });
      return o;
    });
    const ws = XLSX.utils.aoa_to_sheet(rowsToAoA(outRows));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Panel Data');
    XLSX.writeFile(wb, exportFilenameFromDisplay(displayName));
  }

  function parseFile(arrayBuffer) {
    if (typeof XLSX === 'undefined') throw new Error('Spreadsheet library not loaded');
    const wb = XLSX.read(arrayBuffer, { type: 'array', cellDates: true });
    return sheetToRows(wb);
  }

  function mergeIntoRows(mainRows, panelRows) {
    const byKey = new Map();
    const byName = new Map();
    panelRows.forEach((row) => {
      const k = rowKey(row);
      if (k !== '|') byKey.set(k, row);
      const n = norm(row['Opportunity Name']);
      if (n) byName.set(n, row);
    });

    let matched = 0;
    const merged = mainRows.map((main) => {
      const k = rowKey(main);
      let panel = byKey.get(k);
      if (!panel && norm(main['Opportunity Name'])) {
        panel = byName.get(norm(main['Opportunity Name']));
      }
      if (!panel) return { ...main };
      matched += 1;
      const out = { ...main };
      PANEL_FIELDS.forEach((field) => {
        const val = panel[field];
        if (val !== undefined && val !== null && String(val).trim() !== '') {
          out[field] = val;
        }
      });
      return out;
    });
    return { rows: merged, matched };
  }

  return {
    PANEL_COLUMN_LIST,
    exportFromRows,
    parseFile,
    mergeIntoRows,
    exportFilenameFromDisplay,
  };
})();
