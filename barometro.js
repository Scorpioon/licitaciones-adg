/*
 * ADG Plataforma Digital -- barometro.js
 * b4.0 -- Mar 2026
 * Role: Auto-generated sector report -- bignums, discipline/territory
 *       breakdowns, monthly sparklines, top-5 table. Printable format.
 *       NOTE: Will be absorbed into estadisticas.js in Phase 3.
 *       barometro.html will become a redirect tombstone at that point.
 * Page: barometro.html
 * Depends on: app.js (ADG_Utils, ADG, DISC, TERR), shared.js (ADG_Shared)
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * b4.0  Mar 2026  Header updated. Absorption into estadisticas.js pending.
 * v1.0  Mar 2026  F6 initial. Auto-report with bignums, discipline breakdown,
 *                 territorial analysis, market conditions, narrative insights.
 */;(function() {
"use strict";

const { el, t, fmt, fmtFull, discColor, applyI18n, initShared, loadData } = ADG_Utils;

// ── HELPERS ──────────────────────────────────────────────────────────────
function pct(a, b) { return b ? Math.round(a / b * 100) : 0; }
function avg(arr) { return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0; }
function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

function quarterLabel(date) {
  const d = new Date(date);
  const q = Math.ceil((d.getMonth() + 1) / 3);
  return `Q${q} ${d.getFullYear()}`;
}

function monthName(m) {
  const names = { es:['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'] };
  return (names.es || [])[parseInt(m, 10) - 1] || m;
}

// ── SVG MINI CHARTS ──────────────────────────────────────────────────────
function miniBar(items, maxVal, colorFn) {
  if (!items.length) return '';
  const max = maxVal || Math.max(...items.map(([, v]) => v), 1);
  return items.map(([label, val]) => {
    const c = colorFn ? colorFn(label) : 'var(--text)';
    return `<div class="baro-bar-row">
      <div class="baro-bar-label">${esc(label)}</div>
      <div class="baro-bar-track"><div class="baro-bar-fill" style="width:${pct(val, max)}%;background:${c}"></div></div>
      <div class="baro-bar-val">${typeof val === 'number' && val > 999 ? fmt(val) : val}</div>
    </div>`;
  }).join('');
}

// ── RENDER REPORT ────────────────────────────────────────────────────────
function render() {
  const page = el('baro-page');
  if (!page) return;

  const rows = ADG.data;
  if (!rows.length) {
    page.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text3)"><div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase">Sin datos para generar informe</div></div>';
    return;
  }

  const now = new Date();
  const quarter = quarterLabel(now);
  const reportDate = now.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const discC = d => { const dd = DISC[d]; return dd ? (isDark ? dd.ld : dd.lc) : 'var(--text)'; };

  // ── Aggregates ─────────────────────────────────────────────────────────
  const total = rows.length;
  const vigentes = rows.filter(r => r.estat === 'Vigente').length;
  const adjudicados = rows.filter(r => r.estat === 'Adjudicado').length;
  const desiertas = rows.filter(r => r.estat === 'Desierta').length;
  const volumen = rows.reduce((s, r) => s + (r.pressupost || 0), 0);
  const conPpto = rows.filter(r => r.pressupost > 0);
  const avgPpto = conPpto.length ? avg(conPpto.map(r => r.pressupost)) : 0;
  const medianPpto = conPpto.length ? conPpto.sort((a, b) => a.pressupost - b.pressupost)[Math.floor(conPpto.length / 2)].pressupost : 0;
  const tasaAdj = pct(adjudicados, total);
  const tasaDes = pct(desiertas, total);

  // By discipline (count + volume)
  const byDisc = {}, byDiscVol = {};
  rows.forEach(r => (r.disciplines || []).forEach(d => {
    byDisc[d] = (byDisc[d] || 0) + 1;
    byDiscVol[d] = (byDiscVol[d] || 0) + (r.pressupost || 0);
  }));
  const discArr = Object.entries(byDisc).sort((a, b) => b[1] - a[1]);
  const discVolArr = Object.entries(byDiscVol).sort((a, b) => b[1] - a[1]);

  // By CCAA
  const byCCAA = {}, byCCAAVol = {};
  rows.forEach(r => {
    if (r.ccaa) {
      byCCAA[r.ccaa] = (byCCAA[r.ccaa] || 0) + 1;
      byCCAAVol[r.ccaa] = (byCCAAVol[r.ccaa] || 0) + (r.pressupost || 0);
    }
  });
  const ccaaArr = Object.entries(byCCAA).sort((a, b) => b[1] - a[1]);

  // By month
  const byMonth = {};
  rows.forEach(r => {
    if (r.data_pub) { const m = r.data_pub.slice(0, 7); byMonth[m] = (byMonth[m] || 0) + 1; }
  });
  const monthArr = Object.entries(byMonth).sort((a, b) => a[0].localeCompare(b[0])).slice(-6);

  // Top 5 licitaciones
  const top5 = [...rows].filter(r => r.pressupost > 0).sort((a, b) => b.pressupost - a.pressupost).slice(0, 5);

  // Trend (compare last 2 months if possible)
  let trend = null;
  if (monthArr.length >= 2) {
    const last = monthArr[monthArr.length - 1][1];
    const prev = monthArr[monthArr.length - 2][1];
    const diff = pct(last - prev, prev);
    trend = { last, prev, diff, up: last >= prev };
  }

  // ── INSIGHTS ───────────────────────────────────────────────────────────
  const insights = [];
  if (tasaDes >= 25) insights.push({ cls: 'warn', icon: 'bi-exclamation-triangle', text: `La tasa de licitaciones desiertas (${tasaDes}%) supera el 25%. Esto puede indicar presupuestos poco realistas, plazos insuficientes o pliegos excesivamente restrictivos. Recomendamos revisión de las condiciones de contratación.` });
  if (tasaAdj >= 60) insights.push({ cls: 'ok', icon: 'bi-check-circle', text: `Mercado activo: ${tasaAdj}% de tasa de adjudicación. Buen indicador de competencia y resolución de expedientes.` });
  if (avgPpto > 50000) insights.push({ cls: '', icon: 'bi-coin', text: `El presupuesto medio (${fmt(avgPpto)}) indica contratos de tamaño medio-alto. La mediana se sitúa en ${fmt(medianPpto)}, lo que sugiere que los grandes contratos elevan la media.` });
  const topDisc = discArr[0];
  if (topDisc) insights.push({ cls: '', icon: 'bi-palette', text: `La disciplina con más demanda es <strong>${DISC[topDisc[0]]?.label || topDisc[0]}</strong> con ${topDisc[1]} licitaciones. Le siguen ${discArr.slice(1, 3).map(([d]) => DISC[d]?.label || d).join(' y ')}.` });
  if (trend) {
    const dir = trend.up ? 'subido' : 'bajado';
    insights.push({ cls: trend.up ? 'ok' : 'warn', icon: trend.up ? 'bi-graph-up-arrow' : 'bi-graph-down-arrow', text: `El volumen de nuevas licitaciones ha ${dir} un ${Math.abs(trend.diff)}% respecto al mes anterior (${trend.last} vs ${trend.prev}).` });
  }

  // ── Monthly sparkline SVG ──────────────────────────────────────────────
  const maxMonth = Math.max(...monthArr.map(([, v]) => v), 1);
  const sparkBars = monthArr.map(([m, v]) =>
    `<div class="baro-spark-col">
      <div class="baro-spark-bar" style="height:${pct(v, maxMonth)}%"></div>
      <div class="baro-spark-lbl">${monthName(m.split('-')[1])}</div>
      <div class="baro-spark-val">${v}</div>
    </div>`
  ).join('');

  // ── ASSEMBLE ───────────────────────────────────────────────────────────
  page.innerHTML = `
    <!-- REPORT HEADER -->
    <div class="baro-header">
      <div class="baro-header-left">
        <div class="baro-header-eyebrow">Barómetro del Sector · ADG-FAD</div>
        <div class="baro-header-title">Informe de Contratación Pública<br>en Diseño y Comunicación Visual</div>
        <div class="baro-header-meta">${quarter} · Generado el ${reportDate}${ADG.isSample ? ' · <span style="color:var(--s-warn)">Datos de muestra</span>' : ''}</div>
      </div>
      <div class="baro-header-right">
        <button class="htbtn" onclick="window.print()"><i class="bi bi-printer"></i><span>Imprimir</span></button>
      </div>
    </div>

    <!-- KEY FIGURES -->
    <div class="baro-section-title">Cifras clave</div>
    <div class="baro-bignums">
      <div class="baro-bignum"><div class="baro-bignum-val">${total}</div><div class="baro-bignum-lbl">Licitaciones totales</div></div>
      <div class="baro-bignum"><div class="baro-bignum-val" style="color:var(--s-ok)">${vigentes}</div><div class="baro-bignum-lbl">Vigentes</div></div>
      <div class="baro-bignum"><div class="baro-bignum-val">${fmt(volumen)}</div><div class="baro-bignum-lbl">Volumen total</div></div>
      <div class="baro-bignum"><div class="baro-bignum-val">${fmt(avgPpto)}</div><div class="baro-bignum-lbl">Presupuesto medio</div></div>
      <div class="baro-bignum"><div class="baro-bignum-val">${fmt(medianPpto)}</div><div class="baro-bignum-lbl">Mediana</div></div>
      <div class="baro-bignum"><div class="baro-bignum-val">${tasaAdj}%</div><div class="baro-bignum-lbl">Tasa adjudicación</div></div>
    </div>

    <!-- INSIGHTS -->
    <div class="baro-section-title">Análisis automático</div>
    <div class="baro-insights">
      ${insights.map(i => `<div class="baro-insight ${i.cls}"><i class="bi ${i.icon}"></i><div>${i.text}</div></div>`).join('')}
    </div>

    <!-- MONTHLY TREND -->
    <div class="baro-section-title">Evolución mensual</div>
    <div class="baro-card">
      ${monthArr.length ? `<div class="baro-sparks">${sparkBars}</div>` : '<div style="color:var(--text3);font-size:10px">Sin datos temporales</div>'}
    </div>

    <!-- DISCIPLINE + TERRITORY -->
    <div class="baro-section-title">Desglose por disciplina y territorio</div>
    <div class="baro-grid">
      <div class="baro-card">
        <div class="baro-card-title">Licitaciones por disciplina</div>
        <div class="baro-bars">${miniBar(discArr.slice(0, 8).map(([d, v]) => [DISC[d]?.label || d, v]), null, label => { const d = Object.keys(DISC).find(k => DISC[k].label === label); return d ? discC(d) : 'var(--text)'; })}</div>
      </div>
      <div class="baro-card">
        <div class="baro-card-title">Volumen por disciplina</div>
        <div class="baro-bars">${miniBar(discVolArr.slice(0, 8).map(([d, v]) => [DISC[d]?.label || d, v]), null, label => { const d = Object.keys(DISC).find(k => DISC[k].label === label); return d ? discC(d) : 'var(--text)'; })}</div>
      </div>
      <div class="baro-card">
        <div class="baro-card-title">Licitaciones por CCAA</div>
        <div class="baro-bars">${miniBar(ccaaArr.slice(0, 8).map(([c, v]) => [TERR[c]?.name || c, v]))}</div>
      </div>
      <div class="baro-card">
        <div class="baro-card-title">Resolución</div>
        <div class="baro-bars">
          ${miniBar([
            ['Adjudicadas', adjudicados],
            ['Vigentes', vigentes],
            ['Desiertas', desiertas],
          ], total, label => label === 'Adjudicadas' ? 'var(--s-adj)' : label === 'Vigentes' ? 'var(--s-ok)' : 'var(--s-des)')}
        </div>
      </div>
    </div>

    <!-- TOP 5 -->
    <div class="baro-section-title">Top 5 · Mayor presupuesto</div>
    <div class="baro-card">
      <table class="baro-top-table">
        <thead><tr><th>#</th><th>Licitación</th><th>Organismo</th><th>Presupuesto</th><th>Estado</th></tr></thead>
        <tbody>
          ${top5.map((r, i) => `<tr>
            <td>${i + 1}</td>
            <td>${esc(r.titol.length > 50 ? r.titol.slice(0, 50) + '…' : r.titol)}</td>
            <td>${esc(r.organisme || '—')}</td>
            <td style="font-weight:700">${fmtFull(r.pressupost)}</td>
            <td>${r.estat}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>

    <!-- FOOTER -->
    <div class="baro-footer">
      <div>Generado automáticamente por ADG Plataforma · ${reportDate}</div>
      <div>Fuente: PLACSP · contrataciondelestado.es · Datos ${ADG.isSample ? 'de muestra' : 'reales'}</div>
      <div style="margin-top:6px"><strong>ADG-FAD</strong> · Associació de Disseny Gràfic i Comunicació Visual · <a href="https://adg-fad.org" target="_blank" rel="noopener">adg-fad.org</a></div>
    </div>
  `;
}

// ── INIT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  await loadData();
  render();
  document.addEventListener('adg:langchange', () => { applyI18n(); render(); });
  document.addEventListener('adg:themechange', () => render());
});
})();
