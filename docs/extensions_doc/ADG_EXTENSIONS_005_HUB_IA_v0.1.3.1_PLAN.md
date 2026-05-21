# ADG EXTENSIONS — FICHA 005 — HUB IA PLAN

Version: v0.1.3.1  
Status: PLAN / NOT IMPLEMENTED  
Mode: PLAN_MIN  
Branch: extensions  
Visible nav label: ADG+  
Internal name: ADG Extensions  
Output path: `K:/DEVKIT/projects/adg-ops/extensions/ADG_EXTENSIONS_005_HUB_IA_v0.1.3.1_PLAN.md`  
Implementation status: NOT ACTIVE — Phase 2 not yet authorized  
Contract source: `adg_extensions_prompt_002_v0.1.3.1_hub_ia_plan.txt`  

---

## Phase 0 Discovery Findings

The following issues were found in the current `index.html` during the read-only inspection. They are documented here and must be corrected in Phase 2.

| Location | Current value | Correct value | Source |
|---|---|---|---|
| Directorio home-card tag | "Esperando datos" | "Legacy / partial" (or equivalent public label) | Ficha 002, C1 correction in Batch 1.3 |
| Bolsa de Prácticas home-card tag | "Google Forms" | Remove — provider not assumed | Batch 1.3.1 exits this assumption explicitly |
| Alertas home-card tag | "Formspree" | Remove — provider not assumed | Batch 1.3.1 exits this assumption explicitly |
| roadmap-mini F7–8 | "Alertas email · Directorio escuelas" | "Directorio escuelas" is not documented in any ficha | Undocumented item — must not be carried forward until a ficha exists |

Additionally: the app's internal roadmap numbering (F3=Recursos, F4=Mapa, F6=Barómetro) overlaps numerically with ADG Extensions phases 3, 4, 6 (reserved/unassigned). These are two separate numbering systems. The app roadmap is delivery history for active surfaces; ADG Extensions phases are planning positions for future modules. They should not be conflated.

---

## 1. PURPOSE

The ADG+ hub is the central access point to the ADG Extensions module layer.

It is:
- a navigable overview of all current and future ADG Extensions
- a static IA shell in its first phase
- a way to show active, in-progress, and future modules without overclaiming their maturity
- the primary exit point from the main nav to any non-Licitaciones surface or upcoming capability

It is not:
- a working product module itself
- a claim that future modules are active
- a replacement for existing live surfaces (those remain at their own pages)
- a backend-driven registry or app shell

The hub communicates the ADG platform direction honestly. Modules that do not exist appear only as grey disabled stubs. No module should look real before it is real.

---

## 2. NAMING MODEL

| Context | Value |
|---|---|
| Visible nav label | ADG+ |
| Internal system name | ADG Extensions |
| Page title (h1) | ADG Extensions |
| Page subtitle | Módulos, servicios y capacidades de la plataforma ADG |
| Alt page title option | Plataforma ADG |
| Documentation family name | ADG Extensions (unchanged) |

**ADG+ is provisional.**
- It is a clean, short nav label.
- It does not imply a subscription tier or premium product.
- It is not a final brand lock. The documentation family remains "ADG Extensions."
- If a future branding decision changes this label, only the nav copy and i18n key change — no doc renaming required.

**Do not rename the documentation family.** All fichas, batch docs, and consistency reports retain "ADG Extensions."

---

## 3. ROUTE / PAGE MODEL

| Item | Value |
|---|---|
| File (Phase 2) | `extensions.html` |
| Nav label | ADG+ |
| Nav key (i18n) | `nav_ext` |
| Nav icon suggestion | `bi-grid` or `bi-layers` |

**Why `extensions.html` with a nav label of ADG+:**
The file name is internal — users never see it directly. The nav label is what users read. `extensions.html` is clean, descriptive, consistent with the documentation naming, and avoids ambiguity if a future route system is introduced. If the nav label changes, the file name does not need to change.

No route implementation occurs in this phase. Phase 2 creates the static HTML file.

---

## 4. HUB INFORMATION ARCHITECTURE

The hub page is divided into the following sections:

```
ADG+ / ADG Extensions
─────────────────────────────────────────────────────────
[1] INTRO / FRAMING
    One short paragraph: what the ADG platform is building toward.
    Tone: honest, forward-looking, not hype.

[2] SUITE ANCHOR — LIVE
    Licitaciones / Observatorio de Licitaciones
    Clearly marked as the live core module.
    Links to licitaciones.html.

[3] ADG EXTENSIONS MODULE CARDS
    All defined extensions, in phase order.
    Active or partial-legacy modules first, then future/stub.
    Parent modules before their child lanes.
    Disabled cards for anything not yet live.

[4] STATE LEGEND
    Small, unobtrusive. Explains:
    - Active
    - WIP / En desarrollo
    - Próximamente / Coming Soon
    - Esperando datos (internal; may appear as Próximamente publicly)
    - Legacy / parcial

[5] ROADMAP NOTE (optional)
    Short note only if it does not clutter. 
    If present: one line or collapsed/expandable.
    Must not duplicate the module cards above.
─────────────────────────────────────────────────────────
```

**Section ordering rationale:**
- Licitaciones is the live anchor — it must be clearly distinguished from future modules.
- Modules appear in phase order within their tier (live → legacy/partial → esperando datos → no existe nada).
- Parent modules (Oportunidades ADG) appear before their child lanes.
- The state legend anchors meaning for all card states.
- The roadmap note is optional — avoid if it duplicates the card states already visible.

---

## 5. MODULE CARD INVENTORY

### Tier 1 — Live / Core (linked, not disabled)

| Display name | Internal ref | Phase | Current state | Visible state label | Card behavior | CTA behavior | Copy direction |
|---|---|---|---|---|---|---|---|
| Observatorio de Licitaciones | — (existing surface) | Core | Activo | Activo | Clickable | → `licitaciones.html` | "Consulta, filtra y analiza los contratos públicos de diseño en España." |

Note: Licitaciones is the live core module. It is not an ADG Extension — it is the existing primary surface from which the extension layer grows. It appears on the hub as the anchor reference, clearly distinguishable from the future modules below.

---

### Tier 2 — Defined extensions (disabled / stub)

| Display name | Internal ref | Phase | Current state | Visible state label | Card behavior | CTA behavior | Copy direction | Impl. safety |
|---|---|---|---|---|---|---|---|---|
| Laus Tracker | Ficha 001 | 1 | Esperando datos | Próximamente | Disabled | None or "Próximamente" | "Historial editorial de los premios ADG Laus. Medallero, evolución anual y análisis por categoría." | Safe — stub only |
| Directorio de Socios | Ficha 002 | 2 | Legacy / partial exists | En revisión | Disabled (for new module) | None or link to legacy list if suitable | "Directorio profesional de la comunidad ADG. Estudios, freelancers, agencias y escuelas." | Safe — stub for new module; legacy link possible if clean |
| Oportunidades ADG | Ficha 003 | Parent (no number) | No existe nada as product module | Próximamente | Disabled | None or "Próximamente" | "Hub de oportunidades profesionales para la comunidad ADG. Prácticas, freelance y puestos profesionales." | Safe — stub only |
| Bolsa de Prácticas / Juniors / Talents | Ficha 003A | 5 | No existe nada | Próximamente | Disabled | None | "Oportunidades de entrada al sector para estudiantes, talentos y perfiles junior." | Safe — stub only |
| Bolsa de Freelancers | Ficha 003B | Future child lane | Not implemented | Próximamente | Disabled | None | "Oportunidades freelance curadas y revisadas por ADG." | Safe — stub only |
| Bolsa Profesional | Ficha 003C | Future child lane | Not implemented | Próximamente | Disabled | None | "Puestos profesionales seleccionados y aprobados por ADG." | Safe — stub only |
| Alertas por Email | Ficha 004 | 7 | No existe nada as ADG Extension | Próximamente | Disabled | None | "Servicio de alertas sin spam para licitaciones y oportunidades relevantes." | Safe — stub only. No Formspree/provider reference. |

**Important notes:**
- **Bolsa Profesional** is canonical. "Bolsa de Puestos Profesionales" is deprecated — must not appear in any card label or copy.
- **Phases 3, 4, 6** are reserved/unassigned. No card is assigned to these phase numbers.
- **Oportunidades ADG** is the parent of Bolsa de Prácticas, Bolsa de Freelancers, and Bolsa Profesional. On the hub, the parent card appears first, child lanes appear below or nested. They should not appear as peers of Laus Tracker or Directorio at the same visual level without a parent container.
- **Alertas por Email**: the hub card must not reference Formspree, Mailchimp, or any provider. Copy must not imply a live service.
- **Directorio de Socios**: the visible label "En revisión" reflects that something partial exists but the full module does not. The public does not need to see "Esperando datos" — that is internal.
- **Laus Tracker**: public sees "Próximamente", not "Esperando datos". Internal state is tracked in the ficha, not exposed as a UI label.

