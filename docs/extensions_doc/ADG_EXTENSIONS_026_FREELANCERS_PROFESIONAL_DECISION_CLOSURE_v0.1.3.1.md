# ADG_EXTENSIONS_026 — Freelancers / Profesional Decision Closure

**Version:** v0.1.3.1
**Status:** CLOSED FOR STATIC SHELL PLANNING / NOT ACTIVE
**Mode:** DECISION_CLOSURE / PREHUB
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**Source basis:** TXT 087 operator decision audit + operator answers Q1=A, Q2=B, Q3=A, Q4=A
**Git write operations:** FORBIDDEN to Claude CLI — operator performs all staging and commits
**Date:** 2026-05-23
**Implementation status:** DOC ONLY
**Source/data status:** NOT TOUCHED IN TXT 088

---

## 1. Purpose

This document closes the minimum decision layer required to plan static prehub shells for Bolsa Freelancers and Bolsa Profesional.

It exists because TXT 087 found both shells blocked: the existing ficha doc (ADG_EXTENSIONS_003B_003C) is SCOPED / PARTIAL CLOSED FOR DELTA — explicitly not a final implementation spec or ficha closure — and the process contract (ADG_EXTENSIONS_022 OD7) states that source/data implementation for these lanes is BLOCKED until deep fichas are CLOSED.

TXT 087 surfaced four blocking questions (Q1–Q4) for the operator to answer before any shell planning could proceed. The operator has answered those questions. This document records those answers and closes the minimum decision set required for static-only shell implementation.

**This document does NOT:**
- activate Bolsa Freelancers or Bolsa Profesional
- authorize data files, listings, mock data, or board content
- authorize forms, inputs, provider/capture, or any submission flow
- authorize public self-submit or publication workflows
- authorize active surface edits
- grant implementation permission — implementation permission is granted separately in a future IMP prompt (TXT 089)

**This document DOES:**
- record the operator decisions for Q1–Q4
- close the static-shell posture for both lanes
- define the route, card, state, and copy grammar for future shells
- preserve all active-publishing, data, form, and governance gates
- authorize future TXT 089_imp to plan both static shells only after this doc is committed

---

## 2. Operator Decisions Recorded

The following decisions were given by the operator in response to TXT 087 blocking questions:

| Question | Answer | Meaning |
|---|---|---|
| **Q1** — Freelancers v1 flow direction | **A) Entity-posts-need only** | Studios/organizations post freelance needs to ADG in v1. Freelancers do not post availability. No public freelancer profiles. |
| **Q2** — Shell before ficha closure | **B) No — write decision/ficha closure docs first** | Static source shells wait until this docs-only closure exists and is committed. This document is that closure. |
| **Q3** — Profesional governance shell posture | **A) Shell may exist with honest governance-pending copy** | A static Profesional shell is allowed provided it clearly states governance criteria are pending and the lane is not active. Governance review blocks active publication, not an honest static shell. |
| **Q4** — Lane priority | **A) Both lanes together** | Freelancers and Profesional shells may be implemented in the same IMP batch because they share the same static-shell risk layer and Pattern B grammar. |

---

## 3. Bolsa Freelancers — Closed Static-Shell Posture

### Identity

| Field | Value |
|---|---|
| Canonical name | Bolsa de Freelancers |
| Parent module | Oportunidades ADG |
| Lane | freelancers |
| Status | CLOSED FOR STATIC SHELL PLANNING / NOT ACTIVE |

### v1 Flow Direction (Q1=A LOCKED)

- Entity/studio/organization submits a freelance need to ADG.
- ADG receives, reviews, and approves before any publication.
- Submission does not equal publication.
- Freelancers do NOT post availability in v1.
- No public freelancer profiles are created.
- No bidirectional flow in v1.

### Route and Card

| Field | Value |
|---|---|
| Route candidate | `oportunidades-freelancers.html` |
| Card ID | `oportunidades-card-freelancers` (already exists in `oportunidades.html`) |
| Card element when shell exists | `<a href="./oportunidades-freelancers.html">` |
| `data-lane-status` when shell exists | `shell` |
| Card class when shell exists | `home-card home-card--live` |

### Static-Shell Copy Posture

