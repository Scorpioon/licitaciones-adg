/*
 * ADG Plataforma Digital -- shared.js
 * b4.0 -- Mar 2026
 * Role: Shared UI components -- FichaPanel, TrafficLight, ToggleSwitch,
 *       AlertasStub. Available on all pages after app.js.
 * Page: All pages (loaded second, after app.js, before page script)
 * Depends on: app.js -- bare globals: DISC, TERR, ADG
 *             app.js -- ADG_Utils: el, t, fmt, fmtFull, daysTo, isNew,
 *                       discColor, discTag, stateBadge, applyI18n
 * Exports: window.ADG_Shared
 *
 * CHANGELOG (newest first)
 * 0.7.1v Aug 2026 p272 document inventory: deterministic role labels, dedupe and
 *                  ordering over r.documents; two processing states only
 *                  (inventory / resolved); strict https: link rule; factual
 *                  tender-level counts replace the former constant
 *                  pending-enrichment badge.
 * 0.6.36 Jun 2026 fichaHTML emits a drag-grip handle (mobile bottom-sheet, p179). Hidden on desktop via CSS.
 * 0.4.4q May 2026  computeTrafficLight and computeAdvisory use getDisplayStatus/isOpenOpportunity.
 *                   fichaHTML uses stateBadgeRow for current record badge.
 * b4.0  Mar 2026  Initial. FichaPanel, TrafficLight (D8 approved ruleset),
 *                 advisory layer (D9 approved rules), ToggleSwitch,
 *                 AlertasStub. Components available but not yet wired
 *                 to existing pages (Phase 2+).
 */
