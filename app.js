/*
 * ADG Plataforma Digital -- app.js
 * 0.5.0e -- Jun 2026
 * Role: Shared state, I18N (ES/CA/EU/GL), utilities, data loading.
 *       Exposes window.ADG (state) and window.ADG_Utils (functions).
 * Page: All pages (loaded first)
 * Depends on: nothing (defines globals)
 * Exports: window.ADG, window.ADG_Utils
 *
 * CHANGELOG (newest first)
 * 0.5.0k Jun 2026  Zone B list/row-key/duplicate hardening: stable row-key for exact
 *                  detail mapping, duplicate-ID collision fix, lifecycle variant badge.
 * 0.5.0j Jun 2026  Zone A data status/recency hardening: fix production dataset meta
 *                  extraction (raw.meta shape), fix false "Datos de muestra", unify
 *                  3-day recent window for s-new KPI and filter, default sort to
 *                  most recent, clean loading UX deduplication.
 * 0.5.0i Jun 2026  Zone C detail panel hardening: fix &mdash; doc label bug, reorder
 *                  panel hierarchy (title/facts first, then verdict/signals), add
 *                  territory fact, Fetcher 2 placeholder, fix eyebrow accent,
 *                  3-line title clamp. Version bump only — no data changes.
 * 0.5.0g Jun 2026  Loading spinner before fetch. Remove duplicate active-filter chips.
 * 0.5.0f Jun 2026  Increase production dataset fetch timeout for 19MB GitHub Pages JSON.
 * 0.5.0e Jun 2026  Version bump. fp_no_docs i18n "todavía". Console warn copy fix.
 * 0.4.4q May 2026  Runtime display status: getDisplayStatus, isOpenOpportunity, stateBadgeRow. Honest open-opportunity filtering/badges.
 * 0.4.4i May 2026  Version bump for fetcher estat_raw provenance field.
 * 0.4.4h May 2026  (status/date semantics audit only -- no code changes).
 * 0.4.4g May 2026  Version bump for UBL extractor fix + TypeCode -> tipus lane.
 * 0.4.4f May 2026  (audit + diagnostic only -- no code changes).
 * 0.4.4e May 2026  Version bump for fetcher smoke controls + PowerShell readability lane.
 * 0.4.4d May 2026  Version bump for fetcher progress telemetry lane.
 * 0.4.4c May 2026  Version bump for fetcher load_previous() safety fix lane.
 * 0.4.3p Apr 2026  Version bump for alertas visible text repair lane.
 * 0.4.3n Apr 2026  Version bump for stats/barometro responsive scroll lane.
 * 0.4.3m Apr 2026  Version bump for licitaciones detail internal-scroll lane.
 * 0.4.3l Apr 2026  Version bump for licitaciones responsive shell lane.
 * 0.4.3k Apr 2026  Shared runtime version constant ADG.version; initShared syncs [data-adg-version] nodes.
 * b4.0  Mar 2026  Added I18N keys for shared components (FichaPanel,
 *                 TrafficLight, ToggleSwitch, AlertasStub, Alertas nav).
 * b3.1  Mar 2026  Added nav_recursos, nav_mapa i18n keys.
 * b3.0  Mar 2026  Multi-page split. ADG_Utils export. loadData normalizeItem.
 * v1.x  Ene-Feb   Embebido en index.html
 */"use strict";

// ── DISCIPLINE METADATA (colors, icons, labels) ──────────────────────────
const DISC = {
  branding:    { icon:'bi-award',          label:'Branding',    lc:'#D4380D', ld:'#FF7A45', bg:'#FFF2E8', bd:'#2B1600' },
  editorial:   { icon:'bi-journal-text',   label:'Editorial',   lc:'#C4294A', ld:'#FF85A1', bg:'#FFF0F6', bd:'#43091F' },
  web:         { icon:'bi-globe2',         label:'Web',         lc:'#0885A8', ld:'#22D3EE', bg:'#E0F9FF', bd:'#002233' },
  uxui:        { icon:'bi-cursor',         label:'UX · UI',     lc:'#15803D', ld:'#39F669', bg:'#DCFCE7', bd:'#003400' },
  publicitat:  { icon:'bi-megaphone',      label:'Publicidad',  lc:'#B45309', ld:'#FBBF24', bg:'#FFFBEB', bd:'#1A0C00' },
  senyaletica: { icon:'bi-signpost-split', label:'Señalética',  lc:'#7C3AED', ld:'#A78BFA', bg:'#F5F3FF', bd:'#1A0840' },
  fotografia:  { icon:'bi-camera',         label:'Fotografía',  lc:'#0369A1', ld:'#00A8EF', bg:'#E0F2FE', bd:'#001E36' },
  audiovisual: { icon:'bi-film',           label:'Audiovisual', lc:'#4A1D96', ld:'#9694F4', bg:'#EDE9FE', bd:'#01005D' },
  illustracio: { icon:'bi-pen',            label:'Ilustración', lc:'#92400E', ld:'#FB9D04', bg:'#FEF3C7', bd:'#2B0502' },
  impressio:   { icon:'bi-printer',        label:'Impresión',   lc:'#374151', ld:'#9CA3AF', bg:'#F9FAFB', bd:'#111827' },
};

const TERR = {
  AN:{name:'Andalucía',sub:['Almería','Cádiz','Córdoba','Granada','Huelva','Jaén','Málaga','Sevilla']},
  AR:{name:'Aragón',sub:['Huesca','Teruel','Zaragoza']},
  AS:{name:'Asturias',sub:[]},
  IB:{name:'Baleares',sub:['Mallorca','Menorca','Ibiza-Formentera']},
  CN:{name:'Canarias',sub:['Gran Canaria','Tenerife','Lanzarote','Fuerteventura','La Palma']},
  CB:{name:'Cantabria',sub:[]},
  CM:{name:'Castilla-La Mancha',sub:['Albacete','Ciudad Real','Cuenca','Guadalajara','Toledo']},
  CL:{name:'Castilla y León',sub:['Ávila','Burgos','León','Palencia','Salamanca','Segovia','Soria','Valladolid','Zamora']},
  CT:{name:'Catalunya',sub:['Barcelona','Girona','Lleida','Tarragona','Alt Penedès','Anoia','Bages','Baix Llobregat','Barcelonès','Berguedà','Garraf','Maresme','Osona','Vallès Occidental','Vallès Oriental']},
  EX:{name:'Extremadura',sub:['Badajoz','Cáceres']},
  GA:{name:'Galicia',sub:['A Coruña','Lugo','Ourense','Pontevedra']},
  RI:{name:'La Rioja',sub:[]},
  MD:{name:'Madrid',sub:['Madrid Capital','Norte','Sur','Este','Oeste']},
  MU:{name:'Murcia',sub:[]},
  NA:{name:'Navarra',sub:[]},
  PV:{name:'País Vasco',sub:['Álava','Bizkaia','Gipuzkoa']},
  VC:{name:'C. Valenciana',sub:['Alacant','Castelló','València']},
  ES:{name:'Estatal',sub:[]},
};