**Child lane display model:**
Oportunidades ADG and its three child lanes may be displayed as:
- One parent card + three smaller child lane cards below it (recommended for Phase 2)
- Or: one parent card that expands to show child lanes

The flat list model (all 8 cards as equal peers) should be avoided — it collapses the parent/child hierarchy.

---

## 6. STATE LABEL GRAMMAR

| State (ficha) | Internal truth | Visible public label | Card treatment |
|---|---|---|---|
| Activo | Live, working | Activo | Linked card, active indicator |
| WIP / En desarrollo | Being actively worked | En desarrollo (if shown) or Próximamente | Disabled; may use a different visual accent from Coming Soon |
| Esperando datos | Waiting for data contract/source | Próximamente | Disabled / stub — internal state not exposed publicly by default |
| Legacy / partial exists | Partial legacy exists, full module doesn't | En revisión | Disabled for new module; legacy link possible if appropriate |
| No existe nada | Nothing implemented | Próximamente | Disabled / stub — grey card, no clickable service |
| Scoped only | Has a planning doc but no deep ficha | Próximamente | Disabled / stub |
| Coming Soon | Planned/future/not active | Próximamente | Disabled / stub |

**WIP vs Coming Soon distinction:**

| Label | Use when |
|---|---|
| En desarrollo / WIP | A module is actively being built or reviewed. Something real is happening now. |
| Próximamente | A module is planned, scoped, or waiting. Nothing is being actively built. |

This distinction matters for honest communication. In Phase 2, most ADG Extensions cards will be "Próximamente" because nothing is under active construction yet. If a module enters active development, its label may change to "En desarrollo."

**Rule:** Do not show "Esperando datos" or "No existe nada" as public labels. These are internal planning states. The public label is always one of: Activo / En desarrollo / En revisión / Próximamente.

---

## 7. DISABLED / STUB BEHAVIOR

**Disabled cards must not:**
- Link to a fake service page
- Contain a form
- Submit data anywhere
- Imply an active subscription, alert, or application flow
- Load data from any API or file
- Use a CTA that sounds like the service exists ("Subscribe", "Apply", "View opportunities")

**Disabled cards may:**
- Show a grey visual treatment (`.home-card--soon` pattern already exists)
- Show a "Próximamente" or "En desarrollo" badge
- Be non-clickable (preferred)
- If clickable: open only a static explanatory section on the hub page itself — never a fake service page

**Allowed CTA copy for disabled cards:**
- "Próximamente"
- "En preparación"
- (no CTA at all — preferred for cleaner stub state)

**Allowed CTA copy for the Licitaciones anchor:**
- "Ver licitaciones →" (links to `licitaciones.html`)

**AlertasStub note:** The existing `AlertasStub` component in `shared.js` renders a coming-soon form-like UI. It is used on `alertas.html`. The hub should NOT render AlertasStub — the hub card for Alertas is a simple disabled stub card, not an interactive form placeholder.

---

## 8. RELATIONSHIP TO EXISTING index.html STUBS

**Current state of index.html stubs (Phase 0 confirmed):**
- Laus Tracker: `home-card--soon`, "Fase 1", "Esperando datos" — phase/state visible, no CTA
- Directorio: `home-card--soon`, "Fase 2", "Esperando datos" — **state mismatch** (should be "Legacy / partial")
- Bolsa de Prácticas: `home-card--soon`, "Fase 5", "Google Forms" — **provider tag must be removed**
- Alertas: `home-card--soon`, "Fase 7", "Formspree" — **provider tag must be removed**

**Recommended approach: Option A — Keep index.html cards as teasers that link to the ADG+ hub.**

The home page serves a different role from the hub — it is the first landing surface and should give a fast overview of the full suite including what is coming. The hub (ADG+) provides the full inventory with detail per module.

The recommended model:
- `index.html` keeps its four stub cards for Laus, Directorio, Bolsa de Prácticas/Oportunidades, and Alertas
- Each stub card on `index.html` links to the ADG+ hub (`extensions.html`) or to its anchor section within the hub
- The hub contains the full card inventory with state labels and copy
- `index.html` stubs are simplified teasers; the hub has the authoritative detail

**What must change on index.html in Phase 2:**
- Remove "Google Forms" tag from Bolsa de Prácticas card
- Remove "Formspree" tag from Alertas card
- Correct Directorio state tag from "Esperando datos" to "En revisión" (or equivalent)
- Add link to `extensions.html` (or its anchor) on each stub card
- Remove "Directorio escuelas" from roadmap-mini F7–8 — this item is undocumented and must not be carried forward until a ficha exists

