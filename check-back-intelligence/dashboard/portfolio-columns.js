/**
 * Portfolio table column labels, order, width, collapse — persisted in localStorage.
 */
const PortfolioColumns = (function () {
  const LAYOUT_KEY = 'dashboard_table_columns';
  const LABELS = {
    'Calling Setup Assist included (Y/N)': 'Setup Assist included',
  };

  let resizeState = null;

  function getMode() {
    return typeof dashboardMode !== 'undefined' ? dashboardMode : 'checkback';
  }

  function load() {
    try {
      const all = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
      return all[getMode()] || { order: [], widths: {}, collapsed: [] };
    } catch {
      return { order: [], widths: {}, collapsed: [] };
    }
  }

  function save(layout) {
    const all = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
    all[getMode()] = layout;
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(all));
  }

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escAttr(s) {
    return esc(s).replace(/'/g, '&#39;');
  }

  function displayLabel(col) {
    return LABELS[col] || col;
  }

  function orderedColumns(visibleCols) {
    const visible = visibleCols || [];
    const layout = load();
    const set = new Set(visible);
    let order = (layout.order || []).filter((c) => set.has(c));
    visible.forEach((c) => {
      if (!order.includes(c)) order.push(c);
    });
    return order;
  }

  function syncVisible(visibleCols) {
    const layout = load();
    layout.order = orderedColumns(visibleCols);
    save(layout);
  }

  function isCollapsed(col) {
    return (load().collapsed || []).includes(col);
  }

  function getWidth(col) {
    const w = load().widths?.[col];
    return typeof w === 'number' && w > 0 ? w : null;
  }

  function widthStyle(col) {
    if (isCollapsed(col)) return 'width:44px;min-width:44px;max-width:44px';
    const w = getWidth(col);
    if (w) return `width:${w}px;min-width:${w}px;max-width:${w}px`;
    return '';
  }

  function toggleCollapse(col) {
    const layout = load();
    const set = new Set(layout.collapsed || []);
    if (set.has(col)) set.delete(col);
    else set.add(col);
    layout.collapsed = [...set];
    save(layout);
    if (typeof buildTable === 'function') buildTable();
  }

  function reorderColumns(fromCol, toCol) {
    if (!fromCol || !toCol || fromCol === toCol) return;
    const cols = typeof visibleColumns !== 'undefined' ? visibleColumns : [];
    const layout = load();
    let order = orderedColumns(cols);
    const fromIdx = order.indexOf(fromCol);
    const toIdx = order.indexOf(toCol);
    if (fromIdx < 0 || toIdx < 0) return;
    order.splice(fromIdx, 1);
    order.splice(toIdx, 0, fromCol);
    layout.order = order;
    save(layout);
    if (typeof buildTable === 'function') buildTable();
  }

  function setWidth(col, px) {
    const layout = load();
    layout.widths = layout.widths || {};
    layout.widths[col] = Math.max(56, Math.min(520, Math.round(px)));
    save(layout);
  }

  function renderTh(col, sortCol, sortDir) {
    const label = displayLabel(col);
    const sortCls =
      sortCol === col ? (sortDir === 'asc' ? 'sort-asc' : sortDir === 'desc' ? 'sort-desc' : '') : '';
    const collapsed = isCollapsed(col);
    const safe = col.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    const style = widthStyle(col);
    return `<th class="portfolio-th ${sortCls}${collapsed ? ' col-collapsed' : ''}" data-col="${escAttr(col)}"${
      style ? ` style="${style}"` : ''
    }>
      <span class="col-drag-handle" draggable="true" title="Drag to reorder column">⠿</span>
      <span class="col-header-label" onclick="sortTable('${safe}')" title="${escAttr(label)}">${
      collapsed ? '▸' : esc(label)
    }</span>
      <button type="button" class="col-collapse-btn" onclick="event.stopPropagation();PortfolioColumns.toggleCollapse('${safe}')" title="${
      collapsed ? 'Expand column' : 'Minimize column'
    }">${collapsed ? '+' : '−'}</button>
      <span class="col-resize-handle" onmousedown="PortfolioColumns.startResize(event,'${safe}')" title="Drag to resize"></span>
    </th>`;
  }

  function renderHead(visibleCols, sortCol, sortDir) {
    const cols = orderedColumns(visibleCols);
    return `<tr>${cols.map((col) => renderTh(col, sortCol, sortDir)).join('')}</tr>`;
  }

  function bindTable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const thead = table.querySelector('thead');
    if (!thead) return;

    thead.querySelectorAll('.col-drag-handle').forEach((handle) => {
      handle.addEventListener('dragstart', (e) => {
        e.stopPropagation();
        const th = handle.closest('th');
        const col = th?.dataset?.col || '';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', col);
        th?.classList.add('col-dragging');
      });
      handle.addEventListener('dragend', () => {
        handle.closest('th')?.classList.remove('col-dragging');
        thead.querySelectorAll('th').forEach((th) => th.classList.remove('col-drop-target'));
      });
    });

    thead.querySelectorAll('th.portfolio-th').forEach((th) => {
      th.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        th.classList.add('col-drop-target');
      });
      th.addEventListener('dragleave', () => th.classList.remove('col-drop-target'));
      th.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        th.classList.remove('col-drop-target');
        const fromCol = e.dataTransfer.getData('text/plain');
        const toCol = th.dataset.col;
        reorderColumns(fromCol, toCol);
      });
    });
  }

  function startResize(e, col) {
    e.preventDefault();
    e.stopPropagation();
    const th = e.target.closest('th');
    if (!th) return;
    resizeState = { col, startX: e.clientX, startW: th.offsetWidth };
    document.body.classList.add('col-resizing');
    document.addEventListener('mousemove', onResizeMove);
    document.addEventListener('mouseup', onResizeEnd);
  }

  function onResizeMove(e) {
    if (!resizeState) return;
    const w = resizeState.startW + (e.clientX - resizeState.startX);
    setWidth(resizeState.col, w);
    const style = widthStyle(resizeState.col);
    document.querySelectorAll('#dataTable [data-col]').forEach((el) => {
      if (el.getAttribute('data-col') === resizeState.col) el.style.cssText = style;
    });
  }

  function onResizeEnd() {
    resizeState = null;
    document.body.classList.remove('col-resizing');
    document.removeEventListener('mousemove', onResizeMove);
    document.removeEventListener('mouseup', onResizeEnd);
    if (typeof buildTable === 'function') buildTable();
  }

  function resetLayout(silent) {
    const all = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
    delete all[getMode()];
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(all));
    if (!silent && typeof buildTable === 'function') buildTable();
  }

  return {
    displayLabel,
    orderedColumns,
    syncVisible,
    isCollapsed,
    getWidth,
    widthStyle,
    toggleCollapse,
    reorderColumns,
    setWidth,
    startResize,
    renderHead,
    bindTable,
    resetLayout,
    LABELS,
  };
})();
