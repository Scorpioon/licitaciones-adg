/*
 * ADG Plataforma Digital -- licitaciones.js
 * 0.5.0g -- Jun 2026
 * Role: Main procurement table -- state, filtering, sorting, detail panel,
 *       pagination, CSV export, URL sharing, bell subscriptions.
 * Page: licitaciones.html
 * Depends on: app.js (ADG_Utils, ADG, DISC, TERR), shared.js (ADG_Shared)
 * Exports: nothing (IIFE)
 *
 * CHANGELOG (newest first)
 * 0.5.0k Jun 2026  Zone B hardening: stable rowKey for exact detail mapping, fix duplicate-ID
 *                  collision in openDetail, lifecycle variant badge, selectedKey replaces
 *                  selectedId to prevent cross-duplicate selection.
 * 0.5.0j Jun 2026  Zone A hardening: default sort to data_pub desc, consistent 3-day recent
 *                  window for nuevasHoy filter and s-new KPI, clean loading UX deduplication,
 *                  sync sort-sel dropdown to initial state.
 * 0.5.0g Jun 2026  Loading spinner before fetch. Remove duplicate active-filter chips for pills.
 * 0.5.0e Jun 2026  Active-first default (soloActivas=true). Sin etiqueta discipline filter.
 *                   REVISAR badge icon. Version bump.
 * 0.4.4v May 2026  Removed temporary ADG_LIC_DEBUG export after status filter runtime validation.
 * 0.4.4t May 2026  Harden status filter key normalization and status pill active-state sync.
 * 0.4.4q May 2026  Runtime status keys: getDisplayStatus/isOpenOpportunity/stateBadgeRow.
 *                   Honest filter, sort tier, and chip color using canonical lowercase keys.
 * b4.0  Mar 2026  Header updated. Stale copy string fixed.
 *                 Phase 2: FichaPanel wired. Status-tier sort. openDetail/closeDetail replaced.
 * v2.1  Mar 2026  IIFE wrap -- fix 'el' already declared.
 * v2.0  Mar 2026  Multi-disciplina OR logic. Active filter chips.
 * v1.x  Ene-Feb   Embebido en index.html
 */;(function() {
"use strict";

const { el, t, fmt, fmtFull, daysTo, isNew, discColor, discTag, stateBadge,
        getDisplayStatus, isOpenOpportunity, stateBadgeRow,
        applyI18n, updateStrip, updateTicker, initShared, initModal, loadData } = ADG_Utils;

// ── STATE ─────────────────────────────────────────────────────────────────
const S = {
  discs:   new Set(),   // selected disciplines (empty = all)
  estat:   '',
  ccaa:    '',
  comarca: '',
  year:    '',
  query:   '',
  adjQ:    '',
  sortCol: 'data_pub',
  sortDir: 'desc',
  page:    1,
  perPage: 20,
  selectedKey: null,
  soloActivas: true,
  nuevasHoy:   false,
};

// ── ROW KEY MAP (rebuilt on each render) ──────────────────────────────────
let ROW_BY_KEY = {};

// ── DISPLAY HELPERS ───────────────────────────────────────────────────────
function capFirst(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function todayLocalISO() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// ── ROW KEY ───────────────────────────────────────────────────────────────
function rowKey(r, idx) {
  return r.id + '|' + (r.estat_raw || r.estat || '') + '|' + (r.data_pub || '') + '|' + idx;
}

// ── STATUS KEY NORMALIZATION ───────────────────────────────────────────────
function normalizeStatusKey(value) {
  const v = String(value || '').trim().toLowerCase();
  if (!v) return '';
  if (v === 'vigente') return 'open';
  if (v === 'abiertas' || v === 'abierta') return 'open';
  if (v === 'adjudicado') return 'adjudicado';
  if (v === 'desierta') return 'desierta';
  return v;
}

// ── FILTERING ─────────────────────────────────────────────────────────────
function getFiltered() {
  let rows = ADG.canonicalData || ADG.data;
  const statusKey = normalizeStatusKey(S.estat);
  if (statusKey) rows = rows.filter(r => getDisplayStatus(r).key === statusKey);
  if (S.soloActivas) rows = rows.filter(r => r.active_opportunity_eligible === true);
  if (S.ccaa)    rows = rows.filter(r => r.ccaa === S.ccaa);
  if (S.year)    rows = rows.filter(r => (r.data_pub||'').startsWith(S.year));
  if (S.discs.size) {
    const noTag = S.discs.has('__none__');
    const tagged = new Set([...S.discs].filter(d => d !== '__none__'));
    rows = rows.filter(r => {
      const discs = r.disciplines || [];
      if (noTag && discs.length === 0) return true;
      return tagged.size > 0 && discs.some(d => tagged.has(d));
    });
  }
  if (S.nuevasHoy) {
    rows = rows.filter(r => isNew(r));
  }
  if (S.query) {
    const q = S.query.toLowerCase();
    rows = rows.filter(r =>
      (r.titol||'').toLowerCase().includes(q) ||
      (r.organisme||'').toLowerCase().includes(q) ||
      (r.kw||[]).some(k => k.toLowerCase().includes(q))
    );
  }
  if (S.adjQ) {
    const q = S.adjQ.toLowerCase();
    rows = rows.filter(r => (r.adjudicatari||'').toLowerCase().includes(q));
  }
  return rows;
}

function getSorted(rows) {
  var statusTier = function(r) { return isOpenOpportunity(r) ? 0 : 1; };
  return [...rows].sort((a,b) => {
    var ta = statusTier(a), tb = statusTier(b);
    if (ta !== tb) return ta - tb;
    let va = a[S.sortCol], vb = b[S.sortCol];
    if (va == null) va = S.sortDir === 'asc' ? Infinity : -Infinity;
    if (vb == null) vb = S.sortDir === 'asc' ? Infinity : -Infinity;
    if (typeof va === 'string') return S.sortDir === 'asc' ? va.localeCompare(vb,'es') : vb.localeCompare(va,'es');
    return S.sortDir === 'asc' ? va - vb : vb - va;
  });
}

// ── RENDER TABLE ──────────────────────────────────────────────────────────
function render() {
  const filtered = getSorted(getFiltered());
  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / S.perPage));
  S.page = Math.min(S.page, pages);
  const slice = filtered.slice((S.page-1)*S.perPage, S.page*S.perPage);

  // Count
  const cEl = el('count');
  if (cEl) cEl.innerHTML = `<strong>${total.toLocaleString('es-ES')}</strong> RESULTADOS`;

  // Empty
  const emptyEl = el('empty');
  const tableEl = el('main-table');
  if (emptyEl) emptyEl.style.display = slice.length ? 'none' : 'block';
  if (tableEl) tableEl.style.display = slice.length ? '' : 'none';

  // Rows — stable keys for exact detail mapping
  const pageOffset = (S.page-1)*S.perPage;
  const idCounts = {};
  ADG.data.forEach(r => { idCounts[r.id] = (idCounts[r.id]||0)+1; });
  ROW_BY_KEY = {};
  slice.forEach((r, i) => { const k = rowKey(r, pageOffset+i); ROW_BY_KEY[k] = r; });

  const tbody = el('tbody');
  if (!tbody) return;
  tbody.innerHTML = slice.map((r, i) => rowHTML(r, rowKey(r, pageOffset+i), idCounts[r.id]||1)).join('');

  // Click on row — rowKey for exact record; data-id retained for bell/subscription
  tbody.querySelectorAll('tr[data-row-key]').forEach(tr => {
    tr.addEventListener('click', e => {
      if (e.target.closest('.bell-btn')) return;
      openDetailByKey(tr.dataset.rowKey);
    });
    const bb = tr.querySelector('.bell-btn');
    if (bb) bb.addEventListener('click', e => { e.stopPropagation(); toggleBell(tr.dataset.id, bb); });
  });

  // Pagination
  renderPagination(total, pages);

  // Sort arrows
  document.querySelectorAll('th[data-col]').forEach(th => {
    th.classList.toggle('sorted', th.dataset.col === S.sortCol);
    const arrow = th.querySelector('.sort-arrow');
    if (arrow) arrow.textContent = th.dataset.col === S.sortCol ? (S.sortDir === 'asc' ? '↑' : '↓') : '↕';
  });

  // Active filter chips
  renderFilterChips();
}

function rowHTML(r, key, dupCount) {
  const days = daysTo(r.data_limit);
  const dateClass = days !== null && days >= 0 && days <= 7 ? 'date-warn' : (days !== null && days > 7 ? 'date-ok' : '');
  const dateStr = r.data_limit ? new Date(r.data_limit).toLocaleDateString(ADG.lang+'-ES',{day:'2-digit',month:'short',year:'2-digit'}) : '—';
  const pubStr  = r.data_pub  ? new Date(r.data_pub + 'T00:00:00').toLocaleDateString(ADG.lang+'-ES',{day:'2-digit',month:'short',year:'2-digit'}) : '—';
  const tags = (r.disciplines||[]).map(d => discTag(d)).join('');
  const newBadge        = isNew(r) ? `<span class="badge-new">${t('nueva')}</span>` : '';
  const reviewBadge     = r.lifecycle_review_required === true ? `<span class="badge-review"><i class="bi bi-exclamation-triangle" style="font-size:6px;margin-right:2px"></i>Revisar</span>` : '';
  const multiStateBadge = dupCount > 1 ? `<span class="badge-states" title="${dupCount} estados registrados">${dupCount}&nbsp;est.</span>` : '';
  const bellClass = isSubscribed(r.id) ? 'subscribed' : '';
  const isSel = key === S.selectedKey;

  return `<tr data-row-key="${esc(key)}" data-id="${esc(r.id)}" class="${isSel?'sel':''}" tabindex="0">
    <td>
      <div class="tc-name">${esc(capFirst(r.titol))}${newBadge}${reviewBadge}${multiStateBadge}</div>
      <div class="tc-tags">${tags}</div>
    </td>
    <td>
      <div class="tc-org-name">${esc(r.organisme||'—')}</div>
      <div class="tc-org-sub">${r.lloc||''} ${r.ccaa ? '·&nbsp;'+r.ccaa : ''}</div>
    </td>
    <td>
      <div class="tc-amt">${fmt(r.pressupost)}</div>
      <div class="tc-amt-sub">${r.tipus||''}</div>
    </td>
    <td>
      <div class="rel-wrap">
        <div class="rel-bg"><div class="rel-fill" style="width:${r.rellevancia||0}%"></div></div>
        <span class="rel-num">${r.rellevancia||0}</span>
      </div>
    </td>
    <td>${stateBadgeRow(r)}</td>
    <td><div class="tc-date ${dateClass}">${dateStr}</div></td>
    <td><div class="tc-date">${pubStr}</div></td>
    <td class="tc-bell"><button class="bell-btn ${bellClass}" aria-label="Notificación"><i class="bi bi-bell${bellClass?'-fill':''}"></i></button></td>
  </tr>`;
}

// ── DETAIL PANEL ──────────────────────────────────────────────────────────
function openDetailByKey(key) {
  var r = ROW_BY_KEY[key];
  if (!r) return;
  S.selectedKey = key;
  document.querySelectorAll('tbody tr').forEach(function(tr) {
    tr.classList.toggle('sel', tr.dataset.rowKey === key);
  });
  ADG_Shared.FichaPanel(r, {
    container: el('detail'),
    onClose: closeDetail
  });
  updateURL(r.id);
}

function openDetail(id) {
  // URL restore path — find first visible row matching id, else fall back to canonical data
  var key = Object.keys(ROW_BY_KEY).find(function(k) { return ROW_BY_KEY[k].id === id; });
  if (key) { openDetailByKey(key); return; }
  var r = (ADG.canonicalData || ADG.data).find(function(x) { return x.id === id; });
  if (!r) return;
  ADG_Shared.FichaPanel(r, {
    container: el('detail'),
    onClose: closeDetail
  });
  updateURL(id);
}

function closeDetail() {
  S.selectedKey = null;
  ADG_Shared.FichaClose(el('detail'));
  document.querySelectorAll('tbody tr').forEach(function(tr) { tr.classList.remove('sel'); });
  clearURL();
}

// ── PAGINATION ────────────────────────────────────────────────────────────
function renderPagination(total, pages) {
  const bar = el('pagination-bar');
  if (!bar) return;
  bar.style.display = total > S.perPage ? '' : 'none';

  const info = el('pg-info');
  if (info) {
    const from = (S.page-1)*S.perPage+1, to = Math.min(S.page*S.perPage, total);
    info.textContent = `${from}–${to} de ${total}`;
  }

  const pgs = el('pg-pages');
  if (!pgs) return;
  const btns = [];
  const addBtn = (label, page, active=false, disabled=false) => {
    btns.push(`<button class="pg-btn${active?' pg-active':''}" data-page="${page}" ${disabled?'disabled':''}>${label}</button>`);
  };

  addBtn('‹', S.page-1, false, S.page<=1);
  if (pages <= 7) {
    for (let i=1;i<=pages;i++) addBtn(i, i, i===S.page);
  } else {
    addBtn(1, 1, S.page===1);
    if (S.page > 3) btns.push(`<span class="pg-ellipsis">…</span>`);
    for (let i=Math.max(2,S.page-1); i<=Math.min(pages-1,S.page+1); i++) addBtn(i,i,i===S.page);
    if (S.page < pages-2) btns.push(`<span class="pg-ellipsis">…</span>`);
    addBtn(pages, pages, S.page===pages);
  }
  addBtn('›', S.page+1, false, S.page>=pages);

  pgs.innerHTML = btns.join('');
  pgs.querySelectorAll('.pg-btn:not([disabled])').forEach(b => {
    b.addEventListener('click', () => { S.page = +b.dataset.page; render(); });
  });
}

// ── FILTER CHIPS BAR ──────────────────────────────────────────────────────
function renderFilterChips() {
  const bar = el('active-filters-bar');
  if (!bar) return;
  const chips = [];

  // Only show chips for dropdown filters (CCAA, year) — pill-based filters
  // (status, soloActivas, nuevasHoy, disciplines) already show selected state in Zone A.
  if (S.ccaa) {
    chips.push({ label: TERR[S.ccaa]?.name || S.ccaa, color: 'var(--text)', onX: () => { S.ccaa=''; el('sel-ccaa').value=''; el('comarca-group').style.display='none'; render(); } });
  }

  if (S.year) {
    chips.push({ label: S.year, color: 'var(--text)', onX: () => { S.year=''; el('sel-year').value=''; render(); } });
  }

  if (!chips.length) { bar.classList.remove('visible'); return; }
  bar.classList.add('visible');
  bar.innerHTML = `<span class="af-lbl">Filtros activos</span>` +
    chips.map((chip,i) =>
      `<span class="af-chip" style="color:${chip.color};border-color:${chip.color}33;background:${chip.bg||chip.color+'11'}">
        ${esc(chip.label)}<button class="af-chip-x" data-chip="${i}" style="color:${chip.color}">✕</button>
      </span>`
    ).join('') +
    `<button class="clear-all-btn" id="clear-all">Limpiar todo</button>`;

  chips.forEach((chip,i) => {
    bar.querySelector(`[data-chip="${i}"]`)?.addEventListener('click', chip.onX);
  });
  bar.querySelector('#clear-all')?.addEventListener('click', clearAll);
}

function clearAll() {
  S.estat=''; S.ccaa=''; S.year=''; S.discs.clear(); S.query=''; S.adjQ=''; S.page=1;
  S.soloActivas = false; S.nuevasHoy = false;
  el('sel-ccaa').value=''; el('sel-year').value='';
  el('comarca-group').style.display='none';
  el('search').value=''; el('adj-search').value='';
  el('pill-solo-activas')?.classList.remove('active');
  el('sstat-new')?.classList.remove('active');
  syncPills('[data-estat]'); syncDiscPills();
  render();
}

// ── PILL SYNC ─────────────────────────────────────────────────────────────
function syncPills(selector) {
  document.querySelectorAll(selector).forEach(p => {
    if (selector === '[data-estat]') {
      const current = normalizeStatusKey(S.estat);
      const candidate = normalizeStatusKey(p.dataset.estat);
      const active = candidate === current;
      p.classList.toggle('active', active);
      p.setAttribute('aria-pressed', active);
      return;
    }
    const val = p.dataset.estat ?? '';
    p.classList.toggle('active', val === S.estat);
    p.setAttribute('aria-pressed', val === S.estat);
  });
}

function syncDiscPills() {
  const allBtn = el('pill-all-disc');
  const none = S.discs.size === 0;
  if (allBtn) { allBtn.classList.toggle('active', none); allBtn.setAttribute('aria-pressed', none); }
  document.querySelectorAll('[data-disc]').forEach(p => {
    const d = p.dataset.disc;
    const active = S.discs.has(d);
    p.classList.toggle('active', active);
    p.setAttribute('aria-pressed', active);
    if (active) {
      const c = discColor(d);
      p.style.background = c.bg;
      p.style.color = c.text;
      p.style.borderColor = c.text;
    } else {
      p.style.background = '';
      p.style.color = '';
      p.style.borderColor = '';
    }
  });
}

// ── URL STATE ─────────────────────────────────────────────────────────────
function updateURL(id) {
  const url = new URL(location.href);
  url.searchParams.set('id', id);
  history.replaceState({}, '', url);
}
function clearURL() {
  const url = new URL(location.href);
  url.searchParams.delete('id');
  history.replaceState({}, '', url);
}
function checkURL() {
  const id = new URLSearchParams(location.search).get('id');
  if (id) openDetail(id);
}

// ── SUBSCRIPTIONS (localStorage) ─────────────────────────────────────────
function isSubscribed(id) {
  try { return JSON.parse(localStorage.getItem('adg-subs')||'[]').includes(id); } catch { return false; }
}
function toggleBell(id, btn) {
  try {
    let subs = JSON.parse(localStorage.getItem('adg-subs')||'[]');
    if (subs.includes(id)) { subs = subs.filter(s=>s!==id); btn.classList.remove('subscribed'); btn.innerHTML='<i class="bi bi-bell"></i>'; }
    else { subs.push(id); btn.classList.add('subscribed'); btn.innerHTML='<i class="bi bi-bell-fill"></i>'; }
    localStorage.setItem('adg-subs', JSON.stringify(subs));
  } catch {}
}

// ── CSV ───────────────────────────────────────────────────────────────────
function exportCSV() {
  const rows = getSorted(getFiltered());
  const cols = ['titol','organisme','estat','pressupost','data_limit','data_pub','ccaa','disciplines','adjudicatari','url'];
  const hdr = cols.join(';');
  const lines = rows.map(r =>
    cols.map(c => {
      let v = r[c];
      if (Array.isArray(v)) v = v.join(',');
      if (v == null) v = '';
      return `"${String(v).replace(/"/g,'""')}"`;
    }).join(';')
  );
  const blob = new Blob(['\uFEFF'+hdr+'\n'+lines.join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `adg-licitaciones-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
}

// ── SHARE ─────────────────────────────────────────────────────────────────

// ── NOTIFY ────────────────────────────────────────────────────────────────

// ── COMARCA SELECTOR ──────────────────────────────────────────────────────
function updateComarca(ccaaCode) {
  const group = el('comarca-group');
  const sel = el('sel-comarca');
  const subs = TERR[ccaaCode]?.sub || [];
  if (subs.length) {
    sel.innerHTML = `<option value="">Toda la CCAA</option>` + subs.map(s=>`<option value="${s}">${s}</option>`).join('');
    group.style.display = '';
  } else {
    group.style.display = 'none';
  }
}

// ── ESCAPE ────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── INIT ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();

  // Sync sort selector to match S default (data_pub,desc)
  const sortSel = el('sort-sel');
  if (sortSel) sortSel.value = `${S.sortCol},${S.sortDir}`;

  // Sync pill visual state with initial S defaults
  if (S.soloActivas) el('pill-solo-activas')?.classList.add('active');

  // ── Filter events
  document.querySelectorAll('[data-estat]').forEach(p => {
    p.addEventListener('click', () => {
      S.estat = normalizeStatusKey(p.dataset.estat); S.page=1;
      syncPills('[data-estat]'); render();
    });
  });

  // Discipline pills — MULTI select
  el('pill-all-disc')?.addEventListener('click', () => {
    S.discs.clear(); S.page=1; syncDiscPills(); render();
  });
  document.querySelectorAll('[data-disc]').forEach(p => {
    p.addEventListener('click', () => {
      const d = p.dataset.disc;
      if (S.discs.has(d)) S.discs.delete(d);
      else S.discs.add(d);
      S.page=1; syncDiscPills(); render();
    });
  });

  el('sel-ccaa')?.addEventListener('change', e => {
    S.ccaa = e.target.value; S.comarca=''; S.page=1;
    updateComarca(S.ccaa); render();
  });
  el('sel-comarca')?.addEventListener('change', e => {
    S.comarca = e.target.value; S.page=1; render();
  });
  el('sel-year')?.addEventListener('change', e => {
    S.year = e.target.value; S.page=1; render();
  });

  let searchT;
  el('search')?.addEventListener('input', e => {
    clearTimeout(searchT);
    searchT = setTimeout(() => { S.query=e.target.value; S.page=1; render(); }, 200);
  });
  el('adj-search')?.addEventListener('input', e => {
    clearTimeout(searchT);
    searchT = setTimeout(() => { S.adjQ=e.target.value; S.page=1; render(); }, 200);
  });

  el('sort-sel')?.addEventListener('change', e => {
    const [col,dir] = e.target.value.split(',');
    S.sortCol=col; S.sortDir=dir; S.page=1; render();
  });

  el('pg-perpage')?.addEventListener('change', e => {
    S.perPage=+e.target.value; S.page=1; render();
  });

  // Sortable column headers
  document.querySelectorAll('th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (S.sortCol === col) S.sortDir = S.sortDir==='asc'?'desc':'asc';
      else { S.sortCol=col; S.sortDir='desc'; }
      S.page=1; render();
    });
  });

  el('btn-csv')?.addEventListener('click', exportCSV);

  // Solo activas toggle
  el('pill-solo-activas')?.addEventListener('click', () => {
    S.soloActivas = !S.soloActivas;
    el('pill-solo-activas')?.classList.toggle('active', S.soloActivas);
    S.page = 1;
    render();
  });

  // Nuevas Hoy clickable stat
  el('sstat-new')?.addEventListener('click', () => {
    S.nuevasHoy = !S.nuevasHoy;
    el('sstat-new')?.classList.toggle('active', S.nuevasHoy);
    S.page = 1;
    render();
  });

  initModal();

  // Refresh on lang/theme change
  document.addEventListener('adg:langchange', () => {
    applyI18n(); render(); updateStrip();
    _updateActiveStats();
  });
  document.addEventListener('adg:themechange', () => render());

  // Clear s-update during load; updateStrip() sets it after data loads
  const _sUpdate = el('s-update');
  if (_sUpdate) _sUpdate.innerHTML = '';

  // Load data
  await loadData();
  updateStrip();
  _updateActiveStats();

  // Sample notice
  if (ADG.isSample) {
    const notice = el('notice');
    const noticeText = el('notice-text');
    if (notice && noticeText) {
      noticeText.textContent = 'Mostrando datos de ejemplo. Los datos reales se sirven desde data/licitaciones.json.';
      notice.classList.add('show');
    }
  }

  render();
  checkURL();
});

function _updateActiveStats() {
  const activeCount = (ADG.canonicalData || ADG.data).filter(r => r.active_opportunity_eligible === true).length;
  const sVig = el('s-vigent');
  if (sVig) sVig.textContent = activeCount.toLocaleString('es-ES');
  const sacCount = el('solo-activas-count');
  if (sacCount) sacCount.textContent = activeCount.toLocaleString('es-ES');
  const recentCount = (ADG.canonicalData || ADG.data).filter(r => isNew(r)).length;
  const sNew = el('s-new');
  if (sNew) sNew.textContent = recentCount;
}

})();
