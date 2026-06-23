/* auto-generated — run ./build-bundle.sh after editing dashboard modules */
/**
 * Root namespace for Check Back dashboard modules (concat bundle — order matters in build-bundle.sh).
 */
var CheckBack = typeof CheckBack !== 'undefined' ? CheckBack : {};
CheckBack.Dashboard = CheckBack.Dashboard || {};
/**
 * Shared column names and dashboard constants.
 */
CheckBack.Dashboard.Constants = {
  GYR_COL: ' (G/Y/R)',
  /** Merged license column (provisioned/entitled pairs). Legacy split cols still supported in parsers. */
  LICENSE_COL: 'Provisioned/Entitled Lic Calling',
  LEGACY_ENTITLED_COL: 'Entitled Lic Calling',
  LEGACY_PROVISIONED_COL: 'Providioned Lic Calling',
  WEBEX_ORG_ADMIN_PREFIX: 'https://admin.webex.com/help-desk/org/',
  DEFAULT_LINK_ORDER: ['S&C', 'Success Portal'],
  ADDON_ROWS: [
    'PSTN Cisco Calling Plans',
    'Customer Assist',
    'Attendant Console',
    'AI Receptionist',
    'AI Premium',
  ],
  PORTFOLIO_COLUMN_PREFER: [
    'Opportunity Name',
    ' (G/Y/R)',
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
  ],
  BIA_CANONICAL_COLS: new Set([
    'Opportunity Name',
    'Customer org id',
    ' (G/Y/R)',
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
    'Provisioned/Entitled Lic Calling',
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
  ]),
  WORKBOOK_SUPPLEMENT_COLS: [
    'Opportunity (linked)',
    'Salesforce URL',
    'Closed on (MM/YY)',
    'Competitor',
    'Migrating from',
    'Migrating to',
    'Success Portal',
    'CSM name',
    'Sub Term',
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
  ],
};
/**
 * Sanitization and value normalization for BIA slides and workbook rows.
 */
class BiaSanitizer {
  static isEmptyVal(v) {
    const s = String(v ?? '').trim();
    return !s || s === '—' || s === '-' || /^n\/?a$/i.test(s);
  }

