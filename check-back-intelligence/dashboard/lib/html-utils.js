/**
 * HTML escaping and insight-slide UI fragments.
 */
class DashboardHtml {
  static esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  static orgLink(id) {
    const prefix = CheckBack.Dashboard.Constants.WEBEX_ORG_ADMIN_PREFIX;
    const v = String(id || '').trim();
    if (!v) return '—';
    const href = prefix + encodeURIComponent(v);
    return `<a href="${href.replace(/"/g, '&quot;')}" target="_blank" rel="noopener noreferrer" class="customer-link">${DashboardHtml.esc(v)}</a>`;
  }

  static linkLabelForUrl(url) {
    const u = String(url || '').trim();
    if (!u) return 'Link';
    if (/force\.com/i.test(u)) return 'S&C';
    if (/success/i.test(u) && /portal|webex/i.test(u)) return 'Success Portal';
    try {
      return new URL(u).hostname.replace(/^www\./, '');
    } catch {
      return 'Link';
    }
  }

  static escAttr(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;');
  }

  static editableAttrs(col) {
    if (!col) return '';
    return ` class="bia-editable-value" data-col="${DashboardHtml.escAttr(col)}" contenteditable="false"`;
  }

  static kv(label, value, col) {
    const raw = BiaSanitizer.cleanVal(value);
    if (!raw) return '';
    const isLong =
      label === 'Links' ||
      label === 'Term' ||
      raw.length > 72 ||
      /^https?:\/\//i.test(raw);
    let inner = DashboardHtml.esc(raw);
    if (label === 'Customer Org ID' && !col) {
      inner = DashboardHtml.orgLink(raw);
    }
    if (label === 'Links' && /^https?:\/\//i.test(raw)) {
      const href = raw.replace(/"/g, '&quot;');
      inner = `<a href="${href}" target="_blank" rel="noopener noreferrer" class="customer-link">${DashboardHtml.esc(DashboardHtml.linkLabelForUrl(raw))}</a>`;
    }
    const stackClass =
      isLong || label === 'Links' || label === 'Customer Org ID' ? ' insight-kv-stack' : '';
    const attrs = col ? DashboardHtml.editableAttrs(col) : '';
    return `<div class="insight-kv${stackClass}"><span>${DashboardHtml.esc(label)}</span><strong${attrs}>${inner}</strong></div>`;
  }

  static licBar(label, raw, col) {
    const mappedCol = col || CheckBack.Dashboard.BiaSlideEditor?.LIC_LABEL_COL?.[label] || '';
    const s = BiaSanitizer.sanitizeField(raw);
    const m = s.match(/(\d[\d,]*)\s*\/\s*(\d[\d,]*)\s*\((\d+)%\)/);
    if (!m) return DashboardHtml.kv(label, s || '—', mappedCol);
    const u = parseFloat(m[1].replace(/,/g, ''));
    const t = parseFloat(m[2].replace(/,/g, ''));
    const pct = t ? Math.min(100, Math.round((u / t) * 100)) : parseInt(m[3], 10) || 0;
    const attrs = mappedCol ? DashboardHtml.editableAttrs(mappedCol) : '';
    return `<div class="insight-lic-row">
      <span class="insight-lic-label">${DashboardHtml.esc(label)}</span>
      <span class="insight-lic-nums"${attrs}>${DashboardHtml.esc(m[1])}/${DashboardHtml.esc(m[2])} (${pct}%)</span>
      <div class="insight-lic-bar"><div class="insight-lic-fill" style="width:${pct}%"></div></div>
    </div>`;
  }
}

CheckBack.Dashboard.Html = DashboardHtml;
