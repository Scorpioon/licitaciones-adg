/*
 * ADG Plataforma Digital -- about.js
 * 0.5.0e -- Jun 2026
 * Role: Changelog rendering, credit line, guide title I18N update.
 *       Phase 6 will expand into full helpdesk/governance page.
 * Page: about.html
 * Depends on: app.js (ADG_Utils, ADG), shared.js (ADG_Shared)
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * 0.5.0e Jun 2026  v0.5.0 series changelog entries added. Version bump.
 * b4.0  Mar 2026  Header updated. Helpdesk expansion pending (Phase 6).
 * v1.0  Mar 2026  Hardcoded changelog, credit line, guide title i18n.
 */;(function() {
"use strict";

const { el, applyI18n, updateTicker, initShared, loadData } = ADG_Utils;

const CHANGELOG = [
  { ver:'v0.5.0e', date:'Jun 2026', text:'Claridad pública UI. Activas primero por defecto. Copia de producción actualizada (sin lenguaje de muestra). Filtro "Sin etiqueta" para licitaciones no clasificadas. Selección de fila más legible. Documentos placeholder para Fetcher 2.' },
  { ver:'v0.5.0d', date:'Jun 2026', text:'Comentarios del workflow de fetch limpiados.' },
  { ver:'v0.5.0c', date:'Jun 2026', text:'Workflow de fetch apunta a main como rama de producción.' },
  { ver:'v0.5.0b', date:'Jun 2026', text:'Dataset de producción Fetcher 1 actualizado: 6095 registros (de 6093 previos). Validación de ciclo de vida pasada.' },
  { ver:'v0.5.0a', date:'Jun 2026', text:'Compatibilidad de envelope de metadatos para candidatos live de Fetcher 1 (normalización top-level meta).' },
  { ver:'v0.5.0',  date:'Jun 2026', text:'Fetcher 2 F2-A iniciado: herramienta de manifest de documentos. Protocolo WRKOPS v1.7 activado (CLAUDE.md).' },
  { ver:'v0.4.6c', date:'May 2026', text:'UI robustecida para campos de ciclo de vida de Fetcher 1: lifecycle_category, active_opportunity_eligible, lifecycle_review_required, badge REVISAR.' },
  { ver:'β3.1',     date:'11 Mar 2026', text:'Fases 3, 4 y 6. Calculadora de Honorarios interactiva (proyecto, experiencia, complejidad, urgencia). Recursos profesionales: plantillas legales + referencias. Mapa Leaflet con licitaciones por CCAA. Barómetro del Sector: informe automático imprimible. Header genérico "ADG-FAD · Plataforma Digital". Navegación ampliada a 6 tabs. i18n nav_recursos + nav_mapa.' },
  { ver:'β3.0',     date:'11 Mar 2026', text:'Fase 0 · Fundación del ecosistema. Nueva home como hub central con cards a cada herramienta y roadmap visual. Renombrado index.html → licitaciones.html. Datos movidos a carpeta data/. Navegación ampliada con tab Inicio. loadJSON genérico en app.js. Preparada la estructura para Laus Tracker, Directorio de Socios, Recursos, Calculadora, Mapa, Bolsa de Prácticas, Barómetro y Alertas.' },
  { ver:'v2.1',     date:'11 Mar 2026', text:'Fix crítico: error "Identifier el already declared" impedía cargar datos en todas las páginas desde la separación multi-página. Todos los JS de página ahora usan IIFE. Changelog hardcodeado. loadData con timeout de seguridad.' },
  { ver:'v2.0',     date:'Mar 2026', text:'Arquitectura multi-página: index (tabla) · estadísticas · about. CSS y JS compartidos via app.js y style.css. Multi-disciplina OR con chips removibles. Panel estadísticas con filtros locales independientes (año/CCAA/estado/disciplina). Paleta de colores por disciplina (light+dark). Semáforo de estados: verde vigente, gris adjudicado, rojo desierta. Fetcher v2.0 con progress bar, sin límite de items, y enriquecimiento. Navegación por tabs entre páginas.' },
  { ver:'v1.6.7',   date:'Mar 2026', text:'Filtro por año. Estadísticas y condiciones calculadas sobre datos filtrados. Panel Tops: mayores presupuestos, organismos, disciplinas, territorios y adjudicatarios por volumen. Colores por disciplina en todos los gráficos. Fix Calvià → IB. MAX_ITEMS de 500 a 3000.' },
  { ver:'v1.5.3',   date:'Mar 2026', text:'Migración a Bootstrap Icons. i18n completo ES/CA/EU/GL en todos los paneles. Guía de licitaciones para diseñadores con señales de alerta, buenas señales, marco legal LCSP y recursos. Acerca del observatorio con fuentes de datos. Overlay de estadísticas con donut y barras. Fix adjudicatarios con HTML entities. Fix CPV falsos positivos. WIP banner y footer.' },
  { ver:'v1.4.1',   date:'Mar 2026', text:'Fix fila seleccionada en dark/light mode. Fix overlay estadísticas z-index. Adjudicatarios mostrados en panel de detalle. Fix CPV 34928470 mobiliario urbano excluido.' },
  { ver:'v1.4',     date:'Mar 2026', text:'Badge NUEVA en licitaciones recientes. Contador "vencen esta semana". Fecha de última actualización real desde data.json. Exportar resultados filtrados a CSV. Compartir licitación por URL con query param. Vista de estadísticas con bignums y donuts. Campo adjudicatario en datos. Buscador de adjudicatarios. Historial de estados por licitación.' },
  { ver:'v1.3',     date:'Feb 2026', text:'Fix CPV match por familia de 5 dígitos. Filtro CPV_VALID_STARTS para reducir falsos positivos (señalización vial, extintores, etc.).' },
  { ver:'v1.2',     date:'Feb 2026', text:'Filtro por CCAA con selector de provincia/comarca. Búsqueda por adjudicatario. Ordenación por columnas clicables. Paginación configurable (15/20/50/100).' },
  { ver:'v1.1',     date:'Ene 2026', text:'Dark mode con toggle y persistencia. Ticker animado en la cabecera. Stats strip con contadores en vivo. Multilingüe ES/CA/EU/GL con persistencia.' },
  { ver:'v1.0',     date:'Ene 2026', text:'Versión inicial. Fetch de licitaciones desde ATOM de PLACSP. Tabla con filtros por estado y disciplina. Panel de detalle lateral. Scoring por relevancia. GitHub Actions para actualización automática. Datos de muestra como fallback.' },
];

function renderChangelog() {
  const list = el('changelog-list');
  if (!list) return;
  list.innerHTML = CHANGELOG.map(c => `
    <div class="changelog-item">
      <div class="cl-ver">${c.ver}</div>
      <div class="cl-date">${c.date}</div>
      <div>${c.text}</div>
    </div>`).join('');
}

function renderCredit() {
  const c = el('credit-line');
  if (c) c.innerHTML = `Hecho con ♥ por <a href="https://www.collapsecreative.com" target="_blank" rel="noopener">Collapse Creative</a> para la <a href="https://adg-fad.org" target="_blank" rel="noopener">ADG-FAD</a> · <a href="https://github.com/scorpioon/licitaciones-adg" target="_blank" rel="noopener">GitHub</a>`;
}

document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  renderChangelog();
  renderCredit();
  document.addEventListener('adg:langchange', () => {
    applyI18n();
    const gt = el('guide-title');
    if (gt) gt.textContent = ADG_Utils.t('guide_title');
  });
  // Re-render ticker count as background shards stream in (p200 progressive loader)
  document.addEventListener('adg:dataupdated', () => updateTicker());
  await loadData();
  updateTicker();
});
})();
