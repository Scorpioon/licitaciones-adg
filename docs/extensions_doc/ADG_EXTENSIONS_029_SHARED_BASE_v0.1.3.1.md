# ADG_EXTENSIONS_029 — Shared Base / Foundation Document

**Version:** v0.1.3.1
**Status:** ACTIVE FOUNDATION / DOC-ONLY
**Mode:** FOUNDATION_FIRST / SHARED_BASE
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**last_synced_txt:** 125
**source_audit_txt:** 124
**last_synced_commit:** cc5ec6a
**checkpoint_tag:** adg-extensions-prehub-routes-v0.1.3.1
**Git write operations by Claude CLI:** FORBIDDEN
**Source/data status:** NO SOURCE, DATA, ACTIVE SURFACE, SUPPORT, OR PRIVATE FILES TOUCHED

---

## 0. What this document is

This document is the shared foundation for the ADG Extensions completion arc. Every module overlay, QA audit, and governance decision inherits from this document.

It defines one common structure for:
- route/module registry (Layer A)
- data/process doctrine (Layer B)
- governance/admin workflow template (Layer C)
- privacy/legal/consent gate template (Layer D)
- QA/smoke template (Layer E)
- public hygiene checklist (Layer F)
- module overlay template (Layer G)

### Relationship to doc 020

This document **supersedes** `ADG_EXTENSIONS_020_ID_TAXONOMY_REGISTRY_v0.1.3.1.md` **§§5–8 and §15** (Canonical Module Registry, Hub Card Registry, Route Registry, Subhub Registry, and the stale Next Step). Doc 020 carries a pointer amendment note.

This document **preserves and complements** doc 020 **§§1–4 and §§9–13** (naming conventions, reserved prefixes, dataset registry, SQL-readiness contract, mock data policy, retired items, open questions). Those sections remain canonical and are not duplicated here.

### Why this document exists

Sufficient implementation work accumulated since doc 020 was written that the route/card/subhub state in §§5–8 diverged materially from the source. A shared base document is the correct resolution: it establishes a single source-of-truth that all future module overlay documents can reference without re-deriving route state, and it embeds the governance, privacy, QA, and hygiene templates that prevent module-by-module drift.

---

## 1. LAYER A — Route / Module Registry

### Enum Definitions

**`route_state`**

| Value | Meaning |
|---|---|
| `active` | Live route, loads real content, linked from index or navigation |
| `active_prehub` | Live prehub route, serves as parent landing for child surfaces |
| `active_shell` | Route exists, loads stub/shell, partial or no data |
| `stub_shell` | Route exists as honest stub (coming-soon), no data, no form |
| `tombstone` | Route exists but redirects or shows deprecated notice |
| `blocked` | Route does not exist yet; blocked by gate or contract |
| `prohibited` | Route must never be created (extensions.html) |

**`index_state`**

| Value | Meaning |
|---|---|
| `active` | Card in index.html is a live `<a href>` pointing to an existing file |
| `hold` | Card in index.html is a `<div>`, no href, HOLD_PRIVACY or equivalent |
| `deferred_final_lane` | Card in index.html is a `<div>`, no href, final lane only |

**`module_phase`**

| Value | Meaning |
|---|---|
| `active_surface` | Legacy active surface outside extension implementation scope |
| `prehub_live` | Prehub shell live; child surfaces exist |
| `prehub_shell_only` | Shell exists but not linked from index |
| `extension_shell` | Extension module with live prehub route but no data |
| `extension_stub` | Extension module with no route from index (stub only) |
| `extension_partial` | Extension module with live route and partial/limited data |
| `deferred` | Deferred to final lane (Alertas) |

**`gate_state`**

| Value | Meaning |
|---|---|
| `open` | Gate not yet resolved; blocks forward progress |
| `closed` | Gate resolved; prerequisite met |
| `partial` | Gate partially resolved; some sub-items remain open |
| `deferred` | Gate applies to a deferred module |
| `not_applicable` | Gate category does not apply to this module |

**`data_state`**

| Value | Meaning |
|---|---|
| `active_public` | Real public data in JSON; loaded in production; out of ext branch scope |
| `partial_public` | Real public Tier A data for subset of fields/records; some blocked |
| `mock_only` | Only Tier B mock data available; no real source confirmed |
| `no_data` | No data files exist or planned for current implementation phase |
| `blocked_by_gate` | Data creation requires closed gate first |

---

### 1.1 Current Module Registry

| Human label | `module_id` | Type | `module_phase` | `data_state` | Source doc |
|---|---|---|---|---|---|
| Home / Hub | `mod-home-hub` | support_page | active_surface | active_public | doc 000 |
| Observatorio de Licitaciones | `mod-licitaciones` | active_surface | active_surface | active_public | doc 000 |
| Mapa del Diseño | `mod-mapa-diseno` | active_surface | active_surface | active_public | doc 028 |
| Recursos + Calculadora | `mod-recursos-calculadora` | active_surface | prehub_live | active_public | doc 000 |
| Estadísticas Forense | `mod-estadisticas-forense` | active_surface | prehub_live | active_public | doc 000 |
| Barómetro del Sector | `mod-barometro-sector` | active_surface | prehub_live | active_public | doc 028 |
| LAUS Tracker | `mod-laus-tracker` | extension_module | extension_partial | partial_public | doc 001 |
| LAUS Stats | `mod-laus-stats` | extension_module | extension_partial | partial_public | doc 001 |
| Directorio de Socios | `mod-directorio-socios` | extension_module | prehub_shell_only | blocked_by_gate | doc 023 |
| mapa_socios | `mod-mapa-socios` | extension_module | extension_shell | blocked_by_gate | doc 028 |
| Oportunidades ADG | `mod-oportunidades-adg` | extension_module | prehub_live | no_data | doc 022 |
| Bolsa de Prácticas | `mod-practicas` | extension_module | extension_shell | no_data | doc 003A |
| Bolsa de Freelancers | `mod-freelancers` | extension_module | extension_shell | blocked_by_gate | doc 003B |
| Bolsa Profesional | `mod-profesional` | extension_module | extension_shell | blocked_by_gate | doc 003B |
| Alertas por Email | `mod-alertas-email` | extension_module | deferred | blocked_by_gate | doc 021 |
| Acerca de / Transparency | `mod-about-transparency` | support_page | active_surface | active_public | doc 000 |

---

### 1.2 Current Hub Card Registry

