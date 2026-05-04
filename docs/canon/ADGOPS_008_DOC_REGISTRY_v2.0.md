# ADGOPS_008_DOC_REGISTRY_v2.0

Status: ACTIVE DRAFT  
Authority: ADG OPS wave-2 document registry  
Parent docs: `ADGOPS_000_DOC_ARCHITECTURE_v2.0`, `ADGOPS_001_STATUS_QUO_v2.0`  
Language: English  
Purpose: Provide a canonical registry for the ADG OPS wave-2 documentation system, define the role and authority of each document, and make the full doc network readable in the correct order.

---

## 0. What this document is

This is the canonical document registry for ADG OPS wave-2.

It exists to answer:
- which docs currently belong to the active documentation layer
- what job each doc performs
- what authority each doc has
- what reading order should be used depending on the task
- how wave-1 and wave-2 should be separated
- which docs are core, runtime, intended, surface, or support docs

This is not:
- a roadmap
- a patch log
- a surface doc
- a runtime truth doc
- a continuity pack by itself

One-line doctrine:

**If the ADG OPS docs are the network, this registry is the readable routing table.**

---

## 1. Registry rule

Wave-2 is the active documentation layer.

Rule:
- wave-2 docs are the docs that should be used for current reading, current reasoning, and future work support
- wave-1 docs remain useful as archive/reference material only
- active work should not rely on wave-1 as if it were live canon

