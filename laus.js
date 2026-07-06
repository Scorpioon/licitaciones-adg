/*
 * ADG Plataforma Digital -- laus.js
 * 0.6.81 -- Jul 2026
 * Role: Laus Tracker renderer/adapter. Loads public static JSON
 *       (data/public/laus/) and renders editions, categories and jury
 *       per selected year. No data arrays embedded; no external network
 *       beyond the project's own static files.
 * Page: laus.html
 * Depends on: app.js (ADG_Utils), shared.js
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * 0.6.81  Jul 2026  p232 polish: suppress empty stats grid for editions with
 *                   no numeric data (2019/2020/2026), show a single honest
 *                   no-data line instead of four dash cells.
 * 0.6.79b Jul 2026  p228 port from extensions lane (0.1.3.5 laus.js logic)
 *                   rebuilt on current shell conventions: ADG_Utils.loadJSON,
 *                   initShared bootstrap, honest coverage line, jury filter,
 *                   per-section empty/error states.
 */;(function() {
"use strict";

const { el, initShared, applyI18n, loadJSON } = ADG_Utils;

const DATA_BASE = './data/public/laus/';

// Loaded datasets (arrays) — null until boot resolves.
let EDITIONS = null, JURIES = null, CATEGORIES = null;
let ACTIVE_YEAR = null;
let JURY_FILTER = '';

// ── BOOT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  await boot();
  document.addEventListener('adg:langchange', () => applyI18n());
});

async function boot() {
  const [editions, juries, categories] = await Promise.all([
    loadJSON(DATA_BASE + 'editions.json'),
    loadJSON(DATA_BASE + 'juries.json'),
    loadJSON(DATA_BASE + 'categories.json')
  ]);

  if (!Array.isArray(editions) || !editions.length) {
    showError('No se pudieron cargar los datos de ediciones (editions.json).');
    return;
  }
  EDITIONS   = editions;
  JURIES     = Array.isArray(juries) ? juries : [];
  CATEGORIES = Array.isArray(categories) ? categories : [];

  const years = EDITIONS
    .map(e => e.year)
    .filter(y => typeof y === 'number')
    .sort((a, b) => b - a);

  if (!years.length) {
    showError('El dataset de ediciones no contiene años válidos.');
    return;
  }

  ACTIVE_YEAR = years[0];
  renderCoverage();
  renderYearSelector(years);
  renderAll();

  if (!Array.isArray(juries)) {
    const jc = el('laus-jury');
    if (jc) jc.insertAdjacentHTML('beforeend',
      '<p class="laus-error">No se pudieron cargar los datos de jurado (juries.json).</p>');
  }
  if (!Array.isArray(categories)) {
    const cc = el('laus-categories');
    if (cc) cc.insertAdjacentHTML('beforeend',
      '<p class="laus-error">No se pudieron cargar los datos de categorías (categories.json).</p>');
  }
}

// ── COVERAGE LINE (computed from data, no fixed claims) ──────────────────
function renderCoverage() {
  const c = el('laus-coverage');
  if (!c) return;
  const yrs = EDITIONS.map(e => e.year).filter(y => typeof y === 'number');
  const span = yrs.length ? Math.min.apply(null, yrs) + '–' + Math.max.apply(null, yrs) : '—';
  c.textContent =
    EDITIONS.length + ' ediciones disponibles (' + span + ') · ' +
    CATEGORIES.length + ' categorías · ' +
    JURIES.length + ' registros de jurado importados · cobertura según dataset disponible';
}

// ── YEAR SELECTOR ────────────────────────────────────────────────────────
function renderYearSelector(years) {
  const container = el('laus-year-selector');
  if (!container) return;
  container.innerHTML = '';
  years.forEach(year => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = year;
    btn.className = 'laus-year-btn' + (year === ACTIVE_YEAR ? ' laus-year-btn--active' : '');
    btn.setAttribute('aria-pressed', year === ACTIVE_YEAR ? 'true' : 'false');
    btn.addEventListener('click', () => {
      ACTIVE_YEAR = year;
      JURY_FILTER = '';
      container.querySelectorAll('.laus-year-btn').forEach(b => {
        b.classList.toggle('laus-year-btn--active', b === btn);
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      });
      renderAll();
    });
    container.appendChild(btn);
  });
}

// ── PER-YEAR RENDER ──────────────────────────────────────────────────────
function renderAll() {
  const edition   = EDITIONS.find(e => e.year === ACTIVE_YEAR);
  const yearCats  = CATEGORIES.filter(c => c.year === ACTIVE_YEAR);
  renderStats(edition);
  renderCategories(yearCats);
  renderJury();
}