;(function () {
'use strict';

var _utils = ADG_Utils;
var t = _utils.t, fmt = _utils.fmt, fmtFull = _utils.fmtFull,
    daysTo = _utils.daysTo, isNew = _utils.isNew,
    discColor = _utils.discColor, discTag = _utils.discTag, discNoneTag = _utils.discNoneTag,
    stateBadge = _utils.stateBadge,
    getDisplayStatus = _utils.getDisplayStatus,
    isOpenOpportunity = _utils.isOpenOpportunity,
    stateBadgeRow = _utils.stateBadgeRow;

// -- Local utilities ----------------------------------------------------------

function esc(s) {
  return String(s || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function cpvArray(cpvStr) {
  if (!cpvStr) return [];
  return cpvStr.split(',').map(function(s){ return s.trim(); }).filter(Boolean);
}

// -- TRAFFIC LIGHT ------------------------------------------------------------
// D8 approved beta-v1 ruleset. Computed client-side, not stored in JSON.
//
// GOOD    ALL of: pressupost >= 10000, daysTo >= 15, Vigente, no adjudicatari
// BAD     ANY of: 0 < pressupost < 3000, 0 <= daysTo < 10, Desierta
// MEDIUM  Vigente, not GOOD, not BAD
// UNKNOWN Adjudicado, or no deadline AND no budget

function computeTrafficLight(r) {
  var ds     = getDisplayStatus(r);
  var days   = daysTo(r.data_limit);
  var budget = r.pressupost || 0;
  var hasAdj = !!(r.adjudicatari && r.adjudicatari.trim());

  if (ds.key === 'desierta')   return { verdict: 'bad',     label: t('tl_bad')     };
  if (ds.key === 'adjudicado') return { verdict: 'unknown',  label: t('tl_unknown') };
  if (!isOpenOpportunity(r))   return { verdict: 'unknown',  label: t('tl_unknown') };

  var isBad  = (budget > 0 && budget < 3000) ||
               (days !== null && days >= 0 && days < 10);
  var isGood = (budget >= 10000) &&
               (days !== null && days >= 15) &&
               !hasAdj;

  if (isBad)  return { verdict: 'bad',    label: t('tl_bad')    };
  if (isGood) return { verdict: 'good',   label: t('tl_good')   };
  return      { verdict: 'medium', label: t('tl_medium') };
}

function TrafficLight(r) {
  var tl = computeTrafficLight(r);
  return '<div class="sh-traffic sh-traffic--' + tl.verdict + '">' +
    '<div class="sh-traffic__dot"></div>' +
    '<div class="sh-traffic__content">' +
      '<div class="sh-traffic__label">' + esc(tl.label) + '</div>' +
    '</div>' +
  '</div>';
}

// -- ADVISORY LAYER -----------------------------------------------------------
// D9 approved beta-v1 rules. Computed client-side, not stored in JSON.

function computeAdvisory(r) {
  var days      = daysTo(r.data_limit);
  var budget    = r.pressupost || 0;
  var estat     = r.estat || '';
  var estatRaw  = r.estat_raw || '';
  var hasAdj    = !!(r.adjudicatari && r.adjudicatari.trim());
  var tips = [], warns = [], notes = [];

  if (days !== null && days >= 20)       tips.push('Plazo generoso. Tiempo para preparar una propuesta de calidad.');
  else if (days !== null && days >= 10)  tips.push('Plazo razonable. Organiza la documentacion con antelacion.');
  if (budget >= 50000)                   tips.push('Presupuesto significativo. Vale la pena una propuesta solida.');
  else if (budget >= 10000)              tips.push('Presupuesto dentro del rango profesional habitual.');
  if (isOpenOpportunity(r) && !hasAdj)
    tips.push('Licitacion activa y sin adjudicatario. Oportunidad real.');

  if (budget > 0 && budget < 3000)               warns.push('Presupuesto por debajo del umbral minimo recomendado por ADG-FAD.');
  if (days !== null && days >= 0 && days < 10)    warns.push('Plazo muy ajustado -- verifica si puedes cumplir los requisitos.');
  if (days !== null && days < 0)                  warns.push('El plazo de presentacion ya ha vencido.');
  if (hasAdj)                                     warns.push('Ya tiene adjudicatario. Util como referencia, no como oportunidad activa.');
  if (r.ccaa === 'ES')                            warns.push('Ambito estatal. Puede requerir mayor solvencia tecnica acreditada.');
  if (getDisplayStatus(r).key === 'desierta')     warns.push('Declarada desierta. Puede republicarse -- util para seguir el organismo.');

  if ((r.historial || []).length > 1) notes.push('Esta licitacion tiene historial de cambios de estado.');
  var cpvs = cpvArray(r.cpv);
  if (cpvs.some(function(c){ return c.indexOf('79') === 0; })) notes.push('CPV 79: servicios empresariales y creativos.');
  if (estatRaw === 'EV' || estatRaw === 'PRE')    notes.push('En evaluacion / seguimiento. Revisar estado oficial.');

  return { tips: tips, warns: warns, notes: notes };
}

function advisoryHTML(r) {
  var adv = computeAdvisory(r);
  if (!adv.tips.length && !adv.warns.length && !adv.notes.length) return '';
  var items = [];
  adv.tips.forEach(function(msg) {
    items.push('<div class="sh-advisory__item sh-advisory__item--tip"><i class="bi bi-check-circle"></i><span>' + esc(msg) + '</span></div>');
  });
  adv.warns.forEach(function(msg) {
    items.push('<div class="sh-advisory__item sh-advisory__item--warn"><i class="bi bi-exclamation-triangle"></i><span>' + esc(msg) + '</span></div>');
  });
  adv.notes.forEach(function(msg) {
    items.push('<div class="sh-advisory__item sh-advisory__item--note"><i class="bi bi-info-circle"></i><span>' + esc(msg) + '</span></div>');
  });
  return '<div class="sh-advisory">' + items.join('') + '</div>';
}

// -- MINIRESUMEN (p201) -------------------------------------------------------
// Factual, templated, NON-generative one-line summary built ONLY from existing
// structured record fields. Canonical data has no free-text body, so this is
// pure field-templating with independent fallbacks. It never invents
// requirements, eligibility, scoring, documents, locations, entities, deadlines
// or budgets. Computed at render time (like computeTrafficLight/computeAdvisory);
// never stored in JSON. Returns a plain string.
function computeMiniResumen(r) {
  var langStr = (ADG.lang || 'es') + '-ES';

  // discipline / type clause (independent fallback)
  var discs = r.disciplines || [];
  var discLabel = (discs.length && DISC[discs[0]]) ? DISC[discs[0]].label
                : (r.tipus && String(r.tipus).trim() ? String(r.tipus).trim() : '');

  // organism (canonical audit: always present)
  var organisme = (r.organisme && String(r.organisme).trim()) ? String(r.organisme).trim() : '—';

  // budget clause
  var budgetTok = (r.pressupost || r.pressupost === 0) ? fmtFull(r.pressupost) : t('fp_rsum_budget_na');

  // deadline clause
  var deadlineTok = r.data_limit
    ? t('fp_rsum_deadline_to').replace('{date}', new Date(r.data_limit).toLocaleDateString(langStr, { day:'numeric', month:'short', year:'numeric' }))
    : t('fp_rsum_deadline_na');

  var tmpl = discLabel ? t('fp_rsum_full') : t('fp_rsum_full_nodisc');
  var base = tmpl
    .replace('{disc}', discLabel)
    .replace('{org}', organisme)
    .replace('{budget}', budgetTok)
    .replace('{deadline}', deadlineTok);

  // Status / urgency suffix — appended only when supported by existing fields.
  var ds   = getDisplayStatus(r);
  var days = daysTo(r.data_limit);
  var statusTok = '';
  if (ds.key === 'open' && days !== null && days >= 0 && days <= 7) statusTok = t('fp_rsum_expires').replace('{n}', days);
  else if (ds.key === 'adjudicado') statusTok = t('fp_rsum_awarded');
  else if (ds.key === 'desierta')   statusTok = t('fp_rsum_void');

  return statusTok ? (base + ' · ' + statusTok) : base;
}

// -- ASSESSMENT BLOCK (compact rating + signals, replaces TrafficLight+advisory) --
function assessmentBlock(r) {
  var tl = computeTrafficLight(r);
  var adv = computeAdvisory(r);
  var signals = [];
  adv.tips.forEach(function(msg)  { signals.push('<div class="sh-assess__sig sh-assess__sig--tip"><i class="bi bi-check-circle"></i><span>' + esc(msg) + '</span></div>'); });
  adv.warns.forEach(function(msg) { signals.push('<div class="sh-assess__sig sh-assess__sig--warn"><i class="bi bi-exclamation-triangle"></i><span>' + esc(msg) + '</span></div>'); });
  adv.notes.forEach(function(msg) { signals.push('<div class="sh-assess__sig sh-assess__sig--note"><i class="bi bi-info-circle"></i><span>' + esc(msg) + '</span></div>'); });
  return (
    '<div class="sh-assess sh-assess--' + tl.verdict + '">' +
      '<div class="sh-assess__label-box">' +
        '<span class="sh-assess__dot"></span>' +
        '<span class="sh-assess__label">' + esc(tl.label) + '</span>' +
      '</div>' +
      '<div class="sh-assess__signal-box">' +
        (signals.length ? signals.join('') : '<span class="sh-assess__sig sh-assess__sig--note"><i class="bi bi-dash-circle"></i><span>&mdash;</span></span>') +
      '</div>' +
    '</div>'
  );
}

// -- DOCUMENT INVENTORY (p272) ------------------------------------------------
// Presentation layer over record.documents. This surface renders document
// INVENTORY only: what an official source referenced, plus whether a link was
// resolved at some past crawl. It never claims retrieval, parsing, extraction,
// OCR, review, confidence or current reachability -- canonical data carries
// none of those states, so the UI must not imply them.
//
// Two processing states exist and no more:
//   inventory -- an official source referenced the document
//   resolved  -- the link was resolved at a past crawl (past tense, always)

// Strict document link rule: only an absolute https: URL with a non-empty
// hostname may render as a clickable anchor. Relative paths, http:,
// javascript:, data:, file:, blob:, fragments and malformed values all fail,
// and the item then renders as non-interactive metadata instead of a dead link.
function isValidDocUrl(url) {
  if (typeof url !== 'string') return false;
  var raw = url.trim();
  if (!raw.length) return false;
  var parsed;
  try { parsed = new URL(raw); } catch (e) { return false; }
  return parsed.protocol === 'https:' && !!parsed.hostname;
}

function docStr(v) {
  return (typeof v === 'string') ? v.trim() : '';
}

// Notice-type role keys, used only under additionalpublicationdocumentreference.
var DOC_NOTICE_ROLE_KEYS = {
  PUB                   : 'doc_role_notice_publication',
  AWARD                 : 'doc_role_notice_award',
  RES                   : 'doc_role_notice_resolution',
  EV                    : 'doc_role_notice_evaluation',
  PRE                   : 'doc_role_notice_preliminary',
  CONTRACT_MODIFICATION : 'doc_role_notice_contract_modification'
};

// Deterministic role classification from existing canonical fields only.
// Never infers from URL or filename substrings; never returns an empty key or
// a raw source token. Returns an i18n key, never a display string.
function documentRoleKey(d) {
  if (!d) return 'doc_role_document';
  var section = docStr(d.source_section).toLowerCase();
  var type    = docStr(d.document_type);
  var notice  = docStr(d.notice_type).toUpperCase();

  if (section === 'legaldocumentreference')     return 'doc_role_pcap';
  if (section === 'technicaldocumentreference') return 'doc_role_ppt';
  if (type === 'ACTA_ADJ')     return 'doc_role_award_minutes';
  if (type === 'ACTA_FORM')    return 'doc_role_formalization_minutes';
  if (type === 'pliego_admin') return 'doc_role_admin_spec';
  if (section === 'additionalpublicationdocumentreference' &&
      Object.prototype.hasOwnProperty.call(DOC_NOTICE_ROLE_KEYS, notice)) {
    return DOC_NOTICE_ROLE_KEYS[notice];
  }
  if (section === 'f2_document_evidence') return 'doc_role_tender_document';
  return 'doc_role_document';
}

function isResolverDocument(d) {
  return !!d && d.provenance === 'f2b_resolver';
}

// The only authorized "resolved" predicate. Everything else is inventory.
function isResolvedDocument(d) {
  return isResolverDocument(d) && (d.http_status === 200 || d.http_status === '200');
}

// Canonical identity for presentation-layer dedupe only. Lowercases scheme and
// host (case-insensitive by spec) and leaves the path untouched. A value that
// does not parse yields no identity at all: docIdentity then falls through to
// original_url and finally to the guarded metadata composite, so two malformed
// values are never treated as the same document on the strength of matching
// junk.
function normalizeDocUrl(value) {
  var raw = docStr(value);
  if (!raw) return '';
  var parsed;
  try { parsed = new URL(raw); } catch (e) { return ''; }
  return parsed.protocol.toLowerCase() + '//' + parsed.host.toLowerCase() +
         parsed.pathname + parsed.search + parsed.hash;
}

function docIdentity(d) {
  var u = normalizeDocUrl(d.url);
  if (u) return 'u:' + u;
  var o = normalizeDocUrl(d.original_url);
  if (o) return 'u:' + o;
  // Metadata composite, for local display dedupe only. It counts as an identity
  // only when a distinguishing field is present -- source_section alone is
  // shared by thousands of entries and would collapse unrelated documents.
  var distinguishing = [docStr(d.notice_id), docStr(d.document_type),
                        docStr(d.title), docStr(d.published_at)];
  if (!distinguishing.join('')) return '';
  return 'm:' + distinguishing.concat([docStr(d.notice_type), docStr(d.source_section)]).join('|');
}

// Deterministic dedupe. Returns a NEW array; never mutates record.documents and
// never synthesizes an object merging fields from two different producers. When
// identity cannot be established safely both items are retained.
function canonicalDocumentItems(documents) {
  if (!documents || typeof documents.length !== 'number') return [];
  var out = [], seen = {}, i, d, key, prev;
  for (i = 0; i < documents.length; i++) {
    d = documents[i];
    if (!d || typeof d !== 'object') continue;
    key = docIdentity(d);
    if (!key) { out.push(d); continue; }
    if (!Object.prototype.hasOwnProperty.call(seen, key)) {
      seen[key] = out.length;
      out.push(d);
      continue;
    }
    // Same final URL: keep the resolver item, which carries the richer field
    // set. Never merge values across the two producers.
    prev = seen[key];
    if (isResolverDocument(d) && !isResolverDocument(out[prev])) out[prev] = d;
  }
  return out;
}

function documentSortRank(d) {
  var section = docStr(d.source_section).toLowerCase();
  if (section === 'legaldocumentreference')     return 0;
  if (section === 'technicaldocumentreference') return 1;
  if (isResolvedDocument(d))                    return 2;
  return 3;
}

function documentSortTime(d) {
  var raw = docStr(d.published_at);
  if (!raw) return Number.NEGATIVE_INFINITY;
  var ms = new Date(raw).getTime();
  return isNaN(ms) ? Number.NEGATIVE_INFINITY : ms;
}

// Decorate-sort-undecorate: deterministic without relying on engine sort
// stability. Original array order is the final tie-break.
function orderedDocumentItems(items) {
  var decorated = items.map(function (d, i) {
    return { doc: d, idx: i, rank: documentSortRank(d), ts: documentSortTime(d) };
  });
  decorated.sort(function (a, b) {
    if (a.rank !== b.rank) return a.rank - b.rank;
    if (a.rank === 3 && a.ts !== b.ts) return b.ts - a.ts;
    return a.idx - b.idx;
  });
  return decorated.map(function (e) { return e.doc; });
}

// Readable label for proven format values only. Never inferred from the URL.
var DOC_FORMAT_LABELS = {
  'application/pdf' : 'PDF',
  'pdf'             : 'PDF'
};

function documentFormatLabel(d) {
  var raw = docStr(d.mime_hint) || docStr(d.format_hint);
  if (!raw) return '';
  var known = DOC_FORMAT_LABELS[raw.toLowerCase()];
  if (known) return known;
  return raw.length > 24 ? raw.slice(0, 24) : raw;
}

function documentDateLabel(d, langStr) {
  var raw = docStr(d.published_at);
  if (!raw) return '';
  var ms = new Date(raw).getTime();
  if (isNaN(ms)) return raw.length > 24 ? raw.slice(0, 24) : raw;
  return new Date(ms).toLocaleDateString(langStr, { day:'numeric', month:'short', year:'numeric' });
}

function documentItemHTML(d, langStr) {
  var roleLabel = t(documentRoleKey(d));
  var title     = docStr(d.title);
  var headline  = title || roleLabel;
  var resolved  = isResolvedDocument(d);
  var clickable = isValidDocUrl(d.url);

  var meta = [];
  // Only show the role separately when the title is not already the role label.
  if (title) meta.push('<span class="sh-ficha__doc-role">' + esc(roleLabel) + '</span>');
  meta.push('<span class="sh-ficha__doc-badge' + (resolved ? ' sh-ficha__doc-badge--resolved' : '') + '">' +
    esc(t(resolved ? 'fp_doc_state_resolved' : 'fp_doc_state_inventory')) + '</span>');
  var fmt = documentFormatLabel(d);
  if (fmt) meta.push('<span class="sh-ficha__doc-fmt">' + esc(fmt) + '</span>');
  var date = documentDateLabel(d, langStr);
  if (date) meta.push('<span class="sh-ficha__doc-date">' + esc(date) + '</span>');
  if (!clickable) meta.push('<span class="sh-ficha__doc-nolink">' + esc(t('fp_doc_no_link')) + '</span>');

  var inner =
    '<i class="bi bi-file-earmark-text" aria-hidden="true"></i>' +
    '<span class="sh-ficha__doc-body">' +
      '<span class="sh-ficha__doc-title">' + esc(headline) + '</span>' +
      '<span class="sh-ficha__doc-meta">' + meta.join('') + '</span>' +
    '</span>';

  // An unsafe or absent URL keeps its metadata but never becomes an anchor, and
  // the raw value is never emitted.
  return clickable
    ? '<a class="sh-ficha__doc sh-ficha__doc--link" href="' + esc(docStr(d.url)) + '" target="_blank" rel="noopener">' + inner + '</a>'
    : '<div class="sh-ficha__doc sh-ficha__doc--static">' + inner + '</div>';
}

function documentSummaryHTML(items) {
  if (!items.length) return '';
  var resolved = items.filter(isResolvedDocument).length;
  var countTxt = (items.length === 1)
    ? t('fp_docs_count_one')
    : t('fp_docs_count').replace('{n}', items.length);
  var parts = '<span class="sh-ficha__doc-count">' + esc(countTxt) + '</span>';
  // m == 0 omits the clause entirely rather than printing "0 verificados".
  if (resolved > 0) {
    var resTxt = (resolved === 1)
      ? t('fp_docs_resolved_one')
      : t('fp_docs_resolved').replace('{m}', resolved);
    parts += '<span class="sh-ficha__doc-resolved">' + esc(resTxt) + '</span>';
  }
  return '<div class="sh-ficha__doc-status">' + parts + '</div>';
}

function officialSourceLinkHTML(recordUrl) {
  if (!isValidDocUrl(recordUrl)) return '';
  return '<a class="sh-ficha__doc-src" href="' + esc(docStr(recordUrl)) + '" target="_blank" rel="noopener">' +
    '<i class="bi bi-box-arrow-up-right" aria-hidden="true"></i>' +
    '<span>' + esc(t('fp_docs_official_source')) + '</span>' +
  '</a>';
}

// -- FICHA PANEL --------------------------------------------------------------
// Renders a full 1:1 analytical record for a tender.
//
// fichaHTML(record)
//   returns HTML string for innerHTML injection
//
// FichaPanel(record, opts)
//   opts.mode      'side' | 'overlay'  (default 'side')
//   opts.container Element -- renders into container (side mode)
//                  if omitted, creates overlay appended to body
//   opts.onClose   Function -- called on close
//
// FichaClose(containerEl)
//   removes open state / clears container

function fichaHTML(r) {
  var days    = daysTo(r.data_limit);
  var langStr = (ADG.lang || 'es') + '-ES';
  var dlFact          = r.data_limit ? new Date(r.data_limit).toLocaleDateString(langStr, { day:'numeric', month:'short', year:'2-digit' }) : '&mdash;';
  var pubFact         = r.data_pub   ? new Date(r.data_pub).toLocaleDateString(langStr,   { day:'numeric', month:'short', year:'2-digit' }) : '&mdash;';
  var deadlineFactClass = (days !== null && days >= 0 && days <= 7) ? ' sh-ficha__fact--warn' : '';
  var terrLabel = r.lloc || (r.ccaa && TERR[r.ccaa] ? TERR[r.ccaa].name : r.ccaa) || '';

  var ds = getDisplayStatus(r);
  var stateColor = { 'b-ok':'var(--s-ok)', 'b-adj':'var(--s-adj)', 'b-des':'var(--s-des)', 'b-warn':'var(--s-warn)' }[ds.cssClass] || '';
  var stateStyle = stateColor ? ' style="color:' + stateColor + ';font-weight:700"' : '';

  var factsHTML =
    '<div class="sh-ficha__facts">' +
      // Row 1: Estado | Presupuesto
      '<div class="sh-ficha__fact">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_status')) + '</div>' +
        '<div class="sh-ficha__fact-val"' + stateStyle + '>' + esc(ds.label || '—') + '</div>' +
      '</div>' +
      '<div class="sh-ficha__fact">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_budget')) + '</div>' +
        '<div class="sh-ficha__fact-val sh-ficha__fact-val--amt">' + fmtFull(r.pressupost) + '</div>' +
      '</div>' +
      // Row 2: Territorio | Vencimiento
      '<div class="sh-ficha__fact">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_terr')) + '</div>' +
        '<div class="sh-ficha__fact-val">' + esc(terrLabel || '—') + '</div>' +
      '</div>' +
      '<div class="sh-ficha__fact' + deadlineFactClass + '">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_deadline')) + '</div>' +
        '<div class="sh-ficha__fact-val">' + dlFact + '</div>' +
      '</div>' +
      // Row 3: Organismo (wide)
      '<div class="sh-ficha__fact sh-ficha__fact--wide">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_organism')) + '</div>' +
        '<div class="sh-ficha__fact-val">' + esc(r.organisme || '—') + '</div>' +
      '</div>' +
      // Row 4: Tipo | Publicación
      '<div class="sh-ficha__fact">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_type')) + '</div>' +
        '<div class="sh-ficha__fact-val">' + esc(r.tipus || '—') + '</div>' +
      '</div>' +
      '<div class="sh-ficha__fact">' +
        '<div class="sh-ficha__fact-key">' + esc(t('fp_published')) + '</div>' +
        '<div class="sh-ficha__fact-val">' + pubFact + '</div>' +
      '</div>' +
      // Row 5: Adjudicado a (wide, conditional)
      (r.adjudicatari ?
        '<div class="sh-ficha__fact sh-ficha__fact--wide">' +
          '<div class="sh-ficha__fact-key">' + esc(t('fp_adjudicado_a')) + '</div>' +
          '<div class="sh-ficha__fact-val">' + esc(r.adjudicatari) + '</div>' +
        '</div>'
      : '') +
    '</div>';

  var validDiscs = (r.disciplines || []).filter(function(d){ return !!DISC[d]; });
  var discHTML = validDiscs.length
    ? validDiscs.map(function(d){ return discTag(d,'9px'); }).join('')
    : discNoneTag('9px');

  var kwChips = (r.kw || []).map(function(k){ return '<span class="sh-ficha__chip"><i class="bi bi-tag"></i>' + esc(k) + '</span>'; });
  if (r.cpv) cpvArray(r.cpv).slice(0, 3).forEach(function(c){ kwChips.push('<span class="sh-ficha__chip"><i class="bi bi-upc"></i>' + esc(c) + '</span>'); });
  kwChips.push('<span class="sh-ficha__chip sh-ficha__chip--src"><i class="bi bi-database"></i>' + esc(r.font || 'PLACSP') + '</span>');
  var kwHTML = kwChips.join('');

  // Document inventory surface (p272). Every referenced document is retained and
  // described; only its clickability depends on the strict https: rule.
  var docItems = orderedDocumentItems(canonicalDocumentItems(r.documents));
  var docsHTML;
  if (!docItems.length) {
    docsHTML =
      '<div class="sh-ficha__doc-empty">' +
        '<span class="sh-ficha__empty">' + esc(t('fp_no_docs')) + '</span>' +
        officialSourceLinkHTML(r.url) +
      '</div>';
  } else {
    docsHTML = docItems.map(function(d){ return documentItemHTML(d, langStr); }).join('');
    // When no item is clickable, keep a route to the tender's official source.
    if (!docItems.some(function(d){ return isValidDocUrl(d.url); })) {
      docsHTML += officialSourceLinkHTML(r.url);
    }
  }

  var docStatusHTML = documentSummaryHTML(docItems);

  var hist    = r.historial || [];
  var histHTML = hist.length
    ? '<div class="sh-ficha__hist">' + hist.map(function(h){
        return '<div class="sh-ficha__hist-item">' +
          '<div class="sh-ficha__hist-date">' + esc(h.data||'') + '</div>' +
          stateBadge(h.estat) +
          '<div class="sh-ficha__hist-nota">' + esc(h.nota||'') + '</div></div>';
      }).join('') + '</div>'
    : '<span class="sh-ficha__empty">' + esc(t('fp_no_history')) + '</span>';

  var rels = r.duplicate_relations || [];
  var relsSection = '';
  if (rels.length) {
    var rChips = rels.map(function(rel){
      return '<div class="sh-ficha__chip"><i class="bi bi-link-45deg"></i>' + esc(rel.tender_id) + ' &middot; ' + esc(rel.relation_type) + '</div>';
    }).join('');
    relsSection = '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_relations')) + '</div><div class="sh-ficha__chips">' + rChips + '</div></div>';
  }

  var ctaHref = (r.url && r.url.indexOf('http') === 0) ? r.url : 'https://contrataciondelestado.es';
  var ctaNote = (r.url && r.url.indexOf('http') === 0) ? '' : '<p class="sh-ficha__cta-note">URL directa no disponible</p>';

  return (
    '<div class="sh-ficha__grip" aria-hidden="true"><span class="sh-ficha__grip-bar"></span></div>' +
    '<div class="sh-ficha__head">' +
      '<span class="sh-ficha__eyebrow">' + esc(t('fp_eyebrow')) + '</span>' +
      '<button class="sh-ficha__close" aria-label="' + esc(t('fp_close')) + '"><i class="bi bi-x"></i></button>' +
    '</div>' +
    '<div class="sh-ficha__top">' +
      '<div class="sh-ficha__title" id="ficha-title">' + esc(r.titol || '—') + (isNew(r) ? ' <span class="badge-new">' + esc(t('nueva')) + '</span>' : '') + '</div>' +
      '<div class="sh-ficha__resumen">' + esc(computeMiniResumen(r)) + '</div>' +
      factsHTML +
      assessmentBlock(r) +
    '</div>' +
    '<div class="sh-ficha__scroll">' +
      '<div class="sh-ficha__cols">' +
        '<div class="sh-ficha__col">' +
          '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_disciplines')) + '</div><div class="sh-ficha__chips">' + discHTML + '</div></div>' +
          '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_keywords'))    + '</div><div class="sh-ficha__chips">' + kwHTML   + '</div></div>' +
          '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_history'))     + '</div>' + histHTML + '</div>' +
        '</div>' +
        '<div class="sh-ficha__col">' +
          '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_documents'))   + '</div><div class="sh-ficha__docs">'  + docStatusHTML + docsHTML + '</div></div>' +
        '</div>' +
      '</div>' +
      relsSection +
    '</div>' +
    '<div class="sh-ficha__footer">' +
      '<div class="sh-ficha__actions">' +
        '<a class="sh-ficha__cta" href="' + esc(ctaHref) + '" target="_blank" rel="noopener">' +
          '<i class="bi bi-box-arrow-up-right"></i> ' + esc(t('fp_view_official')) +
        '</a>' +
        '<button class="sh-ficha__share" aria-label="' + esc(t('fp_share')) + '"><i class="bi bi-share"></i></button>' +
      '</div>' +
      ctaNote +
    '</div>'
  );
}