const NEW_DAYS = 3;

// ── I18N ─────────────────────────────────────────────────────────────────
const I18N = {
  es:{
    lang:'es',dir:'ltr',
    hd_eyebrow:'ADG-FAD · Plataforma Digital', hd_name:'Diseño y Comunicación Visual',
    btn_about:'Acerca de', btn_guide:'Guía', btn_stats:'Estadísticas',
    btn_alerts:'Alertas', btn_csv:'CSV', btn_close:'Cerrar ✕',
    nav_list:'Licitaciones', nav_stats:'Estadísticas', nav_about:'Acerca de', nav_home:'Inicio',
    nav_recursos:'Recursos', nav_mapa:'Mapa',
    st_total:'licitaciones', st_vigent:'abiertas', st_vol:'volumen €',
    st_week:'vencen esta semana', st_new:'recientes', st_loading:'Cargando…',
    st_updated:'Actualizado', st_sample:'Datos de muestra',
    fl_ccaa:'CCAA', fl_comarca:'Provincia / Comarca', fl_all_terr:'Todo el territorio',
    fl_status:'Estado', fl_disc:'Disciplina', fl_all:'Todas',
    s_vigente:'Vigente', s_adjudicado:'Adjudicado', s_desierta:'Desierta',
    s_open:'Abiertas', s_open_badge:'Abierta', s_expired:'Vencida', s_ev:'En evaluación', s_pre:'Pre-adj.',
    sort_rel:'↓ Relevancia', sort_ppto:'↓ Presupuesto',
    sort_vence:'↑ Vence antes', sort_recent:'↓ Más reciente',
    col_licit:'Licitación', col_org:'Organismo', col_ppto:'Presupuesto',
    col_rel:'Relevancia', col_estat:'Estado', col_term:'Termina',
    empty_t:'Sin resultados', empty_s:'Prueba con otros filtros o términos de búsqueda.',
    dp_eyebrow:'Detalle de licitación', dp_disc:'Disciplinas', dp_kw:'Palabras clave',
    dp_hist:'Historial', dp_cta:'Ver en contrataciondelestado.es ↗',
    dp_notify_btn:'Notificarme sobre cambios', dp_notify_submit:'Activar alerta →',
    dp_notify_ok:'Alerta activada',
    modal_title:'Alertas por email',
    modal_desc:'Recibe un email cuando aparezca una nueva licitación que coincida con tus disciplinas y territorio. Sin spam.',
    modal_email:'Email profesional', modal_disc:'Disciplinas de interés',
    modal_terr:'Territorio', modal_submit:'Suscribirme →',
    modal_ok_t:'¡Suscripción registrada!',
    modal_ok_s:'Te avisaremos cuando aparezcan licitaciones que coincidan con tus preferencias.',
    about_title:'Acerca del observatorio',
    nueva:'NUEVA', adjudicado_a:'Adjudicado a', pg_show:'Mostrar',
    guide_title:'Guía de licitaciones para diseñadores',
    sv_overview:'Visión general', sv_by_disc:'Por disciplina',
    sv_by_terr:'Por territorio', sv_by_range:'Rango de presupuesto',
    sv_by_month:'Evolución mensual', sv_adj:'Empresas adjudicatarias',
    sv_conditions:'Condiciones del mercado', sv_plazo:'Plazo medio por disciplina (días)',
    sv_budget_disc:'Presupuesto medio por disciplina', sv_top_orgs:'Organismos que más contratan',
    sv_resultado:'Resultado de licitaciones', sv_tops:'Tops',
    sv_top_ppto:'Mayor presupuesto', sv_top_orgs_vol:'Organismos por volumen',
    sv_top_disc_vol:'Disciplinas por volumen', sv_top_terr:'Territorios por volumen',
    sv_no_data:'Sin datos suficientes', sv_no_adj:'Sin adjudicatarios identificados',
    sv_filter_label:'Filtrando', sv_of:'de',
    nav_alertas:'Alertas',
    fp_eyebrow:'Detalle de licitación', fp_organism:'Organismo',
    fp_budget:'Presupuesto', fp_deadline:'Termina', fp_published:'Publicado',
    fp_type:'Tipo', fp_adjudicado_a:'Adjudicado a', fp_cpv:'CPV', fp_source:'Fuente',
    fp_disciplines:'Disciplinas', fp_keywords:'Palabras clave',
    fp_history:'Historial', fp_no_history:'Sin historial de estados',
    fp_documents:'Documentos', fp_no_docs:'Sin documentos adjuntos todavía',
    fp_f2_ready:'Preparado para enriquecimiento Fetcher 2',
    fp_docs_available:'documentos en la fuente oficial',
    fp_terr:'Territorio', fp_status:'Estado',
    fp_relations:'Licitaciones relacionadas', fp_no_relations:'Sin relaciones',
    fp_view_official:'Ver en contrataciondelestado.es',
    fp_close:'Cerrar', fp_share:'Compartir',
    fp_advisory_tips:'Buenas senales', fp_advisory_warn:'Atencion', fp_advisory_notes:'Notas',
    tl_good:'Buena licitacion', tl_medium:'Valoracion media',
    tl_bad:'Senales negativas', tl_unknown:'Sin valorar',
    sw_stats:'Estadisticas', sw_barometro:'Barometro',
    sw_licit:'Licitaciones', sw_estudios:'Estudios',
    alr_title:'Alertas por email', alr_profile_lbl:'Perfil',
    alr_profile_talent:'Talento / Estudiante', alr_profile_pro:'Profesional',
    alr_criteria_disc:'Disciplinas de interes', alr_criteria_terr:'Territorio',
    alr_criteria_kw:'Palabras clave', alr_criteria_health:'Calidad de licitacion',
    alr_coming_soon_t:'En desarrollo',
    alr_coming_soon_d:'Las alertas estaran disponibles proximamente.',
    alr_notify_btn:'Activar alertas',
  },
  ca:{
    lang:'ca',dir:'ltr',
    hd_eyebrow:'ADG-FAD · Plataforma Digital', hd_name:'Disseny i Comunicació Visual',
    btn_about:"Sobre l'obs.", btn_guide:'Guia', btn_stats:'Estadístiques',
    btn_alerts:'Alertes', btn_csv:'CSV', btn_close:'Tancar ✕',
    nav_list:'Licitacions', nav_stats:'Estadístiques', nav_about:'Sobre nosaltres', nav_home:'Inici',
    nav_recursos:'Recursos', nav_mapa:'Mapa',
    st_total:'licitacions', st_vigent:'obertes', st_vol:'volum €',
    st_week:'vencen aviat', st_new:'recents', st_loading:'Carregant…',
    st_updated:'Actualitzat', st_sample:'Dades de mostra',
    fl_ccaa:'CCAA', fl_comarca:'Província / Comarca', fl_all_terr:'Tot el territori',
    fl_status:'Estat', fl_disc:'Disciplina', fl_all:'Totes',
    s_vigente:'Vigent', s_adjudicado:'Adjudicat', s_desierta:'Deserta',
    s_open:'Obertes', s_open_badge:'Oberta', s_expired:'Vençuda', s_ev:'En avaluació', s_pre:'Pre-adj.',
    sort_rel:'↓ Rellevància', sort_ppto:'↓ Pressupost',
    sort_vence:'↑ Venç aviat', sort_recent:'↓ Més recent',
    col_licit:'Licitació', col_org:'Organisme', col_ppto:'Pressupost',
    col_rel:'Rellevància', col_estat:'Estat', col_term:'Termina',
    empty_t:'Sense resultats', empty_s:'Prova amb altres filtres o termes de cerca.',
    dp_eyebrow:'Detall de licitació', dp_disc:'Disciplines', dp_kw:'Paraules clau',
    dp_hist:'Historial', dp_cta:'Veure a contrataciondelestado.es ↗',
    dp_notify_btn:'Notificar-me sobre canvis', dp_notify_submit:'Activar alerta →',
    dp_notify_ok:'Alerta activada',
    modal_title:'Alertes per email',
    modal_desc:"Rep un email quan aparegui una nova licitació. Sense spam.",
    modal_email:'Email professional', modal_disc:"Disciplines d'interès",
    modal_terr:'Territori', modal_submit:'Subscriure-me →',
    modal_ok_t:'Subscripció registrada!',
    modal_ok_s:"T'avisarem quan apareguin licitacions.",
    about_title:"Sobre l'observatori",
    nueva:'NOVA', adjudicado_a:'Adjudicat a', pg_show:'Mostrar',
    guide_title:'Guia de licitacions per a dissenyadors',
    sv_overview:'Visió general', sv_by_disc:'Per disciplina',
    sv_by_terr:'Per territori', sv_by_range:'Rang de pressupost',
    sv_by_month:'Evolució mensual', sv_adj:'Empreses adjudicatàries',
    sv_conditions:'Condicions del mercat', sv_plazo:'Termini mitjà per disciplina (dies)',
    sv_budget_disc:'Pressupost mitjà per disciplina', sv_top_orgs:'Organismes que més contracten',
    sv_resultado:'Resultat de licitacions', sv_tops:'Tops',
    sv_top_ppto:'Major pressupost', sv_top_orgs_vol:'Organismes per volum',
    sv_top_disc_vol:'Disciplines per volum', sv_top_terr:'Territoris per volum',
    sv_no_data:'Sense dades suficients', sv_no_adj:'Sense adjudicataris identificats',
    sv_filter_label:'Filtrant', sv_of:'de',
    nav_alertas:'Alertes',
    fp_eyebrow:'Detall de licitació', fp_organism:'Organisme',
    fp_budget:'Pressupost', fp_deadline:'Termina', fp_published:'Publicat',
    fp_type:'Tipus', fp_adjudicado_a:'Adjudicat a', fp_cpv:'CPV', fp_source:'Font',
    fp_disciplines:'Disciplines', fp_keywords:'Paraules clau',
    fp_history:'Historial', fp_no_history:'Sense historial d\u0027estats',
    fp_documents:'Documents', fp_no_docs:'Sense documents adjunts encara',
    fp_f2_ready:"Preparat per a l'enriquiment Fetcher 2",
    fp_docs_available:'documents a la font oficial',
    fp_terr:'Territori', fp_status:'Estat',
    fp_relations:'Licitacions relacionades', fp_no_relations:'Sense relacions',
    fp_view_official:'Veure a contrataciondelestado.es',
    fp_close:'Tancar', fp_share:'Compartir',
    fp_advisory_tips:'Bones senyals', fp_advisory_warn:'Atencio', fp_advisory_notes:'Notes',
    tl_good:'Bona licitacio', tl_medium:'Valoracio mitjana',
    tl_bad:'Senyals negatives', tl_unknown:'Sense valorar',
    sw_stats:'Estadistiques', sw_barometro:'Barometre',
    sw_licit:'Licitacions', sw_estudios:'Estudis',
    alr_title:'Alertes per email', alr_profile_lbl:'Perfil',
    alr_profile_talent:'Talent / Estudiant', alr_profile_pro:'Professional',
    alr_criteria_disc:'Disciplines d\u0027interes', alr_criteria_terr:'Territori',
    alr_criteria_kw:'Paraules clau', alr_criteria_health:'Qualitat de licitacio',
    alr_coming_soon_t:'En desenvolupament',
    alr_coming_soon_d:'Les alertes estaran disponibles aviat.',
    alr_notify_btn:'Activar alertes',
  },
  eu:{
    lang:'eu',dir:'ltr',
    hd_eyebrow:'ADG-FAD · Plataforma Digitala', hd_name:'Diseinu eta Ikusizko Komunikazioa',
    btn_about:'Informazioa', btn_guide:'Gida', btn_stats:'Estatistikak',
    btn_alerts:'Alertak', btn_csv:'CSV', btn_close:'Itxi ✕',
    nav_list:'Lizitazioak', nav_stats:'Estatistikak', nav_about:'Informazioa', nav_home:'Hasiera',
    nav_recursos:'Baliabideak', nav_mapa:'Mapa',
    st_total:'lizitazioak', st_vigent:'irekiak', st_vol:'bolumena €',
    st_week:'laster iraungitzen', st_new:'azkenak', st_loading:'Kargatzen…',
    st_updated:'Eguneratua', st_sample:'Lagin datuak',
    fl_ccaa:'AA EE', fl_comarca:'Probintzia / Eskualdea', fl_all_terr:'Lurralde osoa',
    fl_status:'Egoera', fl_disc:'Diziplina', fl_all:'Denak',
    s_vigente:'Indarrean', s_adjudicado:'Esleituta', s_desierta:'Hutsik',
    s_open:'Irekiak', s_open_badge:'Irekia', s_expired:'Iraungita', s_ev:'Ebaluazioan', s_pre:'Pre-adj.',
    sort_rel:'↓ Garrantzia', sort_ppto:'↓ Aurrekontua',
    sort_vence:'↑ Laster iraungitzen', sort_recent:'↓ Berriena',
    col_licit:'Lizitazioa', col_org:'Erakundea', col_ppto:'Aurrekontua',
    col_rel:'Garrantzia', col_estat:'Egoera', col_term:'Amaiera',
    empty_t:'Emaitzarik ez', empty_s:'Saiatu beste iragazki edo bilaketa-termino batzuekin.',
    dp_eyebrow:'Xehetasunak', dp_disc:'Diziplinak', dp_kw:'Gako-hitzak',
    dp_hist:'Historia', dp_cta:'Ikusi contrataciondelestado.es-en ↗',
    dp_notify_btn:'Jakinarazi aldaketei buruz', dp_notify_submit:'Alerta aktibatu →',
    dp_notify_ok:'Alerta aktibatuta',
    modal_title:'Email alertak', modal_desc:'Jaso email bat lizitazio berri bat agertzen denean.',
    modal_email:'Email profesionala', modal_disc:'Intereseko diziplinak',
    modal_terr:'Lurraldea', modal_submit:'Harpidetu →',
    modal_ok_t:'Harpidetza erregistratuta!', modal_ok_s:'Jakinaraziko dizugu.',
    about_title:'Behatokiari buruz',
    nueva:'BERRIA', adjudicado_a:'Esleituta', pg_show:'Erakutsi',
    guide_title:'Lizitazioen gida diseinatzaileentzat',
    sv_overview:'Ikuspegi orokorra', sv_by_disc:'Diziplinaren arabera',
    sv_by_terr:'Lurraldearen arabera', sv_by_range:'Aurrekontu-tartea',
    sv_by_month:'Hileko eboluzioa', sv_adj:'Esleipendunak',
    sv_conditions:'Merkatuaren baldintzak', sv_plazo:'Batez besteko epea diziplinaren arabera',
    sv_budget_disc:'Batez besteko aurrekontua diziplinaren arabera',
    sv_top_orgs:'Gehien kontratatzen duten erakundeak',
    sv_resultado:'Lizitazioen emaitza', sv_tops:'Top-ak',
    sv_top_ppto:'Aurrekontu handiena', sv_top_orgs_vol:'Erakundeak bolumenaren arabera',
    sv_top_disc_vol:'Diziplinak bolumenaren arabera', sv_top_terr:'Lurraldeak bolumenaren arabera',
    sv_no_data:'Ez dago datu nahikorik', sv_no_adj:'Ez da esleipendunik identifikatu',
    sv_filter_label:'Iragazten', sv_of:'/',
    fp_no_docs:'Oraindik ez dago dokumentu erantsirik',
    fp_f2_ready:'Fetcher 2 aberasterako prestatuta',
  },
  gl:{
    lang:'gl',dir:'ltr',
    hd_eyebrow:'ADG-FAD · Plataforma Dixital', hd_name:'Deseño e Comunicación Visual',
    btn_about:'Sobre nós', btn_guide:'Guía', btn_stats:'Estatísticas',
    btn_alerts:'Alertas', btn_csv:'CSV', btn_close:'Pechar ✕',
    nav_list:'Licitacións', nav_stats:'Estatísticas', nav_about:'Sobre nós', nav_home:'Inicio',
    nav_recursos:'Recursos', nav_mapa:'Mapa',
    st_total:'licitacións', st_vigent:'abertas', st_vol:'volume €',
    st_week:'vencen axiña', st_new:'recentes', st_loading:'Cargando…',
    st_updated:'Actualizado', st_sample:'Datos de mostra',
    fl_ccaa:'CCAA', fl_comarca:'Provincia / Comarca', fl_all_terr:'Todo o territorio',
    fl_status:'Estado', fl_disc:'Disciplina', fl_all:'Todas',
    s_vigente:'Vixente', s_adjudicado:'Adxudicado', s_desierta:'Deserta',
    s_open:'Abertas', s_open_badge:'Aberta', s_expired:'Vencida', s_ev:'En avaliación', s_pre:'Pre-adj.',
    sort_rel:'↓ Relevancia', sort_ppto:'↓ Orzamento',
    sort_vence:'↑ Vence antes', sort_recent:'↓ Máis recente',
    col_licit:'Licitación', col_org:'Organismo', col_ppto:'Orzamento',
    col_rel:'Relevancia', col_estat:'Estado', col_term:'Remata',
    empty_t:'Sen resultados', empty_s:'Proba con outros filtros ou termos de busca.',
    dp_eyebrow:'Detalle da licitación', dp_disc:'Disciplinas', dp_kw:'Palabras clave',
    dp_hist:'Historial', dp_cta:'Ver en contrataciondelestado.es ↗',
    dp_notify_btn:'Notificarme sobre cambios', dp_notify_submit:'Activar alerta →',
    dp_notify_ok:'Alerta activada',
    modal_title:'Alertas por email', modal_desc:'Recibe un email cando aparezan novas licitacións. Sen spam.',
    modal_email:'Email profesional', modal_disc:'Disciplinas de interese',
    modal_terr:'Territorio', modal_submit:'Subscribirme →',
    modal_ok_t:'Subscrición rexistrada!', modal_ok_s:'Avisarémoste cando aparezan licitacións.',
    about_title:'Sobre o observatorio',
    nueva:'NOVA', adjudicado_a:'Adxudicado a', pg_show:'Mostrar',
    guide_title:'Guía de licitacións para deseñadores',
    sv_overview:'Visión xeral', sv_by_disc:'Por disciplina',
    sv_by_terr:'Por territorio', sv_by_range:'Rango de orzamento',
    sv_by_month:'Evolución mensual', sv_adj:'Empresas adxudicatarias',
    sv_conditions:'Condicións do mercado', sv_plazo:'Prazo medio por disciplina (días)',
    sv_budget_disc:'Orzamento medio por disciplina', sv_top_orgs:'Organismos que máis contratan',
    sv_resultado:'Resultado das licitacións', sv_tops:'Tops',
    sv_top_ppto:'Maior orzamento', sv_top_orgs_vol:'Organismos por volume',
    sv_top_disc_vol:'Disciplinas por volume', sv_top_terr:'Territorios por volume',
    sv_no_data:'Sen datos suficientes', sv_no_adj:'Sen adxudicatarios identificados',
    sv_filter_label:'Filtrando', sv_of:'de',
    nav_alertas:'Alertas',
    fp_eyebrow:'Detalle da licitacion', fp_organism:'Organismo',
    fp_budget:'Orzamento', fp_deadline:'Remata', fp_published:'Publicado',
    fp_type:'Tipo', fp_adjudicado_a:'Adxudicado a', fp_cpv:'CPV', fp_source:'Fonte',
    fp_disciplines:'Disciplinas', fp_keywords:'Palabras clave',
    fp_history:'Historial', fp_no_history:'Sen historial de estados',
    fp_documents:'Documentos', fp_no_docs:'Sen documentos adxuntos aínda',
    fp_f2_ready:'Preparado para enriquecemento Fetcher 2',
    fp_terr:'Territorio', fp_status:'Estado',
    fp_relations:'Licitacions relacionadas', fp_no_relations:'Sen relacions',
    fp_view_official:'Ver en contrataciondelestado.es',
    fp_close:'Pechar', fp_share:'Compartir',
    fp_advisory_tips:'Boas sinais', fp_advisory_warn:'Atencio', fp_advisory_notes:'Notas',
    tl_good:'Boa licitacion', tl_medium:'Valoracion media',
    tl_bad:'Sinais negativos', tl_unknown:'Sen valorar',
    sw_stats:'Estatisticas', sw_barometro:'Barometro',
    sw_licit:'Licitacions', sw_estudios:'Estudos',
    alr_title:'Alertas por email', alr_profile_lbl:'Perfil',
    alr_profile_talent:'Talento / Estudante', alr_profile_pro:'Profesional',
    alr_criteria_disc:'Disciplinas de interese', alr_criteria_terr:'Territorio',
    alr_criteria_kw:'Palabras clave', alr_criteria_health:'Calidade da licitacion',
    alr_coming_soon_t:'En desenvolvemento',
    alr_coming_soon_d:'As alertas estaran disponibles proximamente.',
    alr_notify_btn:'Activar alertas',
  },
};

