# ADG_EXTENSIONS_009 — Laus Jury Import Strategy

**Version:** v0.1.3.1
**Status:** PLAN / NOT IMPLEMENTED
**Mode:** PLAN_MIN
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**Git write operations:** FORBIDDEN — all git mutations performed by operator only
**Source files read:** laus_2016.txt through laus_2026.txt, laus.js, juries.json, categories.json, editions.json, ADG_EXTENSIONS_008 Data ID + Table Contract

---

## 1. Executive Verdict

**READY FOR YEAR-BY-YEAR IMPORT AFTER OPERATOR APPROVAL**

- All 11 support_copys exist and contain jury sections with extractable name/role/studio/category data
- Consistent structure across most years; minor deviations documented per year below
- Chair detection varies by year — 2016 embeds chair in role text; 2017–2020 use explicit label lines; 2021–2026 have no chair labels in source (all `is_chair` will be `null`)
- **One pre-import confirmation required before the 2024 slice only:** two category heading abbreviations in laus_2024.txt ("Editorial y dir. arte", "Com. gráfica y publicidad") do not exactly match categories.json labels — operator must confirm these map to the full labels before 2024 import
- Seed reconciliation is straightforward: existing 33 seed IDs must be preserved; new records append with NNN continuing from 004+

---

## 2. Branch / Worktree / Git Check

| Field | Value |
|---|---|
| Path | K:/DEVKIT/projects/adg-ops/adg-ops_extensions |
| Branch | extensions |
| Last commit | a6a7ddd ADG Extensions Phase 2R-4B preflight add jury category IDs |
| Staged changes | None (juries.json committed by operator) |
| Untracked | docs/support_copys/, docs/wrkops/, docs/_old/ — read-only source material |
| Status | SAFE for read-only planning |
| Git mutations | None performed |

---

## 3. Current Data Baseline

| Dataset | Count | Notes |
|---|---|---|
| editions.json | 11 records | 2016–2026 |
| categories.json | 68 records | 5 categories for 2016–2019, 6 for 2020–2023, 8 for 2024–2025, 9 for 2026 |
| juries.json | 33 records | Phase 2R-4B-preflight complete |

**Current juries schema keys:** `id`, `year`, `name`, `role`, `studio_or_context`, `category_judged`, `category_id`, `is_chair`, `import_batch`, `source`, `source_file`

- `category_id` and `import_batch`: present on all 33 seed records ✓
- Renderer impact: `laus.js` groups by `category_judged` and ignores unknown fields — tolerates the full import schema without changes
- No UI or source changes needed for the jury import

---

## 4. Support_Copy Inventory

| File | Lines | Jury present | Categories extractable | Chair extractable | Confidence | Notes |
|---|---|---|---|---|---|---|
| laus_2016.txt | ~622 | YES | YES — 5 categories | PARTIAL — embedded in role text | MEDIUM | Content triplicated in file; chair not on separate label line |
| laus_2017.txt | ~607 | YES | YES — 5 categories | YES — explicit Chairman/Chairwoman label | HIGH | Content appears twice; students page separate section |
| laus_2018.txt | ~466 | YES | YES — 5 categories | YES — explicit Chairman/Chairwoman label | HIGH | Clean single pass |
| laus_2019.txt | ~392 | YES | YES — 5 categories | HIGH — but 2 Chairwoman labels in DG section | MEDIUM | Dual chairwoman in DG needs operator review |
| laus_2020.txt | ~442 | YES | YES — 6 categories incl. Aporta | YES — explicit labels | HIGH | File includes 2021 homepage at end (ignore) |
| laus_2021.txt | ~444 | YES | YES — 5 categories (no Aporta jury section) | NO — no chair labels | HIGH | All is_chair: null |
| laus_2022.txt | ~565 | YES | YES — 6 categories incl. Aporta | PARTIAL — Estudiantes chair only | HIGH | Chair label only for Estudiantes; others null |
| laus_2023.txt | ~530 | YES | YES — 6 categories incl. Aporta | NO — no chair labels | HIGH | Content repeated; jury extractable from first pass |
| laus_2024.txt | ~556 | YES | YES — 8 categories, BUT 2 abbreviated headings | NO — no chair labels | MEDIUM | "Editorial y dir. arte" and "Com. gráfica y publicidad" are abbreviated — need operator confirmation before import |
| laus_2025.txt | ~614 | YES | YES — 8 categories, full labels | NO — no chair labels | HIGH | Complete edition (Nit held); content duplicated |
| laus_2026.txt | ~504 | YES | YES — 9 categories, full labels | NO — no chair labels | HIGH | Active edition — no Premiados tab; jury is public but awards not yet announced |

