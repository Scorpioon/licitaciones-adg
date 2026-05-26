# ADG_EXTENSIONS_020 — ID Taxonomy Registry

**Version:** v0.1.3.1  
**Status:** ACTIVE  
**Mode:** CANON / ID_REGISTRY  
**Branch:** extensions  
**Owner scope:** ADG Extensions  
**Source basis:** TXT 056 audit + TXT 057 decisions + extensions_doc canon  
**Date:** 2026-05-21  
**Git write operations:** FORBIDDEN to Claude CLI — operator performs all staging and commits

---

## AMENDMENT NOTE — TXT 125 / v0.1.3.1

**Added by:** TXT 125 (shared base doc implementation)
**Amendment type:** Pointer / supersession notice — historical text below is preserved unchanged

`ADG_EXTENSIONS_029_SHARED_BASE_v0.1.3.1.md` is now the current source of truth for:
- route/module registry (§5 of this doc)
- hub card registry (§6 of this doc)
- route registry (§7 of this doc)
- subhub/prehub mappings (§8 of this doc)
- current route state, HOLD state, and tombstone register

**This amendment supersedes §§5–8 and §15 of this document.**

The following sections of this document **remain canonical** and are not superseded:
- §1 Purpose
- §2 Canon Summary
- §3 Naming Conventions
- §4 Reserved Prefixes
- §9 Dataset Registry
- §10 SQL-Readiness Contract
- §11 Mock Data Policy
- §13 Retired / Stale Items
- §14 Open Questions (Confirmation State)

**Last synced commit:** cc5ec6a
**Checkpoint tag:** adg-extensions-prehub-routes-v0.1.3.1

---

## 1. Purpose

This registry defines stable, canonical IDs for all ADG Extensions modules, hub cards, routes, subhubs, and datasets before further implementation begins.

Goals:
- Prevent ID drift across implementation prompts
- Enable future SQL migration from JSON seeds
- Anchor module identity to DOM attributes for traceability and analytics hooks
- Document which modules are implementation targets in this branch and which are not

This registry does **not** authorize implementation on active surfaces.  
This registry does **not** create subhub routes.  
This registry does **not** activate any extension module.

---

## 2. Canon Summary

| Rule | Value |
|---|---|
| Global hub | `index.html` — the only entry point; hosts all module cards |
| `extensions.html` | DELETED — prohibited; must never be recreated, referenced, or linked |
| Active surfaces | Out of implementation scope in this branch (inventory IDs assigned for completeness only) |
| Extension modules | In scope for contracts, stub maintenance, subhub planning, and data architecture |
| Data doctrine | All data must be SQL-ready: JSON file = table, JSON object = row, `id` = primary key |
| Mock data | Must be explicitly marked; never masquerades as public/real records |
| Subhub routes | Created only when the module is ready to render meaningful content and its contract is approved |

---

## 3. Naming Conventions

| Layer | Convention | Example |
|---|---|---|
| DOM `id=` attributes | `kebab-case` | `card-laus-tracker`, `modal-close` |
| CSS class names | `kebab-case` with `--` modifier | `.home-card`, `.home-card--live`, `.home-card--soon` |
| JavaScript variables / functions | `camelCase` | `loadData`, `AlertasStub`, `isSubscribed` |
| i18n keys (app.js `I18N`) | `snake_case` with namespace prefix | `nav_home`, `alr_title`, `modal_desc` |
| JSON data field names | `snake_case` | `source_file`, `category_id`, `import_batch` |
| JSON data `id` values | `kebab-case` with domain prefix | `laus-ed-2026`, `laus-jury-2026-001` |
| SQL table names (future) | `snake_case`, plural | `laus_editions`, `laus_juries` |
| SQL column names (future) | `snake_case` | `category_id`, `import_batch`, `source_file` |

**Immutability rule:** Once an `id` is assigned and in production/canon use it must never change. If a slug must be corrected, add a `replaced_by` pointer — do not alter the original `id`.

**Deprecation rule:** Deprecated IDs receive `deprecated: true` and a `replaced_by` field. They are never deleted from the registry.

**Forbidden in IDs:** spaces, accented characters, uppercase letters, visual-order or positional meaning.

---

## 4. Reserved Prefixes