// ── SAMPLE DATA (fallback when data.json not found) ───────────────────────
const TODAY_ISO = new Date().toISOString().slice(0,10);
const SAMPLE = [
  {id:'s1',titol:'Diseño de identidad corporativa y manual de marca — Ajuntament de Girona',organisme:'Ajuntament de Girona',adjudicatari:'',tipus:'Servicios',pressupost:28500,disciplines:['branding','editorial'],ccaa:'CT',lloc:'Catalunya',data_pub:TODAY_ISO,data_limit:'2026-04-20',estat:'Vigente',rellevancia:95,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['identidad corporativa','diseño gráfico','manual de marca'],historial:[]},
  {id:'s2',titol:'Servicio de diseño gráfico y producción de materiales — SEPE',organisme:'Servicio Público de Empleo Estatal',adjudicatari:'',tipus:'Servicios',pressupost:120000,disciplines:['editorial','impressio'],ccaa:'MD',lloc:'Madrid',data_pub:'2026-03-08',data_limit:'2026-04-15',estat:'Vigente',rellevancia:92,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['diseño gráfico','materiales de comunicación'],historial:[]},
  {id:'s3',titol:"Diseño museográfico y señalética — MNAC",organisme:"Museu Nacional d'Art de Catalunya",adjudicatari:'Studio Baldrich S.L.',tipus:'Servicios',pressupost:320000,disciplines:['senyaletica','branding'],ccaa:'CT',lloc:'Catalunya',data_pub:'2026-02-18',data_limit:'2026-03-01',estat:'Adjudicado',rellevancia:90,url:'https://contractaciopublica.gencat.cat',font:'PLACSP',kw:['señalética','museografía'],historial:[{data:'2026-02-01',estat:'Vigente',nota:'Publicación'},{data:'2026-03-05',estat:'Adjudicado',nota:'Adjudicado a Studio Baldrich S.L.'}]},
  {id:'s4',titol:'Campaña publicitaria de promoción turística — Agència Catalana de Turisme',organisme:'Agència Catalana de Turisme',adjudicatari:'',tipus:'Servicios',pressupost:450000,disciplines:['publicitat','branding'],ccaa:'CT',lloc:'Catalunya',data_pub:'2026-03-07',data_limit:'2026-04-10',estat:'Vigente',rellevancia:88,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['campaña publicitaria'],historial:[]},
  {id:'s5',titol:'Producción audiovisual y motion graphics — RTVE',organisme:'RTVE',adjudicatari:'',tipus:'Servicios',pressupost:85000,disciplines:['audiovisual'],ccaa:'MD',lloc:'Madrid',data_pub:'2026-03-01',data_limit:'2026-04-05',estat:'Vigente',rellevancia:83,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['producción audiovisual','motion graphics'],historial:[]},
  {id:'s6',titol:'Serveis de fotografia institucional — Diputació de Barcelona',organisme:'Diputació de Barcelona',adjudicatari:'',tipus:'Servicios',pressupost:22000,disciplines:['fotografia'],ccaa:'CT',lloc:'Catalunya',data_pub:'2026-02-28',data_limit:'2026-04-01',estat:'Vigente',rellevancia:80,url:'https://contractaciopublica.gencat.cat',font:'PLACSP',kw:['fotografía'],historial:[]},
  {id:'s7',titol:'Diseño web y sistema de comunicación digital — Gobierno de Navarra',organisme:'Gobierno de Navarra',adjudicatari:'',tipus:'Servicios',pressupost:195000,disciplines:['web','uxui'],ccaa:'NA',lloc:'Navarra',data_pub:'2026-02-25',data_limit:'2026-04-25',estat:'Vigente',rellevancia:78,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['diseño web','UX','UI'],historial:[]},
  {id:'s8',titol:'Ilustración editorial para campaña — Junta de Andalucía',organisme:'Junta de Andalucía',adjudicatari:'',tipus:'Servicios',pressupost:18000,disciplines:['illustracio','editorial'],ccaa:'AN',lloc:'Andalucía',data_pub:'2026-03-10',data_limit:'2026-03-28',estat:'Vigente',rellevancia:75,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['ilustración','editorial'],historial:[]},
  {id:'s9',titol:'Impresión y producción gráfica de materiales institucionales — Ministerio de Cultura',organisme:'Ministerio de Cultura',adjudicatari:'Gràfiques Valls S.A.',tipus:'Servicios',pressupost:67000,disciplines:['impressio','editorial'],ccaa:'MD',lloc:'Madrid',data_pub:'2026-01-15',data_limit:'2026-02-01',estat:'Adjudicado',rellevancia:72,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['impresión','producción gráfica'],historial:[{data:'2026-01-15',estat:'Vigente',nota:'Publicación'},{data:'2026-02-08',estat:'Adjudicado',nota:'Adjudicado a Gràfiques Valls S.A.'}]},
  {id:'s10',titol:'Señalética y rotulación — Ayuntamiento de Vitoria-Gasteiz',organisme:'Ayuntamiento de Vitoria-Gasteiz',adjudicatari:'',tipus:'Servicios',pressupost:35000,disciplines:['senyaletica'],ccaa:'PV',lloc:'País Vasco',data_pub:'2026-03-05',data_limit:'2026-04-30',estat:'Desierta',rellevancia:70,url:'https://contrataciondelestado.es',font:'PLACSP',kw:['señalética','rotulación'],historial:[{data:'2026-03-05',estat:'Vigente',nota:'Publicación'},{data:'2026-04-02',estat:'Desierta',nota:'Declarada desierta por falta de ofertas'}]},
];