The shell must communicate:
- EN PREPARACIÓN / NOT ACTIVE
- No board, no listings, no form
- Deep ficha pendiente / governance decisions in progress
- ADG-curated model (no automatic publication)
- Contact ADG directly for inquiries

### Directorio Boundary (Q1=A)

- No linkage to Directorio de Socios in v1.
- Opportunity submission does not create or reference member profiles.
- Profile discovery is separate from opportunity publication.
- Any future Directorio linkage requires a separate authorization lane.

### Active Publication Gate

Active publication of freelance listings remains BLOCKED until:
1. A data/process implementation lane is opened with a separate approved IMP prompt.
2. The data schema (candidates in 003B §6) is finalized and committed.
3. Legal/terms for submitting organizations are approved (022 OD14).
4. The intake technology is selected and approved (003 §7).
5. The operator explicitly reopens source scope for data/listing activation.

---

## 4. Bolsa Profesional — Closed Static-Shell Posture

### Identity

| Field | Value |
|---|---|
| Canonical name | Bolsa Profesional |
| Deprecated alternate name | "Bolsa de Puestos Profesionales" — PROHIBITED |
| Parent module | Oportunidades ADG |
| Lane | profesional |
| Status | CLOSED FOR STATIC SHELL PLANNING / NOT ACTIVE |

### v1 Flow Direction

- Entity/studio/organization submits a professional role to ADG.
- ADG reviews and approves before any publication.
- Submission does not equal publication.
- No candidate or profile posting.
- Lower volume, higher quality criteria than internships.

### Route and Card

| Field | Value |
|---|---|
| Route candidate | `oportunidades-profesional.html` |
| Card ID | `oportunidades-card-profesional` (already exists in `oportunidades.html`) |
| Card element when shell exists | `<a href="./oportunidades-profesional.html">` |
| `data-lane-status` when shell exists | `shell` |
| Card class when shell exists | `home-card home-card--live` |

### Static-Shell Copy Posture (Q3=A LOCKED)

The shell must communicate:
- EN PREPARACIÓN / NOT ACTIVE
- Governance criteria pending — publication criteria not yet finalized
- No board, no listings, no form
- ADG-reviewed model (no automatic publication)
- Active publication requires governance criteria lock

Governance blocks active publication, not an honest static prehub shell. The static shell is explicitly not a publication surface and does not imply criteria are final.

### Directorio Boundary

- No linkage to Directorio de Socios in v1.
- Same boundary as Freelancers: opportunity ≠ profile.

### Active Publication Gate

Active publication of professional listings remains BLOCKED until:
1. Senior board/presidency governance review is completed (003B §8).
2. Publication criteria are finalized and committed post-governance.
3. A data/process implementation lane is opened with a separate approved IMP prompt.
4. The data schema (candidates in 003B §12) is finalized.
5. Legal/terms for submitting organizations are approved (022 OD14).
6. The operator explicitly reopens source scope for data/listing activation.

---

## 5. Shared Rules for Both Future Shells

Both static shells must follow these absolute rules, enforced in the IMP prompt (TXT 089) and in every future edit:

### Structural rules (Pattern B grammar)
- shell-top + global nav + page-body + footer + `app.js` + `shared.js` only
- No module-specific CSS unless a separate CSS audit approves it
- Use existing `style.css` only

### Forbidden elements (both shells — absolute)
- No `<form>`
- No `<input>`
- No `<button type="submit">`
- No `action=`
- No `mailto:` submission flow
- No `fetch()` / `XMLHttpRequest` / XHR
- No provider endpoint (Formspree, Mailchimp, Brevo, or any other)
- No email capture
- No data file reference
- No mock listings
- No real listings
- No public self-submit flow
- No active board implication
- No active surface links or references
- No `extensions.html` reference

### Honest-state requirements
- Hero/disclaimer must state EN PREPARACIÓN / NOT ACTIVE
- Must include "Sin tablón activo" / "Sin formulario de envío" tags
- Must not imply any opportunity is live or submittable
- Must not imply governance criteria are finalized (Profesional)

---

## 6. Future TXT 089 Implementation Eligibility

After this document is committed and the operator confirms eligibility, a future TXT 089_imp may create both static shells in one same-risk-layer batch.

### Allowed future writes (TXT 089 only, when approved)