---

## 5. Source Structure Analysis

**Recurring jury section markers:**
- Category heading as a standalone line (e.g., `Diseño Gráfico`, `Digital`, `Packaging`)
- Followed by person blocks: Name line → Role/Studio line → `Ver perfil` line (or empty lines)
- Section ends at next category heading or footer text

**Category heading patterns:**
- 2016–2023: Simple short labels (`Diseño Gráfico`, `Digital`, `Publicidad`, `Audiovisual`, `Estudiantes`, `Aporta`)
- 2024 source: Abbreviated (`Editorial y dir. arte`, `Com. gráfica y publicidad`) — not matching categories.json
- 2025 source: Full labels matching categories.json exactly
- 2026 source: Full labels matching categories.json exactly

**Name/role/studio patterns:**
- Name on one line
- Role and studio on next line, often as `Role, Studio` or `Role` only
- `Ver perfil` or blank lines as separators
- 2016 roles sometimes include company name inline: `Diseñadora Gráfica e Ilustradora` or `Director de Arte, Mucho`

**Chair indicators by year:**
- **2016:** Chair embedded in role text: `Chairman, Director de Arte y Diseñador Gráfico`. No separate label line. Affects: Ivan Serrano Regol (Digital), Albert Romagosa (Estudiantes). DG section: no chair identified from source text.
- **2017–2020:** Explicit `Chairman` or `Chairwoman` label line appears BEFORE the name line. Reliable detection.
- **2021:** No chair labels anywhere in the jury section. All `is_chair: null`.
- **2022:** `Chairman` label present only for Juan Carlos Gauli (Estudiantes). Other categories: no label → `null`.
- **2023–2026:** No chair labels. All `is_chair: null`.

**Years with different formatting:**
- 2016: Chair info embedded in role text; content triplicated in file
- 2019: Two `Chairwoman` labels in Diseño Gráfico (Ainhoa Nagore and Olga Pérez) — anomalous
- 2020: Aporta jury section lists all category chairs plus external members; some names overlap with individual category sections
- 2024: Abbreviated category headings

**Years with partial data:**
- 2026: Active edition. Jury is public. Awards not yet announced. No `Nit Laus` tab in nav.
- 2025: Edition complete, data appears full.

**Years requiring manual review before import:**
- 2016: Chair role parsing
- 2019: Dual chairwoman anomaly in DG
- 2024: Category label abbreviation confirmation

---

## 6. Target Data Model for Full Jury Import

Every full jury record must have:

| Field | Value / Rule |
|---|---|
| `id` | `laus-jury-YYYY-NNN` — immutable once assigned |
| `year` | Integer |
| `name` | String from source |
| `role` | String from source, or `null` if absent |
| `studio_or_context` | String from source, or `null` if absent |
| `category_judged` | Denormalized label from source category heading |
| `category_id` | FK to categories.json for same year — must match exactly or be `null` with reason |
| `is_chair` | `true` if explicit chair label in source; `null` if unknown; `false` only if positively confirmed not chair |
| `import_batch` | Per-year batch identifier (see §10) |
| `source` | `"adg-public"` |
| `source_file` | Corresponding `laus_YYYY.txt` filename |

Rules:
- `category_judged` must retain the exact source heading text as imported
- `category_id` must resolve to a real `categories.id` for the same year — no fuzzy matching
- If the source uses an abbreviated heading ("Editorial y dir. arte"), store the abbreviated text in `category_judged` AND flag the `category_id` as `null` / unresolved until operator confirms the mapping
- `source` is always `"adg-public"` — no exceptions

