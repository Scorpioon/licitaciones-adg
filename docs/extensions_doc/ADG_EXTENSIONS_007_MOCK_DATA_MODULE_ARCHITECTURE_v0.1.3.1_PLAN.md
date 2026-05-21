# ADG EXTENSIONS — MOCK DATA + MODULE ARCHITECTURE PLAN

**Metadata:**
- Version: v0.1.3.1 — Updated with support_copys data-readiness audit
- Status: PLAN / NOT IMPLEMENTED
- Branch: extensions
- Worktree path observed: `K:\DEVKIT\projects\adg-ops\adg-ops_extensions`
- Implementation status: NOT ACTIVE
- Git write operations: FORBIDDEN (operator commits manually)
- Last updated: 2026-05-18

---

## 0. SUPPORT_COPYS DATA-READINESS AUDIT

### Files found at `docs/support_copys/`

| File | Type | Content |
|------|------|---------|
| `laus_2016.txt` | Public source | Jury roster 2016 + edition stats + category list |
| `laus_2017.txt` | Public source | Jury roster 2017 + edition stats + category list |
| `laus_2018.txt` | Public source | Jury roster 2018 + edition stats + category list |
| `laus_2019.txt` | Public source | Jury roster 2019 + edition stats + category list |
| `laus_2020.txt` | Public source | Jury roster 2020 + edition stats + category list |
| `laus_2021.txt` | Public source | Jury roster 2021 + edition stats + category list |
| `laus_2022.txt` | Public source | Jury roster 2022 + edition stats + category list |
| `laus_2023.txt` | Public source | Jury roster 2023 + edition stats + category list |
| `laus_2024.txt` | Public source | Jury roster 2024 + edition stats + category list |
| `laus_2025.txt` | Public source | Jury roster 2025 (edition stats TBC) |
| `laus_2026.txt` | Public source | Jury roster 2026 (in-progress edition — partial) |
| `listado_socios_onlynames.txt` | Public source | Alphabetical member name list (individuals + institutions) |

All files are publicly sourced from adg-fad.org. Scraped in read-only form. No private data.

### What the Laus files contain (PUBLIC — usable)

- **Edition year** (2016–2026)
- **Edition stats** (available 2016–2024, partial for 2025–2026):
  - Total projects/participants submitted
  - Number of nationalities represented
  - Total premios awarded
  - Nit Laus attendee count
- **Jury roster per year**:
  - Juror name
  - Role/title + studio/employer
  - Category judged (varies by year — see below)
- **Category names per year** (not fully stable across editions):
  - 2016: Diseño Gráfico, Digital, Publicidad, Audiovisual, Estudiantes
  - 2024: Editorial y dir. arte, Packaging, Branding y gráfica del entorno, Com. gráfica y publicidad, Digital, Audiovisual, Aporta, Estudiantes
  - 2026: Editorial y dirección de arte, Packaging, Branding y gráfica del entorno, Comunicación gráfica, Digital, Audiovisual, Aporta, Estudiantes

### What the Laus files DO NOT contain

- **Award winners / Premiados**: The "Premiados" tab links to a separate page — NOT scraped. Winning projects, studios, award levels (Oro/Plata/Laus), clients, schools are NOT in these files.
- Project details, images, award briefs

### What the Socios file contains (PUBLIC — usable)

- **Flat alphabetical member list**: ~600+ entries
- Format: `Apellido Apellido Nombre` for individuals; plain studio/school names for institutions
- Includes: individual designers, studios, agencies, schools, universities
- **Names only** — no disciplines, city, CCAA, member type classification, member since date, contact info

### What the Socios file does NOT contain

- Discipline tags, specialties
- Geographic data (city, CCAA)
- Member type classification (individual/studio/school)
- Member since date
- Contact information (email, phone, website)
- Profile photos

### Three-Tier Data Classification

