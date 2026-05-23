# ADG_EXTENSIONS_025 — PREHUB Checkpoint Report

**Version:** v0.1.3.1
**Status:** CHECKPOINT / SOURCE LAYER PAUSED
**Mode:** PREHUB_CHECKPOINT / HANDOFF
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**Source basis:** TXT 083 post-child-shell validation + TXT 084 Freelancers/Profesional readiness audit
**Git write operations:** FORBIDDEN to Claude CLI — operator performs all staging and commits
**Date:** 2026-05-23
**Implementation status:** DOC ONLY
**Source/data status:** NOT TOUCHED IN TXT 085

---

## 1. Purpose

This report checkpoints the ADG Extensions PREHUB source implementation layer after completing the Oportunidades parent shell and Bolsa de Prácticas child shell path.

It records:
- what was safely completed in the PREHUB source layer,
- why further source implementation pauses now,
- what remains blocked and why,
- what decisions are required before any lane can reopen for source work.

This report does not authorize data, forms, provider/capture, real opportunity listings, active surfaces, or remaining shell work for any module or lane.

---

## 2. Completed PREHUB Source Work

The following source implementation was completed safely, committed, and validated:

| TXT | Work | Commit |
|---|---|---|
| TXT 078 | Oportunidades parent prehub shell created (`oportunidades.html`) | eacb74f |
| TXT 080 | Oportunidades hub card activated in `index.html` (`card-oportunidades-adg` → `<a href="./oportunidades.html">`, `data-module-state="shell"`) | 2d19583 |
| TXT 082 | Bolsa de Prácticas child shell created (`oportunidades-practicas.html`); Prácticas lane card activated in `oportunidades.html` (`oportunidades-card-practicas` → `<a href="./oportunidades-practicas.html">`, `data-lane-status="shell"`) | 35eaf3d |

All completed shells are:
- static HTML only
- honest (EN PREPARACIÓN / Not active)
- no forms, no inputs, no submission flow
- no data files, no mock listings
- no provider/capture/API/fetch
- no active board implication

---

## 3. Completed Navigation Path

The following three-layer navigation path is complete and validated:

```
index.html
  └─ card-oportunidades-adg  →  ./oportunidades.html
       └─ oportunidades-card-practicas  →  ./oportunidades-practicas.html
```

| Step | Card / element | State |
|---|---|---|
| Hub → Parent shell | `card-oportunidades-adg` in `index.html` | `<a href="./oportunidades.html">` · `data-module-state="shell"` |
| Parent → Prácticas child | `oportunidades-card-practicas` in `oportunidades.html` | `<a href="./oportunidades-practicas.html">` · `data-lane-status="shell"` |
| Freelancers lane card | `oportunidades-card-freelancers` | `<div>` stub · `home-card--soon` · no href |
| Profesional lane card | `oportunidades-card-profesional` | `<div>` stub · `home-card--soon` · no href |

No `extensions.html` references. No active board implication at any layer.

---

## 4. Current File / State Inventory

| File | State |
|---|---|
| `index.html` | Tracked · Oportunidades card live · all active surfaces untouched |
| `oportunidades.html` | Tracked · Parent prehub shell live · Prácticas lane live · Freelancers/Profesional stubs |
| `oportunidades-practicas.html` | Tracked · Child prehub shell live / static / honest |
| `oportunidades-freelancers.html` | ABSENT / BLOCKED — not created |
| `oportunidades-profesional.html` | ABSENT / BLOCKED — not created |
| `directorio.html` | ABSENT / BLOCKED — gates pending |
| `alertas.html` | Existing honest stub · no edit in this lane |
| `laus.html` | Existing active shell · no expansion in this lane |
| `style.css` | Untouched |
| `app.js` / `shared.js` | Untouched |
| `data/**` | Untouched |
| Active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro) | Untouched / out of scope |

---

## 5. Remaining Lane Statuses

### Bolsa de Freelancers

