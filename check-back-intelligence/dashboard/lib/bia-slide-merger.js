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