| Tier | Label | Definition | Examples |
|------|-------|------------|---------|
| A | **public-source** | Real data from public ADG sources — label as `"source":"adg-public"` | Jury rosters, edition stats, member names |
| B | **mock** | Fabricated records where no real data available — label as `"source":"mock"` | Award winners, member profiles with disciplines/city |
| C | **reserved** | Schema fields confirmed but no source yet — `null` or omitted | Winning project images, member contact |

This distinction must be maintained in all data files, UI badges, and code comments.

---

## 1. EXECUTIVE VERDICT

**READY FOR LIMITED MOCK IMPLEMENTATION AFTER PREWRITE**

- Phase 2R-2 (`index.html` rework) is written but NOT committed — `M index.html` in git status; operator must commit before module work begins
- Phase 2R-3 (delete `extensions.html`, clean style.css ext blocks) is also pending
- Plan artifact `ADG_EXTENSIONS_007_...PLAN.md` did NOT exist before this write — now created
- **Laus readiness upgraded**: Real public jury data + edition stats now available for 2016–2026; winners/projects still pending
- **Directorio partially unblocked**: Public member name list available for name-only prototype; profile fields (disciplines, city, type) still governance-blocked
- Alertas and Oportunidades: unchanged — mock only, no provider activation
- Laus Tracker remains the recommended first implementation slice — now backed by real public data instead of pure mock
- Licitaciones/Observatorio remains live core data — not in mock scope

---

## 2. BRANCH / WORKTREE / DIFF CHECK

| Field | Value |
|-------|-------|
| Required worktree | `K:\DEVKIT\projects\adg-ops\adg-ops_extensions` |
| Required branch | `extensions` |
| git status | `M index.html` (Phase 2R-2 written, not committed) · `?? .claude/` · `?? docs/...` |
| git diff --stat | index.html only — all source files clean |
| Last commit | `ad553b4` — ADG Extensions Phase 2R-1 remove ADG+ nav tab |
| Phase 2R-2 | Written to index.html, NOT committed |
| Phase 2R-3 | NOT executed — extensions.html still exists; style.css ext blocks still present |
| **SAFE** | YES for read and plan; operator must commit 2R-2 before 2R-3 proceeds |

---

## 3. MOCK DATA DOCTRINE

1. Mock data must be 1:1 with visible UI fields — every key must map to a rendered element or an explicitly reserved future field
2. Mock data must be replaceable by real data without UI rename — field names are final; UI labels may differ from keys
3. **Three-tier labeling is mandatory** — every data record must carry a `source` field: `"adg-public"` (Tier A), `"mock"` (Tier B), or reserved/null (Tier C)
4. All mock/fixture files must be marked `/* MOCK/FIXTURE — NOT PRODUCTION DATA */` at file top
5. UI must show a "Demo" badge on any section where Tier B mock records are rendered; no badge required for Tier A public-source records
6. No provider or service is implied by any data — no email backend, no API endpoint, no database
7. No fake submissions — no form that sends anywhere, no subscribe button that fires a request
8. No real personal data beyond what is already publicly listed on adg-fad.org
9. No sensitive data — no DNI, no phone numbers, no private addresses, no email addresses
10. IDs must be stable and semantic: `laus-jury-2024-001`, `socio-est-001`, `op-prac-001`
11. All module containers must carry `data-mock="true"` or `data-source="adg-public"` attribute hooks
12. Mock data files live in `data/mock/` — distinct from `data/` (live data path)

---

## 4. CURRENT UI FIELD INVENTORY

### index.html — Home Cards

**Live cards (5):** Licitaciones, Estadísticas, Recursos+Calculadora, Mapa, Barómetro — live, not mock scope.

**Future cards (4):**
- Laus Tracker: title, desc (historial, medallero, categoría, anual, escuelas), tags: Fase 1 / Próximamente
- Directorio de Socios: title, desc (estudios, freelancers, agencias, escuelas, especialidad, ubicación), tags: Fase 2 / En revisión
- Oportunidades ADG: title, desc (Bolsa Prácticas/Juniors · Freelancers · Bolsa Profesional), tags: Fase 5 / Próximamente
- Alertas por Email: title, desc (disciplinas, territorio, sin spam), tags: Fase 7 / Próximamente

