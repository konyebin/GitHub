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
