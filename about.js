/* ── about.js v2.0 ──────────────────────────────────────────────────────── */
"use strict";

const { el, applyI18n, updateTicker, initShared, loadData } = ADG_Utils;

const CHANGELOG = [
  { ver:'v2.0', date:'Mar 2026', text:'Multi-disciplina con chips removibles. Panel estadísticas con filtros locales independientes. Paleta de colores por disciplina. Semáforo de estados (verde/ámbar/rojo). Acerca de 2 columnas con changelog. i18n completo. Arquitectura multi-página. Fetcher v2.0 con progress bar y sin límite de items.' },
  { ver:'v1.6', date:'Feb 2026', text:'Fix stats cards (grid-column). Etiquetas i18n en tabs Tops y Estadísticas. Ancho etiquetas SV-bar 100→130px. Fix renderStrip i18n.' },
  { ver:'v1.5', date:'Feb 2026', text:'Panel de estadísticas forense. Tab Condiciones con tasas de adjudicación y desierta. Top adjudicatarios.' },
  { ver:'v1.4', date:'Ene 2026', text:'Soporte multi-idioma completo (ES/CA/EU/GL). Selector de comarca/provincia. Paginación con selector de items por página.' },
  { ver:'v1.3', date:'Ene 2026', text:'Panel detalle con historial de estados. Botón notificar por licitación. Compartir URL con estado de detalle.' },
  { ver:'v1.2', date:'Dic 2025', text:'Filtro por territorio (CCAA). Exportación CSV. Búsqueda por adjudicatario. Ordenación multi-columna.' },
  { ver:'v1.1', date:'Dic 2025', text:'Tema oscuro. Ticker animado. Strip de estadísticas globales. Filtros por disciplina y estado.' },
  { ver:'v1.0', date:'Nov 2025', text:'Primera versión pública. Tabla de licitaciones con datos PLACSP. Panel detalle básico. Alertas por email (Formspree).' },
];

function renderChangelog() {
  const list = el('changelog-list');
  if (!list) return;
  list.innerHTML = CHANGELOG.map(c => `
    <div class="changelog-item">
      <div class="cl-ver">${c.ver}</div>
      <div class="cl-date">${c.date}</div>
      <div>${c.text}</div>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  renderChangelog();

  document.addEventListener('adg:langchange', () => {
    applyI18n();
    // Update guide title
    const { t } = ADG_Utils;
    const gt = el('guide-title');
    if (gt) gt.textContent = t('guide_title');
  });

  // Load data just to populate ticker/strip (not required for this page)
  await loadData();
  updateTicker();
});
