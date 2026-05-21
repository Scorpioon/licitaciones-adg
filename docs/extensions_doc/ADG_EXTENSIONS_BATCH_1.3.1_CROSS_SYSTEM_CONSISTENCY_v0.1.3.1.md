# ADG EXTENSIONS — BATCH 1.3.1 CROSS-SYSTEM CONSISTENCY

Version: v0.1.3.1  
Batch: 1.3.1  
Supersedes: `ADG_EXTENSIONS_BATCH_1.3_CROSS_SYSTEM_CONSISTENCY_v0.1.3.md`  
Status: CLOSED CONSISTENCY PASS  
Mode: CROSS-SYSTEM REVIEW  
Language: English documentation / Spanish working source  

---

## 0. What this document is

This document audits the ADG Extensions fichas as a system.

Batch 1.3.1 is a correction pass on top of Batch 1.3.

It checks and resolves:
- stale cross-references
- naming inconsistencies
- phase documentation gaps
- delta section completeness
- all items flagged in the post-Batch 1.3 audit

This is not:
- implementation permission
- a code prompt
- a final roadmap
- a data model

---

## 1. Inputs reviewed

Batch 1.3 base (all v0.1.3 docs):
- Extension Framework
- Laus Tracker
- Directorio de Socios
- Oportunidades ADG Framework
- Bolsa de Prácticas / Juniors / Talents
- Bolsa Freelancers + Bolsa Profesional scoped doc
- Alertas por Email closed ficha
- Batch 1.3 Cross-System Consistency report
- Batch 1.3 Index

---

## 2. Main consistency verdict

Batch 1.3.1 is internally coherent.

All Batch 1.3 contradictions were already resolved. Batch 1.3.1 applies four targeted corrections:

1. Stale cross-references in the Opportunities Framework
2. Bolsa Profesional canonical name lock
3. Phase gap documentation in the Framework
4. Delta log standardization across all fichas

No extension has changed its implementation readiness status. The system remains at the same conceptual stage as Batch 1.3.

---

## 3. Corrections applied in Batch 1.3.1

### C6 — Stale cross-references in Opportunities Framework

Location:
- `ADG_EXTENSIONS_003_OPPORTUNITIES_FRAMEWORK_v0.1.3.md` section 9

Problem:
- Child lane references still pointed to `v0.1.2` filenames after the batch was updated to v0.1.3.

Correction:
- All child lane file references updated to `v0.1.3.1` in the new Opportunities Framework doc.

---

### C7 — Bolsa Profesional naming ambiguity

Location:
- `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.md` section 7
- `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.md` section 9

Problem:
- Two competing visible names: "Bolsa Profesional" and "Bolsa de Puestos Profesionales".
- No canonical choice was declared.

Correction:
- Canonical name locked: **Bolsa Profesional**.
- "Bolsa de Puestos Profesionales" marked as deprecated in the 003B/3C doc.
- Framework and Index updated to use canonical name only.

---

### C8 — Phase gap undocumented

Location:
- `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.md` section 9
- `ADG_EXTENSIONS_BATCH_1.3_INDEX_v0.1.3.md` section 3

Problem:
- Phases 3, 4, and 6 are unassigned in the current batch.
- Oportunidades ADG has no phase number (labeled "parent").
- No explanation was given for these gaps.

Correction:
- Framework section 9 now includes a note: phases 3, 4, 6 are reserved for future modules not yet defined; gaps are intentionally non-contiguous.
- Oportunidades ADG phase field clarified as "parent module (no assigned number)".
- Index table updated to reflect this.

---

### C9 — Delta sections did not cover v0.1.3 step

Location:
- All fichas (001, 002, 003, 003A, 003B/3C, 004)

Problem:
- Delta sections were labeled "Delta from v0.1.0" even when the docs were at v0.1.3.
- No entry existed for the v0.1.2 → v0.1.3 or v0.1.3 → v0.1.3.1 transitions.

Correction:
- All fichas now have a "Delta log" section with entries per version step.
- v0.1.3 → v0.1.3.1 entries added (even where content did not change, the version alignment is documented).

---

## 4. Resolved contradictions carried forward from Batch 1.3

The following were resolved in Batch 1.3 and remain resolved:

### C1 — Directorio state
- Corrected from `Esperando datos` to `Legacy / partial exists`.

### C2 — Bolsa de Prácticas as isolated module
- Corrected: Oportunidades ADG is the parent; Prácticas is a child lane.

### C3 — Alertas pending vs closed
- Pending doc replaced by closed Alertas ficha.

### C4 — Existing alertas surface vs Email Alerts extension
- Distinction preserved: alertas surface/stub ≠ Email Alerts ADG Extension.

### C5 — Freelancers / Profesional closure level
- Confirmed scoped only, not deep-closed fichas.

