# ADG EXTENSIONS — BATCH 1.3.1 — PLAN_MIN / DEEP AUDIT ROADMAP

Version: v0.1.3.1  
Batch: 1.3.1  
Status: AUDIT OUTPUT — DO NOT IMPLEMENT  
Mode: PLAN_MIN / DEEP_AUDIT_ROADMAP  
Branch: extensions  
Contract source: `adg_extensions_prompt_001_v0.1.3.1_deep_audit_roadmap.txt`  
Language: English  

---

## 1. EXECUTIVE VERDICT

**READY FOR ROADMAP ONLY**

- All Batch 1.3.1 extension fichas are closed and internally consistent. Hotfixes C6–C9 are applied. No doc-layer contradictions remain.
- No extension module is implementation-ready for a real dynamic product feature. All are blocked by missing data contracts, intake/moderation process definitions, or governance input.
- The hub/IA architecture is undefined. No extensions hub page exists. No module registry exists in the codebase. Building any extension UI before the hub IA is defined risks inventing architecture that contradicts later decisions.
- The first safe work is a static Hub IA planning document followed by a static stub-only extensions hub page. Both require no data contracts and no backend.
- Active surfaces (Estadísticas, Recursos, Acerca De) have closed design-direction fichas but have not been audited at the code level against those directions. That stream is separate from ADG Extensions but shares the same delivery environment.
- The system is ready to begin Phase 0 (discovery) and Phase 1 (Hub IA document). Implementation planning may start after the Hub IA is accepted.

---

## 2. REPO / BRANCH CHECK

| Item | Value |
|---|---|
| Root path | `K:\DEVKIT\projects\adg-ops\adg-ops` |
| Current branch | `extensions` |
| Base | `experimental/wip` HEAD |
| Remote tracking | None (local branch only) |
| Git status | Untracked: `.claude/`, `_tmp/`, `data/_backup/`, `docs/_old/`, several prompt `.txt` files in `docs/` |
| Uncommitted changes | None |

**Active extension docs found (9):**
- `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.1.md`
- `ADG_EXTENSIONS_001_LAUS_TRACKER_v0.1.3.1.md`
- `ADG_EXTENSIONS_002_DIRECTORIO_SOCIOS_v0.1.3.1.md`
- `ADG_EXTENSIONS_003_OPPORTUNITIES_FRAMEWORK_v0.1.3.1.md`
- `ADG_EXTENSIONS_003A_BOLSA_PRACTICAS_v0.1.3.1.md`
- `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1.md`
- `ADG_EXTENSIONS_004_ALERTAS_EMAIL_v0.1.3.1.md`
- `ADG_EXTENSIONS_BATCH_1.3.1_CROSS_SYSTEM_CONSISTENCY_v0.1.3.1.md`
- `ADG_EXTENSIONS_BATCH_1.3.1_INDEX_v0.1.3.1.md`

**Active surfaces docs found (4, in `active surfaces/` subdirectory):**
- `ADGOPS_ACTIVE_SURFACES_001_ESTADISTICAS_BAROMETRO_v0.1.0_closed.md`
- `ADGOPS_ACTIVE_SURFACES_002_DATA_VIS_GRAMMAR_v0.1.0_closed.md`
- `ADGOPS_ACTIVE_SURFACES_003_RECURSOS_CALCULADORA_v0.1.0_closed.md`
- `ADGOPS_ACTIVE_SURFACES_004_ACERCA_DE_v0.1.0_closed.md`

**Expected docs not present:**
- Hub/IA architecture doc — does not yet exist. Required before Phase 2.
- Data contract docs — none exist yet. Required before Phase 7+.
- Deep fichas for Bolsa de Freelancers and Bolsa Profesional — pending.

---

## 3. DOCUMENT INVENTORY

### ADG Extensions (implementation scope)