// ── SHARED STATE ─────────────────────────────────────────────────────────
window.ADG = window.ADG || {};
ADG.data = [];
ADG.canonicalData = [];
ADG.generatedAt = null;
ADG.dataRefreshedAt = null;
ADG.datasetMeta = {};
ADG.isSample = false;
ADG.lang = localStorage.getItem('adg-lang') || 'es';
ADG.theme = localStorage.getItem('adg-theme') || 'light';
ADG.version = '0.5.0m';

// ── UTILS ─────────────────────────────────────────────────────────────────
const el = id => document.getElementById(id);

function t(key) {
  const tr = I18N[ADG.lang] || I18N.es;
  return key ? (tr[key] || I18N.es[key] || key) : tr;
}

function fmt(n) {
  if (!n && n !== 0) return '—';
  if (n >= 1_000_000) return (n/1_000_000).toFixed(1).replace('.0','') + 'M €';
  if (n >= 1_000)     return Math.round(n/1_000) + 'K €';
  return n.toLocaleString('es-ES') + ' €';
}

function fmtFull(n) {
  if (!n && n !== 0) return '—';
  return n.toLocaleString('es-ES', { style:'currency', currency:'EUR', maximumFractionDigits:0 });
}

function daysTo(dateStr) {
  if (!dateStr) return null;
  const diff = (new Date(dateStr) - new Date()) / 86400000;
  return Math.ceil(diff);
}