---

## 7. ID Generation Strategy

**Pattern:** `laus-jury-YYYY-NNN` (NNN zero-padded to 3 digits)

**Recommended approach: A — Append new rows, preserve seed IDs**

Rationale:
- Existing seed IDs (001, 002, 003 per year) reference real people from the source and must not change (immutability rule from ADG_EXTENSIONS_008)
- Seed people (e.g. laus-jury-2016-001 = Albert Romagosa) appear in the full source — they will remain as their existing rows, now part of the full year import
- New full-import rows for a given year are assigned NNN = 004, 005, 006... sequentially
- NNN within a year does not need to reflect source order — it is an opaque row identifier

**Collision prevention:**
- Before writing any import slice, the PREWRITE must list all proposed IDs
- Within a year, no duplicate NNN
- No duplicate year + name + category_id combination unless manually confirmed as two different people sharing the same name in the same category

**Seed reconciliation on import:**
- For each seed row (001, 002, 003) in a given year: compare against source to verify name, category_judged, role match
- If source confirms the seed row is correct: keep existing row unchanged, keep the ID
- If source provides a correction (e.g. different role): update the seed row fields, document the correction in the PREWRITE report
- Do not silently overwrite — show before/after for any changed field

---

## 8. Seed Record Reconciliation Strategy

**Current seed rows are a representative sample, 3 per year.** Reconciliation plan per year:

1. For each year slice PREWRITE: identify which seed rows (001–003) correspond to source people
2. Confirm: same name, same category, same source_file — if all match, mark seed row as "confirmed, no change"
3. If role or studio text differs slightly (capitalisation, abbreviation): show the diff, operator decides
4. After reconciliation, remaining full-import rows append as 004+

**Aporta participation rule:**
A jury row represents a jury/category participation record, not a unique person profile. The duplicate check is year + name + category_id, not year + name alone.

- Same person + same year + same category_id = duplicate candidate; avoid unless explicitly justified
- Same person + same year + different category_id = allowed when the source explicitly lists them under both categories
- People appearing in both Aporta and another category should be treated as separate category participation records when the source explicitly lists them in both places
- Do not collapse or drop Aporta participation silently
- If a person appears in both Aporta and another category in the source, preserve both rows, each with its own `category_id` and `import_batch`, unless the operator explicitly decides otherwise

**Import_batch for seed rows:**
- Existing seed rows retain `import_batch: "phase2r4a-seed-v0.1.3.1"` — do not change this
- Newly appended full-import rows for the same year get the per-year import_batch (e.g. `"phase2r4c-full-juries-2016-v0.1.3.1"`)
- This allows clear distinction between original seed rows and full-import rows in any future audit

---

## 9. Category Matching Strategy

**Rules:**
1. Match `category_judged` (from source heading) exactly against `categories.label` for the same year
2. If exact match: set `category_id` to that categories.id
3. If no exact match: set `category_id: null` and report as unresolved in PREWRITE — DO NOT import without operator confirmation
4. No silent fuzzy matching
5. No new categories created — if a source category has no matching categories.id, stop and run a category preflight first
6. If categories.json lacks a category that appears in source: raise a blocking question before that year's import

**Known category label issues requiring pre-confirmation:**

| Year | Source heading | categories.json label | Status |
|---|---|---|---|
| 2024 | "Editorial y dir. arte" | "Editorial y dirección de arte" | Unresolved — operator must confirm before 2024 import |
| 2024 | "Com. gráfica y publicidad" | "Comunicación gráfica y publicidad" | Unresolved — operator must confirm before 2024 import |

All other year/category combinations: exact match verified in Phase 2R-4B-preflight or expected to match given full label available in source.

---

## 10. Import Batch Strategy

**Recommendation: per-year import_batch** for maximum traceability.

