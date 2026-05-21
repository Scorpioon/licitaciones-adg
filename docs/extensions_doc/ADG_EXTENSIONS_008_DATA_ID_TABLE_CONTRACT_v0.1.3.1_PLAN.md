# ADG_EXTENSIONS_008 — Data ID + Table Contract

**Version:** v0.1.3.1
**Status:** PLAN / NOT IMPLEMENTED
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**Git write operations:** FORBIDDEN — all git mutations performed by operator only
**Protocol source:** docs/wrkops (read-only reference)

---

## Executive Verdict

**DATA CONTRACT NEEDS FIX BEFORE FULL JURY EXPANSION**

Current seed datasets are structurally sound and correct for Phase 2R-4A. Two schema gaps must be resolved before full jury expansion (Phase 2R-4B):

1. `juries.json` is missing `category_id` — required for stable FK linkage before expanded import
2. `juries.json` is missing `import_batch` — required for provenance tracking before expanded import

No awards, books, schools, studios, or member directory implementation yet. These are reserved for later phases.

---

## Spreadsheet-like Data Doctrine

All ADG Extensions public data follows a strict spreadsheet-like model:

| Concept | Rule |
|---|---|
| JSON file | = table |
| JSON object | = row |
| Object key | = column |
| `id` | = immutable, stable, unique row identifier |
| `null` | = unknown or empty cell — never omit required fields |
| `source` / `source_file` | = provenance columns — required on all public rows |
| Positional arrays | FORBIDDEN — no hidden meaning by index |
| Row order | No semantic meaning — do not rely on sort position |
| Inferred data | FORBIDDEN unless field is marked `estimated`, `derived`, `mock`, or `pending` |
| Key naming | `snake_case` |
| Encoding | UTF-8, no BOM |
| Structure | JSON array of named objects only — no nested tables |

The JSON → CSV → JSON round-trip rule applies: any table must survive export to CSV and re-import without data loss or ambiguity.

---

## Dataset Inventory

### editions.json — 11 records
- **ID pattern:** `laus-ed-YYYY`
- **Schema keys:** `id`, `year`, `edition_label`, `edition_number`, `participants`, `nationalities`, `awards_count`, `attendees_nit_laus`, `status_note`, `source`, `source_file`
- **Risk:** `edition_number` null for some records — acceptable for seed

### categories.json — 68 records
- **ID pattern:** `laus-cat-YYYY-slug`
- **Schema keys:** `id`, `year`, `label`, `source`, `source_file`
- **Risk:** `sort_order` absent — acceptable for seed; no `category_id` FK linkage consumed by other tables yet

### juries.json — 33 seed records (representative sample, not full historical import)
- **ID pattern:** `laus-jury-YYYY-NNN`
- **Schema keys:** `id`, `year`, `name`, `role`, `studio_or_context`, `category_judged`, `is_chair`, `source`, `source_file`
- **Risk:** `category_id` absent — **MUST FIX BEFORE EXPANSION**; `import_batch` absent — **MUST FIX BEFORE EXPANSION**

---

## ID Audit — Canonical Patterns

| Dataset | Pattern | Example |
|---|---|---|
| Editions | `laus-ed-YYYY` | `laus-ed-2026` |
| Categories | `laus-cat-YYYY-slug` | `laus-cat-2026-identidad-corporativa` |
| Juries | `laus-jury-YYYY-NNN` | `laus-jury-2026-001` |
| Awards (future) | `laus-award-YYYY-NNN` | `laus-award-2026-001` |
| Books/annuals (future) | `laus-book-YYYY` | `laus-book-2026` |
| Schools (future) | `laus-school-slug` | `laus-school-eina` |
| Studios/agencies (future) | `laus-studio-slug` | `laus-studio-example-studio` |
| Member directory (future) | `adg-member-NNNNN` | `adg-member-00123` |
| Derived stats (future) | `laus-stat-YYYY-slug` | `laus-stat-2026-top-studios` |

**ID immutability rule:** Once an `id` is assigned and in production use, it must never change. If a slug conflicts or must be corrected, add an alias field — do not alter the original `id`.

---

## Column Contracts

### editions

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-ed-YYYY` |
| `year` | integer | yes | |
| `edition_label` | string | yes | Safe display label, e.g. "ADG Laus 2026"; do not include edition numbers unless authoritatively confirmed. |
| `edition_number` | integer\|null | no | null acceptable for seed |
| `participants` | integer\|null | no | |
| `nationalities` | integer\|null | no | |
| `awards_count` | integer\|null | no | |
| `attendees_nit_laus` | integer\|null | no | |
| `status_note` | string\|null | no | Public-facing note on data completeness |
| `source` | string | yes | e.g. `adg-public` |
| `source_file` | string | yes | |

**Edition number metadata note:** `edition_number_estimated` and `edition_number_source` are metadata-only fields. They must never be rendered or treated as authoritative UI labels unless confirmed by an authoritative source and promoted into `edition_number`.

### categories

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-cat-YYYY-slug` |
| `year` | integer | yes | |
| `label` | string | yes | Category display name |
| `sort_order` | integer\|null | later | Not required for seed |
| `source` | string | yes | |
| `source_file` | string | yes | |

