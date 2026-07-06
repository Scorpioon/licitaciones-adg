/*
 * ADG Plataforma Digital -- directorio.js
 * 0.6.84a -- Jul 2026
 * Role: Directorio de socios renderer. Loads the public static names-only
 *       dataset (data/public/directorio/socios.json) and renders the roster
 *       grouped alphabetically, with a name-only text filter. No contact,
 *       profile or location data; no external network beyond the project's
 *       own static files. No data capture of any kind.
 * Page: directorio.html
 * Depends on: app.js (ADG_Utils), shared.js
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * 0.6.84a Jul 2026  p234a initial build: names-only public mirror of the
 *                   adg-fad.org/socios roster, computed hedged coverage line,
 *                   alphabetical grouping, name filter (LAUS jury filter
 *                   pattern), per-section empty/error states.
 */;(function() {
"use strict";

const { el, initShared, applyI18n, loadJSON } = ADG_Utils;

const DATA_URL = './data/public/directorio/socios.json';

// Loaded dataset (array) — null until boot resolves.
let SOCIOS = null;
let NAME_FILTER = '';

// ── BOOT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  await boot();
  document.addEventListener('adg:langchange', () => applyI18n());
});

async function boot() {
  const socios = await loadJSON(DATA_URL);

  if (!Array.isArray(socios) || !socios.length) {
    showError('No se pudieron cargar los datos del directorio (socios.json).');
    return;
  }
  SOCIOS = socios;

  renderCoverage();
  renderList();

  const input = el('dir-filter');
  if (input) input.addEventListener('input', () => {
    NAME_FILTER = input.value;
    renderList();
  });
}

// ── COVERAGE LINE (computed from data, no fixed claims) ──────────────────
function renderCoverage() {
  const c = el('dir-coverage');
  if (!c) return;
  const persons = SOCIOS.filter(s => s.type === 'person').length;
  const insts   = SOCIOS.length - persons;
  c.textContent =
    SOCIOS.length + ' nombres listados · ' + persons + ' personas · ' +
    insts + ' instituciones (escuelas, estudios) · según adg-fad.org/socios · ' +
    'cobertura según listado disponible en la fuente';
}

// ── LIST (alphabetical groups + name filter) ─────────────────────────────
function renderList() {
  const container = el('dir-list');
  if (!container) return;

  const q = fold(NAME_FILTER.trim());
  const list = !q ? SOCIOS : SOCIOS.filter(s => fold(String(s.name || '')).includes(q));

  if (!list.length) {
    container.innerHTML = '<p class="dir-no-data">Sin coincidencias para el filtro actual.</p>';
    return;
  }

  const grouped = {};
  list.forEach(s => {
    const letter = groupLetter(s.name);
    (grouped[letter] = grouped[letter] || []).push(s);
  });

  let html = '';
  if (q) html += '<p class="dir-filter-count">' + list.length + ' coincidencias</p>';
  Object.keys(grouped).sort().forEach(letter => {
    html += '<div class="dir-group">' +
            '<h3 class="dir-group-title">' + esc(letter) + '</h3>' +
            '<ul class="dir-group-list">';
    grouped[letter].forEach(s => {
      const badge = s.type === 'institution'
        ? ' <span class="dir-type-badge">Institución</span>' : '';
      html += '<li class="dir-item"><span class="dir-name">' + esc(s.name) + '</span>' + badge + '</li>';
    });
    html += '</ul></div>';
  });
  container.innerHTML = html;
}

// First letter of the roster name (surname-first order), accent-folded.
function groupLetter(name) {
  const ch = fold(String(name || '').trim()).charAt(0).toUpperCase();
  return /[A-Z]/.test(ch) ? ch : '#';
}

// Accent-insensitive lowercase fold for filtering/grouping.
function fold(s) {
  return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

// ── ERROR STATE ──────────────────────────────────────────────────────────
function showError(msg) {
  const node = el('dir-list');
  if (node) node.innerHTML =
    '<p class="dir-error">' + esc(msg || 'Error cargando datos.') +
    ' Verifica que los archivos estáticos del proyecto estén accesibles.</p>';
  const c = el('dir-coverage');
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