| File | Version | Role | Authority | Status | Impl. relevance | Notes |
|---|---|---|---|---|---|---|
| 000 EXTENSION_FRAMEWORK | v0.1.3.1 | Defines extension concept, phase/state rules, family | Primary framework | CLOSED | High — governs all extension work | Phase gap note added (3,4,6 reserved) |
| 001 LAUS_TRACKER | v0.1.3.1 | Editorial/historical awards archive spec | Closed ficha | CLOSED | LOW until data contract | Blocked by data access |
| 002 DIRECTORIO_SOCIOS | v0.1.3.1 | Member directory module spec | Closed ficha | CLOSED | PARTIAL — legacy list exists | Gap between legacy and module not yet mapped in code |
| 003 OPPORTUNITIES_FRAMEWORK | v0.1.3.1 | Parent opportunity hub spec | Closed framework | CLOSED | LOW — stub only | No intake/process contract |
| 003A BOLSA_PRACTICAS | v0.1.3.1 | Internship/junior opportunity lane spec | Closed child lane | CLOSED | LOW — stub only | No publication process |
| 003B_003C FREELANCERS_PROFESIONALES | v0.1.3.1 | Scoped placeholder for two lanes | Scoped/partial | SCOPED | NONE currently | Needs deep fichas |
| 004 ALERTAS_EMAIL | v0.1.3.1 | Email alert service spec | Closed ficha | CLOSED | LOW — stub only; AlertasStub exists in shared.js | No delivery/consent contract |
| BATCH_1.3.1_INDEX | v0.1.3.1 | Document index, state table | Index authority | CLOSED | Reference only | Active baseline |
| BATCH_1.3.1_CROSS_SYSTEM_CONSISTENCY | v0.1.3.1 | System-wide consistency report | Consistency authority | CLOSED | Reference only | C6–C9 resolved |

### ADGOPS Active Surfaces (supporting context — separate delivery stream)

| File | Version | Role | Impl. relevance | Notes |
|---|---|---|---|---|
| 001 ESTADISTICAS_BAROMETRO | v0.1.0 | Design direction for analytics surfaces | HIGH for Estadísticas/Barómetro redesign | Rail redesign, interpretive/dashboard split defined |
| 002 DATA_VIS_GRAMMAR | v0.1.0 | Chart/color/density rules across all surfaces | HIGH for any chart work | Governs color tokens, density, no random colors |
| 003 RECURSOS_CALCULADORA | v0.1.0 | Recursos prehub model, Calculadora as first app | HIGH for Recursos redesign | Entry behavior fix required: nav should go to prehub, not Calculadora |
| 004 ACERCA_DE | v0.1.0 | About page hierarchy, WIP/contact/changelog | HIGH for About page | WIP visible, no Alertas claim, contact line needed |

---

## 4. CONSISTENCY AUDIT

### Batch 1.3.1 doc layer — CLEAN

All C1–C9 corrections are applied. No stale references, no naming inconsistencies, no phase/state contradictions remain in the extension docs.

### Remaining flags (non-blocking at doc level, action needed at app level)

**F1 — index.html home-cards vs Batch 1.3.1 state**  
Risk: UNKNOWN until Phase 0 inspection.  
The home-card stubs for Laus Tracker, Directorio, and Bolsa de Prácticas exist on index.html, but their labels, states, and copy have not been verified against Batch 1.3.1. The `roadmap-mini` section (F0–F8 phases) may reference outdated naming or states.  
Action: Phase 0 inspection. Fix in Phase 2 if misaligned.

**F2 — alertas.html stub vs Alertas extension doctrine**  
Risk: LOW-MEDIUM.  
`alertas.html` exists as a coming-soon stub. The `AlertasStub` component in `shared.js` provides a disabled UI. Both pre-date the Batch 1.3.1 Alertas ficha. The stub may claim or imply an active service (Formspree, form logic) that contradicts the current doctrine ("No existe nada as ADG Extension").  
Action: Phase 0 inspection. Fix in Phase 6 if contradictory.

**F3 — about.html active Alertas claims**  
Risk: LOW-MEDIUM.  
`about.html` was created early and may mention Alertas as beta/coming-soon in a way that contradicts the "no active Alertas claim" rule from ACTIVE_SURFACES_004.  
Action: Phase 0 inspection. Fix is part of About page active-surface work.