Archive rule:
- superseded docs go to `._old\`
- wave-1 may still be referenced when historical recovery or older rationale is needed
- but wave-2 is the live documentation surface

---

## 2. Document families

The current ADG OPS wave-2 system is organized into these families:

### 2.1 Core frame docs
Purpose:
- define the documentation system
- define current truth
- define the suite reading

Docs:
- `ADGOPS_000_DOC_ARCHITECTURE_v2.0`
- `ADGOPS_001_STATUS_QUO_v2.0`
- `ADGOPS_002_SUITE_MAP_v2.0`

### 2.2 Runtime and topology docs
Purpose:
- explain where surfaces live
- explain runtime state and maturity
- expose current unevenness honestly

Docs:
- `ADGOPS_003_SURFACE_MAP_v2.0a`
- `ADGOPS_004_RUNTIME_TRUTH_v2.0a`

### 2.3 Intended future docs
Purpose:
- explain intended direction
- explain future modules/capabilities
- explain data/fetching direction without pretending it already exists

Docs:
- `ADGOPS_005_INTENDED_DIRECTION_v2.0`
- `ADGOPS_006_FUTURE_MODULES_v2.0`
- `ADGOPS_007_DATA_AND_FETCHING_v2.0`

### 2.4 Surface docs
Purpose:
- explain each visible surface in readable operational terms
- connect current behavior, key files, fragility, and intended evolution

Docs:
- `ADGOPS_SURFACE_index_v2.0`
- `ADGOPS_SURFACE_licitaciones_v2.0`
- `ADGOPS_SURFACE_estadisticas_v2.0`
- `ADGOPS_SURFACE_barometro_v2.0`
- `ADGOPS_SURFACE_mapa_v2.0`
- `ADGOPS_SURFACE_recursos_v2.0`
- `ADGOPS_SURFACE_alertas_v2.0`
- `ADGOPS_SURFACE_about_v2.0`

### 2.5 Checkpoint docs
Purpose:
- record stabilization or phase-close results
- bridge the gap between major canon doc waves and current repo truth
- preserve lane history without mutating the core frame docs

Docs:
- `ADGOPS_009_STABILIZATION_CHECKPOINT_v0.4.3p`

---

## 3. Canonical registry table

| Doc | Family | Authority level | Dominant job | Use when | Notes |
|---|---|---:|---|---|---|
| `ADGOPS_000_DOC_ARCHITECTURE_v2.0` | Core frame | High | Define the doc system itself | Starting wave-2 work, deciding how docs should be structured | Governs doc families and doc roles |
| `ADGOPS_001_STATUS_QUO_v2.1` | Core frame | High | State current project truth and blockers | Re-entry, current-state reading, before coding or planning | **Active version.** Supersedes v2.0. Updated at 0.4.3p checkpoint. |
| `ADGOPS_001_STATUS_QUO_v2.0` | Core frame | Archive | Historical source for STATUS_QUO | Historical reference only | Superseded by v2.1; retained as source |
| `ADGOPS_002_SUITE_MAP_v2.0` | Core frame | High | Define ADG OPS as a suite | Understanding product scope and suite composition | Broad system reading |
| `ADGOPS_003_SURFACE_MAP_v2.0a` | Runtime/topology | High | Map surfaces and hosting logic | Understanding where surfaces live and how they relate | Page-first with surface substructure |
| `ADGOPS_004_RUNTIME_TRUTH_v2.0a` | Runtime/topology | High | Describe current runtime reality and maturity | Coding support, audit support, truth-vs-wishlist separation | Includes fragility and placeholder logic |
| `ADGOPS_005_INTENDED_DIRECTION_v2.0` | Intended future | High | Explain where the suite is trying to go | Architecture thinking, future-safe coding judgment | Current and future must stay separate |
| `ADGOPS_006_FUTURE_MODULES_v2.0` | Intended future | Medium-High | Classify future additions | Understanding credible future growth | Domain + type + maturity |
| `ADGOPS_007_DATA_AND_FETCHING_v2.0` | Intended future / system | High | Explain current fetcher truth and broader data direction | Data architecture reading, fetcher context, future ingestion planning | Current tooling + future multi-fetcher line |
| `ADGOPS_SURFACE_index_v2.0` | Surface | Medium | Explain the entry surface | Reading the suite gateway | Light-first doc |
| `ADGOPS_SURFACE_licitaciones_v2.0` | Surface | High | Explain the core operational surface | Coding, product understanding, shell/data blockers | One of the most important docs |
| `ADGOPS_SURFACE_estadisticas_v2.0` | Surface | High | Explain configurable analytics | Analytics reading, current shell state, surface distinction | Must not be flattened into barometro |
| `ADGOPS_SURFACE_barometro_v2.0` | Surface | High | Explain period-based interpretive analytics | Sector reading, analysis identity, future deepening | One of the most important docs |
| `ADGOPS_SURFACE_mapa_v2.0` | Surface | Medium | Preserve spatial/contextual surface truth | Understanding support surfaces | Likely to grow later |
| `ADGOPS_SURFACE_recursos_v2.0` | Surface | Medium | Preserve resource-surface truth | Understanding support/resource role | Light-to-medium |
| `ADGOPS_SURFACE_alertas_v2.0` | Surface | Medium-High | Preserve alerts surface truth with future weight | Reading future service direction from current suite | More future-central than it may look |
| `ADGOPS_SURFACE_about_v2.0` | Surface | Medium | Explain framing/explanatory surface | Reading positioning and suite framing | Light-first doc |
| `ADGOPS_009_STABILIZATION_CHECKPOINT_v0.4.3p` | Checkpoint | Medium | Record 0.4.3k–0.4.3p lane results and current version baseline | Re-entry after stabilization work; before 0.4.4 fetcher lanes | Bridges Wave-2 canon and current repo truth |

---

## 4. Authority model

Use this reading model:

### High authority docs
These should strongly govern interpretation:
- `ADGOPS_000_DOC_ARCHITECTURE_v2.0`
- `ADGOPS_001_STATUS_QUO_v2.0`
- `ADGOPS_002_SUITE_MAP_v2.0`
- `ADGOPS_003_SURFACE_MAP_v2.0a`
- `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
- `ADGOPS_005_INTENDED_DIRECTION_v2.0`
- `ADGOPS_007_DATA_AND_FETCHING_v2.0`
- `ADGOPS_SURFACE_licitaciones_v2.0`
- `ADGOPS_SURFACE_estadisticas_v2.0`
- `ADGOPS_SURFACE_barometro_v2.0`

### Medium / medium-high authority docs
These should inform reading strongly, but are more local:
- `ADGOPS_006_FUTURE_MODULES_v2.0`
- `ADGOPS_SURFACE_alertas_v2.0`
- `ADGOPS_SURFACE_mapa_v2.0`
- `ADGOPS_SURFACE_recursos_v2.0`
- `ADGOPS_SURFACE_index_v2.0`
- `ADGOPS_SURFACE_about_v2.0`