| `card_id` | `module_id` | `current_card_state` | `current_href` | `index_state` |
|---|---|---|---|---|
| `card-licitaciones` | `mod-licitaciones` | live `<a>` | `./licitaciones.html` | `active` |
| `card-mapa-diseno` | `mod-mapa-diseno` | live `<a>` | `./mapa.html` | `active` |
| `card-oportunidades-adg` | `mod-oportunidades-adg` | live `<a>` | `./oportunidades.html` | `active` |
| `card-laus-tracker` | `mod-laus-tracker` | live `<a>` | `./laus-prehub.html` | `active` |
| `card-recursos-calculadora` | `mod-recursos-calculadora` | live `<a>` | `./recursos-prehub.html` | `active` |
| `card-estadisticas-forense` | `mod-estadisticas-forense` | live `<a>` | `./estadisticas-prehub.html` | `active` |
| `card-barometro-sector` | `mod-barometro-sector` | live `<a>` | `./estadisticas-prehub.html` | `active` |
| `card-directorio-socios` | `mod-directorio-socios` | stub `<div>`, no href | none | `hold` |
| `card-alertas-email` | `mod-alertas-email` | stub `<div>`, no href | none | `deferred_final_lane` |

---

### 1.3 Current Route Registry

All 20 tracked HTML files (from git ls-files at cc5ec6a):

| HTML file | `module_id` | `route_id` | `route_state` | Notes |
|---|---|---|---|---|
| `index.html` | `mod-home-hub` | `route-home` | `active` | Global hub; all module cards |
| `licitaciones.html` | `mod-licitaciones` | `route-licitaciones` | `active` | Active surface; do not touch in branch |
| `mapa.html` | `mod-mapa-diseno` | `route-mapa` | `active` | Active surface (`mapa_licitaciones` concept); do not rename |
| `recursos.html` | `mod-recursos-calculadora` | `route-recursos` | `active` | Active surface child under recursos-prehub |
| `recursos-prehub.html` | `mod-recursos-calculadora` | `route-recursos-prehub` | `active_prehub` | Hub card points here; parent of recursos.html |
| `estadisticas.html` | `mod-estadisticas-forense` | `route-estadisticas` | `active` | Active surface child under estadisticas-prehub |
| `estadisticas-prehub.html` | `mod-estadisticas-forense` | `route-estadisticas-prehub` | `active_prehub` | Both Estadísticas and Barómetro index cards point here |
| `barometro.html` | `mod-barometro-sector` | `route-barometro` | `tombstone` | Tombstone/redirect → estadisticas.html; must not render as active module |
| `laus-prehub.html` | `mod-laus-tracker` | `route-laus-prehub` | `active_prehub` | Hub card points here; parent of laus.html and laus-stats.html |
| `laus.html` | `mod-laus-tracker` | `route-laus` | `active_shell` | LAUS Tracker child; partial jury/edition data |
| `laus-stats.html` | `mod-laus-stats` | `route-laus-stats` | `active_shell` | LAUS Stats child; partial data |
| `oportunidades.html` | `mod-oportunidades-adg` | `route-oportunidades` | `active_prehub` | Hub card points here; parent of 3 child shells; no live data |
| `oportunidades-practicas.html` | `mod-practicas` | `route-practicas` | `active_shell` | Child shell under Oportunidades prehub; no data |
| `oportunidades-freelancers.html` | `mod-freelancers` | `route-freelancers` | `active_shell` | Child shell; blocked by Freelancers deep ficha |
| `oportunidades-profesional.html` | `mod-profesional` | `route-profesional` | `active_shell` | Child shell; blocked by Profesional deep ficha |
| `directorio.html` | `mod-directorio-socios` | `route-directorio` | `active_shell` | Shell prehub parent; NOT linked from index; HOLD_PRIVACY |
| `directorio-socios.html` | `mod-directorio-socios` | `route-directorio-socios` | `blocked` | Child shell under directorio prehub; HOLD_PRIVACY |
| `mapa-socios.html` | `mod-mapa-socios` | `route-mapa-socios` | `blocked` | mapa_socios shell; HOLD_PRIVACY (Directorio gates) |
| `alertas.html` | `mod-alertas-email` | `route-alertas` | `stub_shell` | Honest coming-soon stub; AlertasStub component; no form; DEFERRED_FINAL_LANE |
| `about.html` | `mod-about-transparency` | `route-about` | `active` | Support page; copy corrections acceptable |

**Hard rule:** `extensions.html` is a PROHIBITED route. It was deleted by TXT 042. It must never be recreated, referenced, linked, or audited as a product surface.

---

### 1.4 Prehub Parent → Child Mapping

| Prehub parent | `prehub_id` | Child surfaces | Index cards that route here | Notes |
|---|---|---|---|---|
| `estadisticas-prehub.html` | `prehub-estadisticas` | `estadisticas.html`, `barometro.html` (tombstone) | card-estadisticas-forense, card-barometro-sector | Both index cards point to same prehub |
| `recursos-prehub.html` | `prehub-recursos` | `recursos.html`; future lanes (Guía licitaciones, Plantillas legales, Referencias personales) | card-recursos-calculadora | Future child lanes defined in prehub architecture; not yet wired |
| `laus-prehub.html` | `prehub-laus` | `laus.html`, `laus-stats.html` | card-laus-tracker | Hub card points to prehub, not directly to laus.html |
| `oportunidades.html` | `prehub-oportunidades` | `oportunidades-practicas.html`, `oportunidades-freelancers.html`, `oportunidades-profesional.html` | card-oportunidades-adg | All 3 children are shells; no live data |
| `directorio.html` | `prehub-directorio` | `directorio-socios.html`, `mapa-socios.html` | none (not linked from index) | Shell prehub only; all children blocked by 11 privacy gates (doc 023) |

---

### 1.5 HOLD / Prohibited / Tombstone Register

| HTML file | `module_id` | Status | Reason | Unblock condition |
|---|---|---|---|---|
| `directorio-socios.html` | `mod-directorio-socios` | HOLD_PRIVACY | 11 Directorio privacy gates open (doc 023 §16) | All 11 gates closed |
| `directorio.html` | `mod-directorio-socios` | HOLD_PRIVACY (unlinked shell) | Not linked from index; gates not cleared | Card link activation requires separate operator authorization |
| `mapa-socios.html` | `mod-mapa-socios` | HOLD_PRIVACY | Requires all Directorio gates OR explicit shell-only operator authorization | Directorio gates closed OR operator explicit shell authorization |
| `alertas.html` | `mod-alertas-email` | DEFERRED_FINAL_LANE | Final lane; all pre-activation consent/delivery gates open (doc 021 §14) | All Alertas gates closed; operator opens final lane sequence |
| `barometro.html` | `mod-barometro-sector` | TOMBSTONE | Redirect/deprecated notice → estadisticas.html | Do not activate as standalone module |
| `extensions.html` | — | PERMANENTLY PROHIBITED | Deleted by TXT 042; must never be recreated | Never |

---

### 1.6 Registry Sync Metadata

| Field | Value |
|---|---|
| `last_synced_txt` | 125 |
| `source_audit_txt` | 124 |
| `last_synced_commit` | cc5ec6a |
| `checkpoint_tag` | adg-extensions-prehub-routes-v0.1.3.1 |
| `doc_020_superseded_sections` | §§5–8 and §15 |
| `doc_020_canonical_sections` | §§1–4 and §§9–13 |

