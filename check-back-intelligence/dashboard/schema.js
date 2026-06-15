/**
 * Schema detection and spreadsheet parsing for Check Back / Renewal / Generic modes.
 */
const SchemaDashboard = (function () {
  const CHECKBACK_MARKERS = ['Entitled Lic Calling', 'Providioned Lic Calling', ' (G/Y/R)'];
  const RENEWAL_MARKERS = ['Collab AOV', 'Renewal Fiscal Qtr'];

  function detectMode(columns) {
    const cols = columns.map((c) => String(c).trim());
    if (CHECKBACK_MARKERS.some((m) => cols.includes(m))) return 'checkback';
    if (RENEWAL_MARKERS.every((m) => cols.includes(m))) return 'renewal';
    return 'generic';
  }

  function isCheckBackSectionRow(ws) {
    const ref = XLSX.utils.decode_range(ws['!ref'] || 'A1');
    if (ref.e.r < 1) return false;
    const row1 = [];
    for (let c = ref.s.c; c <= ref.e.c; c++) {
      const addr = XLSX.utils.encode_cell({ r: 0, c });
      row1.push((ws[addr] && ws[addr].v) || '');
    }
    const text = row1.join(' ').toLowerCase();
    return (
      text.includes('success portal') ||
      text.includes('control hub') ||
      (row1.filter((v) => v !== '').length < 8 && row1.some((v) => String(v).includes('Portal')))
    );
  }

  function rowCellValues(ws, rowIdx) {
    const ref = XLSX.utils.decode_range(ws['!ref'] || 'A1');
    const vals = [];
    for (let c = ref.s.c; c <= ref.e.c; c++) {
      const addr = XLSX.utils.encode_cell({ r: rowIdx, c });
      const v = ws[addr] && ws[addr].v;
      vals.push(v == null ? '' : String(v).trim());
    }
    return vals;
  }

  function detectHeaderRow(ws) {
    const ref = XLSX.utils.decode_range(ws['!ref'] || 'A1');
    const maxScan = Math.min(ref.e.r, 5);
    for (let r = 0; r <= maxScan; r++) {
      const cols = rowCellValues(ws, r).filter(Boolean);
      if (!cols.length) continue;
      if (cols.includes('Opportunity Name')) return r;
      if (CHECKBACK_MARKERS.some((m) => cols.includes(m))) return r;
      if (RENEWAL_MARKERS.every((m) => cols.includes(m))) return r;
    }
    if (isCheckBackSectionRow(ws)) return 1;
    return 0;
  }

  function sheetToJson(wb) {
    const ws = wb.Sheets[wb.SheetNames[0]];
    const range = detectHeaderRow(ws);
    return XLSX.utils.sheet_to_json(ws, { defval: '', range });
  }

  function parseWorkbook(arrayBuffer) {
    const wb = XLSX.read(arrayBuffer, { type: 'array', cellDates: true });
    const json = sheetToJson(wb);
    if (!json.length) return { json: [], mode: 'generic', columns: [] };
    const columns = Object.keys(json[0]);
    const mode = detectMode(columns);
    return { json, mode, columns };
  }

  function getTableSection() {
    return (
      document.querySelector('#portfolioTableMount .table-section') ||
      document.querySelector('#tab-datatable .table-section')
    );
  }

  function movePortfolioTable(mode) {
    const tableSection = getTableSection();
    const adoptionTab = document.getElementById('tab-adoption');
    const datatableTab = document.getElementById('tab-datatable');
    if (!tableSection || !adoptionTab || !datatableTab) return;

    let mount = document.getElementById('portfolioTableMount');
    if (mode === 'checkback') {
      if (!mount) {
        mount = document.createElement('div');
        mount.id = 'portfolioTableMount';
        mount.className = 'portfolio-table-mount';
        const panel = document.getElementById('customerPortfolioPanel') || adoptionTab;
        panel.insertBefore(mount, panel.firstChild);
      }
      if (tableSection.parentElement !== mount) mount.appendChild(tableSection);
      const titleEl = tableSection.querySelector('.table-title');
      if (titleEl) {
        titleEl.innerHTML =
          '📋 Customer Portfolio <span style="font-size:12px;color:var(--text-muted);font-weight:400;">— spreadsheet + Lookback slides in one list · click name for Business Insight view</span>';
      }
      const chartsWrap = document.getElementById('checkbackChartsWrap');
      if (chartsWrap) chartsWrap.style.display = '';
    } else {
      if (tableSection.parentElement !== datatableTab) datatableTab.appendChild(tableSection);
      const titleEl = tableSection.querySelector('.table-title');
      if (titleEl) {
        titleEl.innerHTML =
          '📋 Full Data Table <span style="font-size:12px;color:var(--text-muted);font-weight:400;">— Click any row for full record detail</span>';
      }
    }
  }

  function applyModeUI(mode) {
    window.dashboardMode = mode;
    const badge = document.getElementById('modeBadge');
    if (badge) {
      const labels = {
        checkback: 'Check Back / Adoption',
        renewal: 'Renewal Intelligence',
        generic: 'Generic Data',
      };
      badge.textContent = labels[mode] || mode;
    }

    document.querySelectorAll('.tab').forEach((tab) => {
      const id = tab.dataset.tab;
      if (!id) return;
      if (mode === 'checkback') {
        tab.style.display = id === 'adoption' ? '' : 'none';
        if (id === 'adoption') tab.textContent = '📋 Customer Portfolio';
      } else if (mode === 'renewal') {
        tab.style.display = id === 'adoption' ? 'none' : '';
        if (id === 'adoption') tab.textContent = '🚦 Adoption Health';
      } else {
        tab.style.display = id === 'adoption' ? 'none' : id === 'datatable' || id === 'overview' ? '' : 'none';
        if (id === 'adoption') tab.textContent = '🚦 Adoption Health';
      }
    });

    document.querySelectorAll('.tab-content').forEach((el) => {
      const id = el.id.replace('tab-', '');
      if (mode === 'checkback' && id !== 'adoption') {
        el.classList.remove('active');
      }
    });

    if (mode === 'checkback') {
      movePortfolioTable('checkback');
      const adoptTab = document.querySelector('.tab[data-tab="adoption"]');
      const adoptContent = document.getElementById('tab-adoption');
      if (adoptTab && adoptContent) {
        document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach((t) => t.classList.remove('active'));
        adoptTab.classList.add('active');
        adoptContent.classList.add('active');
      }
    } else {
      movePortfolioTable('renewal');
    }
  }

  return { detectMode, parseWorkbook, applyModeUI, sheetToJson, isCheckBackSectionRow };
})();
