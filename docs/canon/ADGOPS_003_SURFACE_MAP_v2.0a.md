# ADGOPS_003_SURFACE_MAP_v2.0a

Status: ACTIVE DRAFT  
Authority: ADG OPS surface inventory and relationship map  
Parent docs: `ADGOPS_000_DOC_ARCHITECTURE_v2.0`, `ADGOPS_001_STATUS_QUO_v2.0`, `ADGOPS_002_SUITE_MAP_v2.0`  
Language: English  
Purpose: Map the current visible surfaces of ADG OPS, explain where each one lives, and clarify how pages and surfaces relate without flattening the suite into one blob.

---

## 0. What this document is

This is the surface map for ADG OPS wave-2.

It exists to answer:
- what visible surfaces currently exist
- where those surfaces live
- how they relate to pages
- which surfaces are core, supporting, or framing
- which surfaces share UI space but still deserve separate identity
- where future documentation should split surface truth from page truth

This is not:
- the runtime-truth doc
- the intended-direction doc
- the per-surface ficha set
- a code architecture spec
- a sitemap for public navigation only

One-line doctrine:

**Map ADG OPS by visible working surfaces first, then clarify where pages and shared UI containers host them.**

---

## 1. Reading rule

ADG OPS should be read as:

- page-first at the top level
- surface-aware inside those pages
- modular where behavior meaningfully diverges
- expandable where future additions are likely

This means:
- not every page equals one surface
- not every surface deserves its own top-level page
- a shared page may host distinct surfaces with different logic, outputs, and future direction

Locked example:
- `estadisticas` and `barometro` may share UI territory
- but they are not the same surface truth
- therefore both must exist explicitly in the surface map

---

## 2. Current top-level page structure

Current top-level pages/surfaces visible in the suite reading:

- `index`
- `licitaciones`
- `estadisticas`
- `barometro`
- `mapa`
- `recursos`
- `alertas`
- `about`

Important:
- this is a documentation map, not a claim that all these areas have equal implementation maturity
- some are heavier operational surfaces
- some are lighter framing or support surfaces

---

## 3. Core surface cluster

## 3.1 Licitaciones
Type:
- core operational surface
- core technical/conceptual center

Why it matters:
- much of the suite meaning flows from licitaciones
- it is one of the main places where data intake, records, filtering, reading, and future service layers converge

Current documentation consequence:
- deep surface doc required
- runtime truth must track it carefully
- future data/fetching/system docs will likely reference it heavily

## 3.2 Estadisticas
Type:
- configurable analytics surface

Core function:
- allow the user to read, filter, and inspect statistical views of the sector by different dimensions and controls

Reading note:
- estadisticas is not the same as barometro
- it is the broader configurable analytics environment

Current documentation consequence:
- full surface doc required
- relationship to barometro must always be stated explicitly

## 3.3 Barometro
Type:
- sibling analytics / interpretive surface

Core function:
- analyze the sector by period
- extract and articulate automatic reading of the chosen time slice
- describe public procurement behavior across the selected period

Reading note:
- barometro shares UI space with estadisticas, but functionally deserves its own explanation layer
- it should not be buried as a small subsection

Current documentation consequence:
- deep surface doc required
- relationship to estadisticas must be documented carefully
- intended evolution should be tracked separately from generic statistics views

---

## 4. Supporting surface cluster

## 4.1 Mapa
Type:
- supporting intelligence / spatial-reading surface

Working reading:
- a geographic or spatial lens into the ecosystem
- likely important for navigation, context, or territorial interpretation
- expected to become more relevant as the suite matures

Documentation consequence:
- full surface doc required
- depth may remain moderate at first, but the documentation should leave room for future expansion

## 4.2 Recursos
Type:
- support / resource surface

Working reading:
- surface for resource access, support material, or ecosystem utility content
- not yet one of the heaviest current surfaces
- likely to gain weight as the suite grows

Documentation consequence:
- full surface doc required
- should be documented in a way that allows later expansion without having to rewrite the system map

## 4.3 Alertas
Type:
- support / monitoring / future-service bridge surface

