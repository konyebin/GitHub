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
