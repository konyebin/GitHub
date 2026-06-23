/**
 * In-slide editing: map rendered fields ↔ workbook columns; sync to rawData on save.
 */
class BiaSlideEditor {
  static LIC_LABEL_COL = {
    Professional: 'Lic Professional (used/entitled)',
    Workspace: 'Lic Workspace (used/entitled)',
  };

  static rowKey(row) {
    const org = String(row?.['Customer org id'] ?? '').trim();
    const name = String(row?.['Opportunity Name'] ?? '').trim();
    return `${org}\0${name}`;
  }

  static findRowIndex(rows, key) {
    if (!rows?.length || !key) return -1;
    return rows.findIndex((r) => BiaSlideEditor.rowKey(r) === key);
  }

  static serializeAddons(grid) {
    if (!grid || !Object.keys(grid).length) return '';
    return Object.entries(grid)
      .map(([name, cells]) => {
        const p = cells?.P ?? cells?.p ?? '-';
        const t = cells?.T ?? cells?.t ?? '-';
        const u = cells?.U ?? cells?.u ?? '-';
        return `${name}: ${p} / ${t} / ${u}`;
      })
      .join('; ');
  }

  static parseAddonsFromText(text) {
    const names = CheckBack.Dashboard.Constants.ADDON_ROWS;
    const out = {};
    const raw = String(text || '').trim();
    if (!raw) return out;
    if (raw.startsWith('{')) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') return parsed;
      } catch {
        /* fall through */
      }
    }
    names.forEach((name) => {
      const re = new RegExp(
        `${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*:?\\s*([^;\\n]+)`,
        'i'
      );
      const m = raw.match(re);
      if (!m) return;
      const parts = String(m[1])
        .trim()
        .split(/\s*\/\s*|\s+/);
      if (parts.length >= 3) {
        out[name] = { P: parts[0], T: parts[1], U: parts[2] };
      }
    });
    return out;
  }

  static addonsFromRow(row) {
    const json = String(row?._addonsPtu || '').trim();
    if (json.startsWith('{')) {
      try {
        const parsed = JSON.parse(json);
        if (parsed && typeof parsed === 'object') return parsed;
      } catch {
        /* fall through */
      }
    }
    return BiaSlideEditor.parseAddonsFromText(row?.['Add-ons included or not']);
  }

  static collectAddonEdits(root) {
    const grid = {};
    if (!root) return grid;
    root.querySelectorAll('.bia-editable-addon[data-addon-name]').forEach((el) => {
      const name = el.getAttribute('data-addon-name');
      const slot = el.getAttribute('data-addon-slot');
      if (!name || !slot) return;
      if (!grid[name]) grid[name] = { P: '-', T: '-', U: '-' };
      grid[name][slot] = el.innerText.replace(/\u00a0/g, ' ').trim() || '-';
    });
    return grid;
  }

  static resolveRowIndex(rows, row, rowKey) {
    if (!rows?.length) return -1;
    if (row) {
      const byRef = rows.indexOf(row);
      if (byRef >= 0) return byRef;
    }
    let idx = BiaSlideEditor.findRowIndex(rows, rowKey);
    if (idx >= 0) return idx;
    const name = String(row?.['Opportunity Name'] ?? '').trim();
    if (name) {
      idx = rows.findIndex((r) => String(r['Opportunity Name'] || '').trim() === name);
      if (idx >= 0) return idx;
    }
    return -1;
  }

  static readEditableValue(el) {
    const a = el.querySelector('a.customer-link[href]');
    if (a) {
      const href = a.getAttribute('href');
      if (href && href.startsWith('http')) return href.trim();
    }
    const text = el.innerText.replace(/\u00a0/g, ' ').trim();
    if (el.classList.contains('insight-notes-edit') && /^Click to add notes…$/i.test(text)) {
      return '';
    }
    return text;
  }

  static isPlaceholderValue(val) {
    const s = String(val ?? '').trim();
    return s === '' || s === '—' || s === '-' || s === '–';
  }

  static collectEdits(root) {
    const out = {};
    if (!root) return out;
    root.querySelectorAll('.bia-editable-value[data-col]').forEach((el) => {
      const col = el.getAttribute('data-col');
      if (!col) return;
      const val = BiaSlideEditor.readEditableValue(el);
      if (BiaSlideEditor.isPlaceholderValue(val)) return;
      out[col] = val;
    });
    const addonGrid = BiaSlideEditor.collectAddonEdits(root);
    if (Object.keys(addonGrid).length) {
      out._addonsPtu = JSON.stringify(addonGrid);
      out['Add-ons included or not'] = BiaSlideEditor.serializeAddons(addonGrid);
    }
    return out;
  }

  static flattenLinksForEdit(root) {
    root.querySelectorAll('.insight-kv strong a.customer-link, .insight-link-edit-row a.customer-link').forEach((a) => {
      const text = a.getAttribute('href') || a.textContent || '';
      a.replaceWith(document.createTextNode(text));
    });
  }

  static setEditMode(root, on) {
    if (!root) return;
    if (on) BiaSlideEditor.flattenLinksForEdit(root);
    root.classList.toggle('bia-slide-editing', Boolean(on));
    root.querySelectorAll('.bia-editable-value[data-col], .bia-editable-addon[data-addon-name]').forEach((el) => {
      el.contentEditable = on ? 'true' : 'false';
    });
  }

  static applyEditsToRows(edits, ctx, stores) {
    if (!edits || !Object.keys(edits).length) return { ok: false, reason: 'empty' };
    const rowKey = typeof ctx === 'string' ? ctx : ctx?.rowKey;
    const rowRef = typeof ctx === 'object' ? ctx?.rowRef : null;
    const preferIdx = typeof ctx === 'object' ? ctx?.rawIndex : -1;
    let updated = 0;
    (stores || []).forEach((rows) => {
      let idx = -1;
      if (preferIdx >= 0 && rows[preferIdx] === rowRef) idx = preferIdx;
      if (idx < 0) idx = BiaSlideEditor.resolveRowIndex(rows, rowRef, rowKey);
      if (idx < 0) return;
      Object.assign(rows[idx], edits);
      updated += 1;
    });
    return { ok: updated > 0, updated };
  }
}

CheckBack.Dashboard.BiaSlideEditor = BiaSlideEditor;
