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
  quarter: '',
};

// p207: getRows accepts an explicit source so Estadísticas can run on
// canonical/deduped records while Barómetro (renderBaro) keeps its existing
// raw ADG.data behavior unchanged (Barómetro rebuild is deferred to p208).
function getRows(source) {
  let rows = source || ADG.data;
  if (SV.year)  rows = rows.filter(r => (r.data_pub||'').startsWith(SV.year));
  if (SV.ccaa)  rows = rows.filter(r => r.ccaa === SV.ccaa);
  if (SV.estat) rows = rows.filter(r => r.estat === SV.estat);
  if (SV.discs.size) rows = rows.filter(r => (r.disciplines||[]).some(d => SV.discs.has(d)));
  if (SV.quarter) { var qm=parseInt(SV.quarter,10); rows = rows.filter(function(r){ var m=parseInt((r.data_pub||'0000-00').slice(5,7),10); return Math.ceil(m/3)===qm; }); }
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
function syncQuarter() {
  document.querySelectorAll('[data-sv-quarter]').forEach(function(p) {
    var match = (p.dataset.svQuarter === SV.quarter);
    p.classList.toggle('active', match);
    p.setAttribute('aria-pressed', String(match));
  });
}

function pct(a, b) { return b ? Math.round(a/b*100) : 0; }
function avg(arr) { return arr.length ? arr.reduce((s,v)=>s+v,0)/arr.length : 0; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function quarterLabel(d) { var q=Math.ceil((d.getMonth()+1)/3); return 'Q'+q+' '+d.getFullYear(); }
function monthName(m) { return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][parseInt(m,10)-1]||m; }
function miniBar(items, maxVal, colorFn) {
  if (!items.length) return '';
  var mx=maxVal||Math.max.apply(null,items.map(function(x){return x[1];}).concat([1]));
  return items.map(function(x) {
    var lb=x[0], val=x[1], c=colorFn?colorFn(lb):'var(--text)';
    return '<div class="baro-bar-row">'
      +'<div class="baro-bar-label">'+esc(lb)+'</div>'
      +'<div class="baro-bar-track"><div class="baro-bar-fill" style="width:'+pct(val,mx)+'%;background:'+c+'"></div></div>'
      +'<div class="baro-bar-val">'+(typeof val==='number'&&val>999?fmt(val):val)+'</div>'
      +'</div>';
  }).join('');
}

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
    if (SV.quarter) parts.push('Q'+SV.quarter);
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

// ── INIT ──────────────────────────────────────────────────────────────────
// -- BARO RENDER (absorbed from barometro.js) --------------------------------
function renderBaro() {
  var page=el('baro-page'); if (!page) return;
  var rows=getRows();
  if (!rows.length) {
    page.innerHTML='<div style="text-align:center;padding:60px;color:var(--text3)"><div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase">Sin datos para generar informe</div></div>';
    return;
  }
  var now=new Date(), quarter=quarterLabel(now);
  var reportDate=now.toLocaleDateString('es-ES',{day:'numeric',month:'long',year:'numeric'});
  var isDark=document.documentElement.getAttribute('data-theme')==='dark';
  var discC=function(d){var dd=DISC[d];return dd?(isDark?dd.ld:dd.lc):'var(--text)';};
  var total=rows.length;
  var vigentes=rows.filter(function(r){return r.estat==='Vigente';}).length;
  var adjudicados=rows.filter(function(r){return r.estat==='Adjudicado';}).length;
  var desiertas=rows.filter(function(r){return r.estat==='Desierta';}).length;
  var volumen=rows.reduce(function(s,r){return s+(r.pressupost||0);},0);
  var conPpto=rows.filter(function(r){return r.pressupost>0;});
  var avgPpto=conPpto.length?conPpto.reduce(function(s,r){return s+r.pressupost;},0)/conPpto.length:0;
  var srtd=conPpto.slice().sort(function(a,b){return a.pressupost-b.pressupost;});
  var medianPpto=srtd.length?srtd[Math.floor(srtd.length/2)].pressupost:0;
  var tasaAdj=pct(adjudicados,total), tasaDes=pct(desiertas,total);
  var byDisc={},byDiscVol={};
  rows.forEach(function(r){(r.disciplines||[]).forEach(function(d){byDisc[d]=(byDisc[d]||0)+1;byDiscVol[d]=(byDiscVol[d]||0)+(r.pressupost||0);});});
  var discArr=Object.entries(byDisc).sort(function(a,b){return b[1]-a[1];});
  var discVolArr=Object.entries(byDiscVol).sort(function(a,b){return b[1]-a[1];});
  var byCCAA={};
  rows.forEach(function(r){if(r.ccaa)byCCAA[r.ccaa]=(byCCAA[r.ccaa]||0)+1;});
  var ccaaArr=Object.entries(byCCAA).sort(function(a,b){return b[1]-a[1];});
  var byMonth={};
  rows.forEach(function(r){if(r.data_pub){var m=r.data_pub.slice(0,7);byMonth[m]=(byMonth[m]||0)+1;}});
  var monthArr=Object.entries(byMonth).sort(function(a,b){return a[0].localeCompare(b[0]);}).slice(-6);
  var top5=rows.slice().filter(function(r){return r.pressupost>0;}).sort(function(a,b){return b.pressupost-a.pressupost;}).slice(0,5);
  var trend=null;
  if(monthArr.length>=2){var ml=monthArr[monthArr.length-1][1],mp=monthArr[monthArr.length-2][1];trend={last:ml,prev:mp,diff:pct(ml-mp,mp),up:ml>=mp};}
  var insights=[];
  if(tasaDes>=25)insights.push({cls:'warn',icon:'bi-exclamation-triangle',text:'Tasa desierta '+tasaDes+'% supera el umbral del 25%.'});
  if(tasaAdj>=60)insights.push({cls:'ok',icon:'bi-check-circle',text:'Mercado activo: '+tasaAdj+'% de tasa de adjudicacion.'});
  var topD=discArr[0];
  if(topD)insights.push({cls:'',icon:'bi-palette',text:'Disciplina lider: <strong>'+(DISC[topD[0]]&&DISC[topD[0]].label||topD[0])+'</strong> ('+topD[1]+' licitaciones).'});
  if(trend)insights.push({cls:trend.up?'ok':'warn',icon:trend.up?'bi-graph-up-arrow':'bi-graph-down-arrow',text:'Volumen mensual '+(trend.up?'sube':'baja')+' '+Math.abs(trend.diff)+'% vs mes anterior.'});
  var maxM=Math.max.apply(null,monthArr.map(function(x){return x[1];}).concat([1]));
  var sparks=monthArr.map(function(x){return '<div class="baro-spark-col"><div class="baro-spark-bar" style="height:'+pct(x[1],maxM)+'%"></div><div class="baro-spark-lbl">'+monthName(x[0].split('-')[1])+'</div><div class="baro-spark-val">'+x[1]+'</div></div>';}).join('');
  var dL=function(label){var d=Object.keys(DISC).find(function(k){return DISC[k].label===label;});return d?discC(d):'var(--text)';};
  page.innerHTML=''
    +'<div class="baro-header">'
      +'<div class="baro-header-left">'
        +'<div class="baro-header-eyebrow">Barometro del Sector &middot; ADG-FAD</div>'
        +'<div class="baro-header-title">Informe de Contratacion Publica<br>en Diseno y Comunicacion Visual</div>'
        +'<div class="baro-header-meta">'+quarter+' &middot; Generado el '+reportDate+(ADG.isSample?' &middot; <span style="color:var(--s-warn)">Datos de muestra</span>':'')+'</div>'
      +'</div>'
      +'<div class="baro-header-right"><button class="htbtn" onclick="window.print()"><i class="bi bi-printer"></i><span>Imprimir</span></button></div>'
    +'</div>'
    +'<div class="baro-section-title">Cifras clave</div>'
    +'<div class="baro-bignums">'
      +'<div class="baro-bignum"><div class="baro-bignum-val">'+total+'</div><div class="baro-bignum-lbl">Licitaciones totales</div></div>'
      +'<div class="baro-bignum"><div class="baro-bignum-val" style="color:var(--s-ok)">'+vigentes+'</div><div class="baro-bignum-lbl">Vigentes</div></div>'
      +'<div class="baro-bignum"><div class="baro-bignum-val">'+fmt(volumen)+'</div><div class="baro-bignum-lbl">Volumen total</div></div>'
      +'<div class="baro-bignum"><div class="baro-bignum-val">'+fmt(avgPpto)+'</div><div class="baro-bignum-lbl">Presupuesto medio</div></div>'
      +'<div class="baro-bignum"><div class="baro-bignum-val">'+fmt(medianPpto)+'</div><div class="baro-bignum-lbl">Mediana</div></div>'
      +'<div class="baro-bignum"><div class="baro-bignum-val">'+tasaAdj+'%</div><div class="baro-bignum-lbl">Tasa adjudicacion</div></div>'
    +'</div>'
    +'<div class="baro-section-title">Analisis automatico</div>'
    +'<div class="baro-insights">'+insights.map(function(i){return '<div class="baro-insight '+i.cls+'"><i class="bi '+i.icon+'"></i><div>'+i.text+'</div></div>';}).join('')+'</div>'
    +'<div class="baro-section-title">Evolucion mensual</div>'
    +'<div class="baro-card">'+(monthArr.length?'<div class="baro-sparks">'+sparks+'</div>':'<div style="color:var(--text3);font-size:10px">Sin datos temporales</div>')+'</div>'
    +'<div class="baro-section-title">Desglose por disciplina y territorio</div>'
    +'<div class="baro-grid">'
      +'<div class="baro-card"><div class="baro-card-title">Licitaciones por disciplina</div><div class="baro-bars">'+miniBar(discArr.slice(0,8).map(function(x){return [DISC[x[0]]&&DISC[x[0]].label||x[0],x[1]];}),null,dL)+'</div></div>'
      +'<div class="baro-card"><div class="baro-card-title">Volumen por disciplina</div><div class="baro-bars">'+miniBar(discVolArr.slice(0,8).map(function(x){return [DISC[x[0]]&&DISC[x[0]].label||x[0],x[1]];}),null,dL)+'</div></div>'
      +'<div class="baro-card"><div class="baro-card-title">Licitaciones por CCAA</div><div class="baro-bars">'+miniBar(ccaaArr.slice(0,8).map(function(x){return [TERR[x[0]]&&TERR[x[0]].name||x[0],x[1]];}))+'</div></div>'
      +'<div class="baro-card"><div class="baro-card-title">Resolucion</div><div class="baro-bars">'+miniBar([['Adjudicadas',adjudicados],['Vigentes',vigentes],['Desiertas',desiertas]],total,function(l){return l==='Adjudicadas'?'var(--s-adj)':l==='Vigentes'?'var(--s-ok)':'var(--s-des)';})+'</div></div>'
    +'</div>'
    +'<div class="baro-section-title">Top 5 Mayor presupuesto</div>'
    +'<div class="baro-card">'
      +'<table class="baro-top-table">'
        +'<thead><tr><th>#</th><th>Licitacion</th><th>Organismo</th><th>Presupuesto</th><th>Estado</th></tr></thead>'
        +'<tbody>'+top5.map(function(r,i){return '<tr><td>'+(i+1)+'</td><td>'+esc(r.titol.length>50?r.titol.slice(0,50)+'...':r.titol)+'</td><td>'+esc(r.organisme||'-')+'</td><td style="font-weight:700">'+fmtFull(r.pressupost)+'</td><td>'+r.estat+'</td></tr>';}).join('')+'</tbody>'
      +'</table>'
    +'</div>'
    +'<div class="baro-footer">'
      +'<div>Generado automaticamente &middot; ADG Plataforma &middot; '+reportDate+'</div>'
      +'<div>Fuente: PLACSP &middot; contrataciondelestado.es &middot; Datos '+(ADG.isSample?'de muestra':'reales')+'</div>'
      +'<div style="margin-top:6px"><strong>ADG-FAD</strong> &middot; <a href="https://adg-fad.org" target="_blank" rel="noopener">adg-fad.org</a></div>'
    +'</div>';
}

// -- ACTIVE VIEW REFRESH -- routes render call to current view
function refreshActiveView() {
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
  el('sv-year')?.addEventListener('change', e => { SV.year=e.target.value; refreshActiveView(); });
  el('sv-ccaa')?.addEventListener('change', e => { SV.ccaa=e.target.value; refreshActiveView(); });
  document.querySelectorAll('[data-sv-quarter]').forEach(function(p) {
    p.addEventListener('click', function() {
      SV.quarter = p.dataset.svQuarter; syncQuarter(); refreshActiveView();
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
