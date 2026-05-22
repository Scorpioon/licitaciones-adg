# ADG_EXTENSIONS_022 — Oportunidades Process Contract

**Version:** v0.1.3.1
**Status:** PLAN / NOT IMPLEMENTED
**Mode:** CONTRACT / OPORTUNIDADES
**Branch:** extensions
**Owner scope:** ADG Extensions
**Source basis:** TXT 063 audit + TXT 064 locked decisions + extensions_doc canon
**Git write operations:** FORBIDDEN to Claude
**Activation status:** NOT ACTIVE
**Implementation status:** DOC ONLY

---

## 1. Purpose

This document defines the pre-activation process contract for Oportunidades ADG.

It does not activate Oportunidades.

It does not authorize:
- the creation of oportunidades.html
- any public routes or card link activation
- any forms or submission flows
- any data files or mock data
- any source edits to index.html, style.css, app.js, or any active surface

It exists to make future implementation process-safe, data-safe, SQL-ready, and scope-safe — so that when the operator is ready to open source implementation, the decisions, data model, and process rules are already documented and approved.

---

## 2. Current Non-Active State

| Surface | State |
|---|---|
| `card-oportunidades-adg` in index.html | Present as `extension_module` / `stub` — non-clickable `<div>`, no href |
| `data-module-id` | `mod-oportunidades-adg` |
| `data-module-state` | `stub` |
| `data-route-id` | `route-oportunidades` |
| `oportunidades.html` | Does NOT exist |
| Active form / submission flow | Does NOT exist |
| Oportunidades data file (public or mock) | Does NOT exist |
| Mock listings | Do NOT exist |

**Oportunidades is not active.**

The stub card in index.html is the correct and honest current surface. No submission flow, no form, no route, no data.

---

## 3. Locked Operator Decisions (OD1–OD16)

| ID | Decision | Status |
|---|---|---|
| **OD1** | Public self-submit deferred; manual/admin intake v1 only | LOCKED |
| **OD2** | Email-to-ADG/manual intake v1 for all lanes; no public form; Google Form reserved as future option only | LOCKED |
| **OD3** | Moderation mandatory before any publication; submission never equals publication | LOCKED |
| **OD4** | Default incoming listing status = `submitted`; `draft` = internal/admin preparation only | LOCKED |
| **OD5** | Reviewer/owner = ADG/manual operator or designated technical admin; single v1 ownership model, no per-lane complexity | LOCKED |
| **OD6** | All three lanes retained: Prácticas, Freelancers, Profesional | LOCKED |
| **OD7** | Parent process contract may be written now; Freelancers/Profesional lane-specific fields are PROVISIONAL/SCOPED; their source/data implementation is BLOCKED until deep fichas are CLOSED | ACCEPTED WITH NOTE |
| **OD8** | Contact policy = `via_adg` v1; submitter email never in public data; public_email/public_link require future approved contract | LOCKED |
| **OD9** | Auto-expire when deadline_date exists; manual expiration fallback when no deadline; deadline_date required (Prácticas), strongly recommended (Profesional), optional (Freelancers) | LOCKED |
| **OD10** | Archive hidden/admin-only v1; no public searchable archive | LOCKED |
| **OD11** | No public/submitter edits after publication v1; admin-only corrections; substantial edits require new review cycle | LOCKED |
| **OD12** | No mock listings now; future mock in data/mock/ only with is_mock:true, obviously fake, operator-requested | LOCKED |
| **OD13** | TXT 065 doc-only; no source/data changes | LOCKED |
| **OD14** | Legal/terms for submitting organizations required before public intake; pre-activation gate, not optional | LOCKED |
| **OD15** | oportunidades.html must not be created until: contract committed + schema approved + operator reopens source + card link activation approved separately | LOCKED |
| **OD16** | No active surface edits; no extensions.html; no Licitaciones/Barómetro changes; no source/data implementation | LOCKED |

---

## 4. Module Purpose and Child Lanes

### Parent module — Oportunidades ADG

Oportunidades ADG is a centralized, curated opportunity hub for the ADG design community.

**Doctrine (ADG_EXTENSIONS_003):**
> Oportunidades ADG is a curated, ADG-reviewed opportunity hub with multiple sub-boards, designed to serve the community without becoming a spammy job board, exploitative internship channel, or generic marketplace.