function renderStats(edition) {
  const container = el('laus-stats');
  if (!container) return;
  if (!edition) {
    container.innerHTML = '<p class="laus-no-data">Edición no encontrada en el dataset.</p>';
    return;
  }
  const stats = [
    ['Participantes', edition.participants],
    ['Nacionalidades', edition.nationalities],
    ['Premios otorgados', edition.awards_count],
    ['Asistentes Nit Laus', edition.attendees_nit_laus]
  ];
  const hasAnyStat = stats.some(([, value]) => value !== null && value !== undefined);
  const note = edition.status_note
    ? '<p class="laus-status-note">' + esc(edition.status_note) + '</p>'
    : '';
  const body = hasAnyStat
    ? '<div class="laus-stats-grid">' + stats.map(([label, value]) => statCell(label, value)).join('') + '</div>'
    : '<p class="laus-no-data laus-no-stats">Sin estadísticas numéricas disponibles para esta edición en el dataset.</p>';
  container.innerHTML =
    '<h2 class="laus-edition-title">' + esc(edition.edition_label || ('ADG Laus ' + edition.year)) + '</h2>' +
    note +
    body;
}

function statCell(label, value) {
  const display = (value !== null && value !== undefined) ? esc(value) : '—';
  return '<div class="laus-stat-cell">' +
           '<span class="laus-stat-value">' + display + '</span>' +
           '<span class="laus-stat-label">' + esc(label) + '</span>' +
         '</div>';
}

function renderCategories(yearCats) {
  const container = el('laus-categories');
  if (!container) return;
  if (!yearCats.length) {
    container.innerHTML =
      '<h3 class="laus-section-title">Categorías</h3>' +
      '<p class="laus-no-data">No hay categorías registradas para esta edición en el dataset.</p>';
    return;
  }
  container.innerHTML =
    '<h3 class="laus-section-title">Categorías · ' + yearCats.length + '</h3>' +
    '<ul class="laus-cat-list">' +
    yearCats.map(c => '<li class="laus-cat-item">' + esc(c.label) + '</li>').join('') +
    '</ul>';
}

// ── JURY (grouped by category, with text filter) ─────────────────────────
function renderJury() {
  const container = el('laus-jury');
  if (!container) return;

  const yearJuries = JURIES.filter(j => j.year === ACTIVE_YEAR);

  let html = '<h3 class="laus-section-title">Jurado ' + esc(ACTIVE_YEAR) + '</h3>';

  if (!yearJuries.length) {
    container.innerHTML = html +
      '<p class="laus-no-data">No hay datos de jurado para esta edición en el dataset.</p>';
    return;
  }

  html += '<p class="laus-seed-notice">Jurados importados de fuentes públicas — ' +
          yearJuries.length + ' registros para esta edición. Cobertura según dataset disponible.</p>';
  html += '<div class="laus-jury-filter-wrap">' +
            '<i class="bi bi-search" aria-hidden="true"></i>' +
            '<input id="laus-jury-filter" class="laus-jury-filter" type="search" ' +
              'placeholder="Filtrar por nombre, rol o categoría…" ' +
              'aria-label="Filtrar jurado" value="' + esc(JURY_FILTER) + '">' +
          '</div>' +
          '<div id="laus-jury-groups"></div>';

  container.innerHTML = html;

  const input = el('laus-jury-filter');
  if (input) input.addEventListener('input', () => {
    JURY_FILTER = input.value;
    renderJuryGroups(yearJuries);
  });

  renderJuryGroups(yearJuries);
}

function renderJuryGroups(yearJuries) {
  const target = el('laus-jury-groups');
  if (!target) return;

  const q = JURY_FILTER.trim().toLowerCase();
  const list = !q ? yearJuries : yearJuries.filter(j =>
    String(j.name || '').toLowerCase().includes(q) ||
    String(j.role || '').toLowerCase().includes(q) ||
    String(j.studio_or_context || '').toLowerCase().includes(q) ||
    String(j.category_judged || '').toLowerCase().includes(q)
  );

  if (!list.length) {
    target.innerHTML = '<p class="laus-no-data">Sin coincidencias para el filtro actual.</p>';
    return;
  }

  const grouped = {};
  list.forEach(j => {
    const cat = j.category_judged || 'Sin categoría asignada';
    (grouped[cat] = grouped[cat] || []).push(j);
  });

  let html = '';
  Object.keys(grouped).forEach(cat => {
    html += '<div class="laus-jury-group">' +
            '<h4 class="laus-jury-cat-title">' + esc(cat) + '</h4>' +
            '<ul class="laus-jury-list">';
    grouped[cat].forEach(j => {
      const chair  = j.is_chair === true ? ' <span class="laus-chair-badge">Presidente/a</span>' : '';
      const studio = j.studio_or_context ? ' <span class="laus-jury-studio">— ' + esc(j.studio_or_context) + '</span>' : '';
      html += '<li class="laus-jury-item">' +
                '<span class="laus-jury-name">' + esc(j.name) + '</span>' + chair +
                '<span class="laus-jury-role">' + esc(j.role || '') + studio + '</span>' +
              '</li>';
    });
    html += '</ul></div>';
  });
  target.innerHTML = html;
}

// ── ERROR STATE ──────────────────────────────────────────────────────────
function showError(msg) {
  ['laus-stats', 'laus-categories', 'laus-jury'].forEach(id => {
    const node = el(id);
    if (node) node.innerHTML =
      '<p class="laus-error">' + esc(msg || 'Error cargando datos.') +
      ' Verifica que los archivos estáticos del proyecto estén accesibles.</p>';
  });
  const c = el('laus-coverage');
  if (c) c.textContent = '';
}

// ── ESCAPE ───────────────────────────────────────────────────────────────
function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
})();
