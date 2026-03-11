/*
 * ADG Plataforma — recursos.js
 * β3.1 — Mar 2026
 * Página: recursos.html
 * Contiene: Calculadora de Honorarios + Recursos profesionales
 *           Tabs, calc engine, resource cards
 *
 * CHANGELOG
 * v1.0  Mar 2026  F3 initial. Calculadora con 4 variables
 *                 (proyecto, experiencia, complejidad, urgencia).
 *                 Recursos: plantillas legales + referencias.
 *                 IIFE pattern. ADG_Utils integration.
 */
;(function() {
"use strict";

const { el, t, fmt, fmtFull, discColor, discTag,
        applyI18n, initShared, loadJSON } = ADG_Utils;

// ── F3-SPECIFIC I18N ─────────────────────────────────────────────────────
// Kept local to avoid bloating app.js — same pattern as CHANGELOG in about.js
const RC = {
  es: {
    tab_calc:'Calculadora', tab_rec:'Recursos',
    proyecto:'Tipo de proyecto', experiencia:'Nivel de experiencia',
    horas:'Horas estimadas', horas_ref:'Rango orientativo',
    complejidad:'Complejidad', urgencia:'Urgencia / Plazo',
    resultado:'Honorarios estimados', rango_min:'Mínimo', rango_max:'Máximo', rango_med:'Medio',
    desglose:'Desglose', reset:'Reiniciar', selecciona:'Selecciona proyecto y experiencia',
    h:'h', tarifa_h:'Tarifa/hora', subtotal:'Subtotal base', total:'Total estimado',
    disclaimer:'⚠ Cálculos orientativos. Las tarifas reales dependen del mercado, cliente y contexto del proyecto.',
    // Experience
    junior:'Junior (0–3 años)', mid:'Mid (3–7 años)', senior:'Senior (7–15 años)', director:'Director/a Creativo/a (15+)',
    // Complexity
    baja:'Baja', media:'Media', alta:'Alta', muy_alta:'Muy alta',
    baja_d:'Proyecto estándar, requisitos claros', media_d:'Investigación moderada, iteraciones',
    alta_d:'Investigación profunda, múltiples entregables', muy_alta_d:'Alta especialización, gran escala, múltiples fases',
    // Urgency
    estandar:'Estándar', rapido:'Rápido', urgente:'Urgente', express:'Express',
    estandar_d:'Plazo cómodo', rapido_d:'–25% del plazo habitual',
    urgente_d:'–50% del plazo habitual', express_d:'Entrega inmediata / fin de semana',
    // Resources
    plantillas:'Plantillas legales', referencias:'Referencias profesionales',
    descargar:'Descargar', consultar:'Consultar', proximamente:'Próximamente',
    // Templates
    contrato_t:'Contrato de Servicios de Diseño',
    contrato_d:'Modelo de contrato para proyectos de diseño gráfico y creativo. Incluye cláusulas de propiedad intelectual, plazos y condiciones de pago.',
    presupuesto_t:'Plantilla de Presupuesto',
    presupuesto_d:'Modelo profesional de presupuesto para presentar a clientes. Desglose por fases, costes y condiciones.',
    cesion_t:'Cesión de Derechos de Autor',
    cesion_d:'Documento modelo para la cesión total o parcial de derechos de propiedad intelectual sobre el trabajo creativo.',
    nda_t:'Acuerdo de Confidencialidad (NDA)',
    nda_d:'Acuerdo estándar para proteger información sensible del proyecto.',
    brief_t:'Brief Creativo',
    brief_d:'Plantilla de brief para alinear expectativas con el cliente antes de iniciar el proyecto.',
    // References
    tarifas_adg_t:'Guía de Tarifas Orientativas ADG-FAD',
    tarifas_adg_d:'Tarifas orientativas del sector del diseño gráfico y comunicación visual en España.',
    lpi_t:'Ley de Propiedad Intelectual (LPI)',
    lpi_d:'Texto refundido de la LPI española. Referencia esencial para derechos de autor en diseño.',
    irpf_t:'Retenciones IRPF para Autónomos',
    irpf_d:'Guía de retenciones fiscales aplicables a facturas de profesionales autónomos del sector creativo.',
    guia_ppto_t:'Cómo Presupuestar un Proyecto de Diseño',
    guia_ppto_d:'Guía práctica con metodologías de pricing y negociación.',
  },
  ca: {
    tab_calc:'Calculadora', tab_rec:'Recursos',
    proyecto:'Tipus de projecte', experiencia:"Nivell d'experiència",
    horas:'Hores estimades', horas_ref:'Rang orientatiu',
    complejidad:'Complexitat', urgencia:'Urgència / Termini',
    resultado:'Honoraris estimats', rango_min:'Mínim', rango_max:'Màxim', rango_med:'Mitjà',
    desglose:'Desglossament', reset:'Reiniciar', selecciona:'Selecciona projecte i experiència',
    h:'h', tarifa_h:'Tarifa/hora', subtotal:'Subtotal base', total:'Total estimat',
    disclaimer:'⚠ Càlculs orientatius. Les tarifes reals depenen del mercat, client i context del projecte.',
    junior:'Junior (0–3 anys)', mid:'Mid (3–7 anys)', senior:'Senior (7–15 anys)', director:'Director/a Creatiu/va (15+)',
    baja:'Baixa', media:'Mitjana', alta:'Alta', muy_alta:'Molt alta',
    baja_d:'Projecte estàndard, requisits clars', media_d:'Investigació moderada, iteracions',
    alta_d:'Investigació profunda, múltiples lliurables', muy_alta_d:'Alta especialització, gran escala, múltiples fases',
    estandar:'Estàndard', rapido:'Ràpid', urgente:'Urgent', express:'Express',
    estandar_d:'Termini còmode', rapido_d:'–25% del termini habitual',
    urgente_d:'–50% del termini habitual', express_d:'Lliurament immediat / cap de setmana',
    plantillas:'Plantilles legals', referencias:'Referències professionals',
    descargar:'Descarregar', consultar:'Consultar', proximamente:'Properament',
    contrato_t:'Contracte de Serveis de Disseny',
    contrato_d:"Model de contracte per a projectes de disseny gràfic i creatiu. Inclou clàusules de propietat intel·lectual, terminis i condicions de pagament.",
    presupuesto_t:'Plantilla de Pressupost',
    presupuesto_d:'Model professional de pressupost per presentar a clients. Desglossament per fases, costos i condicions.',
    cesion_t:"Cessió de Drets d'Autor",
    cesion_d:"Document model per a la cessió total o parcial de drets de propietat intel·lectual sobre el treball creatiu.",
    nda_t:'Acord de Confidencialitat (NDA)',
    nda_d:'Acord estàndard per protegir informació sensible del projecte.',
    brief_t:'Brief Creatiu',
    brief_d:"Plantilla de brief per alinear expectatives amb el client abans d'iniciar el projecte.",
    tarifas_adg_t:'Guia de Tarifes Orientatives ADG-FAD',
    tarifas_adg_d:'Tarifes orientatives del sector del disseny gràfic i comunicació visual a Espanya.',
    lpi_t:'Llei de Propietat Intel·lectual (LPI)',
    lpi_d:"Text refós de la LPI espanyola. Referència essencial per a drets d'autor en disseny.",
    irpf_t:"Retencions IRPF per a Autònoms",
    irpf_d:'Guia de retencions fiscals aplicables a factures de professionals autònoms del sector creatiu.',
    guia_ppto_t:'Com Pressupostar un Projecte de Disseny',
    guia_ppto_d:'Guia pràctica amb metodologies de pricing i negociació.',
  },
  eu: {
    tab_calc:'Kalkulagailua', tab_rec:'Baliabideak',
    proyecto:'Proiektu mota', experiencia:'Esperientzia maila',
    horas:'Ordu estimatuak', horas_ref:'Orientazio tartea',
    complejidad:'Konplexutasuna', urgencia:'Urgentzia / Epea',
    resultado:'Estimatutako ordainsariak', rango_min:'Gutxienekoa', rango_max:'Gehienekoa', rango_med:'Batez bestekoa',
    desglose:'Xehetasunak', reset:'Berrabiarazi', selecciona:'Hautatu proiektua eta esperientzia',
    h:'h', tarifa_h:'Tarifa/ordua', subtotal:'Oinarrizko azpitotala', total:'Guztira estimatua',
    disclaimer:'⚠ Kalkulu orientagarriak. Tarifa errealak merkatuaren, bezeroaren eta testuinguruaren araberakoak dira.',
    junior:'Junior (0–3 urte)', mid:'Mid (3–7 urte)', senior:'Senior (7–15 urte)', director:'Zuzendari Sortzailea (15+)',
    baja:'Baxua', media:'Ertaina', alta:'Altua', muy_alta:'Oso altua',
    baja_d:'Proiektu estandarra', media_d:'Ikerketa ertaina',
    alta_d:'Ikerketa sakona', muy_alta_d:'Espezializazio altua, eskala handia',
    estandar:'Estandarra', rapido:'Azkarra', urgente:'Urgentea', express:'Express',
    estandar_d:'Epe erosoa', rapido_d:'–25% ohiko epearen',
    urgente_d:'–50% ohiko epearen', express_d:'Berehalako entrega',
    plantillas:'Txantiloi legalak', referencias:'Erreferentzia profesionalak',
    descargar:'Deskargatu', consultar:'Kontsultatu', proximamente:'Laster',
    contrato_t:'Diseinuko Zerbitzu Kontratua',
    contrato_d:'Diseinu grafikoko proiektuetarako kontratu eredua.',
    presupuesto_t:'Aurrekontu Txantiloia',
    presupuesto_d:'Bezeroei aurkezteko aurrekontu profesionala.',
    cesion_t:'Egile-eskubideen Lagapena',
    cesion_d:'Jabetza intelektualaren eskubideen lagapen dokumentua.',
    nda_t:'Konfidentzialtasun Akordioa (NDA)',
    nda_d:'Proiektuaren informazio sentikorra babesteko akordio estandarra.',
    brief_t:'Brief Sortzailea',
    brief_d:'Brief txantiloia bezeroarekin itxaropenak lerrokatzeko.',
    tarifas_adg_t:'ADG-FAD Tarifa Orientagarrien Gida',
    tarifas_adg_d:'Espainiako diseinu grafikoaren sektoreko tarifa orientagarriak.',
    lpi_t:'Jabetza Intelektualaren Legea (LPI)',
    lpi_d:'Espainiako LPIaren testu bateratua. Diseinuko egile-eskubideetarako erreferentzia.',
    irpf_t:'IRPF Atxikipenak Autonomoentzat',
    irpf_d:'Sektore sortzaileko profesional autonomoen fakturetarako atxikipen fiskalak.',
    guia_ppto_t:'Diseinu Proiektu bat nola Aurrekontatua',
    guia_ppto_d:'Pricing eta negoziazio metodologiekin gida praktikoa.',
  },
  gl: {
    tab_calc:'Calculadora', tab_rec:'Recursos',
    proyecto:'Tipo de proxecto', experiencia:'Nivel de experiencia',
    horas:'Horas estimadas', horas_ref:'Rango orientativo',
    complejidad:'Complexidade', urgencia:'Urxencia / Prazo',
    resultado:'Honorarios estimados', rango_min:'Mínimo', rango_max:'Máximo', rango_med:'Medio',
    desglose:'Desagregación', reset:'Reiniciar', selecciona:'Selecciona proxecto e experiencia',
    h:'h', tarifa_h:'Tarifa/hora', subtotal:'Subtotal base', total:'Total estimado',
    disclaimer:'⚠ Cálculos orientativos. As tarifas reais dependen do mercado, cliente e contexto do proxecto.',
    junior:'Junior (0–3 anos)', mid:'Mid (3–7 anos)', senior:'Senior (7–15 anos)', director:'Director/a Creativo/a (15+)',
    baja:'Baixa', media:'Media', alta:'Alta', muy_alta:'Moi alta',
    baja_d:'Proxecto estándar, requisitos claros', media_d:'Investigación moderada, iteracións',
    alta_d:'Investigación profunda, múltiples entregables', muy_alta_d:'Alta especialización, gran escala, múltiples fases',
    estandar:'Estándar', rapido:'Rápido', urgente:'Urxente', express:'Express',
    estandar_d:'Prazo cómodo', rapido_d:'–25% do prazo habitual',
    urgente_d:'–50% do prazo habitual', express_d:'Entrega inmediata / fin de semana',
    plantillas:'Modelos legais', referencias:'Referencias profesionais',
    descargar:'Descargar', consultar:'Consultar', proximamente:'Proximamente',
    contrato_t:'Contrato de Servizos de Deseño',
    contrato_d:'Modelo de contrato para proxectos de deseño gráfico e creativo.',
    presupuesto_t:'Modelo de Orzamento',
    presupuesto_d:'Modelo profesional de orzamento para presentar a clientes.',
    cesion_t:'Cesión de Dereitos de Autor',
    cesion_d:'Documento modelo para a cesión de dereitos de propiedade intelectual.',
    nda_t:'Acordo de Confidencialidade (NDA)',
    nda_d:'Acordo estándar para protexer información sensible do proxecto.',
    brief_t:'Brief Creativo',
    brief_d:'Modelo de brief para aliñar expectativas co cliente.',
    tarifas_adg_t:'Guía de Tarifas Orientativas ADG-FAD',
    tarifas_adg_d:'Tarifas orientativas do sector do deseño gráfico en España.',
    lpi_t:'Lei de Propiedade Intelectual (LPI)',
    lpi_d:'Texto refundido da LPI española. Referencia esencial para dereitos de autor en deseño.',
    irpf_t:'Retencións IRPF para Autónomos',
    irpf_d:'Guía de retencións fiscais para profesionais autónomos do sector creativo.',
    guia_ppto_t:'Como Orzamentar un Proxecto de Deseño',
    guia_ppto_d:'Guía práctica con metodoloxías de pricing e negociación.',
  },
};

function rc(key) {
  const lang = ADG.lang || 'es';
  return (RC[lang] && RC[lang][key]) || RC.es[key] || key;
}

// ── STATE ────────────────────────────────────────────────────────────────
let DATA = null;
let currentTab = 'calculadora';
let CS = { proyecto: null, experiencia: null, horas: 40, complejidad: null, urgencia: null };

const $ = (s, p) => (p || document).querySelector(s);
const $$ = (s, p) => [...(p || document).querySelectorAll(s)];

// ── LOAD DATA ────────────────────────────────────────────────────────────
async function boot() {
  try {
    DATA = await loadJSON('./data/recursos.json');
    if (!DATA || !DATA.calculadora) throw new Error('bad data');
  } catch (e) {
    console.warn('[F3] recursos.json failed, using inline fallback');
    DATA = null;
    return;
  }
  renderAll();
}

// ── RENDER ALL ───────────────────────────────────────────────────────────
function renderAll() {
  if (!DATA) return;
  renderTabs();
  renderCalculadora();
  renderRecursos();
  showTab(currentTab);
  bindEvents();
}

// ── TABS ─────────────────────────────────────────────────────────────────
function renderTabs() {
  const bar = el('rc-tabs');
  if (!bar) return;
  bar.innerHTML = `
    <button class="pill active" data-rc-tab="calculadora"><i class="bi bi-calculator"></i>${rc('tab_calc')}</button>
    <button class="pill" data-rc-tab="recursos"><i class="bi bi-book"></i>${rc('tab_rec')}</button>
  `;
}

function showTab(tab) {
  currentTab = tab;
  $$('[data-rc-tab]').forEach(b => b.classList.toggle('active', b.dataset.rcTab === tab));
  const panelCalc = el('rc-panel-calc');
  const panelRec  = el('rc-panel-rec');
  if (panelCalc) panelCalc.style.display = tab === 'calculadora' ? '' : 'none';
  if (panelRec)  panelRec.style.display  = tab === 'recursos'    ? '' : 'none';
}

// ── CALCULADORA RENDER ───────────────────────────────────────────────────
function renderCalculadora() {
  const panel = el('rc-panel-calc');
  if (!panel) return;
  const C = DATA.calculadora;

  panel.innerHTML = `
    <div class="rc-calc-layout">
      <div class="rc-calc-form">
        <!-- Proyecto -->
        <div class="rc-section">
          <div class="rc-label">${rc('proyecto')}</div>
          <div class="rc-chips rc-chips--proyecto">
            ${C.proyectos.map(p => {
              const d = DISC[p.disc];
              return `<button class="rc-chip" data-rc-proy="${p.id}">
                <i class="bi ${d ? d.icon : 'bi-tag'}"></i>${d ? d.label : p.id}
              </button>`;
            }).join('')}
          </div>
        </div>

        <!-- Experiencia -->
        <div class="rc-section">
          <div class="rc-label">${rc('experiencia')}</div>
          <div class="rc-chips">
            ${C.experiencia.map(e => `
              <button class="rc-chip" data-rc-exp="${e.id}">
                <span>${rc(e.id)}</span>
                <span class="rc-chip-sub">${e.tarifaHora[0]}–${e.tarifaHora[1]}€/h</span>
              </button>
            `).join('')}
          </div>
        </div>

        <!-- Horas -->
        <div class="rc-section">
          <div class="rc-label">${rc('horas')}</div>
          <div class="rc-slider-row">
            <input type="range" id="rc-slider" min="1" max="300" value="40" class="rc-slider" />
            <div class="rc-slider-val"><span id="rc-horas-num">40</span><span class="rc-slider-unit">${rc('h')}</span></div>
          </div>
          <div class="rc-hint" id="rc-horas-ref"></div>
        </div>

        <!-- Complejidad -->
        <div class="rc-section">
          <div class="rc-label">${rc('complejidad')}</div>
          <div class="rc-chips">
            ${C.complejidad.map(c => `
              <button class="rc-chip" data-rc-comp="${c.id}">
                <span>${rc(c.id)}</span>
                <span class="rc-chip-sub">×${c.mult}</span>
              </button>
            `).join('')}
          </div>
          <div class="rc-hint" id="rc-comp-desc"></div>
        </div>

        <!-- Urgencia -->
        <div class="rc-section">
          <div class="rc-label">${rc('urgencia')}</div>
          <div class="rc-chips">
            ${C.urgencia.map(u => `
              <button class="rc-chip" data-rc-urg="${u.id}">
                <span>${rc(u.id)}</span>
                <span class="rc-chip-sub">×${u.mult}</span>
              </button>
            `).join('')}
          </div>
          <div class="rc-hint" id="rc-urg-desc"></div>
        </div>

        <button class="rc-reset" id="rc-reset">${rc('reset')}</button>
      </div>

      <!-- Result -->
      <div class="rc-result" id="rc-result">
        <div class="rc-result-empty" id="rc-empty">
          <i class="bi bi-calculator" style="font-size:28px;opacity:.2"></i>
          <div>${rc('selecciona')}</div>
        </div>
        <div class="rc-result-content" id="rc-content" style="display:none">
          <div class="rc-label">${rc('resultado')}</div>
          <div class="rc-result-ranges">
            <div class="rc-range-item"><div class="rc-range-lbl">${rc('rango_min')}</div><div class="rc-range-val" id="rc-min">—</div></div>
            <div class="rc-range-item rc-range-item--mid"><div class="rc-range-lbl">${rc('rango_med')}</div><div class="rc-range-val rc-range-val--big" id="rc-avg">—</div></div>
            <div class="rc-range-item"><div class="rc-range-lbl">${rc('rango_max')}</div><div class="rc-range-val" id="rc-max">—</div></div>
          </div>
          <div class="rc-bar-wrap">
            <div class="rc-bar"><div class="rc-bar-fill" id="rc-bar-fill"></div><div class="rc-bar-marker" id="rc-bar-marker"></div></div>
            <div class="rc-bar-labels"><span id="rc-bar-min"></span><span id="rc-bar-max"></span></div>
          </div>
          <div class="rc-desglose">
            <div class="rc-label">${rc('desglose')}</div>
            <table class="rc-desglose-table"><tbody id="rc-tbody"></tbody></table>
          </div>
          <div class="rc-disclaimer">${rc('disclaimer')}</div>
        </div>
      </div>
    </div>
  `;
}

// ── RECURSOS RENDER ──────────────────────────────────────────────────────
function renderRecursos() {
  const panel = el('rc-panel-rec');
  if (!panel) return;
  const R = DATA.recursos;

  const icons = { contrato:'bi-file-earmark-text', presupuesto:'bi-currency-euro', cesion:'bi-c-circle',
                  nda:'bi-lock', brief:'bi-clipboard-check',
                  tarifas_adg:'bi-bar-chart', lpi:'bi-bank', irpf:'bi-receipt', guia_ppto:'bi-rulers' };

  function cardHTML(item, type) {
    const icon = icons[item.id] || 'bi-file-earmark';
    const titulo = rc(item.id + '_t');
    const desc = rc(item.id + '_d');
    const actionLabel = type === 'plantilla' ? rc('descargar') : rc('consultar');
    const isLive = item.url && item.url !== '#';
    return `<div class="rc-res-card">
      <div class="rc-res-icon"><i class="bi ${icon}"></i></div>
      <div class="rc-res-body">
        <div class="rc-res-title">${esc(titulo)}</div>
        <div class="rc-res-desc">${esc(desc)}</div>
      </div>
      <div class="rc-res-action">
        ${isLive
          ? `<a href="${item.url}" class="rc-res-btn" target="_blank" rel="noopener">${actionLabel} ↗</a>`
          : `<span class="rc-res-soon">${rc('proximamente')}</span>`
        }
      </div>
    </div>`;
  }

  panel.innerHTML = `
    <div class="rc-section">
      <div class="rc-label">${rc('plantillas')}</div>
      <div class="rc-res-grid">${R.plantillas.map(p => cardHTML(p, 'plantilla')).join('')}</div>
    </div>
    <div class="rc-section" style="margin-top:20px">
      <div class="rc-label">${rc('referencias')}</div>
      <div class="rc-res-grid">${R.referencias.map(r => cardHTML(r, 'referencia')).join('')}</div>
    </div>
  `;
}

// ── EVENTS ───────────────────────────────────────────────────────────────
function bindEvents() {
  // Tabs
  $$('[data-rc-tab]').forEach(b => b.addEventListener('click', () => showTab(b.dataset.rcTab)));

  // Proyecto
  $$('[data-rc-proy]').forEach(b => b.addEventListener('click', () => {
    $$('[data-rc-proy]').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    CS.proyecto = b.dataset.rcProy;
    // Color the active chip by discipline
    const proj = DATA.calculadora.proyectos.find(p => p.id === CS.proyecto);
    if (proj) {
      const c = discColor(proj.disc);
      b.style.background = c.bg; b.style.color = c.text; b.style.borderColor = c.text;
    }
    updateHorasRef();
    recalc();
  }));

  // Experiencia
  $$('[data-rc-exp]').forEach(b => b.addEventListener('click', () => {
    $$('[data-rc-exp]').forEach(x => { x.classList.remove('active'); x.style.background=''; x.style.color=''; x.style.borderColor=''; });
    b.classList.add('active');
    CS.experiencia = b.dataset.rcExp;
    recalc();
  }));

  // Slider
  const slider = el('rc-slider');
  if (slider) {
    slider.addEventListener('input', () => {
      CS.horas = +slider.value;
      const num = el('rc-horas-num');
      if (num) num.textContent = CS.horas;
      updateSliderTrack(slider);
      recalc();
    });
    updateSliderTrack(slider);
  }

  // Complejidad
  $$('[data-rc-comp]').forEach(b => b.addEventListener('click', () => {
    $$('[data-rc-comp]').forEach(x => { x.classList.remove('active'); x.style.background=''; x.style.color=''; x.style.borderColor=''; });
    b.classList.add('active');
    CS.complejidad = b.dataset.rcComp;
    const desc = el('rc-comp-desc');
    if (desc) desc.textContent = rc(CS.complejidad + '_d');
    recalc();
  }));

  // Urgencia
  $$('[data-rc-urg]').forEach(b => b.addEventListener('click', () => {
    $$('[data-rc-urg]').forEach(x => { x.classList.remove('active'); x.style.background=''; x.style.color=''; x.style.borderColor=''; });
    b.classList.add('active');
    CS.urgencia = b.dataset.rcUrg;
    const desc = el('rc-urg-desc');
    if (desc) desc.textContent = rc(CS.urgencia + '_d');
    recalc();
  }));

  // Reset
  el('rc-reset')?.addEventListener('click', resetCalc);
}

// ── SLIDER TRACK ─────────────────────────────────────────────────────────
function updateSliderTrack(s) {
  const pct = ((s.value - s.min) / (s.max - s.min)) * 100;
  s.style.setProperty('--fill', pct + '%');
}

// ── HORAS REF ────────────────────────────────────────────────────────────
function updateHorasRef() {
  const ref = el('rc-horas-ref');
  if (!ref || !CS.proyecto) return;
  const proj = DATA.calculadora.proyectos.find(p => p.id === CS.proyecto);
  if (!proj) return;
  ref.textContent = `${rc('horas_ref')}: ${proj.horasBase[0]}–${proj.horasBase[1]}h`;
  // Auto-set slider to midpoint if still at default
  const slider = el('rc-slider');
  if (slider && CS.horas === 40) {
    const mid = Math.round((proj.horasBase[0] + proj.horasBase[1]) / 2);
    slider.value = mid;
    CS.horas = mid;
    const num = el('rc-horas-num');
    if (num) num.textContent = mid;
    updateSliderTrack(slider);
  }
}

// ── RECALCULATE ──────────────────────────────────────────────────────────
function recalc() {
  const empty = el('rc-empty');
  const content = el('rc-content');
  if (!CS.proyecto || !CS.experiencia) {
    if (empty) empty.style.display = '';
    if (content) content.style.display = 'none';
    return;
  }
  if (empty) empty.style.display = 'none';
  if (content) content.style.display = '';

  const exp = DATA.calculadora.experiencia.find(e => e.id === CS.experiencia);
  const compMult = CS.complejidad ? DATA.calculadora.complejidad.find(c => c.id === CS.complejidad).mult : 1.0;
  const urgMult  = CS.urgencia   ? DATA.calculadora.urgencia.find(u => u.id === CS.urgencia).mult       : 1.0;
  const h = CS.horas || 40;

  const min = Math.round(h * exp.tarifaHora[0] * compMult * urgMult);
  const max = Math.round(h * exp.tarifaHora[1] * compMult * urgMult);
  const avg = Math.round((min + max) / 2);

  const f = n => n.toLocaleString('es-ES') + ' €';

  el('rc-min').textContent = f(min);
  el('rc-max').textContent = f(max);
  el('rc-avg').textContent = f(avg);

  // Bar
  const fill = el('rc-bar-fill');
  const marker = el('rc-bar-marker');
  if (fill && marker) {
    const pct = max > min ? ((avg - min) / (max - min)) * 100 : 50;
    fill.style.width = Math.min(pct + 20, 100) + '%';
    marker.style.left = pct + '%';
  }
  el('rc-bar-min').textContent = f(min);
  el('rc-bar-max').textContent = f(max);

  // Desglose
  const tbody = el('rc-tbody');
  if (tbody) {
    const baseMin = h * exp.tarifaHora[0];
    const baseMax = h * exp.tarifaHora[1];
    tbody.innerHTML = `
      <tr><td>${rc('horas')}</td><td>${h}h</td></tr>
      <tr><td>${rc('tarifa_h')}</td><td>${exp.tarifaHora[0]}–${exp.tarifaHora[1]} €</td></tr>
      <tr><td>${rc('subtotal')}</td><td>${f(Math.round(baseMin))} – ${f(Math.round(baseMax))}</td></tr>
      <tr><td>${rc('complejidad')}</td><td>×${compMult}</td></tr>
      <tr><td>${rc('urgencia')}</td><td>×${urgMult}</td></tr>
      <tr class="rc-desglose-total"><td>${rc('total')}</td><td>${f(min)} – ${f(max)}</td></tr>
    `;
  }
}

// ── RESET ────────────────────────────────────────────────────────────────
function resetCalc() {
  CS = { proyecto: null, experiencia: null, horas: 40, complejidad: null, urgencia: null };
  $$('.rc-chip').forEach(b => { b.classList.remove('active'); b.style.background=''; b.style.color=''; b.style.borderColor=''; });
  const slider = el('rc-slider');
  if (slider) { slider.value = 40; updateSliderTrack(slider); }
  el('rc-horas-num').textContent = '40';
  el('rc-horas-ref').textContent = '';
  el('rc-comp-desc').textContent = '';
  el('rc-urg-desc').textContent = '';
  el('rc-empty').style.display = '';
  el('rc-content').style.display = 'none';
}

// ── ESCAPE ───────────────────────────────────────────────────────────────
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── INIT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initShared();
  await boot();
  // Re-render on lang change
  document.addEventListener('adg:langchange', () => {
    applyI18n();
    if (DATA) renderAll();
  });
  document.addEventListener('adg:themechange', () => {
    if (DATA) renderAll();
  });
});
})();
