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
