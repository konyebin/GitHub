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