**Home card implied detail fields:**
- Laus: year, category, award level, studio/school, project name, jury roster, edition stats
- Directorio: member type, specialty disciplines, city/CCAA, website, ADG member since
- Oportunidades: sub-lane, role, company, location, posted date
- Alertas: discipline filters, territory filter, frequency, opt-in state

---

## 5. MODULE-BY-MODULE MOCK DATA MAP

### 5.1 Laus Tracker

| Field | Detail |
|-------|--------|
| Current UI surface | Home card only (`.home-card--soon`) |
| Future UI surface | Edition browser (year selector) + jury roster + edition stats + awards archive (pending) |
| **Data readiness** | **PARTIAL PUBLIC — upgraded** |
| Tier A (public-source) | Jury rosters 2016–2026, edition stats 2016–2024, category names per edition |
| Tier B (mock) | Award winners per edition (NOT in source files — must remain mock/pending) |
| Tier C (reserved) | Project images, detailed award briefs, Grand Laus detail |
| Mock entity: LausJuror | id, year, name, role, studio, category_judged, source: "adg-public" |
| Mock entity: LausEdition | id, year, edition_name, participants, nationalities, awards_count, attendees, source: "adg-public" |
| Mock entity: LausAward | id, year, category, award_level, studio_or_school, project_name, source: "mock" (pending) |
| IDs/hooks | `laus-ed-2024`, `laus-jury-2024-001`, `laus-award-2024-001` |
| Later real data source | ADG Laus archive for winners — NOT yet confirmed |
| Risks | Award winners source still unconfirmed; category taxonomy not stable across years; jury data includes real names of public professionals |

### 5.2 Directorio de Socios

| Field | Detail |
|-------|--------|
| Current UI surface | Home card only (`.home-card--soon`, "En revisión") |
| Future UI surface | Searchable directory + member ficha/detail |
| **Data readiness** | **PARTIALLY UNBLOCKED — name list available** |
| Tier A (public-source) | Member names (flat list — individuals + institutions) from listado_socios_onlynames.txt |
| Tier B (mock) | Disciplines, city, CCAA, member type, website, member since — all mock until governance |
| Tier C (reserved) | Contact info, bio, profile photo, profile claiming |
| Mock entity: DirectorioMember | id, name, member_type (Tier B), specialty_disciplines[] (Tier B), city (Tier B), ccaa (Tier B), source: "adg-public" for name / "mock" for all other fields |
| IDs/hooks | `socio-{seq}` e.g. `socio-001`; `data-member-type="estudio"` |
| Later real data source | ADG member registry (private) — governance decision required for profile fields |
| Risks | **HIGHEST PRIVACY RISK** — name list is public but enriching with disciplines/city requires governance gate; no real member profiles without ADG approval; "escuelas" listed by name but no ficha until ficha decision; member_type classification must not be inferred |

### 5.3 Oportunidades ADG (umbrella + child lanes)

| Field | Detail |
|-------|--------|
| **Data readiness** | MOCK ONLY — no public data source |
| Tier A | None |
| Tier B | All entity fields |
| child lane: Prácticas | compensation_type mandatory visible (anti-exploitation doctrine) |
| child lane: Freelancers | budget_range optional |
| child lane: Bolsa Profesional | canonical name — must not be renamed |
| Risks | Moderation workflow undefined; no provider locked |

### 5.4 Alertas por Email

| Field | Detail |
|-------|--------|
| **Data readiness** | MOCK/DEMO ONLY — no provider, no subscription |
| Tier A | None |
| Tier B | Preference profile demo records |
| Tier C | Email address, subscriber_id |
| Risks | Provider must NOT be implied; Demo badge mandatory |

### 5.5 Licitaciones / Observatorio

