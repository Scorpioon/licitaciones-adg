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
    discColor = _utils.discColor, discTag = _utils.discTag,
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
      '<div class="sh-assess__rating">' +
        '<span class="sh-assess__dot"></span>' +
        '<span class="sh-assess__label">' + esc(tl.label) + '</span>' +
      '</div>' +
      (signals.length ? '<div class="sh-assess__signals">' + signals.join('') + '</div>' : '') +
    '</div>'
  );
}

function isValidDocUrl(url) {
  if (typeof url !== 'string') return false;
  var u = url.trim();
  return u.length > 0 && u !== '#';
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

  var discHTML = (r.disciplines || []).length
    ? (r.disciplines || []).map(function(d){ return discTag(d,'9px'); }).join('')
    : '<span class="sh-ficha__empty">&mdash;</span>';

  var kwChips = (r.kw || []).map(function(k){ return '<span class="sh-ficha__chip"><i class="bi bi-tag"></i>' + esc(k) + '</span>'; });
  if (r.cpv) cpvArray(r.cpv).slice(0, 3).forEach(function(c){ kwChips.push('<span class="sh-ficha__chip"><i class="bi bi-upc"></i>' + esc(c) + '</span>'); });
  kwChips.push('<span class="sh-ficha__chip sh-ficha__chip--src"><i class="bi bi-database"></i>' + esc(r.font || 'PLACSP') + '</span>');
  var kwHTML = kwChips.join('');

  var docs = r.documents || [];
  var docsHTML;
  if (!docs.length) {
    docsHTML =
      '<div class="sh-ficha__doc-empty">' +
        '<span class="sh-ficha__empty">' + esc(t('fp_no_docs')) + '</span>' +
        '<span class="sh-ficha__f2-hint">' + esc(t('fp_f2_ready')) + '</span>' +
      '</div>';
  } else {
    var hasMeaningfulTitle = docs.some(function(d){ return d.title && d.title.trim().length > 0; });
    if (hasMeaningfulTitle) {
      var validDocs = docs.filter(function(d){ return isValidDocUrl(d.url); });
      if (validDocs.length) {
        docsHTML = validDocs.map(function(d){
          var docLabel = (d.title && d.title.trim())
            ? d.title.trim()
            : (d.notice_type
                ? (d.published_at && d.published_at.trim()
                    ? d.notice_type + ' · ' + d.published_at.trim()
                    : d.notice_type)
                : 'Documento disponible');
          return '<a class="sh-ficha__doc" href="' + esc(d.url) + '" target="_blank" rel="noopener">' +
            '<i class="bi bi-file-earmark-text"></i>' +
            '<span>' + esc(docLabel) + '</span>' +
            (d.date ? '<span class="sh-ficha__hist-date">' + esc(d.date) + '</span>' : '') +
          '</a>';
        }).join('');
      } else {
        var fbHref = (r.url && r.url.indexOf('http') === 0) ? r.url : null;
        docsHTML = fbHref
          ? '<a class="sh-ficha__doc" href="' + esc(fbHref) + '" target="_blank" rel="noopener">' +
              '<i class="bi bi-files"></i>' +
              '<span>' + docs.length + ' ' + esc(t('fp_docs_available')) + '</span>' +
            '</a>'
          : '<span class="sh-ficha__empty">' + esc(t('fp_docs_available')) + '</span>';
      }
    } else {
      var summaryHref = (r.url && r.url.indexOf('http') === 0) ? r.url : '#';
      docsHTML =
        '<a class="sh-ficha__doc" href="' + esc(summaryHref) + '" target="_blank" rel="noopener">' +
          '<i class="bi bi-files"></i>' +
          '<span>' + docs.length + ' ' + esc(t('fp_docs_available')) + '</span>' +
        '</a>';
    }
  }

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
    '<div class="sh-ficha__head">' +
      '<span class="sh-ficha__eyebrow">' + esc(t('fp_eyebrow')) + '</span>' +
      '<button class="sh-ficha__close" aria-label="' + esc(t('fp_close')) + '"><i class="bi bi-x"></i></button>' +
    '</div>' +
    '<div class="sh-ficha__body">' +
      '<div class="sh-ficha__title">' + esc(r.titol || '—') + (isNew(r) ? ' <span class="badge-new">' + esc(t('nueva')) + '</span>' : '') + '</div>' +
      factsHTML +
      assessmentBlock(r) +
      '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_disciplines')) + '</div><div class="sh-ficha__chips">' + discHTML + '</div></div>' +
      '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_keywords'))    + '</div><div class="sh-ficha__chips">' + kwHTML   + '</div></div>' +
      '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_documents'))   + '</div><div class="sh-ficha__docs">'  + docsHTML + '</div></div>' +
      '<div class="sh-ficha__section"><div class="sh-ficha__lbl">' + esc(t('fp_history'))     + '</div>' + histHTML + '</div>' +
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
  fichaHTML           : fichaHTML,
  FichaPanel          : FichaPanel,
  FichaClose          : FichaClose,
  ToggleSwitch        : ToggleSwitch,
  AlertasStub         : AlertasStub
};

})();