```
phase2r4c-full-juries-2016-v0.1.3.1
phase2r4c-full-juries-2017-v0.1.3.1
phase2r4c-full-juries-2018-v0.1.3.1
phase2r4c-full-juries-2019-v0.1.3.1
phase2r4c-full-juries-2020-v0.1.3.1
phase2r4c-full-juries-2021-v0.1.3.1
phase2r4c-full-juries-2022-v0.1.3.1
phase2r4c-full-juries-2023-v0.1.3.1
phase2r4c-full-juries-2024-v0.1.3.1
phase2r4c-full-juries-2025-v0.1.3.1
phase2r4c-full-juries-2026-v0.1.3.1
```

Per-year batches allow:
- Rolling back a single year's import without affecting others
- Auditing which rows came from which import pass
- Distinguishing seed rows (`phase2r4a-seed-v0.1.3.1`) from full import rows

Seed rows retain their existing `import_batch: "phase2r4a-seed-v0.1.3.1"` — do not update.

---

## 11. Validation Contract

**Before each import slice PREWRITE:**
- All proposed IDs are listed with their year, name, category
- No duplicate IDs within the batch
- No duplicate year + name + category_id (same person, same year, same category is a duplicate; same person, same year, different category is allowed when confirmed by source)
- All proposed `category_id` values verified against categories.json
- No unresolved category labels (null category_id rows explicitly listed with reason)
- Seed rows reconciliation report provided

**After each import slice write:**
- JSON parses without error
- Total record count increases by exactly the expected new row count (as listed in the approved PREWRITE for that slice)
- All new records have `id`, `year`, `name`, `category_judged`, `category_id` (or null with reason), `import_batch`, `source: "adg-public"`, `source_file`
- No duplicate `id` values in entire juries.json
- No duplicate year + name + category_id combination unless documented and approved
- Same year + same name + different category_id is allowed when confirmed by source
- If two different people share the same name in the same year/category: require manual disambiguation before import — do not import without operator confirmation
- Every new record has `import_batch` equal to the per-year batch string
- Spot-check: 3+ records per year against source text
- All non-null `category_id` values resolve to existing categories.json IDs for the same year
- No awards data, no member data, no private data
- `laus.js` renderer smoke: laus.html loads, year selector works, juries section renders grouped by category — no console errors
- `git status --short` shows only `M data/public/laus/juries.json`

---

## 12. Proposed Implementation Slices

> **Note:** Expected row counts below are preliminary estimates from support_copy review only. Exact row counts must be recomputed and listed in each year-specific PREWRITE before any write. The operator approves exact rows/counts per PREWRITE, not the approximate counts in this strategy document.

### Phase 2R-4C-A — 2016 only
- **Files:** `data/public/laus/juries.json`
- **Estimated new rows:** ~34 (37 total for 2016 approx., minus 3 seed rows; exact count determined in PREWRITE)
- **Risk:** MEDIUM — chair embedded in role text (2016 only); content triplicated in source file (parse once)
- **Seed reconciliation:** 3 rows confirmed, verify vs source
- **Category matching:** 5 exact matches expected (Diseño Gráfico, Digital, Publicidad, Audiovisual, Estudiantes)
- **Validation:** record count +N per approved PREWRITE; all 2016 rows present; spot-check 3 records
- **Commit boundary:** one commit for 2016 full import

### Phase 2R-4C-B — 2017, 2018, 2019
- **Files:** `data/public/laus/juries.json`
- **Estimated new rows:** ~87 new across three years (exact counts per PREWRITE)
- **Risk:** LOW for 2017, 2018; MEDIUM for 2019 (dual chairwoman in DG)
- **Category matching:** 5 exact matches per year
- **Operator review required before 2019 PREWRITE:** confirm which of Ainhoa Nagore / Olga Pérez is the actual Diseño Gráfico chair
- **Commit boundary:** one commit per year or one combined commit (operator decides)