**Live core data surface. NOT an extension mock module. SAMPLE array in app.js (lines 309–320) is the existing fallback pattern and serves as precedent for the mock data approach.**

---

## 6. RECOMMENDED MOCK FILE STRATEGY

**RECOMMENDATION: Option C — `window.ADG_MOCK` JS fixture file**

**File:** `data/mock/adg_extensions_mock.js`

```js
/* MOCK/FIXTURE — NOT PRODUCTION DATA — ADG Extensions v0.1.3.1 */
/* Tier A records: public-source from adg-fad.org (jury, edition stats, member names) */
/* Tier B records: mock/demo — clearly labeled, not real */
window.ADG_MOCK = {
  _meta: { version: '0.1.3.1', generated: '2026-05', status: 'fixture' },
  laus: {
    editions: [...],   // Tier A — real public stats
    jury: [...],       // Tier A — real public jury rosters
    awards: [...]      // Tier B — mock until real source confirmed
  },
  directorio: {
    members: [...]     // name: Tier A / all other fields: Tier B
  },
  oportunidades: {
    practicas: { items: [...] },     // Tier B
    freelancers: { items: [...] },   // Tier B
    profesional: { items: [...] }    // Tier B
  },
  alertas: { demo_profiles: [...] }  // Tier B
};
```

**Load pattern:** `<script src="./data/mock/adg_extensions_mock.js"></script>` before module JS (synchronous, no fetch)

**Swap path to real data:**
- Replace `<script src="./data/mock/adg_extensions_mock.js">` with `await ADG_Utils.loadJSON('./data/laus.json')` (existing `loadJSON()` function in app.js)
- Same field keys; same adapter layer; no UI rename

**UI badge rules:**
- `data-source="adg-public"`: no Demo badge; sourced from public ADG data
- `data-source="mock"`: show `<span class="tag-demo">Demo</span>` badge
- `data-mock="true"` on containers for targeting

---

## 7. DATA CONTRACT LAYER

### LausEdition (Tier A)
| Category | Fields |
|----------|--------|
| Required | id, year, edition_name, participants, nationalities, awards_count, source |
| Optional | attendees_nit_laus, book_exists |
| Computed | age_years (from 2026 minus year) |
| Status | is_current_edition (boolean) |
| Provenance | source: "adg-public" |

### LausJuror (Tier A)
| Category | Fields |
|----------|--------|
| Required | id, year, name, category_judged, source |
| Optional | role, studio, is_chairman |
| Computed | display_label (name + role) |
| Provenance | source: "adg-public" |
| Privacy | Names are publicly listed by ADG; no private data |

### LausAward (Tier B — pending)
| Category | Fields |
|----------|--------|
| Required | id, year, category, award_level, studio_or_school, project_name, source |
| Optional | client, school_name (if student), special_mention_note |
| Computed | is_student (derived from school_name presence) |
| Status | published (boolean) |
| Provenance | source: "mock" until real archive confirmed |
| Privacy | No personal names — studio/school only |

### DirectorioMember
| Category | Fields |
|----------|--------|
| Required | id, name, source_name, source_profile |
| Optional (Tier B) | member_type, specialty_disciplines[], city, ccaa, website, adg_member_since |
| Computed | discipline_tags[] |
| Provenance | source_name: "adg-public"; source_profile: "mock" or "pending-governance" |
| Privacy | Name from public list; all other fields require governance |

### Oportunidades / Alertas
*(unchanged from prior plan — see §7 of original PLAN_MIN)*

---

## 8. UI 1:1 MAPPING TABLES

### 8.1 Laus Edition Browser Mapping (new — real data)

| UI Label | Data Key | Tier | Type | Example | Source |
|----------|----------|------|------|---------|--------|
| Year | `year` | A | number | `2024` | laus_2024.txt |
| Edition name | `edition_name` | A | string | `"Laus 64"` | derived |
| Participants | `participants` | A | number | `1400` | laus_2024.txt |
| Nationalities | `nationalities` | A | number | `8` | laus_2024.txt |
| Awards given | `awards_count` | A | number | `336` | laus_2024.txt |
| Nit Laus attendees | `attendees_nit_laus` | A | number | `850` | laus_2024.txt |

