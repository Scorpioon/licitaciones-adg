/*
 * ADG Licitaciones — about.js
 * v2.0 — Mar 2026
 * Página: about.html
 * Contiene: fetchChangelog (GitHub API + fallback FALLBACK[]),
 *           VERSION_MAP (detección versión por commit msg),
 *           renderCredit
 *
 * CHANGELOG
 * v2.0  Mar 2026  Changelog en vivo desde GitHub Commits API.
 *                 Fallback estático si API no disponible.
 *                 VERSION_MAP para etiquetar commits con semver.
 * v1.x  Ene–Feb   No existía como página independiente
 */
"use strict";

const { el, applyI18n, updateTicker, initShared, loadData } = ADG_Utils;

const GITHUB_REPO = 'Scorpioon/licitaciones-adg';
const GITHUB_API  = `https://api.github.com/repos/${GITHUB_REPO}/commits?per_page=50`;

// ── VERSION DETECTION (from commit message) ───────────────────────────────
const VERSION_MAP = [
  { match:/v2\.0|multi.p[aá]gina|estadisticas\.html/i,       ver:'v2.0'    },
  { match:/1\.6\.7|MAX_ITEMS.*3000|calvi[àa]/i,              ver:'v1.6.7'  },
  { match:/bootstrap.icon|se[nñ]al[eé]tica.*icon|wip.*foot/i,ver:'v1.5.3'  },
  { match:/cpv.*falso|overlay.*estad|adjudicatar/i,          ver:'v1.5.3'  },
  { match:/1\.4\.1|dark.*light|cpv.*3492/i,                  ver:'v1.4.1'  },
  { match:/badge.*nueva|exportar.*csv|historial.*estado/i,   ver:'v1.4'    },
  { match:/1\.4[^.]|vencen.*semana|compartir.*url/i,         ver:'v1.4'    },
  { match:/cpv.*familia|cpv_valid|falso.*positiv/i,          ver:'v1.3'    },
  { match:/filtro.*ccaa|b[uú]squeda.*adjud|ordenaci/i,       ver:'v1.2'    },
  { match:/dark.mode|ticker|strip.*estadist/i,               ver:'v1.1'    },
  { match:/inicial|first.commit|fetch.*atom|github.action/i, ver:'v1.0'    },
];

// ── CHANGELOG (hardcoded — fuente de verdad del proyecto) ───────────────────
const CHANGELOG = [
  { ver:'v2.0',     date:'11 Mar 2026', text:'Arquitectura multi-página: index (tabla) · estadísticas · about. CSS y JS compartidos via app.js y style.css. Multi-disciplina OR con chips removibles. Panel estadísticas con filtros locales independientes (año/CCAA/estado/disciplina). Paleta de colores por disciplina (light+dark). Semáforo de estados: verde vigente, gris adjudicado, rojo desierta. Fetcher v2.0 con progress bar, sin límite de items, y enriquecimiento. Navegación por tabs entre páginas. Changelog hardcodeado. Fix pprint() default arg. GitHub Actions workflow para actualización diaria.' },
  { ver:'v1.6.7',   date:'Mar 2026', text:'Filtro por año. Estadísticas y condiciones calculadas sobre datos filtrados. Panel Tops: mayores presupuestos, organismos, disciplinas, territorios y adjudicatarios por volumen. Colores por disciplina en todos los gráficos. Fix Calvià → IB. MAX_ITEMS de 500 a 3000.' },
  { ver:'v1.5.3',   date:'Mar 2026', text:'Migración a Bootstrap Icons. i18n completo ES/CA/EU/GL en todos los paneles. Guía de licitaciones para diseñadores con señales de alerta, buenas señales, marco legal LCSP y recursos. Acerca del observatorio con fuentes de datos. Overlay de estadísticas con donut y barras. Fix adjudicatarios con HTML entities. Fix CPV falsos positivos. WIP banner y footer. Señalética icon fix.' },
  { ver:'v1.4.1',   date:'Mar 2026', text:'Fix fila seleccionada en dark/light mode. Fix overlay estadísticas z-index. Adjudicatarios mostrados en panel de detalle. Fix CPV 34928470 mobiliario urbano excluido.' },
  { ver:'v1.4',     date:'Mar 2026', text:'Badge NUEVA en licitaciones recientes. Contador "vencen esta semana". Fecha de última actualización real desde data.json. Exportar resultados filtrados a CSV. Compartir licitación por URL con query param. Vista de estadísticas con bignums y donuts. Campo adjudicatario en datos. Buscador de adjudicatarios. Historial de estados por licitación.' },
  { ver:'v1.3',     date:'Feb 2026', text:'Fix CPV match por familia de 5 dígitos. Filtro CPV_VALID_STARTS para reducir falsos positivos (señalización vial, extintores, etc.).' },
  { ver:'v1.2',     date:'Feb 2026', text:'Filtro por CCAA con selector de provincia/comarca. Búsqueda por adjudicatario. Ordenación por columnas clicables. Paginación configurable (15/20/50/100).' },
  { ver:'v1.1',     date:'Ene 2026', text:'Dark mode con toggle y persistencia. Ticker animado en la cabecera. Stats strip con contadores en vivo. Multilingüe ES/CA/EU/GL con persistencia.' },
  { ver:'v1.0',     date:'Ene 2026', text:'Versión inicial. Fetch de licitaciones desde ATOM de PLACSP. Tabla con filtros por estado y disciplina. Panel de detalle lateral. Scoring por relevancia. GitHub Actions para actualización automática. Datos de muestra como fallback.' },
];

// ── UTILS ─────────────────────────────────────────────────────────────────
function shortDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('es-ES', { day:'2-digit', month:'short', year:'numeric' });
}

function cleanMsg(raw) {
  return (raw || '').split('\n')[0]
    .replace(/^(fix|feat|chore|refactor|style|docs|wip|update|hotfix):\s*/i, '')
    .replace(/^Merge pull request #\d+ from \S+\s*/i, 'Merge: ')
    .trim();
}

function detectVer(msg) {
  for (const { match, ver } of VERSION_MAP) {
    if (match.test(msg)) return ver;
  }
  return null;
}

// ── RENDER ────────────────────────────────────────────────────────────────
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

async function fetchChangelog() {
  // Always render the hardcoded changelog — it's the source of truth
  renderChangelog();
}

function renderCredit() {
  const c = el('credit-line');
  if (c) c.innerHTML = `Hecho con ♥ por <a href="https://www.collapsecreative.com" target="_blank" rel="noopener">Collapse Creative</a> para la <a href="https://adg-fad.org" target="_blank" rel="noopener">ADG-FAD</a> · <a href="https://github.com/scorpioon/licitaciones-adg" target="_blank" rel="noopener">GitHub</a>`;
}

// ── INIT ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  fetchChangelog();
  renderCredit();
  document.addEventListener('adg:langchange', () => {
    applyI18n();
    const gt = el('guide-title');
    if (gt) gt.textContent = ADG_Utils.t('guide_title');
  });
  await loadData();
  updateTicker();
});
