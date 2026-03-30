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

function getRows() {
  let rows = ADG.data;
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

// ── RENDER ────────────────────────────────────────────────────────────────
function render() {
  const rows = getRows();
  const total = rows.length;

  // Summary line
  const sumEl = el('sv-summary');
  if (sumEl) {
    const parts = [];
    if (SV.year)  parts.push(SV.year);
    if (SV.ccaa)  parts.push(TERR[SV.ccaa]?.name || SV.ccaa);
    if (SV.estat) parts.push(SV.estat);
    if (SV.discs.size) parts.push([...SV.discs].map(d=>DISC[d]?.label||d).join(', '));
    const label = parts.length ? `${t('sv_filter_label')}: <strong>${esc(parts.join(' · '))}</strong> — ` : '';
    sumEl.innerHTML = `${label}<strong>${total.toLocaleString('es-ES')}</strong> licitaciones · ${t('sv_of')} <strong>${ADG.data.length.toLocaleString('es-ES')}</strong> totales`;
  }

  const body = el('sv-body');
  if (!body) return;

  if (!total) {
    body.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text3)"><i class="bi bi-funnel" style="font-size:32px;display:block;margin-bottom:10px;opacity:.3"></i><div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase">${t('sv_no_data')}</div></div>`;
    return;
  }

  // ── Compute aggregates ──────────────────────────────────────────────────
  const vigentes   = rows.filter(r => r.estat === 'Vigente').length;
  const adjudicado = rows.filter(r => r.estat === 'Adjudicado').length;
  const desierta   = rows.filter(r => r.estat === 'Desierta').length;
  const volumen    = rows.reduce((s,r) => s+(r.pressupost||0), 0);
  const conPpto    = rows.filter(r=>r.pressupost>0);
  const avgPpto    = conPpto.length ? avg(conPpto.map(r=>r.pressupost)) : 0;
  const tasa_adj   = total ? pct(adjudicado, total) : 0;
  const tasa_des   = total ? pct(desierta, total) : 0;

  // By discipline (count)
  const byDisc = {};
  rows.forEach(r => (r.disciplines||[]).forEach(d => { byDisc[d]=(byDisc[d]||0)+1; }));
  const discArr = Object.entries(byDisc).sort((a,b)=>b[1]-a[1]);

  // By discipline (volume)
  const byDiscVol = {};
  rows.forEach(r => (r.disciplines||[]).forEach(d => { byDiscVol[d]=(byDiscVol[d]||0)+(r.pressupost||0); }));
  const discVolArr = Object.entries(byDiscVol).sort((a,b)=>b[1]-a[1]);

  // By CCAA
  const byCCAA = {};
  rows.forEach(r => { if(r.ccaa) byCCAA[r.ccaa]=(byCCAA[r.ccaa]||0)+1; });
  const ccaaArr = Object.entries(byCCAA).sort((a,b)=>b[1]-a[1]);

  // By CCAA volume
  const byCCAAVol = {};
  rows.forEach(r => { if(r.ccaa) byCCAAVol[r.ccaa]=(byCCAAVol[r.ccaa]||0)+(r.pressupost||0); });
  const ccaaVolArr = Object.entries(byCCAAVol).sort((a,b)=>b[1]-a[1]);

  // By month (last 12)
  const byMonth = {};
  rows.forEach(r => {
    if (r.data_pub) { const m = r.data_pub.slice(0,7); byMonth[m]=(byMonth[m]||0)+1; }
  });
  const monthArr = Object.entries(byMonth).sort((a,b)=>a[0].localeCompare(b[0])).slice(-12);

  // Top adjudicatarios
  const topAdj = {};
  rows.filter(r=>r.adjudicatari).forEach(r => {
    topAdj[r.adjudicatari]=(topAdj[r.adjudicatari]||0)+(r.pressupost||0);
  });
  const adjArr = Object.entries(topAdj).sort((a,b)=>b[1]-a[1]).slice(0,8);

  // Top organismes
  const topOrg = {};
  rows.forEach(r => { if(r.organisme) topOrg[r.organisme]=(topOrg[r.organisme]||0)+(r.pressupost||0); });
  const orgArr = Object.entries(topOrg).sort((a,b)=>b[1]-a[1]).slice(0,8);

  // Budget ranges
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

  // Avg days to deadline by discipline
  const plazos = {};
  const plazosN = {};
  rows.filter(r=>r.data_pub&&r.data_limit).forEach(r => {
    const days = (new Date(r.data_limit)-new Date(r.data_pub))/86400000;
    (r.disciplines||[]).forEach(d => { plazos[d]=(plazos[d]||0)+days; plazosN[d]=(plazosN[d]||0)+1; });
  });
  const plazosArr = Object.entries(plazos).map(([d,s])=>[d,Math.round(s/plazosN[d])]).sort((a,b)=>b[1]-a[1]);

  // ── Color helpers ─────────────────────────────────────────────────────
  const isDark = document.documentElement.getAttribute('data-theme')==='dark';
  const discC  = d => { const c = DISC[d]; return c ? (isDark ? c.ld : c.lc) : 'var(--text)'; };
  const ccaaC  = () => 'var(--text)';
  const rangeColors = ['#6366f1','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444'];
  const statusColors = [
    { label:'Vigente', val:vigentes, color:'var(--s-ok)' },
    { label:'Adjudicado', val:adjudicado, color:'var(--s-adj)' },
    { label:'Desierta', val:desierta, color:'var(--s-des)' },
  ].filter(s=>s.val>0);

  // ── Trend bars (monthly) ──────────────────────────────────────────────
  const maxMonth = Math.max(...monthArr.map(([,v])=>v), 1);
  const trendBars = monthArr.map(([m,v]) =>
    `<div class="trend-bar-col">
      <div class="trend-bar-fill" style="height:${pct(v,maxMonth)}%"></div>
      <div class="trend-bar-lbl">${m.slice(5)}</div>
    </div>`
  ).join('');

  // ── Donut data ────────────────────────────────────────────────────────
  const donutSegs = statusColors.map(s => ({ pct: pct(s.val, total), color: s.color }));
  const donutLegend = statusColors.map(s =>
    `<div class="donut-legend-item">
      <span class="donut-dot" style="background:${s.color}"></span>
      <span>${s.label}</span>
      <span class="donut-pct">${pct(s.val,total)}%</span>
    </div>`
  ).join('');

  // ── Insights ──────────────────────────────────────────────────────────
  const insights = [];
  if (tasa_des >= 30) insights.push({ cls:'warn', text:`<strong>${tasa_des}%</strong> de las licitaciones declaradas desiertas — índice elevado. Puede indicar presupuestos poco realistas o plazos insuficientes.` });
  if (tasa_adj >= 50) insights.push({ cls:'ok', text:`<strong>${tasa_adj}%</strong> de adjudicación — mercado activo con alta resolución.` });
  const topDiscLabel = discArr[0] ? DISC[discArr[0][0]]?.label : null;
  if (topDiscLabel) insights.push({ cls:'', text:`La disciplina con más licitaciones es <strong>${topDiscLabel}</strong> con <strong>${discArr[0][1]}</strong> expedientes.` });

  // ── Top 5 mayor presupuesto ───────────────────────────────────────────
  const top5 = [...rows].filter(r=>r.pressupost>0).sort((a,b)=>b.pressupost-a.pressupost).slice(0,5);
  const top5HTML = top5.map(r => {
    const disc = (r.disciplines||[]).map(d=>discTag(d,'8px')).join('');
    return `<div class="sv-adj-item" style="flex-wrap:wrap;max-width:100%;gap:4px">
      <div style="flex:1;min-width:160px">
        <div style="font-size:10px;font-weight:700;color:var(--text);line-height:1.35">${esc(r.titol.slice(0,70))}${r.titol.length>70?'…':''}</div>
        <div style="font-size:8.5px;color:var(--text3);margin-top:2px">${esc(r.organisme||'—')}</div>
        <div style="margin-top:3px">${disc}</div>
      </div>
      <div style="font-size:13px;font-weight:700;color:var(--text);white-space:nowrap">${fmt(r.pressupost)}</div>
    </div>`;
  }).join('');

  // ── Conditions card ───────────────────────────────────────────────────
  const plazosHTML = plazosArr.slice(0,6).map(([d,days]) => {
    const c = discColor(d);
    return `<div class="sv-bar-row">
      <div class="sv-bar-label">${DISC[d]?.label||d}</div>
      <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${pct(days,plazosArr[0]?.[1]||1)}%;background:${c.text}"></div></div>
      <div class="sv-bar-val">${days}d</div>
    </div>`;
  }).join('');

  // ── Assemble HTML ─────────────────────────────────────────────────────
  body.innerHTML = `
    <!-- BIG NUMBERS -->
    <div class="sv-bignums">
      <div class="sv-bignum">
        <div class="sv-bignum-val">${total.toLocaleString('es-ES')}</div>
        <div class="sv-bignum-lbl">Licitaciones</div>
      </div>
      <div class="sv-bignum">
        <div class="sv-bignum-val" style="color:var(--s-ok)">${vigentes.toLocaleString('es-ES')}</div>
        <div class="sv-bignum-lbl">Vigentes</div>
      </div>
      <div class="sv-bignum">
        <div class="sv-bignum-val">${fmt(volumen)}</div>
        <div class="sv-bignum-lbl">Volumen total</div>
      </div>
      <div class="sv-bignum">
        <div class="sv-bignum-val">${fmt(avgPpto)}</div>
        <div class="sv-bignum-lbl">Presupuesto medio</div>
      </div>
    </div>

    <!-- INSIGHTS -->
    ${insights.map(i=>`<div class="sv-insight ${i.cls}">${i.text}</div>`).join('')}

    <!-- SECTION: VISIÓN GENERAL -->
    <div class="sv-section-title">${t('sv_overview')}</div>
    <div class="sv-grid">
      <!-- Resultado de licitaciones (donut) -->
      <div class="sv-card">
        <div class="sv-card-title">${t('sv_resultado')}</div>
        <div class="chart-wrap">
          ${donutSVG(donutSegs)}
          <div class="donut-legend">${donutLegend}</div>
        </div>
      </div>
      <!-- Evolución mensual -->
      <div class="sv-card">
        <div class="sv-card-title">${t('sv_by_month')}</div>
        ${monthArr.length
          ? `<div class="trend-bars">${trendBars}</div>`
          : `<div class="sv-empty">${t('sv_no_data')}</div>`}
      </div>
      <!-- Rango de presupuesto -->
      ${barCard(t('sv_by_range'), rangesArr, (label,i) => rangeColors[rangesArr.findIndex(([l])=>l===label)%rangeColors.length])}
    </div>

    <!-- SECTION: POR DISCIPLINA -->
    <div class="sv-section-title">${t('sv_by_disc')}</div>
    <div class="sv-grid">
      ${barCard('Licitaciones por disciplina', discArr.map(([d,v])=>[DISC[d]?.label||d,v]), (label) => { const d=Object.keys(DISC).find(k=>DISC[k].label===label); return d?discC(d):'var(--text)'; })}
      ${barCard(t('sv_top_disc_vol'), discVolArr.map(([d,v])=>[DISC[d]?.label||d,v]), (label)=>{ const d=Object.keys(DISC).find(k=>DISC[k].label===label); return d?discC(d):'var(--text)'; }, fmt)}
      ${plazosArr.length ? `<div class="sv-card"><div class="sv-card-title">${t('sv_plazo')}</div><div class="sv-bars">${plazosHTML}</div></div>` : ''}
    </div>

    <!-- SECTION: POR TERRITORIO -->
    <div class="sv-section-title">${t('sv_by_terr')}</div>
    <div class="sv-grid">
      ${barCard('Licitaciones por CCAA', ccaaArr.map(([c,v])=>[TERR[c]?.name||c,v]), ccaaC)}
      ${barCard(t('sv_top_terr'), ccaaVolArr.map(([c,v])=>[TERR[c]?.name||c,v]), ccaaC, fmt)}
    </div>

    <!-- SECTION: TOPS -->
    <div class="sv-section-title">${t('sv_tops')}</div>
    <div class="sv-grid">
      <!-- Top 5 mayor presupuesto -->
      <div class="sv-card" >
        <div class="sv-card-title">${t('sv_top_ppto')}</div>
        ${top5.length ? `<div style="display:flex;flex-direction:column;gap:6px">${top5HTML}</div>` : `<div class="sv-empty">${t('sv_no_data')}</div>`}
      </div>
      <!-- Top organismos por volumen -->
      ${barCard(t('sv_top_orgs_vol'), orgArr, ccaaC, fmt)}
      <!-- Top adjudicatarios -->
      <div class="sv-card">
        <div class="sv-card-title">${t('sv_adj')}</div>
        ${adjArr.length
          ? `<div style="display:flex;flex-direction:column;gap:3px">` +
            adjArr.map(([name,vol]) =>
              `<div class="sv-adj-item">
                <div class="sv-adj-name" title="${esc(name)}">${esc(name)}</div>
                <div class="sv-adj-val">${fmt(vol)}</div>
              </div>`
            ).join('') + `</div>`
          : `<div class="sv-empty">${t('sv_no_adj')}</div>`}
      </div>
    </div>

    <!-- SECTION: CONDICIONES DEL MERCADO -->
    <div class="sv-section-title">${t('sv_conditions')}</div>
    <div class="sv-grid">
      <div class="sv-card">
        <div class="sv-card-title">Tasas de resolución</div>
        <div class="sv-bars">
          <div class="sv-bar-row">
            <div class="sv-bar-label">Tasa adjudicación</div>
            <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${tasa_adj}%;background:var(--s-adj)"></div></div>
            <div class="sv-bar-val">${tasa_adj}%</div>
          </div>
          <div class="sv-bar-row">
            <div class="sv-bar-label">Tasa desierta</div>
            <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${tasa_des}%;background:var(--s-des)"></div></div>
            <div class="sv-bar-val">${tasa_des}%</div>
          </div>
          <div class="sv-bar-row">
            <div class="sv-bar-label">Todavía activas</div>
            <div class="sv-bar-track"><div class="sv-bar-fill" style="width:${pct(vigentes,total)}%;background:var(--s-ok)"></div></div>
            <div class="sv-bar-val">${pct(vigentes,total)}%</div>
          </div>
        </div>
      </div>
      ${barCard(t('sv_budget_disc'), discVolArr.map(([d,v])=>[DISC[d]?.label||d, Math.round(v/(byDisc[d]||1))]), (label)=>{ const d=Object.keys(DISC).find(k=>DISC[k].label===label); return d?discC(d):'var(--text)'; }, fmt)}
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

  await loadData();
  updateStrip();
  updateTicker();
  refreshActiveView();
});
})();