### 8.2 Laus Jury Roster Mapping (new — real data)

| UI Label | Data Key | Tier | Type | Example | Source |
|----------|----------|------|------|---------|--------|
| Juror name | `name` | A | string | `"Diego Etxeberria"` | laus_2024.txt |
| Role / title | `role` | A | string | `"Director de arte, Zara Man Asia"` | laus_2024.txt |
| Category judged | `category_judged` | A | string | `"Editorial y dir. arte"` | laus_2024.txt |
| Chairman flag | `is_chairman` | A | boolean | `false` | derived from text |

### 8.3 Laus Award Archive Mapping (Tier B — pending)

| UI Label | Data Key | Tier | Type | Example | Real Source |
|----------|----------|------|------|---------|-------------|
| Award year | `year` | B | number | `2024` | Future: Laus archive |
| Category | `category` | B | string | `"Packaging"` | Future: Laus archive |
| Award level | `award_level` | B | string | `"Oro"` | Future: Laus archive |
| Studio/School | `studio_or_school` | B | string | `"Estudio Dos Punts"` | Future: Laus archive |
| Project | `project_name` | B | string | `"Marca XYZ"` | Future: Laus archive |
| Client | `client` | B | string | `"Client SA"` | Future: Laus archive |

### 8.4 Directorio Member Card Mapping

| UI Label | Data Key | Tier | Type | Example | Source |
|----------|----------|------|------|---------|--------|
| Member name | `name` | A | string | `"Zoo Studio"` | listado_socios_onlynames.txt |
| Member type | `member_type` | B | string | `"estudio"` | Mock (governance pending) |
| Disciplines | `specialty_disciplines[]` | B | string[] | `["Branding"]` | Mock (governance pending) |
| City | `city` | B | string | `"Barcelona"` | Mock (governance pending) |
| CCAA | `ccaa` | B | string | `"Cataluña"` | Mock (governance pending) |
| Website | `website` | B | url | `"https://..."` | Mock (governance pending) |

### 8.5 Home Card Mapping, Oportunidades, Alertas
*(unchanged from original plan — home cards are static HTML; Oportunidades and Alertas are Tier B only)*

---

## 9. MODULE IMPLEMENTATION ORDER WITH MOCK DATA

### Updated Evaluation Matrix

| Module | UI Readiness | Real Data Available | Privacy Risk | Governance Risk | Visual/Demo Value | Order |
|--------|-------------|---------------------|--------------|-----------------|-------------------|-------|
| Laus Tracker (jury + edition browser) | High | **Yes — jury+stats 2016–2024** | Low (public data) | Low | High | **1st** |
| Laus Tracker (awards archive) | Medium | No — still pending | Low | Low | High | **1b — after data** |
| Directorio (name-only prototype) | Low | **Yes — name list** | Medium | Medium | Medium | **2nd (partial)** |
| Directorio (full profile cards) | Medium | No — governance | **Critical** | **Critical** | High | **BLOCKED** |
| Oportunidades ADG sub-home | Medium | No | Low | Medium | High | **3rd** |
| Alertas preference preview | High | No | Low | Low | Medium | **4th** |

**Laus Tracker is confirmed first.** The first implementation slice now has real public data to display (jury rosters + edition stats) — not just mock records. This significantly increases demo value and data integrity.

---

## 10. FIRST SAFE MOCK IMPLEMENTATION SLICE

**Laus Tracker — Edition Browser with Real Jury Data**

