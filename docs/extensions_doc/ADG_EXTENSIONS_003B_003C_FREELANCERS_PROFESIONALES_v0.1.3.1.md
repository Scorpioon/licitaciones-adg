# ADG EXTENSIONS — FICHA 3B/3C SCOPED — BOLSA FREELANCERS + BOLSA PROFESIONAL

Version: v0.1.3.1  
Supersedes: `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.md`  
Status: SCOPED / PARTIAL CLOSED FOR DELTA  
Mode: CONSISTENCY REVIEW  
Parent module: Oportunidades ADG  

---

Batch 1.3.1 note:
- Carried forward as part of correction pass.
- Fix applied: Bolsa Profesional canonical name locked. "Bolsa de Puestos Profesionales" deprecated.

## 0. Purpose

This document preserves scoped decisions for the Freelancers and Professional opportunity lanes.

These lanes have not received the same full deep-ficha treatment as Bolsa de Prácticas / Juniors / Talents.

This document is:
- continuity document
- future deep-ficha base
- guardrail against drift

It is not:
- final implementation spec
- full standalone ficha closure
- complete data contract
- publication-ready policy

---

## 1. Shared opportunity model

Covered lanes:
1. Bolsa de Freelancers
2. Bolsa Profesional

Shared doctrine:
- ADG reviews before publication
- submission does not equal publication
- avoid spam
- avoid exploitative or vague offers
- avoid generic job-board behavior
- avoid cheap marketplace dynamics

Both may appear in Oportunidades ADG sub-home as grey "en preparación" stubs until active.

---

# PART A — BOLSA DE FREELANCERS

## 2. Identity

Visible name:
- Bolsa de Freelancers

State:
- not implemented as standalone product lane

Type:
- curated freelance opportunity lane
- ecosystem/community service

---

## 3. Role

Role:
- mixed curated lane
- connects freelance needs, freelance availability, and ADG-reviewed opportunities
- serves community without becoming cheap marketplace

Possible future flows:
- studios/agencies/entities publish freelance needs
- freelancers may later indicate availability
- ADG moderates before publication

---

## 4. Publication model

Publication model:
- both sides may eventually participate
- freelance opportunities can be submitted through "publicar oferta" style form
- form is sent to ADG
- ADG reviews and approves before publication

Important:
- form submission is intake only
- publication is not automatic

---

## 5. Risks

- cheap marketplace
- spam
- low-quality briefs
- exploitative or vague offers
- conflict with Directorio
- confusing profile discovery with opportunity publication
- turning ADG into generic freelance board

Guardrail:
**Bolsa de Freelancers must be curated, community-aware, and ADG-reviewed.**

---

## 6. Future data fields

Candidates:
- opportunity title
- submitting entity
- project type
- discipline/specialty
- expected scope
- timeline
- budget/range if allowed/required
- location or remote modality
- contact/application method
- deadline
- ADG review state
- related directory profile if reliable

---

# PART B — BOLSA PROFESIONAL

## 7. Identity

Canonical visible name:
- **Bolsa Profesional**

Note:
- "Bolsa de Puestos Profesionales" is a deprecated alternate name.
- All future references must use "Bolsa Profesional" only.

State:
- not implemented as standalone product lane

Type:
- curated professional opportunity lane
- selected employment/service layer

---

## 8. Role

Role:
- selected professional opportunities
- not generic job board
- curated and quality-gated

Note:
- senior board / presidency may later refine criteria
- criteria remain adjustable until governance review

---

## 9. Difference from internships/junior

Professional lane differs through:
- clearer remuneration
- clearer contract/duration
- more defined responsibilities
- stronger role requirements
- lower volume, higher quality
- stronger publication criteria

---

## 10. Minimum criteria

Minimum:
- clear remuneration
- clear contract or duration
- identified company/entity
- ADG review
- full publication criteria

Publication:
- controlled intake
- ADG review
- approval before listing

---

## 11. Publication model

Working model:
- company/studio/entity uses "publicar oferta" form
- form goes to ADG
- ADG reviews and approves
- only approved opportunities are published

Submission is not publication.

---

## 12. Future data fields

Candidates:
- title
- company/studio/entity
- profile type
- role level
- discipline/specialty
- location
- modality
- contract type
- duration
- remuneration
- role description
- requirements
- application/contact method
- deadline
- ADG review state
- related directory profile if reliable

---

## 13. Relationship to Directorio de Socios

Possible:
- opportunity links to member profile
- profile shows active opportunities
- directory validates identity/context
- claimed profiles may later manage/request publication flows

Hard condition:
- only if entity matching is reliable

---

## 14. Relationship to Oportunidades sub-home

Both lanes live under Oportunidades ADG.

Sub-home should:
- show lane cards
- indicate active / preparation state
- distinguish Prácticas/Juniors, Freelancers, Profesionales
- avoid one undifferentiated feed too early

---

## 15. Delta log

### v0.1.3 → v0.1.3.1

- Bolsa Profesional canonical name locked as "Bolsa Profesional".
- "Bolsa de Puestos Profesionales" marked as deprecated alternate name.
- Consistent name used throughout this document.

### v0.1.0 → v0.1.2

- Clarified that these lanes are scoped, not fully deep-closed.
- Positioned as future deeper fichas before implementation.
- Aligned status with parent framework.

---

## 16. One-line doctrine

**Bolsa de Freelancers and Bolsa Profesional are curated, ADG-reviewed opportunity lanes under Oportunidades ADG: they may later use controlled publication forms, but must never become automatic job-board spam, cheap marketplace dynamics, or unverified public listings.**
