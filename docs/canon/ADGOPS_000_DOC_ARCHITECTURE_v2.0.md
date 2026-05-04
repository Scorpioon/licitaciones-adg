# ADGOPS_000_DOC_ARCHITECTURE_v2.0

Status: ACTIVE DRAFT  
Authority: ADG OPS local document architecture  
Parent canon: WRKOPS / MDP / project-local truth  
Language: English  
Purpose: Define the wave-2 documentation system for ADG OPS so the suite can be read, audited, extended, and coded against without relying on chat memory.

---

## 0. What this document is

This is the document architecture for ADG OPS wave-2.

It exists to define:
- which canonical docs should exist
- what job each doc should do
- how docs relate to each other
- how current truth is separated from intended direction
- how surface docs should be structured
- how old docs should be archived

This is not:
- the roadmap itself
- a patch log
- a single surface doc
- a continuity pack by itself
- a coding prompt

One-line doctrine:

**ADG OPS docs must behave like a readable system, not like accumulated chat residue.**

---

## 1. Core documentation principles

### 1.1 Suite-first
ADG OPS is documented as a **complete suite**, not as a single page or a temporary patch lane.

That means the docs must support:
- current shipped or partially built surfaces
- current development truth
- future additions that are already strategically relevant

### 1.2 Surface-first
The preferred documentation lens is **surface-first**.

Default direction:
- document the suite
- document the surface map
- document runtime truth
- document individual surfaces
- document future systems only after current surfaces are legible

Surface-first does not mean “page-only.”

If a shared UI space contains functionally distinct systems, they may receive separate docs.

Locked example:
- `estadisticas` and `barometro` share UI space but are not the same surface truth
- `barometro` deserves its own doc

### 1.3 Current and intended must stay separate
ADG OPS docs must distinguish between:
- **current truth**
- **intended direction**

Rule:
- current truth explains what exists now
- intended direction explains where the suite is moving
- cross-references between both are allowed and encouraged
- but the two layers must not collapse into one blob

### 1.4 Repo truth is authoritative
The current repo is treated as:
- official development truth
- unpublished but valid
- separate from the live/main repo on purpose

Rule:
- the repo is the truth surface for current implementation reality
- docs must reflect that reality honestly
- docs must not pretend the live/main repo is the same thing as the active development repo

### 1.5 Wave-1 is reference material, not live canon
The first doc wave remains useful as:
- recovery evidence
- historical support
- partial source material

But wave-1 is not treated as the active architecture anymore.