**F4 — Directorio legacy URL/path not documented**  
Risk: LOW.  
The extension docs say "a basic legacy directory exists as a long list/page" but its actual URL and file path in the repo are not identified in any ficha. The gap analysis (Phase 4) cannot proceed without this.  
Action: Phase 4 must locate the legacy directory surface in the repo.

**F5 — WIP vs Coming Soon labels not yet enforced in app**  
Risk: LOW.  
ACTIVE_SURFACES_004 defines the WIP/Coming Soon distinction. This distinction does not yet exist as a formal visual system in the app (there is only `.home-tag.tag-soon`). The extensions hub (Phase 2) will need to implement or respect this two-state model.  
Action: Define in Phase 1 Hub IA doc.

**F6 — Nav hardcoded in 8 HTML files**  
Risk: MEDIUM (mechanical, not complex).  
When the extensions hub page is created, the navigation must be added to all 8 existing HTML pages manually. No shared partial exists. This is a known structural limitation.  
Action: Accept risk. Update 8 files in Phase 2. Future refactor is out of scope for this batch.

---

## 5. MODULE READINESS TABLE

| Module | Current state | Maturity | Data dependency | UI readiness | Impl. readiness | Blocker / debt | Recommended next action |
|---|---|---|---|---|---|---|---|
| Extension Framework | — | Conceptual baseline complete | None | None (governance doc) | Ready for hub IA planning only | Hub IA not defined | Produce Hub IA doc (Phase 1) |
| Laus Tracker | Esperando datos | Closed ficha | CRITICAL — full LAUS historical dataset, defined schema, source confirmed | Data atom defined; navigation model defined; no UI spec | BLOCKED | No data source or contract | Data source investigation (Phase 7 prep) |
| Directorio de Socios | Legacy / partial exists | Closed ficha | HIGH — member DB, privacy model, profile claim model | Profile card model defined; no UI spec | BLOCKED for new module | Data contract + privacy model + legacy gap | Legacy gap analysis (Phase 4) |
| Oportunidades ADG | No existe nada as product module | Closed framework | HIGH — intake/moderation process contract | Sub-home model defined; no UI spec | BLOCKED | No intake/process contract | Stub architecture only (Phase 5) |
| Bolsa de Prácticas | No existe nada | Closed child lane | HIGH — publication process, moderation workflow, offer fields | Offer fields defined; no UI spec | BLOCKED | Intake + moderation contract | Stub card only; defer implementation |
| Bolsa de Freelancers | Not implemented | Scoped only | PENDING — deep ficha first | None | BLOCKED | Deep ficha required | Deep ficha (future batch) |
| Bolsa Profesional | Not implemented | Scoped only | PENDING — deep ficha + governance | None | BLOCKED | Deep ficha + governance review | Governance first, then deep ficha |
| Alertas por Email | No existe nada as ADG Extension | Closed ficha | HIGH — consent, delivery, trigger contract | AlertasStub exists in shared.js (coming-soon placeholder) | BLOCKED for real service | Consent/delivery/data contract | Audit existing stub vs doctrine (Phase 6) |

---

## 6. IMPLEMENTATION ROADMAP PROPOSAL

### Phase 0 — Repo / Current Implementation Discovery

**Goal:** Audit the current app files before any extensions work begins. Establish ground truth.

**What enters:**
- Read `index.html` — home-cards for Laus, Directorio, Bolsa; roadmap-mini F0–F8; current nav labels
- Read `alertas.html` — coming-soon stub state; any Formspree reference
- Read `about.html` — current Alertas mentions; WIP claims; extensions mentions
- Read `app.js` I18N keys — identify any existing extension-related keys; check roadmap copy
- Read `shared.js` AlertasStub section — confirm what it renders and whether it implies a live service
- Read `style.css` — confirm `.home-card--soon` and `.home-tag.tag-soon` classes exist and their current spec

**What stays out:** Any file edits. Any commits.

**Output artifact:** Findings appended to this roadmap as Appendix A, or as a brief inline report.

**Smoke check:** Do the home-cards and roadmap-mini in index.html match Batch 1.3.1 state? Does alertas.html contain any Formspree or active-service claim?

**Risk:** NONE — read-only.

---

