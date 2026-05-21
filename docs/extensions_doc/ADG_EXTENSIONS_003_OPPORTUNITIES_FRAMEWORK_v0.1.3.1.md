# ADG EXTENSIONS — FICHA 3 CLOSED — OPORTUNIDADES ADG FRAMEWORK

Version: v0.1.3.1  
Supersedes: `ADG_EXTENSIONS_003_OPPORTUNITIES_FRAMEWORK_v0.1.3.md`  
Status: CLOSED / DELTA-CONSISTENT  
Mode: CONSISTENCY REVIEW  
Parent module: Oportunidades ADG  

---

Batch 1.3.1 note:
- Carried forward as part of correction pass.
- Fix applied: child lane cross-references updated from v0.1.2 to v0.1.3.1.

## 0. Purpose

This document defines the parent framework for the ADG opportunity system.

It defines:
- parent opportunity system
- sub-home model
- shared moderation rules
- intake/publication principles
- relationship between internship/junior, freelance, and professional lanes

---

## 1. Parent module identity

Visible name:
- Oportunidades ADG

Internal/doc name:
- ADG Opportunities

Family:
- ADG Extensions

Type:
- service
- opportunity layer
- ecosystem utility module

Current state:
- No existe nada as implemented product module

Important:
- this is not a single job board
- it is a parent opportunity surface that can host multiple curated opportunity boards

---

## 2. Parent role

Oportunidades ADG should become a central opportunity hub for the ADG ecosystem.

It may include:
- Bolsa de Prácticas / Juniors / Talents
- Bolsa de Freelancers
- Bolsa Profesional

Doctrine:
**Oportunidades ADG is a curated opportunity hub, not a generic job board.**

---

## 3. Sub-home model

The sub-home should include:
- intro/editorial framing
- global search or discovery entry
- cards for each sub-board
- status visibility for available / locked / in-preparation lanes
- clear access to each opportunity lane

It should have its own weight as a proper section.

It is not:
- loose links
- hidden form page
- single isolated internship page

---

## 4. Inactive lanes

Inactive sub-boards may appear as:
- grey disabled stubs
- "en preparación" cards
- non-clickable or locked cards until ready

Rule:
- unfinished opportunity boards must not look active
- no board should imply publication or application flow before it exists

---

## 5. Shared moderation doctrine

Core rule:
**ADG reviews and approves before publication.**

Reason:
- prevent spam
- prevent predatory internships
- preserve community trust
- avoid low-quality opportunity posting
- avoid generic job-board behavior

Submission does not equal publication.

---

## 6. Intake model by lane

### Prácticas / Juniors / Talents

- organizations contact ADG directly by email
- process requires seriousness and effort
- not a casual open form first
- ADG evaluates internally before publishing

Reason:
- protect students, talents, and juniors
- avoid exploitative internships
- avoid school scalping dynamics

### Freelancers

- entities looking for freelance help may access a "publicar oferta" style form
- form is submitted to ADG
- ADG reviews and approves before publication

### Professional positions

- entities may access a "publicar oferta" style form
- form is submitted to ADG
- ADG reviews and approves before publication
- senior board / presidency may later refine criteria

---

## 7. Technical readiness principle

No specific MVP intake tool is locked yet.

Not locked:
- Google Forms
- email-only flow
- Airtable
- Sheet
- database
- custom form

Must be ready for:
- databases
- intakes
- spreadsheets
- Excel/Sheets workflows
- future forms
- manual review
- publication state changes

Hard rule:
**Do not choose the intake technology before the process/data contract is clear.**

---

## 8. Relationship to Directorio de Socios

Future relationship:
- offer links to studio/agency/member profile
- profile can show active opportunities
- directory can act as trust/context layer
- publication can reference verified or reviewable entities

Only if matching is reliable.

---

## 9. Child lane state

### Bolsa de Prácticas / Juniors / Talents

Status:
- closed in `ADG_EXTENSIONS_003A_BOLSA_PRACTICAS_v0.1.3.1`

### Bolsa de Freelancers

Status:
- scoped in `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1`
- needs deeper ficha before implementation

### Bolsa Profesional

Status:
- scoped in `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1`
- needs deeper ficha before implementation

---

## 10. Shared risks

- turning ADG into generic job board
- spam channel
- exploitative internships
- school/talent scalping
- publication without ADG review
- confusing form submission with automatic publication
- building UI before intake/data/process contract
- mixing students/freelancers/professionals without separation

---

## 11. Delta log

### v0.1.3 → v0.1.3.1

- Section 9: child lane cross-references corrected from `v0.1.2` to `v0.1.3.1`.
- Bolsa Profesional name aligned to canonical "Bolsa Profesional" (removed "Puestos Profesionales" variant).

### v0.1.0 → v0.1.2

- Clarified child lane states.
- Freelancers and Profesional are scoped, not deep-closed.
- Parent module remains closed.
- No intake tech is locked.
- Framework cross-references 003A and 003B/003C added.

---

## 12. One-line doctrine

**Oportunidades ADG is a curated, ADG-reviewed opportunity hub with multiple sub-boards, designed to serve the community without becoming a spammy job board, exploitative internship channel, or generic marketplace.**