| Prefix | Scope | Convention | Example |
|---|---|---|---|
| `mod-` | Module identity | `mod-{domain-slug}` | `mod-laus-tracker` |
| `surf-` | Active surface identity (reserved; use `mod-` for inventory) | `surf-{slug}` | `surf-licitaciones` |
| `card-` | Hub card DOM `id=` | `card-{module-slug}` | `card-laus-tracker` |
| `route-` | Route identity | `route-{slug}` | `route-laus` |
| `subhub-` | Subhub page identity | `subhub-{slug}` | `subhub-oportunidades` |
| `feat-` | Feature within a module | `feat-{module}-{slug}` | `feat-laus-jury-table` |
| `ds-` | Dataset / data domain identity | `ds-{domain}` | `ds-laus-juries` |
| `tbl-` | SQL table name (future reference only) | `tbl-{domain}_{entity}` | `tbl-laus_juries` |
| `src-` | Source / provenance identifier | `src-{slug}` | `src-adg-public` |
| `batch-` | Import batch identifier | `phase{n}-{scope}-{year}-v{version}` | `phase2r4c-full-juries-2016-v0.1.3.1` |
| `laus-ed-` | Laus edition row IDs | `laus-ed-YYYY` | `laus-ed-2026` |
| `laus-cat-` | Laus category row IDs | `laus-cat-YYYY-slug` | `laus-cat-2026-identidad-corporativa` |
| `laus-jury-` | Laus jury row IDs | `laus-jury-YYYY-NNN` | `laus-jury-2026-001` |
| `laus-award-` | Laus award row IDs (future) | `laus-award-YYYY-NNN` | `laus-award-2026-001` |
| `laus-school-` | Laus school row IDs (future) | `laus-school-slug` | `laus-school-eina` |
| `laus-studio-` | Laus studio/agency row IDs (future) | `laus-studio-slug` | `laus-studio-toormix` |
| `adg-member-` | ADG member directory row IDs (future) | `adg-member-NNNNN` | `adg-member-00123` |

---

## 5. Canonical Module Registry

| Human label | `module_id` | Type | `current_state` | `route_now` | `future_route_or_subhub` | `impl_allowed_in_ext_branch` | Source doc | Notes |
|---|---|---|---|---|---|---|---|---|
| Home / Hub | `mod-home-hub` | `support_page` | `active` | `index.html` | — | hub card copy only | TXT 042 canon | Global entry point; hosts all module cards |
| Observatorio de Licitaciones | `mod-licitaciones` | `active_surface` | `active` | `licitaciones.html` | — | **false** | Roadmap Appendix | Core module; active surface stream; TXT 052 historical/applied |
| Estadísticas Forense | `mod-estadisticas-forense` | `active_surface` | `active` | `estadisticas.html` | — | **false** | Roadmap Appendix / ADGOPS_001 | Active surface stream |
| Recursos + Calculadora | `mod-recursos-calculadora` | `active_surface` | `active` | `recursos.html` | — | **false** | ADGOPS_003 / TXT 050 | Active surface stream; TXT 050 verdict: adequate |
| Mapa del Diseño | `mod-mapa-diseno` | `active_surface` | `active` | `mapa.html` | — | **false** | Roadmap Appendix | Active surface stream |
| Barómetro del Sector | `mod-barometro-sector` | `active_surface` | `active` | `estadisticas.html` (toggle view) | — | **false** | TXT 055 / pre-existing rule | View toggle inside estadisticas.html; no separate route |
| Laus Tracker | `mod-laus-tracker` | `extension_module` | `shell` | `laus.html` | `laus.html` (is the module page/subhub) | audit only | Ficha 001 / v0.1.3.1 | Phase 1; partial data active; 2016–2018 jury imported; expansion paused |
| Directorio de Socios | `mod-directorio-socios` | `extension_module` | `stub` | none (div on index) | `directorio.html` (future, blocked) | audit only | Ficha 002 / v0.1.3.1 | Phase 2; Legacy / partial exists; blocked by data/privacy contract |
| Oportunidades ADG | `mod-oportunidades-adg` | `extension_module` | `stub` | none (div on index) | `oportunidades.html` (future, blocked) | audit only | Ficha 003 / v0.1.3.1 | Parent of child lanes; blocked by process contract |
| Alertas por Email | `mod-alertas-email` | `extension_module` | `stub` | `alertas.html` (stub shell) | `alertas.html` (stub shell in place) | stub maintenance only | Ficha 004 / v0.1.3.1 | Phase 7; no consent/delivery contract; stub is honest |
| Acerca de / Transparency | `mod-about-transparency` | `support_page` | `active` | `about.html` | — | copy corrections only | ADGOPS_004 | Not an extension module; doctrine corrections acceptable |

---

## 6. Hub Card Registry

