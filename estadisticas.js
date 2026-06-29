/*
 * ADG Plataforma Digital -- estadisticas.js
 * 0.4.3c -- Mar 2026
 * Role: Statistics dashboard -- local filter state, bignums, donut SVG,
 *       trend bars, bar cards, top5, adjudicatarios, market conditions.
 *       Will absorb barometro.js in Phase 3.
 * Page: estadisticas.html
 * Depends on: app.js (ADG_Utils, ADG, DISC, TERR), shared.js (ADG_Shared)
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * 0.4.3c Mar 2026  Quarter filter; renderBaro uses getRows(); sidebar in .main.
 * b4.0  Mar 2026  Header updated. Barometro toggle pending (Phase 3).
 * v2.1  Mar 2026  IIFE wrap -- fix 'el' already declared.
 * v2.0  Mar 2026  Independent page. Local filters decoupled from table.
 * v1.x  Ene-Feb   Panel overlay inside index.html
 */;(function() {
"use strict";

const { el, t, fmt, fmtFull, daysTo, isNew, discColor, discTag,
        getDisplayStatus, isOpenOpportunity, discNoneTag,
        applyI18n, updateStrip, updateTicker, initShared, loadData } = ADG_Utils;

// ── LOCAL FILTER STATE (independent from main table) ─────────────────────
const SV = {
  year:  '',
  ccaa:  '',
  estat: '',
  discs: new Set(),
  view:  'stats',
  cuatri: '',
};

// ── TRUE CUATRIMESTRE MODEL (p208) ───────────────────────────────────────────
// A cuatrimestre is a third of the calendar year (4 months), NOT a quarter:
//   month 0-3  (Ene-Abr) => C1
//   month 4-7  (May-Ago) => C2
//   month 8-11 (Sep-Dic) => C3
// Returns 1|2|3, or 0 when the date is missing/unparseable.
function getCuatri(dateStr) {
  var m = parseInt((dateStr || '0000-00').slice(5, 7), 10);
  if (!m || m < 1 || m > 12) return 0;
  return Math.floor((m - 1) / 4) + 1;
}
function cuatriLabel(c) { return ({1:'C1 · Ene-Abr', 2:'C2 · May-Ago', 3:'C3 · Sep-Dic'})[c] || ''; }
function cuatriShort(c) { return ({1:'C1', 2:'C2', 3:'C3'})[c] || ''; }
function periodKey(r) { var c = getCuatri(r.data_pub); return c ? (r.data_pub||'').slice(0,4) + '-C' + c : ''; }
function periodTitle(year, c) { return year + ' · ' + cuatriLabel(c); }

// p207: getRows accepts an explicit source so Estadísticas can run on
// canonical/deduped records. p208: the period filter is now a true
// cuatrimestre (C1/C2/C3), not a calendar quarter.
function getRows(source) {
  let rows = source || ADG.data;
  if (SV.year)  rows = rows.filter(r => (r.data_pub||'').startsWith(SV.year));
  if (SV.ccaa)  rows = rows.filter(r => r.ccaa === SV.ccaa);
  if (SV.estat) rows = rows.filter(r => r.estat === SV.estat);
  if (SV.discs.size) rows = rows.filter(r => (r.disciplines||[]).some(d => SV.discs.has(d)));
  if (SV.cuatri) { var cm = parseInt(SV.cuatri, 10); rows = rows.filter(function(r){ return getCuatri(r.data_pub) === cm; }); }
  return rows;
}

// ── SYNC FILTER PILLS ─────────────────────────────────────────────────────
function syncEstat() {
  document.querySelectorAll('[data-sv-estat]').forEach(p => {
    const match = (p.dataset.svEstat ?? '') === SV.estat;
    p.classList.toggle('active', match);
    p.setAttribute('aria-pressed', match);
  });
}

function syncDiscs() {
  const none = SV.discs.size === 0;
  const allBtn = el('sv-all-disc');
  if (allBtn) { allBtn.classList.toggle('active', none); }
  const countEl = el('sv-disc-count');
  if (countEl) countEl.textContent = none ? '' : String(SV.discs.size);
  document.querySelectorAll('[data-sv-disc]').forEach(p => {
    const d = p.dataset.svDisc;
    const active = SV.discs.has(d);
    p.classList.toggle('active', active);
    if (active) {
      const c = discColor(d);
      p.style.background = c.bg; p.style.color = c.text; p.style.borderColor = c.text;
    } else {
      p.style.background = ''; p.style.color = ''; p.style.borderColor = '';
    }
  });
}

// ── HELPERS ───────────────────────────────────────────────────────────────
function syncCuatri() {
  document.querySelectorAll('[data-sv-cuatri]').forEach(function(p) {
    var match = (p.dataset.svCuatri === SV.cuatri);
    p.classList.toggle('active', match);
    p.setAttribute('aria-pressed', String(match));
  });
}

function pct(a, b) { return b ? Math.round(a/b*100) : 0; }
function avg(arr) { return arr.length ? arr.reduce((s,v)=>s+v,0)/arr.length : 0; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── ESTADÍSTICAS v2 VISUAL PRIMITIVES (p211B) ────────────────────────────────
// Restrained, dependency-free building blocks for the v2 data modules. All pure
// and defensive (null/NaN safe). Monochrome base; discipline color is used only
// as a taxonomy identity mark via discColor(). No chart library, no claims.
function fmtNum(n) { return (Number(n) || 0).toLocaleString('es-ES'); }
function formatPercent(a, b) { return pct(a, b) + '%'; }

// Budget bucket label for a single amount (honest fixed ranges, no scoring).
function budgetBucket(p) {
  if (!(p > 0)) return 'Sin presupuesto';
  if (p < 10000)  return '< 10K';
  if (p < 50000)  return '10K–50K';
  if (p < 100000) return '50K–100K';
  if (p < 500000) return '100K–500K';
  return '> 500K';
}

// Coverage ratio over the filtered set: { n, pct } (defensive).
function coverageRatio(rows, predFn) {
  var n = 0; for (var i = 0; i < rows.length; i++) { if (predFn(rows[i])) n++; }
  return { n: n, pct: pct(n, rows.length) };
}

// Small DOM-string fact row (label · value).
function factRow(lbl, val) {
  return '<div class="sv2-fact"><span class="sv2-fact-lbl">' + esc(lbl) + '</span><span class="sv2-fact-val">' + val + '</span></div>';
}
function emptyInline() { return '<div class="sv2-empty-inline">' + esc(t('sv_no_data')) + '</div>'; }

// Module shell: head (title + optional sub + optional tag) + body + optional note.
function sv2Module(title, sub, bodyHTML, opts) {
  opts = opts || {};
  var head = '<div class="sv2-module-head"><div class="sv2-module-titles">'
    + '<div class="sv2-module-title">' + esc(title) + '</div>'
    + (sub ? '<div class="sv2-module-sub">' + esc(sub) + '</div>' : '')
    + '</div>' + (opts.tag ? '<span class="sv2-module-tag">' + esc(opts.tag) + '</span>' : '') + '</div>';
  return '<section class="sv2-module' + (opts.cls ? ' ' + opts.cls : '') + '">'
    + head + (bodyHTML || '') + (opts.note ? '<div class="sv2-note">' + opts.note + '</div>' : '') + '</section>';
}

// Horizontal bar row: optional taxonomy mark, label, track (vs max), value and
// optional share-of-total percentage.
function sv2BarRow(label, val, max, total, color, markColor) {
  var share = total ? pct(val, total) : -1;
  return '<div class="sv2-bar">'
    + (markColor ? '<span class="sv2-bar-mark" style="background:' + markColor + '"></span>' : '')
    + '<div class="sv2-bar-label" title="' + esc(label) + '">' + esc(label) + '</div>'
    + '<div class="sv2-bar-track"><div class="sv2-bar-fill" style="width:' + pct(val, max) + '%'
      + (color ? ';background:' + color : '') + '"></div></div>'
    + '<div class="sv2-bar-val">' + fmtNum(val) + (share >= 0 ? '<span class="sv2-bar-pct">' + share + '%</span>' : '') + '</div>'
    + '</div>';
}

// Coverage ratio row: label, count·percent, thin progress track.
function sv2RatioRow(label, n, total) {
  var p = pct(n, total);
  return '<div class="sv2-ratio">'
    + '<div class="sv2-ratio-head"><span class="sv2-ratio-lbl">' + esc(label) + '</span>'
    + '<span class="sv2-ratio-val">' + fmtNum(n) + '<span class="sv2-bar-pct">' + p + '%</span></span></div>'
    + '<div class="sv2-ratio-track"><div class="sv2-ratio-fill" style="width:' + p + '%"></div></div>'
    + '</div>';
}

// Segmented single-bar + legend (lifecycle/status). segs: [{label,val,color}].
function sv2Segments(segs, total) {
  var active = segs.filter(function(s){ return s.val > 0; });
  var bar = active.map(function(s){
    return '<div class="sv2-seg-fill" style="width:' + pct(s.val, total) + '%;background:' + s.color + '" title="' + esc(s.label) + '"></div>';
  }).join('');
  var legend = active.map(function(s){
    return '<div class="sv2-seg-item"><span class="sv2-seg-dot" style="background:' + s.color + '"></span>'
      + '<span class="sv2-seg-lbl">' + esc(s.label) + '</span>'
      + '<span class="sv2-seg-val">' + fmtNum(s.val) + '<span class="sv2-bar-pct">' + pct(s.val, total) + '%</span></span></div>';
  }).join('');
  return '<div class="sv2-seg">' + (bar || '<div class="sv2-seg-fill" style="width:100%;background:var(--border2)"></div>') + '</div>'
    + '<div class="sv2-seg-legend">' + legend + '</div>';
}

// Ranked compact list. items: [{ main, sub?, val }] (val is pre-formatted HTML/text).
function sv2List(items) {
  if (!items.length) return emptyInline();
  return '<ol class="sv2-list">' + items.map(function(it, i){
    return '<li class="sv2-list-item"><span class="sv2-list-rank">' + (i + 1) + '</span>'
      + '<div class="sv2-list-main"><div class="sv2-list-name" title="' + esc(it.main) + '">' + esc(it.main) + '</div>'
      + (it.sub ? '<div class="sv2-list-sub" title="' + esc(it.sub) + '">' + esc(it.sub) + '</div>' : '') + '</div>'
      + '<div class="sv2-list-val">' + it.val + '</div></li>';
  }).join('') + '</ol>';
}

// ── MODULE REGISTRY FOUNDATION (p210) ────────────────────────────────────────
// Lightweight composition scaffold — NOT a framework. p210 only declares the
// module order per view and exposes reusable render primitives; p207 render()
// and p208 renderBaro() still produce the section bodies inline (strangler
// pattern). p211/p212 will migrate each id below into a composable module fn.
const ANALYTICS_MODULES = {
  stats: ['overview', 'cobertura', 'ciclo-vida', 'presupuesto', 'plazos', 'documentos'],
  baro:  ['periodo', 'actividad', 'evolucion', 'distribucion', 'presupuesto', 'lectura'],
};

// Reusable analytics primitives (shared shell vocabulary for p211/p212 modules).
function modGrid(cardsHTML) { return '<div class="analytics-module-grid">' + cardsHTML + '</div>'; }
function modCard(title, bodyHTML, note) {
  return '<div class="analytics-card">'
    + (title ? '<div class="analytics-card-title">' + esc(title) + '</div>' : '')
    + (bodyHTML || '')
    + (note ? '<div class="analytics-card-note">' + note + '</div>' : '')
    + '</div>';
}
function metricCard(val, label, sub) {
  return '<div class="analytics-metric"><div class="analytics-metric-val">' + val + '</div>'
    + '<div class="analytics-metric-lbl">' + esc(label) + '</div>'
    + (sub ? '<div class="analytics-metric-sub">' + esc(sub) + '</div>' : '') + '</div>';
}
function emptyState(msg) { return '<div class="analytics-empty">' + esc(msg || t('sv_no_data')) + '</div>'; }
function caveatChip(text) { return '<div class="analytics-caveat">' + text + '</div>'; }

// ── SHARED CONTENT HEADER + CONTEXTUAL TIME SEMANTICS (p210) ──────────────────
// The time control means different things per view (the p209 usability trap):
// Estadísticas filters the dataset; Barómetro selects the period it reads.
const VIEW_META = {
  stats: { title:'Estructura del dataset',  railSub:'Estructura del dataset', timeLbl:'Filtro temporal',  timeHint:'Acota el dataset por fecha de publicación.' },
  baro:  { title:'Lectura del cuatrimestre', railSub:'Lectura del periodo',   timeLbl:'Periodo analizado', timeHint:'Selecciona el cuatrimestre de lectura.' },
};

function dataFreshnessLabel() {
  if (ADG.isSample) return 'Datos de muestra';
  if (ADG.dataRefreshedAt) {
    var d = new Date(ADG.dataRefreshedAt);
    if (!isNaN(d.getTime())) return 'Actualizado ' + d.toLocaleDateString('es-ES', { day:'2-digit', month:'short', year:'numeric' });
  }
  return '';
}

function renderHeader() {
  var m = VIEW_META[SV.view] || VIEW_META.stats;
  var titleEl = el('analytics-title'); if (titleEl) titleEl.textContent = m.title;
  var metaEl = el('analytics-meta');
  if (metaEl) {
    var canon = (ADG.canonicalData && ADG.canonicalData.length) ? ADG.canonicalData.length : (ADG.data ? ADG.data.length : 0);
    var raw = ADG.data ? ADG.data.length : 0;
    var parts = [];
    if (canon) parts.push('<strong>' + canon.toLocaleString('es-ES') + '</strong> registros canónicos');
    if (raw)   parts.push('de <strong>' + raw.toLocaleString('es-ES') + '</strong> filas de origen');
    var fresh = dataFreshnessLabel();
    if (fresh) parts.push(fresh);
    metaEl.innerHTML = parts.join(' · ');
  }
}

function syncTimeSemantics() {
  var m = VIEW_META[SV.view] || VIEW_META.stats;
  var lbl = el('sv-time-lbl');  if (lbl)  lbl.textContent = m.timeLbl;
  var hint = el('sv-time-hint'); if (hint) hint.textContent = m.timeHint;
  var sub = el('sv-mode-sub');  if (sub)  sub.textContent = m.railSub;
}

// ── RAIL DATASET STATUS MINI-PANEL (p211) ─────────────────────────────────────
// Compact, always-visible rail panel: canonical records, source rows, and the
// data state (loading / sample / real + freshness). Reads ADG totals defensively
// so it never blocks rendering if data is still streaming in (p200 loader).
function renderRailStatus() {
  var canon = (ADG.canonicalData && ADG.canonicalData.length) ? ADG.canonicalData.length : (ADG.data ? ADG.data.length : 0);
  var raw   = ADG.data ? ADG.data.length : 0;
  var cEl = el('sv-stat-canon'); if (cEl) cEl.textContent = canon ? canon.toLocaleString('es-ES') : '—';
  var rEl = el('sv-stat-raw');   if (rEl) rEl.textContent = raw   ? raw.toLocaleString('es-ES')   : '—';
  var fEl = el('sv-stat-fresh');
  var dot = el('sv-stat-dot');
  var state; // 'load' | 'sample' | 'ok'
  if (!canon && !raw) state = 'load';
  else if (ADG.isSample) state = 'sample';
  else state = 'ok';
  if (fEl) {
    if (state === 'load') fEl.textContent = 'Cargando datos…';
    else if (state === 'sample') fEl.textContent = 'Datos de muestra';
    else fEl.textContent = dataFreshnessLabel() || 'Datos reales';
  }
  if (dot) {
    dot.classList.remove('arail-dot--ok', 'arail-dot--sample', 'arail-dot--load');
    dot.classList.add('arail-dot--' + state);
  }
}

// Paint each discipline pill's taxonomy color mark from discColor() (theme-aware,
// so it must be re-run on theme change). The "Todas" pill has no mark.
function paintDiscMarks() {
  document.querySelectorAll('[data-sv-disc]').forEach(function(p) {
    var mark = p.querySelector('.arail-cmark');
    if (mark) mark.style.background = discColor(p.dataset.svDisc).text;
  });
}

// ── ACTIVE FILTER RIBBON (p210) ───────────────────────────────────────────────
// Compact chips of the active context (no prose summary). Mirrors getRows() so
// the filtered/canonical counts always match what Estadísticas renders.
function ribbonChip(k, v) {
  return '<span class="analytics-chip"><span class="analytics-chip-k">' + esc(k) + '</span>'
    + '<span class="analytics-chip-v">' + esc(v) + '</span></span>';
}
function renderRibbon() {
  var wrap = el('sv-ribbon'); if (!wrap) return;
  var chips = [ ribbonChip('Vista', SV.view === 'baro' ? 'Barómetro' : 'Estadísticas') ];
  if (SV.year)   chips.push(ribbonChip('Año', SV.year));
  if (SV.cuatri) chips.push(ribbonChip('Periodo', cuatriShort(parseInt(SV.cuatri, 10))));
  if (SV.ccaa)   chips.push(ribbonChip('Territorio', (TERR[SV.ccaa] && TERR[SV.ccaa].name) || SV.ccaa));
  if (SV.estat)  chips.push(ribbonChip('Estado', SV.estat));
  if (SV.discs.size) [...SV.discs].forEach(function(d){ chips.push(ribbonChip('Disciplina', (DISC[d] && DISC[d].label) || d)); });

  var hasFilters = !!(SV.year || SV.cuatri || SV.ccaa || SV.estat || SV.discs.size);
  var canon = (ADG.canonicalData && ADG.canonicalData.length) ? ADG.canonicalData : (ADG.data || []);
  var html = chips.join('');
  if (!hasFilters) html += '<span class="analytics-chip analytics-chip--muted">Todo el dataset</span>';
  if (SV.view === 'stats') {
    var filtered = getRows(canon).length;
    html += '<span class="analytics-chip analytics-chip--count"><strong>' + filtered.toLocaleString('es-ES') + '</strong> / ' + canon.length.toLocaleString('es-ES') + '</span>';
  } else {
    html += '<span class="analytics-chip analytics-chip--count"><strong>' + canon.length.toLocaleString('es-ES') + '</strong> canónicos</span>';
  }
  if (hasFilters) html += '<button class="analytics-chip analytics-chip--reset" id="sv-ribbon-reset" type="button"><i class="bi bi-x-circle"></i>Restablecer</button>';
  wrap.innerHTML = html;
  var rb = el('sv-ribbon-reset'); if (rb) rb.addEventListener('click', resetFilters);
}

// ── RESET FILTERS (p210) ──────────────────────────────────────────────────────
// Clears every SV filter, resyncs visible controls, and refreshes the view.
// Does not touch SV.view, reload the page, or use localStorage.
function resetFilters() {
  SV.year = ''; SV.cuatri = ''; SV.ccaa = ''; SV.estat = ''; SV.discs.clear();
  var ys = el('sv-year'); if (ys) ys.value = '';
  var cs = el('sv-ccaa'); if (cs) cs.value = '';
  syncCuatri(); syncEstat(); syncDiscs();
  refreshActiveView();
}

// ── RENDER · ESTADÍSTICAS v2 (p211B) ─────────────────────────────────────────
// Visual data modules answering "¿qué hay dentro del dataset?" (Barómetro/p208
// answers "¿qué está pasando en el periodo?"). Every figure runs on canonical/
// deduped records via getRows(); raw ADG.data is only ever a labelled source
// count. p207 honesty rules preserved: no market claims, no invented intelligence,
// canonical data only. Composition follows ANALYTICS_MODULES.stats.
function render() {
  // Canonical/deduped source — never raw duplicated ADG.data rows.
  const canonSource = (ADG.canonicalData && ADG.canonicalData.length) ? ADG.canonicalData : ADG.data;
  const rows = getRows(canonSource);
  const total = rows.length;
  const canonGlobal = canonSource.length;
  const rawRows = ADG.data ? ADG.data.length : 0;
  const hasFilters = !!(SV.year || SV.cuatri || SV.ccaa || SV.estat || SV.discs.size);

  const body = el('sv-body');
  if (!body) return;

  // ── H · Empty / low-data state ───────────────────────────────────────────
  if (!total) {
    body.innerHTML = renderEmptyState(hasFilters);
    const rb = el('sv2-empty-reset'); if (rb) rb.addEventListener('click', resetFilters);
    return;
  }

  // ── Data-state label (Datos reales / Muestra) ────────────────────────────
  const state = ADG.isSample
    ? { lbl: 'Datos de muestra', cls: 'sample' }
    : { lbl: dataFreshnessLabel() || 'Datos reales', cls: 'ok' };

  // ── Lifecycle / status ───────────────────────────────────────────────────
  // "Sin adjudicar" = active_opportunity_eligible (lifecycle: not yet awarded),
  // NOT "open for bids now". Estado is the declared expediente status.
  const sinAdjudicar = rows.filter(r => r.active_opportunity_eligible === true).length;
  const vigentes     = rows.filter(r => r.estat === 'Vigente').length;
  const adjudicadas  = rows.filter(r => r.estat === 'Adjudicado').length;
  const desiertas    = rows.filter(r => r.estat === 'Desierta').length;
  const otrosEstat   = total - vigentes - adjudicadas - desiertas;

  // ── Budget (distribution, not just total) ────────────────────────────────
  const conPpto    = rows.filter(r => r.pressupost > 0);
  const sinPpto    = total - conPpto.length;
  const pptoSorted = conPpto.map(r => r.pressupost).sort((a,b)=>a-b);
  const medianPpto = pptoSorted.length ? pptoSorted[Math.floor(pptoSorted.length/2)] : 0;
  const minPpto    = pptoSorted.length ? pptoSorted[0] : 0;
  const maxPpto    = pptoSorted.length ? pptoSorted[pptoSorted.length-1] : 0;
  const sumPpto    = conPpto.reduce((s,r)=>s+r.pressupost,0);
  const bucketOrder = ['< 10K','10K–50K','50K–100K','100K–500K','> 500K'];
  const buckets = {}; bucketOrder.forEach(k => buckets[k] = 0);
  conPpto.forEach(r => { buckets[budgetBucket(r.pressupost)]++; });
  const bucketMax = Math.max.apply(null, bucketOrder.map(k => buckets[k]).concat([1]));

  // ── Disciplines (incl. neutral "sin disciplina" bucket) ──────────────────
  const byDisc = {}; let sinDisc = 0;
  rows.forEach(r => {
    const ds = r.disciplines || [];
    if (!ds.length) sinDisc++;
    ds.forEach(d => { byDisc[d] = (byDisc[d]||0)+1; });
  });
  const discArr = Object.entries(byDisc).sort((a,b)=>b[1]-a[1]);

  // ── Territory ────────────────────────────────────────────────────────────
  const byCCAA = {};
  rows.forEach(r => { if (r.ccaa) byCCAA[r.ccaa] = (byCCAA[r.ccaa]||0)+1; });
  const ccaaArr = Object.entries(byCCAA).sort((a,b)=>b[1]-a[1]);
  const esCount = byCCAA['ES'] || 0;

  // ── Documents (link-level coverage only, NOT content extraction) ─────────
  const withDocs  = rows.filter(r => (r.documents||[]).length > 0);
  const totalDocs = withDocs.reduce((s,r)=>s+(r.documents||[]).length, 0);

  // ── Coverage / completeness (field presence ratios) ──────────────────────
  const withDisc = total - sinDisc;
  const withTerr = coverageRatio(rows, r => !!r.ccaa).n;
  const withDate = coverageRatio(rows, r => !!r.data_pub).n;
  const withOrg  = coverageRatio(rows, r => !!r.organisme).n;

  // ── Tops (descriptive facts about the dataset) ───────────────────────────
  const topBudget = conPpto.slice().sort((a,b)=>b.pressupost-a.pressupost).slice(0,5);
  const byOrg = {};
  rows.forEach(r => { if (r.organisme) byOrg[r.organisme] = (byOrg[r.organisme]||0)+1; });
  const orgArr = Object.entries(byOrg).sort((a,b)=>b[1]-a[1]).slice(0,6);

  // ── Assemble v2 modules (ANALYTICS_MODULES.stats composition) ────────────
  body.innerHTML = '<div class="sv2-stack">'
    + renderStatHero({ total, canonGlobal, rawRows, hasFilters, state,
        sinAdjudicar, conPpto: conPpto.length, sumPpto, discCount: discArr.length })
    + renderDisciplineModule(discArr, sinDisc, total)
    + '<div class="sv2-grid sv2-grid--2">'
      + renderStatusModule({ vigentes, adjudicadas, desiertas, otrosEstat, sinAdjudicar }, total)
      + renderBudgetModule({ conPpto: conPpto.length, sinPpto, sumPpto, medianPpto, minPpto, maxPpto, buckets, bucketOrder, bucketMax })
    + '</div>'
    + '<div class="sv2-grid sv2-grid--2">'
      + renderCoverageModule({ conPpto: conPpto.length, withDisc, withTerr, withDate, withOrg }, total)
      + renderDocumentsModule(withDocs.length, totalDocs, total)
    + '</div>'
    + '<div class="sv2-grid sv2-grid--3">'
      + renderTopOrgsModule(orgArr)
      + renderTopBudgetModule(topBudget)
      + renderTopTerrModule(ccaaArr, esCount, total)
    + '</div>'
    + '<div class="sv2-note sv2-note--foot">'
      + '<strong>Cobertura.</strong> Expedientes de contratación pública (PLACSP · contrataciondelestado.es) con relevancia para diseño y comunicación visual. Cifras sobre <strong>registros canónicos</strong> (deduplicados), no sobre filas de origen; no representan el tamaño total del mercado.'
    + '</div>'
    + '</div>';
}

// ── A · HERO / DATASET SNAPSHOT ──────────────────────────────────────────────
function renderStatHero(d) {
  const lead = '<div class="sv2-hero-lead">'
    + '<div class="sv2-hero-state sv2-state--' + d.state.cls + '"><span class="sv2-state-dot"></span>' + esc(d.state.lbl) + '</div>'
    + '<div class="sv2-hero-num">' + fmtNum(d.total) + '</div>'
    + '<div class="sv2-hero-lbl">registros canónicos'
      + (d.hasFilters ? ' <span class="sv2-hero-of">filtrados de ' + fmtNum(d.canonGlobal) + '</span>' : '')
    + '</div>'
    + '<div class="sv2-hero-meta">Derivados de ' + fmtNum(d.rawRows) + ' filas de origen · Fuente PLACSP</div>'
    + '</div>';
  const metric = (val, lbl, sub) => '<div class="sv2-hero-metric"><div class="sv2-hero-metric-val">' + val + '</div>'
    + '<div class="sv2-hero-metric-lbl">' + esc(lbl) + '</div>'
    + (sub ? '<div class="sv2-hero-metric-sub">' + esc(sub) + '</div>' : '') + '</div>';
  const metrics = '<div class="sv2-hero-metrics">'
    + metric('<span style="color:var(--s-ok)">' + fmtNum(d.sinAdjudicar) + '</span>', 'Sin adjudicar', 'ciclo de vida')
    + metric(fmtNum(d.conPpto), 'Con presupuesto', formatPercent(d.conPpto, d.total) + ' del total')
    + metric(fmt(d.sumPpto), 'Suma informada', 'presupuesto base')
    + metric(fmtNum(d.discCount), 'Disciplinas', 'en la selección')
    + '</div>';
  return '<section class="sv2-hero">' + lead + metrics + '</section>';
}

// ── B · DISCIPLINE DISTRIBUTION (featured, central module) ────────────────────
function renderDisciplineModule(discArr, sinDisc, total) {
  const entries = discArr.concat(sinDisc ? [['__none__', sinDisc]] : []);
  let bodyHTML;
  if (!entries.length) {
    bodyHTML = emptyInline();
  } else {
    const max = Math.max.apply(null, entries.map(e => e[1]).concat([1]));
    bodyHTML = '<div class="sv2-bars sv2-bars--2col">' + entries.slice(0, 14).map(function(e){
      const key = e[0], val = e[1];
      const label = key === '__none__' ? (t('disc_none') || 'Sin disciplina') : (DISC[key] && DISC[key].label || key);
      const mark  = key === '__none__' ? 'var(--border)' : discColor(key).text;
      // Monochrome fill + taxonomy color mark; share is % of filtered records.
      return sv2BarRow(label, val, max, total, null, mark);
    }).join('') + '</div>';
  }
  const note = sinDisc
    ? '«Sin disciplina» (' + fmtNum(sinDisc) + ') es un grupo de calidad de datos: expedientes aún sin clasificar. Un registro puede tener varias disciplinas, por lo que los porcentajes pueden sumar más de 100%.'
    : 'Un registro puede tener varias disciplinas, por lo que los porcentajes pueden sumar más de 100%.';
  return sv2Module('Distribución por disciplina', 'Reparto de la selección · % sobre registros filtrados', bodyHTML,
    { cls: 'sv2-module--feature', tag: 'Composición', note: note });
}

// ── C · LIFECYCLE / STATUS ───────────────────────────────────────────────────
function renderStatusModule(s, total) {
  const segs = [
    { label: 'Vigente',    val: s.vigentes,    color: 'var(--s-ok)'  },
    { label: 'Adjudicado', val: s.adjudicadas, color: 'var(--s-adj)' },
    { label: 'Desierta',   val: s.desiertas,   color: 'var(--s-des)' },
  ];
  if (s.otrosEstat > 0) segs.push({ label: 'Otros / sin estado', val: s.otrosEstat, color: 'var(--text3)' });
  return sv2Module('Estado del expediente', 'Distribución por estado declarado', sv2Segments(segs, total), {
    note: '«Sin adjudicar» (' + fmtNum(s.sinAdjudicar) + ') es una clasificación de ciclo de vida y no equivale al estado «Vigente»: el plazo de presentación puede estar vencido.'
  });
}

// ── D · BUDGET SHAPE ─────────────────────────────────────────────────────────
function renderBudgetModule(b) {
  const facts = '<div class="sv2-facts">'
    + factRow('Con presupuesto', fmtNum(b.conPpto))
    + factRow('Sin informar', fmtNum(b.sinPpto))
    + factRow('Mediana', fmt(b.medianPpto))
    + factRow('Rango', fmt(b.minPpto) + ' – ' + fmt(b.maxPpto))
    + factRow('Suma informada', fmt(b.sumPpto))
    + '</div>';
  const bucketBars = b.conPpto
    ? '<div class="sv2-buckets">' + b.bucketOrder.map(function(k){
        return sv2BarRow(k, b.buckets[k], b.bucketMax, b.conPpto, 'var(--text)', null);
      }).join('') + '</div>'
    : emptyInline();
  const bodyHTML = '<div class="sv2-split-cols">'
    + '<div>' + facts + '</div>'
    + '<div><div class="sv2-sub-lbl">Distribución por rango</div>' + bucketBars + '</div>'
    + '</div>';
  return sv2Module('Presupuesto informado', 'Sobre ' + fmtNum(b.conPpto) + ' registros con presupuesto base', bodyHTML, {
    note: 'El presupuesto base de licitación es orientativo; no equivale al valor de mercado y excluye ' + fmtNum(b.sinPpto) + ' registros sin presupuesto.'
  });
}

// ── E · DATA QUALITY / COVERAGE ──────────────────────────────────────────────
function renderCoverageModule(c, total) {
  const bodyHTML = '<div class="sv2-ratios">'
    + sv2RatioRow('Con presupuesto', c.conPpto, total)
    + sv2RatioRow('Con disciplina asignada', c.withDisc, total)
    + sv2RatioRow('Con territorio', c.withTerr, total)
    + sv2RatioRow('Con fecha de publicación', c.withDate, total)
    + sv2RatioRow('Con organismo', c.withOrg, total)
    + '</div>';
  return sv2Module('Calidad y cobertura', 'Campos presentes sobre el total filtrado', bodyHTML, {
    tag: 'Datos',
    note: 'Ratios de cobertura de campos, no una puntuación de calidad: miden qué proporción de registros informa cada campo.'
  });
}

// ── F · DOCUMENT COVERAGE ────────────────────────────────────────────────────
function renderDocumentsModule(withDocs, totalDocs, total) {
  const sinDocs = total - withDocs;
  const segs = [
    { label: 'Con documentos enlazados', val: withDocs, color: 'var(--text)' },
    { label: 'Sin documentos',           val: sinDocs,  color: 'var(--border2)' },
  ];
  const bodyHTML = sv2Segments(segs, total)
    + '<div class="sv2-facts" style="margin-top:12px">'
    + factRow('Total de documentos enlazados', fmtNum(totalDocs))
    + '</div>';
  return sv2Module('Documentos enlazados', 'Cobertura de enlaces del expediente', bodyHTML, {
    tag: 'Datos',
    note: 'Documentos <strong>enlazados</strong> desde el expediente, no leídos ni analizados. No refleja extracción ni clasificación de contenido.'
  });
}

// ── G · TOP OPPORTUNITIES / ORGANISMS ────────────────────────────────────────
function renderTopOrgsModule(orgArr) {
  const items = orgArr.map(function(e){ return { main: e[0], val: fmtNum(e[1]) }; });
  return sv2Module('Organismos con más registros', null, sv2List(items), { cls: 'sv2-module--compact' });
}
function renderTopBudgetModule(topBudget) {
  const items = topBudget.map(function(r){
    const titol = r.titol || '—';
    return { main: titol.slice(0, 64) + (titol.length > 64 ? '…' : ''), sub: r.organisme || '—', val: fmt(r.pressupost) };
  });
  return sv2Module('Mayor presupuesto informado', null, sv2List(items), { cls: 'sv2-module--compact' });
}
function renderTopTerrModule(ccaaArr, esCount, total) {
  const items = ccaaArr.slice(0, 6).map(function(e){
    return { main: (TERR[e[0]] && TERR[e[0]].name) || e[0], val: fmtNum(e[1]) };
  });
  const note = esCount ? 'El ámbito estatal (ES) concentra el ' + formatPercent(esCount, total) + ' de los registros.' : '';
  return sv2Module('Territorios con más registros', null, sv2List(items), { cls: 'sv2-module--compact', note: note });
}

// ── H · EMPTY / LOW DATA STATE ───────────────────────────────────────────────
function renderEmptyState(hasFilters) {
  return '<div class="sv2-empty">'
    + '<i class="bi bi-funnel sv2-empty-icon"></i>'
    + '<div class="sv2-empty-title">Sin registros para esta combinación de filtros</div>'
    + '<div class="sv2-empty-sub">' + (hasFilters ? 'Prueba a ampliar o restablecer los filtros activos.' : 'No hay datos disponibles en este momento.') + '</div>'
    + (hasFilters ? '<button class="sv2-empty-reset" id="sv2-empty-reset" type="button"><i class="bi bi-arrow-counterclockwise"></i>Restablecer filtros</button>' : '')
    + '</div>';
}

// ── BARÓMETRO v1 (p208): cautious temporal reading by true cuatrimestre ──────
// Reads "what is happening over time?" (vs Estadísticas = "what is in the
// data?"). Runs on canonical/deduped records — never raw ADG.data as a
// headline source — and compares the selected year+cuatrimestre against the
// previous comparable cuatrimestre, with explicit caveats for sparse data and
// periods still in progress. No market diagnosis, no causal claims.

function baroCanon() {
  return (ADG.canonicalData && ADG.canonicalData.length) ? ADG.canonicalData : ADG.data;
}

// Sidebar filters EXCEPT the period (year/cuatrimestre): the period is owned by
// the Barómetro selector so the temporal series and previous-period comparison
// stay valid regardless of the sidebar year/cuatrimestre pills.
function baroBase(canon) {
  var rows = canon;
  if (SV.ccaa)  rows = rows.filter(function(r){ return r.ccaa === SV.ccaa; });
  if (SV.estat) rows = rows.filter(function(r){ return r.estat === SV.estat; });
  if (SV.discs.size) rows = rows.filter(function(r){ return (r.disciplines||[]).some(function(d){ return SV.discs.has(d); }); });
  return rows;
}

function currentCuatriContext() {
  var now = new Date();
  return { year: now.getFullYear(), cuatri: getCuatri(now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')) || 1 };
}

// Resolve the period to read: sidebar year/cuatri if set, else the latest
// period that actually has data (so the panel is never empty on first open).
function resolveBaroPeriod(base) {
  var yearsN = base.map(function(r){ return parseInt((r.data_pub||'').slice(0,4),10); }).filter(function(y){ return y>0; });
  var maxY = yearsN.length ? Math.max.apply(null, yearsN) : currentCuatriContext().year;
  var year = SV.year ? parseInt(SV.year,10) : maxY;
  var cuatri, explicit = !!(SV.year || SV.cuatri);
  if (SV.cuatri) cuatri = parseInt(SV.cuatri,10);
  else {
    var cs = base.filter(function(r){ return (r.data_pub||'').slice(0,4) === String(year); })
                 .map(function(r){ return getCuatri(r.data_pub); }).filter(function(c){ return c>0; });
    cuatri = cs.length ? Math.max.apply(null, cs) : currentCuatriContext().cuatri;
  }
  return { year: year, cuatri: cuatri, explicit: explicit };
}

function prevPeriod(p) {
  return p.cuatri > 1 ? { year:p.year, cuatri:p.cuatri-1 } : { year:p.year-1, cuatri:3 };
}
function periodRowsOf(base, p) {
  var key = p.year + '-C' + p.cuatri;
  return base.filter(function(r){ return periodKey(r) === key; });
}

// Step the selected period by ±1 cuatrimestre, clamped to the data year range so
// navigation never wanders into empty future/past. Writes back to the shared
// period state and re-renders.
function stepBaroPeriod(dir) {
  var canon = baroCanon();
  var base = baroBase(canon);
  var p = resolveBaroPeriod(base);
  var c = p.cuatri + dir, y = p.year;
  if (c < 1) { c = 3; y--; }
  if (c > 3) { c = 1; y++; }
  var yearsN = canon.map(function(r){ return parseInt((r.data_pub||'').slice(0,4),10); }).filter(function(n){ return n>0; });
  var minY = yearsN.length ? Math.min.apply(null, yearsN) : y;
  var maxY = Math.max(yearsN.length ? Math.max.apply(null, yearsN) : y, currentCuatriContext().year);
  if (y < minY || y > maxY) return;
  SV.year = String(y); SV.cuatri = String(c);
  var ys = el('sv-year'); if (ys) ys.value = SV.year;
  syncCuatri();
  renderBaro();
}

function medianOf(sortedVals) { return sortedVals.length ? sortedVals[Math.floor(sortedVals.length/2)] : 0; }

function renderBaro() {
  var page = el('baro-page'); if (!page) return;
  var canon = baroCanon();
  var base = baroBase(canon);
  var ctx = currentCuatriContext();
  var p = resolveBaroPeriod(base);
  var pv = prevPeriod(p);
  var rows = periodRowsOf(base, p);
  var prevRows = periodRowsOf(base, pv);
  var total = rows.length, prevTotal = prevRows.length;

  var enCurso = (p.year === ctx.year && p.cuatri === ctx.cuatri);
  var futuro  = (p.year > ctx.year) || (p.year === ctx.year && p.cuatri > ctx.cuatri);
  var reportDate = new Date().toLocaleDateString('es-ES', { day:'numeric', month:'long', year:'numeric' });

  // ── Cuatrimestre evolution series (last 6 periods ending at selection) ──────
  var byPeriod = {};
  base.forEach(function(r){ var k = periodKey(r); if (k) byPeriod[k] = (byPeriod[k]||0)+1; });
  var seq = [], yy = p.year, cc = p.cuatri;
  for (var i=0;i<6;i++){ seq.unshift({ year:yy, cuatri:cc, key: yy+'-C'+cc }); cc--; if (cc<1){ cc=3; yy--; } }
  var serie = seq.map(function(s){ return { label: String(s.year).slice(2)+'·C'+s.cuatri, val: byPeriod[s.key]||0, sel: (s.year===p.year && s.cuatri===p.cuatri) }; });
  var maxSerie = Math.max.apply(null, serie.map(function(s){ return s.val; }).concat([1]));
  var sparks = serie.map(function(s){
    return '<div class="baro-spark-col"><div class="baro-spark-bar" style="height:'+pct(s.val,maxSerie)+'%'+(s.sel?';background:var(--text)':';background:var(--border)')+'"></div>'
      +'<div class="baro-spark-lbl"'+(s.sel?' style="font-weight:700;color:var(--text2)"':'')+'>'+s.label+'</div>'
      +'<div class="baro-spark-val">'+s.val+'</div></div>';
  }).join('');

  // ── Period aggregates (current period) ──────────────────────────────────────
  var byDisc = {}, sinDisc = 0;
  rows.forEach(function(r){ var ds = r.disciplines||[]; if (!ds.length) sinDisc++; ds.forEach(function(d){ byDisc[d] = (byDisc[d]||0)+1; }); });
  var byDiscPrev = {}, sinDiscPrev = 0;
  prevRows.forEach(function(r){ var ds = r.disciplines||[]; if (!ds.length) sinDiscPrev++; ds.forEach(function(d){ byDiscPrev[d] = (byDiscPrev[d]||0)+1; }); });

  var conPpto = rows.filter(function(r){ return r.pressupost > 0; });
  var sinPpto = total - conPpto.length;
  var pptoSorted = conPpto.map(function(r){ return r.pressupost; }).sort(function(a,b){ return a-b; });
  var medianPpto = medianOf(pptoSorted);
  var minPpto = pptoSorted.length ? pptoSorted[0] : 0;
  var maxPpto = pptoSorted.length ? pptoSorted[pptoSorted.length-1] : 0;

  var byCCAA = {};
  rows.forEach(function(r){ if (r.ccaa) byCCAA[r.ccaa] = (byCCAA[r.ccaa]||0)+1; });
  var ccaaArr = Object.entries(byCCAA).sort(function(a,b){ return b[1]-a[1]; });
  var esCount = byCCAA['ES'] || 0, esPct = pct(esCount, total);

  var withDocs = rows.filter(function(r){ return (r.documents||[]).length > 0; });
  var totalDocs = withDocs.reduce(function(s,r){ return s + (r.documents||[]).length; }, 0);
  var docPct = pct(withDocs.length, total);

  // ── Delta chip (activity vs previous comparable cuatrimestre) ───────────────
  function deltaChip(cur, prev) {
    if (!prev) return '<span class="baro-delta flat"><i class="bi bi-dash"></i>sin base comparable</span>';
    var d = cur - prev, pc = Math.round(d/prev*100);
    if (d > 0) return '<span class="baro-delta up"><i class="bi bi-arrow-up-short"></i>+'+d+' ('+pc+'%)</span>';
    if (d < 0) return '<span class="baro-delta down"><i class="bi bi-arrow-down-short"></i>'+d+' ('+pc+'%)</span>';
    return '<span class="baro-delta flat"><i class="bi bi-dash"></i>sin cambio</span>';
  }
  function discDelta(cur, prev) {
    var d = cur - prev;
    if (d > 0) return '<span class="baro-delta up">+'+d+'</span>';
    if (d < 0) return '<span class="baro-delta down">'+d+'</span>';
    return '<span class="baro-delta flat">=</span>';
  }

  // ── Discipline movement bars (p204 colors, incl. "sin disciplina") ──────────
  var discEntries = Object.entries(byDisc).sort(function(a,b){ return b[1]-a[1]; });
  if (sinDisc) discEntries = discEntries.concat([['__none__', sinDisc]]);
  var maxDisc = discEntries.length ? Math.max.apply(null, discEntries.map(function(e){ return e[1]; })) : 1;
  var discBars = discEntries.length ? discEntries.slice(0,12).map(function(e){
    var key = e[0], val = e[1];
    var label = key === '__none__' ? (t('disc_none') || 'Sin disciplina') : (DISC[key] && DISC[key].label || key);
    var prev = key === '__none__' ? sinDiscPrev : (byDiscPrev[key]||0);
    return '<div class="baro-bar-row">'
      +'<div class="baro-bar-label" title="'+esc(label)+'">'+esc(label)+'</div>'
      +'<div class="baro-bar-track"><div class="baro-bar-fill" style="width:'+pct(val,maxDisc)+'%;background:'+discColor(key).text+'"></div></div>'
      +'<div class="baro-bar-val">'+val+' '+discDelta(val, prev)+'</div></div>';
  }).join('') : '<div class="sv-empty">Sin disciplinas registradas en el periodo</div>';

  // ── Territory bars ──────────────────────────────────────────────────────────
  var maxCCAA = ccaaArr.length ? ccaaArr[0][1] : 1;
  var ccaaBars = ccaaArr.length ? ccaaArr.slice(0,8).map(function(e){
    var name = TERR[e[0]] && TERR[e[0]].name || e[0];
    return '<div class="baro-bar-row"><div class="baro-bar-label" title="'+esc(name)+'">'+esc(name)+'</div>'
      +'<div class="baro-bar-track"><div class="baro-bar-fill" style="width:'+pct(e[1],maxCCAA)+'%;background:var(--text)"></div></div>'
      +'<div class="baro-bar-val">'+e[1]+'</div></div>';
  }).join('') : '<div class="sv-empty">Sin territorio registrado en el periodo</div>';

  // ── Narrative reading (computed facts only, cautious language) ───────────────
  var read = [];
  read.push('En <strong>'+periodTitle(p.year, p.cuatri)+'</strong> se registran <strong>'+total+'</strong> oportunidades canónicas en este dataset'
    + (prevTotal ? (', frente a '+prevTotal+' en '+periodTitle(pv.year, pv.cuatri)+' ('+(total-prevTotal>=0?'+':'')+(total-prevTotal)+').') : ' (sin periodo anterior comparable en la cobertura actual).'));
  if (enCurso) read.push('El periodo está <strong>en curso</strong>: las cifras son parciales y cualquier comparación con periodos cerrados es orientativa.');
  var topD = discEntries.filter(function(e){ return e[0] !== '__none__'; })[0];
  if (topD) read.push('Con la cobertura actual, la disciplina con más registros en el periodo es <strong>'+(DISC[topD[0]] && DISC[topD[0]].label || topD[0])+'</strong> ('+topD[1]+').');
  if (sinDisc) read.push('Se observan <strong>'+sinDisc+'</strong> registros sin disciplina asignada (grupo de calidad de datos), que no deben leerse como ausencia de actividad.');
  if (conPpto.length) read.push('Informan presupuesto <strong>'+conPpto.length+'</strong> de '+total+' registros; mediana <strong>'+fmt(medianPpto)+'</strong>. No representa el valor de mercado del periodo.');
  else read.push('Ningún registro del periodo informa presupuesto, por lo que no se ofrece señal económica.');
  if (esCount && esPct >= 40) read.push('La señal territorial está sesgada: el ámbito estatal (ES) concentra el <strong>'+esPct+'%</strong> de los registros del periodo.');
  if (withDocs.length) read.push('Enlazan documentos <strong>'+withDocs.length+'</strong> registros ('+docPct+'%); son enlaces del expediente, no contenido leído ni analizado.');

  // ── Assemble ────────────────────────────────────────────────────────────────
  var periodNote = p.explicit ? '' : ' <span class="baro-tag-curso" style="background:var(--bg2);color:var(--text3);border-color:var(--border2)">último con datos</span>';
  page.innerHTML = ''
    + '<div class="baro-header">'
      + '<div class="baro-header-left">'
        + '<div class="baro-header-eyebrow">Barómetro del Sector · ADG-FAD</div>'
        + '<div class="baro-header-title">Lectura temporal de contratación<br>en diseño y comunicación visual</div>'
        + '<div class="baro-header-meta">Lectura generada el '+reportDate+(ADG.isSample?' · <span style="color:var(--s-warn)">Datos de muestra</span>':'')+'</div>'
      + '</div>'
      + '<div class="baro-header-right"><button class="htbtn" id="baro-print"><i class="bi bi-printer"></i><span>Imprimir</span></button></div>'
    + '</div>'
    + '<div class="baro-section-title">Periodo</div>'
    + '<div class="baro-period">'
      + '<button class="htbtn" id="baro-prev" aria-label="Cuatrimestre anterior"><i class="bi bi-chevron-left"></i></button>'
      + '<div class="baro-period-label">'+periodTitle(p.year, p.cuatri)
        + (enCurso ? ' <span class="baro-tag-curso">periodo en curso</span>' : '')
        + (futuro ? ' <span class="baro-tag-curso" style="border-color:var(--s-warn);color:var(--s-warn)">periodo futuro</span>' : '')
        + periodNote
      + '</div>'
      + '<button class="htbtn" id="baro-next" aria-label="Cuatrimestre siguiente"><i class="bi bi-chevron-right"></i></button>'
    + '</div>'
    + '<div class="baro-section-title">Actividad registrada</div>'
    + '<div class="baro-bignums" style="grid-template-columns:repeat(4,1fr)">'
      + '<div class="baro-bignum"><div class="baro-bignum-val">'+total+'</div><div class="baro-bignum-lbl">Registros canónicos</div><div class="baro-bignum-sub">en el periodo</div></div>'
      + '<div class="baro-bignum"><div class="baro-bignum-val" style="font-size:13px;padding-top:5px">'+deltaChip(total, prevTotal)+'</div><div class="baro-bignum-lbl">Cambio vs anterior</div><div class="baro-bignum-sub">'+cuatriShort(pv.cuatri)+' '+pv.year+(enCurso?' · orientativo':'')+'</div></div>'
      + '<div class="baro-bignum"><div class="baro-bignum-val">'+conPpto.length+'</div><div class="baro-bignum-lbl">Con presupuesto</div><div class="baro-bignum-sub">'+sinPpto+' sin informar</div></div>'
      + '<div class="baro-bignum"><div class="baro-bignum-val">'+fmt(medianPpto)+'</div><div class="baro-bignum-lbl">Mediana de presupuesto</div><div class="baro-bignum-sub">presupuesto informado</div></div>'
    + '</div>'
    + (enCurso ? '<div class="baro-insight warn" style="margin-top:8px"><i class="bi bi-hourglass-split"></i><div>Periodo en curso: la cuatrimestre seleccionada aún no ha terminado. Las cifras son parciales y la comparación con periodos cerrados es <strong>orientativa</strong>.</div></div>' : '')
    + (futuro ? '<div class="baro-insight warn" style="margin-top:8px"><i class="bi bi-calendar-x"></i><div>Periodo futuro sin datos esperados con la cobertura actual.</div></div>' : '')
    + (!prevTotal && !futuro ? '<div class="baro-insight" style="margin-top:8px"><i class="bi bi-info-circle"></i><div>Sin periodo anterior comparable en el dataset: el cambio no puede calcularse de forma fiable.</div></div>' : '')
    + '<div class="baro-section-title">Evolución por cuatrimestre</div>'
    + '<div class="baro-card">'+(serie.some(function(s){return s.val;}) ? '<div class="baro-sparks">'+sparks+'</div><div class="baro-card-note">Registros canónicos por cuatrimestre (C1 Ene-Abr · C2 May-Ago · C3 Sep-Dic). La barra resaltada es el periodo seleccionado.</div>' : '<div class="sv-empty">Sin datos temporales suficientes</div>')+'</div>'
    + '<div class="baro-section-title">Distribución y territorio</div>'
    + '<div class="baro-grid">'
      + '<div class="baro-card"><div class="baro-card-title">Distribución por disciplina</div><div class="baro-bars">'+discBars+'</div><div class="baro-card-note">Delta frente a '+periodTitle(pv.year, pv.cuatri)+'. «Sin disciplina» es un grupo de calidad de datos. Colores por disciplina (p204).</div></div>'
      + '<div class="baro-card"><div class="baro-card-title">Territorio</div><div class="baro-bars">'+ccaaBars+'</div>'+(esCount?'<div class="baro-card-note">El ámbito estatal (ES) supone el '+esPct+'% del periodo; la distribución territorial puede estar sesgada hacia licitaciones estatales.</div>':'')+'</div>'
    + '</div>'
    + '<div class="baro-section-title">Presupuesto y documentos</div>'
    + '<div class="baro-grid">'
      + '<div class="baro-card"><div class="baro-card-title">Presupuesto informado</div><div class="baro-bars">'
        + '<div class="baro-bar-row"><div class="baro-bar-label">Con presupuesto</div><div class="baro-bar-track"><div class="baro-bar-fill" style="width:'+pct(conPpto.length,total||1)+'%;background:var(--text)"></div></div><div class="baro-bar-val">'+conPpto.length+'</div></div>'
        + '<div class="baro-bar-row"><div class="baro-bar-label">Sin presupuesto</div><div class="baro-bar-track"><div class="baro-bar-fill" style="width:'+pct(sinPpto,total||1)+'%;background:var(--border)"></div></div><div class="baro-bar-val">'+sinPpto+'</div></div>'
        + '</div><div class="baro-card-note">Mediana '+fmt(medianPpto)+' · rango '+fmt(minPpto)+' – '+fmt(maxPpto)+'. El presupuesto base es orientativo y no equivale al valor de mercado.</div></div>'
      + '<div class="baro-card"><div class="baro-card-title">Documentos enlazados</div><div class="baro-bars">'
        + '<div class="baro-bar-row"><div class="baro-bar-label">Con documentos</div><div class="baro-bar-track"><div class="baro-bar-fill" style="width:'+pct(withDocs.length,total||1)+'%;background:var(--text)"></div></div><div class="baro-bar-val">'+withDocs.length+' ('+docPct+'%)</div></div>'
        + '</div><div class="baro-card-note">'+totalDocs+' documentos <strong>enlazados</strong> desde el expediente, no leídos ni analizados.</div></div>'
    + '</div>'
    + '<div class="baro-section-title">Lectura orientativa</div>'
    + '<div class="baro-insights">'+read.map(function(x){ return '<div class="baro-insight"><i class="bi bi-dot"></i><div>'+x+'</div></div>'; }).join('')+'</div>'
    + '<div class="baro-footer">'
      + '<div>Lectura orientativa generada a partir de cifras calculadas · ADG Plataforma · '+reportDate+'</div>'
      + '<div>Fuente: PLACSP · contrataciondelestado.es · Registros canónicos (deduplicados) · Datos '+(ADG.isSample?'de muestra':'reales')+'</div>'
      + '<div style="margin-top:6px"><strong>ADG-FAD</strong> · <a href="https://adg-fad.org" target="_blank" rel="noopener">adg-fad.org</a></div>'
    + '</div>';

  // Wire period controls (IIFE-scoped — cannot use inline onclick).
  var bp = el('baro-prev'); if (bp) bp.addEventListener('click', function(){ stepBaroPeriod(-1); });
  var bn = el('baro-next'); if (bn) bn.addEventListener('click', function(){ stepBaroPeriod(1); });
  var pr = el('baro-print'); if (pr) pr.addEventListener('click', function(){ window.print(); });
}

// -- ACTIVE VIEW REFRESH -- routes render call to current view
function refreshActiveView() {
  // p210 shell: keep header, time semantics and ribbon in sync with state,
  // and expose the active module composition for the (future) p211/p212 grid.
  syncTimeSemantics();
  renderHeader();
  renderRailStatus();
  renderRibbon();
  var mainEl = document.querySelector('.analytics-main');
  if (mainEl) mainEl.setAttribute('data-modules', (ANALYTICS_MODULES[SV.view] || []).join(' '));
  if (SV.view === 'baro') renderBaro(); else render();
}
// -- VIEW SWITCH -------------------------------------------------------------
function switchView(v) {
  SV.view = v;
  var isBaro = (v === 'baro');
  document.querySelectorAll('[data-view]').forEach(function(btn) {
    btn.classList.toggle('active', btn.dataset.view === v);
  });
  var body=el('sv-body'), baro=el('baro-page');
  if (body) body.hidden = isBaro;
  if (baro) baro.hidden = !isBaro;
  refreshActiveView();
}
document.addEventListener('DOMContentLoaded', async () => {
  initShared();

  // Estado pills
  document.querySelectorAll('[data-sv-estat]').forEach(p => {
    p.addEventListener('click', () => {
      SV.estat = p.dataset.svEstat ?? ''; syncEstat(); refreshActiveView();
    });
  });

  // Disciplina pills — multi-select
  el('sv-all-disc')?.addEventListener('click', () => {
    SV.discs.clear(); syncDiscs(); refreshActiveView();
  });
  document.querySelectorAll('[data-sv-disc]').forEach(p => {
    p.addEventListener('click', () => {
      const d = p.dataset.svDisc;
      if (SV.discs.has(d)) SV.discs.delete(d); else SV.discs.add(d);
      syncDiscs(); refreshActiveView();
    });
  });

  document.querySelectorAll('[data-view]').forEach(function(b){b.addEventListener('click',function(){switchView(b.dataset.view);});});
  el('sv-reset')?.addEventListener('click', resetFilters);
  el('sv-year')?.addEventListener('change', e => { SV.year=e.target.value; refreshActiveView(); });
  el('sv-ccaa')?.addEventListener('change', e => { SV.ccaa=e.target.value; refreshActiveView(); });
  document.querySelectorAll('[data-sv-cuatri]').forEach(function(p) {
    p.addEventListener('click', function() {
      SV.cuatri = p.dataset.svCuatri; syncCuatri(); refreshActiveView();
    });
  });

  paintDiscMarks();

  document.addEventListener('adg:langchange', () => { applyI18n(); refreshActiveView(); updateStrip(); updateTicker(); });
  document.addEventListener('adg:themechange', () => { paintDiscMarks(); refreshActiveView(); });
  // Re-render as background shards stream in (p200 progressive loader)
  document.addEventListener('adg:dataupdated', () => { refreshActiveView(); updateStrip(); updateTicker(); });

  await loadData();
  updateStrip();
  updateTicker();
  refreshActiveView();
});
})();