Rule:
- higher authority docs define system reading
- lower authority docs should not silently contradict higher authority docs
- if contradiction appears, higher-layer docs win until the registry is explicitly updated

---

## 5. Reading paths

## 5.1 Fast re-entry path
Use this when returning to the project after a break:

1. `ADGOPS_001_STATUS_QUO_v2.0`
2. `ADGOPS_002_SUITE_MAP_v2.0`
3. `ADGOPS_003_SURFACE_MAP_v2.0a`
4. `ADGOPS_004_RUNTIME_TRUTH_v2.0a`

Purpose:
- recover current truth fast
- avoid stale assumptions
- avoid reading the suite as a patch lane only

## 5.2 Product understanding path
Use this when someone needs to understand ADG OPS as a product/system:

1. `ADGOPS_002_SUITE_MAP_v2.0`
2. `ADGOPS_003_SURFACE_MAP_v2.0a`
3. `ADGOPS_005_INTENDED_DIRECTION_v2.0`
4. selected `ADGOPS_SURFACE_*` docs

Purpose:
- understand the suite
- understand the surfaces
- understand where the product is heading

## 5.3 Coding support path
Use this before asking Claude to code or audit a technical plan:

1. `ADGOPS_001_STATUS_QUO_v2.0`
2. `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
3. relevant `ADGOPS_SURFACE_*` docs
4. `ADGOPS_005_INTENDED_DIRECTION_v2.0`
5. `ADGOPS_007_DATA_AND_FETCHING_v2.0` if data/tooling is involved

Purpose:
- keep coding anchored to current truth
- preserve future-readiness without speculative overbuilding
- reduce wrong assumptions

## 5.4 Data/fetching path
Use this when the lane touches ingestion, JSON, fetchers, documents, or future DB direction:

1. `ADGOPS_001_STATUS_QUO_v2.0`
2. `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
3. `ADGOPS_007_DATA_AND_FETCHING_v2.0`
4. `ADGOPS_006_FUTURE_MODULES_v2.0`
5. `ADGOPS_SURFACE_licitaciones_v2.0`

Purpose:
- separate current tooling truth from intended future architecture
- keep fetcher work grounded

## 5.5 Surface deep-read path
Use this when you want to understand one surface in detail:

1. `ADGOPS_003_SURFACE_MAP_v2.0a`
2. relevant `ADGOPS_SURFACE_*` doc
3. `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
4. `ADGOPS_005_INTENDED_DIRECTION_v2.0` if future direction matters

Purpose:
- understand local surface truth without losing suite context

---

## 6. Cross-reference doctrine

The wave-2 docs should behave like a graph.

Rule:
- docs may point to other docs when the detail belongs there
- this is good, not a weakness
- repetition should be reduced by routing the reader to the right layer

Examples:
- use `STATUS_QUO` for current state
- use `RUNTIME_TRUTH` for current behavior/maturity
- use `INTENDED_DIRECTION` for future bridge
- use `DATA_AND_FETCHING` for data-path questions
- use `SURFACE_*` docs for local surface reading

Purpose:
- prevent blob docs
- preserve readable specialization
- support both human and LLM use

---

## 7. Registry rule for future additions

When new docs are created, they should not enter the active system implicitly.

Rule:
- a new doc becomes part of active wave-2 only when:
  - its job is clear
  - its authority layer is clear
  - its family is clear
  - it is added to this registry

This keeps the documentation system:
- traceable
- navigable
- non-chaotic

---

## 8. Relationship to wave-1

Wave-1 docs still matter as:
- archive
- historical context
- recovery evidence
- earlier thinking support

But they should not be used as the live routing layer anymore.

Rule:
- wave-1 should be stored under `._old\`
- wave-2 registry is the active entry point

---

## 9. Current locked conclusions

- ADG OPS wave-2 now has a formal documentation system
- wave-2 is the live doc layer
- registry-based reading is now preferred over ad hoc reading order
- surface docs are active parts of the system, not side notes
- current truth and intended direction remain separate but connected
- coding support should start from wave-2 registry paths, not from stale memory

---

## 10. One-line doctrine

**Use this registry to read ADG OPS wave-2 in the right order, at the right layer, for the right job.**
