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
 * v0.6.71-78 Jul 2026  p218-p225 observatorio completion: structural semáforo in
 *                      Estadísticas (computeStatsSignals, reuses baro2-signal*),
 *                      presupuesto-base ≠ importe de adjudicación copy, ES/Estatal
 *                      framed as ámbito (not a peer territory), claim audit clean.
 *                      award_results stays DO-NOT-USE; adjudicataria = r.adjudicatari.
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
  if (allBtn) { allBtn.classList.toggle('active', none); allBtn.setAttribute('aria-pressed', String(none)); }
  const countEl = el('sv-disc-count');
  if (countEl) countEl.textContent = none ? '' : String(SV.discs.size);
  document.querySelectorAll('[data-sv-disc]').forEach(p => {
    const d = p.dataset.svDisc;
    const active = SV.discs.has(d);
    p.classList.toggle('active', active);
    p.setAttribute('aria-pressed', String(active));
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
// Honest percentage label (p212): 0% only when the count is truly zero; "<1%"
// when a count exists but rounds to 0; otherwise the normal integer percentage.
function pctLabel(a, b) {
  if (!b || !a) return '0%';
  return Math.round(a / b * 100) === 0 ? '<1%' : Math.round(a / b * 100) + '%';
}
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── ESTADÍSTICAS v2 VISUAL PRIMITIVES (p211B) ────────────────────────────────
// Restrained, dependency-free building blocks for the v2 data modules. All pure
// and defensive (null/NaN safe). Monochrome base; discipline color is used only
// as a taxonomy identity mark via discColor(). No chart library, no claims.
function fmtNum(n) { return (Number(n) || 0).toLocaleString('es-ES'); }
// p214: percentage display is unified on the honest pctLabel rule (0% only when the
// count is truly zero; "<1%" when a non-zero count rounds to zero). formatPercent is
// kept as an alias so existing call-sites read naturally and never emit a misleading 0%.
function formatPercent(a, b) { return pctLabel(a, b); }
// p214: canonical small-percentage helper (spec name). Same rule as pctLabel; exposed
// under the documented name so chart/label code can call it explicitly.
function pctSmart(count, total) { return pctLabel(count, total); }

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
  var hasShare = !!total; // total>0 → show share; falsy → geometry-only bar
  // p214: no explicit color ⇒ inherit the CSS slate fill (--sv2-ink), never black.
  return '<div class="sv2-bar">'
    + (markColor ? '<span class="sv2-bar-mark" style="background:' + markColor + '"></span>' : '')
    + '<div class="sv2-bar-label" title="' + esc(label) + '">' + esc(label) + '</div>'
    + '<div class="sv2-bar-track"><div class="sv2-bar-fill" style="width:' + pct(val, max) + '%'
      + (color ? ';background:' + color : '') + '"></div></div>'
    + '<div class="sv2-bar-val">' + fmtNum(val) + (hasShare ? '<span class="sv2-bar-pct">' + pctLabel(val, total) + '</span>' : '') + '</div>'
    + '</div>';
}

// Coverage ratio row: label, count·percent, thin progress track.
function sv2RatioRow(label, n, total) {
  var p = pct(n, total);
  return '<div class="sv2-ratio">'
    + '<div class="sv2-ratio-head"><span class="sv2-ratio-lbl">' + esc(label) + '</span>'
    + '<span class="sv2-ratio-val">' + fmtNum(n) + '<span class="sv2-bar-pct">' + pctLabel(n, total) + '</span></span></div>'
    + '<div class="sv2-ratio-track"><div class="sv2-ratio-fill" style="width:' + p + '%"></div></div>'
    + '</div>';
}

// Segmented single-bar + legend (lifecycle/status). segs: [{label,val,color}].
// p214: opts.thick renders the strong lifecycle bar; legend shares use pctLabel so a
// small non-zero segment (e.g. Desierta 12) reads "<1%", never a misleading 0%.
function sv2Segments(segs, total, opts) {
  opts = opts || {};
  var active = segs.filter(function(s){ return s.val > 0; });
  var bar = active.map(function(s){
    return '<div class="sv2-seg-fill" style="width:' + pct(s.val, total) + '%;background:' + s.color + '" title="' + esc(s.label) + '"></div>';
  }).join('');
  var legend = active.map(function(s){
    return '<div class="sv2-seg-item"><span class="sv2-seg-dot" style="background:' + s.color + '"></span>'
      + '<span class="sv2-seg-lbl">' + esc(s.label) + '</span>'
      + '<span class="sv2-seg-val">' + fmtNum(s.val) + '<span class="sv2-bar-pct">' + pctLabel(s.val, total) + '</span></span></div>';
  }).join('');
  return '<div class="sv2-seg' + (opts.thick ? ' sv2-seg--thick' : '') + '">'
    + (bar || '<div class="sv2-seg-fill" style="width:100%;background:var(--border2)"></div>') + '</div>'
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

// ── DISCIPLINE DONUT / QUESITO (p214) ─────────────────────────────────────────
// Dependency-free SVG donut. Each slice is a <circle> with pathLength=100 so
// stroke-dasharray is a direct percentage, rotated to its cumulative start (clockwise
// from 12 o'clock). Pure + defensive: skips zero/empty slices, degrades to a neutral
// ring when there is nothing to plot. Colors come from discColor() (taxonomy identity)
// and a neutral token for the "Sin disciplina" data-quality bucket.
// items: [{ key, label, val, color }]. `total` is the composition denominator.
function donutSegments(items, total) {
  var cum = 0, segs = [];
  if (!total) return segs;
  for (var i = 0; i < items.length; i++) {
    var val = items[i].val;
    if (!(val > 0)) continue;
    var p = val / total * 100;
    segs.push({ key: items[i].key, label: items[i].label, color: items[i].color, val: val, p: p, start: cum });
    cum += p;
  }
  return segs;
}

function renderDonut(items, total, coreNum, coreLbl) {
  var segs = donutSegments(items, total);
  // Stroke color goes in `style` (not the stroke attribute): CSS var() resolves in a
  // style attribute but NOT in an SVG presentation attribute, so the neutral
  // var(--disc-none-fg) / var(--border3) tokens would otherwise be dropped.
  // p215: interaction data lives on each slice (label/value/share/key) so the
  // center can echo the hovered discipline; slices are keyboard-focusable buttons.
  var ring = segs.map(function(s){
    var deg = (s.start * 3.6 - 90).toFixed(2);
    var share = pctLabel(s.val, total);
    var title = esc(s.label) + ' · ' + fmtNum(s.val) + ' (' + share + ')';
    return '<circle class="sv2-donut-seg" cx="18" cy="18" r="15.915" fill="none" style="stroke:' + s.color
      + '" stroke-width="5.2" pathLength="100" stroke-dasharray="' + s.p.toFixed(3) + ' ' + (100 - s.p).toFixed(3)
      + '" transform="rotate(' + deg + ' 18 18)" tabindex="0" role="button" aria-label="' + title + '"'
      + ' data-key="' + esc(s.key) + '" data-lbl="' + esc(s.label) + '" data-val="' + fmtNum(s.val) + '" data-share="' + share + '">'
      + '<title>' + title + '</title></circle>';
  }).join('');
  // p215: viewBox is padded (-2 -2 40 40) so the 5.2-wide stroke can never be
  // clipped at the ring's top/bottom (r 15.915 + stroke 2.6 = 18.515 > the old 18).
  return '<div class="sv2-donut-wrap">'
    + '<svg class="sv2-donut" viewBox="-2 -2 40 40" role="img" aria-label="Distribución por disciplina">'
    + '<circle cx="18" cy="18" r="15.915" fill="none" style="stroke:var(--border3)" stroke-width="5.2"></circle>'
    + ring
    + '</svg>'
    + '<div class="sv2-donut-core" data-default-num="' + fmtNum(coreNum) + '" data-default-lbl="' + esc(coreLbl || 'registros') + '">'
    + '<div class="sv2-donut-core-num">' + fmtNum(coreNum) + '</div>'
    + '<div class="sv2-donut-core-lbl">' + esc(coreLbl || 'registros') + '</div></div>'
    + '</div>';
}

function renderDonutLegend(items, total) {
  // p215: legend rows carry the same interaction data + key as their slice so
  // hovering/focusing a row drives the donut center and highlights the slice.
  return '<ul class="sv2-donut-legend">' + items.map(function(e){
    var share = pctLabel(e.val, total);
    return '<li class="sv2-donut-legrow" tabindex="0" role="button"'
      + ' data-key="' + esc(e.key) + '" data-lbl="' + esc(e.label) + '" data-val="' + fmtNum(e.val) + '" data-share="' + share + '">'
      + '<span class="sv2-donut-legdot" style="background:' + e.color + '"></span>'
      + '<span class="sv2-donut-leglbl" title="' + esc(e.label) + '">' + esc(e.label) + '</span>'
      + '<span class="sv2-donut-legval">' + fmtNum(e.val) + '<span class="sv2-bar-pct">' + share + '</span></span>'
      + '</li>';
  }).join('') + '</ul>';
}

// p215: wire donut interaction after render. Hovering/focusing a slice or legend
// row shows that discipline's label + value + share in the center; leaving/blurring
// restores the default (total records). Legend hover also highlights its slice via
// is-focus/is-active classes. Dependency-free, keyboard-accessible, defensive.
function wireDonut() {
  var core = document.querySelector('.sv2-donut-core');
  if (!core) return;
  var numEl = core.querySelector('.sv2-donut-core-num');
  var lblEl = core.querySelector('.sv2-donut-core-lbl');
  var defNum = core.getAttribute('data-default-num') || '';
  var defLbl = core.getAttribute('data-default-lbl') || '';
  var svg = document.querySelector('.sv2-donut');
  function highlight(key) {
    if (!svg) return;
    svg.classList.add('is-focus');
    svg.querySelectorAll('.sv2-donut-seg').forEach(function(s){
      s.classList.toggle('is-active', s.getAttribute('data-key') === key);
    });
  }
  function clearHighlight() {
    if (!svg) return;
    svg.classList.remove('is-focus');
    svg.querySelectorAll('.sv2-donut-seg').forEach(function(s){ s.classList.remove('is-active'); });
  }
  function show(node) {
    if (numEl) numEl.textContent = node.getAttribute('data-val');
    if (lblEl) lblEl.textContent = node.getAttribute('data-lbl') + ' · ' + node.getAttribute('data-share');
    highlight(node.getAttribute('data-key'));
  }
  function reset() {
    if (numEl) numEl.textContent = defNum;
    if (lblEl) lblEl.textContent = defLbl;
    clearHighlight();
  }
  document.querySelectorAll('.sv2-donut-seg, .sv2-donut-legrow').forEach(function(n){
    n.addEventListener('mouseenter', function(){ show(n); });
    n.addEventListener('mouseleave', reset);
    n.addEventListener('focus', function(){ show(n); });
    n.addEventListener('blur', reset);
  });
}

// ── MODULE REGISTRY FOUNDATION (p210) ────────────────────────────────────────
// Lightweight composition scaffold — NOT a framework. p210 only declares the
// module order per view and exposes reusable render primitives; p207 render()
// and p208 renderBaro() still produce the section bodies inline (strangler
// pattern). p211/p212 will migrate each id below into a composable module fn.
const ANALYTICS_MODULES = {
  stats: ['overview', 'semaforo', 'cobertura', 'ciclo-vida', 'presupuesto', 'plazos', 'documentos', 'adjudicatarias', 'adjudicatarias-territorio'],
  baro:  ['periodo', 'semaforo', 'actividad', 'estado', 'disciplinas', 'presupuesto', 'cobertura', 'territorio', 'adjudicatarias'],
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
// p213: one phrase per zone. The switcher (rail) owns the view name + Dataset/
// Periodo sub; the header owns the structural title + a short role line; the rail
// status panel owns canónicos/origen/freshness/coverage. `role` replaces the old
// rail mode-sub (which duplicated the header title) and the count-heavy header meta.
const VIEW_META = {
  stats: { title:'Estructura del dataset', role:'Composición, cobertura y calidad del conjunto de datos', timeLbl:'Filtro temporal',  timeHint:'Acota el dataset por fecha de publicación.' },
  baro:  { title:'Lectura del periodo',    role:'Actividad del cuatrimestre seleccionado',                timeLbl:'Periodo analizado', timeHint:'Selecciona el cuatrimestre de lectura.' },
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
  // p213: the header is structural only. The dataset counts/freshness/coverage
  // live in the rail status panel (renderRailStatus); the headline figure lives
  // in each hero; active filters live in the ribbon. The header just states the
  // view's role so the top-left context stops repeating the same numbers.
  var metaEl = el('analytics-meta');
  if (metaEl) metaEl.textContent = m.role || '';
}

function syncTimeSemantics() {
  var m = VIEW_META[SV.view] || VIEW_META.stats;
  var lbl = el('sv-time-lbl');  if (lbl)  lbl.textContent = m.timeLbl;
  var hint = el('sv-time-hint'); if (hint) hint.textContent = m.timeHint;
  // p213: the rail mode-sub was removed (it duplicated the switcher sub + header
  // title). The view-aware context now lives only in the time-section label/hint.
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

  // ── Adjudicatarias (informed-only; source of truth = r.adjudicatari) ──────
  const adj = adjudicatariaCounts(rows);

  // ── Structural semáforo (p220): dataset-level signals, no comparison ─────
  const sig = computeStatsSignals({
    total, sinAdjudicar, conPpto: conPpto.length, sinPpto, sinDisc,
    esCount, withTerr, withDate, withOrg, withDocs: withDocs.length,
    discCount: discArr.length, withAdj: adj.withAdj,
  });

  // ── Assemble v2 modules (ANALYTICS_MODULES.stats composition) ────────────
  body.innerHTML = '<div class="sv2-stack">'
    + renderStatHero({ total, canonGlobal, rawRows, hasFilters, state,
        sinAdjudicar, conPpto: conPpto.length, sumPpto, discCount: discArr.length })
    + renderStatsSignals(sig)
    + renderDisciplineModule(discArr, sinDisc, total)
    + '<div class="sv2-grid sv2-grid--2">'
      + renderStatusModule({ vigentes, adjudicadas, desiertas, otrosEstat, sinAdjudicar }, total)
      + renderBudgetModule({ conPpto: conPpto.length, sinPpto, sumPpto, medianPpto, minPpto, maxPpto, buckets, bucketOrder })
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
    + '<div class="sv2-grid sv2-grid--2">'
      + renderTopAdjudicatariasModule(adj)
      + renderAdjByTerritoryModule(rows)
    + '</div>'
    + '<div class="sv2-note sv2-note--foot">'
      + '<strong>Cobertura 2024–actual.</strong> Expedientes de contratación pública (PLACSP · contrataciondelestado.es) con relevancia para diseño y comunicación visual. Cifras sobre <strong>registros canónicos</strong> (deduplicados), no sobre filas de origen; no representan el tamaño total del mercado.'
    + '</div>'
    + '</div>';

  // p215: attach donut center interaction now the markup is in the DOM.
  wireDonut();
}

// ── A · HERO / DATASET SNAPSHOT ──────────────────────────────────────────────
function renderStatHero(d) {
  const lead = '<div class="sv2-hero-lead">'
    + '<div class="sv2-hero-state sv2-state--' + d.state.cls + '"><span class="sv2-state-dot"></span>' + esc(d.state.lbl) + '</div>'
    + '<div class="sv2-hero-num">' + fmtNum(d.total) + '</div>'
    + '<div class="sv2-hero-lbl">registros canónicos'
      + (d.hasFilters ? ' <span class="sv2-hero-of">filtrados de ' + fmtNum(d.canonGlobal) + '</span>' : '')
    + '</div>'
    + '<div class="sv2-hero-meta">Fuente PLACSP · contrataciondelestado.es</div>'
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

// ── A2 · STRUCTURAL SEMÁFORO (p220) ──────────────────────────────────────────
// Dataset-level signal system for Estadísticas, mirroring computeBaroSignals but
// STRUCTURAL: no previous period, no comparison, no score, no forecast. Every
// signal cites a metric already visible in the render() modules (coverage ratios,
// sin-disciplina, presupuesto, documentos, ES share). Thresholds are transparent
// and appear in each reason. Returns { positive, negative, caution } arrays of
// { label, reason }, rendered with the existing baro2-signal* vocabulary.
function computeStatsSignals(d) {
  var pos = [], neg = [], cau = [];
  var tot = d.total;

  // Positive: high field coverage / breadth, with the numbers in view.
  if (tot && pct(d.withDate, tot) >= 90) pos.push({ label:'Alta cobertura de fecha de publicación', reason:fmtNum(d.withDate)+' de '+fmtNum(tot)+' registros ('+pctLabel(d.withDate, tot)+') informan fecha.' });
  if (tot && pct(d.withOrg, tot) >= 90)  pos.push({ label:'Alta cobertura de organismo', reason:fmtNum(d.withOrg)+' de '+fmtNum(tot)+' registros ('+pctLabel(d.withOrg, tot)+') informan organismo.' });
  if (d.discCount >= 6)                  pos.push({ label:'Amplitud de disciplinas', reason:d.discCount+' disciplinas presentes en la selección.' });
  if (tot && pct(d.conPpto, tot) >= 50)  pos.push({ label:'Presupuesto base informado con frecuencia', reason:fmtNum(d.conPpto)+' de '+fmtNum(tot)+' registros ('+pctLabel(d.conPpto, tot)+') con presupuesto base.' });

  // Negative: structural data-quality gaps.
  if (tot && pct(d.sinDisc, tot) >= 25)          neg.push({ label:'Alta proporción sin disciplina', reason:fmtNum(d.sinDisc)+' registros ('+pctLabel(d.sinDisc, tot)+') aún sin clasificar · calidad de datos.' });
  if (tot && pct(d.withDocs, tot) < 50)          neg.push({ label:'Cobertura documental baja', reason:'Solo '+fmtNum(d.withDocs)+' de '+fmtNum(tot)+' registros ('+pctLabel(d.withDocs, tot)+') tienen documentos enlazados.' });
  if (tot && pct(tot - d.withTerr, tot) >= 20)   neg.push({ label:'Registros sin territorio', reason:fmtNum(tot - d.withTerr)+' registros ('+pctLabel(tot - d.withTerr, tot)+') no informan territorio.' });
  if (tot && pct(d.sinPpto, tot) >= 50)          neg.push({ label:'Mayoría sin presupuesto informado', reason:fmtNum(d.sinPpto)+' de '+fmtNum(tot)+' registros ('+pctLabel(d.sinPpto, tot)+') sin presupuesto base.' });

  // Cautions: honest framing that travels with the dataset (always structural).
  if (d.esCount)  cau.push({ label:'Concentración estatal (ES)', reason:'El ámbito estatal supone el '+pctLabel(d.esCount, tot)+' de la selección y no equivale a un territorio local.' });
  cau.push({ label:'Cobertura 2024–actual', reason:'El dataset no es un censo completo del mercado.' });
  if (d.conPpto)  cau.push({ label:'Presupuesto base orientativo', reason:'No es el importe de adjudicación ni equivale al valor de mercado.' });
  if (d.withDocs) cau.push({ label:'Documentos enlazados', reason:'Enlazados desde el expediente, no leídos ni analizados.' });
  if (d.withAdj)  cau.push({ label:'Adjudicataria informada', reason:'Campo informado en el expediente; no acredita la adjudicación real ni sus importes.' });

  return { positive: pos, negative: neg, caution: cau };
}

// Renders the structural semáforo inside the sv2 module shell, reusing the
// baro2-signal* classes (same visual system in both views, zero new CSS).
function renderStatsSignals(sig) {
  const grid = '<div class="baro2-signal-grid">'
    + baro2SignalBlock('positive', 'Señales positivas', 'bi-arrow-up-circle', sig.positive)
    + baro2SignalBlock('negative', 'Señales negativas', 'bi-arrow-down-circle', sig.negative)
    + baro2SignalBlock('caution',  'Cautelas · lectura prudente', 'bi-shield-exclamation', sig.caution)
    + '</div>';
  return sv2Module('Semáforo estructural', 'Señales derivadas de métricas visibles · sin puntuación ni previsión', grid,
    { tag: 'Semáforo', cls: 'sv2-module--feature' });
}

// ── B · DISCIPLINE DISTRIBUTION (featured, central module) ────────────────────
function renderDisciplineModule(discArr, sinDisc, total) {
  // p214: the discipline distribution is now a donut/quesito centerpiece. Each slice
  // uses the taxonomy color (discColor) so Editorial reads as Editorial everywhere;
  // "Sin disciplina" is a neutral data-quality bucket, never mistaken for a discipline.
  // The donut is a true composition, so its denominator is the sum of discipline
  // mentions (+ the sin-disciplina records) — a record can carry several disciplines.
  const items = discArr.map(function(e){
    return { key: e[0], label: (DISC[e[0]] && DISC[e[0]].label) || e[0], val: e[1], color: discColor(e[0]).text };
  });
  if (sinDisc) items.push({ key: '__none__', label: (t('disc_none') || 'Sin disciplina'), val: sinDisc, color: 'var(--disc-none-fg)' });
  const donutTotal = items.reduce(function(s, e){ return s + e.val; }, 0);
  let bodyHTML;
  if (!items.length || !donutTotal) {
    bodyHTML = emptyInline();
  } else {
    bodyHTML = '<div class="sv2-donut-layout">'
      + renderDonut(items, donutTotal, total, 'registros')
      + renderDonutLegend(items, donutTotal)
      + '</div>';
  }
  const note = sinDisc
    ? '«Sin disciplina» (' + fmtNum(sinDisc) + ') es un grupo de calidad de datos: expedientes aún sin clasificar. El quesito reparte las <strong>menciones</strong> de disciplina de la selección; un registro puede aportar varias, por eso el centro muestra los registros y las porciones suman el 100% de las menciones.'
    : 'El quesito reparte las <strong>menciones</strong> de disciplina de la selección; un registro puede aportar varias, por eso el centro muestra los registros y las porciones suman el 100% de las menciones.';
  return sv2Module('Distribución por disciplina', 'Reparto de la selección · quesito por menciones de disciplina', bodyHTML,
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
  return sv2Module('Estado del expediente', 'Distribución por estado declarado', sv2Segments(segs, total, { thick: true }), {
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
        // p215: bar length and the % label now share ONE denominator (records with
        // budget), so a "1072 · 32%" row reads as a 32%-long bar, not a full bar.
        // p214: no explicit color ⇒ neutral slate fill (--sv2-ink), not black.
        return sv2BarRow(k, b.buckets[k], b.conPpto, b.conPpto, null, null);
      }).join('') + '</div>'
    : emptyInline();
  const bodyHTML = '<div class="sv2-split-cols">'
    + '<div>' + facts + '</div>'
    + '<div><div class="sv2-sub-lbl">Distribución por rango</div>' + bucketBars + '</div>'
    + '</div>';
  return sv2Module('Presupuesto informado', 'Sobre ' + fmtNum(b.conPpto) + ' registros con presupuesto base', bodyHTML, {
    note: 'El presupuesto base de licitación es orientativo: <strong>no es el importe de adjudicación</strong> ni equivale al valor de mercado. Excluye ' + fmtNum(b.sinPpto) + ' registros sin presupuesto.'
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
    { label: 'Con documentos enlazados', val: withDocs, color: 'var(--sv2-ink)' },
    { label: 'Sin documentos',           val: sinDocs,  color: 'var(--sv2-soft)' },
  ];
  const bodyHTML = sv2Segments(segs, total, { thick: true })
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
  // p213: same territorial caveat vocabulary as Barómetro, kept near the
  // territory module (one contextual placement per view). p221: ES framed as an
  // ámbito, never a peer territory rankable against CCAAs.
  const note = 'Estatal / ES es un <strong>ámbito de contratación</strong>, no un territorio equiparable a las CCAA, y no debe leerse como su par en esta lista: una licitación estatal no se asigna directamente a Catalunya, Madrid u otros territorios.'
    + (esCount ? ' Aquí supone el ' + formatPercent(esCount, total) + ' de los registros.' : '');
  return sv2Module('Territorios con más registros', null, sv2List(items), { cls: 'sv2-module--compact', note: note });
}

// ── G2 · TOP ADJUDICATARIAS (descriptive, informed-only) ──────────────────────
// p217: who appears most often as adjudicataria in the current filtered canonical
// selection. Counts the `adjudicatari` field only; % is over rows WITH adjudicataria
// informed (never over all records, never "market share"). Presupuesto base is shown
// as a secondary, explicitly-orientativo figure — never an award amount.
function renderTopAdjudicatariasModule(adj) {
  if (!adj.withAdj) {
    return sv2Module('Adjudicatarias informadas', null,
      '<div class="sv2-empty-inline">Sin adjudicataria informada en la selección</div>',
      { cls: 'sv2-module--compact', tag: 'Adjudicación',
        note: 'Solo se listan registros con el campo adjudicataria poblado; la mayoría de expedientes vigentes o sin adjudicar todavía no lo informan.' });
  }
  const items = adj.entries.slice(0, 8).map(function(e){
    const val = fmtNum(e.count) + '<span class="sv2-bar-pct">' + pctLabel(e.count, adj.withAdj) + '</span>';
    const sub = e.budgetSum > 0 ? 'Presupuesto base informado · ' + fmt(e.budgetSum) : null;
    return { main: e.name, sub: sub, val: val };
  });
  return sv2Module('Top adjudicatarias', 'Sobre ' + fmtNum(adj.withAdj) + ' registros con adjudicataria informada', sv2List(items), {
    cls: 'sv2-module--compact', tag: 'Adjudicación',
    note: 'Cuenta apariciones del campo adjudicataria <strong>informada</strong> (no usa award_results ni infiere nombres); el reparto es sobre esos registros, no sobre el total ni sobre el mercado. El presupuesto base es orientativo y no equivale al importe de adjudicación.'
  });
}

// ── G3 · ADJUDICATARIAS BY TERRITORY (leading company per territory) ──────────
// p217: territory-aware view without overbuilding — the leading adjudicataria(s)
// per territory over informed rows. If a territory filter is active, getRows() has
// already scoped `rows`, so this naturally becomes "within that territory". ES kept
// with the same territorial-noise caveat; no implied local ownership of ES tenders.
function renderAdjByTerritoryModule(rows) {
  const terrs = adjudicatariasByTerritory(rows);
  if (!terrs.length) {
    return sv2Module('Adjudicatarias por territorio', null,
      '<div class="sv2-empty-inline">Sin adjudicataria informada por territorio en la selección</div>',
      { cls: 'sv2-module--compact', tag: 'Territorio' });
  }
  const hasES = terrs.some(function(e){ return e.ccaa === 'ES'; });
  const items = terrs.slice(0, 6).map(function(e){
    const name = (TERR[e.ccaa] && TERR[e.ccaa].name) || e.ccaa;
    const lead = e.top.slice(0, 2).map(function(tp){ return tp[0] + ' (' + tp[1] + ')'; }).join(' · ');
    return { main: name, sub: lead, val: fmtNum(e.withAdj) };
  });
  const note = 'Adjudicataria principal por territorio, sobre registros con adjudicataria informada; el valor es el nº de adjudicaciones informadas del territorio.'
    + (hasES ? ' Estatal / ES es un <strong>ámbito de contratación</strong>, no un territorio equiparable a las CCAA, y no debe compararse como su par: una licitación estatal no se asigna directamente a Catalunya, Madrid u otros territorios.' : '');
  return sv2Module('Adjudicatarias por territorio', 'Adjudicataria principal en los territorios con más adjudicaciones informadas', sv2List(items), {
    cls: 'sv2-module--compact', tag: 'Territorio', note: note });
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

// ── BARÓMETRO v2 (p212): period-reading surface + signal/semáforo base ───────
// Estadísticas answers "¿qué hay dentro del dataset?"; Barómetro answers "¿qué
// está pasando en el periodo seleccionado?". v2 turns the old report-card layout
// into period intelligence modules: a period hero, a semáforo (señales positivas
// / negativas / cautelas) derived only from visible metrics, and thick-bar
// status/discipline/budget/coverage/territory modules. No black-box scoring, no
// market forecast, no "AI says". Bars are thick and never pure-black (operator
// feedback); discipline bars use the taxonomy color via discColor().

// Pure metrics snapshot for one period's rows — shared by current & previous so
// comparisons stay symmetric. Defensive against null/NaN.
function baroPeriodMetrics(rows) {
  var total = rows.length;
  var byDisc = {}, sinDisc = 0;
  rows.forEach(function(r){ var ds = r.disciplines||[]; if (!ds.length) sinDisc++; ds.forEach(function(d){ byDisc[d] = (byDisc[d]||0)+1; }); });
  var conPpto = rows.filter(function(r){ return r.pressupost > 0; });
  var pptoSorted = conPpto.map(function(r){ return r.pressupost; }).sort(function(a,b){ return a-b; });
  var byCCAA = {};
  rows.forEach(function(r){ if (r.ccaa) byCCAA[r.ccaa] = (byCCAA[r.ccaa]||0)+1; });
  var withDocs = rows.filter(function(r){ return (r.documents||[]).length > 0; });
  var vigentes    = rows.filter(function(r){ return r.estat === 'Vigente'; }).length;
  var adjudicadas = rows.filter(function(r){ return r.estat === 'Adjudicado'; }).length;
  var desiertas   = rows.filter(function(r){ return r.estat === 'Desierta'; }).length;
  return {
    total: total,
    byDisc: byDisc, sinDisc: sinDisc, discCount: Object.keys(byDisc).length,
    conPpto: conPpto, conPptoN: conPpto.length, sinPpto: total - conPpto.length,
    median: medianOf(pptoSorted),
    minPpto: pptoSorted.length ? pptoSorted[0] : 0,
    maxPpto: pptoSorted.length ? pptoSorted[pptoSorted.length-1] : 0,
    sumPpto: conPpto.reduce(function(s,r){ return s + r.pressupost; }, 0),
    byCCAA: byCCAA, ccaaArr: Object.entries(byCCAA).sort(function(a,b){ return b[1]-a[1]; }),
    esCount: byCCAA['ES'] || 0,
    withDocsN: withDocs.length,
    totalDocs: withDocs.reduce(function(s,r){ return s + (r.documents||[]).length; }, 0),
    vigentes: vigentes, adjudicadas: adjudicadas, desiertas: desiertas,
    otros: total - vigentes - adjudicadas - desiertas,
  };
}

// Signal/semáforo generator (p212). Transparent rules only — every signal cites a
// visible metric. Comparative signals require a real previous closed period and a
// non-trivial current volume; cautions are honest framing that travels with the
// dataset. Returns { positive, negative, caution } arrays of { label, reason }.
function computeBaroSignals(cur, prev, f) {
  var pos = [], neg = [], cau = [];
  var lowCount = cur.total > 0 && cur.total < 10;
  var canCompare = f.hasPrev && !f.futuro && !lowCount;

  if (canCompare) {
    var d = cur.total - prev.total;
    if (d > 0)      pos.push({ label:'Más actividad que el periodo anterior', reason:'+'+d+' vs '+esc(f.prevTitle)+' ('+prev.total+')' });
    else if (d < 0) neg.push({ label:'Menos actividad que el periodo anterior', reason:d+' vs '+esc(f.prevTitle)+' ('+prev.total+')' });

    if (cur.conPptoN > prev.conPptoN)      pos.push({ label:'Más registros con presupuesto', reason:cur.conPptoN+' vs '+prev.conPptoN });
    else if (cur.conPptoN < prev.conPptoN) neg.push({ label:'Menos registros con presupuesto', reason:cur.conPptoN+' vs '+prev.conPptoN });

    var curDoc = pct(cur.withDocsN, cur.total), prevDoc = pct(prev.withDocsN, prev.total);
    if (curDoc > prevDoc)      pos.push({ label:'Mayor cobertura documental', reason:curDoc+'% vs '+prevDoc+'%' });
    else if (curDoc < prevDoc) neg.push({ label:'Menor cobertura documental', reason:curDoc+'% vs '+prevDoc+'%' });

    if (cur.discCount > prev.discCount)      pos.push({ label:'Más disciplinas presentes', reason:cur.discCount+' vs '+prev.discCount });
    else if (cur.discCount < prev.discCount) neg.push({ label:'Menos disciplinas presentes', reason:cur.discCount+' vs '+prev.discCount });

    var curSin = pct(cur.sinDisc, cur.total), prevSin = pct(prev.sinDisc, prev.total);
    if (cur.sinDisc > 0 && curSin > prevSin) neg.push({ label:'Más registros sin disciplina', reason:curSin+'% vs '+prevSin+'% · calidad de datos' });

    var curDes = pct(cur.desiertas, cur.total), prevDes = pct(prev.desiertas, prev.total);
    if (cur.desiertas >= 3 && curDes > prevDes) neg.push({ label:'Mayor proporción de desiertas', reason:curDes+'% vs '+prevDes+'%' });
  }

  // Cautions — always honest, derived from the period or the dataset itself.
  if (lowCount)                  cau.push({ label:'Periodo de bajo volumen', reason:'Solo '+cur.total+' registros: evita conclusiones fuertes.' });
  if (f.enCurso)                 cau.push({ label:'Periodo en curso', reason:'Cifras parciales; la comparación con periodos cerrados es orientativa.' });
  if (!f.hasPrev && !f.futuro)   cau.push({ label:'Sin periodo anterior comparable', reason:'No hay cuatrimestre previo en la cobertura para comparar.' });
  if (cur.esCount > 0)           cau.push({ label:'Concentración estatal (ES)', reason:'El ámbito estatal supone el '+pct(cur.esCount, cur.total)+'% y puede distorsionar la lectura territorial.' });
  cau.push({ label:'Cobertura 2024–actual', reason:'El dataset no es un censo completo del mercado.' });
  if (cur.conPptoN > 0)          cau.push({ label:'Presupuesto orientativo', reason:'El presupuesto base no equivale al valor de mercado.' });
  cau.push({ label:'Documentos enlazados', reason:'Los documentos están enlazados, no leídos ni analizados.' });

  return { positive: pos, negative: neg, caution: cau };
}

// ── Barómetro v2 visual primitives (thick bars, never pure-black fills) ──────
// Thick horizontal bar row: optional taxonomy mark, label, thick track, value and
// optional share. Defaults to the slate "ink" fill, not var(--text) (black).
function baro2Row(label, val, max, total, fill, markColor, deltaHTML) {
  return '<div class="baro2-row">'
    + (markColor ? '<span class="baro2-row-mark" style="background:' + markColor + '"></span>' : '')
    + '<div class="baro2-row-label" title="' + esc(label) + '">' + esc(label) + '</div>'
    + '<div class="baro2-bar"><div class="baro2-bar-fill" style="width:' + pct(val, max) + '%'
      + (fill ? ';background:' + fill : '') + '"></div></div>'
    + '<div class="baro2-row-val">' + fmtNum(val)
      + (total >= 0 ? '<span class="baro2-row-pct">' + pctLabel(val, total) + '</span>' : '')
      + (deltaHTML || '')
    + '</div></div>';
}

// Thick segmented status bar + legend. segs: [{label,val,color}]. Uses pctLabel so
// non-zero small shares show "<1%" instead of a misleading 0%.
function baro2Segments(segs, total) {
  var active = segs.filter(function(s){ return s.val > 0; });
  var bar = active.map(function(s){
    return '<div class="baro2-segment" style="width:' + pct(s.val, total) + '%;background:' + s.color + '" title="' + esc(s.label) + '"></div>';
  }).join('');
  var legend = active.map(function(s){
    return '<div class="baro2-seg-item"><span class="baro2-seg-dot" style="background:' + s.color + '"></span>'
      + '<span class="baro2-seg-lbl">' + esc(s.label) + '</span>'
      + '<span class="baro2-seg-val">' + fmtNum(s.val) + '<span class="baro2-row-pct">' + pctLabel(s.val, total) + '</span></span></div>';
  }).join('');
  return '<div class="baro2-thickbar">' + (bar || '<div class="baro2-segment" style="width:100%;background:var(--border2)"></div>') + '</div>'
    + '<div class="baro2-seg-legend">' + legend + '</div>';
}

// Module shell mirroring the p211B sv2 vocabulary but period/narrative oriented.
function baro2Module(title, sub, bodyHTML, opts) {
  opts = opts || {};
  var head = '<div class="baro2-module-head"><div class="baro2-module-titles">'
    + '<div class="baro2-module-title">' + esc(title) + '</div>'
    + (sub ? '<div class="baro2-module-sub">' + esc(sub) + '</div>' : '')
    + '</div>' + (opts.tag ? '<span class="baro2-module-tag">' + esc(opts.tag) + '</span>' : '') + '</div>';
  return '<section class="baro2-module' + (opts.cls ? ' ' + opts.cls : '') + '">'
    + head + (bodyHTML || '') + (opts.note ? '<div class="baro2-note">' + opts.note + '</div>' : '') + '</section>';
}

function baro2Fact(lbl, val) {
  return '<div class="baro2-fact"><span class="baro2-fact-lbl">' + esc(lbl) + '</span><span class="baro2-fact-val">' + val + '</span></div>';
}
function baro2RatioRow(label, n, total) {
  return '<div class="baro2-ratio">'
    + '<div class="baro2-ratio-head"><span class="baro2-ratio-lbl">' + esc(label) + '</span>'
    + '<span class="baro2-ratio-val">' + fmtNum(n) + '<span class="baro2-row-pct">' + pctLabel(n, total) + '</span></span></div>'
    + '<div class="baro2-ratio-track"><div class="baro2-ratio-fill" style="width:' + pct(n, total) + '%"></div></div>'
    + '</div>';
}
// Count delta chip vs the previous comparable period.
function baro2Delta(cur, prev, hasPrev) {
  if (!hasPrev) return '<span class="baro2-delta baro2-delta--flat"><i class="bi bi-dash"></i>sin base comparable</span>';
  var d = cur - prev, pc = prev ? Math.round(d/prev*100) : 0;
  if (d > 0) return '<span class="baro2-delta baro2-delta--up"><i class="bi bi-arrow-up-short"></i>+' + d + ' · +' + pc + '%</span>';
  if (d < 0) return '<span class="baro2-delta baro2-delta--down"><i class="bi bi-arrow-down-short"></i>' + d + ' · ' + pc + '%</span>';
  return '<span class="baro2-delta baro2-delta--flat"><i class="bi bi-dash"></i>sin cambio</span>';
}
function discDeltaMini(cur, prev) {
  var d = cur - prev;
  if (d > 0) return '<span class="baro2-delta baro2-delta--up">+' + d + '</span>';
  if (d < 0) return '<span class="baro2-delta baro2-delta--down">' + d + '</span>';
  return '';
}

// ── A · PERIOD HERO ──────────────────────────────────────────────────────────
function renderBaroHero(p, pv, cur, prev, f) {
  var stateLbl = ADG.isSample ? 'Datos de muestra' : (dataFreshnessLabel() || 'Datos reales');
  var stateCls = ADG.isSample ? 'sample' : 'ok';
  var tags = ''
    + (f.enCurso ? '<span class="baro2-period-tag baro2-period-tag--warn">periodo en curso</span>' : '')
    + (f.futuro  ? '<span class="baro2-period-tag baro2-period-tag--warn">periodo futuro</span>' : '')
    + (!p.explicit && !f.enCurso && !f.futuro ? '<span class="baro2-period-tag">último con datos</span>' : '');

  var nav = '<div class="baro2-period">'
    + '<button class="baro2-navbtn" id="baro-prev" type="button" aria-label="Cuatrimestre anterior"><i class="bi bi-chevron-left"></i></button>'
    + '<div class="baro2-period-label">' + esc(periodTitle(p.year, p.cuatri)) + tags + '</div>'
    + '<button class="baro2-navbtn" id="baro-next" type="button" aria-label="Cuatrimestre siguiente"><i class="bi bi-chevron-right"></i></button>'
    + '</div>';

  var lead = '<div class="baro2-hero-lead">'
    + '<div class="baro2-hero-state baro2-state--' + stateCls + '"><span class="baro2-state-dot"></span>' + esc(stateLbl) + '</div>'
    + '<div class="baro2-hero-num">' + fmtNum(cur.total) + '</div>'
    + '<div class="baro2-hero-lbl">registros del periodo</div>'
    + '<div class="baro2-hero-delta">' + baro2Delta(cur.total, prev.total, f.hasPrev) + '<span class="baro2-hero-delta-ref">vs ' + esc(f.prevTitle) + (f.enCurso ? ' · orientativo' : '') + '</span></div>'
    + '<div class="baro2-hero-read"><strong>' + esc(periodTitle(p.year, p.cuatri)) + '</strong> · actividad, estados, disciplinas, presupuesto y territorio del cuatrimestre.</div>'
    + '</div>';

  var metric = function(val, lbl, sub){ return '<div class="baro2-metric"><div class="baro2-metric-val">' + val + '</div>'
    + '<div class="baro2-metric-lbl">' + esc(lbl) + '</div>'
    + (sub ? '<div class="baro2-metric-sub">' + esc(sub) + '</div>' : '') + '</div>'; };
  var metrics = '<div class="baro2-metrics">'
    + metric(fmtNum(prev.total), 'Periodo anterior', f.prevTitle)
    + metric(fmtNum(cur.conPptoN), 'Con presupuesto', pctLabel(cur.conPptoN, cur.total) + ' del periodo')
    + metric(fmt(cur.median), 'Mediana', 'presupuesto base')
    + metric(fmtNum(cur.discCount), 'Disciplinas', 'presentes en el periodo')
    + '</div>';

  return '<section class="baro2-hero">'
    + '<div class="baro2-hero-top">'
      + '<div class="baro2-eyebrow"><i class="bi bi-broadcast-pin"></i><span>Barómetro</span></div>'
      + nav
    + '</div>'
    + '<div class="baro2-hero-body">' + lead + metrics + '</div>'
    + '</section>';
}

// ── B · SEMÁFORO / SIGNAL SYSTEM ─────────────────────────────────────────────
function baro2SignalBlock(kind, title, icon, items) {
  var body = items.length
    ? items.map(function(s){ return '<li class="baro2-signal-item"><span class="baro2-signal-lbl">' + esc(s.label) + '</span><span class="baro2-signal-reason">' + s.reason + '</span></li>'; }).join('')
    : '<li class="baro2-signal-empty">Sin señales en esta categoría</li>';
  return '<div class="baro2-signal baro2-signal--' + kind + '">'
    + '<div class="baro2-signal-head"><i class="bi ' + icon + '"></i><span>' + esc(title) + '</span><span class="baro2-signal-count">' + items.length + '</span></div>'
    + '<ul class="baro2-signal-list">' + body + '</ul></div>';
}
function renderBaroSignals(sig) {
  var grid = '<div class="baro2-signal-grid">'
    + baro2SignalBlock('positive', 'Señales positivas', 'bi-arrow-up-circle', sig.positive)
    + baro2SignalBlock('negative', 'Señales negativas', 'bi-arrow-down-circle', sig.negative)
    + baro2SignalBlock('caution',  'Cautelas · lectura prudente', 'bi-shield-exclamation', sig.caution)
    + '</div>';
  return baro2Module('Semáforo del periodo', 'Señales derivadas de métricas visibles · sin puntuación opaca ni previsión de mercado', grid, { tag: 'Semáforo', cls: 'baro2-module--feature' });
}

// ── C · ACTIVITY / PERIOD VOLUME (with cuatrimestre evolution) ───────────────
function renderBaroActivity(base, p, pv, cur, prev, f) {
  var byPeriod = {};
  base.forEach(function(r){ var k = periodKey(r); if (k) byPeriod[k] = (byPeriod[k]||0)+1; });
  var seq = [], yy = p.year, cc = p.cuatri;
  for (var i=0;i<6;i++){ seq.unshift({ year:yy, cuatri:cc, key: yy+'-C'+cc }); cc--; if (cc<1){ cc=3; yy--; } }
  var serie = seq.map(function(s){ return { label: String(s.year).slice(2)+'·C'+s.cuatri, val: byPeriod[s.key]||0, sel: (s.year===p.year && s.cuatri===p.cuatri) }; });
  var maxSerie = Math.max.apply(null, serie.map(function(s){ return s.val; }).concat([1]));
  var sparks = serie.map(function(s){
    return '<div class="baro2-spark-col"><div class="baro2-spark-bar' + (s.sel ? ' is-sel' : '') + '" style="height:' + pct(s.val, maxSerie) + '%"></div>'
      + '<div class="baro2-spark-lbl' + (s.sel ? ' is-sel' : '') + '">' + s.label + '</div>'
      + '<div class="baro2-spark-val">' + s.val + '</div></div>';
  }).join('');

  var hasSerie = serie.some(function(s){ return s.val; });
  var summary = '<div class="baro2-activity-summary">'
    + baro2Fact('Periodo seleccionado', '<strong>' + fmtNum(cur.total) + '</strong>')
    + baro2Fact('Periodo anterior · ' + esc(f.prevTitle), fmtNum(prev.total))
    + baro2Fact('Cambio', baro2Delta(cur.total, prev.total, f.hasPrev))
    + '</div>';
  var body = summary
    + '<div class="baro2-sub-lbl">Evolución · últimos 6 cuatrimestres</div>'
    + (hasSerie ? '<div class="baro2-sparks">' + sparks + '</div>' : '<div class="baro2-empty-inline">Sin datos temporales suficientes</div>');
  var note = f.enCurso
    ? 'El periodo está <strong>en curso</strong>: las cifras son parciales y la comparación con periodos cerrados es orientativa.'
    : (!f.hasPrev ? 'Sin periodo anterior comparable en la cobertura: el cambio no puede calcularse de forma fiable.'
      : 'C1 Ene–Abr · C2 May–Ago · C3 Sep–Dic. La barra resaltada es el periodo seleccionado.');
  return baro2Module('Actividad del periodo', 'Registros canónicos y evolución por cuatrimestre', body, { tag: 'Volumen', note: note });
}

// ── D · STATUS / LIFECYCLE (thick segmented bar) ─────────────────────────────
function renderBaroStatus(cur) {
  var segs = [
    { label: 'Vigente',    val: cur.vigentes,    color: 'var(--s-ok)'  },
    { label: 'Adjudicado', val: cur.adjudicadas, color: 'var(--s-adj)' },
    { label: 'Desierta',   val: cur.desiertas,   color: 'var(--s-des)' },
  ];
  if (cur.otros > 0) segs.push({ label: 'Otros / sin estado', val: cur.otros, color: 'var(--text3)' });
  var body = cur.total ? baro2Segments(segs, cur.total) : '<div class="baro2-empty-inline">Sin registros en el periodo</div>';
  return baro2Module('Estado del expediente', 'Distribución por estado declarado en el periodo', body, {
    note: 'Porcentajes sobre los ' + fmtNum(cur.total) + ' registros del periodo. Un valor con registros nunca se muestra como 0%.'
  });
}

// ── E · DISCIPLINE MIX (discipline colors, thick bars) ───────────────────────
function renderBaroDisciplines(cur, prev) {
  var entries = Object.entries(cur.byDisc).sort(function(a,b){ return b[1]-a[1]; });
  if (cur.sinDisc) entries = entries.concat([['__none__', cur.sinDisc]]);
  // p216: these bars are intentionally RELATIVE-TO-TOP (max = the largest discipline
  // count) as a ranked mix, and they carry NO share-of-total percentage — baro2Row is
  // called with total = -1 so the % label is suppressed. Only the raw count + delta
  // show, so a full-length top bar can never contradict a share-of-period label.
  var max = entries.length ? Math.max.apply(null, entries.map(function(e){ return e[1]; })) : 1;
  var bars = entries.length ? '<div class="baro2-rows">' + entries.slice(0, 12).map(function(e){
    var key = e[0], val = e[1];
    var label = key === '__none__' ? (t('disc_none') || 'Sin disciplina') : (DISC[key] && DISC[key].label || key);
    var fill  = key === '__none__' ? 'var(--disc-none-fg)' : discColor(key).text;
    var prevVal = key === '__none__' ? prev.sinDisc : (prev.byDisc[key] || 0);
    return baro2Row(label, val, max, -1, fill, fill, ' ' + discDeltaMini(val, prevVal));
  }).join('') + '</div>' : '<div class="baro2-empty-inline">Sin disciplinas registradas en el periodo</div>';
  return baro2Module('Disciplinas del periodo', 'Reparto por disciplina · delta frente al periodo anterior', bars, {
    tag: 'Composición', cls: 'baro2-module--feature',
    note: 'Colores por disciplina (taxonomía ADG). «Sin disciplina» es un grupo de calidad de datos, no ausencia de actividad. Un registro puede tener varias disciplinas.'
  });
}

// ── F · BUDGET PROFILE ───────────────────────────────────────────────────────
function renderBaroBudget(cur) {
  var facts = '<div class="baro2-facts">'
    + baro2Fact('Con presupuesto', fmtNum(cur.conPptoN) + ' <span class="baro2-row-pct">' + pctLabel(cur.conPptoN, cur.total) + '</span>')
    + baro2Fact('Sin informar', fmtNum(cur.sinPpto))
    + baro2Fact('Mediana', fmt(cur.median))
    + baro2Fact('Rango', fmt(cur.minPpto) + ' – ' + fmt(cur.maxPpto))
    + baro2Fact('Suma informada', fmt(cur.sumPpto))
    + '</div>';
  var split = cur.total
    ? '<div class="baro2-rows">'
        + baro2Row('Con presupuesto', cur.conPptoN, cur.total, cur.total, 'var(--baro2-ink)', null)
        + baro2Row('Sin presupuesto', cur.sinPpto, cur.total, cur.total, 'var(--baro2-soft)', null)
      + '</div>'
    : '<div class="baro2-empty-inline">Sin registros en el periodo</div>';
  var body = facts + '<div class="baro2-sub-lbl" style="margin-top:13px">Reparto</div>' + split;
  return baro2Module('Presupuesto del periodo', 'Sobre ' + fmtNum(cur.conPptoN) + ' registros con presupuesto base', body, {
    note: cur.conPptoN
      ? 'El presupuesto base de licitación es orientativo: <strong>no es el importe de adjudicación</strong> ni equivale al valor de mercado. Excluye ' + fmtNum(cur.sinPpto) + ' registros sin presupuesto.'
      : 'Ningún registro del periodo informa presupuesto, por lo que no se ofrece señal económica.'
  });
}

// ── G · DOCUMENT / COVERAGE PROFILE ──────────────────────────────────────────
function renderBaroCoverage(cur) {
  var withDisc = cur.total - cur.sinDisc;
  var withTerr = cur.ccaaArr.reduce(function(s,e){ return s + e[1]; }, 0);
  var body = cur.total
    ? '<div class="baro2-ratios">'
        + baro2RatioRow('Con documentos enlazados', cur.withDocsN, cur.total)
        + baro2RatioRow('Con disciplina asignada', withDisc, cur.total)
        + baro2RatioRow('Con presupuesto', cur.conPptoN, cur.total)
        + baro2RatioRow('Con territorio', withTerr, cur.total)
      + '</div>'
      + '<div class="baro2-facts" style="margin-top:13px">' + baro2Fact('Total de documentos enlazados', fmtNum(cur.totalDocs)) + '</div>'
    : '<div class="baro2-empty-inline">Sin registros en el periodo</div>';
  return baro2Module('Cobertura del periodo', 'Campos presentes sobre los registros del periodo', body, {
    tag: 'Datos',
    note: 'Documentos <strong>enlazados</strong> desde el expediente, no leídos ni analizados. Las ratios miden presencia de campo, no calidad.'
  });
}

// ── ADJUDICATARIAS AGGREGATION (p216 audit · p217 wired) ─────────────────────
// Pure + defensive. Aggregates the awarded-company name from the single reliable,
// already-normalized field `r.adjudicatari` (cleaned in app.js normalizeItem:
// HTML-stripped, entity-decoded, junk placeholders like "detalle"/"adjudicaci…"
// collapsed to ''). It does NOT read `award_results` (present in the data but its
// shape is unaudited in the frontend), does NOT infer names from free text/titles/
// organisms/URLs, and does NOT classify. Per entry it also carries how many of that
// company's records inform a presupuesto base (>0) and the sum of that base — which
// is orientativo and NOT an award amount — plus a ccaa territory breakdown.
// Returns { entries:[{ name, count, budgetCount, budgetSum, territories }] sorted by
// count desc, withAdj: rows with a usable adjudicataria, total: rows.length }.
function adjudicatariaCounts(rows) {
  var by = {}, withAdj = 0;
  (rows || []).forEach(function(r){
    var name = r && typeof r.adjudicatari === 'string' ? r.adjudicatari.trim() : '';
    if (!name) return;
    withAdj++;
    var e = by[name] || (by[name] = { name: name, count: 0, budgetCount: 0, budgetSum: 0, territories: {} });
    e.count++;
    var p = r.pressupost;
    if (typeof p === 'number' && p > 0) { e.budgetCount++; e.budgetSum += p; }
    if (r.ccaa) e.territories[r.ccaa] = (e.territories[r.ccaa] || 0) + 1;
  });
  var entries = Object.keys(by).map(function(k){ return by[k]; }).sort(function(a,b){ return b.count - a.count; });
  return { entries: entries, withAdj: withAdj, total: (rows || []).length };
}

// Territory → leading adjudicatarias, built only from `r.adjudicatari` + `r.ccaa`.
// Pure + defensive; same source-of-truth rules as adjudicatariaCounts. Returns one
// entry per ccaa that has at least one informed adjudicataria, sorted by informed
// count desc, each with its ranked [name, count] list (`top`).
function adjudicatariasByTerritory(rows) {
  var terr = {};
  (rows || []).forEach(function(r){
    var name = r && typeof r.adjudicatari === 'string' ? r.adjudicatari.trim() : '';
    if (!name || !r.ccaa) return;
    var e = terr[r.ccaa] || (terr[r.ccaa] = { ccaa: r.ccaa, withAdj: 0, byName: {} });
    e.withAdj++;
    e.byName[name] = (e.byName[name] || 0) + 1;
  });
  return Object.keys(terr).map(function(k){
    var e = terr[k];
    e.top = Object.entries(e.byName).sort(function(a,b){ return b[1]-a[1]; });
    return e;
  }).sort(function(a,b){ return b.withAdj - a.withAdj; });
}

// ── H · TERRITORIAL READING + ES WARNING ─────────────────────────────────────
function renderBaroTerritory(cur) {
  // p216: bar length and the % label now share ONE denominator (the period total),
  // so a row that labels "61%" renders a 61%-long bar — it is a share-of-period bar,
  // NOT relative-to-top. (Pre-p216 the fill used the top-territory count as its max,
  // so the largest territory always rendered full while its label read e.g. 61%.)
  var bars = cur.ccaaArr.length ? '<div class="baro2-rows">' + cur.ccaaArr.slice(0, 8).map(function(e){
    var name = (TERR[e[0]] && TERR[e[0]].name) || e[0];
    var fill = e[0] === 'ES' ? 'var(--s-warn)' : 'var(--baro2-ink)';
    return baro2Row(name, e[1], cur.total, cur.total, fill, null);
  }).join('') + '</div>' : '<div class="baro2-empty-inline">Sin territorio registrado en el periodo</div>';
  var warning = '<div class="baro2-callout"><i class="bi bi-exclamation-triangle"></i><div>'
    + 'Estatal / ES puede introducir ruido territorial: una licitación estatal no se asigna directamente a Catalunya, Madrid u otros territorios.'
    + (cur.esCount ? ' En este periodo el ámbito estatal supone el <strong>' + pct(cur.esCount, cur.total) + '%</strong> de los registros.' : '')
    + '</div></div>';
  return baro2Module('Territorio del periodo', 'Territorios con más registros en el periodo', bars + warning, { tag: 'Territorio' });
}

// ── H2 · PERIOD ADJUDICATARIAS (compact, informed-only) ──────────────────────
// p217: top adjudicatarias for the selected period only. Bars share ONE denominator
// with their label (withAdj = rows in the period WITH adjudicataria informed), so a
// row labelled 37% renders a 37%-long bar (p216 semantics). Never over all period
// records, never "market share", never award_results.
function renderBaroAdjudicatarias(adj) {
  var body, sub;
  if (!adj.withAdj) {
    sub = 'Adjudicatarias informadas en el periodo';
    body = '<div class="baro2-empty-inline">Sin adjudicataria informada en el periodo</div>';
  } else {
    sub = 'Sobre ' + fmtNum(adj.withAdj) + ' registros del periodo con adjudicataria informada';
    body = '<div class="baro2-rows">' + adj.entries.slice(0, 8).map(function(e){
      return baro2Row(e.name, e.count, adj.withAdj, adj.withAdj, 'var(--baro2-ink)', null);
    }).join('') + '</div>';
  }
  return baro2Module('Adjudicatarias del periodo', sub, body, {
    tag: 'Adjudicación',
    note: adj.withAdj
      ? 'Reparto sobre los <strong>' + fmtNum(adj.withAdj) + '</strong> registros del periodo con adjudicataria informada, no sobre todos los registros ni sobre el mercado. Cuenta apariciones del campo adjudicataria; no usa award_results ni infiere nombres.'
      : 'La mayoría de expedientes del periodo aún no informan adjudicataria (p. ej. vigentes o sin adjudicar). No se listan hasta que el dato existe.'
  });
}

// ── I · EMPTY / LOW-DATA STATE ───────────────────────────────────────────────
function renderBaroEmpty(p, f) {
  return '<div class="baro2-empty">'
    + '<i class="bi bi-calendar2-week baro2-empty-icon"></i>'
    + '<div class="baro2-empty-title">Sin registros en ' + esc(periodTitle(p.year, p.cuatri)) + '</div>'
    + '<div class="baro2-empty-sub">' + (f.futuro
        ? 'Periodo futuro sin datos esperados con la cobertura actual (2024–actual).'
        : 'No hay registros canónicos en este cuatrimestre con los filtros activos. Evita conclusiones sobre un periodo vacío.') + '</div>'
    + '<div class="baro2-empty-nav">'
      + '<button class="baro2-navbtn" id="baro-prev" type="button" aria-label="Cuatrimestre anterior"><i class="bi bi-chevron-left"></i></button>'
      + '<span class="baro2-empty-period">' + esc(periodTitle(p.year, p.cuatri)) + '</span>'
      + '<button class="baro2-navbtn" id="baro-next" type="button" aria-label="Cuatrimestre siguiente"><i class="bi bi-chevron-right"></i></button>'
    + '</div></div>';
}

function renderBaro() {
  var page = el('baro-page'); if (!page) return;
  var canon = baroCanon();
  var base = baroBase(canon);
  var ctx = currentCuatriContext();
  var p = resolveBaroPeriod(base);
  var pv = prevPeriod(p);
  var rows = periodRowsOf(base, p);
  var prevRows = periodRowsOf(base, pv);

  var cur = baroPeriodMetrics(rows);
  var prev = baroPeriodMetrics(prevRows);
  var adj = adjudicatariaCounts(rows); // period-scoped, informed-only

  var f = {
    enCurso: (p.year === ctx.year && p.cuatri === ctx.cuatri),
    futuro:  (p.year > ctx.year) || (p.year === ctx.year && p.cuatri > ctx.cuatri),
    hasPrev: prev.total > 0,
    prevTitle: periodTitle(pv.year, pv.cuatri),
  };

  // ── I · Empty / low-data state (no modules, just the empty surface + nav) ───
  if (!cur.total) {
    page.innerHTML = '<div class="baro2-stack">' + renderBaroEmpty(p, f) + '</div>';
    wireBaroControls();
    return;
  }

  var sig = computeBaroSignals(cur, prev, f);

  page.innerHTML = '<div class="baro2-stack">'
    + renderBaroHero(p, pv, cur, prev, f)
    + renderBaroSignals(sig)
    + '<div class="baro2-grid baro2-grid--2">'
      + renderBaroActivity(base, p, pv, cur, prev, f)
      + renderBaroStatus(cur)
    + '</div>'
    + renderBaroDisciplines(cur, prev)
    + '<div class="baro2-grid baro2-grid--2">'
      + renderBaroBudget(cur)
      + renderBaroCoverage(cur)
    + '</div>'
    + renderBaroTerritory(cur)
    + renderBaroAdjudicatarias(adj)
    + '<div class="baro2-note baro2-note--foot">'
      + '<strong>Lectura del periodo.</strong> Barómetro lee el cuatrimestre seleccionado; Estadísticas describe el dataset completo. '
      + 'Cifras sobre <strong>registros canónicos</strong> (deduplicados) de cobertura <strong>2024–actual</strong> · Fuente PLACSP · contrataciondelestado.es · '
      + 'Datos ' + (ADG.isSample ? 'de muestra' : 'reales') + '. No representa el tamaño total del mercado.'
    + '</div>'
    + '</div>';

  wireBaroControls();
}

// Wire period controls (IIFE-scoped — cannot use inline onclick). Present in both
// the populated and empty states, so it is shared.
function wireBaroControls() {
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