Working reading:
- current alert-oriented surface
- strategically important because future alerting and mail-based functions are likely part of the suite’s growth path
- expected to evolve toward a more core ecosystem role later

Documentation consequence:
- full surface doc required
- should connect clearly to future ecosystem capabilities
- should already be documented with future-weight in mind

---

## 5. Entry and framing surface cluster

## 5.1 Index
Type:
- entry surface
- suite gateway

Working reading:
- first-touch or navigation-framing surface
- currently lighter than the operational core
- still expected to need further polish

Documentation consequence:
- light surface doc at first
- can expand later if entry behavior becomes richer

## 5.2 About
Type:
- framing / explanatory surface

Working reading:
- context, explanation, positioning, or system framing
- currently lighter than the operational core
- some current content may still need future refinement or repositioning

Documentation consequence:
- light surface doc at first
- should still be documented as part of the suite, not ignored as “just static”

---

## 6. Surface relationships

## 6.1 Core dependency reading
The strongest current conceptual dependency chain appears to be:

- `licitaciones` as technical/conceptual base
- `estadisticas` as configurable analytical reading
- `barometro` as period-based interpretive reading

This does not mean:
- one surface fully owns the others
- or one must always technically depend on another

It means:
- documentation and product reading should treat these three as the current most important interpretive cluster

## 6.2 Support relationship reading
Supporting surfaces likely extend or frame the core cluster by:
- adding context
- adding navigation
- adding territorial reading
- adding resources
- adding alerts or monitoring pathways

## 6.3 Entry relationship reading
`index` and `about` do not carry the same operational weight as the core cluster, but they still matter because they shape:
- first contact
- orientation
- public reading of the suite
- overall product legibility

---

## 7. Hosting logic

This section exists to prevent confusion between page structure and surface structure.

### 7.1 Shared analytics area
The analytics area hosts:
- `estadisticas` as the configurable analytics surface
- `barometro` as the interpretive period-analysis surface

Meaning:
- shared UI territory does not erase functional distinction
- both should be documented separately even when hosted in the same broader area

### 7.2 Surface vs page distinction
Some surfaces align closely with a page.
Others may:
- share a page
- share navigation space
- share shell logic
- still deserve separate documentation because their behavior and purpose differ

This rule is especially important for:
- `estadisticas`
- `barometro`

---

## 8. Surface depth priority

Recommended documentation depth priority:

### Deep docs first
- `licitaciones`
- `barometro`

### Full but medium-depth docs
- `estadisticas`
- `mapa`
- `recursos`
- `alertas`

### Light-first docs
- `index`
- `about`

This is a documentation priority rule, not a value judgment on product worth.

---

## 9. Surface-level classification fields to use later

When per-surface docs are created, each should eventually declare:

- surface type
- host page or host area
- current maturity
- current visible behavior
- key files
- dependencies
- relationships to other surfaces
- intended evolution
- known fragility

This document only maps the system.
It does not replace those fichas.

---

## 10. Surface map vs suite map

Simple split:

- `SUITE_MAP` = what ADG OPS is as a suite
- `SURFACE_MAP` = where the visible working surfaces live and how they relate

Rule:
- suite map defines the big picture
- surface map defines the visible product topology

---

## 11. Open edges to keep visible

The following are intentionally not overclaimed here:

- exact maturity of every surface
- exact current runtime completeness of each page
- exact code ownership per surface
- exact future additions inside each surface
- whether every named surface is currently equally implemented

Those belong more strongly to:
- `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
- future surface docs
- intended/future docs

---

## 12. Locked conclusions

- ADG OPS should be mapped page-first with surface substructure where needed
- `barometro` remains a distinct surface
- `licitaciones` is a core surface and conceptual center
- `index` and `about` begin as lighter docs but still belong in the formal map
- support surfaces are part of the suite, not leftovers
- support surfaces should be documented in a way that anticipates future expansion
- future additions do not erase the need for a clean current surface map

---

## 13. One-line doctrine

**Map the current ADG OPS visible system in layers: pages at the top, distinct surfaces where behavior meaningfully diverges.**