### Phase 1 — Hub / IA Audit

**Goal:** Define the information architecture for the ADG Extensions hub before any UI work begins.

**What enters:**
- Hub page IA document (new `.md` file in extensions folder)
- Defines: which modules appear on the hub, in what order, with what labels
- Defines: active vs disabled/stub card visual states
- Defines: WIP vs Coming Soon distinction in the hub context
- Defines: relationship of hub to Licitaciones (primary core module), and to existing nav
- Defines: nav label for the hub page (blocking question — see Section 9)
- Defines: whether Oportunidades ADG is a card in the hub or gets its own sub-home entry point

**What stays out:** Any app file edits. Oportunidades sub-home IA (Phase 5). Active surfaces redesign.

**Output artifact:** `ADG_EXTENSIONS_HUB_IA_v0.1.0.md` in extensions folder.

**Smoke check:** Hub IA reviewed and approved by operator before Phase 2 begins.

**Risk:** NONE — planning document only.

---

### Phase 2 — Static Extensions Hub Shell + Stub State Model

**Goal:** Create the ADG Extensions hub page as a static HTML file with all modules as grey/disabled stubs. No active service. No data. No form.

**What enters:**
- New `extensions.html` — hub page with stub cards for all defined modules
- Possibly new `extensions.js` — minimal page-init IIFE (if needed for i18n/theme)
- New i18n keys in `app.js` — hub labels, module descriptions, stub copy
- CSS additions in `style.css` — if new stub/disabled card variants are needed beyond `.home-card--soon`
- Nav update in all 8 existing HTML files — add extensions hub tab

**What stays out:** Any live module activation. Any form, backend, or data load. Oportunidades sub-home (Phase 5). Alertas stub update (Phase 6). Any active-surface redesign.

**Output artifact:** `extensions.html` visible at port 8080; all existing modules appear as disabled stubs with correct state labels.

**Smoke check:**
1. Navigate to `extensions.html` — hub loads
2. All module cards are visually disabled/stub — none imply active service
3. WIP vs Coming Soon labels are correct per approved IA
4. Theme toggle (light/dark) works
5. Language switch works
6. Nav link from all 8 pages reaches the hub
7. Back-navigation from hub to other pages works

**Risk:** LOW-MEDIUM. Nav update across 8 files is mechanical but error-prone. Must be done with care.

---

### Phase 3 — Active Surfaces Boundary Check

**Goal:** Verify that the three active surfaces with design-direction fichas (Alertas, About, Recursos) are not making claims that contradict their ficha doctrines. This is an audit, not a redesign.

**What enters:**
- Audit `alertas.html` vs ALERTAS_EMAIL ficha (no active service claim)
- Audit `about.html` vs ACERCA_DE ficha (WIP visible, no Alertas claim, contact line present/absent)
- Audit `recursos.html` entry behavior vs RECURSOS_CALCULADORA ficha (prehub vs direct Calculadora)
- Audit `estadisticas.html` vs ESTADISTICAS_BAROMETRO ficha (Barómetro toggle present, rail model)

**What stays out:** Full redesign of any surface. That work belongs to the active-surfaces implementation prompts, not this pass.

**Output artifact:** Gap report per surface (4 items). Classify each as: Compliant / Minor gap / Major gap / Contradicts ficha.

**Smoke check:** No surface is making a claim that contradicts its closed ficha.

**Risk:** LOW — read-only audit.

---

### Phase 4 — Directorio Legacy-to-Future Gap Analysis

**Goal:** Locate the existing legacy directory in the repo, audit it against the Directorio de Socios ficha, and document the gap between current state and intended future module.

**What enters:**
- Find the legacy directory URL/page in the repo (currently undocumented in fichas)
- Read the legacy directory HTML/JS — what it shows, how it loads data, what filtering exists
- Document gap: what the legacy list is vs what the full Directorio module requires

**What stays out:** Any Directorio implementation. Data contract definition (Phase 7).

**Output artifact:** `ADG_EXTENSIONS_002_DIRECTORIO_GAP_v0.1.0.md` in extensions folder.

**Smoke check:** Gap doc reviewed by operator. Legacy URL confirmed and documented.

