/**
 * Check Back / adoption health KPIs, filters, and charts.
 */
const CheckBackDashboard = (function () {
  const GYR_COL = ' (G/Y/R)';
  const LICENSE_COL =
    (CheckBack.Dashboard.Constants && CheckBack.Dashboard.Constants.LICENSE_COL) ||
    'Provisioned/Entitled Lic Calling';
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
    'Active Lic Calling',
    'CSM name',
    'Migrating from',
    'Migrating to',
  ];
  const DRILL_COLS = [
    'Opportunity Name',
    'TCV $',
    GYR_COL,
    LICENSE_COL,
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
      const label =
        typeof PortfolioColumns !== 'undefined' ? PortfolioColumns.displayLabel(col) : col;
      div.innerHTML = `<label class="filter-label">${label}</label>
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

  function fmtLicenseCount(n) {
    if (typeof LicenseProductParser !== 'undefined' && LicenseProductParser.fmtCount) {
      return LicenseProductParser.fmtCount(n);
    }
    return Math.round(Number(n) || 0).toLocaleString();
  }

  function rowLicenseTotals(row) {
    if (typeof LicenseProductParser !== 'undefined' && LicenseProductParser.rowLicenseTotals) {
      return LicenseProductParser.rowLicenseTotals(row);
    }
    const entitled = parseLicenseNumbers(row['Entitled Lic Calling']);
    const provisioned = parseLicenseNumbers(row['Providioned Lic Calling']);
    const active = parseLicenseNumbers(row['Active Lic Calling']);
    return { entitled, provisioned, active };
  }

  function buildKPIs() {
    const d = filteredData;
    let totalEnt = 0;
    let totalProv = 0;
    let totalAct = 0;
    d.forEach((r) => {
      const t = rowLicenseTotals(r);
      totalEnt += t.entitled;
      totalProv += t.provisioned;
      totalAct += t.active;
    });
    const gyr = countBy(d, GYR_COL);
    const red = gyr['R'] || gyr['r'] || 0;
    const yellow = gyr['Y'] || gyr['y'] || 0;
    const green = gyr['G'] || gyr['g'] || 0;
    const noSetup = d.filter(
      (r) => String(r['Calling Setup Assist included (Y/N)'] || '').toUpperCase() === 'N'
    ).length;
    const provEntPct = totalEnt ? Math.round((totalProv / totalEnt) * 100) : 0;
    const actProvPct = totalProv ? Math.round((totalAct / totalProv) * 100) : 0;

    const kpis = [
      {
        id: 'builtin-total-opportunities',
        label: 'Total Opportunities',
        val: d.length.toLocaleString(),
        sub: 'Customers in current view',
        icon: '📋',
        color: 'blue',
        drill: { col: null, val: null },
      },
      {
        id: 'builtin-provisioned-entitled',
        label: 'Provisioned / Entitled',
        val: provEntPct + '%',
        sub: `${fmtLicenseCount(totalProv)} / ${fmtLicenseCount(totalEnt)} licenses`,
        icon: '📊',
        color: 'purple',
        drill: { col: null, val: null },
      },
      {
        id: 'builtin-active-provisioned',
        label: 'Active / Provisioned',
        val: actProvPct + '%',
        sub: `${fmtLicenseCount(totalAct)} / ${fmtLicenseCount(totalProv)} licenses`,
        icon: '📈',
        color: 'green',
        drill: { col: null, val: null },
      },
      {
        id: 'builtin-gyr',
        label: 'G / Y / R',
        val: `${green} / ${yellow} / ${red}`,
        sub: 'Green · Yellow · Red counts',
        icon: '🚦',
        color: 'yellow',
        drill: { col: GYR_COL, val: 'R' },
      },
      {
        id: 'builtin-no-setup-assist',
        label: 'No Setup Assist',
        val: noSetup.toLocaleString(),
        sub: 'Setup Assist = N',
        icon: '🛠️',
        color: 'orange',
        drill: { col: 'Calling Setup Assist included (Y/N)', val: 'N' },
      },
      {
        id: 'builtin-total-tcv',
        label: 'Total TCV',
        val: fmt(sum(d, 'TCV $')),
        sub: 'Sum of deal values',
        icon: '💰',
        color: 'blue',
        drill: { col: null, val: null },
      },
    ];
    if (typeof CustomKpi !== 'undefined') {
      CustomKpi.renderGrid('kpiGrid', kpis);
    } else {
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

  function licenseCellTotal(val, col, row, kind) {
    if (row && typeof LicenseProductParser !== 'undefined' && LicenseProductParser.rowLicenseTotals) {
      if (col === LICENSE_COL) {
        const t = LicenseProductParser.rowLicenseTotals(row);
        if (kind === 'entitled') return t.entitled;
        if (kind === 'active') return t.active;
        return t.provisioned;
      }
    }
    const columnKind =
      col === LICENSE_COL || col === 'Entitled Lic Calling'
        ? 'entitled'
        : col === 'Providioned Lic Calling'
          ? 'provisioned'
          : col === 'Active Lic Calling'
            ? 'active'
            : null;
    if (columnKind && typeof LicenseProductParser !== 'undefined' && LicenseProductParser.sumPlWsCell) {
      const cellVal =
        col === LICENSE_COL && row ? LicenseProductParser.getLicenseCell(row) : val;
      return LicenseProductParser.sumPlWsCell(cellVal || val, columnKind);
    }
    return parseLicenseNumbers(val);
  }

  function buildLicenseGapChart(d) {
    const labels = d.slice(0, 12).map((r) => String(r['Opportunity Name'] || '?').substring(0, 18));
    const entitled = d.slice(0, 12).map((r) => rowLicenseTotals(r).entitled);
    const prov = d.slice(0, 12).map((r) => rowLicenseTotals(r).provisioned);
    const active = d.slice(0, 12).map((r) => rowLicenseTotals(r).active);
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
        scales: { x: { stacked: false }, y: { beginAtZero: true, ticks: { callback: (v) => fmtLicenseCount(v) } } },
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

  function subNumberLinksHtml(val) {
    if (val == null || val === '') return '';
    const subs = String(val)
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (!subs.length) return '';
    return subs
      .map((sub) => {
        const href = `https://ccrc.cisco.com/subscriptions/detail/${encodeURIComponent(sub)}`;
        const label = String(sub)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');
        return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="customer-link" onclick="event.stopPropagation()">${label}</a>`;
      })
      .join(', ');
  }

  function formatCell(col, val, row) {
    if (col === 'Customer org id') {
      const link = webexOrgLinkHtml(val);
      if (link) return link;
    }
    if (col === 'Sub #') {
      const links = subNumberLinksHtml(val);
      if (links) return links;
    }
    if (row && (col === 'Opportunity (linked)' || col === 'CSM Engagement Model (linked)')) {
      const link = salesforceLinkHtml(row, col);
      if (link) return link;
    }
    if (col === GYR_COL) return getGyrBadge(val);
    if (col === LICENSE_COL && row && typeof LicenseProductParser !== 'undefined') {
      return LicenseProductParser.formatLicenseColumn(row) || val;
    }
    if (col === 'Entitled Lic Calling' && row && typeof LicenseProductParser !== 'undefined') {
      return LicenseProductParser.formatEntitledOnlyColumn(row) || val;
    }
    if (col === 'Providioned Lic Calling' && row && typeof LicenseProductParser !== 'undefined') {
      return LicenseProductParser.formatProvisionedOnlyColumn(row) || val;
    }
    if (col === 'Active Lic Calling') {
      if (typeof LicenseProductParser !== 'undefined') {
        return LicenseProductParser.formatActiveColumn(val) || val;
      }
      const n = licenseCellTotal(val, col);
      return n ? fmtLicenseCount(n) : val;
    }
    if (['TCV $', 'AAR $'].includes(col)) {
      const n = numVal(val);
      return fmt(n);
    }
    return val;
  }

  function rowDetailFields() {
    const pri = [
      'Opportunity Name',
      'TCV $',
      GYR_COL,
      LICENSE_COL,
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

  function portfolioColumnAvailable(col) {
    if (allColumns.includes(col)) return true;
    const hasMerged = allColumns.includes(LICENSE_COL);
    if (!hasMerged) return false;
    if (col === 'Entitled Lic Calling' || col === 'Providioned Lic Calling') return true;
    return false;
  }

  function portfolioSortValue(row, col) {
    if (
      row &&
      (col === 'Entitled Lic Calling' ||
        col === 'Providioned Lic Calling' ||
        col === 'Active Lic Calling' ||
        col === LICENSE_COL)
    ) {
      const t = rowLicenseTotals(row);
      if (col === 'Entitled Lic Calling') return t.entitled;
      if (col === 'Providioned Lic Calling') return t.provisioned;
      if (col === 'Active Lic Calling') return t.active;
      return t.provisioned;
    }
    return numVal(row?.[col]);
  }

  function getPortfolioCols() {
    let cols = PORTFOLIO_COLS.filter((c) => portfolioColumnAvailable(c));
    cols = ensurePortfolioVisibleColumns(cols);
    return cols.length ? cols : allColumns.slice(0, Math.min(12, allColumns.length));
  }

  /** Keep Entitled + Active (not merged prov/ent) visible when workbook uses merged license column. */
  function ensurePortfolioVisibleColumns(cols) {
    const list = [...(cols || [])];
    const hasMerged = allColumns.includes(LICENSE_COL);
    if (!hasMerged) return list;

    const withoutMerged = list.filter((c) => c !== LICENSE_COL);
    const licenseCols = ['Entitled Lic Calling', 'Active Lic Calling'];
    const anchor = withoutMerged.indexOf('Sub #');
    licenseCols.forEach((col, i) => {
      if (withoutMerged.includes(col)) return;
      const at = anchor >= 0 ? anchor + 1 + i : withoutMerged.length;
      withoutMerged.splice(at, 0, col);
    });
    return withoutMerged;
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
    LICENSE_COL,
    parseLicenseNumbers,
    rowLicenseTotals,
    licenseCellTotal,
    fmtLicenseCount,
    formatLicenseCell(row, col) {
      if (col === LICENSE_COL) return LicenseProductParser.formatLicenseColumn(row);
      if (col === 'Entitled Lic Calling') return LicenseProductParser.formatEntitledOnlyColumn(row);
      if (col === 'Providioned Lic Calling') return LicenseProductParser.formatProvisionedOnlyColumn(row);
      if (col === 'Active Lic Calling') return LicenseProductParser.formatActiveColumn(row[col]);
      return row[col];
    },
    portfolioSortValue,
    ensurePortfolioVisibleColumns,
    HIGHLIGHT,
    renderAttachmentUI,
    onAttachmentChange,
    GYR_COL,
  };
})();