Rule:
- move wave-1 docs to `._old\`
- create wave-2 as a clean active layer
- reuse wave-1 insights only when they still reflect current truth

---

## 2. Documentation families

## 2.1 Core suite docs

### ADGOPS_001_STATUS_QUO_v2.0
Job:
- state the current real working state
- state known blockers
- state current repo/version reality
- state what is true now without roadmap fog

### ADGOPS_002_SUITE_MAP_v2.0
Job:
- define ADG OPS as a suite
- list major surfaces
- explain high-level relationships
- state which areas are core, secondary, active, partial, or future-facing

### ADGOPS_003_SURFACE_MAP_v2.0
Job:
- map pages and surfaces
- explain where each surface lives
- show surface grouping and overlap
- expose surface hierarchy without inventing modules that the product does not support

### ADGOPS_004_RUNTIME_TRUTH_v2.0
Job:
- describe what the system does today
- describe runtime behavior, maturity, and fragility
- classify surfaces and components as:
  - stable
  - partial
  - fragile
  - broken
  - legacy
- include placeholder / synthetic / fake behavior when relevant

### ADGOPS_005_INTENDED_DIRECTION_v2.0
Job:
- define intended product direction
- explain what the suite is trying to become
- explain what is likely to change
- state future-facing system direction without pretending it already exists

### ADGOPS_006_FUTURE_MODULES_v2.0
Job:
- collect confirmed and strong-candidate additions
- describe future ecosystem capabilities
- keep long-range structure legible without turning into fantasy backlog

### ADGOPS_007_DATA_AND_FETCHING_v2.0
Job:
- explain current data intake reality
- explain current fetcher state and limitations
- explain intended future fetching/data architecture
- document active-but-incomplete data tooling honestly

---

## 2.2 Surface docs

Each major surface should have its own doc when it has enough identity, behavior, or fragility to justify it.

Planned wave-2 surface docs:
- `ADGOPS_SURFACE_index_v2.0`
- `ADGOPS_SURFACE_licitaciones_v2.0`
- `ADGOPS_SURFACE_estadisticas_v2.0`
- `ADGOPS_SURFACE_barometro_v2.0`
- `ADGOPS_SURFACE_mapa_v2.0`
- `ADGOPS_SURFACE_recursos_v2.0`
- `ADGOPS_SURFACE_alertas_v2.0`
- `ADGOPS_SURFACE_about_v2.0`

Rule:
- not all surface docs need equal depth
- `licitaciones` and `barometro` should be deeper
- `index` and `about` may begin as lighter docs and grow later if needed

---

## 2.3 Supporting docs

Allowed supporting docs when needed:
- glossary
- runtime/dependency notes
- architecture fichas
- continuity packs
- implementation handoff docs
- research / R&D notes

Rule:
- supporting docs must not duplicate the dominant jobs of the canonical docs

---

## 3. Surface doc template

Each surface doc should follow a stable medium-depth template.

Recommended structure:

## 0. What this surface is
- what it is
- why it exists

## 1. What the user sees
- visible regions
- major controls
- major outputs

## 2. What the user can do
- actions
- flows
- navigation consequences

## 3. Current behavior
- actual current runtime truth
- placeholder / synthetic behavior if present
- real vs partial implementation notes

## 4. Key files
- main code files
- supporting files
- important dependencies

## 5. Relationships to other surfaces
- where it links
- what it shares
- what it depends on
- what depends on it

## 6. Current maturity
- stable / partial / fragile / broken / legacy
- known issues
- fragility notes

## 7. Intended evolution
- what is likely to change
- what future direction exists
- what is not yet implemented

Rule:
- surface docs must explain both the screen and the system
- they must remain readable by humans and useful to coding LLMs

---

## 4. Cross-reference doctrine

ADG OPS wave-2 docs should behave like a documentation graph.

Rule:
- docs may reference other docs explicitly
- a doc may say “see” another doc when detail belongs elsewhere
- this should reduce duplication, not increase it

Preferred direction:
- reference by clear doc name
- optionally use local reference markers later if the system needs them

Examples:
- see `ADGOPS_004_RUNTIME_TRUTH_v2.0`
- see `ADGOPS_SURFACE_barometro_v2.0`
- see `ADGOPS_007_DATA_AND_FETCHING_v2.0`

Purpose:
- let the documentation system scale
- avoid turning each doc into a giant mixed blob
- let readers follow depth intentionally

---

## 5. Archive and replacement rule

Wave-1 docs should be moved to:
- `._old\`

Rule:
- keep them as historical support
- do not treat them as active canon
- do not keep active and superseded layers mixed in the main docs root

Wave-2 becomes the active reference set.

---

## 6. Naming direction

The local naming canon for ADG OPS wave-2 should stay:
- clear
- readable
- job-visible
- stable

Preferred pattern:
- `ADGOPS_###_<DOC_NAME>_v2.0.md`
- `ADGOPS_SURFACE_<surface_name>_v2.0.md`

Examples:
- `ADGOPS_001_STATUS_QUO_v2.0.md`
- `ADGOPS_004_RUNTIME_TRUTH_v2.0.md`
- `ADGOPS_SURFACE_licitaciones_v2.0.md`

Purpose:
- make the doc role visible from the filename
- keep suite docs and surface docs easy to scan

---

## 7. Creation order

Recommended order:

### Batch 1 — Core frame
1. `ADGOPS_000_DOC_ARCHITECTURE_v2.0.md`
2. `ADGOPS_001_STATUS_QUO_v2.0.md`
3. `ADGOPS_002_SUITE_MAP_v2.0.md`

### Batch 2 — Runtime and surfaces
4. `ADGOPS_003_SURFACE_MAP_v2.0.md`
5. `ADGOPS_004_RUNTIME_TRUTH_v2.0.md`

### Batch 3 — Intended future
6. `ADGOPS_005_INTENDED_DIRECTION_v2.0.md`
7. `ADGOPS_006_FUTURE_MODULES_v2.0.md`
8. `ADGOPS_007_DATA_AND_FETCHING_v2.0.md`

### Batch 4 — Surface docs
9. `ADGOPS_SURFACE_index_v2.0.md`
10. `ADGOPS_SURFACE_licitaciones_v2.0.md`
11. `ADGOPS_SURFACE_estadisticas_v2.0.md`
12. `ADGOPS_SURFACE_barometro_v2.0.md`
13. `ADGOPS_SURFACE_mapa_v2.0.md`
14. `ADGOPS_SURFACE_recursos_v2.0.md`
15. `ADGOPS_SURFACE_alertas_v2.0.md`
16. `ADGOPS_SURFACE_about_v2.0.md`

---

## 8. Locked decisions

- ADG OPS is documented as a suite
- docs are written in English
- current and intended remain separate
- surface-first is the dominant reading lens
- `barometro` gets its own doc
- the repo is official development truth
- wave-1 moves to `._old\`
- the fetcher is active runtime truth, but not the first deep-focus module doc
- `licitaciones` and `barometro` deserve deeper surface docs

---

## 9. One-line doctrine

**Build ADG OPS wave-2 docs as a readable system of truth surfaces, not as one more pile of markdown.**