| Item | Detail |
|------|--------|
| Goal | `laus.html` — edition selector (2016–2026) + jury roster per edition + edition stats. All displayed data is Tier A (real public source). Awards archive section rendered as "Próximamente" placeholder, not fake records. |
| Shell scope | Minimal: `<title>`, `<link rel="stylesheet" href="./style.css">`, page content, back-link to `index.html`. Full shared chrome deferred. |
| Files to create | `laus.html`, `data/mock/adg_extensions_mock.js` (laus.editions + laus.jury only — Tier A), `laus.js` |
| Files to touch | `index.html` — convert Laus card `<div>` to `<a>` with `href="./laus.html"` |
| Files FORBIDDEN | `app.js`, `shared.js`, `style.css`, `extensions.html`, `data/licitaciones.json`, all other HTML |
| Data approach | `adg_extensions_mock.js` laus.editions and laus.jury populated from laus_*.txt files; labeled `source:"adg-public"` |
| UI visible result | Laus page: edition year tabs/selector; selected edition stats (participants, nationalities, awards count, attendees); jury roster cards per category; awards section shows "Premiados — Próximamente" state (NOT fake records) |
| Smoke tests | Page loads; edition selector works; jury cards render; stats display correctly; no Demo badge on Tier A content; "Próximamente" shown for awards; no fetch requests; back to index.html works |
| Risk | Low — new page, no services, no forms, no personal data beyond what ADG lists publicly; edition name derivation (e.g., "Laus 64") may need operator confirmation of naming convention |

---

## 11. FIXTURE DATA EXAMPLES

### LausEdition examples (Tier A — from support_copys)

```js
{ id:'laus-ed-2024', year:2024, edition_name:'Laus 64', participants:1400, nationalities:8, awards_count:336, attendees_nit_laus:850, source:'adg-public' },
{ id:'laus-ed-2022', year:2022, edition_name:'Laus 62', participants:1200, nationalities:9, awards_count:335, attendees_nit_laus:800, source:'adg-public' },
{ id:'laus-ed-2016', year:2016, edition_name:'Laus 56', participants:1188, nationalities:20, awards_count:205, attendees_nit_laus:550, source:'adg-public' }
```

### LausJuror examples (Tier A — from laus_2024.txt)

```js
{ id:'laus-jury-2024-001', year:2024, name:'Diego Etxeberria', role:'Director de arte, Zara Man Asia', category_judged:'Editorial y dir. arte', is_chairman:false, source:'adg-public' },
{ id:'laus-jury-2024-002', year:2024, name:'Xavier Roca', role:'Diseñador gráfico, Run', category_judged:'Packaging', is_chairman:false, source:'adg-public' },
{ id:'laus-jury-2016-001', year:2016, name:'Verònica Fuerte', role:'Diseñadora Gráfica e Ilustradora', category_judged:'Diseño Gráfico', is_chairman:false, source:'adg-public' }
```

### LausAward placeholder (Tier B — awards pending)

```js
// DO NOT DISPLAY as real records — render as "Próximamente" state until real source confirmed
{ id:'laus-award-PENDING', year:null, category:null, award_level:null, studio_or_school:null, project_name:null, source:'pending', status:'unavailable' }
```

### DirectorioMember examples (name: Tier A / profile: Tier B)

```js
{ id:'socio-001', name:'Zoo Studio', source_name:'adg-public', member_type:'estudio', specialty_disciplines:['Branding','Motion'], city:'Barcelona', ccaa:'Cataluña', source_profile:'mock' },
{ id:'socio-002', name:'Eina, Escola de Disseny i Art', source_name:'adg-public', member_type:'escuela', specialty_disciplines:['Diseño Gráfico'], city:'Barcelona', ccaa:'Cataluña', source_profile:'mock' },
{ id:'socio-003', name:'Vasava Artwors, BCN', source_name:'adg-public', member_type:'estudio', specialty_disciplines:['Branding','Editorial'], city:'Barcelona', ccaa:'Cataluña', source_profile:'mock' }
```

### Oportunidades + Alertas examples
*(unchanged from original plan — Tier B mock only)*

---

## 12. REAL DATA SWAP PLAN

