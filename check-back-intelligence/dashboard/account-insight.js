/**
 * Business Insight overlay — delegates rendering to BiaTemplate; supports in-slide edit + save.
 */
const AccountInsight = (function () {
  const Html = CheckBack.Dashboard.Html;
  const Editor = CheckBack.Dashboard.BiaSlideEditor;
  const prefix = CheckBack.Dashboard.Constants.WEBEX_ORG_ADMIN_PREFIX;

  let _stores = null;
  let _ctx = {
    rowKey: '',
    row: null,
    rawIndex: -1,
    listIndex: -1,
    editMode: false,
    dirty: false,
    onSaved: null,
  };

  function filteredRows() {
    return typeof filteredData !== 'undefined' && Array.isArray(filteredData) ? filteredData : [];
  }

  function findListIndex(row) {
    const list = filteredRows();
    if (!list.length || !row) return -1;
    const key = Editor.rowKey(row);
    let idx = list.findIndex((r) => Editor.rowKey(r) === key);
    if (idx >= 0) return idx;
    idx = list.indexOf(row);
    return idx;
  }

  function updateNavButtons() {
    const list = filteredRows();
    const prevBtn = document.getElementById('accountInsightPrevBtn');
    const nextBtn = document.getElementById('accountInsightNextBtn');
    const posEl = document.getElementById('accountInsightNavPos');
    const n = list.length;
    const i = _ctx.listIndex;
    if (prevBtn) prevBtn.disabled = i <= 0;
    if (nextBtn) nextBtn.disabled = i < 0 || i >= n - 1;
    if (posEl) {
      posEl.textContent = n > 0 && i >= 0 ? `${i + 1} / ${n}` : '';
    }
  }

  function saveCtx(row) {
    _ctx.row = row || null;
    _ctx.rowKey = Editor.rowKey(row || {});
    const stores = _stores?.();
    _ctx.rawIndex =
      stores?.raw && row ? Editor.resolveRowIndex(stores.raw, row, _ctx.rowKey) : -1;
  }

  function isOverlayOpen() {
    const overlay = document.getElementById('accountInsightOverlay');
    return Boolean(overlay && overlay.classList.contains('open'));
  }

  function flushPendingEdits() {
    if (!isOverlayOpen() || !_ctx.dirty) return true;
    return saveToWorkbook();
  }

  function configure(opts) {
    if (opts?.getRowStores) _stores = opts.getRowStores;
    if (opts?.onSaved) _ctx.onSaved = opts.onSaved;
  }

  function setStatus(msg, isError) {
    const el = document.getElementById('accountInsightSaveStatus');
    if (!el) return;
    el.textContent = msg || '';
    el.className = isError ? 'account-insight-status is-error' : 'account-insight-status';
  }

  function slideRoot() {
    return document.querySelector('#accountInsightBody .bia-slide');
  }

  function markDirty() {
    _ctx.dirty = true;
    setStatus('Unsaved changes');
  }

  function wireEditListeners(root) {
    if (!root) return;
    root.querySelectorAll('.bia-editable-value[data-col], .bia-editable-addon[data-addon-name]').forEach((el) => {
      el.addEventListener('input', markDirty);
    });
  }

  function openOverlay(html, row, listIndex) {
    const overlay = document.getElementById('accountInsightOverlay');
    const body = document.getElementById('accountInsightBody');
    if (!overlay || !body) return;
    saveCtx(row);
    _ctx.listIndex = typeof listIndex === 'number' ? listIndex : findListIndex(row);
    _ctx.dirty = false;
    body.innerHTML = html;
    wireEditListeners(slideRoot());
    setStatus('');
    updateEditButton();
    updateNavButtons();
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function updateEditButton() {
    const btn = document.getElementById('accountInsightEditBtn');
    if (!btn) return;
    btn.textContent = _ctx.editMode ? 'Done editing' : 'Edit slide';
    btn.classList.toggle('active', _ctx.editMode);
  }

  function toggleEditMode() {
    const root = slideRoot();
    if (!root) return;
    _ctx.editMode = !_ctx.editMode;
    Editor.setEditMode(root, _ctx.editMode);
    updateEditButton();
    if (_ctx.editMode) {
      const first = root.querySelector('.bia-editable-value[data-col]');
      if (first) first.focus();
    }
  }

  function saveToWorkbook() {
    const root = slideRoot();
    if (!root || !_stores) {
      setStatus('Load customer data first', true);
      return false;
    }
    const edits = Editor.collectEdits(root);
    const stores = _stores();
    if (!stores?.raw?.length) {
      setStatus('No workbook loaded', true);
      return false;
    }
    const result = Editor.applyEditsToRows(edits, {
      rowKey: _ctx.rowKey,
      rowRef: _ctx.row,
      rawIndex: _ctx.rawIndex,
    }, [stores.raw, stores.filtered]);
    if (!result.ok) {
      setStatus('Could not find this customer row — close and reopen the slide', true);
      return false;
    }
    if (_ctx.rawIndex >= 0 && stores.raw[_ctx.rawIndex]) {
      _ctx.row = stores.raw[_ctx.rawIndex];
      _ctx.rowKey = Editor.rowKey(_ctx.row);
    }
    _ctx.dirty = false;
    setStatus('Saved — use Full export or Save customer data to download .xlsx');
    if (typeof _ctx.onSaved === 'function') _ctx.onSaved(edits);
    return true;
  }

  function openBia(slide, row) {
    if (typeof BiaTemplate !== 'undefined') {
      const base = BiaTemplate.sanitizeSlide ? BiaTemplate.sanitizeSlide(slide) : slide;
      const merged = row ? BiaTemplate.mergeSlideWithRow(row, base) : base;
      openOverlay(BiaTemplate.render(merged), row || merged);
      return;
    }
    open({ 'Opportunity Name': slide.customerName, 'Customer org id': slide.orgId });
  }

  function buildModel(row) {
    const subDates = String(row['Subscription dates'] || '').trim();
    const term =
      subDates || String(row['Sub Term'] || row['Sub start date (MM/DD/YYYY)'] || '—');

    return {
      name: row['Opportunity Name'] || 'Customer',
      sub: row['Sub #'] || '—',
      term,
      tcv: row['TCV $'] != null ? String(row['TCV $']) : '—',
      aar: row['AAR $'] != null ? String(row['AAR $']) : '—',
      partner: row['Partner'] || '—',
      orgId: row['Customer org id'] || '—',
      entitled:
        row['Provisioned/Entitled Lic Calling'] != null
          ? String(row['Provisioned/Entitled Lic Calling'])
          : row['Entitled Lic Calling'] != null
            ? String(row['Entitled Lic Calling'])
            : '—',
      active: row['Active Lic Calling'] != null ? String(row['Active Lic Calling']) : '—',
      addons: row['Add-ons included or not'] || '—',
      gatheredBy: row['Data gathered by'] || '',
      gatheredDate: row['Data gathered date'] || '',
    };
  }

  /** Legacy fallback when BiaTemplate is unavailable. */
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
          <h1 class="insight-h1 bia-editable-value" data-col="Opportunity Name" contenteditable="false">${Html.esc(m.name)}</h1>
          <p class="insight-subtitle">Business Insight and Analysis</p>
          ${gathered ? `<p class="insight-meta">${Html.esc(gathered)}</p>` : ''}
        </div>
      </div>
      <div class="insight-panels">
        <section class="insight-panel insight-panel-cyan">
          <h3>Subscription Review</h3>
          ${Html.kv('Subscription', m.sub, 'Sub #')}
          ${Html.kv('Term / dates', m.term, 'Subscription dates')}
          ${Html.kv('TCV', m.tcv, 'TCV $')}
          ${Html.kv('AAR', m.aar, 'AAR $')}
          ${Html.kv('Partner', m.partner, 'Partner')}
        </section>
        <section class="insight-panel insight-panel-orange">
          <h3>Provisioning &amp; Usage Data</h3>
          ${Html.kv('Customer Org ID', m.orgId, 'Customer org id')}
          ${Html.kv('Licenses (prov/ent)', m.entitled, 'Provisioned/Entitled Lic Calling')}
          ${Html.kv('Active', m.active, 'Active Lic Calling')}
        </section>
        <section class="insight-panel insight-panel-magenta">
          <h3>Feature use &amp; Add-ons</h3>
          ${Html.kv('Add-ons', m.addons, 'Add-ons included or not')}
        </section>
      </div>
      <div class="insight-footer">© Lookback Program · Cisco Confidential</div>
    </div>`;
  }

  function open(row, listIndex) {
    if (typeof BiaTemplate !== 'undefined' && BiaTemplate.render) {
      const bia = BiaTemplate.findSlide(row);
      const base = bia || BiaTemplate.rowToSlide(row);
      if (base) {
        openOverlay(BiaTemplate.render(BiaTemplate.mergeSlideWithRow(row, base)), row, listIndex);
        return;
      }
    }
    openOverlay(renderFromRow(row), row, listIndex);
  }

  function navigateTo(delta) {
    const list = filteredRows();
    if (!list.length) return false;
    const nextIdx =
      _ctx.listIndex >= 0 ? _ctx.listIndex + delta : findListIndex(_ctx.row) + delta;
    if (nextIdx < 0 || nextIdx >= list.length) return false;
    if (_ctx.dirty) {
      const saved = saveToWorkbook();
      if (!saved) {
        const ok = window.confirm('Discard unsaved slide edits and move to another customer?');
        if (!ok) return false;
        _ctx.dirty = false;
      }
    }
    if (_ctx.editMode) {
      const root = slideRoot();
      if (root) Editor.setEditMode(root, false);
      _ctx.editMode = false;
      updateEditButton();
    }
    open(list[nextIdx], nextIdx);
    return true;
  }

  function previous() {
    return navigateTo(-1);
  }

  function next() {
    return navigateTo(1);
  }

  function exportPdf() {
    if (!isOverlayOpen()) {
      alert('Open a customer Business Insight slide first.');
      return Promise.resolve(false);
    }
    if (_ctx.dirty) {
      const ok = window.confirm('Save slide edits to the workbook before exporting PDF?');
      if (ok && !saveToWorkbook()) return Promise.resolve(false);
    }
    if (typeof ensurePdfLibs !== 'function') {
      alert('PDF libraries are not available.');
      return Promise.resolve(false);
    }
    return ensurePdfLibs()
      .then(() => exportCustomerInsightPdf(_ctx.row))
      .catch((err) => {
        alert('PDF export failed: ' + err.message);
        return false;
      });
  }

  function close(force) {
    if (!force && _ctx.dirty) {
      const ok = window.confirm('Discard unsaved slide edits?');
      if (!ok) return;
    }
    const root = slideRoot();
    if (root) Editor.setEditMode(root, false);
    _ctx.editMode = false;
    _ctx.dirty = false;
    const overlay = document.getElementById('accountInsightOverlay');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
    setStatus('');
  }

  function openByIndex(dataArray, idx) {
    const row = dataArray[idx];
    if (row) open(row, idx);
  }

  return {
    open,
    close,
    openByIndex,
    previous,
    next,
    openBia,
    buildModel,
    render: renderFromRow,
    configure,
    toggleEditMode,
    saveToWorkbook,
    exportPdf,
    flushPendingEdits,
    isOverlayOpen,
  };
})();
