/* auto-generated — run ./build-bundle.sh after editing local dashboard modules */
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

  function sheetToJson(wb) {
    const ws = wb.Sheets[wb.SheetNames[0]];
    let range = 0;
    if (isCheckBackSectionRow(ws)) range = 1;
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
/**
 * Check Back / adoption health KPIs, filters, and charts.
 */
const CheckBackDashboard = (function () {
  const GYR_COL = ' (G/Y/R)';
  const GYR_COLORS = { G: '#00d4a0', Y: '#fbbf24', R: '#ef4444', '': '#64748b' };
  const FILTER_COLUMNS = [
    'Partner',
    'Migrating from',
    'Migrating to',
    'CSM name',
    'Calling Setup Assist included (Y/N)',
    'CCEP trial (Y/N)',
    GYR_COL,
  ];
  const PORTFOLIO_COLS = [
    'Opportunity Name',
    GYR_COL,
    'Partner',
    'SL2',
    'TCV $',
    'Sub #',
    'Entitled Lic Calling',
    'Providioned Lic Calling',
    'Active Lic Calling',
    'CSM name',
    'Migrating from',
    'Migrating to',
  ];
  const DRILL_COLS = [
    'Opportunity Name',
    'TCV $',
    GYR_COL,
    'Entitled Lic Calling',
    'Providioned Lic Calling',
    'Active Lic Calling',
    'Partner',
    'Customer org id',
    'Migrating from',
    'Migrating to',
    'Sub #',
    'CSM name',
  ];
  const HIGHLIGHT = new Set([
    'Opportunity Name',
    'Entitled Lic Calling',
    'Providioned Lic Calling',
    'Active Lic Calling',
    GYR_COL,
    'Customer org id',
  ]);

  function parseLicenseNumbers(val) {
    if (val === null || val === undefined || val === '') return 0;
    const s = String(val);
    const nums = s.match(/[\d,]+/g);
    if (!nums) return 0;
    return Math.max(...nums.map((n) => parseFloat(n.replace(/,/g, '')) || 0));
  }

  function getGyrBadge(val) {
    const v = String(val || '').trim().toUpperCase().charAt(0);
    if (v === 'G') return `<span class="badge badge-low">G</span>`;
    if (v === 'Y') return `<span class="badge badge-medium">Y</span>`;
    if (v === 'R') return `<span class="badge badge-high">R</span>`;
    return val || '';
  }

  function buildFilters() {
    const grid = document.getElementById('filtersGrid');
    grid.innerHTML = '';
    const sd = document.createElement('div');
    sd.className = 'filter-group';
    sd.innerHTML = `<label class="filter-label">Opportunity Search</label><input class="search-input" placeholder="Opportunity Name..." id="acctSearch" oninput="applyFilters()">`;
    grid.appendChild(sd);
    FILTER_COLUMNS.forEach((col) => {
      if (!allColumns.includes(col)) return;
      const vals = [...new Set(rawData.map((r) => r[col]).filter((v) => v !== ''))].sort();
      if (vals.length < 2) return;
      const div = document.createElement('div');
      div.className = 'filter-group';
      div.innerHTML = `<label class="filter-label">${col}</label>
        <select class="filter-select" data-col="${col}" onchange="applyFilters()">
        <option value="">All</option>${vals.map((v) => `<option value="${v}">${v}</option>`).join('')}
        </select>`;
      grid.appendChild(div);
    });
  }

  function applyFiltersAccountKey(row, acct) {
    const key = row['Opportunity Name'] || row['Account Name'] || '';
    return !acct || String(key).toLowerCase().includes(acct);
  }

  function buildKPIs() {
    const d = filteredData;
    let totalEnt = 0;
    let totalProv = 0;
    let totalAct = 0;
    let gapAccounts = 0;
    d.forEach((r) => {
      const e = parseLicenseNumbers(r['Entitled Lic Calling']);
      const p = parseLicenseNumbers(r['Providioned Lic Calling']);
      const a = parseLicenseNumbers(r['Active Lic Calling']);
      totalEnt += e;
      totalProv += p;
      totalAct += a;
      if (e > 0 && (p < e * 0.9 || a < p * 0.5)) gapAccounts++;
    });
    const gyr = countBy(d, GYR_COL);
    const red = gyr['R'] || gyr['r'] || 0;
    const yellow = gyr['Y'] || gyr['y'] || 0;
    const green = gyr['G'] || gyr['g'] || 0;
    const noSetup = d.filter(
      (r) => String(r['Calling Setup Assist included (Y/N)'] || '').toUpperCase() === 'N'
    ).length;
    const adoptionPct = totalEnt ? Math.round((totalAct / totalEnt) * 100) : 0;

    const kpis = [
      {
        label: 'Total Opportunities',
        val: d.length.toLocaleString(),
        sub: `${new Set(d.map((r) => r['Opportunity Name']).filter(Boolean)).size} accounts`,
        icon: '📋',
        color: 'blue',
        drill: { col: null, val: null },
      },
      {
        label: 'Adoption Rate',
        val: adoptionPct + '%',
        sub: `Active / Entitled (${fmtNum(totalAct)} / ${fmtNum(totalEnt)})`,
        icon: '📈',
        color: 'green',
        drill: { col: null, val: null },
      },
      {
        label: 'License Gap Accounts',
        val: gapAccounts.toLocaleString(),
        sub: 'Provisioned or active below entitled',
        icon: '⚠️',
        color: 'orange',
        drill: { col: null, val: null },
      },
      {
        label: 'G / Y / R',
        val: `${green} / ${yellow} / ${red}`,
        sub: 'Health distribution',
        icon: '🚦',
        color: 'yellow',
        drill: { col: GYR_COL, val: 'R' },
      },
      {
        label: 'No Setup Assist',
        val: noSetup.toLocaleString(),
        sub: 'Calling Setup Assist = N',
        icon: '🛠️',
        color: 'purple',
        drill: { col: 'Calling Setup Assist included (Y/N)', val: 'N' },
      },
      {
        label: 'Total TCV',
        val: fmt(sum(d, 'TCV $')),
        sub: 'Sum of deal values',
        icon: '💰',
        color: 'cyan',
        drill: { col: null, val: null },
      },
    ];
    document.getElementById('kpiGrid').innerHTML = kpis
      .map(
        (k, i) => `
    <div class="kpi-card ${k.color}" onclick="openDrillFromKPI(${i})" style="cursor:pointer;">
      <div class="kpi-drill-hint">🔍 Click to drill</div>
      <div class="kpi-icon">${k.icon}</div>
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.val}</div>
      <div class="kpi-sub">${k.sub}</div>
      <div class="kpi-bg-icon">${k.icon}</div>
    </div>`
      )
      .join('');
    window._kpiDefs = kpis;
  }

  function buildAllCharts() {
    const d = filteredData;
    buildGyrChart(d);
    buildLicenseGapChart(d);
    buildMigrationChart(d);
    buildPartnerChart(d);
    buildTrialChart(d);
  }

  function buildGyrChart(d) {
    const gyr = countBy(d, GYR_COL);
    const labels = ['G', 'Y', 'R', ''].filter((k) => gyr[k] || gyr[k.toLowerCase()]);
    const data = labels.map((k) => Math.round(gyr[k] || gyr[k.toLowerCase()] || 0));
    const colors = labels.map((k) => GYR_COLORS[k] || '#64748b');
    makeChart(
      'cbGyrChart',
      'doughnut',
      labels.length ? labels : ['Unknown'],
      [
        {
          data: data.length ? data : [d.length],
          backgroundColor: colors.map((c) => c + 'cc'),
          borderColor: colors,
          borderWidth: 2,
        },
      ],
      { plugins: { legend: { position: 'right' } } },
      { col: GYR_COL, tabName: 'Adoption' }
    );
  }

  function buildLicenseGapChart(d) {
    const labels = d.slice(0, 12).map((r) => String(r['Opportunity Name'] || '?').substring(0, 18));
    const entitled = d.slice(0, 12).map((r) => parseLicenseNumbers(r['Entitled Lic Calling']));
    const prov = d.slice(0, 12).map((r) => parseLicenseNumbers(r['Providioned Lic Calling']));
    const active = d.slice(0, 12).map((r) => parseLicenseNumbers(r['Active Lic Calling']));
    makeChart(
      'cbLicenseChart',
      'bar',
      labels,
      [
        { label: 'Entitled', data: entitled, backgroundColor: '#00bcebcc', borderRadius: 4 },
        { label: 'Provisioned', data: prov, backgroundColor: '#7c3aedcc', borderRadius: 4 },
        { label: 'Active', data: active, backgroundColor: '#00d4a0cc', borderRadius: 4 },
      ],
      {
        plugins: { legend: { position: 'top' } },
        scales: { x: { stacked: false }, y: { beginAtZero: true } },
      },
      { col: 'Opportunity Name', tabName: 'Adoption' }
    );
  }

  function buildMigrationChart(d) {
    const paths = {};
    d.forEach((r) => {
      const from = String(r['Migrating from'] || '?');
      const to = String(r['Migrating to'] || '?');
      const k = `${from} → ${to}`;
      paths[k] = (paths[k] || 0) + 1;
    });
    const top = topN(paths, 8);
    makeChart(
      'cbMigrationChart',
      'bar',
      top.map((x) => x[0]),
      [{ label: 'Count', data: top.map((x) => x[1]), backgroundColor: CC.map((c) => c + 'cc'), borderRadius: 6 }],
      { indexAxis: 'y', plugins: { legend: { display: false } } },
      { col: 'Migrating from', tabName: 'Adoption' }
    );
  }

  function buildPartnerChart(d) {
    const p = cleanTopN(countBy(d, 'Partner'), 10);
    makeChart(
      'cbPartnerChart',
      'doughnut',
      p.map((x) => x[0]),
      [{ data: p.map((x) => x[1]), backgroundColor: CC.map((c) => c + 'cc'), borderColor: CC, borderWidth: 2 }],
      {},
      { col: 'Partner', tabName: 'Adoption' }
    );
  }

  function buildTrialChart(d) {
    const t = countBy(d, 'CCEP trial (Y/N)');
    makeChart(
      'cbTrialChart',
      'bar',
      Object.keys(t),
      [
        {
          label: 'Count',
          data: Object.values(t).map((v) => Math.round(v)),
          backgroundColor: CC.map((c) => c + 'cc'),
          borderRadius: 6,
        },
      ],
      { plugins: { legend: { display: false } } },
      { col: 'CCEP trial (Y/N)', tabName: 'Adoption' }
    );
  }

  function buildInsights() {
    const el = document.getElementById('adoptionInsights');
    if (!el) return;
    el.innerHTML = '';
  }

  function getDrillCols() {
    return DRILL_COLS.filter((c) => allColumns.includes(c));
  }

  const WEBEX_ORG_ADMIN_PREFIX = 'https://admin.webex.com/help-desk/org/';

  function webexOrgLinkHtml(val) {
    const id = String(val ?? '').trim();
    if (!id || id === '—') return '';
    const href = WEBEX_ORG_ADMIN_PREFIX + encodeURIComponent(id);
    const u = href.replace(/"/g, '&quot;');
    const l = id.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<a href="${u}" target="_blank" rel="noopener noreferrer" class="customer-link" onclick="event.stopPropagation()">${l}</a>`;
  }

  function salesforceLinkHtml(row, col) {
    if (!row || (col !== 'Opportunity (linked)' && col !== 'CSM Engagement Model (linked)')) return '';
    let href = String(row['Salesforce URL'] || '').trim();
    if (!href && row[col] && String(row[col]).trim().startsWith('http')) href = String(row[col]).trim();
    if (!href) return '';
    const raw = row[col];
    const label =
      raw && !String(raw).startsWith('http')
        ? String(raw)
        : col === 'Opportunity (linked)'
          ? 'Salesforce'
          : 'Success Portal';
    const u = href.replace(/"/g, '&quot;');
    const l = label.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<a href="${u}" target="_blank" rel="noopener noreferrer" class="customer-link" onclick="event.stopPropagation()">${l}</a>`;
  }

  function formatCell(col, val, row) {
    if (col === 'Customer org id') {
      const link = webexOrgLinkHtml(val);
      if (link) return link;
    }
    if (row && (col === 'Opportunity (linked)' || col === 'CSM Engagement Model (linked)')) {
      const link = salesforceLinkHtml(row, col);
      if (link) return link;
    }
    if (col === GYR_COL) return getGyrBadge(val);
    if (['Entitled Lic Calling', 'Providioned Lic Calling', 'Active Lic Calling', 'TCV $', 'AAR $'].includes(col)) {
      const n = col === 'TCV $' || col === 'AAR $' ? numVal(val) : parseLicenseNumbers(val);
      return col === 'TCV $' || col === 'AAR $' ? fmt(n) : fmtNum(n);
    }
    return val;
  }

  function rowDetailFields() {
    const pri = [
      'Opportunity Name',
      'TCV $',
      GYR_COL,
      'Entitled Lic Calling',
      'Providioned Lic Calling',
      'Active Lic Calling',
      'Customer org id',
      'Partner',
      'Migrating from',
      'Migrating to',
      'Sub #',
      'CSM name',
      'Notes from Calling Analytics',
      'Notes from provisioned features',
      'TAC/BEMS',
    ];
    const other = allColumns.filter((c) => !pri.includes(c));
    return [...pri.filter((c) => allColumns.includes(c)), ...other];
  }

  function attachmentKey(row) {
    return row['Customer org id'] || row['Opportunity Name'] || 'unknown';
  }

  function saveAttachment(key, fileName) {
    const store = JSON.parse(sessionStorage.getItem('cb_attachments') || '{}');
    store[key] = store[key] || [];
    if (!store[key].includes(fileName)) store[key].push(fileName);
    sessionStorage.setItem('cb_attachments', JSON.stringify(store));
  }

  function getAttachments(key) {
    const store = JSON.parse(sessionStorage.getItem('cb_attachments') || '{}');
    return store[key] || [];
  }

  function renderAttachmentUI(row) {
    const key = attachmentKey(row);
    const files = getAttachments(key);
    return `
      <div class="row-detail-field" style="grid-column:1/-1;">
        <div class="row-detail-field-label">Screenshot attachments</div>
        <div class="row-detail-field-value">
          <input type="file" accept="image/*" multiple onchange="CheckBackDashboard.onAttachmentChange(event,'${String(key).replace(/'/g, "\\'")}')">
          <ul style="margin-top:8px;font-size:12px;color:var(--text-secondary);">${files.map((f) => `<li>${f}</li>`).join('') || '<li>No attachments yet</li>'}</ul>
        </div>
      </div>`;
  }

  function getPortfolioCols() {
    const cols = PORTFOLIO_COLS.filter((c) => allColumns.includes(c));
    return cols.length ? cols : allColumns.slice(0, Math.min(12, allColumns.length));
  }

  function onAttachmentChange(ev, key) {
    Array.from(ev.target.files || []).forEach((f) => saveAttachment(key, f.name));
    ev.target.value = '';
    alert('Saved attachment reference: ' + key);
  }

  return {
    buildFilters,
    buildKPIs,
    buildAllCharts,
    buildInsights,
    applyFiltersAccountKey,
    getDrillCols,
    getPortfolioCols,
    formatCell,
    salesforceLinkHtml,
    webexOrgLinkHtml,
    rowDetailFields,
    getGyrBadge,
    parseLicenseNumbers,
    HIGHLIGHT,
    renderAttachmentUI,
    onAttachmentChange,
    GYR_COL,
  };
})();
/** Link Salesforce opportunity names → BIA deck slides (by org id). */
const BIA_MATCH_ALIASES = {
  '45c3c1ff-5a61-4606-9dc5-9437eb0208b2': ['alamo', 'workforce'],
  '2ff94611-b956-4fa8-9a0e-c196fb50383d': ['sacramento', 'city unified', 'scusd'],
  'fb078f9f-4332-4ace-8b1f-6a46313aa4ea': ['berkeley', 'rnw_sc-berkeley', 'rnw_sc'],
  'b7299b4e-59e5-4d38-a80f-42ad8f6d6672': ['umpqua', 'rnw_umpqua'],
  '707f1259-feb5-4ea2-9a06-05b36402f6cf': ['smbc'],
  'ff5c7f01-4067-44b9-b50a-8a505bee459f': ['santander', 'totta', 'banco santander'],
  '6fb77fb2-4ce6-4608-831c-0a97d43039b8': ['dallas county', 'dallas', 'community college'],
  '7c32f78b-822d-4a07-bda8-f4b11f4a821b': ['baylor', 'health care system'],
  '40357664-235c-44a7-9127-3b4518eeb757': [
    'tennessee medical',
    'university of tenness',
    'ut medical',
    'voice renewal',
  ],
  'a8bbe6ca-841c-46e7-ac4c-d6a5704547d2': ['healthequity', 'health equity'],
};
/** Auto-generated from Lookback BIA Slide Template PDF — run scripts/parse_bia_pdf.py */
const BIA_SLIDES = [
  {
    "page": 3,
    "customerName": "Alamo Workforce Development Inc",
    "orgId": "45c3c1ff-5a61-4606-9dc5-9437eb0208b2",
    "gatheredBy": "",
    "gatheredDate": "March 4, 2026",
    "health": "Upsell",
    "platforms": "Meetings: NU _ EA _ | Calling: NU _ EA _ | Suite: NU _ EA _ | WxCC _",
    "subscription": {
      "sub": "Sub1972464",
      "term": "36M from 09-18-2024 to 09-18-2027",
      "tcv": "$240K",
      "aar": "$54,699.00",
      "collabAe": "Name A / Name B",
      "segment": "SLED",
      "partner": "Barcom Technology Solutions",
      "csmModel": "TAC Supported",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "45c3c1ff-5a61-4606-9dc5-9437eb0208b2",
      "entitled": "918 total including growth",
      "professional": "459/540 (85%)",
      "standard": "",
      "workspace": "125/270 (4)",
      "activeUsers": "322 (55% of provisioned)",
      "externalCalls": "xx out of yy calls (%)",
      "meetings": "NU _ EA _ | Calling: NU _ EA _ | Suite: NU _ EA _ | WxCC _ Customer Org ID: 45c3c1ff-5a61-4606-9dc5-9437eb0208b2",
      "messaging": "64 Active Users, 590 messages sent in the analyzed period. AI Premium - -",
      "numbersAssigned": "xx out of yy numbers (%)",
      "locations": "xx out of yy locations (%)"
    },
    "features": {
      "autoAttendant": "20",
      "huntGroups": "-",
      "callQueues": "5",
      "connectedUc": "-",
      "virtualLines": "215"
    },
    "trends": [
      "Provisioned licenses DOWN -.1% last 90 days",
      "Active users UP +21% last 90 days",
      "Call volume UP +1.5% last 90 days"
    ],
    "notes": [
      {
        "who": "Renewal SE",
        "text": "Notes [[[ Here we should put our overall commentary for this customer situation ]]]"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Address the low adoption of messaging and meetings despite having the licenses available. Use only one"
      },
      {
        "who": "CSM / Acct Team",
        "text": "The customer has a local gateway and Connected-UC configured, Seems to have not traffic on it. Verify if it is still required or should be decommissioned."
      },
      {
        "who": "Acct Team",
        "text": "Address the low adoption of messaging and meetings despite having the licenses available. Use only one"
      },
      {
        "who": "Acct Team",
        "text": "The customer has a local gateway and Connected-UC configured, Seems to have not traffic on it. Verify if it is still required or should be decommissioned."
      },
      {
        "who": "Acct Team",
        "text": "Confirm overage on the Cisco Calling Plan (580/540)"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "X",
        "U": "X"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "09-18-2024 to 09-18-2027",
    "isTemplate": true
  },
  {
    "page": 5,
    "customerName": "Sacramento City Unified School District",
    "orgId": "2ff94611-b956-4fa8-9a0e-c196fb50383d",
    "gatheredBy": "Jeremy Abrams",
    "gatheredDate": "May 19, 2026",
    "health": "Unknown",
    "platforms": "Meetings: | Calling: NU _ EA _ | Suite:",
    "subscription": {
      "sub": "Sub2187758",
      "term": "36M from 11-6-2025 - to 10-6-2028",
      "tcv": "$1,327,091K",
      "aar": "$353,121.60",
      "collabAe": "Erik O'Herron/ Benjamin Lewis",
      "segment": "US PS Market",
      "partner": "ConvergeOne Inc",
      "csmModel": "Scale",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "2ff94611-b956-4fa8-9a0e-c196fb50383d",
      "entitled": "8135total including growth",
      "professional": "1033/1200 (86%)",
      "standard": "3220/4485 (71%) Workspace: 38/2450",
      "workspace": "38/2450",
      "activeUsers": "3861(90% of provisioned)",
      "externalCalls": "197Kout of 1.1Mcalls (17%)",
      "meetings": "| Calling: NU _ EA _ | Suite: Customer Org ID: 2ff94611-b956-4fa8-9a0e-c196fb50383d",
      "messaging": "13 Active Users, 19 messages sent in the analyzed period. AI Premium - - -",
      "numbersAssigned": "Add-Ons (Purchased, Trial, Using) P T U",
      "locations": "PSTN Cisco Calling Plans - - -"
    },
    "features": {
      "autoAttendant": "168",
      "huntGroups": "101",
      "callQueues": "-",
      "connectedUc": "-",
      "virtualLines": "271"
    },
    "trends": [
      "Active users UP +18% last 90 days",
      "Call volume UP +95% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Discuss the Domain Claim status, as it is marked as \u201cNot Completed\u201d in control hub. SSO not enabled"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Address the low adoption of messaging despite having the licenses available."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Core Calling adoption is strong. Biggest watchout is low common area licenses used. (is migration still in progress?)"
      },
      {
        "who": "Acct Team",
        "text": "Discuss the Domain Claim status, as it is marked as \u201cNot Completed\u201d in control hub. SSO not enabled"
      },
      {
        "who": "Acct Team",
        "text": "Address the low adoption of messaging despite having the licenses available."
      },
      {
        "who": "Acct Team",
        "text": "Core Calling adoption is strong. Biggest watchout is low common area licenses used. (is migration still in progress?)"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "11-6-2025 to 10-6-2028",
    "isTemplate": false
  },
  {
    "page": 6,
    "customerName": "Berkeley County School District",
    "orgId": "fb078f9f-4332-4ace-8b1f-6a46313aa4ea",
    "gatheredBy": "Jeremy Abrams",
    "gatheredDate": "May 19, 2026",
    "health": "Good",
    "platforms": "Meetings: | Calling: NU _ EA _ | Suite:",
    "subscription": {
      "sub": "Sub963004",
      "term": "60M from 22-5-2025 to 21-5-2030",
      "tcv": "$1.154M",
      "aar": "$261,696",
      "collabAe": "Peter Caterinicchia",
      "segment": "US PS Market",
      "partner": "Bridgetek Solutions LLC",
      "csmModel": "Scale",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "fb078f9f-4332-4ace-8b1f-6a46313aa4ea",
      "entitled": "7357total including growth",
      "professional": "4376/5193 (84%)",
      "standard": "0/0 (0%) Workspace: 377/2164 (17%)",
      "workspace": "377/2164 (17%)",
      "activeUsers": "4142(87% of provisioned)",
      "externalCalls": "35.8Kout of 1.1Mcalls (3%)",
      "meetings": "| Calling: NU _ EA _ | Suite: Customer Org ID: fb078f9f-4332-4ace-8b1f-6a46313aa4ea",
      "messaging": "1 Active Users, 1messages sent in the analyzed period. AI Premium - - -",
      "numbersAssigned": "Add-Ons (Purchased, Trial, Using) P T U",
      "locations": "PSTN Cisco Calling Plans - - -"
    },
    "features": {
      "autoAttendant": "113",
      "huntGroups": "9",
      "callQueues": "-",
      "connectedUc": "Y",
      "virtualLines": "96"
    },
    "trends": [
      "Active users UP +2.6% last 90 days",
      "Call volume UP +52% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Customer is using Connected-UC, looks like the UCM cluster is still online, but no users are configured on the cluster."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Customer is using Local Gateway for PSTN access Good"
      },
      {
        "who": "CSM/ Acct Team",
        "text": "Core calling usage looks strong, main concern is adoption. Not enabled SSO, Directory connector."
      },
      {
        "who": "CSM/ Acct Team",
        "text": "Core calling usage looks strong, main concern is adoption. Not enabled SSO, Directory connector."
      },
      {
        "who": "Acct Team",
        "text": "Customer is using Connected-UC, looks like the UCM cluster is still online, but no users are configured on the cluster."
      },
      {
        "who": "Acct Team",
        "text": "Customer is using Local Gateway for PSTN access Good"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "22-5-2025 to 21-5-2030",
    "isTemplate": false
  },
  {
    "page": 7,
    "customerName": "Umpqua Bank",
    "orgId": "b7299b4e-59e5-4d38-a80f-42ad8f6d6672",
    "gatheredBy": "Jeremy Abrams",
    "gatheredDate": "May 19, 2026",
    "health": "Risk",
    "platforms": "Meetings: AU _ Meeting| Calling: NU _ EA _ | WxCC",
    "subscription": {
      "sub": "Sub201124",
      "term": "35M from 2-12-2024 to 6-11-2027",
      "tcv": "$926,331",
      "aar": "$430,052",
      "collabAe": "Shane Colling",
      "segment": "Global Enterprise",
      "partner": "Insight Direct",
      "csmModel": "Scale",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "b7299b4e-59e5-4d38-a80f-42ad8f6d6672",
      "entitled": "8501total including growth",
      "professional": "7015/6000 (116%)",
      "standard": "0/0 (0%) Workspace: 477/2501 (19%)",
      "workspace": "477/2501 (19%)",
      "activeUsers": "2571(34% of provisioned)",
      "externalCalls": "1.4Mout of 1.5Mcalls (93%)",
      "meetings": "AU _ Meeting| Calling: NU _ EA _ | WxCC Customer Org ID: b7299b4e-59e5-4d38-a80f-42ad8f6d6672",
      "messaging": "64 Active Users, 590 messages sent in the analyzed period. AI Premium - - -",
      "numbersAssigned": "Add-Ons (Purchased, Trial, Using) P T U",
      "locations": "PSTN Cisco Calling Plans - - -"
    },
    "features": {
      "autoAttendant": "17",
      "huntGroups": "20",
      "callQueues": "-",
      "connectedUc": "Y",
      "virtualLines": "622"
    },
    "trends": [
      "Active users UP +27.5% last 90 days",
      "Call volume UP +15% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Connected-UC is enabled, UCM cluster is now offline"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Customer is using Local Gateway for PSTN access at several sites Risk"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Account team is trying to renew early to consolidate contracts and make them all co-term. (Umpqua + Columbia Bank)"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Concern: yes, for Meeting usage (Microsoft) - No major concern: for Calling usage"
      },
      {
        "who": "Acct Team",
        "text": "Connected-UC is enabled, UCM cluster is now offline"
      },
      {
        "who": "Acct Team",
        "text": "Customer is using Local Gateway for PSTN access at several sites Risk"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "Y",
        "T": "-",
        "U": "Y"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "2-12-2024 to 6-11-2027",
    "isTemplate": false
  },
  {
    "page": 8,
    "customerName": "SMBC",
    "orgId": "707f1259-feb5-4ea2-9a06-05b36402f6cf",
    "gatheredBy": "Alejandra Garcia",
    "gatheredDate": "May 19, 2026",
    "health": "Unknown",
    "platforms": "Meetings: NU _ EA _ | Calling: NU _ EA _ | Suite: NU _ EA X | WxCC _",
    "subscription": {
      "sub": "Sub2160044",
      "term": "36M from 03-Apr-2025 to 02-Apr-2028",
      "tcv": "$1,513,404",
      "aar": "$-",
      "collabAe": "James Bigg / Michael Ciulei",
      "segment": "ENT-MAJOR",
      "partner": "NATILIK LTD",
      "csmModel": "High Touch",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "707f1259-feb5-4ea2-9a06-05b36402f6cf",
      "entitled": "6353 total including growth",
      "professional": "0/4428 (0%)",
      "standard": "",
      "workspace": "0/1925 (0%)",
      "activeUsers": "0 (0% of provisioned)",
      "externalCalls": "0 out of 0 calls (0%)",
      "meetings": "NU _ EA _ | Calling: NU _ EA _ | Suite: NU _ EA X | WxCC _ Customer Org ID: 707f1259-feb5-4ea2-9a06-05b36402f6cf",
      "messaging": "105 Active Users, 321 messages sent in the analyzed period. AI Premium - - -",
      "numbersAssigned": "0 out of 0 numbers (%)",
      "locations": "0 out of 0 locations (%)"
    },
    "features": {
      "autoAttendant": "-",
      "huntGroups": "-",
      "callQueues": "-",
      "connectedUc": "-",
      "virtualLines": "-"
    },
    "trends": [
      "Active users - 0% last 90 days",
      "Call volume - 0% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Continue working on showing Speech to speech translation."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Promote webinars for large scale meetings despite customer is already moving to Teams for Meetings and messaging."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Discuss Webex Calling Integration with MS Teams ."
      },
      {
        "who": "Acct Team",
        "text": "Continue working on showing Speech to speech translation."
      },
      {
        "who": "Acct Team",
        "text": "Promote webinars for large scale meetings despite customer is already moving to Teams for Meetings and messaging."
      },
      {
        "who": "Acct Team",
        "text": "Discuss Webex Calling Integration with MS Teams ."
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "",
    "isTemplate": false
  },
  {
    "page": 9,
    "customerName": "BANCO SANTANDER TOTTA SA",
    "orgId": "ff5c7f01-4067-44b9-b50a-8a505bee459f",
    "gatheredBy": "Alejandra Garcia",
    "gatheredDate": "May 21, 2026",
    "health": "Upsell",
    "platforms": "Meetings: NU _ EA _ | Calling: NU _ EA X| Suite: NU _ EA _ | WxCC _",
    "subscription": {
      "sub": "Sub2063875",
      "term": "60M from 22-Jan-2025 to 21-Jan-2030",
      "tcv": "$1,473,000",
      "aar": "",
      "collabAe": "Joana de Oliveira Carvalho / Marcio Costa",
      "segment": "",
      "partner": "TELEFONICA ESPANA",
      "csmModel": "Scale AI Receptionist - - -",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "ff5c7f01-4067-44b9-b50a-8a505bee459f",
      "entitled": "8500 total including growth",
      "professional": "4901/6000 (81%)",
      "standard": "",
      "workspace": "23/2500 (0.92%)",
      "activeUsers": "717 (14.5% of provisioned)",
      "externalCalls": "454.1K out of 1.1M calls (45%)",
      "meetings": "NU _ EA _ | Calling: NU _ EA X| Suite: NU _ EA _ | WxCC _ Customer Org ID: ff5c7f01-4067-44b9-b50a-8a505bee459f",
      "messaging": "10 Active Users, 8 messages sent in the analyzed period.",
      "numbersAssigned": "",
      "locations": ""
    },
    "features": {
      "autoAttendant": "322",
      "huntGroups": "46",
      "callQueues": "985",
      "connectedUc": "N",
      "virtualLines": "1"
    },
    "trends": [
      "Active users UP +3.3% last 90 days",
      "Call volume UP +10.15% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Discuss the Directory Sync, SSO and Hybrid Calendar integrations in Control Hub."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Address the opportunity of increasing the usage of the calling licenses. Less than 10% are actively used. UPSELL Customer uses Basic Call Queues and Auto Attendant, discuss the Upselling opportunity for Customer Assist for a more elevated experience. Possible"
      },
      {
        "who": "CSM / Acct Team",
        "text": "opportunity for AI Receptionist"
      },
      {
        "who": "Acct Team",
        "text": "Discuss the Directory Sync, SSO and Hybrid Calendar integrations in Control Hub."
      },
      {
        "who": "Acct Team",
        "text": "Address the opportunity of increasing the usage of the calling licenses. Less than 10% are actively used. UPSELL Customer uses Basic Call Queues and Auto Attendant, discuss the Upselling opportunity for Customer Assist for a more elevated experience. Possible"
      },
      {
        "who": "Acct Team",
        "text": "opportunity for AI Receptionist"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "",
    "isTemplate": false
  },
  {
    "page": 10,
    "customerName": "DALLAS COUNTY COMMUNITY COLLEGE DISTRICT",
    "orgId": "6fb77fb2-4ce6-4608-831c-0a97d43039b8",
    "gatheredBy": "Fred W",
    "gatheredDate": "May 21, 2026",
    "health": "Unknown",
    "platforms": "Meetings: NU _ EA | Calling: NU _ EA | Suite: NU _ EA |",
    "subscription": {
      "sub": "Sub2050374",
      "term": "60M from 01-20-2025 to 01-19-2030",
      "tcv": "$1,838,043.60",
      "aar": "$367,685.52",
      "collabAe": "",
      "segment": "US PS",
      "partner": "NETSYNC NETWORK SOLUTIONS",
      "csmModel": "Scale",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "6fb77fb2-4ce6-4608-831c-0a97d43039b8",
      "entitled": "7,468 total including growth",
      "professional": "0/5205 (0%)",
      "standard": "",
      "workspace": "0/2263 (0%)",
      "activeUsers": "0 for calling / 50 unique hosts for meetings over past 90 days",
      "externalCalls": "0 out of 0 calls (0%)",
      "meetings": "NU _ EA | Calling: NU _ EA | Suite: NU _ EA | Customer Org ID: 6fb77fb2-4ce6-4608-831c-0a97d43039b8",
      "messaging": "29 Daily Active Users, 7.5K messages sent over past 90 days AI Premium - - -",
      "numbersAssigned": "0 out of 0 numbers (0%)",
      "locations": "0 out of 2 locations (0%)"
    },
    "features": {
      "autoAttendant": "-",
      "huntGroups": "-",
      "callQueues": "-",
      "connectedUc": "\u2014",
      "virtualLines": "-"
    },
    "trends": [
      "Provisioned licenses - 0% last 90 days",
      "Active users - 0% last 90 days",
      "Call volume 0 0% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Address the migration issue with customer. They are still using their on prem and will loose entitlement soon."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Consider proposing setup assist to help with the migration."
      },
      {
        "who": "Acct Team",
        "text": "Address the migration issue with customer. They are still using their on prem and will loose entitlement soon."
      },
      {
        "who": "Acct Team",
        "text": "Consider proposing setup assist to help with the migration."
      },
      {
        "who": "Acct Team",
        "text": "Extension of entitlement for on prem system will most likely be needed."
      },
      {
        "who": "Note",
        "text": "Customer has dual entitlement to on prem until July 20th 2026. They have nothing set up in WxC multi tenant or DI. They will lose entitlement soon."
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "01-20-2025 to 01-19-2030",
    "isTemplate": false
  },
  {
    "page": 11,
    "customerName": "BAYLOR HEALTH CARE SYSTEM",
    "orgId": "7c32f78b-822d-4a07-bda8-f4b11f4a821b",
    "gatheredBy": "Fred W",
    "gatheredDate": "May 25, 2026",
    "health": "Unknown",
    "platforms": "Meetings: AU EA _ | Calling: NU _ EA | Suite: NU _ EA _",
    "subscription": {
      "sub": "Sub1972464",
      "term": "39.23M from 03-24-2025 to 06-30-2028",
      "tcv": "$4,330,667.18",
      "aar": "$1,324,700.64",
      "collabAe": "",
      "segment": "",
      "partner": "WWT",
      "csmModel": "Hight Touch AI Receptionist - - -",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "7c32f78b-822d-4a07-bda8-f4b11f4a821b",
      "entitled": "13,500 total including growth",
      "professional": "2/6K (.03%)",
      "standard": "",
      "workspace": "0/7.5K (0%)",
      "activeUsers": "0",
      "externalCalls": "0 out of 0 calls (0%)",
      "meetings": "AU EA _ | Calling: NU _ EA | Suite: NU _ EA _ Customer Org ID: 7c32f78b-822d-4a07-bda8-f4b11f4a821b",
      "messaging": "158 Active Users, 2.6K messages sent over past 90 days AI Premium - - -",
      "numbersAssigned": "0 out of 0 numbers (0%)",
      "locations": "0 out of 5 locations (0%)"
    },
    "features": {
      "autoAttendant": "-",
      "huntGroups": "-",
      "callQueues": "-",
      "connectedUc": "-",
      "virtualLines": "-"
    },
    "trends": [
      "Provisioned licenses - -% last 90 days",
      "Active users - -% last 90 days",
      "Call volume - -% last 90 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "Discuss with customer what their plans are to migrate to WxC."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Propose set up assist to aid with building out WxC deployment."
      },
      {
        "who": "Acct Team",
        "text": "Discuss with customer what their plans are to migrate to WxC."
      },
      {
        "who": "Acct Team",
        "text": "Propose set up assist to aid with building out WxC deployment."
      },
      {
        "who": "Note",
        "text": "Great usage of Meetings and Messaging"
      },
      {
        "who": "Note",
        "text": "Still seeing heavy usage on prem calling, but nothing is provisioned in WxC (numbers, features, users, etc). UCM most likely needs to be upgraded to v15."
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "03-24-2025 to 06-30-2028",
    "isTemplate": false
  },
  {
    "page": 12,
    "customerName": "THE UNIVERSITY OF TENNESSEE MEDICAL CENTER",
    "orgId": "40357664-235c-44a7-9127-3b4518eeb757",
    "gatheredBy": "KennethO on",
    "gatheredDate": "May 18, 2026",
    "health": "Unknown",
    "platforms": "Meetings: EA | Calling: NU | WxCC",
    "subscription": {
      "sub": "Sub2195655, Sub2195656, Sub535343",
      "term": "60.00 Months from 28-Apr-2025 to 27-Apr-2030(Webex) & Basic Call Queues 3",
      "tcv": "$2,071K",
      "aar": "$500,611.56",
      "collabAe": "Kristen Dawson / Kyle Davenport",
      "segment": "USPS PSTN Cisco Calling Plans - - -",
      "partner": "Internetwork Engineering (Presidio)",
      "csmModel": "TAC Supported AI Assistant -",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "40357664-235c-44a7-9127-3b4518eeb757",
      "entitled": "PL: 40/105, WS: 34/82, WxM: 347/5762",
      "professional": "",
      "standard": "",
      "workspace": "",
      "activeUsers": "Calling: 56; Endpoints: 108;",
      "externalCalls": "22.9K out of 40.5K calls (%)",
      "meetings": "EA | Calling: NU | WxCC Customer Org ID: 40357664-235c-44a7-9127-3b4518eeb757",
      "messaging": "21 Active Users; 1.5K Messages sent AI Agent -",
      "numbersAssigned": "xx out of yy numbers (%)",
      "locations": "xx out of yy locations (%)"
    },
    "features": {
      "autoAttendant": "14",
      "huntGroups": "1",
      "callQueues": "3",
      "connectedUc": "\u2014",
      "virtualLines": "1"
    },
    "trends": [
      "Active users UP +7.69% last 30 days",
      "Call volume UP +11.2% last 30 days"
    ],
    "notes": [
      {
        "who": "Renewals SE",
        "text": "Renewal SE to reach out to account team"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Address the low adoption of messaging and meetings."
      },
      {
        "who": "CSM / Acct Team",
        "text": "Monitor customer usage. Is this a hybrid deployment? Recommended Actions"
      },
      {
        "who": "Acct Team",
        "text": "Address the low adoption of messaging and meetings."
      },
      {
        "who": "Acct Team",
        "text": "Monitor customer usage. Is this a hybrid deployment? Recommended Actions"
      },
      {
        "who": "Insight",
        "text": "The customer has a local gateway and Connected-UC configured. Over 24K calls with only 1% poor calls"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "",
    "isTemplate": false
  },
  {
    "page": 13,
    "customerName": "HealthEquity, Inc.",
    "orgId": "a8bbe6ca-841c-46e7-ac4c-d6a5704547d2",
    "gatheredBy": "KennethO on",
    "gatheredDate": "May 18, 2026",
    "health": "Good",
    "platforms": "Meetings: EA | Calling: EA | WxCC",
    "subscription": {
      "sub": "Sub239706, Sub1661355, Sub1661356",
      "term": "60.00 Months from 12-Dec-2024 to 11-Dec-2029(calling) & Basic Call Queues -",
      "tcv": "$1,009K",
      "aar": "$201,813.04 calls: 97.7% (up 0.14%)",
      "collabAe": "",
      "segment": "Commercial",
      "partner": "Presidio",
      "csmModel": "Scale \u2013 Jessi Carrasco AI Premium - - -",
      "links": "S&C | Success Portal"
    },
    "provisioning": {
      "orgId": "a8bbe6ca-841c-46e7-ac4c-d6a5704547d2",
      "entitled": "WxM: 272/3500; PL: 45/3896; WS: 34/1663; Auto Attendant -",
      "professional": "",
      "standard": "",
      "workspace": "",
      "activeUsers": "Calling: 27; Endpoints: 64 Connected-UC -",
      "externalCalls": "59.4K out of 60K calls (%)",
      "meetings": "EA | Calling: EA | WxCC",
      "messaging": "4 Active Users, 40 messages sent.",
      "numbersAssigned": "xx out of yy numbers (%)",
      "locations": ""
    },
    "features": {
      "autoAttendant": "-",
      "huntGroups": "-",
      "callQueues": "-",
      "connectedUc": "-",
      "virtualLines": "-"
    },
    "trends": [
      "Active users UP +0% last 30 days",
      "Call volume UP +95.33% last 30 days"
    ],
    "notes": [
      {
        "who": "CSM / Acct Team",
        "text": "99% of licenses not provisioned"
      },
      {
        "who": "CSM / Acct Team",
        "text": "Address the low adoption of messaging and meetings despite having the licenses available."
      },
      {
        "who": "Acct Team",
        "text": "99% of licenses not provisioned"
      },
      {
        "who": "Acct Team",
        "text": "Address the low adoption of messaging and meetings despite having the licenses available."
      },
      {
        "who": "Insight",
        "text": "Still on CUCM 2,622 Enahnced and 1492 Std Unity"
      },
      {
        "who": "Insight",
        "text": "67 Hours of VIMT calls and 66 locally wired. Assuming that\u2019s also Teams meetings Recommended Actions"
      }
    ],
    "addons": {
      "PSTN Cisco Calling Plans": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Customer Assist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "Attendant Console": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Receptionist": {
        "P": "-",
        "T": "-",
        "U": "-"
      },
      "AI Premium": {
        "P": "-",
        "T": "-",
        "U": "-"
      }
    },
    "subscriptionDates": "",
    "isTemplate": false
  }
];
/**
 * Lookback BIA slide template renderer (matches PDF deck layout).
 */
const BiaTemplate = (function () {
  const WEBEX_ORG_ADMIN_PREFIX = 'https://admin.webex.com/help-desk/org/';
  const GYR_COL = ' (G/Y/R)';

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function orgLink(id) {
    const v = String(id || '').trim();
    if (!v) return '—';
    const href = WEBEX_ORG_ADMIN_PREFIX + encodeURIComponent(v);
    return `<a href="${href.replace(/"/g, '&quot;')}" target="_blank" rel="noopener noreferrer" class="customer-link">${esc(v)}</a>`;
  }

  function healthClass(h) {
    const x = String(h || '').toLowerCase();
    if (x === 'good') return { class: 'good', label: 'Good' };
    if (x === 'risk') return { class: 'risk', label: 'Risk' };
    if (x === 'upsell') return { class: 'upsell', label: 'Upsell' };
    return { class: 'unknown', label: h || '—' };
  }

  function isEmptyVal(v) {
    const s = String(v ?? '').trim();
    return !s || s === '—' || s === '-' || /^n\/?a$/i.test(s);
  }

  /** Strip PDF parser bleed (org ids, add-on tables, wrong field merges). */
  function sanitizeField(raw) {
    let s = String(raw ?? '').trim();
    if (!s) return '';
    s = s.replace(/Customer Org ID:\s*[a-f0-9-]{36}/gi, '');
    s = s.replace(/Add-Ons \(Purchased, Trial, Using\)[\s\S]*/i, '');
    s = s.replace(/\|\s*Calling:.*$/i, '');
    s = s.replace(/Meetings:\s*NU[^|]*/i, '');
    s = s.replace(/\s+/g, ' ').trim();
    if (/^(NU|AU)\s*_/i.test(s) && s.length < 40) return '';
    if (/^PSTN Cisco Calling Plans/i.test(s)) return '';
    return s;
  }

  function sanitizeMoney(raw) {
    const s = sanitizeField(raw);
    if (!s || s === '$-' || s === '-') return '';
    if (/Licenses Active|External Calls vs|numbers \(/i.test(s)) return '';
    const m = s.match(/^\$[\d,.]+[KMB]?/i);
    return m ? m[0] : s.split(/\s{2,}/)[0].trim();
  }

  function sanitizeSegment(raw) {
    const s = sanitizeField(raw);
    if (/External Calls|Licenses Active|@cisco\.com/i.test(s)) return '';
    return s;
  }

  function licPair(raw) {
    const s = sanitizeField(raw);
    const m = s.match(/(\d[\d,]*)\s*\/\s*(\d[\d,]*)/);
    return m ? `${m[1]}/${m[2]}` : s;
  }

  function cleanVal(v) {
    const s = sanitizeField(v);
    if (!s || s === '—') return '';
    return s;
  }

  function kv(label, value) {
    const raw = cleanVal(value);
    if (!raw) return '';
    const html = label === 'Customer Org ID' ? orgLink(raw) : esc(raw);
    return `<div class="insight-kv"><span>${esc(label)}</span><strong>${html}</strong></div>`;
  }

  function licBar(label, raw) {
    const s = sanitizeField(raw);
    const m = s.match(/(\d[\d,]*)\s*\/\s*(\d[\d,]*)\s*\((\d+)%\)/);
    if (!m) return kv(label, s || '—');
    const u = parseFloat(m[1].replace(/,/g, ''));
    const t = parseFloat(m[2].replace(/,/g, ''));
    const p = t ? Math.min(100, Math.round((u / t) * 100)) : parseInt(m[3], 10) || 0;
    return `<div class="insight-lic-row">
      <span class="insight-lic-label">${esc(label)}</span>
      <span class="insight-lic-nums">${esc(m[1])}/${esc(m[2])} (${p}%)</span>
      <div class="insight-lic-bar"><div class="insight-lic-fill" style="width:${p}%"></div></div>
    </div>`;
  }

  function normName(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/\b(the|inc|llc|ltd|corp|sa|co)\b/g, ' ')
      .replace(/[^a-z0-9]+/g, '')
      .trim();
  }

  function namesMatch(a, b) {
    const na = normName(a);
    const nb = normName(b);
    if (!na || !nb) return false;
    if (na === nb) return true;
    const min = Math.min(na.length, nb.length, 16);
    if (min >= 8 && (na.includes(nb.slice(0, min)) || nb.includes(na.slice(0, min)))) return true;
    const ta = new Set(na.match(/[a-z]{4,}/g) || []);
    const tb = new Set(nb.match(/[a-z]{4,}/g) || []);
    let overlap = 0;
    ta.forEach((t) => {
      if (tb.has(t)) overlap += 1;
    });
    return overlap >= 2;
  }

  function matchByAlias(opportunityName) {
    if (typeof BIA_MATCH_ALIASES === 'undefined' || typeof BIA_SLIDES === 'undefined') return null;
    const hay = String(opportunityName || '').toLowerCase();
    if (!hay) return null;
    for (const slide of BIA_SLIDES) {
      const org = slide.orgId;
      if (!org) continue;
      const keys = BIA_MATCH_ALIASES[org] || [];
      if (keys.some((k) => hay.includes(k))) return slide;
    }
    return null;
  }

  function healthToGyr(health) {
    const h = String(health || '').toLowerCase();
    if (h === 'good') return 'G';
    if (h === 'risk') return 'R';
    if (h === 'upsell') return 'Y';
    return '';
  }

  function findSlide(row) {
    if (typeof BIA_SLIDES === 'undefined' || !BIA_SLIDES.length) return null;
    const org = String(row?.['Customer org id'] || '').trim().toLowerCase();
    if (org) {
      const hit = BIA_SLIDES.find((s) => s.orgId && s.orgId.toLowerCase() === org);
      if (hit) return hit;
    }
    const name = row?.['Opportunity Name'] || row?.['Account Name'] || '';
    const alias = matchByAlias(name);
    if (alias) return alias;
    if (!name) return null;
    return BIA_SLIDES.find((s) => namesMatch(name, s.customerName)) || null;
  }

  function sanitizeSlide(slide) {
    const s = slide.subscription || {};
    const p = slide.provisioning || {};
    const f = slide.features || {};
    return {
      ...slide,
      platforms: sanitizeField(slide.platforms),
      subscription: {
        ...s,
        sub: sanitizeField(s.sub),
        term: sanitizeField(s.term),
        tcv: sanitizeMoney(s.tcv),
        aar: sanitizeMoney(s.aar),
        collabAe: sanitizeField(s.collabAe),
        segment: sanitizeSegment(s.segment),
        partner: sanitizeField(s.partner),
        csmModel: sanitizeField(s.csmModel),
      },
      provisioning: {
        ...p,
        entitled: sanitizeField(p.entitled),
        professional: sanitizeField(p.professional),
        standard: sanitizeField(p.standard),
        workspace: sanitizeField(p.workspace),
        activeUsers: sanitizeField(p.activeUsers),
        externalCalls: sanitizeField(p.externalCalls),
        meetings: sanitizeField(p.meetings),
        messaging: sanitizeField(p.messaging),
        numbersAssigned: sanitizeField(p.numbersAssigned),
        locations: sanitizeField(p.locations),
      },
      features: { ...f },
    };
  }

  /** Columns owned by the Lookback BIA deck (not copied wholesale from the workbook). */
  const BIA_CANONICAL_COLS = new Set([
    'Opportunity Name',
    'Customer org id',
    GYR_COL,
    'TCV $',
    'AAR $',
    'Sub #',
    'Subscription dates',
    'Sub term (months)',
    'Platforms',
    'Partner',
    'SL2',
    'Collab AE/SE',
    'CSM Engagement Model (linked)',
    'Entitled Lic Calling',
    'Providioned Lic Calling',
    'Active Lic Calling',
    'Lic Professional (used/entitled)',
    'Lic Standard (used/entitled)',
    'Lic Workspace (used/entitled)',
    'Meetings usage',
    'Messaging usage',
    'External calls',
    'Auto Attendant count',
    'Hunt Groups count',
    'Call Queues count',
    'Connected-UC (Y/N)',
    'Virtual Lines count',
    'Active % of provisioned',
    'Data gathered by',
    'Data gathered date',
    'Notes from Calling Analytics',
    'Calls busiest hour',
    'Trend active users 90d',
    'Trend call volume 90d',
  ]);

  /** Spreadsheet-only fields to keep when a row is linked to a BIA slide. */
  const WORKBOOK_SUPPLEMENT_COLS = [
    'Opportunity (linked)',
    'Salesforce URL',
    'Closed on (MM/YY)',
    'Competitor',
    'Migrating from',
    'Migrating to',
    'Success Portal',
    'CSM name',
    'Sub start date (MM/DD/YYYY)',
    'Add-ons included or not',
    'Calling Setup Assist included (Y/N)',
    'CCEP trial (Y/N)',
    'Notes from provisioned features',
    'Trial',
    'Final Determination',
    'Recommended Actions',
    'TAC/BEMS',
    'Control Hub Helpdesk',
  ];

  /** Build one row from the BIA slide (same shape for every deck customer). */
  function applyBiaFields(out, deck, wb) {
    const s = deck.subscription || {};
    const p = deck.provisioning || {};
    const f = deck.features || {};
    const wbRow = wb || {};

    function set(col, val) {
      if (val != null && String(val).trim() !== '') out[col] = val;
    }

    set('Opportunity Name', deck.customerName);
    set('Customer org id', deck.orgId);
    set(GYR_COL, healthToGyr(deck.health) || wbRow[GYR_COL] || wbRow['Final Determination'] || '');
    set('TCV $', s.tcv || wbRow['TCV $']);
    set('AAR $', s.aar || wbRow['AAR $']);
    set('Sub #', s.sub || wbRow['Sub #']);
    set('Subscription dates', s.term);
    set('Sub term (months)', (s.term || '').split(' from ')[0].trim() || wbRow['Sub term (months)']);
    set('Platforms', deck.platforms);
    set('Partner', s.partner || wbRow['Partner']);
    set('SL2', s.segment || wbRow['SL2']);
    set('Collab AE/SE', s.collabAe);
    set('CSM Engagement Model (linked)', s.csmModel || wbRow['CSM Engagement Model (linked)']);
    set('Entitled Lic Calling', p.entitled);
    set('Providioned Lic Calling', p.professional);
    set('Active Lic Calling', p.activeUsers);
    set('Lic Professional (used/entitled)', licPair(p.professional));
    set('Lic Standard (used/entitled)', licPair(p.standard));
    set('Lic Workspace (used/entitled)', licPair(p.workspace));
    set('Meetings usage', p.meetings);
    set('Messaging usage', p.messaging);
    set('External calls', p.externalCalls);
    set('Auto Attendant count', f.autoAttendant);
    set('Hunt Groups count', f.huntGroups);
    set('Call Queues count', f.callQueues);
    set('Connected-UC (Y/N)', f.connectedUc);
    set('Virtual Lines count', f.virtualLines);
    const actPct = String(p.activeUsers || '').match(/(\d+)%/);
    if (actPct) set('Active % of provisioned', actPct[1] + '%');
    set('Data gathered by', deck.gatheredBy);
    set('Data gathered date', deck.gatheredDate);

    (deck.trends || []).forEach((t) => {
      const text = sanitizeField(t);
      if (/active users/i.test(text)) set('Trend active users 90d', text);
      if (/call volume|provisioned licenses/i.test(text)) set('Trend call volume 90d', text);
    });

    const noteText = (deck.notes || [])
      .map((n) => (n.who ? n.who + ': ' : '') + (n.text || ''))
      .filter((t) => t.length > 24)
      .join('\n');
    if (noteText) set('Notes from Calling Analytics', noteText);

    if (deck.orgId) out._biaSlide = true;
    return out;
  }

  function mergeWorkbookSupplements(out, wb) {
    if (!wb) return out;
    WORKBOOK_SUPPLEMENT_COLS.forEach((col) => {
      const v = wb[col];
      if (v != null && String(v).trim() !== '') out[col] = v;
    });
    Object.keys(wb).forEach((col) => {
      if (col.startsWith('_') || BIA_CANONICAL_COLS.has(col) || WORKBOOK_SUPPLEMENT_COLS.includes(col)) {
        return;
      }
      if (out[col] !== undefined) return;
      const v = wb[col];
      if (v != null && String(v).trim() !== '') out[col] = v;
    });
    return out;
  }

  /**
   * Lookback customers: BIA slide is the source of truth (same field set for each).
   * Workbook only adds migration / Salesforce / trial columns — not a full row copy.
   */
  function enrichRow(row) {
    const slide = findSlide(row);
    if (!slide) return row;
    const deck = sanitizeSlide(slide);
    const out = applyBiaFields({}, deck, row);
    return mergeWorkbookSupplements(out, row);
  }

  function slideToRow(slide) {
    return enrichRow({
      'Opportunity Name': slide.customerName,
      'Customer org id': slide.orgId,
    });
  }

  function rowMatchesSlide(row, slide) {
    if (!slide?.orgId) return false;
    const found = findSlide(row);
    return found && found.orgId && found.orgId.toLowerCase() === slide.orgId.toLowerCase();
  }

  function sortPortfolio(rows) {
    return [...rows].sort((a, b) =>
      String(a['Opportunity Name'] || '').localeCompare(String(b['Opportunity Name'] || ''), undefined, {
        sensitivity: 'base',
      })
    );
  }

  /**
   * One customer list: each BIA deck account merged with its spreadsheet row when present,
   * then remaining spreadsheet-only accounts — all sorted together by name.
   */
  function mergePortfolioWithBia(rows) {
    const workbookRows = rows || [];
    const usedWorkbookIdx = new Set();
    const portfolio = [];

    if (typeof BIA_SLIDES !== 'undefined' && BIA_SLIDES.length) {
      BIA_SLIDES.forEach((slide) => {
        if (!slide.orgId || slide.isTemplate) return;
        let wbRow = null;
        let wbIdx = -1;
        for (let i = 0; i < workbookRows.length; i++) {
          if (usedWorkbookIdx.has(i)) continue;
          if (rowMatchesSlide(workbookRows[i], slide)) {
            wbRow = workbookRows[i];
            wbIdx = i;
            break;
          }
        }
        if (wbIdx >= 0) usedWorkbookIdx.add(wbIdx);
        const stub = {
          'Opportunity Name': slide.customerName,
          'Customer org id': slide.orgId,
        };
        portfolio.push(enrichRow(wbRow ? { ...stub, ...wbRow } : stub));
      });
    }

    workbookRows.forEach((row, i) => {
      if (usedWorkbookIdx.has(i)) return;
      portfolio.push(enrichRow(row));
    });

    return sortPortfolio(portfolio);
  }

  function collectAllColumns(rows) {
    if (!rows || !rows.length) return [];
    const prefer = [
      'Opportunity Name',
      GYR_COL,
      'Customer org id',
      'TCV $',
      'AAR $',
      'Platforms',
      'Partner',
      'SL2',
      'Sub #',
      'Entitled Lic Calling',
      'Providioned Lic Calling',
      'Active Lic Calling',
    ];
    const seen = new Set();
    const ordered = [];
    prefer.forEach((c) => {
      if (rows.some((r) => r[c] != null && String(r[c]).trim() !== '')) {
        ordered.push(c);
        seen.add(c);
      }
    });
    rows.forEach((r) => {
      Object.keys(r).forEach((k) => {
        if (k.startsWith('_') || seen.has(k)) return;
        seen.add(k);
        ordered.push(k);
      });
    });
    return ordered;
  }

  function mergeSlideWithRow(row, slide) {
    const merged = sanitizeSlide(JSON.parse(JSON.stringify(slide)));
    if (!isEmptyVal(row['Salesforce URL'])) merged.salesforceUrl = row['Salesforce URL'];
    if (!isEmptyVal(row['Data gathered by']) && isEmptyVal(merged.gatheredBy)) {
      merged.gatheredBy = row['Data gathered by'];
    }
    if (!isEmptyVal(row['Data gathered date']) && isEmptyVal(merged.gatheredDate)) {
      merged.gatheredDate = row['Data gathered date'];
    }
    return merged;
  }

  function render(slide) {
    const deck = sanitizeSlide(slide);
    const s = deck.subscription || {};
    const p = deck.provisioning || {};
    const f = deck.features || {};
    const h = healthClass(deck.health);
    const gathered =
      deck.gatheredBy || deck.gatheredDate
        ? `Data gathered${deck.gatheredBy ? ' by ' + deck.gatheredBy : ''}${deck.gatheredDate ? ' on ' + deck.gatheredDate : ''}`
        : '';

    const trends = (deck.trends || [])
      .map((t) => `<span class="insight-trend">${esc(sanitizeField(t))}</span>`)
      .join('');

    const notes = (deck.notes || [])
      .filter((n) => n.text && n.text.length > 20 && !n.text.includes('Subscription Review'))
      .map((n) => `<div class="insight-note"><strong>${esc(n.who)}:</strong> ${esc(n.text)}</div>`)
      .join('');

    const years = deck.timelineYears || 5;
    const yearSpans = Array.from({ length: years }, (_, i) => {
      const y = i + 1;
      const now = y === 2 && years >= 2;
      return now
        ? `<span class="insight-now">Year ${y} · NOW ▼</span>`
        : `<span>Year ${y}</span>`;
    }).join('');

    return `
    <div class="insight-slide bia-slide">
      <div class="insight-top">
        <div class="insight-title-block">
          <h1 class="insight-h1">${esc(deck.customerName)}</h1>
          <p class="insight-subtitle">Business Insight and Analysis</p>
          ${gathered ? `<p class="insight-meta">${esc(gathered)}</p>` : ''}
          ${deck.isTemplate ? '<p class="insight-meta bia-template-tag">Reference template slide</p>' : ''}
        </div>
        <div class="insight-health insight-health-${h.class}">
          <span>${esc(h.label)}</span>
        </div>
      </div>

      <div class="insight-timeline">${yearSpans}</div>

      <div class="insight-panels">
        <section class="insight-panel insight-panel-cyan">
          <h3>Subscription Review</h3>
          ${deck.platforms ? kv('Platforms', deck.platforms) : ''}
          ${kv('Subscription', s.sub)}
          ${kv('Term', s.term)}
          ${kv('Total Contract Value', s.tcv)}
          ${kv('Total Recurring Revenue (AAR)', s.aar)}
          ${kv('Collab AE/SE', s.collabAe)}
          ${kv('Segment', s.segment)}
          ${kv('Partner', s.partner)}
          ${kv('CSM Coverage Model', s.csmModel)}
          ${s.links ? kv('Links', s.links) : ''}
        </section>

        <section class="insight-panel insight-panel-orange">
          <h3>Provisioning &amp; Usage Data</h3>
          ${kv('Customer Org ID', p.orgId || deck.orgId)}
          ${kv('Entitled Licenses', p.entitled)}
          ${p.professional ? licBar('Professional', p.professional) : ''}
          ${p.standard ? licBar('Standard', p.standard) : ''}
          ${p.workspace ? licBar('Workspace', p.workspace) : ''}
          ${kv('Active Users', p.activeUsers)}
          ${kv('Numbers Assigned / Provisioned', p.numbersAssigned)}
          ${kv('Location w/ Main Number / VM', p.locations)}
          ${kv('External Calls vs Total', p.externalCalls)}
          ${kv('Meetings', p.meetings)}
          ${kv('Messaging', p.messaging)}
        </section>

        <section class="insight-panel insight-panel-magenta">
          <h3>Feature use &amp; Add-ons</h3>
          <p class="bia-feature-caption">Included features (Using – how many)</p>
          <div class="insight-feature-grid">
            <div><span>Auto Attendant</span><strong>${esc(f.autoAttendant || '—')}</strong></div>
            <div><span>Hunt Groups</span><strong>${esc(f.huntGroups || '—')}</strong></div>
            <div><span>Basic Call Queues</span><strong>${esc(f.callQueues || '—')}</strong></div>
            <div><span>Connected-UC</span><strong>${esc(f.connectedUc || '—')}</strong></div>
            <div><span>Virtual Lines</span><strong>${esc(f.virtualLines || '—')}</strong></div>
          </div>
          <table class="bia-addon-table">
            <thead><tr><th>Add-Ons</th><th>P</th><th>T</th><th>U</th></tr></thead>
            <tbody>
              <tr><td>PSTN Cisco Calling Plans</td><td>—</td><td>—</td><td>—</td></tr>
              <tr><td>Customer Assist</td><td>—</td><td>—</td><td>—</td></tr>
              <tr><td>Attendant Console</td><td>—</td><td>—</td><td>—</td></tr>
              <tr><td>AI Receptionist</td><td>—</td><td>—</td><td>—</td></tr>
              <tr><td>AI Premium</td><td>—</td><td>—</td><td>—</td></tr>
            </tbody>
          </table>
        </section>
      </div>

      ${trends ? `<div class="bia-trends-row">${trends}</div>` : ''}

      <section class="insight-panel insight-panel-notes">
        <h3>Notes &amp; Recommended Actions</h3>
        ${notes || '<div class="insight-note">No notes extracted for this slide.</div>'}
      </section>

      <div class="insight-footer">© 2025 Cisco · Lookback Program · Cisco Confidential</div>
    </div>`;
  }

  function listSlides() {
    return typeof BIA_SLIDES !== 'undefined' ? BIA_SLIDES : [];
  }

  return {
    render,
    findSlide,
    listSlides,
    healthClass,
    enrichRow,
    enrichAllRows: mergePortfolioWithBia,
    mergePortfolioWithBia,
    collectAllColumns,
    mergeSlideWithRow,
    sanitizeSlide,
    healthToGyr,
  };
})();
/**
 * Business Insight slide view — uses Lookback BIA deck when available, else spreadsheet row.
 */
const AccountInsight = (function () {
  const GYR_COL = ' (G/Y/R)';
  const WEBEX_ORG_ADMIN_PREFIX = 'https://admin.webex.com/help-desk/org/';

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function orgIdLinkHtml(orgId) {
    const id = String(orgId ?? '').trim();
    if (!id || id === '—') return esc('—');
    const href = WEBEX_ORG_ADMIN_PREFIX + encodeURIComponent(id);
    return `<a href="${href.replace(/"/g, '&quot;')}" target="_blank" rel="noopener noreferrer" class="customer-link">${esc(id)}</a>`;
  }

  function openOverlay(html) {
    const overlay = document.getElementById('accountInsightOverlay');
    const body = document.getElementById('accountInsightBody');
    if (!overlay || !body) return;
    body.innerHTML = html;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function openBia(slide, row) {
    if (typeof BiaTemplate !== 'undefined') {
      const base = BiaTemplate.sanitizeSlide ? BiaTemplate.sanitizeSlide(slide) : slide;
      const merged = row ? BiaTemplate.mergeSlideWithRow(row, base) : base;
      openOverlay(BiaTemplate.render(merged));
      return;
    }
    open({ 'Opportunity Name': slide.customerName, 'Customer org id': slide.orgId });
  }

  function buildModel(row) {
    const notes = { prof: null, ws: null, std: null, meetings: '', messaging: '' };
    const subDates = String(row['Subscription dates'] || '').trim();
    const term = subDates || String(row['Sub start date (MM/DD/YYYY)'] || '—');

    return {
      name: row['Opportunity Name'] || 'Customer',
      health: { label: '—', class: 'unknown' },
      sub: row['Sub #'] || '—',
      term,
      tcv: row['TCV $'] != null ? String(row['TCV $']) : '—',
      aar: row['AAR $'] != null ? String(row['AAR $']) : '—',
      segment: row['SL2'] || '—',
      partner: row['Partner'] || '—',
      collabAe: row['Collab AE/SE'] || '—',
      serviceLines: row['Platforms'] || row['Service lines'] || '—',
      csmModel: row['CSM Engagement Model (linked)'] || '—',
      orgId: row['Customer org id'] || '—',
      entitled: row['Entitled Lic Calling'] != null ? String(row['Entitled Lic Calling']) : '—',
      prov: row['Providioned Lic Calling'] != null ? String(row['Providioned Lic Calling']) : '—',
      active: row['Active Lic Calling'] != null ? String(row['Active Lic Calling']) : '—',
      actPct: row['Active % of provisioned'] || '—',
      addons: row['Add-ons included or not'] || '—',
      linked: row['Opportunity (linked)'] || '',
      salesforceUrl: String(row['Salesforce URL'] || '').trim(),
      gatheredBy: row['Data gathered by'] || '',
      gatheredDate: row['Data gathered date'] || '',
      extCalls: row['External calls'] || '—',
      notes,
    };
  }

  function renderFromRow(row) {
    const m = buildModel(row);
    const gathered =
      m.gatheredBy || m.gatheredDate
        ? `Data gathered${m.gatheredBy ? ' by ' + m.gatheredBy : ''}${m.gatheredDate ? ' on ' + m.gatheredDate : ''}`
        : '';

    return `
    <div class="insight-slide">
      <div class="insight-top">
        <div class="insight-title-block">
          <h1 class="insight-h1">${esc(m.name)}</h1>
          <p class="insight-subtitle">Business Insight and Analysis</p>
          ${gathered ? `<p class="insight-meta">${esc(gathered)}</p>` : ''}
          <p class="insight-meta">No matching Lookback BIA slide for this account</p>
        </div>
      </div>
      <div class="insight-panels">
        <section class="insight-panel insight-panel-cyan">
          <h3>Subscription Review</h3>
          <div class="insight-kv"><span>Subscription</span><strong>${esc(m.sub)}</strong></div>
          <div class="insight-kv"><span>Term / dates</span><strong>${esc(m.term)}</strong></div>
          <div class="insight-kv"><span>TCV</span><strong>${esc(m.tcv)}</strong></div>
          <div class="insight-kv"><span>AAR</span><strong>${esc(m.aar)}</strong></div>
          <div class="insight-kv"><span>Partner</span><strong>${esc(m.partner)}</strong></div>
        </section>
        <section class="insight-panel insight-panel-orange">
          <h3>Provisioning &amp; Usage Data</h3>
          <div class="insight-kv"><span>Customer Org ID</span><strong class="insight-mono">${orgIdLinkHtml(m.orgId)}</strong></div>
          <div class="insight-kv"><span>Entitled</span><strong>${esc(m.entitled)}</strong></div>
          <div class="insight-kv"><span>Active</span><strong>${esc(m.active)}</strong></div>
        </section>
        <section class="insight-panel insight-panel-magenta">
          <h3>Feature use &amp; Add-ons</h3>
          <div class="insight-kv"><span>Add-ons</span><strong>${esc(m.addons)}</strong></div>
        </section>
      </div>
      <div class="insight-footer">© Lookback Program · Cisco Confidential</div>
    </div>`;
  }

  function render(row) {
    return renderFromRow(row);
  }

  function open(row) {
    if (typeof BiaTemplate !== 'undefined') {
      const bia = BiaTemplate.findSlide(row);
      if (bia) {
        openBia(bia, row);
        return;
      }
    }
    openOverlay(renderFromRow(row));
  }

  function close() {
    const overlay = document.getElementById('accountInsightOverlay');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  function openByIndex(dataArray, idx) {
    const row = dataArray[idx];
    if (row) open(row);
  }

  return { open, close, openByIndex, openBia, buildModel, render };
})();