| File | Allowed action |
|---|---|
| `oportunidades-freelancers.html` | Create — static prehub shell only |
| `oportunidades-profesional.html` | Create — static prehub shell only |
| `oportunidades.html` | Edit — activate the two lane cards only (`oportunidades-card-freelancers` and `oportunidades-card-profesional` → `<a href>` + `data-lane-status="shell"`) |

### Forbidden even in TXT 089

| File / category | Reason |
|---|---|
| `index.html` | Hub activation of Oportunidades card is already live — no edit needed or allowed |
| `data/**` | No data files for these lanes |
| Forms / provider / capture | Blocked by shared rules §5 and active publication gate |
| `directorio.html` | Separate blocked module |
| `alertas.html` | Blocked by Contract 021 §16 |
| `laus.html` | Blocked — data contract required |
| `style.css` / `app.js` / `shared.js` | Untouched unless separately approved |
| Active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro) | Out of scope |

### TXT 089 preconditions

Before TXT 089_imp may be executed:
1. This document (ADG_EXTENSIONS_026) must be committed.
2. git status must be clean.
3. The operator must explicitly submit a TXT 089 IMP prompt.
4. No data, forms, provider, or active board work is included in TXT 089 scope.

---

## 7. Remaining Blocked Items

| Item | Status |
|---|---|
| Active data/listings for Freelancers | BLOCKED — data/process gate not cleared |
| Active data/listings for Profesional | BLOCKED — governance criteria + data/process gate |
| Public form / intake | BLOCKED — 022 OD2 locks email-to-ADG only in v1 |
| Provider / capture | BLOCKED |
| Freelancers availability posting | DEFERRED — not in v1 (Q1=A) |
| Profesional governance criteria | PENDING — required for active publication; not for static shell |
| Directorio relation (both lanes) | DEFERRED — no linkage v1; future requires separate authorization |
| `directorio.html` | BLOCKED — ADG-FAD authorization + legal review + 11 gates |
| `alertas.html` activation | BLOCKED — Contract 021 §16 + 11 consent/legal/provider gates |
| Laus Tracker expansion | BLOCKED — data contract required |
| Active surfaces | OUT OF SCOPE — Licitaciones, Estadísticas, Recursos, Mapa, Barómetro |
| Private / support / member data | PROHIBITED |
| `git add .` | NEVER |

---

## 8. Safe Reopen Paths

| Path | Condition |
|---|---|
| **TXT 089_imp** — static shell implementation for both lanes | After this doc is committed + git clean + operator-submitted IMP prompt |
| Active listing/data system (Freelancers or Profesional) | New data/process lane after: data schema finalized + intake tech selected + legal/terms approved + operator scope reopen |
| Public submission / provider / capture | Consent/legal/provider gate closure (separate from shell work) |
| Directorio linkage | Directorio authorization + privacy lane complete |
| Profesional governance publication | Senior board/presidency criteria lock + ficha update |
| Any active surface work | Separate branch / out of extensions scope |

---

## 9. ROADMAP PRÓXIMO

- **TXT 088** — COMPLETE: Freelancers/Profesional decision closure doc ← THIS DOCUMENT
- **TXT 089** — likely: static shell implementation for both lanes (pending TXT 088 commit + operator IMP prompt)
- **TXT 090** — likely: post-shell validation + PREHUB close/handoff
- **TXT 091** — optional: Oportunidades data/process planning only after gates
- **PREHUB LAYER 3** — parent + Prácticas: COMPLETE
- **PREHUB LAYER 3.5** — Freelancers/Profesional static-shell decision layer: CLOSING ← THIS DOCUMENT
- **PREHUB LAYER 4** — data/mock only after gates (blocked)
- **HOLD** — active data/listings/forms/provider/capture
- **HOLD** — Freelancers availability posting (v1 deferral locked by Q1=A)
- **HOLD** — Profesional governance criteria for active publication
- **HOLD** — Directorio de Socios (ADG-FAD auth + legal + 11 gates)
- **HOLD** — Alertas por Email (Contract 021 §16 + 11 gates)
- **HOLD** — Laus Tracker expansion (data contract required)
- **HOLD** — active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro)
- **HOLD** — private data / forms / provider / capture
- **HOLD** — no `git add .` ever
