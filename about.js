/*
 * ADG Plataforma Digital -- about.js
 * 0.6.88-about -- Jul 2026
 * Role: Public changelog rendering, credit line, guide title I18N update.
 * Page: about.html
 * Depends on: app.js (ADG_Utils, ADG), shared.js (ADG_Shared)
 * Exports: nothing (IIFE)
 *
 * PUBLIC CHANGELOG POLICY
 * - Product-facing history only.
 * - No author names.
 * - No raw/personal commit messages.
 * - No private/local-cleaning lanes.
 * - Extensions branch is remapped into public ADG platform versions v0.5.1-v0.5.45.
 */;(function() {
"use strict";

const { el, applyI18n, updateTicker, initShared, loadData } = ADG_Utils;

const CHANGELOG = [
  { ver:"v0.6.88", date:"Jul 2026", text:"Sincronización de verdad pública: README y changelog alineados con el runtime en vivo; esquema y privacidad del Directorio de socios verificados (652 registros); datos públicos de Laus verificados como UTF-8 estricto, sin corrupción de codificación." },
  { ver:"v0.6.87", date:"Jul 2026", text:"Higiene de código muerto: se retira el index.js residual de raíz (sin uso) y las claves de un antiguo modal de suscripción por email (cero consumidores); se sustituye una acción de descarga de PDF inexistente por un aviso honesto de documento no disponible." },
  { ver:"v0.6.86", date:"Jul 2026", text:"Higiene de plataforma: versión pública, changelog y copy de portada/README alineados con el estado real de cada superficie." },
  { ver:"v0.6.85", date:"Jul 2026", text:"Frescura de datos: los shards públicos se regeneran y validan tras cada actualización programada, incluida la resincronización posterior a cambios en main." },
  { ver:"v0.6.84", date:"Jul 2026", text:"Extensiones: Directorio de socios (solo nombres) y Oportunidades (shell estático, sin captura) pasan a ser superficies públicas; Alertas queda como stub neutral sin ningún flujo de captura." },
  { ver:"v0.6.79 – v0.6.81", date:"Jul 2026", text:"Laus Tracker: se integra el registro de referencia de los premios ADG Laus en la navegación pública y se pulen legibilidad y comportamiento responsive." },
  { ver:"v0.6.59 – v0.6.78", date:"Jun-Jul 2026", text:"Observatorio / Estadísticas: rediseño progresivo del panel analítico (shell, rail de control, gramática visual, barómetro por cuatrimestres, rankings de adjudicatarias) sobre el dataset canónico." },
  { ver:"v0.6.58", date:"Jun 2026", text:"Taxonomía de datos: se aplica una reclasificación controlada de disciplinas y se regeneran los shards públicos del dataset." },
  { ver:"v0.6.57", date:"Jun 2026", text:"Clasificador de disciplinas: se añade un banco de pruebas dry-run para medir cobertura antes de tocar datos de producción." },
  { ver:"v0.6.56", date:"Jun 2026", text:"UI de disciplinas: se añade sistema de color por disciplina y fallback visible para licitaciones sin clasificación." },
  { ver:"v0.6.55", date:"Jun 2026", text:"Panel de detalle: se añade mini-resumen de la licitación y superficie de estado documental." },
  { ver:"v0.6.54", date:"Jun 2026", text:"Rendimiento público: el dataset se divide en shards JSON y la UI carga datos de forma progresiva." },
  { ver:"v0.6.53", date:"Jun 2026", text:"Fetcher 2: se añade extractor de anexos PCAP/PPT para localizar documentación contractual relevante." },
  { ver:"v0.6.52", date:"Jun 2026", text:"Fetcher 2: se añade prueba dirigida de adjuntos feed_xml para mejorar descubrimiento de documentos." },
  { ver:"v0.6.51", date:"Jun 2026", text:"Fetcher 2: se añaden etiquetas y targeting de fuentes documentales para distinguir mejor de dónde viene cada documento." },
  { ver:"v0.6.50", date:"Jun 2026", text:"Fetcher 2: se amplía DocReader y se añade extractor de apéndices para enriquecer la lectura documental." },
  { ver:"v0.6.48", date:"Jun 2026", text:"Fetcher 2: se incorpora prototipo local de DocReader para lectura controlada de documentos." },
  { ver:"v0.6.46", date:"Jun 2026", text:"Arquitectura de fetchers: se documenta la nomenclatura y separación entre capas de descarga, lectura y validación." },
  { ver:"v0.6.44", date:"Jun 2026", text:"Fetcher 1: se añade harness offline de regresión para probar el scheduled fetch sin depender de una ejecución real." },
  { ver:"v0.6.42", date:"Jun 2026", text:"Automatización: se añade reporte machine-readable para cada ejecución programada." },
  { ver:"v0.6.41", date:"Jun 2026", text:"Automatización: los commits de actualización de datos incorporan identidad y estado de ejecución más claros." },
  { ver:"v0.6.40", date:"Jun 2026", text:"Automatización: el estado fail-closed se preserva en el resumen del workflow para evitar falsos positivos." },
  { ver:"v0.6.39b", date:"Jun 2026", text:"Automatización: se endurecen los diagnósticos y resultados de los scheduled runs." },
  { ver:"v0.6.38", date:"Jun 2026", text:"Mobile UI: controles de lista y filtros compactados para mejorar lectura en pantallas pequeñas." },
  { ver:"v0.6.37", date:"Jun 2026", text:"Mobile UI: se endurecen shell, footer y scroll del bottom-sheet de detalle." },
  { ver:"v0.6.36", date:"Jun 2026", text:"Mobile UI: se añade panel de detalle tipo bottom-sheet para consultar licitaciones en móvil." },
  { ver:"v0.6.35", date:"Jun 2026", text:"Panel de detalle: se mejora el scroll interno y la jerarquía canónica de contenido." },
  { ver:"v0.6.34", date:"Jun 2026", text:"Dataset/UI: se colapsan avisos duplicados mediante representante canónico." },
  { ver:"v0.6.32", date:"Jun 2026", text:"Workflow programado: guard runtime robusto ante retrasos del cron." },
  { ver:"v0.6.27", date:"Jun 2026", text:"Fetcher 2 UI: se endurece el renderizado de documentos y las pistas i18n." },
  { ver:"v0.6.21", date:"Jun 2026", text:"Fetcher 2: se aplica append controlado de documentos persistidos al dataset." },
  { ver:"v0.6.20", date:"Jun 2026", text:"Fetcher 2: se añade herramienta protegida para aplicar planes de persistencia documental." },
  { ver:"v0.6.18", date:"Jun 2026", text:"Fetcher 2: se añade planificador dry-run para persistencia documental." },
  { ver:"v0.6.0o", date:"Jun 2026", text:"Fetcher 2: merge gate v3 con soporte para copias enriquecidas." },
  { ver:"v0.6.0m", date:"Jun 2026", text:"Fetcher 2: merge gate v2 consciente de documentos resueltos." },
  { ver:"v0.6.0i", date:"Jun 2026", text:"Fetcher 2B: guard contra reutilización accidental de outputs al reanudar checkpoints." },
  { ver:"v0.6.0g", date:"Jun 2026", text:"Fetcher 2B: soporte de checkpoint para resolución documental por lotes." },
  { ver:"v0.6.0a", date:"Jun 2026", text:"Fetcher 2: se añade resolver documental y merge gate en modo dry-run." },
  { ver:"v0.5.45", date:"Jun 2026", text:"Navegación: se añade inyector global compartido para unificar navegación entre superficies." },
  { ver:"v0.5.44", date:"Jun 2026", text:"LAUS: se ajusta la copia pública del estado hold." },
  { ver:"v0.5.43", date:"Jun 2026", text:"Directorio: se ajusta la copia pública del estado hold." },
  { ver:"v0.5.42", date:"Jun 2026", text:"Home: se alinean los estados de las cards con el estado real de cada módulo." },
  { ver:"v0.5.41", date:"Jun 2026", text:"Navegación: se añade pase de honestidad para reflejar qué superficies están listas y cuáles están en espera." },
  { ver:"v0.5.40", date:"Jun 2026", text:"LAUS: se importan estructuras de jurado 2021-2025." },
  { ver:"v0.5.39", date:"Jun 2026", text:"LAUS: se importa estructura de jurado 2020." },
  { ver:"v0.5.38", date:"Jun 2026", text:"LAUS: se importa estructura de jurado 2019." },
  { ver:"v0.5.37", date:"Jun 2026", text:"Extensiones: se añade contrato de gobernanza para mantener separación entre módulos y datos públicos." },
  { ver:"v0.5.36", date:"May 2026", text:"Directorio: se expone solo la shell padre mientras el contenido detallado queda en espera." },
  { ver:"v0.5.35", date:"May 2026", text:"Sistema: se añade matriz de módulos y overlays." },
  { ver:"v0.5.34", date:"May 2026", text:"Sistema: se añade base compartida para futuras extensiones." },
  { ver:"v0.5.33", date:"May 2026", text:"Rutas: se activan rutas seleccionadas de prehub." },
  { ver:"v0.5.32", date:"May 2026", text:"Estadísticas / Barómetro: se añade shell prehub." },
  { ver:"v0.5.31", date:"May 2026", text:"Recursos: se añade shell prehub." },
  { ver:"v0.5.30", date:"May 2026", text:"Directorio: se amplía la base de mapa y shells de socios." },
  { ver:"v0.5.29", date:"May 2026", text:"Directorio: se añaden prehub y shells de socios." },
  { ver:"v0.5.28", date:"May 2026", text:"LAUS: se añaden superficies prehub y estadísticas." },
  { ver:"v0.5.27", date:"May 2026", text:"Oportunidades: se ajusta layout de tres columnas." },
  { ver:"v0.5.26", date:"May 2026", text:"Prehub: se endurecen cards y se cierra la taxonomía de Mapa." },
  { ver:"v0.5.25", date:"May 2026", text:"Oportunidades: se cierra la capa PREHUB de navegación y estructura." },
  { ver:"v0.5.24", date:"May 2026", text:"Oportunidades: se añaden shells estáticos de Freelancers y Profesional." },
  { ver:"v0.5.23", date:"May 2026", text:"Oportunidades: se cierran decisiones de estructura para Freelancers y Profesional." },
  { ver:"v0.5.22", date:"May 2026", text:"Prehub: se consolida checkpoint de alcance para la capa de extensiones." },
  { ver:"v0.5.21", date:"May 2026", text:"Oportunidades: se añade subsuperficie de Prácticas." },
  { ver:"v0.5.20", date:"May 2026", text:"Home: se activa la card de Oportunidades en el hub." },
  { ver:"v0.5.19", date:"May 2026", text:"Oportunidades: se añade shell prehub." },
  { ver:"v0.5.18", date:"May 2026", text:"Extensiones: se cierra el primer alcance de rama y se consolida el checkpoint de plataforma." },
  { ver:"v0.5.17", date:"May 2026", text:"Seguridad local: se añaden protecciones para evitar exposición de materiales no públicos." },
  { ver:"v0.5.16", date:"May 2026", text:"Directorio: se define el contrato de privacidad de datos antes de exponer información de socios." },
  { ver:"v0.5.15", date:"May 2026", text:"Oportunidades: se define el contrato de proceso para futuras superficies de oportunidades." },
  { ver:"v0.5.14", date:"May 2026", text:"Alertas: se define el contrato de consentimiento y entrega antes de activar notificaciones." },
  { ver:"v0.5.13", date:"May 2026", text:"Home: se añaden IDs estables a las cards del hub." },
  { ver:"v0.5.12", date:"May 2026", text:"Sistema: se documenta el canon de extensiones de la plataforma." },
  { ver:"v0.5.11", date:"May 2026", text:"Sistema: se añade registro de taxonomía de IDs para las extensiones." },
  { ver:"v0.5.10", date:"May 2026", text:"Alertas: se desactiva el formulario dormido dentro de Licitaciones para evitar expectativas falsas." },
  { ver:"v0.5.9", date:"May 2026", text:"Acerca de / Alertas: se ajusta la copia pública de plataforma y el estado de alertas." },
  { ver:"v0.5.8", date:"May 2026", text:"Home: se corrige el canon de rutas de las cards del hub." },
  { ver:"v0.5.7", date:"May 2026", text:"LAUS: se importa estructura de jurado 2017-2018." },
  { ver:"v0.5.6", date:"May 2026", text:"LAUS: se importa estructura de jurado 2016." },
  { ver:"v0.5.5", date:"May 2026", text:"LAUS: se prepara la base de categorías de jurado para importaciones históricas." },
  { ver:"v0.5.4", date:"May 2026", text:"LAUS: se añade shell modular para Laus Tracker." },
  { ver:"v0.5.3", date:"May 2026", text:"Home: se reordena el inicio como hub central de plataforma." },
  { ver:"v0.5.2", date:"May 2026", text:"Navegación: se retira la pestaña provisional ADG+ para mantener una arquitectura pública más clara." },
  { ver:"v0.5.1", date:"May 2026", text:"Extensiones: se añade el hub base para futuras superficies de la plataforma ADG." },
  { ver:"v0.5.0o", date:"Jun 2026", text:"Fetcher 2: se añade herramienta de reporte de quality gate." },
  { ver:"v0.5.0n", date:"Jun 2026", text:"Fetcher 2A: se añade modelo de candidato v2 y hardening del clasificador." },
  { ver:"v0.5.0m", date:"Jun 2026", text:"Fetcher 2A: se endurece el quality gate de descubrimiento documental." },
  { ver:"v0.5.0l", date:"Jun 2026", text:"UI pública: pulido de Zona A y Zona C para mejorar filtros, estado de datos y detalle." },
  { ver:"v0.5.0k", date:"Jun 2026", text:"Zona B: se endurece el mapping entre fila seleccionada y panel de detalle." },
  { ver:"v0.5.0j", date:"Jun 2026", text:"Zona A: se endurecen estado de datos, recencia y señales de actualización." },
  { ver:"v0.5.0i", date:"Jun 2026", text:"Zona C: se endurece el panel de detalle de licitación." },
  { ver:"v0.5.0h", date:"Jun 2026", text:"Fetcher 1: dataset de producción actualizado." },
  { ver:"v0.5.0g", date:"Jun 2026", text:"Zona A: se añade spinner de carga y se unifican filtros duplicados." },
  { ver:"v0.5.0f", date:"Jun 2026", text:"Carga de datos: se amplía el timeout para datasets de producción pesados." },
  { ver:"v0.5.0e", date:"Jun 2026", text:"Claridad pública UI. Activas primero por defecto. Copia de producción actualizada. Filtro Sin etiqueta para licitaciones no clasificadas. Selección de fila más legible. Documentos placeholder para Fetcher 2." },
  { ver:"v0.5.0d", date:"Jun 2026", text:"Workflow de fetch: se limpian comentarios internos para reducir ruido operativo." },
  { ver:"v0.5.0c", date:"Jun 2026", text:"Workflow de fetch: main queda como rama de producción." },
  { ver:"v0.5.0b", date:"Jun 2026", text:"Fetcher 1: dataset de producción actualizado y validación de ciclo de vida pasada." },
  { ver:"v0.5.0a", date:"Jun 2026", text:"Fetcher 1: compatibilidad de envelope de metadatos para candidatos live." },
  { ver:"v0.5.0", date:"Jun 2026", text:"Fetcher 2 F2-A iniciado: herramienta de manifest de documentos y activación de gobernanza operativa." },
  { ver:"v0.4.6c", date:"May 2026", text:"UI robustecida para campos de ciclo de vida de Fetcher 1: categoría, oportunidad activa, revisión requerida y badge REVISAR." },
  { ver:"v0.4.5ar", date:"May 2026", text:"Fetcher 1: helper de scheduled merge y workflow compatible con cambio horario." },
  { ver:"v0.4.5al", date:"May 2026", text:"Fetcher 1: aplicación del dataset de producción." },
  { ver:"v0.4.5z", date:"May 2026", text:"Fetcher 1: corrección de contabilidad del score gate y vistos previos." },
  { ver:"v0.4.5f", date:"May 2026", text:"ContractFolder: integración de merge master v2." },
  { ver:"v0.4.5b", date:"May 2026", text:"ContractFolder: helpers de extracción añadidos." },
  { ver:"v0.4.4v", date:"May 2026", text:"Runtime: limpieza de debug temporal y ajuste de parámetros de caché." },
  { ver:"v0.4.4u", date:"May 2026", text:"Runtime: cache-bust de scripts para asegurar carga de versión correcta." },
  { ver:"v0.4.4t", date:"May 2026", text:"UI: normalización robusta de status pills." },
  { ver:"v0.4.4r", date:"May 2026", text:"Clasificación: backfill de disciplinas mediante enriquecimiento CPV y keywords." },
  { ver:"v0.4.4q", date:"May 2026", text:"Filtros: corrección de semántica del filtro de licitaciones abiertas." },
  { ver:"v0.4.4p", date:"May 2026", text:"Fetcher 1: refresco de delta live tras política de retry." },
  { ver:"v0.4.4o", date:"May 2026", text:"Fetcher 1: política de retry para feeds live." },
  { ver:"v0.4.4n", date:"May 2026", text:"Fetcher 1: detección de ejecuciones parciales y guard contra escritura de producción incompleta." },
  { ver:"v0.4.4m", date:"May 2026", text:"Dataset: refresco de delta live." },
  { ver:"v0.4.4l", date:"May 2026", text:"Panel de detalle: jerarquía interna refinada." },
  { ver:"v0.4.4i", date:"May 2026", text:"Dataset: backfill histórico de licitaciones." },
  { ver:"v0.4.4i+", date:"May 2026", text:"Fetcher: se añade procedencia de estado raw para mejorar trazabilidad." },
  { ver:"v0.4.4g", date:"May 2026", text:"Extractor UBL: corrección de rutas y TypeCode." },
  { ver:"v0.4.4e", date:"May 2026", text:"Fetcher: controles de smoke para telemetría." },
  { ver:"v0.4.4d", date:"May 2026", text:"Fetcher: telemetría de progreso." },
  { ver:"v0.4.4c", date:"May 2026", text:"Fetcher: load_previous pasa a fallo duro si no puede cargar el dataset previo." },
  { ver:"v0.4.3p", date:"May 2026", text:"Alertas: reparación de texto visible." },
  { ver:"v0.4.3n", date:"May 2026", text:"Estadísticas / Barómetro: corrección de scroll." },
  { ver:"v0.4.3m", date:"Apr 2026", text:"Panel de detalle: scroll interno añadido." },
  { ver:"v0.4.3l", date:"Apr 2026", text:"Licitaciones: contrato responsive de shell." },
  { ver:"v0.4.3k", date:"Apr 2026", text:"Runtime: versión visible alineada con la versión real." },
  { ver:"v0.4.3f", date:"Apr 2026", text:"Rail: primera estabilización del comportamiento de rail." },
  { ver:"v0.4.3e", date:"Apr 2026", text:"Desktop shell: fix validado." },
  { ver:"β3.1", date:"11 Mar 2026", text:"Fases 3, 4 y 6. Calculadora de Honorarios interactiva. Recursos profesionales. Mapa Leaflet con licitaciones por CCAA. Barómetro del Sector. Header genérico de plataforma. Navegación ampliada a 6 tabs." },
  { ver:"β3.0", date:"11 Mar 2026", text:"Fase 0: fundación del ecosistema. Nueva home como hub central, licitaciones separadas, datos movidos a carpeta data y estructura preparada para nuevas superficies." },
  { ver:"v2.1", date:"11 Mar 2026", text:"Fix crítico de carga multipágina: todos los JS de página usan IIFE. Changelog hardcodeado y loadData con timeout de seguridad." },
  { ver:"v2.0", date:"Mar 2026", text:"Arquitectura multi-página: licitaciones, estadísticas y acerca de. CSS/JS compartidos, filtros multidisciplina, panel de estadísticas y navegación por tabs." },
  { ver:"v1.6.7", date:"Mar 2026", text:"Filtro por año, estadísticas sobre datos filtrados, panel Tops, colores por disciplina y ampliación de límite de carga." },
  { ver:"v1.5.3", date:"Mar 2026", text:"Bootstrap Icons, i18n ES/CA/EU/GL, guía de licitaciones para diseñadores, fuentes de datos, estadísticas y fixes de adjudicatarios/CPV." },
  { ver:"v1.4.1", date:"Mar 2026", text:"Fix de fila seleccionada en dark/light mode, overlay de estadísticas y CPV excluido por falso positivo." },
  { ver:"v1.4", date:"Mar 2026", text:"Badge NUEVA, contador de vencimientos, export CSV, compartir por URL, estadísticas, adjudicatarios e historial de estados." },
  { ver:"v1.3", date:"Feb 2026", text:"Fix CPV por familia y filtro CPV_VALID_STARTS para reducir falsos positivos." },
  { ver:"v1.2", date:"Feb 2026", text:"Filtro por CCAA, búsqueda por adjudicatario, ordenación por columnas y paginación configurable." },
  { ver:"v1.1", date:"Ene 2026", text:"Dark mode, ticker animado, stats strip y multilingüe persistente." },
  { ver:"v1.0", date:"Ene 2026", text:"Versión inicial: fetch desde ATOM de PLACSP, tabla filtrable, panel de detalle, scoring, GitHub Actions y fallback de datos." },
];

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderChangelog() {
  const list = el("changelog-list");
  if (!list) return;
  list.innerHTML = CHANGELOG.map(c => `
    <div class="changelog-item">
      <div class="cl-ver">${escapeHtml(c.ver)}</div>
      <div class="cl-date">${escapeHtml(c.date)}</div>
      <div>${escapeHtml(c.text)}</div>
    </div>`).join("");
}

function renderCredit() {
  const c = el("credit-line");
  if (c) c.innerHTML = `Hecho con ♥ por <a href="https://www.collapsecreative.com" target="_blank" rel="noopener">Collapse Creative</a> para la <a href="https://adg-fad.org" target="_blank" rel="noopener">ADG-FAD</a> · <a href="https://github.com/scorpioon/licitaciones-adg" target="_blank" rel="noopener">GitHub</a>`;
}

document.addEventListener("DOMContentLoaded", async () => {
  initShared();
  renderChangelog();
  renderCredit();
  document.addEventListener("adg:langchange", () => {
    applyI18n();
    const gt = el("guide-title");
    if (gt) gt.textContent = ADG_Utils.t("guide_title");
  });
  document.addEventListener("adg:dataupdated", () => updateTicker());
  await loadData();
  updateTicker();
});
})();
