# ADG_EXTENSIONS_030 — Module Overlay Matrix

**Version:** v0.1.3.1
**Status:** ACTIVE FOUNDATION / DOC-ONLY
**Mode:** FOUNDATION_FIRST / MODULE_OVERLAY_MATRIX
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**last_synced_txt:** 128
**source_audit_txt:** 127
**shared_base_doc:** ADG_EXTENSIONS_029_SHARED_BASE_v0.1.3.1.md
**source_commit:** a1810ec
**base_checkpoint_tag:** adg-extensions-shared-base-v0.1.3.1
**Git write operations by Claude CLI:** FORBIDDEN
**Source/data status:** NO SOURCE, DATA, ACTIVE SURFACE, SUPPORT, OR PRIVATE FILES TOUCHED

---

## 0. What This Document Is

This document persists the module overlay matrix produced by the TXT 127 audit. It is the decision surface for all ADG Extensions modules and lanes — every routing state, data state, governance need, gate state, blocker, and advancement decision is recorded here in one place.

This document inherits `ADG_EXTENSIONS_029_SHARED_BASE_v0.1.3.1.md` Layers A through G as its shared foundation. All enum definitions, gate templates, data doctrine, governance workflow, QA template, hygiene checklist, and the module overlay template in doc 029 Layers A–G are considered inherited here and are not duplicated.

This document does **not** authorize source, data, active-surface, support, or private-file work of any kind. It is planning and foundation canon only.

---

## 1. Source Basis

This document was produced from the following foundation docs. No private, support, data, or member file contents were read at any point.

| Doc | Purpose |
|---|---|
| `ADG_EXTENSIONS_029_SHARED_BASE_v0.1.3.1.md` | Shared base / foundation; Layers A–G; module registry; gate templates |
| `ADG_EXTENSIONS_020_ID_TAXONOMY_REGISTRY_v0.1.3.1.md` | ID taxonomy; naming conventions; dataset registry; §§1–4, §§9–13 canonical |
| `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.1.md` | Extension framework; phase/state model; extension list |
| `ADG_EXTENSIONS_001_LAUS_TRACKER_v0.1.3.1.md` | LAUS module governance and field contracts |
| `ADG_EXTENSIONS_002_DIRECTORIO_SOCIOS_v0.1.3.1.md` | Directorio framework doc |
| `ADG_EXTENSIONS_003_OPPORTUNITIES_FRAMEWORK_v0.1.3.1.md` | Oportunidades framework |
| `ADG_EXTENSIONS_003A_BOLSA_PRACTICAS_v0.1.3.1.md` | Bolsa de Prácticas lane |
| `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1.md` | Freelancers + Profesional lanes |
| `ADG_EXTENSIONS_004_ALERTAS_EMAIL_v0.1.3.1.md` | Alertas framework doc |
| `ADG_EXTENSIONS_007_MOCK_DATA_MODULE_ARCHITECTURE_v0.1.3.1_PLAN.md` | Mock data architecture; three-tier classification |
| `ADG_EXTENSIONS_008_DATA_ID_TABLE_CONTRACT_v0.1.3.1_PLAN.md` | Data ID table contract; column contracts; SQL-readiness |
| `ADG_EXTENSIONS_021_ALERTAS_CONSENT_DELIVERY_CONTRACT_v0.1.3.1_PLAN.md` | Alertas consent/delivery contract; locked decisions D1–D10; 10 pre-activation gates |
| `ADG_EXTENSIONS_022_OPORTUNIDADES_PROCESS_CONTRACT_v0.1.3.1_PLAN.md` | Oportunidades process contract; locked decisions OD1–OD16 |
| `ADG_EXTENSIONS_023_DIRECTORIO_DATA_PRIVACY_CONTRACT_v0.1.3.1_PLAN.md` | Directorio data/privacy contract; locked decisions DD1–DD17; 11 privacy gates |
| `ADG_EXTENSIONS_028_MAP_TAXONOMY_CLOSURE_v0.1.3.1.md` | Map taxonomy closure; mapa_licitaciones vs mapa_socios naming |
| `ADG_EXTENSIONS_BATCH_1.3.1_INDEX_v0.1.3.1.md` | Batch baseline index; module state table; active reading order |

No private/support/data/member contents were read. `docs/support_copys/**` was not accessed. `data/**` contents were not opened. All data-readiness assessments were inferred from docs and contracts only.

---

## 2. Matrix Model

### Column Definitions

| Column | Type | Definition |
|---|---|---|
| `module_id` | string | Canonical module identifier from doc 020 / doc 029 Layer A |
| `module_family` | enum | `active_surface` / `extension_module` / `support_page` / `infrastructure` |
| `human_label` | string | Display name for the module or lane |
| `route_state` | enum | See doc 029 Layer A §1 enum — `active`, `active_prehub`, `active_shell`, `stub_shell`, `tombstone`, `blocked`, `prohibited` |
| `index_state` | enum | `active` / `hold` / `deferred_final_lane` / `not_applicable` |
| `data_state` | enum | `active_public` / `partial_public` / `mock_only` / `no_data` / `blocked_by_gate` / `not_applicable` |
| `governance_state` | string | `not_applicable` / `template_inherited` / `partial` / `blocked` |
| `gate_state_summary` | string | `all_closed` / `N gates open` / `not_applicable` |
| `QA_state` | string | Checklist status relative to doc 029 Layer E base template |
| `blockers_to_100` | string | Outstanding blockers to theoretical 100% |
| `risk_level` | enum | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `can_advance` | enum | `NOW` / `LATER` / `END` / `HOLD` |
| `inherited_layers` | string | Layers from doc 029 that apply: A, B, C, D, E, F, G |
| `next_TXT_lane` | string | Next TXT scope for this module |
| `notes` | string | Module-specific deltas or hard rules |