It is not:
- a generic job board
- an open posting wall
- a spam channel
- a marketplace with automatic publication

It uses a sub-home model: the Oportunidades parent page serves as a landing and entry point; each child lane is a distinct curated board with its own requirements.

---

### Child lanes

#### Bolsa de Prácticas / Juniors / Talents — CLOSED

**Ficha:** ADG_EXTENSIONS_003A_BOLSA_PRACTICAS_v0.1.3.1 (Status: CLOSED)

Purpose: Entry-to-sector lane supporting students, talents, and junior profiles entering the design industry.

Doctrine: This lane exists to support entry into the sector, not to exploit early-career people.

Who may submit: studios, schools, agencies, relevant entities — by contacting ADG directly by email.

ADG review is mandatory before any publication. Exploitative, unpaid-without-disclosure, or low-effort internships are excluded by the review process.

Field definitions for this lane are CONCRETE and locked. See §11A.

---

#### Bolsa de Freelancers — PROVISIONAL / SCOPED

**Ficha:** ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1 (Status: SCOPED — not CLOSED)

> ⚠️ PROVISIONAL: This lane's field definitions are candidates, not locked decisions. Source/data implementation is BLOCKED until a deep ficha is written and CLOSED.

Purpose: Curated freelance opportunity lane — connects freelance needs with ADG-reviewed opportunities.

Submission model: entities seeking freelance help submit via intake; ADG reviews and approves before publication.

This lane must never become a cheap marketplace or generic freelance board.

---

#### Bolsa Profesional — PROVISIONAL / SCOPED

**Ficha:** ADG_EXTENSIONS_003B_003C_FREELANCERS_PROFESIONALES_v0.1.3.1 (Status: SCOPED — not CLOSED)

> ⚠️ PROVISIONAL: This lane's field definitions are candidates, not locked decisions. Source/data implementation is BLOCKED until a deep ficha is written and CLOSED.

**Canonical name:** Bolsa Profesional (NOT "Bolsa de Puestos Profesionales" — deprecated).

Purpose: Selected professional opportunity lane for employment-level positions. Lower volume, higher quality criteria than internships.

Submission model: company/studio/entity submits via intake; ADG reviews and approves; only approved listings are published.

Criteria may be further refined by ADG senior board or presidency before implementation.

---

### Shared doctrine (all three lanes)

| Rule | Detail |
|---|---|
| ADG moderation | Mandatory before any publication — no exceptions |
| Submission ≠ publication | Hard rule for all lanes |
| Manual/admin intake v1 | Email-to-ADG is the v1 channel for all lanes |
| Contact mediation | Via ADG — submitter email never exposed publicly |
| Public self-submit | Deferred — not in scope until separately authorized |
| No intake technology locked | Email v1; Google Form reserved for future; no database, API, or form infrastructure yet |

### Lane-specific distinctions

| Dimension | Prácticas | Freelancers | Profesional |
|---|---|---|---|
| Eligibility target | Students / juniors / talents | Freelance-capable designers | Employment-level designers |
| Duration semantics | Internship period (weeks/months) | Project scope / timeline | Employment contract/duration |
| Remuneration semantics | Must be explicit; unpaid must be declared | Budget/rate if required by policy | Remuneration range / contract type |
| Ficha status | CLOSED | SCOPED / PROVISIONAL | SCOPED / PROVISIONAL |

---

## 5. Intake Model

**v1 intake model for all three lanes: email-to-ADG / manual intake.**

| Aspect | Rule |
|---|---|
| Who submits | Organizations, studios, agencies, schools, entities |
| Submission channel | Email to ADG (v1 default for all lanes) |
| Google Form | Reserved as future operational option only — not MVP activation |
| Public self-submit | DEFERRED — not authorized until process and privacy contract exist and operator reopens |
| Default status on receipt | `submitted` |
| No technology locked | email v1; Airtable, Google Forms, database, custom form — all future options |

**Required fields before publication:**

- Prácticas: **concrete** (see §11A)
- Freelancers: **provisional** (see §11B) — candidates, not locked; deep ficha required
- Profesional: **provisional** (see §11C) — candidates, not locked; deep ficha required

