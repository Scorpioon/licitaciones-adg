# ADGOPS_004_RUNTIME_TRUTH_v2.0a

Status: ACTIVE DRAFT  
Authority: ADG OPS current runtime and maturity reading  
Parent docs: `ADGOPS_001_STATUS_QUO_v2.0`, `ADGOPS_003_SURFACE_MAP_v2.0a`  
Language: English  
Purpose: Describe the current runtime reality of ADG OPS, classify surface maturity, and make visible where behavior is stable, partial, fragile, broken, legacy, or synthetic.

---

## 0. What this document is

This is the runtime truth document for ADG OPS wave-2.

It exists to answer:
- what the suite appears to do today
- what currently behaves acceptably
- what remains fragile or broken
- what is placeholder or synthetic
- which areas are currently more mature
- which areas are active but still incomplete

This is not:
- the intended-direction doc
- the suite map
- the full code architecture doc
- the per-surface ficha set
- a patch history

One-line doctrine:

**Describe what ADG OPS actually does today, not what it is hoped to do later.**

---

## 1. Runtime classification vocabulary

This doc uses the following runtime classes:

- **stable**  
  usable and currently coherent for the present version

- **partial**  
  real and working in some meaningful sense, but incomplete

- **fragile**  
  works, but recent issues, structural sensitivity, or narrow fixes make it easy to misread as more stable than it is

- **broken**  
  currently known to behave incorrectly in a way that matters

- **legacy**  
  still present, but based on an older truth model or likely to be superseded

Important:
- these are operational runtime labels
- not emotional judgments
- not product worth rankings

---

## 2. Current overall runtime reading

The suite is real and already functionally meaningful.

At the same time:
- runtime maturity is uneven
- some areas improved significantly during recent work
- some areas remain unresolved
- some tooling is active but incomplete
- some behavior may still be synthetic, placeholder, or partially implemented

The correct current reading is:
- **usable in parts**
- **promising overall**
- **not yet uniformly mature**

---

## 3. Core runtime reading by major surface

## 3.1 Licitaciones
Current class:
- **fragile**

Blocker note:
- licitaciones remains the main currently visible blocker area

Why:
- the recent shell/footer parity lane was not fully resolved by the narrow CSS-only fix
- the issue now requires broader re-audit from real files

What this means:
- licitaciones is still central
- but it is not currently the most trustworthy surface in runtime terms

Documentation consequence:
- future surface doc must distinguish clearly between:
  - conceptual centrality
  - current runtime maturity
- blocker status must stay visible without flattening the entire surface into “down”

## 3.2 Estadisticas
Current class:
- **partial to stable**

Why:
- recent work improved the estadisticas shell and surrounding behavior
- for the current version, this lane reads as more acceptable than licitaciones

Caution:
- this should not be read as “finished”
- it should be read as “currently more stable than the licitaciones lane”

Documentation consequence:
- describe as currently acceptable but not final
- note likely presence of partial or evolving behavior

## 3.3 Barometro
Current class:
- **partial to stable**

Why:
- barometro benefited from recent work alongside the analytics lane
- current reading suggests it is currently acceptable for this stage

Caution:
- this should not be read as “finished”
- it should be read as “currently more stable than the licitaciones lane”
- barometro’s identity and logic are distinct enough that future fragility or intended evolution may diverge from generic statistics work

Documentation consequence:
- treat it as a distinct runtime truth surface, not a decorative analytics mode

---

## 4. Supporting runtime reading by surface

## 4.1 Mapa
Current class:
- **partial / uncertain**

Reason:
- it exists in the suite structure, but current maturity is not yet fully established in the present documentation wave

Rule:
- do not overclaim implementation depth until the surface-specific doc is written
- document it in a way that leaves room for future increase in relevance

## 4.2 Recursos
Current class:
- **partial / uncertain**

Reason:
- present as part of the system reading
- exact runtime depth still needs tighter audit

