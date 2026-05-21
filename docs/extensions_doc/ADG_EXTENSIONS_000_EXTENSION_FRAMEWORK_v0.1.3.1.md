# ADG EXTENSIONS — FICHA 0 CLOSED — EXTENSION FRAMEWORK

Version: v0.1.3.1  
Supersedes: `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.md`  
Status: CLOSED / CONSISTENCY-CORRECTED  
Mode: CONSISTENCY REVIEW  
Project layer: ADGOPS_EXTENSIONS  

---

## 0. What this document is

This document defines the shared framework for the ADG Extensions lane.

It defines:
- what an ADG Extension is
- how phase and state remain separate
- how unfinished extensions are represented
- how data contracts govern future work
- how the extension layer relates to ADG OPS, ADG, and possible future LAUS platform replacement

---

## 1. Family name

The family name is:

**ADG Extensions**

Reason:
- it should not be limited to "ADG OPS Extensions"
- it leaves room for a broader ADG platform layer
- it allows the extensions to outgrow the current ADG OPS surface reading if needed

---

## 2. Definition

An ADG Extension is a functional module that may later become:
- a page
- a data surface
- a service
- an integration
- a platform capability

An extension is not automatically a current feature.

Each extension must be classified before design or implementation.

---

## 3. Phase vs state

Phase and state are separate.

### Phase

Phase means:
- roadmap sequence
- intended order
- planning position

### State

State means:
- current implementation reality
- what exists now
- what does not exist now
- what is waiting for data
- what is stubbed, partial, or active

Hard rule:

**Do not use phase as proof of implementation.**

---

## 4. Allowed states

Allowed state vocabulary:

- No existe nada
- Esperando datos
- Legacy / partial exists
- Stub
- MVP externo
- Parcial
- Activo

Delta from v0.1.0:
- added `Legacy / partial exists` because Directorio currently exists as a basic long list but not as the intended module.

---

## 5. Visibility rule

Extensions should be accessible from a central hub.

The hub acts as:
- a central exit/access point to all modules
- a readable overview of the ADG platform direction
- a way to show active and future modules without overclaiming maturity

Licitaciones remains a major/core module.

Unfinished extensions are not activated.

If an extension does not exist yet, it may appear only as:
- a grey disabled stub in the home/hub
- a non-active placeholder
- an internal planning item

It must not look like a working feature.

---

## 6. Internal vs public truth

### No existe nada

If an extension state is `No existe nada`:
- no live page should be implied
- no real workflow should be implied
- no form should be implied
- no delivery logic should be implied
- no backend or integration should be implied

### Esperando datos

`Esperando datos` is internal operator truth.

It does not automatically need to be shown to the public user.

Public-facing treatment may be:
- hidden until ready
- disabled stub
- controlled demo only if explicitly marked as mock/demo

---

## 7. Data discipline

Every extension requires a data contract before detailed UI or implementation.

Hard rule:

**No data contract, no real product claim.**

Minimum data discipline:
- required fields
- optional fields
- source of truth
- update method
- ownership
- privacy constraints
- public/private visibility
- what can be displayed without misleading users

---

## 8. Platform direction

ADG Extensions may become part of a broader ADG platform layer.

If the system evolves successfully, this web may eventually replace the current LAUS platform.

Current reading:
- intended direction
- not current implementation truth

Rule:
- do not present future platform replacement as active truth.

---

## 9. Current extension list — Batch 1.3.1

### Laus Tracker

Phase:
- Fase 1

Current state:
- Esperando datos

Type:
- module / intelligence layer

Initial role:
- historical LAUS archive
- medallero
- annual evolution
- category analysis
- school ranking

Hard doctrine:
- editorial / historical / expository
- not competitive

### Directorio de Socios

Phase:
- Fase 2

Current state:
- Legacy / partial exists

Type:
- ecosystem capability / directory module / future profile-community layer

Initial role:
- professional ADG community directory
- studios, freelancers, agencies, schools
- filtering by specialty and location
- future claimable profiles

Correction:
- a basic legacy directory exists as a long list/page
- the intended future module does not yet exist in complete form

### Oportunidades ADG

Phase:
- parent module for opportunity lanes (no phase number assigned)

Current state:
- No existe nada as implemented product module

Type:
- service / opportunity layer / ecosystem utility

Child lanes:
- Bolsa de Prácticas / Juniors / Talents — Fase 5
- Bolsa de Freelancers — future child lane
- Bolsa Profesional — future child lane

Note on phase gaps:
- Phases 3, 4, and 6 are not assigned to any current extension in this batch.
- These phases are reserved for future modules not yet defined.
- Phase numbers in this batch are intentionally non-contiguous.

### Bolsa de Prácticas / Juniors / Talents

Phase:
- Fase 5

Current state:
- No existe nada

Type:
- service / opportunity lane

Initial role:
- curated ADG-reviewed entry-to-sector opportunities

### Bolsa de Freelancers

Current state:
- not implemented as standalone lane

Type:
- curated freelance opportunity lane

Status:
- scoped for delta
- needs future deep ficha before implementation

### Bolsa Profesional

Canonical name:
- **Bolsa Profesional**

Note:
- "Bolsa de Puestos Profesionales" is a deprecated alternate name.
- All future references must use "Bolsa Profesional" only.

Current state:
- not implemented as standalone lane

Type:
- curated professional opportunity lane

Status:
- scoped for delta
- needs future deep ficha before implementation

### Alertas por Email

Phase:
- Fase 7

Current state:
- No existe nada as ADG Extension

Type:
- service / delivery layer

Initial role:
- future no-spam digest service
- first licitaciones alerts
- later opportunities/profile/ecosystem alerts

Important distinction:
- existing ADG OPS `alertas` surface may exist as a stub/development surface
- Email Alerts as an ADG Extension remains not implemented
- Batch 1.3 replaces the prior pending doc with the closed Alertas ficha

## 10. Audit sequence — Batch 1.3.1

Completed:
1. Extension Framework
2. Laus Tracker
3. Directorio de Socios
4. Oportunidades ADG Framework
5. Bolsa de Prácticas / Juniors / Talents
6. Scoped preservation for Freelancers + Profesional
7. Alertas por Email
8. Cross-system consistency pass (Batch 1.3)
9. Correction pass (Batch 1.3.1)

Pending:
10. Hub / IA audit
11. Data contracts batch
12. Governance / moderation / permissions pass
13. Master Claude PLAN_MIN prompt
14. Implementation only after audit closure

---

## 11. Working protocol for each ficha

Each extension should follow:
1. Open ficha
2. Ask strategic questions
3. User answers
4. Assistant performs handshake
5. Assistant detects contradictions / missing logic
6. Close ficha
7. Produce downloadable markdown document
8. Continue to next ficha

Hard rule:
**Every closed ficha must produce a downloadable `.md` document for later delta.**

---

## 12. Delta log

### v0.1.3 → v0.1.3.1

- Bolsa Profesional: locked canonical name, deprecated "Bolsa de Puestos Profesionales"
- Added explicit note on phase gaps (Phases 3, 4, 6 reserved/unassigned)
- Oportunidades ADG phase field clarified as parent with no assigned number
- Batch reference updated to 1.3.1

### v0.1.0 → v0.1.2

- Added `Legacy / partial exists` state for Directorio
- Corrected Directorio current state from `Esperando datos`
- Restructured opportunity hierarchy: Oportunidades ADG as parent, child lanes separate

---

## 13. One-line doctrine

**ADG Extensions is the future module layer of the ADG platform direction: every extension must be phase-marked, state-marked, data-disciplined, and prevented from looking real before it is real.**
