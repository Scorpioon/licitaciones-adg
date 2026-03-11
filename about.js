/* ── about.js v2.0 ──────────────────────────────────────────────────────── */
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

// ── FALLBACK changelog (shown when GitHub API unavailable) ─────────────────
const FALLBACK = [
  { ver:'v2.0',     date:'Mar 2026', text:'Arquitectura multi-página (index / estadísticas / about). CSS y JS compartidos. Multi-disciplina con chips removibles. Panel estadísticas con filtros locales independientes. Paleta colores por disciplina. Semáforo estados verde/ámbar/rojo. Changelog en vivo desde GitHub. Fetcher v2.0 con progress bar y sin límite de items.' },
  { ver:'v1.6.7',   date:'Mar 2026', text:'Filtro año. Estadísticas y condiciones sobre datos filtrados. Panel Tops (presupuestos / organismos / disciplinas / territorios / adjudicatarios). Colores por disciplina en gráficos. Fix Calvià → IB. MAX_ITEMS 500 → 3000.' },
  { ver:'v1.5.3',   date:'Mar 2026', text:'Bootstrap Icons. i18n completo. Panel Guía de licitaciones. Panel Acerca de. Overlay de estadísticas. Fix adjudicatarios. Fix CPV falsos positivos. WIP footer. Señalética icon fix.' },
  { ver:'v1.4.1',   date:'Mar 2026', text:'Fix fila seleccionada dark/light. Fix overlay estadísticas. Adjudicatarios en panel. Fix CPV 34928470 mobiliario urbano.' },
  { ver:'v1.4',     date:'Mar 2026', text:'Badge NUEVA. Contador "vencen esta semana". Fecha de última actualización real. Exportar CSV. Compartir licitación por URL. Vista estadísticas. Campo adjudicatario. Buscador adjudicatarios. Historial de estados.' },
  { ver:'v1.3',     date:'Feb 2026', text:'Fix CPV match por familia de 5 dígitos. Filtro CPV_VALID_STARTS. Reducción de falsos positivos.' },
  { ver:'v1.0–1.2', date:'Ene–Feb 2026', text:'Versión inicial: fetch PLACSP Atom, tabla con filtros, panel detalle, dark mode, multilingüe, GitHub Actions.' },
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
function renderFallback() {
  const list = el('changelog-list');
  if (!list) return;
  list.innerHTML = FALLBACK.map(c => `
    <div class="changelog-item">
      <div class="cl-ver">${c.ver}</div>
      <div class="cl-date">${c.date}</div>
      <div>${c.text}</div>
    </div>`).join('');
}

async function fetchChangelog() {
  const list = el('changelog-list');
  if (!list) return;
  list.innerHTML = `<div style="font-size:10px;color:var(--text3);padding:6px 0">Cargando historial…</div>`;

  try {
    const res = await fetch(GITHUB_API, { headers:{ Accept:'application/vnd.github.v3+json' } });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const commits = await res.json();
    if (!Array.isArray(commits) || !commits.length) throw new Error('empty');

    // Detect known versions; fill gaps with minor bumps off the last known
    let currentBase = 'v2.0';
    let minorIdx = 0;

    const rows = commits.map(c => {
      const raw = c.commit?.message || '';
      const known = detectVer(raw);
      if (known) { currentBase = known; minorIdx = 0; return { c, label: known }; }
      minorIdx++;
      return { c, label: `${currentBase}.${minorIdx}` };
    });

    list.innerHTML = rows.map(({ c, label }) => {
      const date = shortDate(c.commit?.committer?.date || c.commit?.author?.date);
      const url  = c.html_url || '#';
      const sha  = (c.sha||'').slice(0,7);
      const msg  = cleanMsg(c.commit?.message);
      return `<div class="changelog-item">
        <div class="cl-ver">${label}</div>
        <div class="cl-date">${date}</div>
        <div style="flex:1;min-width:0">${msg} <a href="${url}" target="_blank" rel="noopener" style="margin-left:4px;font-size:8px;color:var(--text3);border-bottom:1px solid var(--border3);font-family:monospace">${sha}</a></div>
      </div>`;
    }).join('');

  } catch(e) {
    console.warn('[ADG] GitHub changelog unavailable:', e.message);
    renderFallback();
  }
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