function FichaPanel(record, opts) {
  opts = opts || {};
  var container = opts.container || null;
  var onClose   = opts.onClose   || null;

  if (container) {
    container.innerHTML = fichaHTML(record);
    container.classList.add('open');
    _bindFichaEvents(container, onClose);
  } else {
    var wrap  = document.createElement('div');
    wrap.className = 'sh-ficha sh-ficha--overlay';
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-modal', 'true');
    var inner = document.createElement('div');
    inner.className = 'sh-ficha__wrap';
    inner.innerHTML = fichaHTML(record);
    wrap.appendChild(inner);
    document.body.appendChild(wrap);
    _bindFichaEvents(inner, function(){ wrap.remove(); if (onClose) onClose(); });
    wrap.addEventListener('click', function(e){
      if (e.target === wrap){ wrap.remove(); if (onClose) onClose(); }
    });
  }
}

function FichaClose(containerEl) {
  if (!containerEl) return;
  containerEl.classList.remove('open');
  containerEl.innerHTML = '';
}

function _bindFichaEvents(el, onClose) {
  var closeBtn = el.querySelector('.sh-ficha__close');
  if (closeBtn) closeBtn.addEventListener('click', function(){ if (onClose) onClose(); });

  var shareBtn = el.querySelector('.sh-ficha__share');
  if (shareBtn) {
    shareBtn.addEventListener('click', function(){
      if (navigator.clipboard) {
        navigator.clipboard.writeText(location.href).then(function(){
          shareBtn.innerHTML = '<i class="bi bi-check2"></i>';
          setTimeout(function(){ shareBtn.innerHTML = '<i class="bi bi-share"></i>'; }, 1800);
        });
      }
    });
  }

  var escH = function(e){
    if (e.key === 'Escape'){ if (onClose) onClose(); document.removeEventListener('keydown', escH); }
  };
  document.addEventListener('keydown', escH);
}