**Critical rule (ADG_EXTENSIONS_003 §7):** Do not choose the intake technology before the process/data contract is clear. This document is that contract for the parent process. Lane-specific technology must wait until lane-specific fichas are CLOSED.

---

## 6. Moderation and Approval Model

Moderation is a core product value of Oportunidades ADG — not an optional step.

| Rule | Detail |
|---|---|
| Moderation mandatory | Every listing reviewed by ADG/admin before publication |
| Submission ≠ publication | ADG review is the gateway; no automatic publish |
| Reviewer/owner v1 | ADG/manual operator or designated technical admin |
| Single v1 ownership | One admin owner for v1; no per-lane role complexity |
| Rejection/return-for-edit | Handled manually by admin in v1; rejection reason logged in admin notes |
| Re-submission | Possible after operator clears the return-for-edit; re-enters review cycle |
| Abuse/spam handling | Not yet defined for v1 since public self-submit is deferred |
| Approval log | Should later be recorded in `oportunidades_status_events` |

**Why this matters:** Allowing automatic publication would turn Oportunidades ADG into a generic job board, a spam channel, or a source of predatory internships. The review step is the product value.

---

## 7. Listing Lifecycle

### Status machine

| Status | Meaning | Entry condition |
|---|---|---|
| `draft` | Internal/admin preparation — not received from outside | Admin creates internally |
| `submitted` | Received by ADG from outside; awaiting review | Default status on external receipt |
| `under_review` | Admin assigned; review in progress | Admin assigns reviewer |
| `approved` | ADG approved; ready to publish | Admin approves after review |
| `published` | Visible on platform | Admin publishes after approval |
| `expired` | Past deadline_date or manually expired | Auto-expire or admin action |
| `archived` | Retained for record; not visible to public | Admin archives |
| `rejected` | ADG rejected submission | Admin rejects after review |
| `withdrawn` | Submitter requested removal before publication | Admin processes withdrawal |

### Transition rules

```
submitted → under_review → approved → published
published → expired    (auto when deadline_date passes, or admin manual expire)
published → archived   (admin action only)
rejected               (terminal — from under_review)
withdrawn              (terminal — from submitted, under_review, or approved)
substantial edit of published → admin withdraws → edit → new review cycle
```

### Editing after publication

- **No submitter/public edits.** Listings are locked after publication.
- **Admin-only corrections** (typos, format issues) are allowed without re-review.
- **Substantial changes** (title, terms, scope, remuneration, contact) require: admin withdraws → applies edits → re-enters review cycle.

---

## 8. Expiration and Archive Model

| Rule | Detail |
|---|---|
| Auto-expire | Triggers when `deadline_date` passes; status → `expired` |
| Manual expiration | Admin sets status to `expired` when no deadline exists or listing is stale |
| `deadline_date` — Prácticas | REQUIRED |
| `deadline_date` — Profesional | STRONGLY RECOMMENDED |
| `deadline_date` — Freelancers | Optional / case-dependent (pending deep ficha) |
| Archive visibility | Hidden / admin-only for v1 |
| Public searchable archive | NOT in v1 |
| Archiving trigger | Admin action only; expired listings do not auto-archive without admin decision |
| Retention policy | Undefined for v1; must be addressed before long-term data accumulates |

**Honest state:** When no listings exist, the platform shows an honest empty state. Stub card on index.html is the correct current surface.

---

## 9. Ownership / Admin Model

| Aspect | Rule |
|---|---|
| Initial owner | ADG/manual operator or designated technical admin |
| Ownership model | Single v1 — no per-lane splits |
| Admin authority | Can create, edit, approve, archive, reject, withdraw, expire listings |
| Automatic publishing | FORBIDDEN — admin must explicitly publish after approval |
| Submitter access | NONE post-submission; submitters have no platform account or listing management |
| Admin corrections after publication | Admin-only; logged in admin_notes |
| Substantial edits | Require re-review cycle (see §7) |
| Audit trail | Should be recorded in `oportunidades_status_events` (see §12) |
| Internal notes | Should be recorded in `oportunidades_admin_notes` (see §12) |
| Submitter contact access | Controlled; admin only; submitter_ref never in public data |

---

## 10. Public / Private Field Boundary

### Public-safe fields

Fields that may be exposed in the public listing view:

- `title`
- `lane_type`
- `organization_name`
- `location_city` / `location_region` / `location_scope`
- `modality`
- `duration_text`
- `employment_type` (where relevant — Profesional)
- `remuneration_policy`
- `remuneration_display` (human-readable only; no raw salary data)
- `description`
- `requirements`
- `contact_policy` (the policy label, not the submitter contact)
- `public_contact` (only if contact_policy allows a public method — default is via_adg)
- `deadline_date`
- `published_at`
- `expires_at`

### Private / admin-only fields

Fields that must never appear in public data or public API:

- `submitter_ref` (submitter identification — admin intake record only)
- Submitter email / personal contact (must never be stored in public listing row)
- `source_file` (import provenance)
- `listing_status` (admin-internal state machine field)
- `visibility_status` (admin-internal control)
- `source` (admin provenance field)
- `archived_at` / `created_at` / `updated_at` (admin temporal fields)
- Status transition notes from `oportunidades_status_events`
- Rejection reasons from `oportunidades_admin_notes`
- `changed_by` / admin identity
- `is_mock` / `mock_reason`

### Contact information boundary

| Policy | Meaning | Default? |
|---|---|---|
| `via_adg` | All contact mediated through ADG; no direct submitter contact exposed | YES — v1 default |
| `public_email` | A designated public contact email may be shown | NOT v1 — requires future approved contract |
| `public_link` | An external URL may be shown | NOT v1 — requires future approved contract |
| `none` | No contact method shown | For withdrawn / expired listings |

**Hard rule: Submitter email must never appear in the public listing row.** Submitter contact goes only in `oportunidades_submission_events` (admin-only table).

---

## 11. Lane-Specific Rules and Provisional Fields

### 11A — Bolsa de Prácticas (CLOSED)

Minimum required fields (locked per ADG_EXTENSIONS_003A §9):

| Field | Required? | Notes |
|---|---|---|
| title | YES | — |
| organization_name | YES | Studio / school / agency |
| location | YES | City + region at minimum |
| modality | YES | presencial / remoto / híbrido |
| duration | YES | e.g., "3 meses" |
| remuneration_policy | YES | remunerado / no_remunerado / a_convenir |
| remuneration_display | YES | Explicit; conditions must protect candidates |
| description | YES | Public listing body |
| requirements | YES | What is expected from the candidate |
| contact_method | YES | via_adg (v1) |
| deadline_date | YES | Required for this lane |
| ADG review state | YES | Internal status field |

**Unpaid disclosure:** If a position is not remunerated, `remuneration_policy = "no_remunerado"` and conditions must be stated explicitly in `remuneration_display`. No obscured or hidden unpaid internships.

---

### 11B — Bolsa de Freelancers (PROVISIONAL / SCOPED)

> ⚠️ PROVISIONAL — NOT CLOSED
>
> The following fields are candidates from ADG_EXTENSIONS_003B_003C §6. They are NOT locked decisions. Source/data implementation based on these fields is BLOCKED until a deep Freelancers ficha is written and CLOSED.

Provisional field candidates:

| Field | Status | Notes |
|---|---|---|
| title / opportunity title | Candidate | — |
| organization_name / submitting entity | Candidate | — |
| project_type / discipline_specialty | Candidate | — |
| expected_scope | Candidate | Brief description of deliverables |
| estimated_duration / timeline | Candidate | Project timeline |
| remuneration_display / budget_range | Candidate | "If allowed/required by policy" — not locked |
| location_scope / modality | Candidate | Remote / local / hybrid |
| contact_policy | Candidate | via_adg v1 default |
| deadline_date | Candidate | Optional / case-dependent |
| ADG review state | Candidate | Mandatory — same as all lanes |

**Blocking condition:** This lane cannot be implemented (no data file, no listing template, no form) until the deep Freelancers ficha closes these fields as locked decisions.

---

### 11C — Bolsa Profesional (PROVISIONAL / SCOPED)

> ⚠️ PROVISIONAL — NOT CLOSED
>
> The following fields are candidates from ADG_EXTENSIONS_003B_003C §12. They are NOT locked decisions. Source/data implementation based on these fields is BLOCKED until a deep Profesional ficha is written and CLOSED.

Provisional field candidates:

| Field | Status | Notes |
|---|---|---|
| title | Candidate | — |
| organization_name / company | Candidate | — |
| profile_type / role_level | Candidate | Junior / senior / etc. |
| discipline_specialty | Candidate | — |
| location | Candidate | — |
| modality | Candidate | presencial / remoto / híbrido |
| employment_type | Candidate | indefinido / temporal / autonomo / proyecto |
| duration | Candidate | Contract duration |
| remuneration_display / range | Candidate | Must be "clear" per ficha §10 |
| role_description | Candidate | — |
| requirements | Candidate | — |
| contact_policy | Candidate | via_adg v1 default |
| deadline_date | Candidate | Strongly recommended |
| ADG review state | Candidate | Mandatory |

**Blocking condition:** This lane cannot be implemented until the deep Profesional ficha closes these fields as locked decisions.

---

## 12. SQL-Ready Table Model

**Registry-compatible dataset ID:** `ds-oportunidades-listings`

No tables are implemented. This section defines the future data model for when the operator approves implementation.

---

### Table A: `oportunidades_listings`

**Purpose:** Master listing record — one row per opportunity posting across all lanes.
**dataset_id:** `ds-oportunidades-listings`
**Primary key pattern:** `oport-{lane_prefix}-{org_slug}-{YYYYMMDD}` (lane prefixes: `prac-` / `free-` / `prof-`)

| Field | Type | Public | Required | Notes |
|---|---|---|---|---|
| `id` | string | YES | YES | Stable PK |
| `title` | string | YES | YES | — |
| `lane_type` | enum | YES | YES | practicas \| freelancers \| profesional |
| `organization_name` | string | YES | YES | — |
| `location_city` | string | YES | NO | — |
| `location_region` | string | YES | NO | CCAA / province |
| `location_scope` | enum | YES | YES | local \| regional \| national \| remote |
| `modality` | enum | YES | NO | presencial \| remoto \| hibrido (Prácticas: required) |
| `duration_text` | string | YES | NO | Free text e.g. "3 meses" |
| `employment_type` | enum | YES | NO | Profesional only — see vocab §13 |
| `remuneration_policy` | enum | YES | YES (Prácticas) | remunerado \| no_remunerado \| a_convenir |
| `remuneration_display` | string | YES | NO | Human-readable; no raw salary number |
| `description` | string | YES | YES | Public listing body |
| `requirements` | string | YES | NO | — |
| `contact_policy` | enum | YES | YES | via_adg \| public_email \| public_link \| none |
| `public_contact` | string | YES | NO | Only if contact_policy ≠ via_adg |
| `deadline_date` | ISO date | YES | NO | Required (Prácticas); strongly recommended (Profesional) |
| `listing_status` | enum | NO | YES | Admin-only state machine — see vocab §13 |
| `visibility_status` | enum | NO | YES | Admin-only — private \| public \| archived \| hidden |
| `source` | enum | NO | YES | email \| form \| admin \| mock |
| `source_file` | string | NO | NO | Import provenance |
| `submitted_at` | ISO datetime | NO | YES | — |
| `published_at` | ISO datetime | YES | NO | — |
| `expires_at` | ISO datetime | YES | NO | Derived from deadline_date |
| `archived_at` | ISO datetime | NO | NO | — |
| `created_at` | ISO datetime | NO | YES | — |
| `updated_at` | ISO datetime | NO | YES | — |
| `is_mock` | boolean | NO | YES | Default false |
| `mock_reason` | string | NO | NO | Required if is_mock = true |

**Note:** Submitter email / personal contact must NEVER appear in this table. Goes only in `oportunidades_submission_events`.
**Foreign keys:** lane_type → oportunidades_lanes
**Mock policy:** No mock rows in `data/public/`. Future mock rows in `data/mock/` only with `is_mock:true`, obviously fake org names, operator-requested.

---

### Table B: `oportunidades_lanes`

**Purpose:** Static registry of the three child lanes.
**Primary key pattern:** `oport-lane-{slug}`

| Field | Type | Notes |
|---|---|---|
| `id` | string | oport-lane-practicas / oport-lane-freelancers / oport-lane-profesional |
| `lane_type` | enum | practicas \| freelancers \| profesional |
| `display_name_es` | string | e.g., "Bolsa de Prácticas / Juniors / Talents" |
| `status` | enum | active \| draft \| stub |
| `ficha_status` | enum | closed \| scoped \| draft |
| `notes` | string | — |

