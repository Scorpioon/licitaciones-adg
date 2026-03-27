/*
 * ADG Plataforma Digital -- mapa.js
 * b4.0 -- Mar 2026
 * Role: Interactive territorial map -- Leaflet.js, CCAA centroids,
 *       discipline-coloured circle markers, sidebar list and filters.
 *       Phase 5: I18N pass, estudios toggle, FichaPanel integration.
 * Page: mapa.html
 * Depends on: app.js (ADG_Utils, ADG, DISC, TERR), shared.js (ADG_Shared),
 *             Leaflet.js CDN
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * b4.0  Mar 2026  Header updated. I18N pass and estudios stub pending (Phase 5).
 * v1.0  Mar 2026  F4 initial. Leaflet map with CCAA centroids.
 */;(function() {
"use strict";

const { el, t, fmt, discColor, discTag, stateBadge, applyI18n, initShared, loadData } = ADG_Utils;

// ── CCAA CENTROIDS ───────────────────────────────────────────────────────
const COORDS = {
  AN: [37.39, -4.23], AR: [41.65, -0.88], AS: [43.36, -5.85],
  IB: [39.57, 2.65],  CN: [28.12, -15.43], CB: [43.18, -3.99],
  CM: [39.28, -2.93], CL: [41.65, -4.73], CT: [41.82, 1.47],
  EX: [39.21, -6.16], GA: [42.75, -7.87], RI: [42.29, -2.51],
  MD: [40.42, -3.70], MU: [37.99, -1.13], NA: [42.70, -1.65],
  PV: [42.99, -2.62], VC: [39.47, -0.75], ES: [40.42, -3.70],
};

// ── STATE ────────────────────────────────────────────────────────────────
let map, markers = [];
const MS = { estat: '', discs: new Set() };

function getRows() {
  let rows = ADG.data;
  if (MS.estat) rows = rows.filter(r => r.estat === MS.estat);
  if (MS.discs.size) rows = rows.filter(r => (r.disciplines||[]).some(d => MS.discs.has(d)));
  return rows;
}

// ── INIT MAP ─────────────────────────────────────────────────────────────
function initMap() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const tileUrl = isDark
    ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

  map = L.map('map', {
    center: [40.0, -3.0],
    zoom: 6,
    zoomControl: true,
    attributionControl: false,
  });

  L.tileLayer(tileUrl, { maxZoom: 18 }).addTo(map);
  L.control.attribution({ prefix: false, position: 'bottomright' })
    .addAttribution('© <a href="https://carto.com">CARTO</a> · © <a href="https://osm.org">OSM</a>')
    .addTo(map);
}

// ── RENDER MARKERS ───────────────────────────────────────────────────────
function renderMarkers() {
  // Clear existing
  markers.forEach(m => map.removeLayer(m));
  markers = [];

  const rows = getRows();
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  // Group by CCAA for clustering
  const byCCAA = {};
  rows.forEach(r => {
    const cc = r.ccaa || 'ES';
    if (!byCCAA[cc]) byCCAA[cc] = [];
    byCCAA[cc].push(r);
  });

  Object.entries(byCCAA).forEach(([ccaa, items]) => {
    const coords = COORDS[ccaa];
    if (!coords) return;

    items.forEach((r, i) => {
      // Slight offset to avoid overlap
      const jitter = items.length > 1 ? 0.08 : 0;
      const angle = (i / items.length) * Math.PI * 2;
      const lat = coords[0] + Math.sin(angle) * jitter;
      const lng = coords[1] + Math.cos(angle) * jitter;

      // Color from primary discipline
      const disc = (r.disciplines || [])[0];
      const dc = disc ? DISC[disc] : null;
      const color = dc ? (isDark ? dc.ld : dc.lc) : '#666';

      const stateColor = r.estat === 'Vigente' ? 'var(--s-ok)'
        : r.estat === 'Adjudicado' ? 'var(--s-adj)' : 'var(--s-des)';

      // Custom circle marker
      const marker = L.circleMarker([lat, lng], {
        radius: Math.max(5, Math.min(12, Math.log10((r.pressupost || 1000) + 1) * 2.5)),
        fillColor: color,
        color: '#fff',
        weight: 1.5,
        fillOpacity: 0.85,
      }).addTo(map);

      // Popup
      const discs = (r.disciplines || []).map(d => {
        const dd = DISC[d];
        return dd ? dd.label : d;
      }).join(', ');

      marker.bindPopup(`
        <div style="font-family:var(--f);min-width:200px">
          <div style="font-size:10px;font-weight:700;line-height:1.4;margin-bottom:6px">${esc(r.titol)}</div>
          <div style="font-size:9px;color:#666;margin-bottom:4px">${esc(r.organisme || '—')}</div>
          <div style="font-size:13px;font-weight:700;margin-bottom:6px">${fmt(r.pressupost)}</div>
          <div style="font-size:8px;color:#888;margin-bottom:3px">${discs}</div>
          <div style="font-size:8px;color:#888">${r.estat} · ${r.ccaa || ''}</div>
          ${r.url && r.url.startsWith('http') ? `<a href="${r.url}" target="_blank" rel="noopener" style="display:block;margin-top:6px;font-size:8px;color:#0066cc">Ver en PLACSP ↗</a>` : ''}
        </div>
      `, { maxWidth: 280 });

      markers.push(marker);
    });
  });

  // Update count
  const countEl = el('map-count');
  if (countEl) countEl.textContent = `${rows.length} licitaciones en el mapa`;
}

// ── RENDER SIDEBAR LIST ──────────────────────────────────────────────────
function renderList() {
  const list = el('map-list');
  if (!list) return;
  const rows = getRows().sort((a, b) => (b.pressupost || 0) - (a.pressupost || 0));

  if (!rows.length) {
    list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text3);font-size:10px">Sin resultados</div>';
    return;
  }

  list.innerHTML = rows.slice(0, 50).map(r => {
    const disc = (r.disciplines || [])[0];
    const dc = disc ? discColor(disc) : { text: 'var(--text3)', bg: 'var(--bg2)' };
    return `<div class="map-list-item" data-ccaa="${r.ccaa || 'ES'}">
      <div class="map-list-dot" style="background:${dc.text}"></div>
      <div class="map-list-body">
        <div class="map-list-title">${esc(r.titol.length > 60 ? r.titol.slice(0, 60) + '…' : r.titol)}</div>
        <div class="map-list-meta">${esc(r.organisme || '—')} · ${fmt(r.pressupost)}</div>
      </div>
    </div>`;
  }).join('');

  // Click to fly to CCAA
  list.querySelectorAll('.map-list-item').forEach(item => {
    item.addEventListener('click', () => {
      const cc = item.dataset.ccaa;
      const coords = COORDS[cc];
      if (coords && map) map.flyTo(coords, 8, { duration: 0.8 });
    });
  });
}

