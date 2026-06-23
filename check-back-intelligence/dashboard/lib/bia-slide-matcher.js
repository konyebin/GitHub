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