function isNew(row) {
  if (!row.data_pub) return false;
  return daysTo(row.data_pub) > -NEW_DAYS;
}

function discColor(key) {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  const d = DISC[key];
  if (!d) return { text:'var(--text2)', bg:'var(--bg2)', border:'var(--border2)' };
  return { text: dark ? d.ld : d.lc, bg: dark ? d.bd : d.bg, border: dark ? d.ld : d.lc };
}

function discTag(key, iconSize = '8.5px') {
  const d = DISC[key];
  if (!d) return '';
  const c = discColor(key);
  return `<span class="disc-tag" style="color:${c.text};background:${c.bg};border-color:${c.text}20">
    <i class="bi ${d.icon}" style="font-size:${iconSize}"></i>${d.label}
  </span>`;
}

function stateBadge(estat) {
  if (estat === 'Vigente')    return `<span class="badge b-ok"><i class="bi bi-circle-fill" style="font-size:6px"></i>${t('s_vigente')}</span>`;
  if (estat === 'Adjudicado') return `<span class="badge b-adj"><i class="bi bi-flag-fill" style="font-size:7px"></i>${t('s_adjudicado')}</span>`;
  if (estat === 'Desierta')   return `<span class="badge b-des"><i class="bi bi-x-circle-fill" style="font-size:7px"></i>${t('s_desierta')}</span>`;
  return `<span class="badge">${estat}</span>`;
}