| `module_id` | `card_id` | `current_card_state` | `current_route_or_none` | `future_behavior` | `allowed_next_action` |
|---|---|---|---|---|---|
| `mod-licitaciones` | `card-licitaciones` | `live` — `<a href="./licitaciones.html">` | `licitaciones.html` | No change in this branch | Inventory only |
| `mod-estadisticas-forense` | `card-estadisticas-forense` | `live` — `<a href="./estadisticas.html">` | `estadisticas.html` | No change in this branch | Inventory only |
| `mod-recursos-calculadora` | `card-recursos-calculadora` | `live` — `<a href="./recursos.html">` | `recursos.html` | No change in this branch | Inventory only |
| `mod-mapa-diseno` | `card-mapa-diseno` | `live` — `<a href="./mapa.html">` | `mapa.html` | No change in this branch | Inventory only |
| `mod-barometro-sector` | `card-barometro-sector` | `live` — `<a href="./estadisticas.html">` | `estadisticas.html` (toggle) | No change in this branch | Inventory only |
| `mod-laus-tracker` | `card-laus-tracker` | `live` — `<a href="./laus.html">` | `laus.html` | Evolves as Laus data expands | Add `id=` + `data-module-*` attributes (TXT 058) |
| `mod-directorio-socios` | `card-directorio-socios` | `stub` — `<div>`, no href | none | Links to `directorio.html` when route is ready | Add `id=` + `data-module-*` attributes (TXT 058) |
| `mod-oportunidades-adg` | `card-oportunidades-adg` | `stub` — `<div>`, no href | none | Links to `oportunidades.html` when route is ready | Add `id=` + `data-module-*` attributes (TXT 058) |
| `mod-alertas-email` | `card-alertas-email` | `stub` — `<div>`, no href | none (stub shell at `alertas.html` via nav only) | Remains stub until consent/delivery contract | Add `id=` + `data-module-*` attributes (TXT 058) |

**Proposed `data-*` pattern for TXT 058 (not yet implemented):**

```html
<!-- Live extension module card -->
<a id="card-laus-tracker"
   class="home-card home-card--live"
   href="./laus.html"
   data-module-id="mod-laus-tracker"
   data-module-state="shell"
   data-module-kind="extension_module">

<!-- Stub extension module card -->
<div id="card-directorio-socios"
     class="home-card home-card--soon"
     data-module-id="mod-directorio-socios"
     data-module-state="stub"
     data-module-kind="extension_module">

<!-- Live active surface card (inventory attributes only) -->
<a id="card-licitaciones"
   class="home-card home-card--live"
   href="./licitaciones.html"
   data-module-id="mod-licitaciones"
   data-module-state="active"
   data-module-kind="active_surface">
```

---

## 7. Route Registry

| `module_id` | `route_id` | `current_route` | `route_status` | Notes |
|---|---|---|---|---|
| `mod-home-hub` | `route-home` | `index.html` | `active` | Global hub |
| `mod-licitaciones` | `route-licitaciones` | `licitaciones.html` | `active` | Active surface; do not touch in this branch |
| `mod-estadisticas-forense` | `route-estadisticas` | `estadisticas.html` | `active` | Active surface |
| `mod-recursos-calculadora` | `route-recursos` | `recursos.html` | `active` | Active surface |
| `mod-mapa-diseno` | `route-mapa` | `mapa.html` | `active` | Active surface |
| `mod-barometro-sector` | `route-barometro` | — | `no_separate_route` | Toggle view inside `estadisticas.html`; no dedicated HTML file |
| `mod-laus-tracker` | `route-laus` | `laus.html` | `active_shell` | Extension module page; partial data |
| `mod-directorio-socios` | `route-directorio` | — | `blocked` | Future `directorio.html`; blocked by data/privacy contract |
| `mod-oportunidades-adg` | `route-oportunidades` | — | `blocked` | Future `oportunidades.html`; blocked by process contract |
| `mod-alertas-email` | `route-alertas` | `alertas.html` | `stub_shell` | Honest coming-soon stub via AlertasStub component |
| `mod-about-transparency` | `route-about` | `about.html` | `active` | Support page |

**Hard rule:** `extensions.html` is a PROHIBITED route. It must never be recreated or referenced.

---

## 8. Subhub Registry

