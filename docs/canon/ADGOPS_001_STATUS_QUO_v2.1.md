# ADGOPS_001_STATUS_QUO_v2.1

Status: ACTIVE DRAFT
Authority: ADG OPS current project state
Parent docs: `ADGOPS_000_DOC_ARCHITECTURE_v2.0`, active repo truth
Language: English
Purpose: State the current real working state of ADG OPS, the active blockers, and the current known truth of the development repo without mixing it with intended future direction.

Last updated: 0.4.3p stabilization checkpoint. See `ADGOPS_009_STABILIZATION_CHECKPOINT_v0.4.3p`.

Supersedes: `ADGOPS_001_STATUS_QUO_v2.0.md` (retained as historical source)

---

## 0. What this document is

This is the current status quo for ADG OPS wave-2.

It exists to answer:
- what ADG OPS is today
- what repo truth is active
- what major surfaces exist
- what is currently acceptable
- what is currently unresolved
- what the active blockers are
- what should not be assumed

This is not:
- the full runtime map
- the full suite map
- the intended direction doc
- the roadmap
- a patch log

---

## 1. Current baseline reality

ADG OPS currently exists as:
- a live product family with multiple real surfaces
- a separate active development repo
- an unpublished-but-official development truth distinct from the live/main repo

Important distinction:
- the live/main repo is not the same thing as the current development truth
- the active repo is the correct source for current implementation reading

Reason:
- new features and structural changes were intentionally separated to avoid overwriting the live version prematurely

Rule:
- repo truth is authoritative for current implementation state

---

## 2. Current project reading

ADG OPS is no longer a narrow "one-page" or "one-lane" project.

It should currently be read as:
- a modular suite
- surface-driven
- already functionally meaningful
- still uneven in maturity across surfaces
- actively evolving toward a broader ecosystem

This broader direction is real, but it does not erase the need to document current truth accurately.

---

## 3. Current known strengths

### 3.1 Stats / barometro lane improved materially
The `estadisticas` / `barometro` side has received more recent structural work and is currently more acceptable than the licitaciones lane for the present version.

That does not mean it is final.
It means it is currently more stable and more readable as working development truth.

### 3.2 Product interest is real
There is strong real-world positive feedback around the product direction.

This matters strategically:
- the suite is not being documented only as an internal experiment
- documentation quality now matters as infrastructure for finishing well

This point is strategic context, not implementation truth.

### 3.3 The project has enough real shape to deserve proper docs
The suite already has enough product structure, runtime behavior, and future direction that it now needs:
- a clean documentation system
- surface docs
- current/intended separation
- explicit runtime truth
- explicit module/surface mapping

---

## 4. Current known blockers

### 4.1 Licitaciones shell/footer parity — resolved
Shell/footer parity was resolved across 0.4.3l (responsive shell: `body.lic-page` / `main.lic-main` / ≤860px contract) and 0.4.3m (detail panel internal scroll: `min-height:0` on `.sh-ficha__body`). Licitaciones no longer carries this specific blocker. Remaining licitaciones depth and data issues are still tracked separately. See `ADGOPS_009_STABILIZATION_CHECKPOINT_v0.4.3p`.

### 4.2 Documentation truth lags behind repo truth
Wave-1 docs were useful during recovery, but they no longer describe the current repo and suite shape well enough.

This is now a documentation blocker for future safe work:
- coding context becomes weaker
- module understanding becomes weaker
- current vs intended gets blurred
- future coding LLM work becomes noisier than necessary

---

## 5. Current known debts

### 5.1 Surface-level maturity is uneven
Not all surfaces are at the same level of stability, depth, or clarity.

### 5.2 Runtime version truth
Runtime version truth is centralized in `app.js` through `ADG.version` and synced to `[data-adg-version]` nodes during `initShared()` on DOMContentLoaded. Static HTML fallback badge values may lag behind the runtime source; runtime source wins. `mapa.html` currently carries no `[data-adg-version]` node and has no standard footer — a shell/trace debt tracked for a separate lane.

### 5.3 Fetching/data intake is active but not mature
The current fetcher is real and active, but:
- it has known logic issues
- it is not the final data architecture
- more than one fetcher is expected in the future
- deep fetcher documentation belongs later, after core suite truth is stabilized

### 5.4 Placeholder / synthetic / partial behavior still exists
Some areas likely still rely on:
- partial data truth
- synthetic states
- placeholder behavior
- incomplete implementation layers

This must be documented explicitly in runtime docs.

---

## 6. Current known later-items

The following are real, but not the immediate documentation blocker:

- fetcher overhaul
- future multi-fetcher architecture
- SQL / DB integration
- Laus Tracker
- partner directory
- internship board
- email alerts
- table/order/list polish
- deeper future module architecture

These matter, but they belong to intended/future documentation layers after the current suite truth is stabilized.

---

## 7. What should not be assumed

Do not assume:
- that the live repo equals the current development repo
- that all surfaces share the same maturity level
- that `barometro` is just a subsection of `estadisticas`
- that the fetcher is finished
- that wave-1 docs still describe the project correctly without qualification
- that current truth and intended direction can be merged safely in one doc

---

## 8. Active documentation consequence

Because the repo is now the official development truth and the suite shape is broader than the first documentation wave assumed, ADG OPS now needs a wave-2 documentation layer that:

- treats the product as a suite
- works surface-first
- separates current from intended
- moves wave-1 to `._old\`
- explains runtime truth honestly
- prepares better coding support for future Claude work

---

## 9. Immediate next move

The next correct move is to proceed toward 0.4.3s (final smoke / release-candidate audit) after validating 0.4.3n scroll behavior in the browser, then move into the 0.4.4 data/kernel trust phase.

For full current version baseline and lane history, see `ADGOPS_009_STABILIZATION_CHECKPOINT_v0.4.3p`.

---

## 10. One-line doctrine

**ADG OPS is already too real and too broad to be documented as a patch lane; it now requires suite-level truth.**