---

## 2. LAYER B — Data / Process Doctrine

### 2.1 Data Classification Tiers

| Tier | Label | `source` value | Definition | UI / doc policy |
|---|---|---|---|---|
| A | public-source | `adg-public` | Real data from confirmed public ADG sources; `source_file` required | No Demo badge required; provenance must be documented |
| B | mock | `mock` | Fabricated/placeholder data where no real source is available | Demo badge mandatory on any UI rendering Tier B records; `data/mock/` directory only |
| C | reserved | `pending` or `null` | Schema field confirmed; no authoritative source yet | `null` value in data; never displayed as real content |
| — | derived | `derived` | Calculated from other tables at query/render time | `derived_from` field required; never stored in primary tables |

### 2.2 Data Lifecycle States

| State | Applies to | Meaning |
|---|---|---|
| `draft` | Admin-created records | Internal preparation; not from external submission |
| `submitted` | External intake records | Received by ADG; default on external receipt |
| `under_review` | All modules with intake | Admin reviewing; not yet decided |
| `approved` | All modules with intake | ADG approved; ready to publish |
| `published` | All modules with intake | Live and publicly visible |
| `expired` | Oportunidades listings | Past deadline date (auto) or manually expired |
| `archived` | All modules | Retained for record; hidden from public |
| `rejected` | Intake records | ADG rejected submission; terminal |
| `removed` | Member profiles, consent records | Removed/anonymized by data subject request |
| `withdrawn` | Listings, submissions | Submitter-requested removal before or after publication |

### 2.3 Source-of-Truth Principles

1. All data lives in JSON files. No records embedded in HTML or JS.
2. JSON file = table; JSON object = row; `id` = immutable, stable, unique primary key.
3. `snake_case` keys throughout; `null` for unknown or empty — never empty string for a missing value.
4. Round-trip rule: JSON → CSV → JSON must be lossless and unambiguous.
5. Provenance required on all public rows: `source` + `source_file` when `source = "adg-public"`.
6. `import_batch` required on all batch-imported records.
7. No positional arrays; row order has no semantic meaning unless an explicit `sort_order` integer field exists.

### 2.4 No-Private-Read Policy

| Rule | Detail |
|---|---|
| `docs/support_copys/**` | Always gitignored; never read by Claude CLI without an explicit operator data contract opening that file |
| `data/**` contents | Do not open without an explicit per-dataset data contract |
| Member data | Never imported or read without ADG-FAD authorization |
| Support/private/member files | Forbidden in all audit and implementation prompts unless a named contract exists |

### 2.5 No-Fake-Data Policy

| Absolute prohibition | Module | Notes |
|---|---|---|
| Fake award winners | LAUS | Never, under any circumstances — show honest empty/Próximamente state |
| Fake member profiles | Directorio | Real names or inferred personal data are never fabricated |
| Fake opportunity listings | Oportunidades | No fake companies, salaries, or offers |
| Fake email subscriptions | Alertas | No fake subscriber records; never real email addresses |
| Mock rows in `data/public/` | All modules | Mock stays in `data/mock/` only, never in production paths |
| Realistic-looking mock data | All modules | Mock names must be obviously fake (e.g., "Estudio de Prueba SA") |

### 2.6 Per-Module Data Readiness

| Module | `data_state` | What is available | What is blocked |
|---|---|---|---|
| Licitaciones | `active_public` | Full licitaciones.json (PLACSP source) | Out of scope in branch; do not touch |
| Mapa del Diseño | `active_public` | Active surface data | Out of scope in branch |
| Recursos | `active_public` | recursos.json active | Out of scope in branch |
| Estadísticas | `active_public` | Active surface data | Out of scope in branch |
| Barómetro | `active_public` | Active surface data (toggle inside estadisticas) | Out of scope in branch; barometro.html is tombstone |
| LAUS Tracker | `partial_public` | Tier A: editions + juries (2016–2018 full; 2019–2026 seed only) | Awards, schools, studios blocked by data contract; expansion paused (doc 008) |
| Directorio | `blocked_by_gate` | listado_socios_onlynames.txt is Tier A candidate (names only) — but FORBIDDEN to read without gate clearance | All fields; all data creation blocked by 11 privacy gates (doc 023) |
| Oportunidades | `no_data` | Prácticas field schema locked (doc 022 §11A) | No mock/real listings; Freelancers/Profesional require deep fichas before data |
| Alertas | `blocked_by_gate` | Schema defined (doc 021) | All data creation blocked; consent/delivery/legal gates open |

---

## 3. LAYER C — Governance / Admin Workflow Template

### 3.1 Manual-First Workflow (v1, all modules)

```
EXTERNAL CONTACT (email to ADG / manual intake)
  ↓
RECEIVED  →  status: submitted
  ↓ admin acknowledges
UNDER REVIEW  →  status: under_review
  ↓ admin reviews against module criteria
  ┌─────────────────┬────────────────────┐
  ↓                 ↓                    ↓
APPROVED        REJECTED          RETURN FOR EDIT
(→ published)  (terminal)        (→ back to submitted)
  ↓
PUBLISHED
  ↓ auto-expire (when deadline_date passes) OR admin action
EXPIRED  →  admin decides  →  ARCHIVED
```

All steps are manual in v1. Automated publishing is forbidden. Submission never equals publication.

### 3.2 Review State Vocabulary

| State | Meaning |
|---|---|
| `not_reviewed` | Default on creation |
| `under_review` | Admin actively reviewing |
| `approved` | Admin approved for publication |
| `changes_requested` | Returned to submitter/admin for correction; re-enters review cycle |
| `rejected` | Admin rejected; terminal for this submission |

### 3.3 Admin Action Vocabulary

| Action | Applies from state | Effect |
|---|---|---|
| `approve` | under_review | Moves to approved |
| `publish` | approved | Moves to published; makes visible to public |
| `reject` | under_review | Terminal rejection; logs reason in admin_notes |
| `return_for_edit` | under_review | Returns to submitted; admin logs reason |
| `expire` | published | Marks as expired (manual when no deadline exists) |
| `archive` | expired or published | Moves to archive; hidden from public |
| `suppress` | published | Emergency suppression; record preserved; not shown publicly |
| `restore` | archived or suppressed | Returns to last public-safe state; requires admin review |
| `remove_by_request` | any state | LOPD/GDPR erasure or removal per data subject request; anonymizes personal data |

### 3.4 Ownership Model

| Property | v1 value |
|---|---|
| Admin owner | ADG/manual operator or designated technical admin |
| Account model | Single v1 owner model; no per-module or per-lane splits |
| Automated publishing | FORBIDDEN — admin must explicitly publish after approval |
| Submitter access post-submission | None; no submitter platform account in MVP |
| Abuse handling | Admin-mediated; public self-submit is deferred for all modules |

### 3.5 Audit Trail Fields (inherited by all module event tables)