| Dimension | Status |
|---|---|
| Canonical name | LOCKED — "Bolsa de Freelancers" |
| Ficha status | SCOPED / PROVISIONAL / HOLD |
| Implementation readiness | NOT READY |
| Direction of flow | OPEN — entity-posts-need vs. freelancer-availability vs. bidirectional unresolved |
| Directorio relationship | OPEN — conflict risk noted in 003B §5; no resolution |
| Submission / review model | OPEN — form described conceptually; not designed or locked |
| Public / private boundary | OPEN |
| Anti-marketplace rules | Doctrine only; not operationalized |
| Data schema | Candidate fields only; not finalized |
| Route / page naming | Not specified |
| Shell source eligibility | NOT ELIGIBLE — requires deep ficha closure first |

### Bolsa Profesional

| Dimension | Status |
|---|---|
| Canonical name | LOCKED — "Bolsa Profesional" (deprecated: "Bolsa de Puestos Profesionales") |
| Ficha status | SCOPED / PROVISIONAL / HOLD |
| Implementation readiness | NOT READY |
| Governance review | OPEN — "senior board / presidency may later refine criteria" (003C §8) |
| Publication criteria | OPEN — "criteria remain adjustable until governance review" |
| Role boundary vs. Freelancers | OPEN — what distinguishes Profesional from Freelancers scope not operationalized |
| Submission / review model | OPEN — form described conceptually; not locked |
| Public / private boundary | OPEN |
| Data schema | Candidate fields only; not finalized |
| Route / page naming | Not specified |
| Shell source eligibility | NOT ELIGIBLE — governance review + criteria must close first |

---

## 6. Why PREHUB Source Layer Pauses

1. **Continuing source implementation would overbuild provisional lanes.** Freelancers and Profesional have open architecture decisions (direction of flow, governance, criteria). Building shells before those decisions close risks creating structures inconsistent with the eventual design.

2. **Shells for remaining lanes could imply readiness that does not exist.** A clickable lane card linking to a shell implies a module is architecturally defined. It is not yet the case for either remaining lane.

3. **Deep ficha decisions must close first.** The 003B/003C document explicitly states it is not a "final implementation spec," "full standalone ficha closure," "complete data contract," or "publication-ready policy." Source work cannot safely proceed from a partial continuity doc.

4. **Current completed path is useful, coherent, and stable.** The three-layer navigation — hub → Oportunidades parent → Prácticas child — is a meaningful first prehub arc. Stopping here preserves safety and reduces drift risk.

---

## 7. Required Decisions Before Reopening Freelancers

Before any source shell implementation for Bolsa de Freelancers is authorized:

- **v1 flow direction:** decide between entity-posts-need only / freelancer-posts-availability only / bidirectional. Lock explicitly.
- **Directorio overlap boundary:** decide how the Freelancers lane relates to or avoids Directorio profiles. Document the boundary.
- **Intake model:** email-to-ADG only? Google Form? Lock v1 intake method.
- **Moderation / review criteria:** define what ADG checks. What passes? What fails?
- **Public / private boundary:** what is visible before and after ADG review?
- **Anti-marketplace rules:** operationalize what is prohibited; how ADG enforces minimum quality.
- **Route / page naming:** lock canonical filename and card ID for the child shell.
- **Shell before process:** explicit operator decision on whether a static prehub shell may exist before the process model is fully locked.

---

## 8. Required Decisions Before Reopening Profesional

Before any source shell implementation for Bolsa Profesional is authorized:

- **Governance / board review completion:** senior board / presidency must complete criteria review before publication standards can be finalized.
- **Publication criteria:** post-governance, lock minimum criteria list with no ambiguity.
- **Senior / professional role boundary:** clarify what distinguishes Profesional from Freelancers; avoid overlap.
- **Intake model:** lock v1 intake method (email-to-ADG? form?).
- **Moderation / review criteria:** define what ADG checks; what qualifies as professional-level.
- **Public / private boundary:** what is visible before and after ADG review?
- **Anti-marketplace rules:** operationalize prohibitions; quality gatekeeping.
- **Route / page naming:** lock canonical filename and card ID.
- **Shell before process:** explicit operator decision on whether a static shell may exist before all criteria are finalized.

---

## 9. Blocked Modules

### Directorio de Socios
- Blocked by ADG-FAD authorization (required, not obtained).
- Blocked by legal / privacy review (GDPR/LOPD obligations for member personal data).
- Blocked by data/schema approval (member visibility model not finalized).
- Blocked by all 11 pre-activation gates in Contract ADG_EXTENSIONS_023.
- `directorio.html` must not be created until all gates are cleared and operator explicitly reopens source scope.

