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