| Field | Required | Notes |
|---|---|---|
| `id` | YES | Stable immutable PK per event row |
| `created_at` | YES | ISO 8601 |
| `updated_at` | YES | ISO 8601 (on master record) |
| `changed_by` | YES | Admin actor identifier |
| `{module}_status_events` | YES | Immutable transition log table; one per module |
| `{module}_admin_notes` | YES | Internal review/correction/removal notes; one per module |

### 3.6 Module Inheritance

| Module | Governance template | Notes |
|---|---|---|
| Oportunidades — Prácticas | Full inheritance | Concrete field set; workflow in doc 022 |
| Oportunidades — Freelancers | Partial | Deep ficha required before full field set is locked |
| Oportunidades — Profesional | Partial | Deep ficha required before full field set is locked |
| Directorio de Socios | Full inheritance + privacy gate layer | Doc 023 adds 11 privacy gates on top of base template |
| LAUS (expansion) | Full inheritance | Data-focused; no intake workflow until awards/expansion is authorized |
| Alertas | Full inheritance + consent/delivery layer | Final lane; doc 021 defines consent/delivery additions |
| Recursos future sub-modules | Full inheritance | Applies when Guía / Plantillas / Referencias lanes open |

### 3.7 Correction / Removal Pathway

1. Member or user contacts ADG via the designated channel (email or contact form).
2. Admin receives request; logs in `{module}_admin_notes` with `note_type: correction` or `removal`.
3. Admin reviews:
   - Minor correction (typo, formatting): applied without re-review; logged.
   - Substantial change (title, scope, terms, personal data): admin withdraws → applies edit → re-enters review cycle.
4. Status transition logged in `{module}_status_events`.
5. For LOPD/GDPR erasure requests: personal data anonymized on master record; status_events and consent_events retained (without personal data) for compliance audit trail; delivery_logs retained without personal data.

---

## 4. LAYER D — Privacy / Legal / Consent Gate Template

### 4.1 Gate Template Fields

| Field | Type | Notes |
|---|---|---|
| `gate_id` | string | Format: `gate-{module_slug}-{category}-{seq}` — e.g., `gate-directorio-legal_review-001` |
| `gate_category` | enum | See §4.2 |
| `gate_state` | enum | See §4.3 |
| `gate_authority` | enum | See §4.4 |
| `blocked_actions` | list | Actions that cannot proceed while this gate is open |
| `notes` | string | Current status and what is needed to close |
| `closed_by_txt` | string\|null | TXT that closed this gate; null if still open |

### 4.2 Gate Categories

| Category | Meaning |
|---|---|
| `legal_review` | Legal/privacy analysis required before activation |
| `consent_model` | Consent mechanism (opt-in, double opt-in) must be designed and operational |
| `provider_decision` | Technology or service provider must be decided and confirmed |
| `schema_approval` | Data table schema must be explicitly approved by operator |
| `visibility_policy` | Default visibility and publication rules must be locked |
| `correction_channel` | Correction/removal/erasure channel must exist and be operational |
| `opt_in_design` | Opt-in UX flow must be designed and approved |
| `data_source_approval` | Data source authorization (e.g., ADG-FAD) must be confirmed |
| `geography_policy` | Territory or location exposure policy must be defined |
| `contact_exposure` | Contact information display policy must be locked |

### 4.3 Gate States

| State | Meaning |
|---|---|
| `open` | Gate not resolved; blocks forward progress |
| `closed` | Gate resolved; prerequisite met |
| `partial` | Partially resolved; some sub-items remain open |
| `deferred` | Gate deferred with the module it belongs to |
| `not_applicable` | Gate category does not apply to this module |

### 4.4 Gate Authority

| Authority | Meaning |
|---|---|
| `operator` | ADG/technical admin can close this gate independently |
| `legal` | Qualified legal/privacy reviewer must sign off |
| `adg_board` | ADG-FAD board or data controller must authorize |
| `technical_audit` | Technical implementation must be verified complete |
| `provider_decision` | Gate closes when provider is selected and confirmed by operator |

### 4.5 Blocked Actions per Open Gate

| Gate category | Actions blocked while gate is open |
|---|---|
| `legal_review` | Any public data publication; route activation with real data |
| `consent_model` | Any data capture; any email collection; any subscription form |
| `provider_decision` | Any automated send; any provider API integration |
| `schema_approval` | Data file creation; table seed implementation |
| `visibility_policy` | Any profile or listing publication |
| `correction_channel` | Any public data publication (channel must exist first) |
| `opt_in_design` | Form creation; any UI that implies active subscription |
| `data_source_approval` | Any import or seed from the affected data source |
| `geography_policy` | Location filter activation |
| `contact_exposure` | Any public_email or public_link field exposure |

### 4.6 Directorio Gate Application

All 11 gates from doc 023 §16 — all currently open:

| Gate | `gate_category` | `gate_state` | `gate_authority` | Blocked action |
|---|---|---|---|---|
| ADG-FAD data source authorization | `data_source_approval` | `open` | `adg_board` | All member data import |
| Legal basis for publication | `legal_review` | `open` | `legal` | Any profile publication |
| Privacy notice updated for Directorio | `legal_review` | `open` | `operator` + `legal` | Any new data use |
| Correction/removal request channel operational | `correction_channel` | `open` | `operator` | Any profile publication |
| Erasure/anonymization flow designed and operational | `correction_channel` | `open` | `technical_audit` | Any profile publication |
| Schema approved by operator | `schema_approval` | `open` | `operator` | Data file creation |
| Admin ownership confirmed | `visibility_policy` | `open` | `operator` | Intake and moderation |
| Specialty vocabulary approved | `schema_approval` | `open` | `operator` | Specialty filter activation |
| Source/provenance/import policy approved | `data_source_approval` | `open` | `operator` | Import batches |
| Operator explicitly reopens source scope | `visibility_policy` | `open` | `operator` | directorio.html creation |
| Card link activation separately approved | `visibility_policy` | `open` | `operator` | card-directorio-socios href |

### 4.7 mapa_socios Gate Application

`mapa-socios.html` (`mod-mapa-socios`) inherits the full Directorio gate template (all 11 gates above).

Additionally:
- Gate: `operator_shell_authorization` (`gate_category: visibility_policy`, `gate_authority: operator`) — operator may explicitly authorize a shell-only creation of `mapa-socios.html` with zero member data, bypassing the full Directorio gate sequence.
- If shell-only authorization is granted: `mapa-socios.html` may be created as a zero-data shell. No member names, no profiles, no real locations.
- If not granted: blocked in full until all 11 Directorio gates are cleared.

### 4.8 Alertas Final Lane Gate Application

All gates from doc 021 §14 — all currently open:

| Gate | `gate_category` | `gate_state` | `gate_authority` | Blocked action |
|---|---|---|---|---|
| Consent text drafted and reviewed | `consent_model` | `open` | `operator` | Any subscription form |
| Privacy notice drafted and reviewed | `legal_review` | `open` | `operator` | Any data use |
| **Legal/privacy review completed (D6 — REQUIRED GATE)** | `legal_review` | `open` | `legal` | **ANY Alertas activation** |
| Double opt-in flow designed | `consent_model` | `open` | `technical_audit` | Form creation |
| Unsubscribe mechanism designed | `consent_model` | `open` | `technical_audit` | Form creation |
| Provider or manual-send mechanism decided | `provider_decision` | `open` | `operator` | Automated sends |
| API key / credential boundary defined | `provider_decision` | `open` | `operator` | Provider integration |
| Admin ownership / access rights formally approved | `visibility_policy` | `open` | `operator` | Send approval |
| Table schema seeds implemented | `schema_approval` | `open` | `technical_audit` | Data file creation |
| Licitaciones cross-boundary trigger contract approved | `data_source_approval` | `open` | `operator` | Trigger matching logic |

**Hard rule:** Alertas is `DEFERRED_FINAL_LANE`. No gate in the above table may be opened, and no Alertas implementation work of any kind may proceed, without explicit operator instruction to begin the final lane sequence. The AlertasStub component is the correct and honest current user-facing state.

**AlertasStub UI note (from doc 021 §2):** The AlertasStub prototype renders four disabled fields (discipline, territory, keywords, health signals). Keywords and health signal fields are prototype artifacts. Contracted MVP scope (D4) is discipline + territory + frequency only. These are NOT implementation targets.

---

## 5. LAYER E — QA / Smoke Template

### 5.1 Route Smoke (per HTML file)

| Check | Pass condition |
|---|---|
| File exists and is tracked | Present in git ls-files |
| File loads without error | No 404 / server error |
| No uncaught console JS errors on load | Zero JS errors |
| `<title>` present and not empty | Meaningful title |
| Back navigation link to index or prehub parent | `<a href>` present and resolves |

### 5.2 Index Smoke (index.html)

| Check | Pass condition |
|---|---|
| All 7 active cards have `<a href>` | Confirmed |
| Both HOLD cards are `<div>` with no href | Confirmed |
| All 7 active hrefs point to existing tracked files | All targets in git ls-files |
| HOLD cards have no href attribute anywhere | No href on card-directorio-socios or card-alertas-email |
| No reference to extensions.html | Absent throughout index.html |
| No console errors on index load | Zero errors |

### 5.3 Prehub Smoke (per prehub HTML)

| Check | Pass condition |
|---|---|
| Prehub loads | No error |
| All child card links are present and correct | hrefs match expected child HTML filenames |
| All child pages exist | All child files in git ls-files |
| Back navigation to index | Link present and resolves |
| No console errors | Zero errors |
| No horizontal overflow | Visual check passes |

Prehub files: `estadisticas-prehub.html`, `recursos-prehub.html`, `laus-prehub.html`, `oportunidades.html`

### 5.4 Child Surface Smoke

| Check | Pass condition |
|---|---|
| File loads | No error |
| Expected content renders (or honest empty state shown) | No broken placeholder UI |
| Back navigation to prehub parent | Link present and resolves |
| No console errors | Zero errors |
| No broken icons or missing assets | All assets resolve |

### 5.5 Active Surface QA (out of implementation scope; smoke-level only)

| Check | Pass condition |
|---|---|
| licitaciones.html loads with data | Licitaciones cards render |
| estadisticas.html loads with data | Data renders correctly |
| recursos.html loads | Content renders |
| mapa.html loads | Map renders |
| barometro.html | Tombstone behavior: redirects or shows deprecated notice; does NOT render as an active standalone module |

### 5.6 Negative / HOLD Route Checks

| Check | Pass condition |
|---|---|
| extensions.html absent | NOT in git ls-files; NOT loadable |
| card-directorio-socios: no href | Element is `<div>` with no `href=` attribute |
| card-alertas-email: no href | Element is `<div>` with no `href=` attribute |
| directorio.html NOT reachable via normal index navigation | Not linked from index.html or active nav |
| mapa-socios.html NOT navigable from directorio.html | Not linked until Directorio gates cleared |
| No form active on alertas.html | AlertasStub all inputs disabled; no XHR, no fetch, no form action |

### 5.7 No Exposure Checks

| Check | Pass condition |
|---|---|
| No docs/support_copys/ paths in any HTML or JS | Zero references |
| No API keys or credentials in tracked files | Zero |
| No data embedded in HTML or JS | All data loads via JSON/fetch |
| data/mock/ not referenced in production paths | Only in local dev contexts if used |

### 5.8 Module-Specific Smoke Overlays

Each module overlay document (Layer G) must include a "Module QA Delta" section listing checks specific to that module beyond this base template. The base template is the default floor; module deltas add only what is genuinely different.

---

## 6. LAYER F — Public Hygiene Checklist

### 6.1 PANOPTES / GRC / CLEANREPO Checklist

**Pre-commit checks:**

| Check | Rule |
|---|---|
| `docs/support_copys/**` | Must be gitignored; verify with `git check-ignore -v` before any staging |
| `docs/adg_extensions_prompt_*.txt` | Must be gitignored |
| `docs/extensions_doc/*.zip` and other local artifacts | Must not be staged or committed |
| `data/mock/**` | Must not be committed to public repo without explicit operator decision |
| `.env`, credentials, API keys | Zero tolerance; never commit |
| Local absolute paths in source | No Windows/local filesystem paths in HTML, JS, CSS, or data files |
| `extensions.html` | Must be absent from any diff |

### 6.2 Public / Private File Boundary