### Allowed Values — `risk_level`

`LOW` — no personal data, no gate risk, branch-scope constraint only
`MEDIUM` — data/process gates open; advancement depends on contracts; real but manageable risk
`HIGH` — privacy/legal gates open; real personal data of real people or high-risk intake
`CRITICAL` — activation without gate closure would cause consent/legal violation or irreversible harm

### Allowed Values — `can_advance`

`NOW` — no blocking gates; work can proceed in current TXT lane
`LATER` — blocked by gate or branch constraint; can advance after closure or reopen
`END` — deferred final lane; closed until operator opens final lane sequence
`HOLD` — explicit hold; must not advance until named unblock condition is met

---

## 3. Full Module Overlay Matrix

### Module 01 — Hub / Index Route Architecture

| Field | Value |
|---|---|
| `module_id` | `mod-home-hub` |
| `module_family` | `support_page` |
| `human_label` | Home / Hub (index.html) |
| `route_state` | `active` |
| `index_state` | `not_applicable` (this IS the index) |
| `data_state` | `active_public` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `all_closed` |
| `QA_state` | Base Layer E §5.2 index smoke required; 7 active cards + 2 HOLD divs must pass at every QA cycle |
| `blockers_to_100` | Active-surface reopen required for content/card-state changes; QA must confirm no href on HOLD cards each cycle |
| `risk_level` | LOW |
| `can_advance` | LATER — active surface reopen required for any card-state change |
| `inherited_layers` | A, E, F |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | HOLD cards: card-directorio-socios and card-alertas-email must remain `<div>` with no href at all times; 7 active cards must point to tracked HTML files |

---

### Module 02 — Licitaciones

| Field | Value |
|---|---|
| `module_id` | `mod-licitaciones` |
| `module_family` | `active_surface` |
| `human_label` | Observatorio de Licitaciones |
| `route_state` | `active` |
| `index_state` | `active` |
| `data_state` | `active_public` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Base Layer E §5.5 active surface smoke; confirm licitaciones.html loads with data |
| `blockers_to_100` | Active-surface reopen required for any feature or content work (branch-scope constraint) |
| `risk_level` | LOW |
| `can_advance` | LATER — active surface reopen required |
| `inherited_layers` | A, E, F |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | Out of scope in extensions branch; do not touch source; PLACSP data feed is authoritative |

---

### Module 03 — Mapa del Diseño / mapa_licitaciones

| Field | Value |
|---|---|
| `module_id` | `mod-mapa-diseno` |
| `module_family` | `active_surface` |
| `human_label` | Mapa del Diseño (mapa_licitaciones) |
| `route_state` | `active` — mapa.html |
| `index_state` | `active` |
| `data_state` | `active_public` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Base Layer E §5.5 active surface smoke; confirm map renders |
| `blockers_to_100` | Active-surface reopen required; Guía licitaciones migration from licitaciones.html blocked (doc 028 §6) until reopen |
| `risk_level` | LOW |
| `can_advance` | LATER — active surface reopen required |
| `inherited_layers` | A, E, F |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | Canonical route name is `mapa_licitaciones`; mapa.html must not be renamed; distinct from mapa_socios (doc 028) |

---

### Module 04 — Recursos / Calculadora

| Field | Value |
|---|---|
| `module_id` | `mod-recursos-calculadora` |
| `module_family` | `active_surface` |
| `human_label` | Recursos + Calculadora |
| `route_state` | `active_prehub` (recursos-prehub.html) / `active` (recursos.html) |
| `index_state` | `active` |
| `data_state` | `active_public` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Base Layer E §5.3 prehub smoke; confirm child card links recursos.html; confirm future sub-lane placeholders show honest stubs if present |
| `blockers_to_100` | Active-surface reopen required; future sub-lanes (Guía, Plantillas legales, Referencias personales) defined in prehub architecture but not yet wired or routed |
| `risk_level` | LOW |
| `can_advance` | LATER — active surface reopen required |
| `inherited_layers` | A, E, F |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | Prehub parent of recursos.html and future child lanes; Guía licitaciones migration accepted as product direction (doc 028) but blocked until active-surface reopen |

---

### Module 05 — Plantillas Legales