1. `window.ADG_MOCK` is the fixture adapter. Real adapter: `await ADG_Utils.loadJSON('./data/laus.json')` — same `loadJSON()` function as licitaciones
2. Tier A records (jury, edition stats) → already real data; swap means structured JSON replaces the fixture inline records, keys unchanged
3. Tier B records (awards, profiles) → replace with real data source when confirmed; same keys; UI doesn't change
4. `data-source` attribute enables targeted badge logic: `if (record.source === 'mock') showDemoBadge()`
5. Award category taxonomy: must be normalized before real data arrives — category strings must match across editions and the filter UI
6. Directorio: name list is Tier A; enrichment fields are Tier B → when governance provides profile data, only the profile fields update, not the name or id

---

## 13. RISKS

| Risk | Mitigation |
|------|-----------|
| Jury names perceived as private data | These are publicly credited on adg-fad.org — no private context; label source clearly |
| Award winners not available → shown as fake records | FORBIDDEN — awards section must show "Próximamente" state, not fabricated Tier B winners |
| Directorio name list enriched with inferred data | All non-name fields must be Tier B labeled as mock, not derived from name patterns |
| Category taxonomy inconsistency across years | Map categories to a normalized set before building filter UI; document raw vs. normalized |
| Edition name derivation ("Laus 64") not confirmed | Verify ADG's numbering convention before displaying; operator must confirm |
| Directorio escuelas without ficha | School names appear in list — must NOT have clickable profile until ficha decision |
| Mock becoming perceived as real | Three-tier labeling + Demo badge system is the guard |
| CSS drift | First slice: existing tokens only; any new class requires operator approval |
| Service activation | No fetch() in fixture; window.ADG_MOCK is synchronous |
| Overbuilding | Laus first, then Directorio name-only, then Oportunidades — in that order |

---

## 14. NEXT FILES FOR IMPLEMENTATION PROMPT

First implementation slice (Laus Tracker — Jury + Edition Browser):

```
laus.html;data/mock/adg_extensions_mock.js;laus.js;index.html
```

Source files for fixture data (read-only reference):
```
docs/support_copys/laus_2016.txt;docs/support_copys/laus_2017.txt;docs/support_copys/laus_2018.txt;
docs/support_copys/laus_2019.txt;docs/support_copys/laus_2020.txt;docs/support_copys/laus_2021.txt;
docs/support_copys/laus_2022.txt;docs/support_copys/laus_2023.txt;docs/support_copys/laus_2024.txt;
docs/support_copys/laus_2025.txt;docs/support_copys/laus_2026.txt
```

Forbidden in implementation prompt:
```
app.js;shared.js;style.css;extensions.html;data/licitaciones.json;alertas.html;recursos.html;estadisticas.html;mapa.html;about.html
```

---

## 15. BLOCKING QUESTIONS

**One open item for operator before Laus implementation prompt:**

> What is the correct edition number naming convention for Laus? Files show "ADG Laus 2024" as the year name, but historically editions are also numbered (e.g., "Laus 64"). Should edition names use year only, or year + number (e.g., "Laus 64 · 2024")? This affects how `edition_name` is populated in the fixture.

Recommended answer: Operator provides the numbering baseline (e.g., "Laus 2016 = edition 56") so the series can be derived consistently.

All other questions from the original plan are resolved. Phase 2R-2 commit is pending operator action. Phase 2R-3 is pending after 2R-2.

---

## 16. STOP

This is the complete PLAN_MIN artifact with support_copys data-readiness update. No implementation. No source edits. No commits.

Hard rules maintained:
- No git add / git commit / git push
- No source writes (HTML/CSS/JS/data)
- No mock data files written from this prompt
- No real provider assumptions
- No backend assumptions
- No forms / subscriptions
- No real personal data beyond publicly listed ADG members
- Batch 1.3.1 states preserved
- Bolsa Profesional canonical name preserved
- No Google Forms / Formspree reintroduced
- No Directorio escuelas without ficha
- Licitaciones/Observatorio classified as live core — not mock scope
- Award winners NOT rendered as fake records — "Próximamente" state only until real source confirmed