### Phase 2R-4C-C — 2020, 2021
- **Files:** `data/public/laus/juries.json`
- **Estimated new rows:** ~65 new across two years (exact counts per PREWRITE)
- **Risk:** LOW — 2020 has clean structure; 2021 has no chair labels (all null, acceptable)
- **Category matching:** 6 per year for 2020 (incl. Aporta); 5 for 2021
- **Aporta note:** people listed under Aporta in source are preserved as separate participation rows per the Aporta rule in §8
- **Commit boundary:** one commit per year

### Phase 2R-4C-D — 2022, 2023
- **Files:** `data/public/laus/juries.json`
- **Estimated new rows:** ~66 new across two years (exact counts per PREWRITE)
- **Risk:** LOW — 2022 partial chair data (Estudiantes only, others null — acceptable)
- **Category matching:** 6 per year (incl. Aporta)
- **Commit boundary:** one commit per year

### Phase 2R-4C-E — 2024, 2025, 2026
- **Files:** `data/public/laus/juries.json`
- **Estimated new rows:** ~99 new across three years (exact counts per PREWRITE)
- **Risk:** MEDIUM for 2024 (abbreviated category headings); LOW for 2025; MEDIUM for 2026 (active edition)
- **Pre-condition for 2024 PREWRITE:** operator must confirm "Editorial y dir. arte" → "Editorial y dirección de arte" and "Com. gráfica y publicidad" → "Comunicación gráfica y publicidad" before that PREWRITE proceeds
- **2026 note:** active edition — jury is public, awards not yet announced; `import_batch: "phase2r4c-full-juries-2026-v0.1.3.1"`
- **Commit boundary:** one commit per year

### Phase 2R-4C-F — Final coverage audit
- **Files:** read-only audit only
- **Scope:** Verify total record count, no duplicates, all categories covered, all seed rows reconciled, all import_batch values correct
- **Output:** audit report only — no writes unless corrections needed

---

## 13. Operator Review Points

**Before each year's PREWRITE, operator must review:**
- Extracted row count for that year (listed in PREWRITE)
- Any unresolved category_id (null values and their reasons)
- Any duplicate year + name + category_id candidate within the year
- Names shared by different people in the same year/category: require explicit disambiguation
- Chair flags: list of is_chair: true rows and the source text that confirms them
- Role/studio text for any name where parsing ambiguity exists
- Aporta participation: list of people appearing in both Aporta and another category section — both rows to be preserved unless operator explicitly decides otherwise

**Year-specific reviews:**
- **2016:** Confirm chair detection from embedded role text (Ivan Serrano Regol, Albert Romagosa)
- **2019:** Confirm which of Ainhoa Nagore / Olga Pérez is the actual Diseño Gráfico chair (source shows both labeled "Chairwoman")
- **2024:** Confirm abbreviated category label mappings before PREWRITE

---

## 14. Prewrite Requirement for Next Step

The next implementation prompt must be a **PREWRITE for Phase 2R-4C-A (2016 only)**.

Requirements for that PREWRITE:
- List all proposed rows for 2016 with exact field values (or summarized table with enough diff-safe detail)
- Show seed reconciliation for laus-jury-2016-001, 002, 003 with before/after comparison
- List all 2016 category_id mappings
- Confirm chair detection for 2016
- Confirm import_batch: `"phase2r4c-full-juries-2016-v0.1.3.1"`
- Show exact record count delta (juries.json before → after)
- Ask operator for approval before writing

**Do not import all years in one prompt.** One year (or one approved slice) per approval cycle.

---

## 15. Blocking Questions

**No blocking questions for Phase 2R-4C-A (2016 only).**

Pre-conditions for later slices (not blocking now):
- **Before 2019 PREWRITE:** Operator confirms which of Ainhoa Nagore / Olga Pérez is the single Diseño Gráfico chair
- **Before 2024 PREWRITE:** Operator confirms "Editorial y dir. arte" = "Editorial y dirección de arte" and "Com. gráfica y publicidad" = "Comunicación gráfica y publicidad"

**Recommended next step:** Phase 2R-4C-A PREWRITE for 2016-only full jury import.

---

## 16. Stop

- No source/data edits
- No git mutations
- No implementation
- This artifact is strategy documentation only
