# ADG_EXTENSIONS_028 — Map Taxonomy Closure

**Version:** v0.1.3.1
**Status:** CLOSED / TAXONOMY ONLY / NOT IMPLEMENTED
**Mode:** PRODUCT_HARDENING / MAP_TAXONOMY
**Branch:** extensions
**Worktree:** K:/DEVKIT/projects/adg-ops/adg-ops_extensions
**Source basis:** TXT 092 feedback audit + TXT 093 architecture closure
**Git write operations:** FORBIDDEN to Claude CLI — operator performs all staging and commits
**Date:** 2026-05-23
**Implementation status:** DOC ONLY
**Source/data status:** NO MAP SOURCE FILES TOUCHED IN TXT 094

---

## 1. Purpose

This document closes the map taxonomy distinction for future product work in ADG Extensions.

It defines:
- the conceptual split between `mapa_licitaciones` and `mapa_socios`,
- the locked file/route naming convention,
- the physical route status of each concept,
- the privacy and gate constraints on `mapa_socios`,
- and the relationship to the future Directorio prehub.

**This document does NOT:**
- rename or edit `mapa.html` or any other active surface
- create `mapa-socios.html`
- authorize any map source implementation
- contain member data, socios names, or any private information

---

## 2. Locked Naming Convention

As decided in TXT 093 (D093-1):

| Layer | Convention | Example |
|---|---|---|
| HTML file | `kebab-case` | `mapa-socios.html` |
| Conceptual / taxonomy ID | `snake_case` | `mapa_socios`, `mapa_licitaciones` |
| DOM card `id=` | `kebab-case` | `card-mapa-socios` |
| `data-module-id` | `kebab-case` | `mod-mapa-socios` |

This is consistent with the existing repo pattern:
- Files: `oportunidades-practicas.html`, `oportunidades-freelancers.html` (kebab)
- DOM IDs: `card-licitaciones`, `mod-laus-tracker` (kebab)
- JSON / SQL: `snake_case`

---

## 3. `mapa_licitaciones`

| Attribute | Value |
|---|---|
| Conceptual / taxonomy ID | `mapa_licitaciones` |
| Existing physical route | `mapa.html` |
| Module ID (registry) | `mod-mapa-diseno` (existing) — annotated as `mapa_licitaciones` context |
| Context | Procurement / licitation map: PLACSP licitaciones data, Leaflet.js, 17 CCAA, territorial map |
| Status | **Active surface — IMPLEMENTATION HOLD** |
| Rename authorized? | **NO** — `mapa.html` stays as `mapa.html` |
| Source edit in TXT 094? | **NO** — not touched |
| Nav tab target | `href="./mapa.html"` in all shells — licitaciones map context; no change |

**Hard rule:** `mapa.html` must never be renamed. The taxonomy concept `mapa_licitaciones` is a documentation label for the existing active surface. It does not imply a file rename or route change of any kind.

---

## 4. `mapa_socios`

| Attribute | Value |
|---|---|
| Conceptual / taxonomy ID | `mapa_socios` |
| Future physical route candidate | `mapa-socios.html` |
| Module ID (future) | `mod-mapa-socios` |
| Context | Directorio / member map: socios locations, professional community context |
| Privacy | **Privacy-sensitive** — no member names, no profiles, no real socios data |
| Status | **Future — NOT CREATED in TXT 094** |
| Created in TXT 094? | **NO** |
| Creation gate | Requires: Directorio privacy/legal gates cleared (Contract 023, 11 gates) OR explicit shell-only authorization by operator |

**Hard rule:** `mapa-socios.html` must NOT be created until either:
- All 11 Directorio privacy/legal gates (Contract 023) are cleared, OR
- The operator explicitly authorizes a shell-only creation with no member data

Any future `mapa-socios.html` must contain zero member data — no names, no profiles, no real locations. Shell description only.

---

## 5. Directorio Relationship

The future Directorio prehub (when privacy gates are cleared) should include two columns:
- **Column 1:** Directorio de socios
- **Column 2:** Mapa

The Mapa column in the Directorio prehub refers conceptually to `mapa_socios` — not to the existing `mapa.html` (`mapa_licitaciones`).

**Current state:**
- `directorio.html` does NOT exist — blocked by 11 privacy/legal gates (Contract 023)
- `mapa-socios.html` does NOT exist — deferred to Directorio gate closure
- No `directorio.html` creation in TXT 094

---

## 6. Active Surface Holds

The following active surfaces are implementation-hold and were NOT touched in TXT 094:

| File | Taxonomy context | Status |
|---|---|---|
| `mapa.html` | `mapa_licitaciones` | Active surface — HOLD |
| `recursos.html` | Recursos + Calculadora | Active surface — HOLD |
| `estadisticas.html` | Estadísticas Forense + Barómetro | Active surface — HOLD |
| `barometro.html` | Barómetro (tombstone redirect) | Active surface tombstone — HOLD |
| `licitaciones.html` | Observatorio de Licitaciones | Active surface — HOLD |

**"Guía de licitaciones para diseñadores"** migration from `licitaciones.html` → `recursos.html` is accepted as product direction but blocked until active-surface reopen. Not implemented in TXT 094.

---

## 7. Future Reopen Paths

| Path | Condition |
|---|---|
| `mapa_socios` shell (`mapa-socios.html`) | Directorio privacy gates cleared (Contract 023, all 11) OR explicit shell-only operator authorization; no member data ever |
| `directorio.html` creation | All 11 Directorio privacy/legal gates closed; ADG-FAD authorization |
| `mapa_licitaciones` planning audit | Active-surface reopen required; separate TXT audit prompt |
| Recursos prehub (incl. Guía migration) | Active-surface reopen required; separate TXT audit + IMP prompt |
| Estadísticas/Barómetro prehub | Active-surface reopen required; separate TXT audit + IMP prompt |
| Data / forms / provider / capture | All gates closed per module; never without explicit operator authorization |
| Private / member / support data | Permanently prohibited without contract |

---

## 8. Brújula / ROADMAP PRÓXIMO

- **TXT 094** ← CURRENT: Product hardening batch 1 — prehub card grammar + map taxonomy closure
- **TXT 095** → NEXT: Post-batch validation + visual/browser smoke audit
- **TXT 096** → DECISION: Next prehub/product-hardening batch — Recursos / Laus split / Directorio + `mapa_socios` / Estadísticas-Barómetro / roadmap copy
- **COMPLETE** — Oportunidades PREHUB Layer 3 (hub card + parent shell + 3 child shells)
- **COMPLETE** — Prehub card grammar hardening (`.prehub-*` CSS family, TXT 094)
- **COMPLETE** — Map taxonomy closure (this document, TXT 094)
- **HOLD** — `mapa.html` / `mapa_licitaciones` source (active surface)
- **HOLD** — `mapa-socios.html` / `mapa_socios` (Directorio gates)
- **HOLD** — `directorio.html` (11 privacy/legal gates)
- **HOLD** — Member / private / support data
- **HOLD** — Active surfaces: Licitaciones / Estadísticas / Recursos / Mapa / Barómetro
- **HOLD** — Data / listings / forms / provider / capture
- **HOLD** — no `git add .` ever
