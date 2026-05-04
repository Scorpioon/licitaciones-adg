# ADGOPS_009_STABILIZATION_CHECKPOINT_v0.4.3p

Status: ACTIVE RECORD
Authority: ADG OPS stabilization phase record
Current baseline: 0.4.3p
Parent docs: `ADGOPS_001_STATUS_QUO_v2.1`, `ADGOPS_004_RUNTIME_TRUTH_v2.0a`
Language: English
Purpose: Record the 0.4.3k–0.4.3p stabilization lane results, current version baseline, open debts, and roadmap position as of the close of the 0.4.3 stabilization phase.

---

## 0. What this document is

This is the stabilization checkpoint record for ADG OPS after the 0.4.3k–0.4.3p lane series.

It exists to answer:
- what the current runtime version baseline is
- what the stabilization lanes achieved
- what the current shell/layout status is
- what open debts remain
- where the project sits on the roadmap

This is not:
- a replacement for the canonical status doc
- a runtime truth update
- a product direction change
- a roadmap revision

It bridges the gap between the pre-stabilization Wave-2 canon docs and current repo truth.

---

## 1. Version baseline

- `ADG.version = '0.4.3p'` in `app.js` is the canonical runtime source.
- Runtime badges sync through `[data-adg-version]` during `initShared()` / DOMContentLoaded.
- Static HTML fallback badge values may lag; runtime source wins.

---

## 2. Stabilization lanes completed

| Lane | Description |
|------|-------------|
| 0.4.3k | Runtime version truth: `ADG.version` constant added; `initShared()` syncs all `[data-adg-version]` nodes |
| 0.4.3l | Licitaciones scoped responsive shell: `body.lic-page`, `main.main.lic-main`, ≤860px natural page-scroll contract |
| 0.4.3m | Detail panel internal scroll: `min-height:0` added to `.sh-ficha__body` |
| 0.4.3n | Stats/barometro scroll / white-cut CSS fix: `min-height:0` added to `.sv-body` and `.baro-page` |
| 0.4.3p | Alertas visible text degradation repair: 3 missing-diacritic strings repaired in static HTML (nav × 2, footer × 1) |

---

## 3. Current shell/layout status

- **Licitaciones responsive shell:** stable after 0.4.3l smoke test.
- **Detail panel scroll:** source-level fix in place (0.4.3m); browser validation expected.
- **Stats/barometro scroll:** source-level fix confirmed in `style.css` (0.4.3n); browser validation required before final closure.
- **Runtime version badge mechanism:** stable in code; all pages except `mapa.html` carry a `[data-adg-version]` node.
- **Alertas visible text:** repaired in 0.4.3p; three previously degraded static strings are now correct.

---

## 4. Confirmed open debts

| Item | Classification | Notes |
|------|---------------|-------|
| 0.4.3q semantic copy cleanup | parked, not canceled | Intentionally deferred; lower priority than data work |
| `mapa.html`: no standard footer / runtime version badge | shell/trace debt | Separate lane; not encoding or text repair |
| `estadisticas.js`: stale top header comment (shows 0.4.3h) | debt | No functional impact; not this lane |
| `about.js`: changelog stale at β3.1 (Mar 2026) | later | |
| `index.js` / `licitaciones.js`: ~95% code duplication | debt | Do not refactor yet; no immediate user-visible impact |
| Formspree placeholder in `licitaciones.html` | later | Feature not live; placeholder is correct holding state |
| Fetcher/data trust | next major phase | Belongs to 0.4.4 |

---

## 5. Roadmap position

### Current phase: 0.4.3 stabilization — nearing closure

Remaining 0.4.3 lanes:
- **0.4.3q** — semantic copy cleanup (parked)
- **0.4.3r** — docs/session truth checkpoint (this lane)
- **0.4.3s** — final smoke / release-candidate audit

Gate before 0.4.3s: browser validation of 0.4.3n stats/barometro scroll behavior. If it fails, a targeted CSS fix lane is inserted before 0.4.3s.

### Next major phase: 0.4.4 — data/kernel trust

- 0.4.4a — fetcher architecture audit
- 0.4.4b — data truth model
- 0.4.4c — PDF/document extraction plan
- 0.4.4d — provenance + trust indicators
- 0.4.4e — SQL path design

---

## 6. Canon consequence

- `ADGOPS_001_STATUS_QUO_v2.1.md` supersedes v2.0 for current status.
- `ADGOPS_004_RUNTIME_TRUTH_v2.0a.md` remains useful but contains known stale licitaciones fragility wording (shell issue is now resolved). Update after 0.4.3s or during 0.4.4a.
- Prompt docs in `docs/` root remain execution records only; not canonical product docs.

---

## 7. Reading path consequence

Future Claude sessions re-entering after 0.4.3p should read this doc immediately after `ADGOPS_001_STATUS_QUO_v2.1` to recover current version baseline and lane history before proceeding to runtime truth or surface docs.