function getDisplayStatus(row) {
  const raw  = (row.estat_raw || '').toUpperCase();
  const days = daysTo(row.data_limit);
  if (raw === 'PUB') {
    return (days === null || days >= 0)
      ? { key:'open',       label:t('s_open_badge'), cssClass:'b-ok',   icon:'bi-circle-fill'    }
      : { key:'expired',    label:t('s_expired'),    cssClass:'b-warn', icon:'bi-clock'           };
  }
  if (raw === 'EV')  return { key:'ev',         label:t('s_ev'),         cssClass:'b-warn', icon:'bi-hourglass-split' };
  if (raw === 'PRE') return { key:'pre',        label:t('s_pre'),        cssClass:'b-warn', icon:'bi-hourglass-split' };
  if (raw === 'ADJ' || raw === 'RES') return { key:'adjudicado', label:t('s_adjudicado'), cssClass:'b-adj', icon:'bi-flag-fill'     };
  if (raw === 'ANUL') return { key:'desierta',  label:t('s_desierta'),   cssClass:'b-des',  icon:'bi-x-circle-fill'  };
  // Fallback: derive from stored estat (covers sample data without estat_raw)
  const estat = row.estat || '';
  if (estat === 'Adjudicado') return { key:'adjudicado', label:t('s_adjudicado'), cssClass:'b-adj', icon:'bi-flag-fill'    };
  if (estat === 'Desierta')   return { key:'desierta',   label:t('s_desierta'),   cssClass:'b-des', icon:'bi-x-circle-fill' };
  if (estat === 'Vigente')    return { key:'open',       label:t('s_open_badge'), cssClass:'b-ok',  icon:'bi-circle-fill'  };
  return { key:'unknown', label:estat || '?', cssClass:'', icon:'' };
}