---

## 5. State matrix

| Area | Current state | Closure | Implementation meaning |
|---|---|---|---|
| Laus Tracker | Esperando datos | Closed | Needs data/source contract before product claim |
| Directorio | Legacy / partial exists | Closed | Needs data/privacy/profile claim contract |
| Oportunidades ADG | No existe nada as implemented module | Closed framework | Needs hub/process/data contract |
| Bolsa Prácticas | No existe nada | Closed child lane | Needs moderation/intake/data contract |
| Bolsa Freelancers | Not implemented | Scoped only | Needs deep ficha |
| Bolsa Profesional | Not implemented | Scoped only | Needs deep ficha / governance input |
| Alertas Email | No existe nada | Closed | Needs consent/delivery/data contract |

---

## 6. Public visibility rules

### Can appear as active

Only existing, trustworthy surfaces/features can appear active.

Currently:
- no ADG Extension should appear as a fully working new service unless implemented separately later.

### Can appear as grey / disabled / in preparation

Allowed:
- Laus Tracker if useful
- Oportunidades ADG
- Bolsa Prácticas
- Freelancers
- Profesional
- Alertas por Email

Condition:
- no activation flow implied
- no fake functionality
- no live service promise

### Should be represented as legacy/partial

Directorio:
- may reflect existing basic directory truth
- but future module must not be implied as complete

---

## 7. Data contract consistency

Global rule:
**No data contract, no real product claim.**

Needed contracts:

### Laus Tracker
- award/project historical data
- category taxonomy
- school/tutor optionality
- source references
- demo/mock policy

### Directorio
- member identity fields
- profile type
- location
- specialties/tags
- public/private fields
- claim profile state
- moderation/ownership

### Oportunidades / Prácticas
- opportunity fields
- publication status
- ADG review state
- remuneration/conditions
- deadline/application path
- intake source

### Freelancers / Profesional
- future data contracts needed after deep fichas

### Alertas
- email
- discipline preference
- territory preference
- frequency
- consent
- unsubscribe
- trigger/source
- send date
- send state

---

## 8. Governance / moderation consistency

ADG review is a core product principle in:
- Oportunidades
- Bolsa Prácticas
- Freelancers
- Profesional

Possible future ADG review or moderation also appears in:
- Directorio profile claiming
- forum/community layer
- alert preference management if profiles exist

Governance must be audited before:
- public forms
- claimed profiles
- publish offer flows
- profile posts
- forum posts/replies
- admin panels

---

## 9. Anti-drift design rules

### Laus
- must not become competitive leaderboard

### Directorio
- must not become marketplace
- must not reduce itself to a map

### Oportunidades
- must not become generic job board

### Bolsa Prácticas
- must not become exploitative internship board

### Freelancers
- must not become cheap marketplace or race-to-bottom board

### Profesional
- must not become low-quality job scraping surface

### Alertas
- must not become spam or fake automation

---

## 10. Hub / IA audit needed

The next product audit should define:

### ADG Extensions hub
- which modules appear
- active vs disabled states
- grey card logic
- module status language
- relationship to Licitaciones as core module
- relationship to ADG OPS existing navigation

### Oportunidades ADG sub-home
- cards for Prácticas / Freelancers / Profesional
- active vs en preparación states
- whether global search exists before data
- CTA per lane
- empty states

Without this, UI implementation will risk inventing IA.

---

## 11. What enters Batch 1.3.1

Enters:
- correction pass (C6 through C9)
- updated framework with phase gap note
- locked Bolsa Profesional canonical name
- standardized delta logs across all fichas
- updated index (Batch 1.3.1)
- updated consistency report (this document)

---

## 12. What exits active Batch 1.3.1

Exits from active package:
- all `v0.1.3` documents (archived to `_old/`)
- "Bolsa de Puestos Profesionales" as an alternate name
- undocumented phase gaps
- delta sections that only referenced v0.1.0

---

## 13. Recommended next sequence

1. Hub / IA audit
2. Data contracts batch
3. Governance / moderation / permissions audit
4. Claude PLAN_MIN prompt
5. Claude audit, not implementation yet
6. Implementation only after user approval

---

## 14. Claude readiness

Claude can receive Batch 1.3.1 for:
- audit
- architecture questions
- PLAN_MIN
- implementation risk review
- data contract proposal

Claude should not yet receive a direct implementation task unless the task is only:
- create static documentation
- create non-functional hub/stub shell
- create planning artifacts

Any real feature implementation needs more contracts.

---

## 15. One-line closure

**Batch 1.3.1 applies four targeted corrections to Batch 1.3 and closes the first consistency baseline for ADG Extensions; the recommended next step remains Hub/IA audit, data contracts, and governance before any serious implementation.**