// -- TOGGLE SWITCH ------------------------------------------------------------
// Creates a toggle button group inside the given wrapper element.
//
// Usage:
//   ToggleSwitch('wrapper-id', [
//     { id: 'stats',     label: t('sw_stats') },
//     { id: 'barometro', label: t('sw_barometro') }
//   ], function(id){ switchView(id); }, 0);
//
// Returns { setActive: function(id){} }

function ToggleSwitch(wrapperId, items, onChange, defaultIdx) {
  var wrap = (typeof wrapperId === 'string') ? document.getElementById(wrapperId) : wrapperId;
  if (!wrap){ console.warn('[ADG_Shared] ToggleSwitch: wrapper not found', wrapperId); return null; }
  if (!defaultIdx) defaultIdx = 0;
  var activeId = (items[defaultIdx] || items[0]).id;

  function renderToggle(){
    wrap.innerHTML = '<div class="sh-toggle">' +
      items.map(function(item){
        return '<button class="sh-toggle__btn' + (item.id === activeId ? ' active' : '') +
          '" data-toggle-id="' + esc(item.id) + '">' + esc(item.label) + '</button>';
      }).join('') + '</div>';
    wrap.querySelectorAll('.sh-toggle__btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        activeId = btn.dataset.toggleId;
        renderToggle();
        if (onChange) onChange(activeId);
      });
    });
  }

  renderToggle();
  return { setActive: function(id){ activeId = id; renderToggle(); } };
}