**Mock policy:** Static reference data — no mock rows.

---

### Table C: `oportunidades_submission_events`

**Purpose:** Tracks intake events per listing. Entirely admin-only — never exposed in public API or `data/public/`.
**Primary key pattern:** `oport-sub-evt-{listing_id}-{seq}`

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable PK |
| `listing_id` | string | FK → oportunidades_listings |
| `event_type` | enum | received \| acknowledged \| assigned_reviewer \| returned_for_edit \| approved \| rejected |
| `event_at` | ISO datetime | — |
| `submission_channel` | enum | email \| form \| admin |
| `submitter_ref` | string | PRIVATE — admin only; submitter contact/ID; never in public JSON |
| `notes` | string | Admin intake note |

**Public/private boundary:** ENTIRELY PRIVATE.
**Mock policy:** No mock rows.

---

### Table D: `oportunidades_status_events`

**Purpose:** Immutable audit log of every `listing_status` transition. Admin-only.
**Primary key pattern:** `oport-status-evt-{listing_id}-{seq}`

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable PK |
| `listing_id` | string | FK → oportunidades_listings |
| `from_status` | enum | Previous listing_status value |
| `to_status` | enum | New listing_status value |
| `changed_by` | string | Admin identifier |
| `changed_at` | ISO datetime | — |
| `reason_code` | string | Optional controlled code |
| `notes` | string | Optional free text |

**Public/private boundary:** ENTIRELY PRIVATE.
**Mock policy:** No mock rows.

---

### Table E: `oportunidades_admin_notes`

**Purpose:** Internal review, moderation, and correction notes per listing. Admin-only.
**Primary key pattern:** `oport-note-{listing_id}-{seq}`

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable PK |
| `listing_id` | string | FK → oportunidades_listings |
| `note_type` | enum | review \| rejection \| moderation \| internal |
| `content` | string | PRIVATE — never exposed in public API |
| `created_by` | string | Admin identifier |
| `created_at` | ISO datetime | — |

**Public/private boundary:** ENTIRELY PRIVATE.
**Mock policy:** No mock rows.

---

### Optional / deferred tables

| Table | Purpose | Create when |
|---|---|---|
| `oportunidades_contacts` | Contact mediation log if via_adg requires formal record | Only if via_adg volume justifies it |
| `oportunidades_sources` | Multi-channel intake metadata | Only if channel volume grows |
| `oportunidades_locations` | CCAA/province normalization | Only if location filter complexity requires it |

---

## 13. Status Vocabularies

### `listing_status`
`draft` | `submitted` | `under_review` | `approved` | `published` | `expired` | `archived` | `rejected` | `withdrawn`

### `lane_type`
`practicas` | `freelancers` | `profesional`

### `submission_source`
`email` | `form` | `admin` | `mock`

### `moderation_status`
`pending` | `under_review` | `approved` | `rejected` | `returned_for_edit`

### `visibility_status`
`private` | `public` | `archived` | `hidden`

### `contact_policy`
`via_adg` | `public_email` | `public_link` | `none`

### `location_scope`
`local` | `regional` | `national` | `remote` | `international`

### `employment_type` (Bolsa Profesional only)
`indefinido` | `temporal` | `autonomo` | `proyecto`

### `remuneration_policy`
`remunerado` | `no_remunerado` | `a_convenir`

---

## 14. Mock Data Policy

- Mock oportunidades listings are **NOT ALLOWED** until the process/data contract is approved by operator and operator explicitly requests them.
- Fake real companies, studios, schools, people, salaries, or offers are **ABSOLUTELY FORBIDDEN.** No exceptions.
- No mock rows in `data/public/` under any circumstances.
- If future UI testing ever requires mock rows, all of the following must be true:
  - Location: `data/mock/` only — never `data/public/`
  - `source: "mock"`
  - `is_mock: true`
  - `mock_reason` required (non-empty string)
  - Organization names must be obviously fake (e.g., "Estudio de Prueba SA", "Empresa Ejemplo SL")
  - Contact: `contact_policy: "via_adg"` or `public_contact: "contacto@example.com"` only
  - Operator must explicitly request the mock rows in a prompt