| `subhub_id` | `module_id` | Proposed route | Current state | `implementation_readiness` | Blocked by |
|---|---|---|---|---|---|
| `subhub-laus` | `mod-laus-tracker` | `laus.html` (exists) | Module page/subhub shell, partial data | `audit_only` for current shell; `blocked_by_data_contract` for awards/schools/studios expansion | Awards/schools/studios data contract (future) |
| `subhub-directorio` | `mod-directorio-socios` | `directorio.html` (future) | Not created — stub div on index | `blocked_by_data_privacy_contract` | Privacy model, member data contract, ADG-FAD approval |
| `subhub-oportunidades` | `mod-oportunidades-adg` | `oportunidades.html` (future) | Not created — stub div on index | `blocked_by_process_contract` | Intake/moderation process contract for all child lanes |
| `subhub-alertas` | `mod-alertas-email` | `alertas.html` (stub shell, exists) | Honest stub shell, coming-soon only | `blocked_by_consent_delivery_contract` | Consent model, delivery workflow, trigger contract |

**Subhub rules:**
- Do not create `directorio.html` until data/privacy contract is approved
- Do not create `oportunidades.html` until process contract is approved
- Do not link stub cards to dead/empty subhub routes
- `alertas.html` exists as an honest stub shell only — no form, no provider, no intake
- `laus.html` is the only active extension module page; it will evolve into a deeper subhub as data expands

---

## 9. Dataset Registry

| `dataset_id` | Future SQL table | Current JSON file | Source/provenance | Implementation status | Notes |
|---|---|---|---|---|---|
| `ds-laus-editions` | `laus_editions` | `data/public/laus/editions.json` | `adg-public` | Active — 11 records (2016–2026) | Editions complete for seed |
| `ds-laus-categories` | `laus_categories` | `data/public/laus/categories.json` | `adg-public` | Active — 68 records | Categories complete for all years |
| `ds-laus-juries` | `laus_juries` | `data/public/laus/juries.json` | `adg-public` | Partial — 146 records; 2016–2018 fully imported; 2019–2026 seed only (3 rows/year); expansion paused | Expansion paused; do not continue without operator approval |
| `ds-laus-awards` | `laus_awards` | — | — | Future — Phase 2R-5; blocked by data contract | No fake winners; blocked until real data available |
| `ds-laus-schools` | `laus_schools` | — | — | Future — Phase 2R-7; blocked | — |
| `ds-laus-studios` | `laus_studios` | — | — | Future — Phase 2R-7; blocked | — |
| `ds-adg-members` | `adg_members` | — | — | Future — Phase 2R-8; blocked by privacy/data contract | No fake member profiles |
| `ds-oportunidades-listings` | `oportunidades_listings` | — | — | Future; blocked by process contract | No fake opportunity listings |
| `ds-alertas-subscriptions` | `alertas_subscriptions` | — | — | Future; blocked by consent/delivery contract | No fake subscriptions; never capture email without contract |
| `ds-recursos` | `recursos` | `data/recursos.json` | mixed | Active — active surface; out of implementation scope in this branch | Do not modify in this branch |
| `ds-licitaciones` | `licitaciones` | `data/licitaciones.json` | `adg-public` (PLACSP) | Active — active surface; out of implementation scope | Do not modify in this branch |

---

## 10. SQL-Readiness Contract

All JSON data files must follow these rules to enable future SQL migration without destructive changes:

| Rule | Detail |
|---|---|
| JSON file = table seed | One JSON file per logical table |
| JSON object = row | Each object in the array is one record |
| `id` | Required on every row; stable, immutable, unique within the table; becomes PRIMARY KEY |
| `*_id` fields | Foreign keys — must resolve to existing `id` in the referenced table; named `{entity}_id` |
| Field names | `snake_case` throughout — no camelCase, no kebab in JSON keys |
| `null` | Use for unknown or empty cells — never use empty string `""` for a missing value |
| No positional arrays | Never use array index position as business data — use explicit fields |
| No hardcoded data | All records live in JSON files; no data embedded in HTML or JS |
| Display order | No semantic meaning in row order unless an explicit `sort_order` integer field exists |
| Labels separate from IDs | Display labels (`label`, `category_judged`) always separate from stable IDs (`category_id`) |
| Provenance required | `source` + `source_file` required on all public rows; `import_batch` required for batch-imported data |
| Controlled vocabularies | Status, type, and source fields use fixed controlled values only |
| Migrations additive | New fields are added with `null` defaults on existing rows where possible — no destructive renames |
| Round-trip rule | JSON → CSV → JSON must be lossless and unambiguous |

**Provenance vocabulary for `source` field:**