### juries

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-jury-YYYY-NNN` |
| `year` | integer | yes | |
| `name` | string | yes | |
| `role` | string\|null | no | Free-text role description |
| `studio_or_context` | string\|null | no | Studio or employer context |
| `category_judged` | string\|null | no | Denormalized display label — keep alongside `category_id` once added |
| `category_id` | string\|null | **MUST ADD BEFORE EXPANSION** | FK to `categories.id` |
| `is_chair` | boolean\|null | no | null = unknown; false = confirmed not chair |
| `import_batch` | string\|null | **MUST ADD BEFORE EXPANSION** | e.g. `2026-seed-001` |
| `source` | string | yes | |
| `source_file` | string | yes | |

### awards (future — Phase 2R-5)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-award-YYYY-NNN` |
| `year` | integer | yes | |
| `edition_id` | string | yes | FK to `editions.id` |
| `category_id` | string | yes | FK to `categories.id` |
| `category_label` | string | yes | Denormalized display label — store alongside `category_id` |
| `award_level_raw` | string | yes | Exact label as found in public source — never altered |
| `award_level_normalized` | string | yes | Controlled value — see taxonomy note below |
| `studio_or_agency` | string\|null | no | |
| `studio_id` | string\|null | later | FK to studios table once normalized |
| `school_id` | string\|null | later | FK to schools table once normalized |
| `project_title` | string\|null | no | |
| `source` | string | yes | |
| `source_file` | string | yes | |
| `source_url` | string\|null | later | |
| `import_batch` | string | yes | |

**Award taxonomy — `award_level_normalized` provisional values:**

| Value | Meaning |
|---|---|
| `gran_laus` | Gran Laus |
| `oro` | Oro |
| `plata` | Plata |
| `bronce` | Bronce |
| `inbook` | In Book / Selección |
| `other` | Any other awarded level |
| `pending` | Level not yet confirmed from source |

Rules:
- `award_level_raw` = exact label as found in the public source; never altered or normalized in place
- `award_level_normalized` = provisional controlled value from the list above
- Do not display `award_level_normalized` in the UI when `award_level_raw` is available
- Do not invent award levels
- Final taxonomy must be confirmed when real winners and awards source data are available
- Do not create awards data until Phase 2R-5 is approved

### books/annuals (future — Phase 2R-6)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-book-YYYY` |
| `year` | integer | yes | |
| `edition_id` | string | yes | FK to editions |
| `title` | string\|null | no | |
| `isbn` | string\|null | later | |
| `source` | string | yes | |
| `source_file` | string | yes | |

### schools (future — Phase 2R-7)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-school-slug` |
| `name` | string | yes | |
| `city` | string\|null | no | |
| `source` | string | yes | |
| `source_file` | string | yes | |

### studios/agencies (future — Phase 2R-7)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-studio-slug` |
| `name` | string | yes | |
| `city` | string\|null | no | |
| `source` | string | yes | |
| `source_file` | string | yes | |

### public member directory (future — Phase 2R-8)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `adg-member-NNNNN` |
| `display_name` | string | yes | |
| `discipline` | string\|null | no | |
| `city` | string\|null | no | |
| `member_since` | integer\|null | no | year |
| `source` | string | yes | Public ADG member directory only — no private fields |
| `source_file` | string | yes | |

### derived statistics (future — later phases)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `laus-stat-YYYY-slug` |
| `year` | integer\|null | no | null = cross-year stat |
| `stat_type` | string | yes | e.g. `top_studios`, `awards_by_category` |
| `value` | number\|null | no | |
| `label` | string\|null | no | |
| `source` | string | yes | `derived` |
| `derived_from` | string | yes | Source table(s) used |

### sources/provenance — reserved fields

| Field | Notes |
|---|---|
| `source` | Required on all rows: `adg-public` \| `mock` \| `pending` \| `derived` |
| `source_file` | Required when `source = adg-public` |
| `source_url` | Reserved — add when source URLs available |
| `source_accessed_at` | Reserved — ISO 8601 date |
| `import_batch` | Reserved — batch identifier string |
| `source_notes` | Reserved — free text |

---

## Schema Gap Analysis