| Field | Value |
|---|---|
| `module_id` | `mod-plantillas-legales` (sub-lane of recursos-prehub) |
| `module_family` | `extension_module` |
| `human_label` | Plantillas Legales |
| `route_state` | `blocked` — no route created; defined as future recursos-prehub child |
| `index_state` | `not_applicable` — sub-lane, not in index directly |
| `data_state` | `no_data` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` (no personal data; public content only) |
| `QA_state` | Not yet applicable — route does not exist |
| `blockers_to_100` | Active-surface reopen of Recursos prehub; route does not exist |
| `risk_level` | LOW |
| `can_advance` | LATER — requires Recursos prehub reopen |
| `inherited_layers` | A |
| `next_TXT_lane` | TXT 131 — active surface QA batch (Recursos reopen) |
| `notes` | Defined in prehub architecture as a future recursos-prehub child lane; not yet wired; no source or data created |

---

### Module 06 — Referencias Personales

| Field | Value |
|---|---|
| `module_id` | `mod-referencias-personales` (sub-lane of recursos-prehub) |
| `module_family` | `extension_module` |
| `human_label` | Referencias Personales |
| `route_state` | `blocked` — no route created; defined as future recursos-prehub child |
| `index_state` | `not_applicable` |
| `data_state` | `no_data` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Not yet applicable |
| `blockers_to_100` | Active-surface reopen of Recursos prehub; route does not exist |
| `risk_level` | LOW |
| `can_advance` | LATER — requires Recursos prehub reopen |
| `inherited_layers` | A |
| `next_TXT_lane` | TXT 131 — active surface QA batch (Recursos reopen) |
| `notes` | Defined in prehub architecture as a future recursos-prehub child lane; no source or data created |

---

### Module 07 — Guía de Licitaciones para Diseñadores

| Field | Value |
|---|---|
| `module_id` | `mod-guia-licitaciones` (sub-lane of recursos-prehub) |
| `module_family` | `extension_module` |
| `human_label` | Guía de Licitaciones para Diseñadores |
| `route_state` | `blocked` — no route created; migration from licitaciones.html blocked (doc 028 §6) |
| `index_state` | `not_applicable` |
| `data_state` | `no_data` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Not yet applicable |
| `blockers_to_100` | Active-surface reopen of both Recursos prehub and Licitaciones; migration block per doc 028 §6; route does not exist |
| `risk_level` | LOW |
| `can_advance` | LATER — requires active-surface reopen |
| `inherited_layers` | A |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | Doc 028 §6 accepted as product direction; migration from licitaciones.html explicitly blocked until active-surface reopen; no unauthorized link from licitaciones.html |

---

### Module 08 — Estadísticas Forense

| Field | Value |
|---|---|
| `module_id` | `mod-estadisticas-forense` |
| `module_family` | `active_surface` |
| `human_label` | Estadísticas Forense |
| `route_state` | `active_prehub` (estadisticas-prehub.html) / `active` (estadisticas.html) |
| `index_state` | `active` |
| `data_state` | `active_public` |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Base Layer E §5.3 prehub smoke; confirm both index cards (estadisticas + barómetro) route to estadisticas-prehub.html; confirm estadisticas.html loads with data |
| `blockers_to_100` | Active-surface reopen required for feature work |
| `risk_level` | LOW |
| `can_advance` | LATER — active surface reopen required |
| `inherited_layers` | A, E, F |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | Shares estadisticas-prehub.html with Barómetro; both index cards (card-estadisticas-forense and card-barometro-sector) route to the same prehub |

---

### Module 09 — Barómetro del Sector

| Field | Value |
|---|---|
| `module_id` | `mod-barometro-sector` |
| `module_family` | `active_surface` |
| `human_label` | Barómetro del Sector |
| `route_state` | `tombstone` — barometro.html redirects/deprecated notice → estadisticas.html |
| `index_state` | `active` — card points to estadisticas-prehub.html |
| `data_state` | `active_public` (toggle inside estadisticas; out of scope in branch) |
| `governance_state` | `not_applicable` |
| `gate_state_summary` | `not_applicable` |
| `QA_state` | Confirm barometro.html tombstone behavior (redirect or deprecated notice); confirm it does NOT render as a standalone active module; confirm no live data or interactive features on barometro.html |
| `blockers_to_100` | Active-surface reopen; tombstone behavior must be preserved — do not activate barometro.html as standalone module |
| `risk_level` | LOW |
| `can_advance` | LATER — tombstone is correct current state; any change requires active-surface reopen |
| `inherited_layers` | A, E, F |
| `next_TXT_lane` | TXT 131 — active surface QA batch |
| `notes` | TOMBSTONE — barometro.html must show redirect or deprecated notice only; must not render as standalone active module; card still in index but points to estadisticas-prehub.html, not barometro.html directly |

---

### Module 10 — LAUS Tracker

| Field | Value |
|---|---|
| `module_id` | `mod-laus-tracker` |
| `module_family` | `extension_module` |
| `human_label` | LAUS Tracker |
| `route_state` | `active_prehub` (laus-prehub.html) / `active_shell` (laus.html) |
| `index_state` | `active` |
| `data_state` | `partial_public` — Tier A editions + juries (2016–2018 full; 2019–2026 seed only) |
| `governance_state` | `template_inherited` — doc 001 |
| `gate_state_summary` | partial — data expansion paused; expansion TXT not yet authorized |
| `QA_state` | Base Layer E §5.3 prehub smoke; §5.4 child surface smoke; confirm partial data renders; confirm no broken expansion references; confirm honest empty/Próximamente state for unavailable records |
| `blockers_to_100` | Awards, schools, studios data blocked by data contract (doc 008); expansion paused; 2019–2026 editions seed only; full LAUS expansion requires operator authorization + source audit |
| `risk_level` | MEDIUM |
| `can_advance` | LATER — data expansion requires operator authorization and source audit |
| `inherited_layers` | A, B, C, E, F |
| `next_TXT_lane` | TXT 132 — LAUS data expansion readiness |
| `notes` | Fake award winners are absolutely forbidden under any circumstances — honest empty/Próximamente state is always correct; expansion contract in doc 008 must be re-authorized before any import |

---

### Module 11 — LAUS Stats

| Field | Value |
|---|---|
| `module_id` | `mod-laus-stats` |
| `module_family` | `extension_module` |
| `human_label` | LAUS Stats |
| `route_state` | `active_shell` — laus-stats.html |
| `index_state` | `active` (via laus-prehub.html) |
| `data_state` | `partial_public` — inherits LAUS Tracker data constraint |
| `governance_state` | `template_inherited` — doc 001 |
| `gate_state_summary` | partial — same data expansion constraint as LAUS Tracker |
| `QA_state` | Base Layer E §5.4 child surface smoke; confirm shell renders honest empty/partial state; no broken data references |
| `blockers_to_100` | Same as LAUS Tracker — awards/schools/studios blocked; stats aggregation unavailable until full expansion authorized |
| `risk_level` | MEDIUM |
| `can_advance` | LATER — same expansion authorization as LAUS Tracker |
| `inherited_layers` | A, B, C, E, F |
| `next_TXT_lane` | TXT 132 — LAUS data expansion readiness |
| `notes` | Child of laus-prehub.html; stats aggregation not available until full LAUS expansion is operator-authorized; must show honest partial state |

---

### Module 12 — Oportunidades ADG Parent

| Field | Value |
|---|---|
| `module_id` | `mod-oportunidades-adg` |
| `module_family` | `extension_module` |
| `human_label` | Oportunidades ADG (prehub) |
| `route_state` | `active_prehub` — oportunidades.html |
| `index_state` | `active` |
| `data_state` | `no_data` |
| `governance_state` | `partial` — moderation-mandatory model locked; manual-intake-only locked; admin ownership not formally designated (OD5) |
| `gate_state_summary` | partial — OD14 (legal terms for submitting organizations) open; admin ownership open; Freelancers/Profesional deep fichas open |
| `QA_state` | Base Layer E §5.3 prehub smoke; confirm 3 child cards render; confirm no forms active on any surface |
| `blockers_to_100` | Freelancers deep ficha; Profesional deep ficha; OD14 legal terms; admin ownership designation; no public self-submit until intake/privacy contract approved |
| `risk_level` | MEDIUM |
| `can_advance` | LATER — Prácticas data contract is ready for doc/schema work when operator authorizes; Freelancers/Profesional blocked by deep fichas |
| `inherited_layers` | A, B, C, F |
| `next_TXT_lane` | Data seed TXT (Prácticas only, when operator authorizes separately) |
| `notes` | Hard product doctrine: submission ≠ publication; no automatic publishing ever; all 3 children are shells with no live data |

---

### Module 13 — Bolsa de Prácticas

| Field | Value |
|---|---|
| `module_id` | `mod-practicas` |
| `module_family` | `extension_module` |
| `human_label` | Bolsa de Prácticas |
| `route_state` | `active_shell` — oportunidades-practicas.html |
| `index_state` | `active` (via oportunidades prehub) |
| `data_state` | `no_data` — field schema locked (doc 022 §11A); no data files exist |
| `governance_state` | `template_inherited` — doc 022 |
| `gate_state_summary` | partial — OD14 (legal terms for submitting organizations) open; admin ownership designation open |
| `QA_state` | Base Layer E §5.4 child surface smoke; confirm shell shows honest empty state; NEGATIVE: no forms active; no mock listings rendered |
| `blockers_to_100` | OD14 (legal terms for submitting organizations); admin ownership designation; no public self-submit until intake/privacy contract separately approved |
| `risk_level` | MEDIUM |
| `can_advance` | LATER — field schema is locked and ready for data contract implementation when operator explicitly authorizes |
| `inherited_layers` | A, B, C, F |
| `next_TXT_lane` | Prácticas data seed TXT (when operator authorizes separately) |
| `notes` | Most advanced child lane — field schema locked per doc 022 §11A; ready for data seed when operator gives explicit authorization; no self-submit in current scope |

---

### Module 14 — Bolsa de Freelancers

| Field | Value |
|---|---|
| `module_id` | `mod-freelancers` |
| `module_family` | `extension_module` |
| `human_label` | Bolsa de Freelancers |
| `route_state` | `active_shell` — oportunidades-freelancers.html |
| `index_state` | `active` (via oportunidades prehub) |
| `data_state` | `blocked_by_gate` — deep ficha required before field set is locked |
| `governance_state` | `partial` — deep ficha required |
| `gate_state_summary` | open — deep ficha not closed; field set currently provisional |
| `QA_state` | Base Layer E §5.4; NEGATIVE: no forms active; no data rendered; no submitter email fields in public HTML |
| `blockers_to_100` | Deep ficha required (HIGH if bypassed — field set is provisional); legal terms for submitting organizations; contact_policy locked as via_adg until separately changed |
| `risk_level` | HIGH (if deep ficha bypassed) |
| `can_advance` | HOLD — deep ficha must close before any field set is locked or data work begins |
| `inherited_layers` | A, B, C, F |
| `next_TXT_lane` | Deep ficha TXT (when operator authorizes) |
| `notes` | All contact exposure is via ADG only (contact_policy: via_adg); no public phone, email, or direct contact fields in MVP; deep ficha is a prerequisite — not optional |

---

### Module 15 — Bolsa Profesional

| Field | Value |
|---|---|
| `module_id` | `mod-profesional` |
| `module_family` | `extension_module` |
| `human_label` | Bolsa Profesional |
| `route_state` | `active_shell` — oportunidades-profesional.html |
| `index_state` | `active` (via oportunidades prehub) |
| `data_state` | `blocked_by_gate` — deep ficha required before field set is locked |
| `governance_state` | `partial` — deep ficha required |
| `gate_state_summary` | open — deep ficha not closed; field set currently provisional |
| `QA_state` | Base Layer E §5.4; NEGATIVE: no forms active; no data rendered |
| `blockers_to_100` | Deep ficha required (same as Freelancers); canonical name decision already locked |
| `risk_level` | HIGH (if deep ficha bypassed) |
| `can_advance` | HOLD — deep ficha must close before any field set is locked or data work begins |
| `inherited_layers` | A, B, C, F |
| `next_TXT_lane` | Deep ficha TXT (when operator authorizes) |
| `notes` | Canonical name is "Bolsa Profesional" — the deprecated name "Bolsa de Puestos Profesionales" must not be reintroduced in any doc, source, or commit message |

---

### Module 16 — Directorio de Socios

| Field | Value |
|---|---|
| `module_id` | `mod-directorio-socios` |
| `module_family` | `extension_module` |
| `human_label` | Directorio de Socios |
| `route_state` | `active_shell` (directorio.html — unlinked shell prehub parent, not reachable from index) / `blocked` (directorio-socios.html) |
| `index_state` | `hold` — card-directorio-socios is `<div>` with no href |
| `data_state` | `blocked_by_gate` — all data creation blocked by 11 privacy gates; listado_socios_onlynames.txt FORBIDDEN to read without gate clearance |
| `governance_state` | `partial` — ownership model defined; correction/erasure channel not yet operational |
| `gate_state_summary` | 11 gates open — see doc 023 §16 and doc 029 Layer D §4.6 |
| `QA_state` | NEGATIVE: card-directorio-socios no href; directorio.html not reachable via index; directorio-socios.html not reachable via directorio.html; mapa-socios.html not linked; no adg_members data anywhere; listado_socios_onlynames.txt path not referenced in any tracked source file |
| `blockers_to_100` | All 11 privacy/legal gates from doc 023 §16 (CRITICAL — all open); ADG-FAD board authorization is hardest dependency; specialty vocabulary must be operator-approved before filter activation |
| `risk_level` | HIGH — real personal data of real people; privacy/legal complexity |
| `can_advance` | HOLD — all 11 gates must close; explicit operator decision required at TXT 130 |
| `inherited_layers` | A, B, C, D, F |
| `next_TXT_lane` | TXT 130 — Directorio exposure decision |
| `notes` | Two-tier consent model (entities admin-curated vs individuals explicit opt-in only); unclaimed individual profiles never shown publicly in MVP; phone field absolutely forbidden for public; claiming of profiles deferred to MVP+; mapa_socios inherits all 11 gates |

---

### Module 17 — mapa_socios

| Field | Value |
|---|---|
| `module_id` | `mod-mapa-socios` |
| `module_family` | `extension_module` |
| `human_label` | mapa_socios |
| `route_state` | `blocked` — mapa-socios.html; HOLD_PRIVACY |
| `index_state` | `hold` — not in index; not linked from directorio.html |
| `data_state` | `blocked_by_gate` — inherits all Directorio gates |
| `governance_state` | `partial` — inherits Directorio governance; additionally requires operator_shell_authorization gate |
| `gate_state_summary` | 11 gates open (inherits all Directorio gates); additionally: operator_shell_authorization gate open |
| `QA_state` | NEGATIVE: mapa-socios.html not linked from directorio.html or any other tracked surface; no member data of any kind |
| `blockers_to_100` | All 11 Directorio privacy gates (CRITICAL); OR explicit operator shell authorization for zero-data shell (alternative path only) |
| `risk_level` | HIGH — inherits full Directorio privacy gate complexity |
| `can_advance` | HOLD — until Directorio gates close OR operator explicitly authorizes shell-only creation with zero member data |
| `inherited_layers` | A, B, D, F |
| `next_TXT_lane` | TXT 130 — Directorio exposure decision (shared with Directorio) |
| `notes` | Shell-only path is available if operator explicitly authorizes a zero-data shell of mapa-socios.html; if shell-only authorized: no member names, no profiles, no real locations; distinct from mapa_licitaciones (doc 028) — naming confusion is permanently closed |

---

### Module 18 — Alertas por Email

| Field | Value |
|---|---|
| `module_id` | `mod-alertas-email` |
| `module_family` | `extension_module` |
| `human_label` | Alertas por Email |
| `route_state` | `stub_shell` — alertas.html (AlertasStub component; honest coming-soon UI) |
| `index_state` | `deferred_final_lane` — card-alertas-email is `<div>` with no href |
| `data_state` | `blocked_by_gate` — schema defined (doc 021); no data files exist or are permitted |
| `governance_state` | `partial` — manual-first v1 workflow locked (D2); admin ownership not formally designated |
| `gate_state_summary` | 10 gates open — see doc 021 §14 and doc 029 Layer D §4.8; CRITICAL: D6 (legal/privacy review) is a REQUIRED GATE, not optional commentary |
| `QA_state` | NEGATIVE: card-alertas-email no href; alertas.html shows stub UI only; no subscription form active; no XHR/fetch/form action; all AlertasStub inputs disabled; no email provider connected; no data capture of any kind |
| `blockers_to_100` | D6 (legal/privacy review — CRITICAL — requires qualified external reviewer); all 10 Alertas pre-activation gates (doc 021 §14 — all open); must not be reopened without explicit operator instruction |
| `risk_level` | CRITICAL — if activated without consent gates: email capture without consent; irreversible regulatory exposure |
| `can_advance` | END — DEFERRED_FINAL_LANE; only after all other modules are assessed and operator opens final lane sequence explicitly |
| `inherited_layers` | A, B, C, D, F |
| `next_TXT_lane` | TXT 133 — Alertas final lane |
| `notes` | AlertasStub keyword + health signal fields are prototype artifacts, NOT contracted MVP scope (D5 locked); contracted MVP scope: discipline + territory + frequency only; Formspree and Google Forms explicitly excluded (removed TXT 052; must not be reintroduced); no Alertas implementation work of any kind may proceed without explicit operator instruction |

---

### Module 19 — Mock / Data Architecture

| Field | Value |
|---|---|
| `module_id` | (cross-cutting infrastructure) |
| `module_family` | `infrastructure` |
| `human_label` | Mock / Data Architecture |
| `route_state` | `not_applicable` |
| `index_state` | `not_applicable` |
| `data_state` | doc-bound — three-tier classification locked (doc 007); mock strategy locked; no data/mock/ committed to public repo without explicit operator decision |
| `governance_state` | `template_inherited` — doc 007, doc 008 |
| `gate_state_summary` | partial — schema locks active; SQL-readiness contract in doc 008; per-module data contracts must close before any live data creation |
| `QA_state` | Confirm no data/mock/ committed without authorization; confirm Tier A data in correct public paths; confirm no private/member data in public paths; confirm no mock rows in data/public/ |
| `blockers_to_100` | Per-module data contracts must close before any live data creation; mock policy must be followed across all modules |
| `risk_level` | LOW — doc-bound; no source work needed |
| `can_advance` | NOW — doc-bound; data architecture is complete at this layer |
| `inherited_layers` | B, F |
| `next_TXT_lane` | TXT 129 — PANOPTES/GRC public hygiene audit (includes data file hygiene) |
| `notes` | Mock data must never appear in data/public/; realistic-looking mock names forbidden (use obviously fake names like "Estudio de Prueba SA"); data/mock/ directory not committed to public repo without operator decision |

---

### Module 20 — ID Taxonomy / Registry

| Field | Value |
|---|---|
| `module_id` | (cross-cutting infrastructure) |
| `module_family` | `infrastructure` |
| `human_label` | ID Taxonomy / Registry |
| `route_state` | `not_applicable` |
| `index_state` | `not_applicable` |
| `data_state` | `not_applicable` |
| `governance_state` | `template_inherited` — doc 020 |
| `gate_state_summary` | foundation complete — doc 020 §§1–4 and §§9–13 canonical; doc 029 Layer A supersedes doc 020 §§5–8 and §15; doc 020 carries amendment pointer note |
| `QA_state` | Confirm naming conventions (doc 020 §§1–4) followed in all new modules; confirm no deprecated names reintroduced (e.g., "Bolsa de Puestos Profesionales") |
| `blockers_to_100` | None — foundation complete and active |
| `risk_level` | LOW |
| `can_advance` | NOW — foundation complete |
| `inherited_layers` | A |
| `next_TXT_lane` | TXT 129 — PANOPTES/GRC public hygiene audit |
| `notes` | Naming conventions in doc 020 §§1–4 remain canonical and are not superseded; reserved prefix list must be consulted before any new module ID is assigned |

---

### Module 21 — Public Hygiene / Release Lane

| Field | Value |
|---|---|
| `module_id` | (cross-cutting infrastructure) |
| `module_family` | `infrastructure` |
| `human_label` | Public Hygiene / PANOPTES Release Lane |
| `route_state` | `not_applicable` |
| `index_state` | `not_applicable` |
| `data_state` | `not_applicable` |
| `governance_state` | `template_inherited` — doc 029 Layer F |
| `gate_state_summary` | open — PANOPTES/GRC audit not yet run against current HEAD (a1810ec) |
| `QA_state` | Full Layer F checklist (doc 029 §§6.1–6.6) must be run; pre-push checks; pre-release checks; gitignore verification for support_copys/ and prompt files |
| `blockers_to_100` | PANOPTES/GRC audit must be run against current HEAD; all Layer F checklist items must pass; private file boundary must be verified |
| `risk_level` | LOW |
| `can_advance` | NOW — TXT 129 is the next immediate lane |
| `inherited_layers` | F |
| `next_TXT_lane` | TXT 129 — PANOPTES/GRC public hygiene audit |
| `notes` | TXT 129 is the first lane after this document; includes: private/public file boundary check, gitignore verification, no-API-key check, pre-push checklist execution against a1810ec; Claude CLI does not push; operator performs all staging and push manually |

---

## 4. Module Groups / Priority Order

### Group A — Stable / No Immediate Work Needed

Modules in this group are either complete at this layer or have no blocking work in the current TXT sequence. No doc, source, or data action is needed to advance them beyond periodic QA.

| Module | Reason |
|---|---|
| Hub / index route architecture | Active; stable; HOLD cards confirmed; QA only at each cycle |
| ID taxonomy / registry | Foundation complete; naming conventions active; doc 020 canonical |
| Mock / data architecture | Three-tier classification locked; doc-bound; no source work needed |

---

### Group B — Can Advance via Docs / Overlay Now

Modules in this group can move forward within the current doc-only lane without source or data changes.

| Module | Advance path |
|---|---|
| Public hygiene / PANOPTES release lane | TXT 129 runs PANOPTES/GRC audit — first post-128 lane |
| ID taxonomy / registry | Available for doc-level reference in all overlay docs |
| Mock / data architecture | Available for per-module data contract docs when operator authorizes |

---

### Group C — Needs QA Only

Modules in this group need only a QA smoke pass. No new implementation, data, or source changes are needed — they are waiting for a QA batch audit when their surface type is reopened.

| Module | QA type |
|---|---|
| Licitaciones | Active surface smoke (Layer E §5.5) |
| Mapa del Diseño | Active surface smoke (Layer E §5.5) |
| Recursos + Calculadora | Prehub smoke (Layer E §5.3) + child surface smoke |
| Estadísticas Forense | Prehub smoke (Layer E §5.3) + child surface smoke |
| Barómetro del Sector | Tombstone behavior QA — must NOT render as standalone module |

All Group C modules are blocked by the active-surface reopen gate. They advance together in TXT 131.

---

### Group D — Needs Privacy / Legal / Governance Closure

Modules in this group cannot advance until named governance, privacy, or legal gates are closed by the operator.

| Module | Gate burden |
|---|---|
| Directorio de Socios | 11 privacy gates (doc 023 §16) — all open; ADG-FAD authorization hardest |
| mapa_socios | Inherits all 11 Directorio gates + operator_shell_authorization gate |
| Bolsa de Freelancers | Deep ficha required; field set provisional |
| Bolsa Profesional | Deep ficha required; field set provisional |

None of these modules may receive source, data, or form work until the operator explicitly closes the named gates.

---

### Group E — Needs Data / Process Contract Before Implementation

Modules in this group have their route and shell state settled but cannot progress to data implementation until a named data/process contract is authorized by the operator.

| Module | Blocking contract |
|---|---|
| LAUS Tracker | Data expansion contract (doc 008) must be re-authorized; awards/schools/studios blocked |
| LAUS Stats | Same as LAUS Tracker |
| Oportunidades ADG (parent) | Admin ownership designation; OD14 legal terms |
| Bolsa de Prácticas | OD14 open; admin ownership; schema locked and ready |
| Plantillas Legales | Recursos prehub reopen required |
| Referencias Personales | Recursos prehub reopen required |
| Guía de Licitaciones | Recursos prehub reopen + Licitaciones reopen required |

---

### Group F — Deferred Final Lane

Modules that must not be reopened without explicit operator instruction. Work on these modules in any TXT before their named final lane is absolutely prohibited.

| Module | Final lane TXT |
|---|---|
| Alertas por Email | TXT 133 — all 10 gates must close first; D6 (legal/privacy review) is a REQUIRED GATE |

---

### Group G — Public Hygiene / Release

The cross-cutting hygiene and release lane. It runs first after this document and sets the safety baseline for all future module advances.

| Module | Next TXT |
|---|---|
| Public hygiene / PANOPTES release lane | TXT 129 |

---

## 5. Blocker Map to Theoretical 100%

### Route / Status Blockers

| Blocker | Affected modules |
|---|---|
| Active-surface reopen required (branch constraint) | Licitaciones, Mapa del Diseño, Recursos + Calculadora, Estadísticas Forense, Barómetro del Sector, Hub |
| No route created yet (future prehub child lanes) | Plantillas Legales, Referencias Personales, Guía de Licitaciones |
| Route blocked by 11 privacy gates | Directorio de Socios (directorio-socios.html), mapa_socios (mapa-socios.html) |
| Route is DEFERRED_FINAL_LANE only | Alertas por Email (alertas.html is stub; card is div with no href) |
| Tombstone state must be preserved | Barómetro del Sector (barometro.html → estadisticas.html) |

---

### Data / Process Blockers

| Blocker | Affected modules |
|---|---|
| LAUS expansion contract (doc 008) not re-authorized | LAUS Tracker, LAUS Stats (awards, schools, studios data blocked) |
| No listings data; Prácticas schema locked but no data contract opened | Oportunidades ADG, Bolsa de Prácticas |
| Deep ficha required before data contracts | Bolsa de Freelancers, Bolsa Profesional |
| All data blocked by 11 privacy gates | Directorio de Socios, mapa_socios |
| All data blocked by 10 consent/delivery gates | Alertas por Email |
| No routes / no contracts for future sub-lanes | Plantillas Legales, Referencias Personales, Guía de Licitaciones |

---

### Governance / Admin Blockers

| Blocker | Affected modules |
|---|---|
| Admin ownership not formally designated | Oportunidades ADG (OD5), Bolsa de Prácticas, Alertas por Email |
| Correction / erasure channel not operational | Directorio de Socios |
| Admin access rights not formally approved for send approval | Alertas por Email |
| Deep ficha closure required before governance model locks | Bolsa de Freelancers, Bolsa Profesional |

---

### Privacy / Legal / Consent Blockers

| Blocker | Affected modules |
|---|---|
| All 11 Directorio privacy gates open (doc 023 §16) | Directorio de Socios, mapa_socios |
| ADG-FAD board authorization (hardest gate; requires board/association action) | Directorio de Socios, mapa_socios |
| D6 — Legal/privacy review (REQUIRED GATE for any Alertas activation) | Alertas por Email |
| All 10 Alertas pre-activation gates open (doc 021 §14) | Alertas por Email |
| OD14 — Legal terms for submitting organizations | Bolsa de Prácticas, Oportunidades ADG |
| Deep ficha — field set provisional; contact_policy via_adg | Bolsa de Freelancers, Bolsa Profesional |

---

### QA Blockers

| Blocker | Affected modules |
|---|---|
| PANOPTES/GRC audit not yet run against current HEAD | All modules (cross-cutting) |
| Active surface QA batch not yet run (TXT 131) | Licitaciones, Mapa, Recursos, Estadísticas, Barómetro, Hub |
| LAUS module-specific QA delta not yet run | LAUS Tracker, LAUS Stats |
| Prehub smoke not yet formally confirmed in current state | Recursos, Estadísticas, LAUS, Oportunidades |
| Negative route / HOLD checks must be re-verified at each QA cycle | Directorio, mapa_socios, Alertas |

---

### Public Hygiene Blockers

| Blocker | Affected modules |
|---|---|
| PANOPTES/GRC audit not yet run against a1810ec | All (cross-cutting; TXT 129) |
| Pre-push checklist not yet formally confirmed for current state | All (cross-cutting) |
| GitIgnore verification for docs/support_copys/ and prompt files | Cross-cutting |

---

### Final-Lane Blockers

| Blocker | Affected modules |
|---|---|
| All 10 Alertas gates must close before final lane opens | Alertas por Email |
| D6 (legal/privacy review — REQUIRED GATE) requires external qualified reviewer | Alertas por Email |
| Operator must explicitly open final lane sequence | Alertas por Email |
| Alertas must not be reopened in any TXT before TXT 133 | Alertas por Email |

---

## 6. Recommended TXT Sequence

| TXT | Lane | Scope |
|---|---|---|
| **TXT 128** | current — module overlay matrix doc implementation | Create `ADG_EXTENSIONS_030_MODULE_OVERLAY_MATRIX_v0.1.3.1.md` (this document) |
| **TXT 129** | PANOPTES/GRC public hygiene audit | Run full Layer F checklist against a1810ec; verify private/public file boundary; verify gitignore rules; verify pre-push conditions; no source changes |
| **TXT 130** | Directorio exposure decision | Operator decision audit: which (if any) Directorio/mapa_socios gate can be advanced; define unblock path; no source changes until decision |
| **TXT 131** | Active surface QA batch | Smoke-level QA against all active surface routes (Licitaciones, Mapa, Recursos, Estadísticas, Barómetro, Hub); prehub smoke; tombstone verification; no source changes |
| **TXT 132** | LAUS data expansion readiness | Audit LAUS Tracker + LAUS Stats data state; operator decision on expansion contract; define data import path if authorized |
| **TXT 133** | Alertas final lane | Open Alertas final lane sequence only after all 10 gates are closed by operator; D6 (legal/privacy review) is a REQUIRED GATE for this TXT to proceed |

**Numbering note:** This TXT sequence shifted from the earlier roadmap because doc 030 (this document) now occupies TXT 128. All prior roadmap references to TXT numbers after 127 are superseded by the sequence above.

---

## 7. HOLD Register

| Hold | Reason | Unblock condition | TXT |
|---|---|---|---|
| Directorio index activation (card-directorio-socios href) | 11 privacy/legal gates open (doc 023 §16) | All 11 gates explicitly closed by operator; card link activation is its own named gate | TXT 130 |
| directorio.html linking from index | Not linked until card-directorio-socios href is separately authorized | Explicit operator authorization of card link activation gate | TXT 130 |
| directorio-socios.html creation / activation | Blocked child; all 11 gates open | All 11 Directorio gates closed | TXT 130 |
| mapa-socios.html creation / linking | Inherits all 11 Directorio gates | All 11 gates closed OR explicit operator shell-only authorization with zero member data | TXT 130 |
| Alertas por Email activation | DEFERRED_FINAL_LANE; all 10 consent/delivery gates open (doc 021 §14); D6 is REQUIRED | All 10 gates closed; operator opens final lane sequence explicitly | TXT 133 only |
| Active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro) | Out of implementation scope in extensions branch; active production surfaces | Dedicated active-surface reopen prompt; separate audit and IMP sequence | TXT 131 |
| Data / listings / forms / provider / capture (Oportunidades, Directorio, Alertas) | Data and process contracts not fully closed per module | Per-module gate closure; explicit operator authorization | Per module |
| LAUS expansion (awards, schools, studios) | Data contract (doc 008) not re-authorized; expansion paused | Operator authorization + source audit | TXT 132 |
| Bolsa de Freelancers deep ficha | Field set currently provisional; data blocked | Deep ficha TXT authorized by operator | To be named |
| Bolsa Profesional deep ficha | Field set currently provisional; data blocked | Deep ficha TXT authorized by operator | To be named |
| Recursos sub-lanes (Plantillas, Referencias, Guía) | No routes or contracts; blocked by Recursos prehub constraint | Recursos active-surface reopen | TXT 131 |
| Private / member / support data | No contract exists for any private data use | Explicit operator contract naming file, purpose, and scope | Contract required |
| `git add .` | Hard rule — always forbidden; broad staging risks committing private/artifact files | Never — operator uses explicit file-level `git add` only | Permanent |

---

## 8. STOP

- No source HTML, CSS, or JS edits.
- No data file writes.
- No active surface edits.
- No support / private / member file reads.
- No git mutations by Claude CLI. All staging, commit, push, and tag operations are performed by the operator manually.
- This document is planning and foundation canon only.
- No writes beyond this file were performed in TXT 128.
