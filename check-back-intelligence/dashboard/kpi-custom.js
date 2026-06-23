/**
 * User-defined KPI cards — persisted in localStorage, merged into buildKPIs().
 */
const CustomKpi = (function () {
  const STORAGE_KEY = 'dashboard_custom_kpis';
  const LAYOUT_KEY = 'dashboard_kpi_layout';
  const COLORS = ['blue', 'green', 'orange', 'purple', 'yellow', 'pink', 'teal', 'cyan'];
  const METRICS = [
    { id: 'count', label: 'Count rows' },
    { id: 'sum', label: 'Sum column' },
    { id: 'avg', label: 'Average column' },
    { id: 'pct_rows', label: '% rows matching filter' },
    { id: 'ratio_sum', label: 'Ratio (sum A ÷ sum B)' },
    { id: 'distinct', label: 'Distinct values in column' },
  ];

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function save(defs) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(defs));
  }

  function getMode() {
    return typeof dashboardMode !== 'undefined' ? dashboardMode : 'checkback';
  }

  function loadLayout() {
    try {
      const all = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
      return all[getMode()] || { order: [], hidden: [] };
    } catch {
      return { order: [], hidden: [] };
    }
  }

  function saveLayout(layout) {
    const all = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
    all[getMode()] = layout;
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(all));
  }

  function isCustomId(id) {
    return String(id || '').startsWith('kpi-');
  }

  function ensureIds(kpis) {
    return kpis.map((k) => ({
      ...k,
      id: k.id || k.customId || 'kpi-' + String(k.label || 'custom').toLowerCase().replace(/[^a-z0-9]+/g, '-'),
    }));
  }

  function applyLayout(allKpis) {
    const layout = loadLayout();
    const withIds = ensureIds(allKpis);
    window._kpiAllIds = withIds.map((k) => k.id);

    let order = (layout.order || []).filter((id) => window._kpiAllIds.includes(id));
    withIds.forEach((k) => {
      if (!order.includes(k.id)) order.push(k.id);
    });

    const byId = Object.fromEntries(withIds.map((k) => [k.id, k]));
    window._kpiHiddenMeta = Object.fromEntries(withIds.map((k) => [k.id, k.label]));
    const validIds = new Set(withIds.map((k) => k.id));
    const prunedHidden = (layout.hidden || []).filter((id) => validIds.has(id));
    if (prunedHidden.length !== (layout.hidden || []).length) {
      layout.hidden = prunedHidden;
      saveLayout(layout);
    }
    const hidden = new Set(prunedHidden);
    return order.filter((id) => !hidden.has(id)).map((id) => byId[id]).filter(Boolean);
  }

  function reorderKpis(fromId, toId) {
    if (!fromId || !toId || fromId === toId) return;
    const layout = loadLayout();
    const allIds = window._kpiAllIds || [];
    let order = (layout.order || []).filter((id) => allIds.includes(id));
    allIds.forEach((id) => {
      if (!order.includes(id)) order.push(id);
    });
    const fromIdx = order.indexOf(fromId);
    const toIdx = order.indexOf(toId);
    if (fromIdx < 0 || toIdx < 0) return;
    order.splice(fromIdx, 1);
    order.splice(toIdx, 0, fromId);
    layout.order = order;
    saveLayout(layout);
    if (typeof buildKPIs === 'function') buildKPIs();
  }

  function hideKpi(id) {
    if (isCustomId(id)) {
      save(load().filter((d) => d.id !== id));
      const layout = loadLayout();
      layout.order = (layout.order || []).filter((x) => x !== id);
      layout.hidden = (layout.hidden || []).filter((x) => x !== id);
      saveLayout(layout);
    } else {
      const layout = loadLayout();
      if (!(layout.hidden || []).includes(id)) {
        layout.hidden = [...(layout.hidden || []), id];
      }
      saveLayout(layout);
    }
    if (typeof buildKPIs === 'function') buildKPIs();
  }

  function restoreKpi(id) {
    const layout = loadLayout();
    layout.hidden = (layout.hidden || []).filter((x) => x !== id);
    saveLayout(layout);
    if (typeof buildKPIs === 'function') buildKPIs();
  }

  function resetLayout(silent) {
    if (!silent && !confirm('Reset KPI order and restore all hidden KPIs?')) return;
    const all = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
    delete all[getMode()];
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(all));
    if (!silent && typeof buildKPIs === 'function') buildKPIs();
  }

  function uid() {
    return 'kpi-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
  }

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtLicenseCount(n) {
    return Math.round(Number(n) || 0).toLocaleString();
  }

  function parseCellNum(val, useLicense, col, row, kind) {
    if (useLicense) {
      if (
        col &&
        row &&
        typeof CheckBackDashboard !== 'undefined' &&
        CheckBackDashboard.licenseCellTotal
      ) {
        return CheckBackDashboard.licenseCellTotal(val, col, row, kind);
      }
      if (
        col &&
        typeof CheckBackDashboard !== 'undefined' &&
        CheckBackDashboard.licenseCellTotal
      ) {
        return CheckBackDashboard.licenseCellTotal(val, col);
      }
      if (typeof CheckBackDashboard !== 'undefined' && CheckBackDashboard.parseLicenseNumbers) {
        return CheckBackDashboard.parseLicenseNumbers(val);
      }
    }
    return typeof numVal === 'function' ? numVal(val) : parseFloat(String(val).replace(/[^0-9.-]/g, '')) || 0;
  }

  function rowMatchesFilter(r, def) {
    if (!def.filterCol) return true;
    const v = String(r[def.filterCol] ?? '').trim();
    const f = String(def.filterVal ?? '').trim();
    const op = def.filterOp || 'eq';
    if (op === 'eq') return v === f;
    if (op === 'neq') return v !== f;
    if (op === 'contains') return v.toLowerCase().includes(f.toLowerCase());
    if (op === 'notempty') return v.length > 0;
    return true;
  }

  function evaluateOne(def, rows) {
    const filtered = rows.filter((r) => rowMatchesFilter(r, def));
    let val = '—';
    let sub = def.sub || '';

    switch (def.metric) {
      case 'count':
        val = filtered.length.toLocaleString();
        if (!sub) sub = `${filtered.length.toLocaleString()} records`;
        break;
      case 'sum': {
        const col = def.column;
        let total = 0;
        filtered.forEach((r) => {
          total += parseCellNum(r[col], def.useLicenseParse, col, r);
        });
        val = def.useLicenseParse
          ? fmtLicenseCount(total)
          : typeof fmtNum === 'function'
            ? fmtNum(total)
            : total.toLocaleString();
        if (!sub) sub = col ? `Sum of ${col}` : 'Sum';
        break;
      }
      case 'avg': {
        const col = def.column;
        let total = 0;
        let n = 0;
        filtered.forEach((r) => {
          const x = parseCellNum(r[col], def.useLicenseParse, col, r);
          if (x || r[col] !== '' && r[col] != null) {
            total += x;
            n += 1;
          }
        });
        const avg = n ? total / n : 0;
        val = def.useLicenseParse
          ? fmtLicenseCount(Math.round(avg))
          : typeof fmtNum === 'function'
            ? fmtNum(Math.round(avg))
            : Math.round(avg).toLocaleString();
        if (!sub) sub = col ? `Avg of ${col}` : 'Average';
        break;
      }
      case 'pct_rows': {
        const base = rows.length;
        const match = filtered.length;
        const pct = base ? Math.round((match / base) * 100) : 0;
        val = pct + '%';
        if (!sub) sub = `${match.toLocaleString()} of ${base.toLocaleString()} rows`;
        break;
      }
      case 'ratio_sum': {
        const colA = def.columnA;
        const colB = def.columnB;
        let sumA = 0;
        let sumB = 0;
        filtered.forEach((r) => {
          sumA += parseCellNum(r[colA], def.useLicenseParse, colA, r, 'provisioned');
          sumB += parseCellNum(r[colB], def.useLicenseParse, colB, r, 'entitled');
        });
        const pct = sumB ? Math.round((sumA / sumB) * 100) : 0;
        val = pct + '%';
        const aFmt = def.useLicenseParse
          ? fmtLicenseCount(sumA)
          : typeof fmtNum === 'function'
            ? fmtNum(sumA)
            : sumA.toLocaleString();
        const bFmt = def.useLicenseParse
          ? fmtLicenseCount(sumB)
          : typeof fmtNum === 'function'
            ? fmtNum(sumB)
            : sumB.toLocaleString();
        if (!sub) sub = `${aFmt} / ${bFmt}`;
        break;
      }
      case 'distinct': {
        const col = def.column;
        const set = new Set(filtered.map((r) => String(r[col] ?? '').trim()).filter(Boolean));
        val = set.size.toLocaleString();
        if (!sub) sub = col ? `Unique ${col}` : 'Distinct count';
        break;
      }
      default:
        val = '—';
        if (!sub) sub = 'Unknown metric';
    }

    const drill =
      def.drillCol && String(def.drillCol).length
        ? { col: def.drillCol, val: def.drillVal ?? '' }
        : { col: null, val: null };

    return {
      id: def.id,
      label: def.label || 'Custom KPI',
      val,
      sub,
      icon: def.icon || '📌',
      color: COLORS.includes(def.color) ? def.color : 'purple',
      drill,
      customId: def.id,
    };
  }

  function evaluateAll(rows) {
    return load().map((d) => evaluateOne(d, rows));
  }

  function renderCard(kpi, idx) {
    const id = esc(kpi.id);
    return `
    <div class="kpi-card ${kpi.color}" data-kpi-id="${id}" onclick="openDrillFromKPI(${idx})" style="cursor:pointer;">
      <button type="button" class="kpi-remove" title="Remove KPI" onclick="event.stopPropagation();CustomKpi.hideKpi('${id}')">×</button>
      <span class="kpi-drag-handle" draggable="true" data-kpi-id="${id}" title="Drag to reorder" onclick="event.stopPropagation()">⠿</span>
      <div class="kpi-drill-hint">🔍 Click to drill</div>
      <div class="kpi-icon">${kpi.icon}</div>
      <div class="kpi-label">${esc(kpi.label)}</div>
      <div class="kpi-value">${esc(kpi.val)}</div>
      <div class="kpi-sub">${esc(kpi.sub)}</div>
      <div class="kpi-bg-icon">${kpi.icon}</div>
    </div>`;
  }

  function attachDragDrop(gridEl) {
    if (!gridEl) return;

    gridEl.querySelectorAll('.kpi-drag-handle').forEach((handle) => {
      handle.addEventListener('dragstart', (e) => {
        e.stopPropagation();
        const id = handle.dataset.kpiId || handle.closest('.kpi-card')?.dataset.kpiId || '';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', id);
        handle.closest('.kpi-card')?.classList.add('kpi-dragging');
      });
      handle.addEventListener('dragend', () => {
        handle.closest('.kpi-card')?.classList.remove('kpi-dragging');
        gridEl.querySelectorAll('.kpi-card').forEach((c) => c.classList.remove('kpi-drop-target'));
      });
    });

    gridEl.querySelectorAll('.kpi-card').forEach((card) => {
      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        card.classList.add('kpi-drop-target');
      });
      card.addEventListener('dragleave', () => card.classList.remove('kpi-drop-target'));
      card.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        card.classList.remove('kpi-drop-target');
        const fromId = e.dataTransfer.getData('text/plain');
        const toId = card.dataset.kpiId;
        reorderKpis(fromId, toId);
      });
    });
  }

  function renderGrid(gridId, builtInKpis) {
    const rows = typeof filteredData !== 'undefined' ? filteredData : [];
    const custom = evaluateAll(rows);
    const all = ensureIds(builtInKpis).concat(custom);
    window._kpiDefs = applyLayout(all);
    const el = document.getElementById(gridId);
    if (!el) return;
    el.innerHTML = window._kpiDefs.map((k, i) => renderCard(k, i)).join('');
    attachDragDrop(el);
  }

  function columnOptions(selected) {
    const cols = typeof allColumns !== 'undefined' ? allColumns : [];
    return cols
      .map(
        (c) =>
          `<option value="${String(c).replace(/"/g, '&quot;')}"${c === selected ? ' selected' : ''}>${c}</option>`
      )
      .join('');
  }

  function fillColumnSelects(def) {
    def = def || {};
    ['kpiFormColumn', 'kpiFormColumnA', 'kpiFormColumnB', 'kpiFormFilterCol', 'kpiFormDrillCol'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      const sel =
        id === 'kpiFormColumn'
          ? def.column
          : id === 'kpiFormColumnA'
            ? def.columnA
            : id === 'kpiFormColumnB'
              ? def.columnB
              : id === 'kpiFormFilterCol'
                ? def.filterCol
                : def.drillCol;
      el.innerHTML = '<option value="">—</option>' + columnOptions(sel);
    });
  }

  function updateFormVisibility() {
    const metric = document.getElementById('kpiFormMetric')?.value || 'count';
    const showCol = ['sum', 'avg', 'distinct'].includes(metric);
    const showRatio = metric === 'ratio_sum';
    const showLicense = ['sum', 'avg', 'ratio_sum'].includes(metric);
    document.querySelectorAll('[data-kpi-field="column"]').forEach((el) => {
      el.style.display = showCol ? '' : 'none';
    });
    document.querySelectorAll('[data-kpi-field="ratio"]').forEach((el) => {
      el.style.display = showRatio ? '' : 'none';
    });
    document.querySelectorAll('[data-kpi-field="license"]').forEach((el) => {
      el.style.display = showLicense ? '' : 'none';
    });
  }

  function resetForm(def) {
    def = def || {};
    document.getElementById('kpiEditId').value = def.id || '';
    document.getElementById('kpiFormLabel').value = def.label || '';
    document.getElementById('kpiFormIcon').value = def.icon || '📌';
    document.getElementById('kpiFormColor').value = def.color || 'purple';
    document.getElementById('kpiFormMetric').value = def.metric || 'count';
    document.getElementById('kpiFormUseLicense').checked = !!def.useLicenseParse;
    document.getElementById('kpiFormFilterVal').value = def.filterVal || '';
    document.getElementById('kpiFormFilterOp').value = def.filterOp || 'eq';
    document.getElementById('kpiFormSub').value = def.sub || '';
    document.getElementById('kpiFormDrillVal').value = def.drillVal ?? '';
    fillColumnSelects(def);
    updateFormVisibility();
    const title = document.getElementById('kpiModalTitle');
    if (title) title.textContent = def.id ? '✏️ Edit custom KPI' : '➕ Add custom KPI';
  }

  function readForm() {
    return {
      id: document.getElementById('kpiEditId').value || uid(),
      label: document.getElementById('kpiFormLabel').value.trim() || 'Custom KPI',
      icon: document.getElementById('kpiFormIcon').value.trim() || '📌',
      color: document.getElementById('kpiFormColor').value,
      metric: document.getElementById('kpiFormMetric').value,
      column: document.getElementById('kpiFormColumn').value,
      columnA: document.getElementById('kpiFormColumnA').value,
      columnB: document.getElementById('kpiFormColumnB').value,
      useLicenseParse: document.getElementById('kpiFormUseLicense').checked,
      filterCol: document.getElementById('kpiFormFilterCol').value,
      filterVal: document.getElementById('kpiFormFilterVal').value,
      filterOp: document.getElementById('kpiFormFilterOp').value,
      sub: document.getElementById('kpiFormSub').value.trim(),
      drillCol: document.getElementById('kpiFormDrillCol').value,
      drillVal: document.getElementById('kpiFormDrillVal').value,
    };
  }

  function openAdd() {
    resetForm({});
    document.getElementById('kpiModal').classList.add('open');
  }

  function openEdit(id) {
    const def = load().find((d) => d.id === id);
    if (!def) return;
    resetForm(def);
    document.getElementById('kpiManageModal').classList.remove('open');
    document.getElementById('kpiModal').classList.add('open');
  }

  function closeModal() {
    document.getElementById('kpiModal').classList.remove('open');
  }

  function saveForm() {
    const def = readForm();
    if (!def.label) {
      alert('Label is required.');
      return;
    }
    if (['sum', 'avg', 'distinct'].includes(def.metric) && !def.column) {
      alert('Select a column for this metric.');
      return;
    }
    if (def.metric === 'ratio_sum' && (!def.columnA || !def.columnB)) {
      alert('Select both columns for the ratio.');
      return;
    }
    const defs = load();
    const idx = defs.findIndex((d) => d.id === def.id);
    if (idx >= 0) defs[idx] = def;
    else defs.push(def);
    save(defs);
    closeModal();
    if (typeof buildKPIs === 'function') buildKPIs();
  }

  function openManage() {
    const list = document.getElementById('kpiManageList');
    const defs = load();
    const layout = loadLayout();
    const hidden = layout.hidden || [];
    let html = '';

    if (hidden.length) {
      html += '<div class="kpi-manage-section"><div class="kpi-manage-heading">Hidden KPIs</div>';
      html += hidden
        .map(
          (id) => `
        <div class="kpi-manage-row">
          <div class="kpi-manage-info">
            <div class="kpi-manage-label">${esc((window._kpiHiddenMeta && window._kpiHiddenMeta[id]) || id)}</div>
            <div class="kpi-manage-meta">Hidden</div>
          </div>
          <button type="button" class="btn btn-outline btn-sm" onclick="CustomKpi.restoreKpi('${esc(id)}')">Restore</button>
        </div>`
        )
        .join('');
      html += '</div>';
    }

    if (defs.length) {
      html += '<div class="kpi-manage-section"><div class="kpi-manage-heading">Custom KPIs</div>';
      html += defs
        .map(
          (d) => `
        <div class="kpi-manage-row">
          <span class="kpi-manage-icon">${d.icon || '📌'}</span>
          <div class="kpi-manage-info">
            <div class="kpi-manage-label">${esc(d.label)}</div>
            <div class="kpi-manage-meta">${esc(METRICS.find((m) => m.id === d.metric)?.label || d.metric)}</div>
          </div>
          <button type="button" class="btn btn-outline btn-sm" onclick="CustomKpi.openEdit('${d.id}')">Edit</button>
          <button type="button" class="btn btn-outline btn-sm" onclick="CustomKpi.remove('${d.id}')">Delete</button>
        </div>`
        )
        .join('');
      html += '</div>';
    }

    if (!html) {
      html = '<p class="kpi-manage-empty">No hidden or custom KPIs. Drag cards to reorder; use × on a card to remove.</p>';
    }

    list.innerHTML = html;
    document.getElementById('kpiManageModal').classList.add('open');
  }

  function closeManage() {
    document.getElementById('kpiManageModal').classList.remove('open');
  }

  function remove(id) {
    if (!confirm('Delete this custom KPI?')) return;
    hideKpi(id);
    openManage();
  }

  return {
    load,
    save,
    evaluateAll,
    renderGrid,
    openAdd,
    openEdit,
    closeModal,
    saveForm,
    openManage,
    closeManage,
    remove,
    hideKpi,
    restoreKpi,
    resetLayout,
    reorderKpis,
    updateFormVisibility,
    METRICS,
    COLORS,
  };
})();