**What stays on index.html:**
- Phase badges ("Fase 1", "Fase 2", "Fase 5", "Fase 7")
- Module names and brief descriptions
- `.home-card--soon` treatment
- roadmap-mini with corrected F7–8 text

**Option B (move detail into hub, remove from index)** and **Option C (avoid all duplication)** are deferred. They would require removing cards from the home page, which risks reducing the home page's informational value. This is a future IA decision, not Phase 2 scope.

---

## 9. RELATIONSHIP TO ALERTAS

Two separate things exist and must remain clearly distinct:

| Thing | What it is | Where it lives | Current state |
|---|---|---|---|
| `alertas.html` | Existing coming-soon stub page for the Alertas nav tab | `alertas.html` in repo | Live stub; possibly contains Formspree/form references (to be verified in Phase 3) |
| Alertas por Email ADG Extension | Future email alert service defined in Ficha 004 | Planning doc only | "No existe nada" as implemented service |

The hub card for Alertas refers to the **ADG Extension** — the future service. It must not link to `alertas.html` as if that page is the working service.

If `alertas.html` is updated in Phase 6 to be a clean stub, the hub card may optionally link to it as an informational page only — but only if `alertas.html` makes no active service claim.

**Hard rule:** No Formspree, Mailchimp, Brevo, or any provider reference on the hub card or on any page linked from it.

---

## 10. RELATIONSHIP TO ACTIVE SURFACES

The four ADGOPS_ACTIVE_SURFACES docs (Estadísticas/Barómetro, Data Vis Grammar, Recursos/Calculadora, Acerca De) are supporting context for the broader ADG OPS delivery, not part of ADG Extensions hub implementation.

| Surface | Relationship to ADG+ hub | Action in Phase 2 |
|---|---|---|
| Estadísticas / Barómetro | Not a module card in the hub. Live surface reachable via its own nav tab. | None — separate delivery stream |
| Data Vis Grammar | Cross-cutting design rule. Applies when hub cards are styled. | Apply grammar rules if chart/badge elements are used in hub cards |
| Recursos / Calculadora | Not a module card in the hub. Live surface at its own nav tab. | None — separate delivery stream |
| Acerca De | Not a module card in the hub. May link to hub when hub exists. | None — About redesign is separate |

**Future cross-linking (not Phase 2):** Once the hub exists, `about.html` may link to the ADG+ hub to explain what is coming. This is deferred to the About active-surface implementation pass.

---

## 11. PHASE 2 STATIC HUB SHELL BOUNDARY

Phase 2 may implement exactly:

**Permitted:**
- New `extensions.html` — static hub page with module cards
- All module cards appear as disabled stubs (exception: Licitaciones anchor, which is linked)
- State labels per the grammar in Section 6
- WIP vs Coming Soon visual distinction
- Theme toggle (light/dark) using existing `applyTheme()` and `data-theme` pattern
- Language switch using existing `applyI18n()` and `data-i18n` pattern
- New i18n keys in `app.js` — hub-specific labels only (nav label, module names, card copy) — minimum set only
- New CSS in `style.css` — only if existing `.home-card--soon` / `.home-tag.tag-soon` classes are insufficient; prefer reuse over new classes
- Nav update — add "ADG+" tab to all 8 existing HTML files (index, licitaciones, estadisticas, recursos, mapa, alertas, about, barometro)
- Corrections to index.html stub cards (provider tags removal, state correction, link addition) — scoped to the four stub cards only
- roadmap-mini F7–8 correction on index.html (remove "Directorio escuelas")

**Forbidden in Phase 2:**
- Any live module activation
- Any form, input, or submission path
- Any data load (no `fetch`, no JSON read, no API call)
- Any backend or server-side logic
- AlertasStub component rendered on the hub page
- Any Formspree, Mailchimp, Brevo, or provider reference
- Any Oportunidades sub-home page (Phase 5)
- Any active-surface redesign (Estadísticas, Recursos, About)
- Any route system or SPA behavior
- New JavaScript files beyond a minimal page-init IIFE (only if needed)

---

## 12. PHASE 2 FILES TO INSPECT

Before Phase 2 implementation begins, the following files must be read in full:

`index.html;licitaciones.html;estadisticas.html;recursos.html;mapa.html;alertas.html;about.html;barometro.html;style.css;app.js;shared.js`