**Risk:** LOW.

---

### Phase 5 — Oportunidades ADG Hub/Stub Architecture

**Goal:** Design the Oportunidades ADG sub-home stub — the parent entry point showing three child lane cards (Prácticas, Freelancers, Profesional), all in disabled/en-preparación state.

**What enters:**
- IA document for Oportunidades sub-home
- Card states for each child lane: Bolsa de Prácticas (stub), Bolsa de Freelancers (stub), Bolsa Profesional (stub)
- "en preparación" visual model for non-active lanes

**What stays out:** Any intake form. Any publication flow. Any moderation logic. Any Prácticas opportunity list.

**Output artifact:** `ADG_EXTENSIONS_003_OPORTUNIDADES_HUB_IA_v0.1.0.md` in extensions folder.

**Smoke check:** IA approved before any Oportunidades sub-home page is created.

**Risk:** LOW — planning document only.

---

### Phase 6 — Alertas Placeholder Refinement

**Goal:** Review the existing `alertas.html` and `shared.js` AlertasStub. If they contradict the Alertas ficha doctrine, apply minimal corrective patch only.

**What enters:**
- Patch `alertas.html` if it contains active service claims (Formspree, live form, beta claim)
- Patch `shared.js` AlertasStub section if it implies active subscription/delivery
- Ensure stub is correctly labelled as coming-soon with no live backend implied

**What stays out:** Any real alert logic. Any provider integration. Any subscription form activation.

**Output artifact:** Verified/patched stub. Alertas page and component correctly reflect current state.

**Smoke check:**
1. `alertas.html` at port 8080 — no active form, no submission path
2. No Formspree endpoint referenced
3. Correct coming-soon language per I18N keys

**Risk:** LOW. Scoped to removing/correcting false claims only.

---

### Phase 7 — Data Contract Package

**Goal:** Produce data contract draft documents for all closed extensions. No implementation until contracts are reviewed.

**What enters:**
- Data contract draft for Laus Tracker (award/project/edition schema, source TBD)
- Data contract draft for Directorio (member identity, profile type, location, specialties, public/private)
- Data contract draft for Oportunidades / Prácticas (opportunity fields, publication status, ADG review state)
- Data contract draft for Alertas (email, preferences, consent, unsubscribe, trigger, send state)

**What stays out:** Freelancers and Bolsa Profesional (need deep fichas first). Any live implementation.

**Output artifact:** Four data contract `.md` files in extensions folder.

**Smoke check:** Each contract reviewed and accepted by operator before any dynamic module work.

**Risk:** LOW — planning documents only.

---

### Phase 8 — Implementation Split Plan

**Goal:** After data contracts are accepted, produce a module-level implementation prompt for each closed extension. One prompt per module. No cross-module integration until individual modules are stable.

**What enters:** Accepted data contracts from Phase 7; accepted hub IA from Phase 1; accepted sub-home IA from Phase 5.

**What stays out:** Freelancers and Bolsa Profesional (still need deep fichas). Cross-module profile linking (deferred until profiles exist).

**Output artifact:** One implementation prompt `.md` per module (4 prompts: Laus, Directorio, Oportunidades/Prácticas, Alertas).

**Smoke check:** Each prompt reviewed and approved before any code is written.

**Risk:** MEDIUM — first real implementation work begins here.

---

## 7. FIRST IMPLEMENTATION CANDIDATE

**Recommended: Phase 1 → Phase 2 — Hub IA Document + Static Extensions Hub Shell**

Phase 1 (Hub IA doc) is the immediate next action. It is purely a planning document — no code, no file edits, zero risk. It must be completed and approved before Phase 2 begins.

Phase 2 (static hub shell) is the first actual code-producing slice. It is the safest possible visible deliverable:
- Requires no data contracts
- Requires no backend, no forms, no services
- Relies entirely on existing CSS/JS patterns (`.home-card--soon`, `.home-tag`, `data-i18n`, `initShared()`)
- The `AlertasStub` component in `shared.js` is already a reference model for how stub UI works
- Produces a visible, testable output on port 8080
- Consistent with the framework doctrine ("grey disabled stub in hub")