function isOpenOpportunity(row) {
  return getDisplayStatus(row).key === 'open';
}

function stateBadgeRow(row) {
  const ds = getDisplayStatus(row);
  if (!ds.cssClass) return `<span class="badge">${ds.label || '?'}</span>`;
  return `<span class="badge ${ds.cssClass}"><i class="bi ${ds.icon}" style="font-size:6px"></i>${ds.label}</span>`;
}

function applyI18n() {
  document.documentElement.lang = ADG.lang;
  document.querySelectorAll("[data-i18n]").forEach(node => {
    const val = t(node.dataset.i18n);
    if (!val || val === node.dataset.i18n) return;
    if (node.children.length === 0) node.textContent = val;
  });
  document.querySelectorAll("select option[data-i18n]").forEach(opt => {
    const val = t(opt.dataset.i18n);
    if (val) opt.textContent = val;
  });
  document.querySelectorAll("[data-estat]").forEach(btn => {
    const map = {"":"fl_all","open":"s_open","adjudicado":"s_adjudicado","desierta":"s_desierta"};
    const key = map[btn.dataset.estat];
    if (!key) return;
    const val = t(key);
    const span = btn.querySelector("span[data-i18n]");
    if (span) span.textContent = val;
  });
  document.querySelectorAll(".lang-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.lang === ADG.lang);
  });
}

function applyTheme(theme) {
  ADG.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  const icon = el('theme-icon');
  if (icon) icon.className = 'bi bi-' + (theme === 'dark' ? 'sun' : 'moon-stars');
  localStorage.setItem('adg-theme', theme);
}

async function loadData() {
  ADG.data = SAMPLE;
  ADG.canonicalData = SAMPLE;
  ADG.isSample = true;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    const r = await fetch(`./data/licitaciones.json?t=${Date.now()}`, { signal: controller.signal });
    clearTimeout(timeout);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const raw = await r.json();
    const items = Array.isArray(raw) ? raw : (raw.data || []);
    if (items.length) {
      items.forEach(normalizeItem);
      ADG.data = items;
      ADG.canonicalData = buildCanonicalRecords(items);
      ADG.datasetMeta = raw.meta || {};
      ADG.generatedAt = raw.meta?.generated_at || raw.generated_at || null;
      ADG.dataRefreshedAt = raw.meta?.scheduled_merge_applied_at || raw.meta?.generated_at || raw.generated_at || null;
      ADG.fetcher_version = raw.meta?.version || raw.meta?.fetcher_version || raw.fetcher_version || '?';
      ADG.isSample = false;
    }
  } catch (e) {
    console.warn('[ADG] licitaciones.json failed or timed out, using sample:', e.message);
  }
  document.dispatchEvent(new Event('adg:loaded'));
}

// ── CANONICAL COLLAPSE ────────────────────────────────────────────────────
function pickCanonicalEntry(a, b) {
  var ar = a.rec, br = b.rec;
  var aHasKey = !!(ar.canonical_key || ar.contract_folder_id);
  var bHasKey = !!(br.canonical_key || br.contract_folder_id);
  if (bHasKey && !aHasKey) return b;
  if (aHasKey && !bHasKey) return a;
  var aRank = ar.status_rank != null ? Number(ar.status_rank) : -1;
  var bRank = br.status_rank != null ? Number(br.status_rank) : -1;
  if (bRank !== aRank) return bRank > aRank ? b : a;
  var aDate = ar.last_notice_date || '';
  var bDate = br.last_notice_date || '';
  if (bDate !== aDate) return bDate > aDate ? b : a;
  var aPub = ar.data_pub || '';
  var bPub = br.data_pub || '';
  if (bPub !== aPub) return bPub > aPub ? b : a;
  var aHasAdj = !!(ar.adjudicatari || (ar.award_results && ar.award_results.length > 0));
  var bHasAdj = !!(br.adjudicatari || (br.award_results && br.award_results.length > 0));
  if (bHasAdj && !aHasAdj) return b;
  if (aHasAdj && !bHasAdj) return a;
  var aDocs = (ar.documents || []).length;
  var bDocs = (br.documents || []).length;
  if (bDocs !== aDocs) return bDocs > aDocs ? b : a;
  return b.origIdx > a.origIdx ? b : a;
}

function buildCanonicalRecords(records) {
  var groups = new Map();
  records.forEach(function(r, idx) {
    var key = r.id || r.url || ('__idx__' + idx);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push({ rec: r, origIdx: idx });
  });
  var result = [];
  groups.forEach(function(entries) {
    if (entries.length === 1) { result.push(entries[0].rec); return; }
    var best = entries[0];
    for (var i = 1; i < entries.length; i++) best = pickCanonicalEntry(best, entries[i]);
    result.push(best.rec);
  });
  return result;
}

