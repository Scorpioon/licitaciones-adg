# ADGOPS_SURFACE_licitaciones_v2.0a

Status: ACTIVE DRAFT  
Authority: ADG OPS surface doc  
Parent docs: `ADGOPS_003_SURFACE_MAP_v2.0a`, `ADGOPS_004_RUNTIME_TRUTH_v2.0a`, `ADGOPS_005_INTENDED_DIRECTION_v2.0`, `ADGOPS_007_DATA_AND_FETCHING_v2.0`  
Language: English  
Purpose: Explain the licitaciones surface as it exists today, why it is central to ADG OPS, what the user sees, how it behaves, what files matter most, and where it remains fragile.

---

## 0. What this surface is

`licitaciones` is the core technical and conceptual surface of ADG OPS.

It is currently the strongest anchor for:
- procurement records
- browsing and filtering
- list/detail reading
- current data preview
- future data enrichment
- future alerts and downstream intelligence
- the broader meaning of the suite

This is one of the deepest product surfaces and should not be treated as a simple content page.

---

## 1. Why it exists

The surface exists to let the user work with the public procurement domain directly.

Its role is to:
- expose the live record space
- let the user search and filter it
- inspect individual entries
- turn raw procurement flow into a usable working surface
- act as a base for later analytics, alerts, and ecosystem capabilities

This is why the surface is both:
- a runtime/UI surface
- a structural center of the suite

---

## 2. What the user sees

The current reading of the surface suggests a shell with these main regions:

- top shell / chrome area
- filter and control area
- main list/table area
- detail panel area
- footer / lower shell area

Typical visible expectations include:
- filtering
- list or row-based reading
- detail inspection
- pagination / bottom list controls
- shell/footer coexistence inside the viewport

The exact layout is still under active refinement.

---

## 3. What the user can do

The dominant current user flow should be read as:

- search / filter
- list reading
- detail inspection
- pagination / continued browsing

This makes `licitaciones` the main operational browsing surface of the suite.

---

## 4. Current behavior

Current runtime reading:
- the surface is real and central
- it is also currently fragile

Known reading:
- shell/footer parity is not fully resolved yet
- a narrow CSS-only fix was not sufficient
- a broader re-audit is required from real files

Important distinction:
- the surface is not conceptually broken
- the surface is currently operationally fragile

That distinction must stay visible in future coding and documentation work.

---

## 5. Current maturity

Runtime class:
- **fragile**

Reason:
- the surface still carries the main currently visible blocker lane
- layout/shell behavior is not fully settled
- it remains the area most likely to mislead others if documented too optimistically

What this does **not** mean:
- that the surface lacks value
- that it should be deprioritized conceptually
- that the broader suite can be understood without it

---

## 6. Key files

Primary surface files:
- `licitaciones.html`
- `licitaciones.js`
- `style.css`

Likely shared/supporting files:
- `app.js`
- `shared.js`

Related tooling:
- current licitaciones fetcher / data intake tooling
- future data/fetching architecture docs

This file list may expand later as deeper architecture docs are written.

---

## 7. Dependencies and relationships

### Conceptual relationships
`licitaciones` feeds the wider suite reading:
- analytics
- interpretation
- alerts
- future directory / service layers
- future structured data work

### Surface relationships
Strongest relationships:
- `estadisticas`
- `barometro`

These surfaces do not replace licitaciones.
They build interpretive value on top of the broader procurement domain it anchors.

### Tooling and data relationships
This relationship is **dominant**.

`licitaciones` depends critically on:
- current fetcher/data intake
- preview correctness
- materialized dataset correctness
- future ingestion expansion
- future structured storage / queryability

The fetcher should be read here as a kernel-core trust indicator for the whole surface.

Reason:
- if preview or data materialization is wrong, the system can unintentionally mislead the user
- that means data-path correctness is not just a backend concern
- it is a truth concern for the product itself

This is why the data/fetching relationship is not a side note in `licitaciones`.
It is one of the strongest structural dependencies of the surface.

---

## 8. Current issues / fragility

Known fragility includes:
- unresolved shell/footer parity
- sensitivity to layout chain decisions
- dependence on a still-maturing data/tooling path
- risk of being read as “solved enough” when it still needs careful re-audit

Current severity reading:
- shell/layout blocker
- plus signal of broader architecture tension

This is one of the surfaces where current truth must stay more important than optimistic narrative.

---

## 9. Intended evolution

`licitaciones` is likely to evolve toward:
- stronger shell stability
- better data flow reliability
- richer list/detail reading
- improved integration with future data architecture
- stronger relationship to alerts, analytics, and future service layers

The intended direction is not to replace this surface.
It is to stabilize and strengthen it as a core suite foundation.

---

## 10. Relationship to other docs

See:
- `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
- `ADGOPS_005_INTENDED_DIRECTION_v2.0`
- `ADGOPS_007_DATA_AND_FETCHING_v2.0`

---

## 11. One-line doctrine

**`licitaciones` is the core operational and conceptual surface of ADG OPS, and its data path is a product-truth dependency, not just a technical detail.**