  /** Strip PDF parser bleed (org ids, add-on tables, wrong field merges). */
  static sanitizeField(raw) {
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

  static sanitizeMoney(raw) {
    const s = BiaSanitizer.sanitizeField(raw);
    if (!s || s === '$-' || s === '-') return '';
    if (/Licenses Active|External Calls vs|numbers \(/i.test(s)) return '';
    const m = s.match(/^\$[\d,.]+[KMB]?/i);
    return m ? m[0] : s.split(/\s{2,}/)[0].trim();
  }

  static sanitizeSegment(raw) {
    const s = BiaSanitizer.sanitizeField(raw);
    if (/External Calls|Licenses Active|@cisco\.com/i.test(s)) return '';
    return s;
  }

  static cleanVal(v) {
    const s = BiaSanitizer.sanitizeField(v);
    if (!s || s === '—') return '';
    return s;
  }

  static licPair(raw) {
    const s = BiaSanitizer.sanitizeField(raw);
    const m = s.match(/(\d[\d,]*)\s*\/\s*(\d[\d,]*)/);
    return m ? `${m[1]}/${m[2]}` : s;
  }

  static healthClass(h) {
    const x = String(h || '').toLowerCase();
    if (x === 'good') return { class: 'good', label: 'Good' };
    if (x === 'risk') return { class: 'risk', label: 'Risk' };
    if (x === 'upsell') return { class: 'upsell', label: 'Upsell' };
    return { class: 'unknown', label: h || '—' };
  }

  static healthToGyr(health) {
    const h = String(health || '').toLowerCase();
    if (h === 'good') return 'G';
    if (h === 'risk') return 'R';
    if (h === 'upsell') return 'Y';
    return '';
  }

  static gyrToHealth(gyr) {
    const v = String(gyr || '').trim().toUpperCase();
    const c = v.charAt(0);
    if (c === 'G') return 'Good';
    if (c === 'R') return 'Risk';
    if (c === 'Y') return 'Upsell';
    return '';
  }

  static parseTimelineFromTerm(term) {
    const t = String(term || '');
    let years = 5;
    let currentYear = 2;
    const yrMatch = t.match(/(\d+)\s*yr/i);
    if (yrMatch) years = Math.min(10, Math.max(1, parseInt(yrMatch[1], 10)));
    const yearOf = t.match(/Year\s+(\d+)\s+of\s+(\d+)/i);
    if (yearOf) {
      currentYear = parseInt(yearOf[1], 10) || currentYear;
      years = parseInt(yearOf[2], 10) || years;
    }
    return { years, currentYear };
  }

  static normalizeOrgId(val) {
    return String(val ?? '').trim().toLowerCase();
  }
}

CheckBack.Dashboard.BiaSanitizer = BiaSanitizer;
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
/**
 * Parse Check Back note fields into structured provisioning columns (mirrors src/workbook/note_parser.py).
 */
class NoteParser {
  static PROF_RE =
    /professional(?:\s+calling)?\s+(?:assigned\s+)?(\d[\d,]*)\s*\/\s*(\d[\d,]*)/i;
  static STD_RE = /standard(?:\s+calling)?\s+(?:assigned\s+)?(\d[\d,]*)\s*\/\s*(\d[\d,]*)/i;
  static WS_RE = /workspace(?:\s+calling)?\s+(?:assigned\s+)?(\d[\d,]*)\s*\/\s*(\d[\d,]*)/i;
  static PL_RE = /\bPL[:\s]+(\d[\d,]*)\s*\/\s*(\d[\d,]*)/i;
  /** e.g. "1,265 workspace 335" → Professional 1265, Workspace 335 */
  static PROF_WS_SHORT_RE = /(\d[\d,]*)\s+workspace\s+(\d[\d,]*)/i;
  static EXT_CALLS_RE = /([\d,.]+[KMkm]?)\s*(?:out of|\/)\s*([\d,.]+[KMkm]?)\s*calls/i;
  static ACTIVE_TREND_RE = /active\s*users?[^.;]{0,40}?(UP|DOWN)\s*([+-]?[\d.]+%?)/i;
  static CALL_TREND_RE = /call\s*volume[^.;]{0,40}?(UP|DOWN)\s*([+-]?[\d.]+%?)/i;
  static ACTIVE_PCT_RE = /(\d{1,3})%\s*of\s*provisioned/i;
  static MSG_USAGE_RE =
    /(\d+)\s*active\s*users?[^;]*;?\s*([\d,.]+[KMkm]?)\s*messages?\s*sent/i;

  static pairMatch(m) {
    if (!m) return '';
    return `${m[1]}/${m[2]}`;
  }

  static trendMatch(m) {
    if (!m) return '';
    return `${m[1].toUpperCase()} ${m[2]}`;
  }

  static parseNotesToStructured(analytics, features, addons = '') {
    const combined = [analytics, features, addons].filter(Boolean).join(' ');
    const out = {};

    for (const [re, key] of [
      [NoteParser.PROF_RE, 'Lic Professional (used/entitled)'],
      [NoteParser.STD_RE, 'Lic Standard (used/entitled)'],
      [NoteParser.WS_RE, 'Lic Workspace (used/entitled)'],
    ]) {
      const m = combined.match(re);
      if (m) out[key] = NoteParser.pairMatch(m);
    }

    const pl = combined.match(NoteParser.PL_RE);
    if (pl && !out['Lic Professional (used/entitled)']) {
      out['Lic Professional (used/entitled)'] = NoteParser.pairMatch(pl);
    }

    const ec = combined.match(NoteParser.EXT_CALLS_RE);
    if (ec) out['External calls'] = `${ec[1]} out of ${ec[2]}`;

    const at = combined.match(NoteParser.ACTIVE_TREND_RE);
    if (at) out['Trend active users 90d'] = NoteParser.trendMatch(at);

    const ct = combined.match(NoteParser.CALL_TREND_RE);
    if (ct) out['Trend call volume 90d'] = NoteParser.trendMatch(ct);

    const ms = combined.match(NoteParser.MSG_USAGE_RE);
    if (ms) out['Messaging usage'] = `${ms[1]} active users; ${ms[2]} messages sent`;

    const ap = combined.match(NoteParser.ACTIVE_PCT_RE);
    if (ap) out['Active % of provisioned'] = `${ap[1]}%`;

    return out;
  }

  static parseProfWsShorthand(text) {
    const m = String(text || '').match(NoteParser.PROF_WS_SHORT_RE);
    if (!m) return null;
    return {
      professional: m[1].replace(/,/g, ''),
      workspace: m[2].replace(/,/g, ''),
    };
  }

  static applyProfWsShorthandFromCells(row, out) {
    for (const field of [
      'Provisioned/Entitled Lic Calling',
      'Entitled Lic Calling',
      'Providioned Lic Calling',
    ]) {
      const parsed = NoteParser.parseProfWsShorthand(row[field]);
      if (!parsed) continue;
      const fromProvisioned =
        field === 'Providioned Lic Calling' || field === 'Provisioned/Entitled Lic Calling';
      if (fromProvisioned || !out['Lic Professional (used/entitled)']) {
        out['Lic Professional (used/entitled)'] = parsed.professional;
      }
      if (fromProvisioned || !out['Lic Workspace (used/entitled)']) {
        out['Lic Workspace (used/entitled)'] = parsed.workspace;
      }
    }
    return out;
  }

  static buildProvidionedLic(pl, ws) {
    const parts = [];
    if (pl && String(pl).trim()) parts.push(`PL: ${String(pl).trim()}`);
    if (ws && String(ws).trim()) parts.push(`WS: ${String(ws).trim()}`);
    return parts.join(', ');
  }

  static computeActivePct(provisioned, active) {
    const simpleMax = (val) => {
      if (val == null || val === '') return null;
      const s = String(val);
      if (/workspace|professional|standard|PL:|WxM|Agent/i.test(s)) return null;
      const nums = s.match(/[\d,]+(?:\.\d+)?/g) || [];
      const vals = nums
        .map((n) => parseFloat(n.replace(/,/g, '')))
        .filter((n) => !Number.isNaN(n));
      if (!vals.length || vals.length > 2) return null;
      return Math.max(...vals);
    };
    const p = simpleMax(provisioned);
    const a = simpleMax(active);
    if (p == null || a == null || p <= 0 || a > p * 1.05) return '';
    return `${Math.round((a / p) * 100)}%`;
  }

  /** Fill empty structured columns from note text (does not overwrite existing values). */
  static enrichRowFromNotes(row) {
    const out = { ...row };
    const analytics = String(row['Notes from Calling Analytics'] || '');
    const features = String(row['Notes from provisioned features'] || '');
    const addons = String(row['Add-ons included or not'] || '');
    const parsed = NoteParser.parseNotesToStructured(analytics, features, addons);
    NoteParser.applyProfWsShorthandFromCells(row, parsed);

    const pct = NoteParser.computeActivePct(
      row['Provisioned/Entitled Lic Calling'],
      row['Providioned Lic Calling'],
      row['Active Lic Calling']
    );
    if (pct) parsed['Active % of provisioned'] = pct;

    Object.entries(parsed).forEach(([key, val]) => {
      if (val != null && String(val).trim() !== '' && BiaSanitizer.isEmptyVal(out[key])) {
        out[key] = val;
      }
    });

    return out;
  }
}

CheckBack.Dashboard.NoteParser = NoteParser;
/**
 * Parse PL/WS and Webex product license pairs (used/entitled) from spreadsheet text.
 */
class LicenseProductParser {
  static LICENSE_COL = 'Provisioned/Entitled Lic Calling';
  static LEGACY_ENT_COL = 'Entitled Lic Calling';
  static LEGACY_PROV_COL = 'Providioned Lic Calling';

  /** Order matters: WxMS before WxM so "WxMS" is not read as "WxM". */
  static PRODUCT_PAIR_RE =
    /\b(WxMS|WxM|WxCC|PL|WS)\s*:?\s*(\d[\d,]*)\s*\/\s*(\d[\d,]*)/gi;
  /** e.g. "1,265 workspace 335" → Professional 1265, Workspace 335 */
  static PROF_WS_SHORT_RE = /(\d[\d,]*)\s+workspace\s+(\d[\d,]*)/i;

  static DISPLAY_LABELS = {
    wxMeetingSuite: 'Webex Meeting Suite',
    wxMeetings: 'Webex Meetings',
    wxContactCenter: 'Webex Contact Center',
    pl: 'Professional',
    ws: 'Workspace',
  };

  static parseFromText(...sources) {
    const combined = sources.filter((s) => s != null && String(s).trim()).join(' ');
    const out = {
      pl: '',
      ws: '',
      wxMeetingSuite: '',
      wxMeetings: '',
      wxContactCenter: '',
    };
    if (!combined.trim()) return out;

    const re = new RegExp(LicenseProductParser.PRODUCT_PAIR_RE.source, 'gi');
    let m;
    while ((m = re.exec(combined)) !== null) {
      const token = m[1].toUpperCase();
      const pair = `${m[2]}/${m[3]}`;
      if (token === 'WXMS') out.wxMeetingSuite = pair;
      else if (token === 'WXM') out.wxMeetings = pair;
      else if (token === 'WXCC') out.wxContactCenter = pair;
      else if (token === 'PL') out.pl = pair;
      else if (token === 'WS') out.ws = pair;
    }
    return out;
  }

  static parseProfWsShorthand(text) {
    const m = String(text || '').match(LicenseProductParser.PROF_WS_SHORT_RE);
    if (!m) return null;
    return { pl: m[1], ws: m[2] };
  }

  static fmtCount(n) {
    return Math.round(Number(n) || 0).toLocaleString();
  }

  static parsePlWsSingleCell(val) {
    const out = { pl: null, ws: null };
    const s = String(val ?? '').trim();
    if (!s) return out;
    let m;
    const plRe = /\bPL\s*:\s*(\d[\d,]*)/gi;
    const wsRe = /\bWS\s*:\s*(\d[\d,]*)/gi;
    while ((m = plRe.exec(s)) !== null) out.pl = LicenseProductParser.parseNum(m[1]);
    while ((m = wsRe.exec(s)) !== null) out.ws = LicenseProductParser.parseNum(m[1]);
    return out;
  }

  static hasProfWsPairFormat(val) {
    return /\b(?:Professional|Workspace|PL|WS)\s*:?\s*\d[\d,]*\s*\/\s*\d[\d,]*/i.test(
      String(val ?? '')
    );
  }

  static normalizeProfWsDisplay(text) {
    let s = String(text ?? '').trim();
    if (!s) return '';
    s = s.replace(
      /\bPL\s*:?\s*(\d[\d,]*)\s*\/\s*(\d[\d,]*)/gi,
      (_, p, e) =>
        `Professional ${LicenseProductParser.fmtCount(p)}/${LicenseProductParser.fmtCount(e)}`
    );
    s = s.replace(
      /\bWS\s*:?\s*(\d[\d,]*)\s*\/\s*(\d[\d,]*)/gi,
      (_, p, e) =>
        `Workspace ${LicenseProductParser.fmtCount(p)}/${LicenseProductParser.fmtCount(e)}`
    );
    s = s.replace(
      /\bProfessional\s+(\d[\d,]*)\s*\/\s*(\d[\d,]*)/gi,
      (_, p, e) =>
        `Professional ${LicenseProductParser.fmtCount(p)}/${LicenseProductParser.fmtCount(e)}`
    );
    s = s.replace(
      /\bWorkspace\s+(\d[\d,]*)\s*\/\s*(\d[\d,]*)/gi,
      (_, p, e) =>
        `Workspace ${LicenseProductParser.fmtCount(p)}/${LicenseProductParser.fmtCount(e)}`
    );
    return s.replace(/\s*;\s*/g, '; ').replace(/,\s*(?=Workspace)/g, '; ');
  }

  static getLicenseCell(row) {
    const merged = String(row?.[LicenseProductParser.LICENSE_COL] ?? '').trim();
    if (merged) return merged;
    return '';
  }

  static hasLegacySplitColumns(row) {
    return Boolean(
      String(row?.[LicenseProductParser.LEGACY_ENT_COL] ?? '').trim() ||
        String(row?.[LicenseProductParser.LEGACY_PROV_COL] ?? '').trim()
    );
  }

  /** Entitled counts only — from merged prov/ent cell or legacy entitled column. */
  static formatEntitledOnlyColumn(row) {
    const merged = LicenseProductParser.getLicenseCell(row);
    if (merged && LicenseProductParser.hasProfWsPairFormat(merged)) {
      const parts = [];
      const pairRe =
        /\b(Professional|Workspace|PL|WS)\s*:?\s*\d[\d,]*\s*\/\s*(\d[\d,]*)/gi;
      let m;
      while ((m = pairRe.exec(merged)) !== null) {
        const token = m[1].toUpperCase();
        const name =
          token === 'WS' || token === 'WORKSPACE' ? 'Workspace' : 'Professional';
        parts.push(`${name} ${LicenseProductParser.fmtCount(m[2])}`);
      }
      if (parts.length) return parts.join('; ');
      const total = LicenseProductParser.sumPlWsCell(merged, 'entitled');
      return total ? LicenseProductParser.fmtCount(total) : merged;
    }
    return LicenseProductParser.formatEntitledColumn(row);
  }

  /** Provisioned counts only — from merged prov/ent cell or legacy provisioned column. */
  static formatProvisionedOnlyColumn(row) {
    const merged = LicenseProductParser.getLicenseCell(row);
    if (merged && LicenseProductParser.hasProfWsPairFormat(merged)) {
      const parts = [];
      const pairRe =
        /\b(Professional|Workspace|PL|WS)\s*:?\s*(\d[\d,]*)\s*\/\s*\d[\d,]*/gi;
      let m;
      while ((m = pairRe.exec(merged)) !== null) {
        const token = m[1].toUpperCase();
        const name =
          token === 'WS' || token === 'WORKSPACE' ? 'Workspace' : 'Professional';
        parts.push(`${name} ${LicenseProductParser.fmtCount(m[2])}`);
      }
      if (parts.length) return parts.join('; ');
      const total = LicenseProductParser.sumPlWsCell(merged, 'provisioned');
      return total ? LicenseProductParser.fmtCount(total) : merged;
    }
    return LicenseProductParser.formatProvisionedColumn(row);
  }

  /** Display merged prov/ent column (normalize commas / labels). */
  static formatLicenseColumn(row) {
    const merged = LicenseProductParser.getLicenseCell(row);
    if (merged && LicenseProductParser.hasProfWsPairFormat(merged)) {
      return LicenseProductParser.normalizeProfWsDisplay(merged);
    }
    if (merged) return merged;
    return LicenseProductParser.formatEntitledColumn(row);
  }

  /** @deprecated use formatLicenseColumn — legacy entitled-only display */
  static formatEntitledColumn(row) {
    const entitledRaw = String(row[LicenseProductParser.LEGACY_ENT_COL] ?? '').trim();
    const provRaw = String(row[LicenseProductParser.LEGACY_PROV_COL] ?? '').trim();

    if (LicenseProductParser.hasProfWsPairFormat(entitledRaw)) {
      return LicenseProductParser.normalizeProfWsDisplay(entitledRaw);
    }

    if (LicenseProductParser.hasProfWsPairFormat(provRaw) && !entitledRaw) {
      return LicenseProductParser.normalizeProfWsDisplay(provRaw);
    }

    const ent = LicenseProductParser.parsePlWsSingleCell(entitledRaw);
    const prov = LicenseProductParser.parsePlWsSingleCell(provRaw);
    const parts = [];
    if (ent.pl != null || prov.pl != null) {
      parts.push(
        `Professional ${LicenseProductParser.fmtCount(prov.pl ?? 0)}/${LicenseProductParser.fmtCount(ent.pl ?? 0)}`
      );
    }
    if (ent.ws != null || prov.ws != null) {
      parts.push(
        `Workspace ${LicenseProductParser.fmtCount(prov.ws ?? 0)}/${LicenseProductParser.fmtCount(ent.ws ?? 0)}`
      );
    }
    if (parts.length) return parts.join('; ');
    return entitledRaw;
  }

  /** @deprecated split-column layout — use formatLicenseColumn */
  static formatProvisionedColumn(row) {
    const provRaw = String(row[LicenseProductParser.LEGACY_PROV_COL] ?? '').trim();
    if (LicenseProductParser.hasProfWsPairFormat(provRaw)) {
      return LicenseProductParser.normalizeProfWsDisplay(provRaw);
    }
    const prov = LicenseProductParser.parsePlWsSingleCell(provRaw);
    const parts = [];
    if (prov.pl != null) parts.push(`Professional ${LicenseProductParser.fmtCount(prov.pl)}`);
    if (prov.ws != null) parts.push(`Workspace ${LicenseProductParser.fmtCount(prov.ws)}`);
    if (parts.length) return parts.join('; ');
    return provRaw;
  }

  static formatActiveColumn(val) {
    const n = LicenseProductParser.sumPlWsCell(val, 'active');
    if (n) return LicenseProductParser.fmtCount(n);
    return String(val ?? '').trim();
  }

  static parseNum(s) {
    return parseFloat(String(s ?? '').replace(/,/g, '')) || 0;
  }

  /**
   * Sum Professional + Workspace counts from a license cell.
   * @param {string} val - cell text
   * @param {'entitled'|'provisioned'|'active'} columnKind - which column the value came from
   */
  static sumPlWsCell(val, columnKind) {
    const s = String(val ?? '').trim();
    if (!s) return 0;

    let total = 0;
    let found = false;

    const pairRe = /\b(?:PL|WS|Professional|Workspace)\s*:?\s*(\d[\d,]*)\s*\/\s*(\d[\d,]*)/gi;
    let m;
    while ((m = pairRe.exec(s)) !== null) {
      found = true;
      const prov = LicenseProductParser.parseNum(m[1]);
      const ent = LicenseProductParser.parseNum(m[2]);
      if (columnKind === 'entitled') total += ent;
      else total += prov;
    }
    if (found) return total;

    const singleRe = /\b(?:PL|WS)\s*:\s*(\d[\d,]*)/gi;
    while ((m = singleRe.exec(s)) !== null) {
      found = true;
      total += LicenseProductParser.parseNum(m[1]);
    }
    if (found) return total;

    const shorthand = LicenseProductParser.parseProfWsShorthand(s);
    if (shorthand) {
      return (
        LicenseProductParser.parseNum(shorthand.pl) + LicenseProductParser.parseNum(shorthand.ws)
      );
    }

    const nums = s.match(/\d[\d,]*(?:\.\d+)?/g);
    if (!nums) return 0;
    if (nums.length === 1) return LicenseProductParser.parseNum(nums[0]);
    if (columnKind === 'active') {
      return nums.reduce((acc, n) => acc + LicenseProductParser.parseNum(n), 0);
    }
    return 0;
  }

  static rowLicenseTotals(row) {
    const merged = LicenseProductParser.getLicenseCell(row);
    if (merged && LicenseProductParser.hasProfWsPairFormat(merged)) {
      return {
        entitled: LicenseProductParser.sumPlWsCell(merged, 'entitled'),
        provisioned: LicenseProductParser.sumPlWsCell(merged, 'provisioned'),
        active: LicenseProductParser.sumPlWsCell(row['Active Lic Calling'], 'active'),
      };
    }
    const entitled = LicenseProductParser.sumPlWsCell(
      row[LicenseProductParser.LEGACY_ENT_COL],
      'entitled'
    );
    const provisioned = LicenseProductParser.sumPlWsCell(
      row[LicenseProductParser.LEGACY_PROV_COL],
      'provisioned'
    );
    const active = LicenseProductParser.sumPlWsCell(row['Active Lic Calling'], 'active');
    return { entitled, provisioned, active };
  }

  /** Last source in the list wins for shorthand counts (provisioned over entitled). */
  static mergeShorthandFromSources(sources) {
    let pl = '';
    let ws = '';
    sources.forEach((src) => {
      const parsed = LicenseProductParser.parseProfWsShorthand(src);
      if (!parsed) return;
      pl = parsed.pl;
      ws = parsed.ws;
    });
    return { pl, ws };
  }

  static mergeIntoProvisioning(p, sources) {
    const parsed = LicenseProductParser.parseFromText(...sources);
    const shorthand = LicenseProductParser.mergeShorthandFromSources(sources);
    const pl =
      BiaSanitizer.sanitizeField(p.licProfessional || p.professional || '') ||
      parsed.pl ||
      shorthand.pl;
    const ws =
      BiaSanitizer.sanitizeField(p.licWorkspace || p.workspace || '') ||
      parsed.ws ||
      shorthand.ws;
    return {
      pl,
      ws,
      wxMeetingSuite: BiaSanitizer.sanitizeField(p.wxMeetingSuite || '') || parsed.wxMeetingSuite,
      wxMeetings: BiaSanitizer.sanitizeField(p.wxMeetings || '') || parsed.wxMeetings,
      wxContactCenter:
        BiaSanitizer.sanitizeField(p.wxContactCenter || '') || parsed.wxContactCenter,
    };
  }

  static hasPlWsBreakdown(lic) {
    return Boolean(lic.pl || lic.ws);
  }

  static hasAnyProduct(lic) {
    return Boolean(
      lic.pl || lic.ws || lic.wxMeetingSuite || lic.wxMeetings || lic.wxContactCenter
    );
  }
}

CheckBack.Dashboard.LicenseProductParser = LicenseProductParser;
/**
 * Match workbook rows to bundled Lookback BIA deck slides.
 */
class BiaSlideMatcher {
  static normName(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/\b(the|inc|llc|ltd|corp|sa|co)\b/g, ' ')
      .replace(/[^a-z0-9]+/g, '')
      .trim();
  }

  static namesMatch(a, b) {
    const na = BiaSlideMatcher.normName(a);
    const nb = BiaSlideMatcher.normName(b);
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

  static matchByAlias(opportunityName) {
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

  static findSlide(row) {
    if (typeof BIA_SLIDES === 'undefined' || !BIA_SLIDES.length) return null;
    const org = BiaSanitizer.normalizeOrgId(row?.['Customer org id']);
    if (org) {
      const hit = BIA_SLIDES.find((s) => s.orgId && s.orgId.toLowerCase() === org);
      if (hit) return hit;
    }
    const name = row?.['Opportunity Name'] || row?.['Account Name'] || '';
    const alias = BiaSlideMatcher.matchByAlias(name);
    if (alias) return alias;
    if (!name) return null;
    return BIA_SLIDES.find((s) => BiaSlideMatcher.namesMatch(name, s.customerName)) || null;
  }

  static rowMatchesSlide(row, slide) {
    if (!slide?.orgId) return false;
    const org = BiaSanitizer.normalizeOrgId(row?.['Customer org id']);
    if (org && org === slide.orgId.toLowerCase()) return true;
    const found = BiaSlideMatcher.findSlide(row);
    return Boolean(found && found.orgId && found.orgId.toLowerCase() === slide.orgId.toLowerCase());
  }

  static listSlides() {
    return typeof BIA_SLIDES !== 'undefined' ? BIA_SLIDES : [];
  }
}

CheckBack.Dashboard.BiaSlideMatcher = BiaSlideMatcher;
/**
 * Map spreadsheet / export rows ↔ BIA slide-shaped objects.
 */
class BiaWorkbookMapper {
  static collectRowNotes(row) {
    const notes = [];
    const seen = new Set();
    const add = (who, text) => {
      const t = String(text || '').trim();
      if (t.length < 5 || seen.has(t)) return;
      seen.add(t);
      notes.push({ who, text: t });
    };
    add('Analytics', row['Notes from Calling Analytics']);
    add('Provisioning', row['Notes from provisioned features']);
    add('Recommended', row['Recommended Actions']);
    const tac = row['TAC/BEMS'];
    if (tac && String(tac).trim().length > 1 && !/^[YN]$/i.test(String(tac).trim())) {
      add('TAC/BEMS', tac);
    }
    return notes;
  }

  static resolveUrls(row) {
    const oppLink = row['Opportunity (linked)'] || row['Salesforce URL'] || '';
    const salesforceUrl = String(row['Salesforce URL'] || '').trim();
    const oppUrl = String(oppLink).trim();
    const resolvedSf =
      salesforceUrl.startsWith('http') ? salesforceUrl : oppUrl.startsWith('http') ? oppUrl : '';
    const successPortalUrl = String(row['Success Portal'] || '').trim().startsWith('http')
      ? String(row['Success Portal']).trim()
      : '';
    return { oppLink, resolvedSf, successPortalUrl };
  }

  static buildLinkLabels(row) {
    const links = [];
    const seen = new Set();
    const pushLink = (label) => {
      const l = String(label || '').trim();
      const key = l.toLowerCase();
      if (!l || seen.has(key)) return;
      seen.add(key);
      links.push(l);
    };
    const { oppLink } = BiaWorkbookMapper.resolveUrls(row);
    if (!BiaSanitizer.isEmptyVal(oppLink)) {
      const o = String(oppLink).trim();
      pushLink(/^https?:\/\//i.test(o) ? 'S&C' : o);
    }
    if (!BiaSanitizer.isEmptyVal(row['Success Portal'])) {
      const sp = String(row['Success Portal']).trim();
      pushLink(/^https?:\/\//i.test(sp) ? 'Success Portal' : sp);
    }
    pushLink('Success Portal');
    return links;
  }

  static rowToSlide(row) {
    const enriched = NoteParser.enrichRowFromNotes(row);
    const GYR_COL = CheckBack.Dashboard.Constants.GYR_COL;
    const subTerm =
      enriched['Sub Term'] ||
      enriched['Subscription dates'] ||
      enriched['Sub start date (MM/DD/YYYY)'] ||
      '';
    const timeline = BiaSanitizer.parseTimelineFromTerm(subTerm);
    const gyr = enriched[GYR_COL] || enriched['Final Determination'] || '';
    const trends = [];
    if (!BiaSanitizer.isEmptyVal(enriched['Trend active users 90d'])) {
      trends.push(String(enriched['Trend active users 90d']).trim());
    }
    if (!BiaSanitizer.isEmptyVal(enriched['Trend call volume 90d'])) {
      trends.push(String(enriched['Trend call volume 90d']).trim());
    }
    const links = BiaWorkbookMapper.buildLinkLabels(enriched);
    const { resolvedSf, successPortalUrl } = BiaWorkbookMapper.resolveUrls(enriched);

    const licSources = [
      enriched['Notes from Calling Analytics'],
      enriched['Notes from provisioned features'],
      enriched['Provisioned/Entitled Lic Calling'],
      enriched['Entitled Lic Calling'],
      enriched['Providioned Lic Calling'],
    ];
    const lic = LicenseProductParser.mergeIntoProvisioning(
      {
        licProfessional: enriched['Lic Professional (used/entitled)'],
        licWorkspace: enriched['Lic Workspace (used/entitled)'],
      },
      licSources
    );
    const hasPlWsCols =
      (!BiaSanitizer.isEmptyVal(enriched['Lic Professional (used/entitled)']) &&
        !BiaSanitizer.isEmptyVal(enriched['Lic Workspace (used/entitled)'])) ||
      (Boolean(lic.pl) && Boolean(lic.ws));

    const slide = {
      customerName: enriched['Opportunity Name'] || 'Customer',
      orgId: String(enriched['Customer org id'] || '').trim(),
      gatheredBy: enriched['Data gathered by'] || '',
      gatheredDate: enriched['Data gathered date'] || '',
      health: BiaSanitizer.gyrToHealth(gyr),
      platforms: enriched['Platforms'] || enriched['Service lines'] || '',
      timelineYears: timeline.years,
      timelineCurrentYear: timeline.currentYear,
      subscription: {
        sub: enriched['Sub #'] || '',
        term: subTerm,
        tcv: enriched['TCV $'] || '',
        aar: enriched['AAR $'] || '',
        collabAe: enriched['Collab AE/SE'] || '',
        segment: enriched['SL2'] || '',
        partner: enriched['Partner'] || '',
        csmModel: enriched['CSM Engagement Model (linked)'] || enriched['CSM name'] || '',
        links: links.join(' | '),
      },
      provisioning: {
        orgId: String(enriched['Customer org id'] || '').trim(),
        entitled:
          enriched['Provisioned/Entitled Lic Calling'] ||
          enriched['Entitled Lic Calling'] ||
          '',
        provisioned: hasPlWsCols
          ? ''
          : enriched['Providioned Lic Calling'] ||
            enriched['Provisioned/Entitled Lic Calling'] ||
            '',
        licProfessional: lic.pl,
        licWorkspace: lic.ws,
        wxMeetingSuite: lic.wxMeetingSuite,
        wxMeetings: lic.wxMeetings,
        wxContactCenter: lic.wxContactCenter,
        activeUsers: enriched['Active Lic Calling'] || '',
        externalCalls: enriched['External calls'] || '',
        meetings: enriched['Meetings usage'] || '',
        messaging: enriched['Messaging usage'] || '',
        numbersAssigned: enriched['Numbers assigned'] || '',
        locations: enriched['Locations main number'] || '',
      },
      features: {
        autoAttendant: enriched['Auto Attendant count'] || '—',
        huntGroups: enriched['Hunt Groups count'] || '—',
        callQueues: enriched['Call Queues count'] || '—',
        connectedUc: enriched['Connected-UC (Y/N)'] || '—',
        virtualLines: enriched['Virtual Lines count'] || '—',
      },
      trends,
      notes: BiaWorkbookMapper.collectRowNotes(enriched),
      workbookNotes: {
        analytics: enriched['Notes from Calling Analytics'] || '',
        features: enriched['Notes from provisioned features'] || '',
        recommended: enriched['Recommended Actions'] || '',
      },
      salesforceUrl: resolvedSf,
      successPortalUrl,
      fromWorkbook: true,
    };
    const rowAddons = BiaSlideEditor.addonsFromRow(enriched);
    if (Object.keys(rowAddons).length) slide.addons = rowAddons;
    return slide;
  }

  static applyBiaFields(out, deck, wb) {
    const GYR_COL = CheckBack.Dashboard.Constants.GYR_COL;
    const s = deck.subscription || {};
    const p = deck.provisioning || {};
    const f = deck.features || {};
    const wbRow = wb || {};

    const set = (col, val) => {
      if (val != null && String(val).trim() !== '') out[col] = val;
    };

    set('Opportunity Name', deck.customerName);
    set('Customer org id', deck.orgId);
    set(GYR_COL, BiaSanitizer.healthToGyr(deck.health) || wbRow[GYR_COL] || wbRow['Final Determination'] || '');
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
    if (deck.salesforceUrl) set('Salesforce URL', deck.salesforceUrl);
    if (deck.successPortalUrl) set('Success Portal', deck.successPortalUrl);
    set('Provisioned/Entitled Lic Calling', p.entitled || wbRow['Provisioned/Entitled Lic Calling']);
    set('Entitled Lic Calling', p.entitled);
    set(
      'Providioned Lic Calling',
      p.provisioned || p.professional || wbRow['Providioned Lic Calling']
    );
    set('Active Lic Calling', p.activeUsers);
    set('Lic Professional (used/entitled)', BiaSanitizer.licPair(p.professional || p.licProfessional));
    set('Lic Standard (used/entitled)', BiaSanitizer.licPair(p.standard));
    set('Lic Workspace (used/entitled)', BiaSanitizer.licPair(p.workspace || p.licWorkspace));
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
      const text = BiaSanitizer.sanitizeField(t);
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

  static mergeWorkbookSupplements(out, wb) {
    if (!wb) return out;
    const { WORKBOOK_SUPPLEMENT_COLS, BIA_CANONICAL_COLS } = CheckBack.Dashboard.Constants;
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
}

CheckBack.Dashboard.BiaWorkbookMapper = BiaWorkbookMapper;
/**
 * Portfolio list: workbook rows are source of truth; BIA deck enriches slides at view time only.
 */
class BiaPortfolioService {
  static sortPortfolio(rows) {
    return [...rows].sort((a, b) =>
      String(a['Opportunity Name'] || '').localeCompare(String(b['Opportunity Name'] || ''), undefined, {
        sensitivity: 'base',
      })
    );
  }

  /** Note parsing only — does not overlay bundled BIA deck onto row data (export stays faithful). */
  static enrichRow(row) {
    if (!row) return {};
    return NoteParser.enrichRowFromNotes({ ...row });
  }

  static rowInWorkbook(workbookRows, slide) {
    if (!slide?.orgId) return null;
    for (const row of workbookRows) {
      if (BiaSlideMatcher.rowMatchesSlide(row, slide)) return row;
    }
    return null;
  }

  static mergePortfolioWithBia(rows, options) {
    const includeBiaDeck = !options || options.includeBiaDeck !== false;
    const workbookRows = (rows || []).map((row) => BiaPortfolioService.enrichRow(row));
    const portfolio = [...workbookRows];

    if (includeBiaDeck && typeof BIA_SLIDES !== 'undefined' && BIA_SLIDES.length) {
      BIA_SLIDES.forEach((slide) => {
        if (!slide.orgId || slide.isTemplate) return;
        if (BiaPortfolioService.rowInWorkbook(workbookRows, slide)) return;
        portfolio.push({
          'Opportunity Name': slide.customerName,
          'Customer org id': slide.orgId,
          _biaSlideOnly: true,
        });
      });
    }

    return BiaPortfolioService.sortPortfolio(portfolio);
  }

  /** Workbook rows only — no bundled BIA deck stubs (use on user file upload). */
  static workbookRowsOnly(rows) {
    return BiaPortfolioService.mergePortfolioWithBia(rows, { includeBiaDeck: false });
  }

  static collectAllColumns(rows) {
    if (!rows || !rows.length) return [];
    const prefer = CheckBack.Dashboard.Constants.PORTFOLIO_COLUMN_PREFER;
    const licenseCol = CheckBack.Dashboard.Constants.LICENSE_COL;
    const seen = new Set();
    const ordered = [];

    function columnHasData(col) {
      if (col === 'Entitled Lic Calling' || col === 'Providioned Lic Calling') {
        if (rows.some((r) => r[col] != null && String(r[col]).trim() !== '')) return true;
        return rows.some((r) => String(r[licenseCol] || '').trim());
      }
      return rows.some((r) => r[col] != null && String(r[col]).trim() !== '');
    }

    prefer.forEach((c) => {
      if (columnHasData(c)) {
        ordered.push(c);
        seen.add(c);
      }
    });
    const hasMerged = rows.some((r) => String(r[licenseCol] || '').trim());
    if (hasMerged) {
      ['Entitled Lic Calling', 'Providioned Lic Calling'].forEach((virtualCol) => {
        if (!seen.has(virtualCol)) {
          const actIdx = ordered.indexOf('Active Lic Calling');
          const at = actIdx >= 0 ? actIdx : ordered.length;
          ordered.splice(at, 0, virtualCol);
          seen.add(virtualCol);
        }
      });
    }
    rows.forEach((r) => {
      Object.keys(r).forEach((k) => {
        if (seen.has(k)) return;
        if (k.startsWith('_') && k !== '_addonsPtu') return;
        if (k === licenseCol && seen.has('Entitled Lic Calling')) return;
        seen.add(k);
        ordered.push(k);
      });
    });
    return ordered;
  }
}

CheckBack.Dashboard.BiaPortfolioService = BiaPortfolioService;
/**
 * Deep-merge workbook rows into BIA slide objects for display.
 */
class BiaSlideMerger {
  static sanitizeSlide(slide) {
    const s = slide.subscription || {};
    const p = slide.provisioning || {};
    const f = slide.features || {};
    return {
      ...slide,
      platforms: BiaSanitizer.sanitizeField(slide.platforms),
      subscription: {
        ...s,
        sub: BiaSanitizer.sanitizeField(s.sub),
        term: BiaSanitizer.sanitizeField(s.term),
        tcv: BiaSanitizer.sanitizeMoney(s.tcv),
        aar: BiaSanitizer.sanitizeMoney(s.aar),
        collabAe: BiaSanitizer.sanitizeField(s.collabAe),
        segment: BiaSanitizer.sanitizeSegment(s.segment),
        partner: BiaSanitizer.sanitizeField(s.partner),
        csmModel: BiaSanitizer.sanitizeField(s.csmModel),
      },
      provisioning: {
        ...p,
        entitled: BiaSanitizer.sanitizeField(p.entitled),
        provisioned: BiaSanitizer.sanitizeField(p.provisioned),
        licProfessional: BiaSanitizer.sanitizeField(p.licProfessional),
        licWorkspace: BiaSanitizer.sanitizeField(p.licWorkspace),
        wxMeetingSuite: BiaSanitizer.sanitizeField(p.wxMeetingSuite),
        wxMeetings: BiaSanitizer.sanitizeField(p.wxMeetings),
        wxContactCenter: BiaSanitizer.sanitizeField(p.wxContactCenter),
        professional: BiaSanitizer.sanitizeField(p.professional),
        standard: BiaSanitizer.sanitizeField(p.standard),
        workspace: BiaSanitizer.sanitizeField(p.workspace),
        activeUsers: BiaSanitizer.sanitizeField(p.activeUsers),
        externalCalls: BiaSanitizer.sanitizeField(p.externalCalls),
        meetings: BiaSanitizer.sanitizeField(p.meetings),
        messaging: BiaSanitizer.sanitizeField(p.messaging),
        numbersAssigned: BiaSanitizer.sanitizeField(p.numbersAssigned),
        locations: BiaSanitizer.sanitizeField(p.locations),
      },
      features: { ...f },
    };
  }

  static mergeSubscriptionLinks(merged, rowSlide) {
    const v = rowSlide.subscription?.links;
    const slideLinks = String(merged.subscription?.links || '').trim();
    const rowLinks = String(v || '').trim();
    if (isEmptyLinksMerge(slideLinks, rowLinks)) {
      merged.subscription.links = slideLinks;
    } else if (!BiaSanitizer.isEmptyVal(rowLinks)) {
      merged.subscription.links = rowLinks;
    }
  }

  static mergeSlideWithRow(row, slide) {
    const merged = BiaSlideMerger.sanitizeSlide(JSON.parse(JSON.stringify(slide)));
    const rowSlide = BiaWorkbookMapper.rowToSlide(row);

    if (!BiaSanitizer.isEmptyVal(row['Salesforce URL'])) merged.salesforceUrl = row['Salesforce URL'];
    if (!BiaSanitizer.isEmptyVal(rowSlide.salesforceUrl)) merged.salesforceUrl = rowSlide.salesforceUrl;
    if (!BiaSanitizer.isEmptyVal(rowSlide.successPortalUrl)) {
      merged.successPortalUrl = rowSlide.successPortalUrl;
    }
    if (!BiaSanitizer.isEmptyVal(rowSlide.gatheredBy)) merged.gatheredBy = rowSlide.gatheredBy;
    if (!BiaSanitizer.isEmptyVal(rowSlide.gatheredDate)) merged.gatheredDate = rowSlide.gatheredDate;
    if (!BiaSanitizer.isEmptyVal(rowSlide.customerName)) merged.customerName = rowSlide.customerName;
    if (!BiaSanitizer.isEmptyVal(rowSlide.health)) merged.health = rowSlide.health;
    if (!BiaSanitizer.isEmptyVal(rowSlide.platforms)) merged.platforms = rowSlide.platforms;

    merged.timelineYears = rowSlide.timelineYears || merged.timelineYears || 5;
    if (rowSlide.timelineCurrentYear) merged.timelineCurrentYear = rowSlide.timelineCurrentYear;

    Object.keys(rowSlide.subscription || {}).forEach((k) => {
      const v = rowSlide.subscription[k];
      if (k === 'links') {
        BiaSlideMerger.mergeSubscriptionLinks(merged, rowSlide);
        return;
      }
      if (!BiaSanitizer.isEmptyVal(v)) merged.subscription[k] = v;
    });
    Object.keys(rowSlide.provisioning || {}).forEach((k) => {
      const v = rowSlide.provisioning[k];
      if (!BiaSanitizer.isEmptyVal(v)) merged.provisioning[k] = v;
    });
    Object.keys(rowSlide.features || {}).forEach((k) => {
      const v = rowSlide.features[k];
      if (!BiaSanitizer.isEmptyVal(v)) merged.features[k] = v;
    });

    if (rowSlide.trends?.length) merged.trends = rowSlide.trends;

    if (rowSlide.notes?.length) {
      if (slide.fromWorkbook || !merged.notes?.length) {
        merged.notes = rowSlide.notes;
      } else {
        const texts = new Set((merged.notes || []).map((n) => n.text));
        rowSlide.notes.forEach((n) => {
          if (!texts.has(n.text)) merged.notes.push(n);
        });
      }
    }

    if (rowSlide.addons) merged.addons = { ...(merged.addons || {}), ...rowSlide.addons };

    merged.workbookNotes = {
      analytics: String(row['Notes from Calling Analytics'] ?? rowSlide.workbookNotes?.analytics ?? '').trim(),
      features: String(row['Notes from provisioned features'] ?? rowSlide.workbookNotes?.features ?? '').trim(),
      recommended: String(row['Recommended Actions'] ?? rowSlide.workbookNotes?.recommended ?? '').trim(),
    };

    return merged;
  }
}

function isEmptyLinksMerge(slideLinks, rowLinks) {
  if (BiaSanitizer.isEmptyVal(slideLinks) && !BiaSanitizer.isEmptyVal(rowLinks)) return false;
  return (
    !BiaSanitizer.isEmptyVal(slideLinks) &&
    (BiaSanitizer.isEmptyVal(rowLinks) || slideLinks.includes('|') || /^https?:\/\//i.test(rowLinks))
  );
}

CheckBack.Dashboard.BiaSlideMerger = BiaSlideMerger;
/**
 * Lookback BIA slide HTML renderer (three-panel layout).
 */
class BiaSlideRenderer {
  static linkUrlCell(url, col) {
    const u = String(url ?? '').trim();
    const attrs = DashboardHtml.editableAttrs(col);
    let inner;
    if (u.startsWith('http')) {
      const href = u.replace(/"/g, '&quot;');
      inner = `<a href="${href}" target="_blank" rel="noopener noreferrer" class="customer-link bia-link-view">${DashboardHtml.esc(u)}</a>`;
    } else {
      inner = DashboardHtml.esc(u || '—');
    }
    return `<strong${attrs}>${inner}</strong>`;
  }

  static addonCell(name, slot, value) {
    const v = BiaSanitizer.sanitizeField(value || '—');
    const attrs = ` class="bia-editable-addon" data-addon-name="${DashboardHtml.escAttr(name)}" data-addon-slot="${slot}" contenteditable="false"`;
    return `<td><span${attrs}>${DashboardHtml.esc(v)}</span></td>`;
  }

  static renderLinksRow(s, deck) {
    const sf = String(deck.salesforceUrl || '').trim();
    const spUrl = String(deck.successPortalUrl || '').trim();
    return `<div class="insight-kv insight-kv-links insight-kv-stack">
      <span>Links</span>
      <div class="insight-links-grid">
        <div class="insight-link-edit-row"><span class="insight-link-label">S&amp;C</span>${BiaSlideRenderer.linkUrlCell(sf, 'Salesforce URL')}</div>
        <div class="insight-link-edit-row"><span class="insight-link-label">Success Portal</span>${BiaSlideRenderer.linkUrlCell(spUrl, 'Success Portal')}</div>
      </div>
    </div>`;
  }

  static renderProvisionedBlock(p) {
    const lic = LicenseProductParser.mergeIntoProvisioning(p, [p.entitled, p.provisioned]);

    const rows = [
      ['pl', lic.pl],
      ['ws', lic.ws],
      ['wxMeetingSuite', lic.wxMeetingSuite],
      ['wxMeetings', lic.wxMeetings],
      ['wxContactCenter', lic.wxContactCenter],
    ].filter(([, val]) => val);

    if (!rows.length) {
      const provRaw = BiaSanitizer.sanitizeField(p.provisioned || '');
      if (!provRaw) return '';
      return `<p class="bia-feature-caption">Provisioned licenses</p>${DashboardHtml.kv('Licenses', provRaw, 'Provisioned/Entitled Lic Calling')}`;
    }

    const parts = ['<p class="bia-feature-caption">Provisioned licenses</p>'];
    rows.forEach(([key, val]) => {
      const label = LicenseProductParser.DISPLAY_LABELS[key] || key;
      parts.push(DashboardHtml.licBar(label, val));
    });
    return parts.join('');
  }

  static renderAddonTable(addons) {
    const ADDON_ROWS = CheckBack.Dashboard.Constants.ADDON_ROWS;
    const tbody = ADDON_ROWS.map((name) => {
      const a = addons?.[name] || {};
      const p = a.P ?? a.p ?? '—';
      const t = a.T ?? a.t ?? '—';
      const u = a.U ?? a.u ?? '—';
      return `<tr><td>${DashboardHtml.esc(name)}</td>${BiaSlideRenderer.addonCell(name, 'P', p)}${BiaSlideRenderer.addonCell(name, 'T', t)}${BiaSlideRenderer.addonCell(name, 'U', u)}</tr>`;
    }).join('');
    return `<table class="bia-addon-table">
      <thead><tr><th>Add-Ons</th><th>P</th><th>T</th><th>U</th></tr></thead>
      <tbody>${tbody}</tbody>
    </table>`;
  }

  static renderFeatureCell(label, value, col) {
    const raw = BiaSanitizer.sanitizeField(value || '—');
    const attrs = DashboardHtml.editableAttrs(col);
    return `<div><span>${DashboardHtml.esc(label)}</span><strong${attrs}>${DashboardHtml.esc(raw)}</strong></div>`;
  }

  static notesFromDeck(deck) {
    const out = { analytics: '', features: '', recommended: '' };
    (deck?.notes || []).forEach((n) => {
      const text = BiaSanitizer.sanitizeField(n.text || '');
      if (!text || text.length < 3) return;
      const who = String(n.who || '').toLowerCase();
      if (who.includes('recommend')) {
        out.recommended = out.recommended ? `${out.recommended}\n\n${text}` : text;
      } else if (who.includes('provis')) {
        out.features = out.features ? `${out.features}\n\n${text}` : text;
      } else {
        const line = n.who ? `${n.who}: ${text}` : text;
        out.analytics = out.analytics ? `${out.analytics}\n\n${line}` : line;
      }
    });
    return out;
  }

  static resolveWorkbookNotes(slide) {
    if (slide?.workbookNotes) {
      return {
        analytics: BiaSanitizer.cleanVal(slide.workbookNotes.analytics) || '',
        features: BiaSanitizer.cleanVal(slide.workbookNotes.features) || '',
        recommended: BiaSanitizer.cleanVal(slide.workbookNotes.recommended) || '',
      };
    }
    return BiaSlideRenderer.notesFromDeck(slide);
  }

  static notesField(label, col, value) {
    const raw = BiaSanitizer.cleanVal(value);
    const colAttr = DashboardHtml.escAttr(col);
    return `<div class="insight-notes-field">
      <span class="insight-notes-field-label">${DashboardHtml.esc(label)}</span>
      <div class="insight-notes-edit bia-editable-value" data-col="${colAttr}" contenteditable="false">${raw ? DashboardHtml.esc(raw) : ''}</div>
    </div>`;
  }

  static renderNotesBlock(slide) {
    const wb = BiaSlideRenderer.resolveWorkbookNotes(slide);
    return `<div class="insight-notes-grid">
      ${BiaSlideRenderer.notesField('Calling analytics', 'Notes from Calling Analytics', wb.analytics)}
      ${BiaSlideRenderer.notesField('Provisioned features', 'Notes from provisioned features', wb.features)}
      ${BiaSlideRenderer.notesField('Recommended actions', 'Recommended Actions', wb.recommended)}
    </div>`;
  }

  static render(slide) {
    const deck = BiaSlideMerger.sanitizeSlide(slide);
    const GYR_COL = CheckBack.Dashboard.Constants.GYR_COL;
    const s = deck.subscription || {};
    const p = deck.provisioning || {};
    const f = deck.features || {};
    const h = BiaSanitizer.healthClass(deck.health);
    const gathered =
      deck.gatheredBy || deck.gatheredDate
        ? `Data gathered${deck.gatheredBy ? ' by ' + deck.gatheredBy : ''}${deck.gatheredDate ? ' on ' + deck.gatheredDate : ''}`
        : '';

    const trends = (deck.trends || [])
      .map((t) => `<span class="insight-trend">${DashboardHtml.esc(BiaSanitizer.sanitizeField(t))}</span>`)
      .join('');

    const notesHtml = BiaSlideRenderer.renderNotesBlock(deck);

    const years = deck.timelineYears || 5;
    const nowYear =
      deck.timelineCurrentYear || BiaSanitizer.parseTimelineFromTerm(s.term).currentYear || 2;
    const yearSpans = Array.from({ length: years }, (_, i) => {
      const y = i + 1;
      const now = y === nowYear;
      return now
        ? `<span class="insight-now">Year ${y} · NOW ▼</span>`
        : `<span>Year ${y}</span>`;
    }).join('');

    return `
    <div class="insight-slide bia-slide">
      <div class="insight-top">
        <div class="insight-title-block">
          <h1 class="insight-h1 bia-editable-value" data-col="Opportunity Name" contenteditable="false">${DashboardHtml.esc(deck.customerName)}</h1>
          <p class="insight-subtitle">Business Insight and Analysis</p>
          ${gathered ? `<p class="insight-meta">${DashboardHtml.esc(gathered)}</p>` : ''}
          ${deck.isTemplate ? '<p class="insight-meta bia-template-tag">Reference template slide</p>' : ''}
        </div>
        <div class="insight-health insight-health-${h.class}">
          <span class="bia-editable-value" data-col="${DashboardHtml.escAttr(GYR_COL)}" contenteditable="false">${DashboardHtml.esc(h.label)}</span>
        </div>
      </div>

      <div class="insight-timeline">${yearSpans}</div>

      <div class="insight-panels">
        <section class="insight-panel insight-panel-cyan">
          <h3>Subscription Review</h3>
          ${deck.platforms ? DashboardHtml.kv('Platforms', deck.platforms, 'Platforms') : ''}
          ${DashboardHtml.kv('Subscription', s.sub, 'Sub #')}
          ${DashboardHtml.kv('Term', s.term, 'Subscription dates')}
          ${DashboardHtml.kv('Total Contract Value', s.tcv, 'TCV $')}
          ${DashboardHtml.kv('Total Recurring Revenue (AAR)', s.aar, 'AAR $')}
          ${DashboardHtml.kv('Collab AE/SE', s.collabAe, 'Collab AE/SE')}
          ${DashboardHtml.kv('Segment', s.segment, 'SL2')}
          ${DashboardHtml.kv('Partner', s.partner, 'Partner')}
          ${DashboardHtml.kv('CSM Coverage Model', s.csmModel, 'CSM Engagement Model (linked)')}
          ${BiaSlideRenderer.renderLinksRow(s, deck)}
        </section>

        <section class="insight-panel insight-panel-orange">
          <h3>Provisioning &amp; Usage Data</h3>
          ${DashboardHtml.kv('Customer Org ID', p.orgId || deck.orgId, 'Customer org id')}
          ${DashboardHtml.kv('Licenses (prov/ent)', p.entitled, 'Provisioned/Entitled Lic Calling')}
          ${BiaSlideRenderer.renderProvisionedBlock(p)}
          ${DashboardHtml.kv('Active Users', p.activeUsers, 'Active Lic Calling')}
          ${DashboardHtml.kv('Numbers Assigned / Provisioned', p.numbersAssigned, 'Numbers assigned')}
          ${DashboardHtml.kv('Location w/ Main Number / VM', p.locations, 'Locations main number')}
          ${DashboardHtml.kv('External Calls vs Total', p.externalCalls, 'External calls')}
          ${DashboardHtml.kv('Meetings', p.meetings, 'Meetings usage')}
          ${DashboardHtml.kv('Messaging', p.messaging, 'Messaging usage')}
        </section>

        <section class="insight-panel insight-panel-magenta">
          <h3>Feature use &amp; Add-ons</h3>
          <p class="bia-feature-caption">Included features (Using – how many)</p>
          <div class="insight-feature-grid">
            ${BiaSlideRenderer.renderFeatureCell('Auto Attendant', f.autoAttendant, 'Auto Attendant count')}
            ${BiaSlideRenderer.renderFeatureCell('Hunt Groups', f.huntGroups, 'Hunt Groups count')}
            ${BiaSlideRenderer.renderFeatureCell('Basic Call Queues', f.callQueues, 'Call Queues count')}
            ${BiaSlideRenderer.renderFeatureCell('Connected-UC', f.connectedUc, 'Connected-UC (Y/N)')}
            ${BiaSlideRenderer.renderFeatureCell('Virtual Lines', f.virtualLines, 'Virtual Lines count')}
          </div>
          ${BiaSlideRenderer.renderAddonTable(deck.addons)}
        </section>
      </div>

      ${trends ? `<div class="bia-trends-row">${trends}</div>` : ''}

      <section class="insight-panel insight-panel-notes">
        <h3>Notes &amp; Recommended Actions</h3>
        ${notesHtml}
      </section>

      <div class="insight-footer">© 2025 Cisco · Lookback Program · Cisco Confidential</div>
    </div>`;
  }
}

CheckBack.Dashboard.BiaSlideRenderer = BiaSlideRenderer;
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
/**
 * Schema detection and spreadsheet parsing for Check Back / Renewal / Generic modes.
 */
const SchemaDashboard = (function () {
  const CHECKBACK_MARKERS = [
    'Provisioned/Entitled Lic Calling',
    'Entitled Lic Calling',
    'Providioned Lic Calling',
    ' (G/Y/R)',
  ];
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

  function normalizeParsedRows(rows) {
    return rows.map((row) => {
      const out = { ...row };
      const oid = out['Customer org id'];
      if (oid != null && String(oid).trim() !== '') {
        out['Customer org id'] = String(oid).trim();
      }
      return out;
    });
  }

  function parseWorkbook(arrayBuffer) {
    const wb = XLSX.read(arrayBuffer, { type: 'array', cellDates: true });
    const json = normalizeParsedRows(sheetToJson(wb));
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
      const tabsEl = document.querySelector('.tabs');
      if (tabsEl) tabsEl.style.display = 'none';
      const pdfBtn = document.getElementById('exportPdfBtn');
      if (pdfBtn) pdfBtn.style.display = 'none';
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
      const tabsEl = document.querySelector('.tabs');
      if (tabsEl) tabsEl.style.display = '';
      const pdfBtn = document.getElementById('exportPdfBtn');
      if (pdfBtn) pdfBtn.style.display = '';
    }
  }

  return { detectMode, parseWorkbook, applyModeUI, sheetToJson, isCheckBackSectionRow };
})();
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
 * Public facade for Lookback BIA slide operations (stable global API for index.html).
 */
class BiaTemplateFacade {
  static render(slide) {
    return BiaSlideRenderer.render(slide);
  }

  static findSlide(row) {
    return BiaSlideMatcher.findSlide(row);
  }

  static listSlides() {
    return BiaSlideMatcher.listSlides();
  }

  static healthClass(h) {
    return BiaSanitizer.healthClass(h);
  }

  static enrichRow(row) {
    return BiaPortfolioService.enrichRow(row);
  }

  static enrichAllRows(rows) {
    return BiaPortfolioService.mergePortfolioWithBia(rows);
  }

  static mergePortfolioWithBia(rows, options) {
    return BiaPortfolioService.mergePortfolioWithBia(rows, options);
  }

  static workbookRowsOnly(rows) {
    return BiaPortfolioService.workbookRowsOnly(rows);
  }

  static collectAllColumns(rows) {
    return BiaPortfolioService.collectAllColumns(rows);
  }

  static mergeSlideWithRow(row, slide) {
    return BiaSlideMerger.mergeSlideWithRow(row, slide);
  }

  static rowToSlide(row) {
    return BiaWorkbookMapper.rowToSlide(row);
  }

  static sanitizeSlide(slide) {
    return BiaSlideMerger.sanitizeSlide(slide);
  }

  static healthToGyr(health) {
    return BiaSanitizer.healthToGyr(health);
  }
}

CheckBack.Dashboard.BiaTemplate = BiaTemplateFacade;

/** @deprecated Use CheckBack.Dashboard.BiaTemplate — kept for index.html and inline handlers. */
const BiaTemplate = BiaTemplateFacade;
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
/**
 * Export in-memory dashboard customer rows (portfolio / data table) to xlsx.
 */
const DashboardExport = (function () {
  function exportColumns(columns) {
    return columns.filter(
      (c) =>
        c &&
        c !== '_biaSlideOnly' &&
        (!String(c).startsWith('_') || c === '_addonsPtu')
    );
  }

  function cellValue(val) {
    if (val == null) return '';
    if (val instanceof Date) return val.toISOString().slice(0, 10);
    return val;
  }

  function rowForExport(row, columns) {
    const out = {};
    columns.forEach((col) => {
      out[col] = cellValue(row[col]);
    });
    return out;
  }

  function filenameFromDisplay(displayName) {
    const base = String(displayName || 'check_back').replace(/\.xlsx?$/i, '');
    return base + '_from_dashboard.xlsx';
  }

  function mergeExportColumns(columns, rows) {
    const cols = exportColumns(columns || []);
    const seen = new Set(cols);
    (rows || []).forEach((row) => {
      Object.keys(row || {}).forEach((k) => {
        if (!k || seen.has(k)) return;
        if (k.startsWith('_') && k !== '_addonsPtu') return;
        seen.add(k);
        cols.push(k);
      });
    });
    return cols;
  }

  function exportCustomerData(rows, columns, displayName) {
    if (typeof XLSX === 'undefined') throw new Error('Spreadsheet library not loaded');
    if (!rows || !rows.length) throw new Error('No customer rows in the dashboard table');
    const workbookRows = rows.filter((r) => !r._biaSlideOnly);
    const exportRows = workbookRows.length ? workbookRows : rows;
    const cols = mergeExportColumns(columns, exportRows);
    if (!cols.length) throw new Error('No columns to export');
    const body = exportRows.map((row) => rowForExport(row, cols));
    const ws = XLSX.utils.json_to_sheet(body, { header: cols });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Customer Data');
    XLSX.writeFile(wb, filenameFromDisplay(displayName));
  }

  return {
    exportColumns,
    mergeExportColumns,
    exportCustomerData,
    filenameFromDisplay,
  };
})();
