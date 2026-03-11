/* ── index.js v2.0 — tabla, filtros multi-disc, panel detalle ───────────── */
"use strict";

const { el, t, fmt, fmtFull, daysTo, isNew, discColor, discTag, stateBadge,
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
  sortCol: 'rellevancia',
  sortDir: 'desc',
  page:    1,
  perPage: 20,
  selectedId: null,
};

// ── FILTERING ─────────────────────────────────────────────────────────────
function getFiltered() {
  let rows = ADG.data;
  if (S.estat)   rows = rows.filter(r => r.estat === S.estat);
  if (S.ccaa)    rows = rows.filter(r => r.ccaa === S.ccaa);
  if (S.year)    rows = rows.filter(r => (r.data_pub||'').startsWith(S.year));
  if (S.discs.size) rows = rows.filter(r => (r.disciplines||[]).some(d => S.discs.has(d)));
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
  return [...rows].sort((a,b) => {
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

  // Rows
  const tbody = el('tbody');
  if (!tbody) return;
  tbody.innerHTML = slice.map(r => rowHTML(r)).join('');

  // Click on row
  tbody.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', e => {
      if (e.target.closest('.bell-btn')) return;
      openDetail(tr.dataset.id);
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

function rowHTML(r) {
  const days = daysTo(r.data_limit);
  const dateClass = days !== null && days >= 0 && days <= 7 ? 'date-warn' : (days !== null && days > 7 ? 'date-ok' : '');
  const dateStr = r.data_limit ? new Date(r.data_limit).toLocaleDateString(ADG.lang+'-ES',{day:'2-digit',month:'short',year:'2-digit'}) : '—';
  const tags = (r.disciplines||[]).map(d => discTag(d)).join('');
  const newBadge = isNew(r) ? `<span class="badge-new">${t('nueva')}</span>` : '';
  const bellClass = isSubscribed(r.id) ? 'subscribed' : '';
  const isSel = r.id === S.selectedId;

  return `<tr data-id="${r.id}" class="${isSel?'sel':''}" tabindex="0">
    <td>
      <div class="tc-name">${esc(r.titol)}${newBadge}</div>
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
    <td>${stateBadge(r.estat)}</td>
    <td><div class="tc-date ${dateClass}">${dateStr}</div></td>
    <td class="tc-bell"><button class="bell-btn ${bellClass}" aria-label="Notificación"><i class="bi bi-bell${bellClass?'-fill':''}"></i></button></td>
  </tr>`;
}

// ── DETAIL PANEL ──────────────────────────────────────────────────────────
function openDetail(id) {
  const r = ADG.data.find(x => x.id === id);
  if (!r) return;
  S.selectedId = id;
  document.querySelectorAll('tbody tr').forEach(tr => tr.classList.toggle('sel', tr.dataset.id === id));

  const panel = el('detail');
  panel.classList.add('open');

  el('dp-title').textContent = r.titol;

  // Badges
  const days = daysTo(r.data_limit);
  let badges = stateBadge(r.estat);
  if (r.ccaa) badges += ` <span class="badge b-info">${TERR[r.ccaa]?.name || r.ccaa}</span>`;
  if (isNew(r)) badges += ` <span class="badge-new">${t('nueva')}</span>`;
  el('dp-badges').innerHTML = badges;

  // Rows
  const rows = [
    ['Organismo', esc(r.organisme||'—')],
    ['Presupuesto', `<span class="dp-amt">${fmtFull(r.pressupost)}</span>`],
    ['Termina', r.data_limit ? `<span class="${days!==null&&days<=7?'date-warn':days>7?'date-ok':''}">${new Date(r.data_limit).toLocaleDateString(ADG.lang+'-ES',{weekday:'long',day:'numeric',month:'long',year:'numeric'})}</span>` : '—'],
    ['Publicado', r.data_pub ? new Date(r.data_pub).toLocaleDateString(ADG.lang+'-ES',{day:'numeric',month:'long',year:'numeric'}) : '—'],
    ['Tipo', r.tipus||'—'],
    r.adjudicatari ? ['Adjudicado a', `<strong>${esc(r.adjudicatari)}</strong>`] : null,
    r.cpv ? ['CPV', `<span class="dp-cpv">${esc(r.cpv)}</span>`] : null,
    ['Fuente', `<span class="source-badge">${esc(r.font||'PLACSP')}</span>`],
  ].filter(Boolean);

  el('dp-rows').innerHTML = rows.map(([k,v]) =>
    `<div class="dp-row"><div class="dp-key">${k}</div><div class="dp-val">${v}</div></div>`
  ).join('');

  // Disc chips
  el('dp-disc-chips').innerHTML = (r.disciplines||[]).map(d => {
    const c = discColor(d);
    return `<span class="dp-chip" style="color:${c.text};border-color:${c.text}20;background:${c.bg}">
      <i class="bi ${DISC[d]?.icon||'bi-tag'}"></i>${DISC[d]?.label||d}
    </span>`;
  }).join('') || '<span style="font-size:10px;color:var(--text3)">—</span>';

  // KW chips
  el('dp-kw-chips').innerHTML = (r.kw||[]).map(k =>
    `<span class="dp-chip"><i class="bi bi-tag"></i>${esc(k)}</span>`
  ).join('') || '<span style="font-size:10px;color:var(--text3)">—</span>';

  // Historial
  const hw = el('dp-hist-wrap');
  const hist = r.historial||[];
  hw.style.display = hist.length ? '' : 'none';
  if (hist.length) {
    el('dp-historial').innerHTML = hist.map(h =>
      `<div class="dp-hist-item">
        <div class="dp-hist-date">${h.data||''}</div>
        <div>${stateBadge(h.estat)}</div>
        <div class="dp-hist-nota">${esc(h.nota||'')}</div>
      </div>`
    ).join('');
  }

  // CTA
  const ctaEl = el('dp-cta');
  const noteEl = el('dp-cta-note');
  if (r.url && r.url.startsWith('http')) {
    ctaEl.href = r.url;
    noteEl.textContent = '';
  } else {
    ctaEl.href = 'https://contrataciondelestado.es';
    noteEl.textContent = 'URL directa no disponible';
  }

  // URL sharing
  updateURL(id);
}

function closeDetail() {
  S.selectedId = null;
  el('detail').classList.remove('open');
  document.querySelectorAll('tbody tr').forEach(tr => tr.classList.remove('sel'));
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

  if (S.estat) {
    const colors = { Vigente:'var(--s-ok)', Adjudicado:'var(--s-adj)', Desierta:'var(--s-des)' };
    const c = colors[S.estat] || 'var(--text)';
    chips.push({ label: S.estat, color: c, onX: () => { S.estat=''; render(); syncPills('[data-estat]'); } });
  }

  if (S.ccaa) {
    chips.push({ label: TERR[S.ccaa]?.name || S.ccaa, color: 'var(--text)', onX: () => { S.ccaa=''; el('sel-ccaa').value=''; el('comarca-group').style.display='none'; render(); } });
  }

  if (S.year) {
    chips.push({ label: S.year, color: 'var(--text)', onX: () => { S.year=''; el('sel-year').value=''; render(); } });
  }

  S.discs.forEach(d => {
    const c = discColor(d);
    chips.push({ label: DISC[d]?.label || d, color: c.text, bg: c.bg, onX: () => { S.discs.delete(d); S.page=1; render(); syncDiscPills(); } });
  });

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
  el('sel-ccaa').value=''; el('sel-year').value='';
  el('comarca-group').style.display='none';
  el('search').value=''; el('adj-search').value='';
  syncPills('[data-estat]'); syncDiscPills();
  render();
}

// ── PILL SYNC ─────────────────────────────────────────────────────────────
function syncPills(selector) {
  document.querySelectorAll(selector).forEach(p => {
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
function initShare() {
  const btn = el('dp-share');
  if (!btn) return;
  btn.addEventListener('click', () => {
    navigator.clipboard?.writeText(location.href).then(() => {
      btn.classList.add('copied');
      btn.innerHTML = '<i class="bi bi-check2"></i>';
      setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML='<i class="bi bi-share"></i>'; }, 2000);
    });
  });
}

// ── NOTIFY ────────────────────────────────────────────────────────────────
function initNotify() {
  const toggle = el('dp-notify-toggle');
  const form = el('dp-notify-form');
  const submit = el('dp-notify-submit');
  const ok = el('dp-notify-ok');
  if (!toggle) return;

  toggle.addEventListener('click', () => {
    form.classList.toggle('open');
    toggle.classList.toggle('active', form.classList.contains('open'));
  });
  if (submit) submit.addEventListener('click', () => {
    ok.style.display = 'block';
    submit.style.display = 'none';
    toggle.classList.add('active');
    try {
      const subs = JSON.parse(localStorage.getItem('adg-subs')||'[]');
      if (S.selectedId && !subs.includes(S.selectedId)) { subs.push(S.selectedId); localStorage.setItem('adg-subs', JSON.stringify(subs)); }
    } catch {}
  });
}

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

  // ── Filter events
  document.querySelectorAll('[data-estat]').forEach(p => {
    p.addEventListener('click', () => {
      S.estat = p.dataset.estat; S.page=1;
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
  el('dp-close')?.addEventListener('click', closeDetail);

  initShare();
  initNotify();
  initModal();

  // Refresh on lang/theme change
  document.addEventListener('adg:langchange', () => { applyI18n(); render(); updateStrip(); });
  document.addEventListener('adg:themechange', () => render());

  // Load data
  await loadData();
  updateStrip();

  // Sample notice
  if (ADG.isSample) {
    const notice = el('notice');
    const noticeText = el('notice-text');
    if (notice && noticeText) {
      noticeText.textContent = 'Mostrando datos de ejemplo. Coloca data.json junto a index.html para ver datos reales.';
      notice.classList.add('show');
    }
  }

  render();
  checkURL();
});