| Value | Meaning |
|---|---|
| `adg-public` | Sourced from public ADG materials; `source_file` required |
| `mock` | Placeholder or synthetic data — must be replaced before production |
| `pending` | Real data not yet available; row is a placeholder |
| `derived` | Calculated from other tables; `derived_from` field required |

---

## 11. Mock Data Policy

| Rule | Detail |
|---|---|
| Allowed purpose | UI and system behavior testing only — never to simulate real user-facing records |
| Never masquerades | Mock data must not look like real public records to a user |
| Required fields | `source: "mock"`, `is_mock: true`, `mock_reason: "..."` on all mock rows |
| Schema match | Mock rows must map 1:1 to the future real table schema — no mock-only fields |
| Easy to remove | All mock rows identifiable by `source: "mock"` — a single filter removes them all |
| Prefer honest empty states | If a module has no data, show an honest "no data yet" state instead of inventing records |
| Location | `data/mock/` directory only — never inside `data/public/` |
| No hardcoded mock in source | No records embedded in HTML or JS files |
| Forbidden categories | Fake award winners, fake member profiles, fake opportunity listings, fake email subscriptions — **never, under any circumstances** |

---

## 12. Future Implementation Path

| TXT candidate | Suffix | Scope | Prerequisite | Risk |
|---|---|---|---|---|
| **TXT 058** | `_imp` | Apply `id="card-*"`, `data-module-id`, `data-module-state`, `data-module-kind` attributes to hub cards in `index.html` only | This registry approved | LOW — attribute-only; no layout, routing, or behavior change |
| **TXT 059** | `_audit` | Subhub readiness audit — re-audit `laus.html` against module page needs; confirm `directorio.html` and `oportunidades.html` do not exist | TXT 058 complete | LOW — read-only |
| **TXT 060** | `_audit` | Chosen module data contract audit — operator selects which extension module to open next (Directorio, Oportunidades, or Alertas) | Operator decision | LOW — read-only |

**Hard rules for this path:**
- No implementation on active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro)
- No further Laus jury imports unless operator explicitly reopens that scope
- No subhub route creation before contract and readiness confirmation
- No mock data before ID/data contract is approved per module

---

## 13. Retired / Stale Items

These items are explicitly retired from the ADG Extensions implementation queue:

| Item | Reason |
|---|---|
| Stale "33-seed-row Laus gap fix" plan | **RETIRED** — Phase 2R-4B added `category_id` + `import_batch` to seed rows; 2016–2018 fully imported; this gap no longer exists |
| Laus jury import continuation | **PAUSED** — 2016–2018 complete; further imports require operator to explicitly reopen scope |
| `extensions.html` recreation | **HARD RETIRED** — deleted by TXT 042; prohibited by canon; must never be recreated |
| Licitaciones follow-up fixes | **RETIRED FROM BRANCH** — active surface; TXT 052 is historical/applied; do not touch without explicit scope reopening |
| Barómetro fixes | **RETIRED FROM BRANCH** — active surface; INFORMATIONAL ONLY / OUT OF SCOPE |
| Active surface implementation (all) | **RETIRED FROM BRANCH** — Estadísticas, Recursos, Mapa are active surfaces; their implementation belongs to the active surfaces delivery stream, not this branch |
| `#modal-success` orphan cleanup in licitaciones.html | **RETIRED** — licitaciones is out of scope; dead code, never shown |

---

## 14. Open Questions — Confirmation State

All four TXT 056 open questions are now resolved:

| Q | Decision |
|---|---|
| **Q1** — `mod-*` prefix vs plain slugs | **CONFIRMED: `mod-*`** — clean namespace, aligned with domain-prefix pattern |
| **Q2** — Active surfaces in registry | **CONFIRMED: yes, inventory-only** — `impl_allowed_in_extensions_branch: false` for all active surfaces |
| **Q3** — Docs registry first or direct to source | **CONFIRMED: docs registry first** — this document; index.html attributes in TXT 058 |
| **Q4** — Subhub routes: create now or hold | **CONFIRMED: hold** — no `directorio.html` or `oportunidades.html` until contracts approved |

---

## 15. Next Step

**Recommended TXT 058 `_imp`** — Apply ID attributes to `index.html` hub cards only.

Scope: add `id="card-*"`, `data-module-id`, `data-module-state`, `data-module-kind` to all 9 hub cards in `index.html`. No layout, routing, or behavior changes. Active surface cards receive inventory attributes (`data-module-kind="active_surface"`) but are otherwise untouched.

Prerequisite: operator approves this registry (TXT 057).

---

## Stop

- No source file edits
- No data writes
- No git mutations
- This document is canon/registry only