// -- ALERTAS STUB -------------------------------------------------------------
// Renders the alertas stub UI. All interactions show a coming-soon modal.
// No data is submitted or persisted.

function AlertasStub(containerEl) {
  if (!containerEl) return;

  containerEl.innerHTML =
    '<div class="sh-alertas">' +
      '<div class="sh-alertas__header">' +
        '<div class="sh-alertas__title"><i class="bi bi-bell" style="margin-right:8px;opacity:.6"></i>' + esc(t('alr_title')) + '</div>' +
        '<div class="sh-alertas__desc">' + esc(t('alr_coming_soon_d')) + '</div>' +
      '</div>' +
      '<div class="sh-alertas__profile">' +
        '<button class="sh-alertas__profile-btn" data-alr-profile="talent">' +
          '<i class="bi bi-mortarboard" style="display:block;font-size:18px;margin-bottom:6px;opacity:.5"></i>' +
          esc(t('alr_profile_talent')) +
        '</button>' +
        '<button class="sh-alertas__profile-btn" data-alr-profile="pro">' +
          '<i class="bi bi-person-badge" style="display:block;font-size:18px;margin-bottom:6px;opacity:.5"></i>' +
          esc(t('alr_profile_pro')) +
        '</button>' +
      '</div>' +
      '<div class="sh-alertas__criteria">' +
        '<div class="sh-alertas__field"><div class="sh-alertas__field-lbl">' + esc(t('alr_criteria_disc'))   + '</div><input class="sh-alertas__field-input" type="text" placeholder="Branding, Web, Editorial..." disabled></div>' +
        '<div class="sh-alertas__field"><div class="sh-alertas__field-lbl">' + esc(t('alr_criteria_terr'))   + '</div><input class="sh-alertas__field-input" type="text" placeholder="Catalunya, Madrid..." disabled></div>' +
        '<div class="sh-alertas__field"><div class="sh-alertas__field-lbl">' + esc(t('alr_criteria_kw'))     + '</div><input class="sh-alertas__field-input" type="text" placeholder="identidad, campana..." disabled></div>' +
        '<div class="sh-alertas__field"><div class="sh-alertas__field-lbl">' + esc(t('alr_criteria_health')) + '</div><input class="sh-alertas__field-input" type="text" placeholder="Buenas senales..." disabled></div>' +
      '</div>' +
      '<div class="sh-alertas__cta-wrap">' +
        '<div class="sh-alertas__soon-icon"><i class="bi bi-bell-slash"></i></div>' +
        '<div class="sh-alertas__soon-title">' + esc(t('alr_coming_soon_t')) + '</div>' +
        '<div class="sh-alertas__soon-desc">'  + esc(t('alr_coming_soon_d')) + '</div>' +
        '<button class="sh-alertas__notify-btn" id="sh-alr-cta-btn"><i class="bi bi-bell"></i> ' + esc(t('alr_notify_btn')) + '</button>' +
      '</div>' +
    '</div>';

  containerEl.querySelectorAll('[data-alr-profile]').forEach(function(btn){
    btn.addEventListener('click', function(){ _showAlertasModal(); });
  });
  var ctaBtn = containerEl.querySelector('#sh-alr-cta-btn');
  if (ctaBtn) ctaBtn.addEventListener('click', function(){ _showAlertasModal(); });
}