| File / path | Classification | Rule |
|---|---|---|
| `*.html` (tracked) | Public | In git; exposed via GitHub Pages; no private data may appear |
| `style.css`, `app.js`, `shared.js`, `*.js` | Public | In git; no credentials or private data |
| `data/public/**` (licitaciones.json, recursos.json, laus/**) | Public | Tier A real data; no private fields permitted |
| `data/mock/**` | Local / dev only | Not for public production; not committed without explicit operator decision |
| `docs/support_copys/**` | ALWAYS PRIVATE | Gitignored; never read or exposed |
| `docs/adg_extensions_prompt_*.txt` | Private | Gitignored |
| `docs/extensions_doc/**` | Public (tracked) | Contains no private data; policy docs and contracts only |
| Any `adg_members` data files | Forbidden until all gates cleared | Must never exist in `data/public/` |
| Any `alertas_subscriptions` or similar data | Forbidden until all gates cleared | Must never exist in `data/public/` |

### 6.3 Local Artifact Policy

| Artifact | Policy |
|---|---|
| `docs/extensions_doc/*.zip` | Do not commit; local reference artifact only |
| Untracked `docs/extensions_doc/` audit files (TXT 120 artifacts) | Do not commit; do not clean without explicit operator classification |
| Editor temp files, OS artifacts | Do not commit |
| `data/mock/` directory and contents | Do not commit until operator explicitly authorizes |

**Hard rule:** Do not remove any file that may be needed at runtime or is part of the current tracked working set without classifying it first. Cleaning an untracked artifact is not the same as removing a tracked runtime file.

### 6.4 GitHub Pages Exposure Readiness

| Check | Rule |
|---|---|
| No private data in any tracked HTML, JS, CSS, or JSON files | Verified |
| No credentials or API keys in any tracked files | Verified |
| extensions.html permanently absent | Verified |
| directorio.html not linked from index | Not reachable via index navigation |
| No adg_members data files | Do not exist |
| No alertas subscription data files | Do not exist |
| barometro.html shows tombstone behavior | Does not present as an active module |

### 6.5 Pre-Push Checklist

1. `git status --short --untracked-files=all` — confirm no unexpected tracked changes
2. `git diff --stat` — confirm diff scope exactly matches the intended change
3. `git check-ignore -v docs/support_copys/listado_socios_onlynames.txt` — must be ignored
4. Confirm `extensions.html` absent from diff output
5. Confirm no API keys, credentials, or private data anywhere in diff
6. Confirm no `data/mock/**` files in diff unless explicitly authorized by operator
7. Operator performs all `git add` and `git commit` manually; Claude CLI never runs git add/commit/push/tag

### 6.6 Pre-Release / Pre-Tag Checklist

All pre-push checks, plus:

1. Smoke test all 7 active index routes (manual browser check)
2. Confirm both HOLD cards (directorio, alertas) still have no href
3. Confirm barometro.html tombstone behavior is correct
4. Confirm extensions.html is absent
5. Confirm no broken console errors on any tracked HTML file
6. Tag with operator approval only; Claude CLI never runs git tag

---

## 7. LAYER G — Module Overlay Template

### 7.1 Reusable Module Overlay / Ficha Template

```markdown
## MODULE OVERLAY — {module_id}

### Identity
- module_id:       {mod-xxx}
- module_family:   {active_surface | extension_module | support_page}
- human_label:     {display name}
- source_doc:      {ADG_EXTENSIONS_00N}

### Route State
- route_state:     {active | active_prehub | active_shell | stub_shell | blocked | tombstone | prohibited}
- html_file:       {filename.html}
- prehub_parent:   {filename.html | none}
- child_surfaces:  [{filename.html, ...} | none]

### Index State
- index_state:     {active | hold | deferred_final_lane}
- card_id:         {card-xxx}
- current_card_href: {./filename.html | none}

### Data / Process Needs
- data_state:      {active_public | partial_public | mock_only | no_data | blocked_by_gate}
- available:       {what Tier A data exists}
- blocked:         {what data creation is blocked and why}
- data_contract_doc: {ADG_EXTENSIONS_00N | none}

### Privacy / Legal / Consent Needs
- gate_summary:    {all_closed | N gates open | not_applicable}
- open_gates:      [{gate_id, gate_category, gate_authority}]
- gate_contract_doc: {ADG_EXTENSIONS_00N | none}

### Governance / Admin Needs
- governance:      {not_applicable | template_inherited | partial | blocked}
- admin_owner:     {ADG operator | TBD | not_applicable}
- notes:           {any deviation from base template}

### QA Needs
- base_template:   LAYER E inherited
- module_qa_delta: [{specific checks beyond base template}]

### Blockers to 100%
- [{description, blocking gate or doc, severity: LOW|MEDIUM|HIGH|CRITICAL}]

### Risk Level
- {LOW | MEDIUM | HIGH | CRITICAL}
- reason: {brief explanation}

### Can Advance Now / Later / End
- {now | later | end} — {reason}

### Next TXT Lane
- {TXTnnn_{audit|imp}} — {brief scope}

### Inherited Base Layers
- {list: A, B, C, D, E, F, G as applicable}

### Module-Specific Deltas
- {only what genuinely differs from the shared base}
```

---

### 7.2 Example Overlay — Recursos + Calculadora

**Identity**
- module_id: `mod-recursos-calculadora`
- module_family: active_surface
- human_label: Recursos + Calculadora
- source_doc: ADG_EXTENSIONS_000

**Route State**
- route_state: `active` (recursos.html); prehub: `active_prehub` (recursos-prehub.html)
- html_file: recursos-prehub.html (entry from index), recursos.html (child surface)
- prehub_parent: none (recursos-prehub.html is itself the prehub)
- child_surfaces: recursos.html; future: Guía licitaciones, Plantillas legales, Referencias personales

**Index State**
- index_state: `active`
- card_id: card-recursos-calculadora
- current_card_href: `./recursos-prehub.html`

**Data / Process Needs**
- data_state: `active_public` — recursos.json active; out of scope in this branch
- available: recursos.json production data
- blocked: source edit is out of scope; do not touch in this branch
- data_contract_doc: none needed until active-surface reopen

**Privacy / Legal / Consent Needs**
- gate_summary: not_applicable — no personal data; public content only
- open_gates: none

**Governance / Admin Needs**
- governance: not_applicable for current state
- admin_owner: not_applicable

**QA Needs**
- base_template: LAYER E inherited
- module_qa_delta:
  - Confirm recursos-prehub.html child card links to recursos.html correctly
  - Confirm future sub-lane placeholders (Guía, Plantillas, Referencias) display as honest stubs if present
  - Confirm no unauthorized link to Guía migration from licitaciones.html (doc 028 §6 — blocked until active-surface reopen)

**Blockers to 100%**
- Active-surface reopen required for any content or feature work (LOW — branch constraint only)
- Guía licitaciones migration from licitaciones.html blocked until active-surface reopen (LOW)

**Risk Level**: LOW

**Can Advance Now / Later / End**: later — active surface reopen required

**Next TXT Lane**: TXT 130 — active surface QA batch

**Inherited Base Layers**: A, E, F

**Module-Specific Deltas**: Two named routes (prehub + child); future resource sub-lanes defined in prehub architecture but not yet wired; Guía migration accepted as product direction but blocked.

---

### 7.3 Example Overlay — Estadísticas Forense + Barómetro del Sector

**Identity**
- module_id: `mod-estadisticas-forense` / `mod-barometro-sector`
- module_family: active_surface
- source_doc: ADG_EXTENSIONS_000 / doc 028

**Route State**
- Estadísticas: `active` (estadisticas.html); prehub: `active_prehub` (estadisticas-prehub.html)
- Barómetro: `tombstone` (barometro.html → estadisticas.html)
- Both index cards point to estadisticas-prehub.html

**Index State**
- index_state: both `active`
- card_id: card-estadisticas-forense, card-barometro-sector
- both current_card_href: `./estadisticas-prehub.html`

**Data / Process Needs**
- data_state: `active_public` — out of scope in this branch

**Privacy / Legal / Consent Needs**
- gate_summary: not_applicable

**Governance / Admin Needs**
- governance: not_applicable for current state

**QA Needs**
- base_template: LAYER E inherited
- module_qa_delta:
  - Confirm both index cards route to estadisticas-prehub.html (not estadisticas.html directly)
  - Confirm estadisticas-prehub.html child cards route to estadisticas.html and barometro.html correctly
  - Confirm barometro.html shows tombstone behavior (redirect or deprecated notice); must NOT render as a standalone active module
  - Confirm barometro.html does not render with live data or interactive features

**Blockers to 100%**: Active-surface reopen required for feature work (LOW)

**Risk Level**: LOW

**Can Advance Now / Later / End**: later — active surface reopen required

**Next TXT Lane**: TXT 130 — active surface QA batch

**Inherited Base Layers**: A, E, F

**Module-Specific Deltas**: Two separate module_ids share one prehub parent; barometro is tombstone (not a dead route — it exists and must behave correctly as a tombstone).

---

### 7.4 Example Overlay — Directorio de Socios

**Identity**
- module_id: `mod-directorio-socios`
- module_family: extension_module
- human_label: Directorio de Socios
- source_doc: ADG_EXTENSIONS_023

**Route State**
- route_state: `blocked` (directorio.html exists as unlinked shell prehub parent; directorio-socios.html and mapa-socios.html blocked)
- html_file: directorio.html (shell, not linked); directorio-socios.html (blocked child); mapa-socios.html (blocked child — see also mod-mapa-socios)
- prehub_parent: none (directorio.html is the unlinked prehub)
- child_surfaces: directorio-socios.html (blocked), mapa-socios.html (blocked)

**Index State**
- index_state: `hold`
- card_id: card-directorio-socios
- current_card_href: none (div, no href)

**Data / Process Needs**
- data_state: `blocked_by_gate`
- available: listado_socios_onlynames.txt is a Tier A candidate (names only) — FORBIDDEN to read without gate clearance (DD2 locked)
- blocked: ALL data creation; member names must not be enumerated; no adg_members seed data; raw member list forbidden
- data_contract_doc: ADG_EXTENSIONS_023

**Privacy / Legal / Consent Needs**
- gate_summary: 11 gates open — see doc 023 §16 and Layer D §4.6 of this document
- open_gates: ADG-FAD authorization, legal basis, privacy notice, correction channel, erasure flow, schema approval, admin ownership, specialty vocabulary, source policy, source scope reopen, card link activation
- gate_contract_doc: ADG_EXTENSIONS_023

**Governance / Admin Needs**
- governance: partial — ownership model defined; correction channel not yet operational
- admin_owner: TBD — must be explicitly named before any activation
- notes: two-tier consent model applies (entities vs individuals per DD1); claiming deferred to MVP+

**QA Needs**
- base_template: LAYER E inherited
- module_qa_delta:
  - NEGATIVE: card-directorio-socios must have no href attribute
  - NEGATIVE: directorio.html must NOT be reachable via index.html navigation
  - NEGATIVE: directorio-socios.html must NOT be reachable via directorio.html navigation (blocked)
  - NEGATIVE: mapa-socios.html must NOT be linked from directorio.html
  - NEGATIVE: no adg_members data exposed anywhere
  - NEGATIVE: listado_socios_onlynames.txt path not referenced in any tracked source file

**Blockers to 100%**
- All 11 privacy/legal gates from doc 023 §16 (CRITICAL — all open)
- ADG-FAD authorization is the hardest dependency (requires board/association action)
- Specialty vocabulary must be operator-approved before filter activation

**Risk Level**: HIGH (privacy/legal — real personal data of real people)

**Can Advance Now / Later / End**: later — explicit operator decision after gate closure required

**Next TXT Lane**: TXT 129 — Directorio exposure decision

**Inherited Base Layers**: A, B, C, D, F

**Module-Specific Deltas**: Highest privacy complexity in the extension set; two-tier consent (entities admin-curated vs individuals explicit opt-in only); unclaimed individual profiles never shown publicly in MVP; phone field absolutely forbidden for public; claiming deferred; mapa_socios inherits all 11 gates.

---

### 7.5 Example Overlay — Alertas por Email (Final Lane)

**Identity**
- module_id: `mod-alertas-email`
- module_family: extension_module
- human_label: Alertas por Email
- source_doc: ADG_EXTENSIONS_021

**Route State**
- route_state: `stub_shell` (alertas.html — AlertasStub component; honest coming-soon UI)
- html_file: alertas.html
- prehub_parent: none
- child_surfaces: none

**Index State**
- index_state: `deferred_final_lane`
- card_id: card-alertas-email
- current_card_href: none (div, no href)

**Data / Process Needs**
- data_state: `blocked_by_gate`
- available: schema fully defined in doc 021; no data files exist or are allowed
- blocked: ALL data creation; no alertas_subscriptions, no preference data, no consent events, no delivery logs until ALL gates are closed
- data_contract_doc: ADG_EXTENSIONS_021

**Privacy / Legal / Consent Needs**
- gate_summary: 10 gates open — see doc 021 §14 and Layer D §4.8 of this document
- critical gate: legal/privacy review (D6) — this is a REQUIRED GATE, not optional commentary; no activation without it
- open_gates: consent text, privacy notice, legal review (D6), double opt-in flow, unsubscribe mechanism, provider decision, API credential boundary, admin ownership, schema implementation, Licitaciones cross-boundary trigger contract
- gate_contract_doc: ADG_EXTENSIONS_021

**Governance / Admin Needs**
- governance: partial — manual-first v1 workflow model locked (D2); admin ownership model defined but not formally designated
- admin_owner: TBD — must be explicitly named before any activation
- notes: no automated sending in v1; admin reviews and approves each digest before delivery

**QA Needs**
- base_template: LAYER E inherited
- module_qa_delta:
  - NEGATIVE: card-alertas-email must have no href attribute
  - NEGATIVE: alertas.html must show honest stub UI only (AlertasStub)
  - NEGATIVE: no subscription form active on alertas.html
  - NEGATIVE: no XHR, no fetch, no form action on alertas.html
  - NEGATIVE: no email provider connected
  - NEGATIVE: no data capture of any kind
  - CONFIRM: AlertasStub all inputs are disabled
  - CONFIRM: UI shows coming-soon state, not functional subscription flow

**Blockers to 100%**
- Legal/privacy review (D6) — CRITICAL — hardest gate; requires qualified external reviewer
- All 10 Alertas pre-activation gates (doc 021 §14) — all open
- Must not be reopened without explicit operator instruction

**Risk Level**: CRITICAL if activated without consent gates closed (email capture without consent)

**Can Advance Now / Later / End**: end — DEFERRED_FINAL_LANE; only after all other modules are assessed

**Next TXT Lane**: TXT 132 — Alertas final lane

**Inherited Base Layers**: A, B, C, D, F

**Module-Specific Deltas**: Final lane only; must not be treated as an immediate implementation target; AlertasStub keyword + health signal fields are prototype artifacts, NOT contracted MVP scope (D5 locked); contracted MVP scope is discipline + territory + frequency only; Formspree and Google Forms are explicitly excluded (removed TXT 052; not to be reintroduced).

---

### 7.6 Example Overlay — Oportunidades ADG

**Identity**
- module_id: `mod-oportunidades-adg`
- module_family: extension_module
- human_label: Oportunidades ADG
- source_doc: ADG_EXTENSIONS_022

**Route State**
- route_state: `active_prehub` (oportunidades.html — live prehub shell, no data)
- html_file: oportunidades.html (prehub), oportunidades-practicas.html, oportunidades-freelancers.html, oportunidades-profesional.html (all child shells)
- prehub_parent: none (oportunidades.html is itself the prehub)
- child_surfaces: oportunidades-practicas.html, oportunidades-freelancers.html, oportunidades-profesional.html

**Index State**
- index_state: `active`
- card_id: card-oportunidades-adg
- current_card_href: `./oportunidades.html`

**Data / Process Needs**
- data_state: `no_data` for now
- available: Prácticas field schema is locked (doc 022 §11A) — ready for data contract implementation when operator authorizes
- blocked: no mock or real listings; Freelancers/Profesional data blocked until deep fichas are closed; no oportunidades data files in data/public/
- data_contract_doc: ADG_EXTENSIONS_022

**Privacy / Legal / Consent Needs**
- gate_summary: LOW for Prácticas; MEDIUM for Freelancers/Profesional
- open_gates for Prácticas: legal terms for submitting organizations (OD14); admin ownership designation; card link activation already done
- open_gates for Freelancers: deep ficha must be closed before any field set is locked
- open_gates for Profesional: deep ficha must be closed before any field set is locked
- gate_contract_doc: ADG_EXTENSIONS_022

**Governance / Admin Needs**
- governance: partial — moderation-mandatory model locked; manual intake (email) locked; ownership model defined (OD5) but not formally designated
- admin_owner: TBD — must be named before intake opens
- notes: submission ≠ publication is the hard product doctrine for all three lanes; no automatic publishing ever

**QA Needs**
- base_template: LAYER E inherited
- module_qa_delta:
  - Confirm oportunidades.html (prehub) loads and renders 3 child cards
  - Confirm all 3 child shell pages (practicas, freelancers, profesional) load and show honest empty state
  - NEGATIVE: no forms active on any child shell
  - NEGATIVE: no mock listings rendered
  - NEGATIVE: no submitter email fields anywhere in public HTML
  - NEGATIVE: no Freelancers/Profesional implementation beyond shell until deep fichas closed

**Blockers to 100%**
- Freelancers deep ficha required (field set currently provisional; HIGH if bypassed)
- Profesional deep ficha required (same)
- Legal terms for submitting organizations (OD14) required before public intake (MEDIUM)
- Admin ownership designation (MEDIUM)
- No public self-submit until intake form/process/privacy contract separately approved

**Risk Level**: MEDIUM

**Can Advance Now / Later / End**: partial — Prácticas data contract is ready for doc/schema work when operator authorizes; Freelancers/Profesional blocked

**Next TXT Lane**: TXT 127 — module overlay matrix; later TXT for Oportunidades data seed (Prácticas only)

**Inherited Base Layers**: A, B, C, F

**Module-Specific Deltas**: Three-lane child model with different ficha closure states; `submission ≠ publication` is the hard product doctrine; Bolsa Profesional canonical name is locked — "Bolsa de Puestos Profesionales" is deprecated and must not be used; all lanes default `contact_policy: via_adg` until separately changed.

---

## 8. Cross-References to Existing Docs

| Doc | What it governs | Relationship to this doc |
|---|---|---|
| ADG_EXTENSIONS_000 | Extension framework; definition; phase/state model; extension list | Canonical framework; §§1–9 remain authoritative |
| ADG_EXTENSIONS_007 | Mock data module architecture; three-tier data classification; fixture strategy | Layer B data classification tiers derived from this; mock file strategy references here |
| ADG_EXTENSIONS_008 | Data ID table contract; column contracts; schema gap analysis; SQL-readiness | Layer B source-of-truth principles derived from this; column contracts remain authoritative here |
| ADG_EXTENSIONS_020 | Original ID taxonomy registry; naming conventions; reserved prefixes; dataset registry; SQL-readiness; mock data policy | §§1–4 and §§9–13 remain canonical; §§5–8 and §15 superseded by this document (Layer A) |
| ADG_EXTENSIONS_021 | Alertas consent + delivery contract; locked decisions D1–D10; schema; vocabularies; pre-activation gates | Layer C/D Alertas applications reference this doc; Layer G §7.5 Alertas overlay references this doc |
| ADG_EXTENSIONS_022 | Oportunidades process contract; locked decisions OD1–OD16; lane rules; schema; vocabularies; pre-activation gates | Layer C Oportunidades inheritance; Layer G §7.6 Oportunidades overlay references this doc |
| ADG_EXTENSIONS_023 | Directorio data + privacy contract; locked decisions DD1–DD17; 11 pre-activation gates; schema; vocabularies | Layer D Directorio gate application; Layer G §7.4 Directorio overlay references this doc |
| ADG_EXTENSIONS_028 | Map taxonomy closure; mapa_licitaciones vs mapa_socios distinction; locked naming convention | Layer A route registry mapa entries; Layer D mapa_socios gate application |
| ADG_EXTENSIONS_BATCH_1.3.1_INDEX | Batch baseline index; module state table; active reading order | Status reference; not superseded; still describes Batch 1.3.1 baseline |

---

## 9. HOLD Register

| Hold | Reason | Unblock path | TXT |
|---|---|---|---|
| Directorio index activation | 11 privacy/legal gates open (doc 023 §16) | All 11 gates explicitly closed by operator | TXT 129 |
| Alertas activation | All pre-activation consent/delivery gates open (doc 021 §14); DEFERRED_FINAL_LANE | All gates closed; operator opens final lane sequence explicitly | TXT 132 |
| Active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro) | Out of implementation scope in this branch; active production surfaces | Dedicated active-surface reopen prompt; separate audit and IMP sequence | TXT 130 |
| Data/listings/forms/provider/capture (Oportunidades, Directorio, Alertas) | Data and process contracts not yet fully closed per module | Per-module gate closure; operator explicit authorization | Per module |
| Private/member/support data | No contract exists for any private data use | Explicit operator contract naming the file, purpose, and scope | Contract required |
| `git add .` | Hard rule — always forbidden | Never — operator uses explicit file-level git add only | Permanent |

---

## 10. STOP

- No source HTML, CSS, or JS edits
- No data file writes
- No active surface edits
- No support/private/member file reads
- No git mutations by Claude CLI
- This document is planning/foundation canon only
- All staging, commit, push, and tag operations are performed by the operator manually
