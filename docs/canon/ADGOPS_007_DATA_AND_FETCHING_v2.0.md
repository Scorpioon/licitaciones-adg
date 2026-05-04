# ADGOPS_007_DATA_AND_FETCHING_v2.0

Status: ACTIVE DRAFT  
Authority: ADG OPS data intake and future fetching layer  
Parent docs: `ADGOPS_004_RUNTIME_TRUTH_v2.0a`, `ADGOPS_005_INTENDED_DIRECTION_v2.0`, `ADGOPS_006_FUTURE_MODULES_v2.0`  
Language: English  
Purpose: Explain the current fetcher truth, the current limits of data intake, and the intended future direction toward a broader multi-fetcher and structured-data architecture.

---

## 0. What this document is

This is the data-and-fetching document for ADG OPS wave-2.

It exists to answer:
- what the current fetcher reality is
- what is currently wrong or incomplete
- why the solution is broader than one local bugfix
- how data intake is expected to evolve
- how future structured storage and ingestion should be understood today

This is not:
- a final DB design
- a full ETL spec
- a patch request
- a claim that the data stack is already mature

One-line doctrine:

**Treat the current fetcher as real current tooling, but document the data path as an architecture still in transition.**

---

## 1. Current truth

## 1.1 The current fetcher is active
The current fetcher is real active tooling.
It is part of current runtime truth.
It matters now.

It should not be described as:
- hypothetical
- future-only
- irrelevant until later

## 1.2 The current fetcher is not sufficient
The current fetcher is also not the finished answer.

Known reading:
- it has a logic flaw
- it can overwrite the licitaciones JSON
- the issue is not only a small local bug
- the deeper problem points toward broader ingestion and architecture work

This means:
- a small fetcher fix may still be needed
- but the real documentation truth must show that the path ahead is larger than that one correction

---

## 2. Current classification

### Current fetcher
- Type: tooling/runtime component
- Runtime class: partial / active / fragile
- Current state:
  - active
  - useful
  - incomplete
  - not final

Why this matters:
- under-documenting it would create false certainty
- over-documenting it as if it were the final system would also be false

---

## 3. Why the current issue is broader than one bug

The current fetcher problem should be read in two layers:

### Layer A — local logic flaw
- the current fetcher has behavior that can overwrite the licitaciones JSON
- this is a real operational problem

### Layer B — architectural incompleteness
- the future data path should not depend on one fetcher doing everything
- broader ingestion needs already exist
- deeper document-based extraction is already directionally relevant
- future data architecture likely requires multiple fetchers / intake lines

Correct reading:
- local bug and architecture gap coexist
- fixing the local bug does not solve the whole data future
- the future architecture does not cancel the need for local correctness now

---

## 4. Intended future direction

The intended data/fetching direction currently points toward:

- more than one fetcher
- clearer separation of intake roles
- deeper document ingestion
- stronger structured storage
- better long-term queryability
- less brittle data flow

The system is likely moving toward:
- current fetcher as one line in a broader intake architecture
- document/PDF ingestion as another meaningful line
- future DB/SQL-backed storage as a later structured layer

---

## 5. PDF / deeper document ingestion

This is not just a side note.

PDF or deeper document ingestion belongs in canon as:

- part of intended data architecture
- a likely second ingestion line
- a structural reason not to overfit the current fetcher to every future need

What it changes now:
- current fetcher docs must remain modest
- present architecture should stay open enough for another intake line later
- future coding work should not assume one fetcher can remain the whole data story forever

---

## 6. SQL / structured storage direction

Structured storage should currently be read as:

- intended capability
- still formative
- important enough to shape readiness
- not yet frozen into a final technical implementation

Meaning:
- today’s docs should not promise a full DB model
- but they should make clear that the suite is likely moving toward stronger structured storage later

This matters because:
- current JSON-centered or file-centered flow may not be the long-term endpoint
- future intelligence depth will likely require better persistence and query structure

---

## 7. Current documentation rule

Today’s docs must show all three truths at once:

### Truth 1
The current fetcher is active and matters now.

### Truth 2
The current fetcher has known flaws and is not sufficient.

### Truth 3
The intended data path is broader than the current fetcher and likely includes multi-fetcher + deeper ingestion + structured storage.

If one of these truths is removed, the documentation becomes misleading.

---

## 8. Relationship to coding partners

Coding partners may:
- simplify local fetcher solutions
- propose cleaner intake boundaries
- recommend less brittle architecture
- ask for clarification where ingestion responsibility is unclear

Coding partners may not:
- silently redefine product meaning
- assume final DB architecture without confirmation
- convert a future architecture note into immediate speculative implementation

If the intended data architecture is unclear, questions must be asked rather than guessed.

---

## 9. Locked conclusions

- the current fetcher is active current tooling
- the current fetcher is not final
- the current issue is both a local flaw and an architectural incompleteness signal
- a broader multi-fetcher direction is already canonically relevant
- PDF/deeper document ingestion belongs to intended data architecture
- SQL / structured storage is intended, but still formative
- current docs must keep present truth and future data direction separate but connected

---

## 10. One-line doctrine

**Document the current fetcher honestly, but design the ADG OPS data narrative around a broader future than one fragile intake script.**