function normalizeItem(r) {
  if (r.font && /^LOCAL(?:-ZIP)?$/.test(r.font)) r.font = 'PLACSP';
  if (r.adjudicatari) {
    if (/detalle|adjudicaci/i.test(r.adjudicatari)) {
      r.adjudicatari = '';
    } else {
      r.adjudicatari = r.adjudicatari
        .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n))
        .replace(/<[^>]+>/g, '')
        .replace(/\s+/g, ' ').trim();
    }
  }
  return r;
}

function initShared() {
  applyTheme(ADG.theme);
  const themeBtn = el('btn-theme');
  if (themeBtn) themeBtn.addEventListener('click', () => {
    applyTheme(ADG.theme === 'light' ? 'dark' : 'light');
    document.dispatchEvent(new Event('adg:themechange'));
  });
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      ADG.lang = btn.dataset.lang;
      localStorage.setItem('adg-lang', ADG.lang);
      applyI18n();
      document.dispatchEvent(new Event('adg:langchange'));
    });
  });
  applyI18n();
  document.querySelectorAll('[data-adg-version]').forEach(function(vEl){ vEl.textContent = ADG.version; });
  initMobileNav();
  updateTicker();
}

// ── MOBILE NAV MENU (p180) ────────────────────────────────────────────────
// At mobile widths the header actions (nav tabs, language, theme) collapse
// behind a single menu toggle. Injected here so every page inherits the same
// control without duplicating markup that could drift. Desktop is untouched:
// the toggle stays display:none > 860px and .header-actions renders inline.
function initMobileNav() {
  const header = document.querySelector('.header');
  const actions = header && header.querySelector('.header-actions');
  if (!header || !actions || header.querySelector('.nav-toggle')) return;

  const btn = document.createElement('button');
  btn.className = 'nav-toggle hbtn';
  btn.type = 'button';
  btn.setAttribute('aria-label', 'Menú');
  btn.setAttribute('aria-expanded', 'false');
  btn.innerHTML = '<i class="bi bi-list"></i>';
  header.appendChild(btn);

  const setOpen = (open) => {
    header.classList.toggle('nav-open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    const i = btn.querySelector('i');
    if (i) i.className = open ? 'bi bi-x' : 'bi bi-list';
  };

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    setOpen(!header.classList.contains('nav-open'));
  });
  // Selecting a nav target or language closes the menu.
  actions.addEventListener('click', (e) => {
    if (e.target.closest('.nav-tab') || e.target.closest('.lang-btn')) setOpen(false);
  });
  // Click outside the menu/toggle closes it.
  document.addEventListener('click', (e) => {
    if (!header.classList.contains('nav-open')) return;
    if (e.target.closest('.header-actions') || e.target.closest('.nav-toggle')) return;
    setOpen(false);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 860 && header.classList.contains('nav-open')) setOpen(false);
  });
}

function updateTicker() {
  const tk = t('st_total') || 'licitaciones';
  const count = (ADG.canonicalData || ADG.data).length || '';
  const msg = count ? `${count} ${tk}` : '';
  ['tk-a','tk-b'].forEach(id => { const e = el(id); if (e) e.textContent = msg; });
}

function updateStrip() {
  const d = ADG.canonicalData || ADG.data;
  const setEl = (id, val) => { const e = el(id); if (e) e.textContent = val; };
  setEl('s-total',  d.length);
  setEl('s-vigent', d.filter(r => isOpenOpportunity(r)).length);
  setEl('s-vol',    fmt(d.reduce((s,r) => s + (r.pressupost||0), 0)));
  setEl('s-warn',   d.filter(r => { const n = daysTo(r.data_limit); return isOpenOpportunity(r) && n !== null && n >= 0 && n <= 7; }).length);
  setEl('s-new',    d.filter(isNew).length);
  const uEl = el('s-update');
  if (!uEl) return;
  if (ADG.isSample) {
    uEl.innerHTML = `<strong>${t('st_sample')}</strong>`;
  } else if (ADG.dataRefreshedAt) {
    const d2 = new Date(ADG.dataRefreshedAt);
    const date = d2.toLocaleDateString(ADG.lang + '-ES', {day:'2-digit',month:'short',year:'numeric'});
    const time = d2.toLocaleTimeString(ADG.lang + '-ES', {hour:'2-digit',minute:'2-digit'});
    uEl.innerHTML = `<strong>${t('st_updated')}</strong> ${date} ${time}`;
  } else {
    uEl.innerHTML = `Datos cargados`;
  }
  updateTicker();
}

function initModal() {
  const overlay = el('overlay');
  if (!overlay) return;
  const open = () => overlay.classList.add('open');
  const close = () => overlay.classList.remove('open');
  const subBtn = el('btn-subscribe');
  const mc = el('modal-close');
  const form = el('sub-form');
  if (subBtn) subBtn.addEventListener('click', open);
  if (mc) mc.addEventListener('click', close);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  if (form) form.addEventListener('submit', async e => {
    e.preventDefault();
    try {
      const res = await fetch(e.target.action, { method:'POST', body:new FormData(e.target), headers:{Accept:'application/json'} });
      if (res.ok) { el('modal-form-wrap').style.display = 'none'; el('modal-success').style.display = 'block'; }
    } catch { alert('Configura el FORM_ID de Formspree.'); }
  });
}

window.ADG_Utils = { el, t, fmt, fmtFull, daysTo, isNew, discColor, discTag, stateBadge, getDisplayStatus, isOpenOpportunity, stateBadgeRow, applyI18n, updateStrip, updateTicker, initShared, initModal, loadData, loadJSON, buildCanonicalRecords };

async function loadJSON(path, timeoutMs) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs || 4000);
    const r = await fetch(`${path}?t=${Date.now()}`, { signal: controller.signal });
    clearTimeout(timer);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const raw = await r.json();
    return Array.isArray(raw) ? raw : (raw.data || raw);
  } catch (e) {
    console.warn('[ADG] loadJSON failed for', path, e.message);
    return null;
  }
}

