# ADG OPS — Fetcher Architecture Naming Map
<!-- p193 / v0.6.46 — documentation only, no runtime changes -->

## 1. Purpose

This document is the canonical naming reference for all data-pipeline components
in ADG OPS.  It exists to prevent confusion between layers (e.g. "Fetcher 2"
was used to mean both document-link discovery *and* the missing document-reading
layer), to set ownership boundaries before the DocReader/Appendix build, and to
give future prompts a stable mental model.

---

## 2. Naming Rule

**Do not use Fetcher 1 / Fetcher 1.1 / Fetcher 2 / Fetcher 2.1 as canonical
names.**  These labels conflate responsibility with iteration order.

Use responsibility-based English engineering names in code and documentation.
UI-facing labels (Spanish/Castilian) may remain as-is.

---

## 3. Architecture Table

| Component | Canonical Name | Current Files | Responsibility | Input | Output | Status | Next Action |
|---|---|---|---|---|---|---|---|
| Fetcher 1 | **Harvester** | `fetch_licitaciones.py` | Fetch PLACSP ATOM feeds; score, classify, enrich, and merge licitaciones. | PLACSP source feeds | `data/licitaciones.json` (candidate envelope) | installed, frozen | freeze |
| Scheduled merge orchestrator | **Merger** | `tools/scheduled_fetch_merge.py` | Lifecycle-safe append/merge of Harvester candidate into production. | Harvester candidate, `data/licitaciones.json` | Updated `data/licitaciones.json` | installed, frozen | freeze |
| Operational classifier | **RunReporter** | `tools/scheduled_run_classify.py` | Classify scheduled-run outcome; emit machine-readable report and workflow summary. | Env vars, `_tmp/` helper logs | `ADGOPS_SCHEDULED_RUN_REPORT_V1` JSON + GitHub step summary | installed, frozen | freeze |
| Offline regression harness | **RegressionHarness** | `tools/fetcher_fixture_regression.py`, `tools/fixtures/fetcher/*.json` | Table-driven offline regression of Merger + RunReporter semantics; proves production data untouched. | Fixture JSON, Merger/RunReporter modules | PASS/FAIL terminal report | installed, frozen | freeze |
| Fetcher 2-A | **DocIndexer** | `tools/fetch_documents_f2.py` | Read licitaciones detail pages; extract candidate document/pliego/anexo links. | `data/licitaciones.json` (read-only), PLACSP detail page HTML | F2-A sidecar manifest (`f2a/1`) | installed, operator-run | maintain |
| Fetcher 2-B | **LinkResolver** | `tools/fetch_documents_f2b.py` | Probe F2-A candidate URLs; resolve final URL, content-type, MIME, filename. | F2-A manifest (`f2a/1`) | F2-B sidecar manifest (`f2b/1`) | installed, operator-run | maintain |
| F2 consolidate/gate/plan/apply | **DocEvidenceChain** | `tools/f2b_consolidate.py`, `tools/f2_quality_gate.py`, `tools/f2_merge_gate.py`, `tools/f2_persist_plan.py`, `tools/f2_apply_persist_plan.py` | Consolidate F2-B batches; gate quality; produce dry-run merge plan; apply evidence to production `documents[]`. | F2-B manifests, production `data/licitaciones.json` (read-only for plan) | `f2merge/3` plan → `f2persist/1` plan → production `documents[]` update | installed, operator-run | maintain |
| — | **DocReader** | *(not built)* | Fetch and extract text/metadata from confirmed document URLs. | `documents[]` confirmed links | Per-document content sidecar | **not built** | build next |
| — | **Appendix** | *(not built)* | Produce per-licitación document intelligence summary (Apéndice). | DocReader output | Appendix sidecar / UI panel | **not built** | build after DocReader |
| — | **StatsEngine** | `estadisticas.js`, `estadisticas.html` | Descriptive analytics over the licitaciones corpus. | `data/licitaciones.json` | Estadísticas UI | installed, partial | redesign later |
| — | **BarometerEngine** | *(not built)* | Interpretive signal layer: opportunity/risk/pressure scoring (Barómetro). | Licitaciones corpus + appendix intel | Barómetro UI signals | **not built** | design after Appendix |
| — | **ExtensionsLane** | *(separate lane)* | Community/partner extensions. Classify per item as KEEP/PORT/REWRITE/DROP/DEFER before merge. | Extensions repo | TBD | separate lane | audit and classify |

---

## 4. Frozen Components

These four components are **stable and should not absorb additional product scope**:

- **Harvester** — PLACSP fetch, score, enrich, merge. Closed.
- **Merger** — lifecycle-safe scheduled merge orchestrator. Closed.
- **RunReporter** — operational classifier and machine-readable report. Closed.
- **RegressionHarness** — offline fixture-driven regression suite. Closed.

Bugs may be fixed; new responsibilities must not be added without a deliberate
architecture decision.

---

## 5. Document Stack

The document pipeline is **a distinct layer from the licitaciones harvester**.
It is not "Fetcher 2" in the sense of a second harvester iteration.

```
DocIndexer      discovers document links from detail pages       → f2a/1 manifest
LinkResolver    resolves/verifies URLs, MIME, content-type       → f2b/1 manifest
DocEvidenceChain  consolidates, gates, plans, applies documents[] → production update

DocReader       (not built) reads/extracts document contents     → content sidecar
Appendix        (not built) per-licitación document intelligence → Apéndice UI
```

The inventory layer (DocIndexer → LinkResolver → DocEvidenceChain) is
**installed**.  As of p192: 3,211 records carry `documents[]`, 19,574 documents
exist, 8,316 confirmed `application/pdf`.

The content layer (DocReader → Appendix) is **the true missing product layer**.

---

## 6. StatsEngine vs BarometerEngine

| | StatsEngine | BarometerEngine |
|---|---|---|
| Nature | Descriptive analytics | Interpretive signals |
| Output | Counts, distributions, timelines | Opportunity / risk / pressure scores |
| UI label | Estadísticas | Barómetro |
| Status | Installed (partial) | Not built |

These are **not the same product**.  StatsEngine is a reporting layer;
BarometerEngine is an intelligence layer.  Do not merge their roadmaps.

---

## 7. Source Health

**Status: PAUSED SAFELY (p192 decision)**

Source health (freshness monitoring, outage detection per source) is not
required by the current runtime.  No component depends on it.  Reopen only if
source-freshness or outage observability becomes product-critical.

---

## 8. Extensions Lane

**Status: SEPARATE LANE — no blind merge**

Extensions live in their own lane.  Before any merge into the main pipeline,
classify each extension item as one of: `KEEP` / `PORT` / `REWRITE` / `DROP` /
`DEFER`.  Do not merge extensions wholesale without this audit.

---

## 9. Next Roadmap

In priority order:

1. **Doc inventory verification** — confirm document[] coverage, surface gaps
2. **DocReader prototype** — fetch + extract content from confirmed PDFs
3. **Appendix sidecar/schema** — define per-licitación intelligence schema
4. **UI doc-intel panel** — surface DocReader/Appendix output in the UI
5. **Stats/Barómetro redesign** — separate and deepen both layers
6. **Extensions port** — audit and classify extensions lane items

---

*Generated by p193. Registry: `tools/fetcher_architecture_registry.json`*
