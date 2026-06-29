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

function donutSVG(segments, size=64) {
  const r = 20, cx=32, cy=32, circ=2*Math.PI*r;
  let offset = 0;
  const paths = segments.map(s => {
    const len = circ * s.pct / 100;
    const path = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="8" stroke-dasharray="${len} ${circ-len}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})"/>`;
    offset += len;
    return path;
  });
  return `<svg width="${size}" height="${size}" viewBox="0 0 64 64">${paths.join('')}<circle cx="${cx}" cy="${cy}" r="12" fill="var(--bg)"/></svg>`;
}

function barCard(title, items, colorFn, valFn) {
  if (!items.length) return `<div class="sv-card"><div class="sv-card-title">${title}</div><div class="sv-empty">${t('sv_no_data')}</div></div>`;
  const max = items[0][1] || 1;
  const bars = items.slice(0,8).map(([label,val]) => {
    const color = colorFn ? colorFn(label) : 'var(--text)';
    const display = valFn ? valFn(val) : val.toLocaleString('es-ES');
    return `<div class="sv-bar-row">
      <div class="sv-bar-label" title="${esc(label)}">${esc(label)}</div>
      <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${pct(val,max)}%;background:${color}"></div></div>
      <div class="sv-bar-val">${display}</div>
    </div>`;
  }).join('');
  return `<div class="sv-card"><div class="sv-card-title">${title}</div><div class="sv-bars">${bars}</div></div>`;
}

// ── DISCIPLINE BAR CARD (p207) ──────────────────────────────────────────────
// Renders discipline counts using p204 discColor() helpers. Accepts an explicit
// '__none__' key for the neutral "sin disciplina" data-quality bucket so it is
// shown honestly rather than hidden.
function discBarCard(title, entries, note) {
  if (!entries.length) return `<div class="sv-card"><div class="sv-card-title">${title}</div><div class="sv-empty">${t('sv_no_data')}</div></div>`;
  const max = entries[0][1] || 1;
  const bars = entries.slice(0,12).map(([key,val]) => {
    const label = key === '__none__' ? (t('disc_none') || 'Sin disciplina') : (DISC[key]?.label || key);
    const color = discColor(key).text; // neutral fallback built in for unknown/none keys
    return `<div class="sv-bar-row">
      <div class="sv-bar-label" title="${esc(label)}">${esc(label)}</div>
      <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${pct(val,max)}%;background:${color}"></div></div>
      <div class="sv-bar-val">${val.toLocaleString('es-ES')}</div>
    </div>`;
  }).join('');
  return `<div class="sv-card"><div class="sv-card-title">${title}</div><div class="sv-bars">${bars}</div>${note?`<div class="sv-card-note">${note}</div>`:''}</div>`;
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
  stats: { title:'Estructura del dataset',  timeLbl:'Filtro temporal',  timeHint:'Acota el dataset por fecha de publicación.' },
  baro:  { title:'Lectura del cuatrimestre', timeLbl:'Periodo analizado', timeHint:'Define el cuatrimestre que lee el Barómetro.' },
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

// ── RENDER ────────────────────────────────────────────────────────────────
// p207: Estadísticas v1 — descriptive, honest, canonical-data surface.
// Answers "what is in the data?" (Barómetro/p208 answers "what is happening
// in the sector over time?"). All figures run on canonical/deduped records.
function render() {
  // Canonical/deduped source — never raw duplicated ADG.data rows.
  const canonSource = (ADG.canonicalData && ADG.canonicalData.length) ? ADG.canonicalData : ADG.data;
  const rows = getRows(canonSource);
  const total = rows.length;
  const canonGlobal = canonSource.length;
  const rawRows = ADG.data.length;

  // Summary line — canonical count is the headline; raw rows are labelled as source.
  const sumEl = el('sv-summary');
  if (sumEl) {
    const parts = [];
    if (SV.year)  parts.push(SV.year);
    if (SV.cuatri) parts.push(cuatriShort(parseInt(SV.cuatri,10)));
    if (SV.ccaa)  parts.push(TERR[SV.ccaa]?.name || SV.ccaa);
    if (SV.estat) parts.push(SV.estat);
    if (SV.discs.size) parts.push([...SV.discs].map(d=>DISC[d]?.label||d).join(', '));
    const label = parts.length ? `${t('sv_filter_label')}: <strong>${esc(parts.join(' · '))}</strong> — ` : '';
    sumEl.innerHTML = `${label}<strong>${total.toLocaleString('es-ES')}</strong> registros canónicos · ${t('sv_of')} <strong>${canonGlobal.toLocaleString('es-ES')}</strong> · derivados de <strong>${rawRows.toLocaleString('es-ES')}</strong> filas de origen`;
  }

  const body = el('sv-body');
  if (!body) return;

  if (!total) {
    body.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text3)"><i class="bi bi-funnel" style="font-size:32px;display:block;margin-bottom:10px;opacity:.3"></i><div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase">${t('sv_no_data')}</div></div>`;
    return;
  }

  // ── Lifecycle / status (canonical classification) ───────────────────────
  // "Sin adjudicar" = active_opportunity_eligible (lifecycle: not yet awarded),
  // NOT "open for bids right now" — submission windows are reported separately.
  const sinAdjudicar = rows.filter(r => r.active_opportunity_eligible === true).length;
  const adjudicadas  = rows.filter(r => r.estat === 'Adjudicado').length;
  const desiertas    = rows.filter(r => r.estat === 'Desierta').length;

  // ── Budget (distribution, not just total) ───────────────────────────────
  const conPpto    = rows.filter(r => r.pressupost > 0);
  const sinPpto    = total - conPpto.length;
  const pptoSorted = conPpto.map(r => r.pressupost).sort((a,b)=>a-b);
  const medianPpto = pptoSorted.length ? pptoSorted[Math.floor(pptoSorted.length/2)] : 0;
  const minPpto    = pptoSorted.length ? pptoSorted[0] : 0;
  const maxPpto    = pptoSorted.length ? pptoSorted[pptoSorted.length-1] : 0;
  const sumPpto    = conPpto.reduce((s,r)=>s+r.pressupost,0);

  const ranges = {'< 10K':0,'10K–30K':0,'30K–100K':0,'100K–300K':0,'300K–1M':0,'> 1M':0};
  conPpto.forEach(r => {
    const p = r.pressupost;
    if (p<10000) ranges['< 10K']++;
    else if (p<30000) ranges['10K–30K']++;
    else if (p<100000) ranges['30K–100K']++;
    else if (p<300000) ranges['100K–300K']++;
    else if (p<1000000) ranges['300K–1M']++;
    else ranges['> 1M']++;
  });
  const rangesArr = Object.entries(ranges).filter(([,v])=>v>0);

  // ── Disciplines (incl. neutral "sin disciplina" bucket) ─────────────────
  const byDisc = {}; let sinDisc = 0;
  rows.forEach(r => {
    const ds = r.disciplines || [];
    if (!ds.length) sinDisc++;
    ds.forEach(d => { byDisc[d]=(byDisc[d]||0)+1; });
  });
  const discArr = Object.entries(byDisc).sort((a,b)=>b[1]-a[1]);
  const discEntries = discArr.concat(sinDisc ? [['__none__', sinDisc]] : []);

  // ── Territory ───────────────────────────────────────────────────────────
  const byCCAA = {};
  rows.forEach(r => { if(r.ccaa) byCCAA[r.ccaa]=(byCCAA[r.ccaa]||0)+1; });
  const ccaaArr = Object.entries(byCCAA).sort((a,b)=>b[1]-a[1]);
  const esCount = byCCAA['ES'] || 0;
  const esPct   = pct(esCount, total);

  // ── Submission deadlines (open opportunities only, honest + sparse) ──────
  const openOpps   = rows.filter(r => isOpenOpportunity(r));
  const openWithDl = openOpps.filter(r => { const n = daysTo(r.data_limit); return n !== null && n >= 0; });
  const dlBuckets  = {'≤ 7 días':0,'8–30 días':0,'> 30 días':0};
  openWithDl.forEach(r => { const n = daysTo(r.data_limit); if (n<=7) dlBuckets['≤ 7 días']++; else if (n<=30) dlBuckets['8–30 días']++; else dlBuckets['> 30 días']++; });
  const dlArr = Object.entries(dlBuckets).filter(([,v])=>v>0);

  // ── Documents (link-level coverage only, NOT content extraction) ─────────
  const withDocs  = rows.filter(r => (r.documents||[]).length > 0);
  const totalDocs = withDocs.reduce((s,r)=>s+(r.documents||[]).length, 0);
  const docPct    = pct(withDocs.length, total);

  // ── Tops (descriptive facts about the dataset) ──────────────────────────
  const top5 = conPpto.slice().sort((a,b)=>b.pressupost-a.pressupost).slice(0,5);
  const top5HTML = top5.map(r => {
    const disc = (r.disciplines||[]).map(d=>discTag(d,'8px')).join('') || discNoneTag('8px');
    return `<div class="sv-adj-item" style="flex-wrap:wrap;max-width:100%;gap:4px">
      <div style="flex:1;min-width:160px">
        <div style="font-size:10px;font-weight:700;color:var(--text);line-height:1.35">${esc(r.titol.slice(0,70))}${r.titol.length>70?'…':''}</div>
        <div style="font-size:8.5px;color:var(--text3);margin-top:2px">${esc(r.organisme||'—')}</div>
        <div style="margin-top:3px">${disc}</div>
      </div>
      <div style="font-size:13px;font-weight:700;color:var(--text);white-space:nowrap">${fmt(r.pressupost)}</div>
    </div>`;
  }).join('');

  const byOrg = {};
  rows.forEach(r => { if(r.organisme) byOrg[r.organisme]=(byOrg[r.organisme]||0)+1; });
  const orgArr = Object.entries(byOrg).sort((a,b)=>b[1]-a[1]).slice(0,8);

  // ── Donut (lifecycle classification) ────────────────────────────────────
  const statusSegs = [
    { label:'Sin adjudicar', val:sinAdjudicar, color:'var(--s-ok)'  },
    { label:'Adjudicadas',   val:adjudicadas,  color:'var(--s-adj)' },
    { label:'Desiertas',     val:desiertas,    color:'var(--s-des)' },
  ].filter(s=>s.val>0);
  const donutSegs = statusSegs.map(s => ({ pct: pct(s.val, total), color: s.color }));
  const donutLegend = statusSegs.map(s =>
    `<div class="donut-legend-item">
      <span class="donut-dot" style="background:${s.color}"></span>
      <span>${s.label}</span>
      <span class="donut-pct">${pct(s.val,total)}%</span>
    </div>`
  ).join('');

  // ── Range colors (qualitative, fixed order) ─────────────────────────────
  const rangeColors = ['#6366f1','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444'];

  // ── Assemble HTML ─────────────────────────────────────────────────────
  body.innerHTML = `
    <!-- BIG NUMBERS: dataset overview -->
    <div class="sv-bignums">
      <div class="sv-bignum">
        <div class="sv-bignum-val">${total.toLocaleString('es-ES')}</div>
        <div class="sv-bignum-lbl">Registros canónicos</div>
        <div class="sv-bignum-sub">de ${rawRows.toLocaleString('es-ES')} filas de origen</div>
      </div>
      <div class="sv-bignum">
        <div class="sv-bignum-val" style="color:var(--s-ok)">${sinAdjudicar.toLocaleString('es-ES')}</div>
        <div class="sv-bignum-lbl">Sin adjudicar</div>
        <div class="sv-bignum-sub">clasificación de ciclo de vida</div>
      </div>
      <div class="sv-bignum">
        <div class="sv-bignum-val">${conPpto.length.toLocaleString('es-ES')}</div>
        <div class="sv-bignum-lbl">Con presupuesto</div>
        <div class="sv-bignum-sub">${sinPpto.toLocaleString('es-ES')} sin informar</div>
      </div>
      <div class="sv-bignum">
        <div class="sv-bignum-val">${fmt(medianPpto)}</div>
        <div class="sv-bignum-lbl">Mediana de presupuesto</div>
        <div class="sv-bignum-sub">presupuesto informado</div>
      </div>
    </div>

    <!-- COVERAGE CAVEAT (replaces unsupported insights) -->
    <div class="sv-insight">
      <strong>Cobertura del dataset.</strong> Expedientes de contratación pública (PLACSP · contrataciondelestado.es) detectados con relevancia para diseño y comunicación visual. Las cifras se calculan sobre <strong>registros canónicos</strong> (deduplicados), no sobre filas de origen, y no representan el tamaño total del mercado.
    </div>

    <!-- SECTION: CICLO DE VIDA -->
    <div class="sv-section-title">Ciclo de vida</div>
    <div class="sv-grid">
      <div class="sv-card">
        <div class="sv-card-title">Estado del expediente</div>
        <div class="chart-wrap">
          ${donutSVG(donutSegs)}
          <div class="donut-legend">${donutLegend}</div>
        </div>
        <div class="sv-card-note">«Sin adjudicar» indica que el expediente aún no consta resuelto; no implica que el plazo de presentación siga abierto (ver Plazos de presentación).</div>
      </div>
      ${discBarCard('Distribución por disciplina', discEntries, sinDisc ? `«Sin disciplina» (${sinDisc.toLocaleString('es-ES')}) es un grupo de calidad de datos: expedientes aún sin clasificar.` : '')}
      <div class="sv-card">
        <div class="sv-card-title">Territorios con más registros</div>
        <div class="sv-bars">
          ${ccaaArr.slice(0,10).map(([c,v]) => `<div class="sv-bar-row">
            <div class="sv-bar-label" title="${esc(TERR[c]?.name||c)}">${esc(TERR[c]?.name||c)}</div>
            <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${pct(v,ccaaArr[0][1])}%;background:var(--text)"></div></div>
            <div class="sv-bar-val">${v.toLocaleString('es-ES')}</div>
          </div>`).join('')}
        </div>
        ${esCount ? `<div class="sv-card-note">El ámbito estatal (ES) concentra el ${esPct}% de los registros; la distribución territorial está sesgada hacia licitaciones de ámbito estatal.</div>` : ''}
      </div>
    </div>

    <!-- SECTION: PRESUPUESTO INFORMADO -->
    <div class="sv-section-title">Presupuesto informado</div>
    <div class="sv-grid">
      <div class="sv-card">
        <div class="sv-card-title">Resumen de presupuesto</div>
        <div class="sv-facts">
          <div class="sv-fact"><span class="sv-fact-lbl">Con presupuesto informado</span><span class="sv-fact-val">${conPpto.length.toLocaleString('es-ES')}</span></div>
          <div class="sv-fact"><span class="sv-fact-lbl">Sin presupuesto informado</span><span class="sv-fact-val">${sinPpto.toLocaleString('es-ES')}</span></div>
          <div class="sv-fact"><span class="sv-fact-lbl">Mediana</span><span class="sv-fact-val">${fmt(medianPpto)}</span></div>
          <div class="sv-fact"><span class="sv-fact-lbl">Rango</span><span class="sv-fact-val">${fmt(minPpto)} – ${fmt(maxPpto)}</span></div>
          <div class="sv-fact"><span class="sv-fact-lbl">Suma informada</span><span class="sv-fact-val">${fmt(sumPpto)}</span></div>
        </div>
        <div class="sv-card-note">El presupuesto base de licitación es orientativo. La suma informada no equivale al valor de mercado y excluye ${sinPpto.toLocaleString('es-ES')} registros sin presupuesto.</div>
      </div>
      ${barCard('Distribución por rango', rangesArr, (label) => rangeColors[rangesArr.findIndex(([l])=>l===label)%rangeColors.length])}
      <div class="sv-card">
        <div class="sv-card-title">Mayor presupuesto informado</div>
        ${top5.length ? `<div style="display:flex;flex-direction:column;gap:6px">${top5HTML}</div>` : `<div class="sv-empty">${t('sv_no_data')}</div>`}
      </div>
    </div>

    <!-- SECTION: PLAZOS DE PRESENTACIÓN -->
    <div class="sv-section-title">Plazos de presentación</div>
    <div class="sv-grid">
      <div class="sv-card">
        <div class="sv-card-title">Ventana de presentación vigente</div>
        <div class="sv-facts">
          <div class="sv-fact"><span class="sv-fact-lbl">Abiertas a presentación hoy</span><span class="sv-fact-val">${openOpps.length.toLocaleString('es-ES')}</span></div>
          <div class="sv-fact"><span class="sv-fact-lbl">Con plazo futuro explícito</span><span class="sv-fact-val">${openWithDl.length.toLocaleString('es-ES')}</span></div>
        </div>
        ${dlArr.length ? `<div class="sv-bars" style="margin-top:10px">${dlArr.map(([label,v]) => `<div class="sv-bar-row">
          <div class="sv-bar-label">${label}</div>
          <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${pct(v,openWithDl.length||1)}%;background:var(--s-ok)"></div></div>
          <div class="sv-bar-val">${v.toLocaleString('es-ES')}</div>
        </div>`).join('')}</div>` : ''}
        <div class="sv-card-note">Cifras escasas: el dataset es una instantánea histórica y la mayoría de los plazos ya han vencido o no constan. No interpretar como urgencia.</div>
      </div>
    </div>

    <!-- SECTION: DOCUMENTOS ENLAZADOS -->
    <div class="sv-section-title">Documentos enlazados</div>
    <div class="sv-grid">
      <div class="sv-card">
        <div class="sv-card-title">Cobertura de enlaces</div>
        <div class="sv-facts">
          <div class="sv-fact"><span class="sv-fact-lbl">Registros con documentos enlazados</span><span class="sv-fact-val">${withDocs.length.toLocaleString('es-ES')} (${docPct}%)</span></div>
          <div class="sv-fact"><span class="sv-fact-lbl">Total de documentos enlazados</span><span class="sv-fact-val">${totalDocs.toLocaleString('es-ES')}</span></div>
        </div>
        <div class="sv-card-note">Documentos <strong>enlazados</strong> desde el expediente, no leídos ni analizados. La cobertura de contenido (extracción/DocIntel) no está reflejada en esta cifra.</div>
      </div>
      ${barCard('Organismos con más registros', orgArr, () => 'var(--text)')}
    </div>
  `;
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

  document.addEventListener('adg:langchange', () => { applyI18n(); refreshActiveView(); updateStrip(); updateTicker(); });
  document.addEventListener('adg:themechange', () => { refreshActiveView(); });
  // Re-render as background shards stream in (p200 progressive loader)
  document.addEventListener('adg:dataupdated', () => { refreshActiveView(); updateStrip(); updateTicker(); });

  await loadData();
  updateStrip();
  updateTicker();
  refreshActiveView();
});
})();