// ── RENDER DISC PILLS ────────────────────────────────────────────────────
function renderDiscPills() {
  const wrap = el('map-disc-pills');
  if (!wrap) return;
  wrap.innerHTML = `<button class="pill ${MS.discs.size === 0 ? 'active' : ''}" data-map-disc-all>Todas</button>` +
    Object.entries(DISC).map(([key, d]) =>
      `<button class="pill ${MS.discs.has(key) ? 'active' : ''}" data-map-disc="${key}"><i class="bi ${d.icon}"></i>${d.label}</button>`
    ).join('');
}

// ── BIND EVENTS ──────────────────────────────────────────────────────────
function bindFilters() {
  // Estat
  document.querySelectorAll('[data-map-estat]').forEach(p => {
    p.addEventListener('click', () => {
      MS.estat = p.dataset.mapEstat || '';
      document.querySelectorAll('[data-map-estat]').forEach(b => b.classList.toggle('active', (b.dataset.mapEstat || '') === MS.estat));
      refresh();
    });
  });

  // Discipline pills (delegated since they re-render)
  el('map-disc-pills')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-map-disc]');
    const btnAll = e.target.closest('[data-map-disc-all]');
    if (btnAll) {
      MS.discs.clear();
    } else if (btn) {
      const d = btn.dataset.mapDisc;
      if (MS.discs.has(d)) MS.discs.delete(d); else MS.discs.add(d);
    } else return;
    renderDiscPills();
    // Color active pills
    document.querySelectorAll('[data-map-disc]').forEach(p => {
      const d = p.dataset.mapDisc;
      if (MS.discs.has(d)) {
        const c = discColor(d);
        p.style.background = c.bg; p.style.color = c.text; p.style.borderColor = c.text;
      } else {
        p.style.background = ''; p.style.color = ''; p.style.borderColor = '';
      }
    });
    refresh();
  });
}

function refresh() {
  renderMarkers();
  renderList();
}

// ── ESCAPE ───────────────────────────────────────────────────────────────
function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

// ── INIT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  initMap();
  renderDiscPills();
  bindFilters();

  await loadData();
  refresh();

  document.addEventListener('adg:langchange', () => applyI18n());
  document.addEventListener('adg:themechange', () => {
    // Rebuild map with new tiles
    if (map) map.remove();
    initMap();
    refresh();
  });
});
})();