| Gap | Severity | Action |
|---|---|---|
| `juries.category_id` missing | **SHOULD FIX BEFORE EXPANSION** | Add before Phase 2R-4B jury import |
| `juries.import_batch` missing | **SHOULD FIX BEFORE EXPANSION** | Add before Phase 2R-4B jury import |
| `id` slug immutability not enforced in tooling | **SHOULD FIX BEFORE EXPANSION** | Document in import scripts; do not alter existing IDs |
| `categories.sort_order` missing | ACCEPTABLE FOR SEED | Add in later refinement |
| `source_url` missing across tables | LATER | Reserved; add when source URLs available |
| `is_chair` null semantics | ACCEPTABLE FOR SEED | null = unknown; false = confirmed not chair |
| No `created_at` / `updated_at` | LATER | Not needed until multi-contributor workflow |
| `listado_socios` PDF not parsed | LATER | Out of scope until Phase 2R-8 |
| No awards table exists | LATER | Phase 2R-5 |
| `edition_number` null for some records | ACCEPTABLE FOR SEED | Fill in as official numbering confirmed |

---

## Relationship Model

```
editions (1) ─────────────────────────── categories (N)
     │                                        │
     └──── juries (N)                         │
                └─── category_id ─────────────┘  (FK — add before Phase 2R-4B)
                     category_judged              (denormalized label — keep both)

editions (1) ─────────────────────────── awards (N)  (future Phase 2R-5)
                                              ├─── category_id ──► categories
                                              ├─── studio_id   ──► studios (future)
                                              └─── school_id   ──► schools (future)
```

- `category_id` = stable FK for joins and filtering
- `category_judged` = denormalized display/export label — always store alongside `category_id` once added; do not remove it
- Derived statistics must never be stored in primary tables

---

## Source/Provenance Contract

| `source` value | Meaning |
|---|---|
| `adg-public` | Sourced from public ADG materials; `source_file` required |
| `mock` | Placeholder or synthetic data — must be replaced before production |
| `pending` | Real data not yet available; row is a placeholder |
| `derived` | Calculated from other tables; `derived_from` required |

---

## Editability / CSV Compatibility

- One row per record — no nested objects in primary tables
- No hidden multi-values in a single field
- Separate join tables preferred over embedded arrays
- `snake_case` keys throughout
- UTF-8, no BOM
- JSON → CSV → JSON round-trip must be lossless and unambiguous

---

## Data Quality Rules

- IDs unique within each table
- All required columns present on every row
- `source_file` required when `source = adg-public`
- `year` must be a numeric integer
- Use `null` for unknown/empty — never empty strings
- No duplicate juror rows within the same edition unless independently verified
- No fake award winners — ever, under any circumstances
- Do not derive `edition_number` in the renderer; store it in `editions.json`
- Do not infer member profiles from jury or awards data
- `category_id` references must resolve to existing `categories.json` IDs after the field is added
- No private data in any public-facing JSON file

---

## Renderer Contract (laus.js)

- May `fetch` local JSON from `./data/public/laus/` only
- May sort and group data for display
- Must handle `null` values gracefully — no crashes on missing fields
- Must not contain any inline data records
- Must not patch or augment data at runtime
- Must not create or display fake awards
- Must not infer `category_id` relationships — once `category_id` exists, use it directly
- Renderer/adapter only — all data lives in the JSON files

---

## Future Expansion Plan

| Phase | Scope | Status |
|---|---|---|
| 2R-4A | Laus Tracker modular JSON + CSS extract + platform shell alignment | **Committed** |
| 2R-4B | Add `category_id` + `import_batch` to juries; expand juries year-by-year | NEXT — preflight required |
| 2R-5 | Awards table contract + seed data import | Later |
| 2R-6 | Books/annuals | Later |
| 2R-7 | Schools + studios normalization | Later |
| 2R-8 | Member directory public baseline | Later |

---

## Recommended First Fix Before Full Jury Expansion (Phase 2R-4B Preflight)

Before importing full jury records for all editions:

1. Add `category_id` field to all existing `juries.json` records (`null` is acceptable for seed rows where category data is unavailable)
2. Add `import_batch` field to all existing `juries.json` records (e.g. `2026-seed-001`)
3. Validate that all non-null `category_id` values resolve to matching IDs in `categories.json` for the same `year`
4. Update this contract if the ID pattern or schema changes during preflight

This is a later implementation prompt. This artifact documents the requirement only — do not edit data files as part of this plan write.

---

## Git Status at Artifact Write

Branch: `extensions` — worktree K:/DEVKIT/projects/adg-ops/adg-ops_extensions

docs/adg_extensions_prompt_001–003, reply_004 — existing docs cleanup/deletion state; do not touch in this task

Last commit: `560af83 ADG Extensions Phase 2R-4A add Laus Tracker modular shell`

---

## Blocking Questions

None. Contract is ready for Phase 2R-4B preflight planning.

---

## Stop

- No source file edits
- No data writes
- No git mutations
- This artifact is contract documentation only