- **Honest empty state is correct and preferred now.**

---

## 15. Active Surface Boundaries

The following are active surfaces. No source edits authorized by this contract.

| Surface | Status | Rule |
|---|---|---|
| Licitaciones / Observatorio | Active surface | OUT OF SCOPE |
| Estadísticas Forense | Active surface | OUT OF SCOPE |
| Recursos + Calculadora | Active surface | OUT OF SCOPE |
| Mapa del Diseño | Active surface | OUT OF SCOPE |
| Barómetro del Sector | Active surface | OUT OF SCOPE |

---

## 16. Implementation Blockers / Pre-Activation Gates

The following must be completed before any source/data implementation can begin:

1. **This process contract must be committed** — operator stages and commits ADG_EXTENSIONS_022.
2. **Schema must be approved** — table model in §12 must be reviewed and explicitly approved.
3. **Freelancers deep ficha must be CLOSED** — before any Freelancers lane-specific data, fields, or UI.
4. **Profesional deep ficha must be CLOSED** — before any Profesional lane-specific data, fields, or UI.
5. **Legal/terms for submitting organizations** — required before public intake is opened; pre-activation gate.
6. **Contact policy must remain `via_adg`** — until future approved contract allows public_email or public_link.
7. **Admin ownership must be confirmed** — named person/role must be designated before submission intake is opened.
8. **oportunidades.html source scope must be reopened by operator** — requires explicit operator authorization.
9. **Card link activation must be separately approved** — adding href to card-oportunidades-adg requires explicit authorization.
10. **No mock data** — until operator explicitly requests it following the mock policy in §14.
11. **No public self-submit** — until an intake form/process/privacy contract is separately approved.

---

## 17. Explicitly Out of Scope

The following are explicitly out of scope for this contract and for the current ADG Extensions branch:

- Creating `oportunidades.html`
- Activating `card-oportunidades-adg` (adding href, changing div to a)
- Creating any data file for oportunidades (public or mock)
- Creating mock listings
- Adding any form or submission flow
- Public self-submit of any kind
- Editing any active surface (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro)
- Resurrecting `extensions.html` (PERMANENTLY PROHIBITED)
- Directorio de Socios data/privacy implementation
- Alertas activation or email capture
- Implementing Freelancers or Profesional lane-specific source/data before deep fichas are CLOSED
- Implementing any subhub route not separately authorized

---

## 18. Next Steps

**Recommended next TXT:** `TXT 066_audit` — choose next lane: Directorio data/privacy audit OR branch close readiness audit.

Do not recommend source implementation until this contract document is reviewed and committed by operator.

After operator commits this document (suggested commit message: `ADG Extensions write Oportunidades process contract doc`), the branch holds two committed contract documents:
- ADG_EXTENSIONS_021 — Alertas Consent + Delivery Contract
- ADG_EXTENSIONS_022 — Oportunidades Process Contract (this document)

---

## 19. ROADMAP PRÓXIMO

| TXT | Type | Module | Scope |
|---|---|---|---|
| **065** | `_imp` | **Oportunidades** | **CURRENT** — write this process contract doc |
| **066** | `_audit` | Next lane | Choose next: Directorio data/privacy audit OR branch close readiness audit |
| **067** | `_audit` | Directorio or close | Directorio data/privacy contract audit OR final branch close report |
| **068** | `_imp` (if applicable) | Directorio or close | Write Directorio contract doc OR close branch |

**HOLD — Oportunidades source/subhub:** oportunidades.html and all data files blocked until this contract is committed and operator reopens source scope (see §16)
**HOLD — Freelancers/Profesional implementation:** lane-specific source/data blocked until deep fichas are CLOSED
**HOLD — Directorio de Socios:** blocked by data/privacy/consent contract; member data source and ADG-FAD approval pending
**HOLD — Alertas activation:** pre-activation gates not cleared (consent text, privacy notice, legal review, provider, schema implementation)
**HOLD — Laus awards/studios/schools:** data contract pending; current shell functional and untouched
**HOLD — Active surfaces:** Licitaciones, Estadísticas, Recursos, Mapa, Barómetro — out of scope this branch