Reason: All 8 HTML files must be read before the nav update, to confirm exact nav block structure. `style.css` must be read to confirm which card/tag classes already exist. `app.js` must be read to confirm I18N key structure before adding new keys. `shared.js` must be read to confirm AlertasStub is not accidentally invoked in the hub page.

---

## 13. PHASE 2 SMOKE CHECKS

After Phase 2 is implemented:

| Check | Pass condition |
|---|---|
| `extensions.html` loads at localhost:8080 | Page renders without JS errors |
| Nav link "ADG+" appears on all 8 pages | All 8 HTML files have the new tab; active state on extensions.html only |
| Theme toggle works | Light/dark switch applies correctly; cards render in both modes |
| Language switch works | i18n keys resolve in ES/CA/EU/GL; no raw key strings visible |
| Licitaciones card is linked and active | Clicking opens licitaciones.html; card is not grey/disabled |
| All extension module cards are visually disabled | No card implies an active service; all have "Próximamente" or equivalent label |
| WIP vs Coming Soon labels display correctly | If both states are used, they are visually distinct |
| No form or submission path exists | No `<form>`, no `fetch`, no Formspree endpoint in extensions.html |
| Alertas card does not render AlertasStub | Hub card is a simple stub, not the interactive form placeholder |
| Oportunidades parent/child hierarchy is visible | Parent card precedes child lane cards; hierarchy is readable |
| index.html stub corrections applied | "Google Forms" and "Formspree" tags removed; Directorio state corrected; links to hub present |
| roadmap-mini F7–8 corrected | "Directorio escuelas" removed from roadmap-mini |
| No "Bolsa de Puestos Profesionales" visible | Only "Bolsa Profesional" appears in card labels |

---

## 14. RISKS

| Risk | Severity | Mitigation |
|---|---|---|
| ADG+ misunderstood as final brand name | LOW | Document clearly as provisional. Only nav label. No brand rollout. |
| Hub implies extension modules are active | HIGH | Strict disabled/stub card treatment. No fake CTAs. State labels on every card. |
| Nav update across 8 hardcoded HTML files introduces errors | MEDIUM | Read all 8 nav blocks before editing. Verify each file after update. |
| Future modules overpromised in copy | MEDIUM | Card copy must be brief and non-committal. No "subscribe now" or "apply" language. |
| "No existe nada" state accidentally appears as clickable service | HIGH | Disable click on all future-module cards. No link on disabled stubs. |
| Active-surface docs (Estadísticas, Recursos, Acerca De) pulled into Phase 2 scope | MEDIUM | Phase 2 boundary is strict: hub shell only. Active-surface work is a separate stream. |
| Directorio legacy link leads to a stale/broken page | LOW-MEDIUM | Verify legacy directory URL before adding any link. Default: no link on Directorio card in Phase 2. |
| Oportunidades ADG parent/child hierarchy collapses into flat list | MEDIUM | Enforce parent card + child lane sub-cards in hub IA. Do not flatten to peers. |
| index.html corrections break other card behavior | LOW | Corrections are tag removal and link addition only. No structural changes. |
| "Directorio escuelas" added back without a ficha | MEDIUM | Hard rule: undocumented items do not appear. Needs a ficha before any reference. |

---

## 15. OPEN QUESTIONS

**No blocking questions.**

The two blocking questions from the roadmap (Q1 hub nav label, Q2 output path) are resolved per the contract:
- Nav label: ADG+ (provisional)
- Output path: `extensions/` folder

One non-blocking clarification for Phase 2:

**Q3 (non-blocking) — Directorio card link behavior:**
The Directorio de Socios card on the hub represents a module where a legacy basic directory exists but the full module does not. Phase 2 options:
- Option A: No link — card is fully disabled, legacy directory is not surfaced through the hub (cleaner, avoids implying the legacy list is the intended module)
- Option B: Optional link to legacy directory — only if the legacy URL is clean and can be presented without implying the full module exists

Recommended default for Phase 2: **Option A (no link)**. Revisit after Phase 4 legacy gap analysis confirms the legacy directory URL and its current state.

Ready for assistant audit before Phase 2 implementation prompt.

---

## 16. STOP

This is the Hub IA planning document for Phase 1.

Phase 2 (static hub shell) is not authorized until this document is reviewed and approved by the operator.

Do not implement Phase 2 from this document alone.
Do not edit any HTML, JS, or CSS file.
Do not create `extensions.html`.
Do not modify the nav in any existing page.