### Alertas por Email
- Blocked by Contract ADG_EXTENSIONS_021 §16: "alertas.html editing is OUT OF SCOPE until all consent/legal/provider gates are closed."
- 11 pre-activation gates all OPEN (double opt-in model, consent language, provider selection, schema, unsubscribe flow, etc.).
- No form, capture, or provider may be added without gate closure.

### Laus Tracker
- Existing shell active (`laus.html`).
- Data expansion (awards panel, extended jury data) paused pending separate data contract and operator scope reopen.
- Shell is functional; no expansion without gate.

### Active Surfaces
- Licitaciones / Observatorio — out of scope for this lane.
- Estadísticas Forense — out of scope.
- Recursos + Calculadora — out of scope.
- Mapa del Diseño — out of scope.
- Barómetro del Sector — out of scope.

---

## 10. Prohibited Future Actions

The following actions are prohibited without an explicit new operator-authorized scope reopen:

- `git add .` — never.
- Resurrection of `extensions.html` — permanently prohibited.
- Creation of `oportunidades-freelancers.html` — blocked until Freelancers deep ficha is CLOSED.
- Creation of `oportunidades-profesional.html` — blocked until Profesional deep ficha + governance review are CLOSED.
- Creation of `directorio.html` — blocked until ADG-FAD authorization + legal review + all gates cleared.
- Editing or activating `alertas.html` forms/capture — blocked until Contract 021 gates closed.
- Real opportunity data / listings / mock data — blocked; no data file activation without separate approval.
- Forms / inputs / provider / capture / fetch / API — blocked.
- Active surface edits (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro) — out of scope.
- Private / support / member data reads — prohibited.
- Source implementation without explicit operator reopen TXT — blocked.

---

## 11. Safe Reopen Paths

### Option A — Freelancers/Profesional deep ficha operator decision lane (recommended if advancing)

**TXT 086_audit:** Freelancers/Profesional operator decision closure audit.
- Read-only.
- Collect required operator decisions in one efficient batch.
- Close: flow direction, intake model, governance status (Profesional), criteria, naming.
- Output: locked decision set.
- Follow with **TXT 087_imp:** deep ficha doc writes (one doc per lane if decisions close).
- Follow with **TXT 088_imp:** source shell implementation only after ficha docs are committed.

### Option B — PREHUB close/freeze + new planning lane when operator is ready

- Leave current checkpoint in place.
- Begin a new explicit planning lane when operator is ready to advance Freelancers, Profesional, Directorio, or Alertas.
- Each module requires its own gate-clearing process before any source.

### General future source reopen conditions (apply to any lane)

Before any new source shell is approved:
1. Lane ficha is CLOSED (not SCOPED / PROVISIONAL).
2. Route / card names are locked.
3. Status copy is locked.
4. No data / forms / provider unless separately approved in a subsequent explicit TXT.
5. Exact file scope is defined and approved in the IMP prompt.

---

## 12. ROADMAP PRÓXIMO

- **TXT 085** — current: PREHUB checkpoint close report ← THIS DOCUMENT
- **TXT 086** — optional: Freelancers/Profesional deep ficha operator decision lane (audit or decision closure)
- **TXT 087** — optional: Oportunidades data/process planning only after fichas + gates close
- **TXT 088** — optional: new safe source shell only if a ficha closes and operator reopens scope
- **PREHUB LAYER 3** — parent shell + Prácticas child shell: **COMPLETE**
- **PREHUB LAYER 4** — data/mock only after gates (blocked; no open path)
- **HOLD** — Bolsa Freelancers source shell (direction of flow unresolved; intake model not locked; Directorio conflict unresolved)
- **HOLD** — Bolsa Profesional source shell (governance review outstanding; publication criteria adjustable)
- **HOLD** — `directorio.html` (ADG-FAD auth + legal + 11 gates blocked)
- **HOLD** — `alertas.html` activation (Contract 021 §16; 11 gates open)
- **HOLD** — Laus expansion (data contract required)
- **HOLD** — real opportunity data / listings / mock
- **HOLD** — active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro)
- **HOLD** — private data / forms / provider / capture
- **HOLD** — no `git add .` ever