function _showAlertasModal() {
  var ex = document.querySelector('.sh-alertas-modal-overlay');
  if (ex) ex.remove();

  var overlay = document.createElement('div');
  overlay.className = 'sh-alertas-modal-overlay';
  overlay.innerHTML =
    '<div class="sh-alertas-modal" role="dialog" aria-modal="true">' +
      '<div class="sh-alertas-modal__icon"><i class="bi bi-hourglass-split"></i></div>' +
      '<div class="sh-alertas-modal__title">' + esc(t('alr_coming_soon_t')) + '</div>' +
      '<div class="sh-alertas-modal__desc">'  + esc(t('alr_coming_soon_d')) + '</div>' +
      '<button class="sh-alertas-modal__close">' + esc(t('fp_close')) + '</button>' +
    '</div>';

  document.body.appendChild(overlay);
  var closeModal = function(){ overlay.remove(); };
  overlay.querySelector('.sh-alertas-modal__close').addEventListener('click', closeModal);
  overlay.addEventListener('click', function(e){ if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', function escH(e){
    if (e.key === 'Escape'){ closeModal(); document.removeEventListener('keydown', escH); }
  });
}

// -- EXPORTS ------------------------------------------------------------------

window.ADG_Shared = {
  computeTrafficLight : computeTrafficLight,
  TrafficLight        : TrafficLight,
  computeAdvisory     : computeAdvisory,
  advisoryHTML        : advisoryHTML,
  computeMiniResumen  : computeMiniResumen,
  fichaHTML           : fichaHTML,
  FichaPanel          : FichaPanel,
  FichaClose          : FichaClose,
  ToggleSwitch        : ToggleSwitch,
  AlertasStub         : AlertasStub
};

})();