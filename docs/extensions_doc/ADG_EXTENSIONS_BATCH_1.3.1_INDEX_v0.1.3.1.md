# ADG EXTENSIONS — BATCH 1.3.1 INDEX

Version: v0.1.3.1  
Batch: 1.3.1  
Supersedes: `ADG_EXTENSIONS_BATCH_1.3_INDEX_v0.1.3.md`  
Status: CORRECTION PASS — ACTIVE BASELINE  
Mode: CONSISTENCY REVIEW  
Language: English documentation / Spanish working source  

---

## 0. What this batch is

Batch 1.3.1 is a targeted correction pass on top of Batch 1.3.

It supersedes Batch 1.3 as the active package.

It is not:
- an implementation prompt
- a code request
- a final UI wireframe
- a final backend/data model
- a legal/privacy policy

It is:
- the current documentary baseline for the ADG Extensions lane
- the package to use before Claude PLAN_MIN / audit prompts
- the reference set for future deltas

---

## 1. Documents included

1. `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.1.md`
2. `ADG_EXTENSIONS_001_LAUS_TRACKER_v0.1.3.1.md`
3. `ADG_EXTENSIONS_002_DIRECTORIO_SOCIOS_v0.1.3.1.md`
4. `ADG_EXTENSIONS_003_OPPORTUNITIES_FRAMEWORK_v0.1.3.1.md`
5. `ADG_EXTENSIONS_003A_BOLSA_PRACTICAS_v0.1.3.1.md`
6. `ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1.md`
7. `ADG_EXTENSIONS_004_ALERTAS_EMAIL_v0.1.3.1.md`
8. `ADG_EXTENSIONS_BATCH_1.3.1_CROSS_SYSTEM_CONSISTENCY_v0.1.3.1.md`

---

## 2. Corrections applied in Batch 1.3.1

| ID | Area | Fix |
|---|---|---|
| C6 | Opportunities Framework | Child lane references updated from v0.1.2 to v0.1.3.1 |
| C7 | Bolsa Profesional | Canonical name locked; "Bolsa de Puestos Profesionales" deprecated |
| C8 | Framework / Index | Phase gaps (3, 4, 6) documented as reserved/unassigned |
| C9 | All fichas | Delta log sections standardized with per-version entries |

---

## 3. Current module state table

| Module / lane | Phase | Current state | Closure state |
|---|---:|---|---|
| Laus Tracker | 1 | Esperando datos | Closed |
| Directorio de Socios | 2 | Legacy / partial exists | Closed |
| Oportunidades ADG | Parent (no number) | No existe nada as implemented module | Closed framework |
| Bolsa de Prácticas / Juniors / Talents | 5 | No existe nada | Closed child lane |
| Bolsa de Freelancers | Future child lane | Not implemented | Scoped only |
| Bolsa Profesional | Future child lane | Not implemented | Scoped only |
| Alertas por Email | 7 | No existe nada | Closed |

Phase note:
- Phases 3, 4, and 6 are unassigned in this batch.
- These are reserved for future modules not yet defined.
- Phase numbering in ADG Extensions is intentionally non-contiguous.

---

## 4. Active reading order

Use this order:

1. `ADG_EXTENSIONS_000_EXTENSION_FRAMEWORK_v0.1.3.1.md`
2. `ADG_EXTENSIONS_BATCH_1.3.1_CROSS_SYSTEM_CONSISTENCY_v0.1.3.1.md`
3. The target ficha:
   - Laus
   - Directorio
   - Oportunidades
   - Prácticas
   - Freelancers/Profesional scoped
   - Alertas

For Claude planning:
1. Framework
2. Consistency report
3. Relevant fichas
4. ADG OPS wave-2 docs if implementation touches existing surfaces

---

## 5. Implementation readiness summary

Ready for conceptual planning:
- all closed fichas

Ready for UI shell planning:
- ADG Extensions hub
- grey stubs / inactive module cards
- editorial navigation architecture

Not ready for real product implementation without more work:
- Laus Tracker data model and source audit
- Directorio full data contract and privacy/claim model
- Oportunidades intake/process/data contract
- Bolsa Prácticas publication process and moderation criteria
- Alertas data/consent/delivery workflow
- Freelancers and Profesional deep fichas

---

## 6. Next valid moves

Recommended next sequence:

1. Hub / IA audit for ADG Extensions
2. Data contracts batch
3. Governance / moderation / permissions pass
4. Claude PLAN_MIN prompt
5. Implementation planning only after the above is accepted

---

## 7. Archive note

All v0.1.3 documents have been moved to `_old/`.

Active batch is v0.1.3.1 only.

---

## 8. One-line doctrine

**Batch 1.3.1 is the corrected ADG Extensions consistency baseline: four targeted fixes applied, all fichas version-aligned, and the system remains ready for Hub/IA audit and data contracts before any implementation.**