Rule:
- document it carefully now without understating its possible future importance

## 4.3 Alertas
Current class:
- **partial / strategically active**

Reason:
- alerting is already part of the suite’s conceptual and future-functional direction
- current runtime truth likely exists, but not yet at the final intended service depth

Rule:
- document current truth modestly
- but leave clear room for this area to become more central later

## 4.4 Index
Current class:
- **partial / light**

Reason:
- entry/framing surface
- likely lighter operational complexity than the core surfaces
- still expected to need future polish

## 4.5 About
Current class:
- **partial / light**

Reason:
- explanatory/framing surface
- likely lighter runtime density than the core operational areas
- some content or positioning may still change later

---

## 5. Runtime truth about tooling and data intake

## 5.1 Fetcher
Current class:
- **partial / active / fragile**

Type:
- tooling/runtime component
- not a user-facing surface

What is true:
- the current fetcher is active working truth
- it is not merely hypothetical
- it already matters to the product runtime ecosystem

What is not yet true:
- it is not finished
- it is not the final data architecture
- it is not the only future fetcher
- it still has logic problems that require deeper work

Current known direction:
- the issue is not only local fetcher correction
- the data/fetching layer is expected to broaden, including deeper PDF-document ingestion needs

Documentation consequence:
- fetcher belongs in runtime truth
- but deep system-level treatment should wait for `DATA_AND_FETCHING`

---

## 6. Placeholder / synthetic / partial behavior rule

ADG OPS must currently be read with the assumption that some areas may still contain:

- placeholder behavior
- synthetic values
- partial state logic
- incomplete runtime wiring
- surfaces that are visually meaningful before they are fully final

Rule:
- this is not failure by itself
- but it must be documented honestly
- runtime docs must prevent people from confusing visible UI with full implementation truth

This rule is especially important for:
- analytics surfaces
- support surfaces
- future-service-oriented surfaces
- evolving data pathways

---

## 7. Runtime truth about version and lane asymmetry

Current repo truth suggests lane asymmetry:

- stats/barometro advanced further in recent work
- licitaciones remains more problematic
- not all files or surfaces reflect the same degree of progress

Meaning:
- the suite should not be described as if all parts matured together
- mixed progress is current truth
- documentation must expose that rather than smoothing it over

---

## 8. Known runtime dangers

### 8.1 False-stability danger
A surface can look better visually than its deeper runtime truth justifies.

### 8.2 Placeholder confusion danger
Users or future coders may mistake a visible surface for a fully mature one if synthetic/partial behavior is not documented.

### 8.3 Core-surface contradiction danger
`licitaciones` is conceptually central, but currently runtime-fragile.  
That contradiction must stay visible.

### 8.4 Tooling-understatement danger
The fetcher is active enough to matter, but immature enough that under-documenting it would create false certainty.

---

## 9. Current locked runtime conclusions

- the suite is functionally meaningful already
- runtime maturity is uneven
- stats/barometro is currently more acceptable than licitaciones
- licitaciones remains the main visible blocker area
- fetcher is an active tooling/runtime component, not future fiction
- placeholder/synthetic/partial behavior must be treated as real documentation content
- runtime docs must distinguish conceptual centrality from current stability

---

## 10. What this document does not settle yet

This doc does not yet settle:
- exact file ownership per surface
- exact maturity of every support surface
- exact runtime completeness of every page
- precise current behavior of every interaction path

Those belong more strongly to:
- per-surface docs
- future technical audits
- current coding/audit lanes when they focus on a specific area

---

## 11. Immediate next documentation consequence

Because runtime truth is uneven, the first deeper surface docs should prioritize:

1. `licitaciones`
2. `barometro`
3. `estadisticas`

Reason:
- they carry the strongest current product meaning
- they also carry the highest current risk of misunderstanding

---

## 12. One-line doctrine

**Document the ADG OPS runtime as it is now: real, meaningful, uneven, and still maturing.**
