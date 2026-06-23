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