**Prerequisite:** Phase 1 Hub IA doc must be written and operator-approved before any `extensions.html` code is touched.

**Scope boundary:** Phase 2 produces only disabled/stub cards. Zero module activation. Zero data loads. The hub page is a static planning surface, not a working product.

---

**Deferred/alternative slices (in priority order):**

1. Phase 0 (repo discovery) — should run before Phase 1, but is read-only and may be done inline. Low effort, confirms ground truth before any doc is written.
2. Phase 6 (Alertas stub check) — can run in parallel with Phase 1 after Phase 0 confirms what alertas.html contains. Low effort if no contradictions found.
3. Phase 3 (Active surfaces boundary check) — important but does not block the extensions hub work. Can run after Phase 2 is shipped.
4. Phase 4 (Directorio gap analysis) — useful before any Directorio-related hub card copy is finalized. Can run during Phase 1/2 preparation.
5. Phases 5, 7, 8 — all deferred until hub shell and boundary checks are complete.

---

## 8. FILES TO INSPECT NEXT

**For Phase 0 (read-only discovery):**

`index.html; alertas.html; about.html; app.js; shared.js; style.css`

**For Phase 1 (Hub IA doc — no files needed, planning only).**

**For Phase 2 (hub shell, after Phase 1 approval):**

`index.html; licitaciones.html; estadisticas.html; recursos.html; mapa.html; alertas.html; about.html; barometro.html; style.css; app.js; shared.js`

Note: All 8 HTML files are required for Phase 2 because the navigation update touches each one.

---

## 9. CRITICAL QUESTIONS

**Q1 — Hub page nav label [BLOCKING for Phase 1]**

The extensions hub page requires a navigation tab in the app's main nav. The current tabs are: Inicio / Licitaciones / Estadísticas / Recursos / Mapa / Alertas / Acerca de.

What should the new tab be called?

Candidates:
- "Plataforma"
- "Módulos"
- "ADG+"
- "Extensiones"
- Other (operator-provided)

This label must be decided before the Hub IA doc can be written. It affects nav copy, page title, URL (`/extensions.html` or `/plataforma.html`), and i18n keys across 4 languages.

**Q2 — Hub IA output path [BLOCKING for Phase 1]**

Should the Hub IA document go into the `extensions/` planning folder (alongside the fichas), or into the repo's `docs/` folder (alongside the prompt contract files)?

Proposed default: `extensions/` folder, following the existing Batch 1.3.1 naming convention.
Alternate: `docs/` folder, to keep planning docs co-located with the repo.

Confirm or redirect.

---

## APPENDIX — Active Surfaces Classification

These four docs are present in `extensions/active surfaces/` and were read as supporting context per the contract instructions. They are classified here but are **not** ADG Extensions implementation scope in this batch.

| Surface | Ficha | Design direction defined | Main gaps vs current app | Delivery stream |
|---|---|---|---|---|
| Estadísticas / Barómetro | 001 | Yes — analytical split, rail redesign, dashboard vs report posture | Rail recycled from Licitaciones; Barómetro needs interpretive layer; monthly chart is black block wall | Active surfaces stream |
| Data Vis Grammar | 002 | Yes — chart grammar, color tokens, density rules | No color token system yet; random chart colors currently | Cross-cutting; applies to all surfaces |
| Recursos / Calculadora | 003 | Yes — prehub model; Calculadora as first app card | Recursos nav likely goes directly to Calculadora, not prehub | Active surfaces stream |
| Acerca De | 004 | Yes — hierarchy, WIP visible, no Alertas claim, contact line | About may still claim Alertas; changelog needs better UI; contact line missing | Active surfaces stream |

None of these surfaces block ADG Extensions hub work. They should be sequenced as a parallel or subsequent delivery stream after the extensions hub shell is stable.

---

## STOP

This document is the PLAN_MIN / DEEP_AUDIT_ROADMAP output for Batch 1.3.1.  
Do not implement from this document.  
Proceed to Phase 0 (read-only discovery) and then Phase 1 (Hub IA document) after blocking questions are resolved.
