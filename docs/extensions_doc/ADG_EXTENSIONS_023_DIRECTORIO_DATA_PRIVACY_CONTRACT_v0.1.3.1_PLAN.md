# ADG_EXTENSIONS_023 — Directorio Data + Privacy Contract

**Version:** v0.1.3.1
**Status:** PLAN / NOT IMPLEMENTED
**Mode:** CONTRACT / DIRECTORIO
**Branch:** extensions
**Owner scope:** ADG Extensions
**Source basis:** TXT 067 audit + TXT 068 locked decisions + extensions_doc canon
**Date:** 2026-05-22
**Git write operations:** FORBIDDEN to Claude CLI — operator performs all staging and commits
**Activation status:** NOT ACTIVE
**Implementation status:** DOC ONLY

---

## 1. Purpose

This document defines the pre-activation data and privacy contract for Directorio de Socios.

It does **not** activate Directorio.
It does **not** authorize the creation of `directorio.html`, routes, data files, member imports, mock member data, forms, profile flows, or any source edits.

It exists to make future Directorio implementation:
- **Privacy-safe:** consent model, field visibility, and legal basis defined before any data is used
- **Consent-safe:** publication gates and opt-in requirements locked before any profile is shown
- **SQL-ready:** table model, ID patterns, and status vocabularies defined before schema is built
- **Scope-safe:** explicit blockers and out-of-scope rules prevent premature activation

This contract must be committed before any further Directorio work is approved. No implementation may proceed until all pre-activation gates listed in Section 16 are cleared and the operator explicitly reopens source scope.

---

## 2. Current Non-Active State

| Check | Status |
|---|---|
| `card-directorio-socios` in `index.html` | EXISTS — `<div>` stub, non-clickable, no `href` |
| `data-module-id` | `mod-directorio-socios` |
| `data-module-kind` | `extension_module` |
| `data-module-state` | `stub` |
| `data-route-id` | `route-directorio` |
| `directorio.html` | DOES NOT EXIST |
| Active form/profile flow | NONE |
| `adg_members` data file | DOES NOT EXIST — `ds-adg-members` is future/blocked |
| Raw member data read | NOT READ — `listado_socios_onlynames.txt` access forbidden |
| Mock member data | NONE |
| Directorio module | NOT ACTIVE |

**Directorio is an extension module stub only. It must not be activated until this contract is reviewed, committed, and all pre-activation gates are cleared.**

---

## 3. Locked Operator Decisions

The following decisions were locked in TXT 068 and are the authoritative basis for this contract.

| ID | Decision | Status |
|---|---|---|
| **DD1** | No profile may appear publicly by default. Individual/freelance profiles require explicit opt-in before any public visibility. Studio/school/company/entity profiles may be admin-approved from confirmed public sources **only if ADG/legal approval exists**. All future records default `visibility_status: "hidden"`. | LOCKED (two-tier rule) |
| **DD2** | Do not import or read raw member lists. No import from `docs/support_copys/listado_socios_onlynames.txt`. No enumeration of member names. No `adg_members` seed data. | LOCKED |
| **DD3** | Default visibility for any future row: `hidden` / unpublished. No automatic public visibility after import or creation. | LOCKED |
| **DD4** | Unclaimed profiles are hidden by default. Admin-curated entity profiles from approved public source are allowed only with ADG/legal approval. Unclaimed individual/freelance profiles are not public in MVP. | LOCKED |
| **DD5** | Profile claiming is deferred as self-serve functionality. MVP = admin-curated / admin-mediated only. Claiming may be modeled in schema but must not be implemented. | LOCKED |
| **DD6** | MVP candidate profile types: studio / agency / company + school / institution. Freelance profile: MVP candidate with explicit opt-in only. Individual ADG member profile: deferred or explicit opt-in only. Collective / other entities: deferred. | LOCKED |
| **DD7** | `public_email` is forbidden by default. May be shown only with explicit opt-in and a defined `public_contact` policy. Submitter/member private email must never be public. | LOCKED |
| **DD8** | `phone` is fully forbidden/private for public MVP. Do not include phone in any public field set. | LOCKED |
| **DD9** | `website` and `portfolio_url` are allowed only if member-provided or confirmed public source. Social links are deferred or opt-in only. Do not scrape or infer URLs. | LOCKED |
| **DD10** | Specialty/discipline filter is allowed later, but only after a controlled vocabulary is approved. Use closed vocabulary first. No free-tag explosion. | LOCKED |
| **DD11** | No mock member data now. No fake real people. No mock rows in `data/public/`. Future UI mock only if explicitly operator-approved: `data/mock/` only, `source:"mock"`, `is_mock:true`, `mock_reason` required, obviously fake/test-only names, `@example.com` only. | LOCKED |
| **DD12** | Initial admin owner: ADG/manual operator or designated technical admin. Single v1 owner model. No self-serve accounts in MVP. | LOCKED |
| **DD13** | A correction/removal channel is mandatory before activation. Initial channel: ADG email/manual request. Erasure/anonymization must be a pre-activation gate, not optional. | LOCKED |
| **DD14** | Legal/privacy review is required before any public profile publication. This is a pre-activation gate. | LOCKED |
| **DD15** | TXT 069 is doc-only. No source/data changes. | LOCKED |
| **DD16** | `directorio.html` must not be created until: contract doc committed + schema approved + operator explicitly reopens source implementation + card link activation separately approved. | LOCKED |
| **DD17** | No active surface edits. No `extensions.html`. No Licitaciones changes. No Barómetro changes. No source/data implementation in this branch. | LOCKED |

---

## 4. Module Purpose

**What Directorio de Socios is:**
A public professional ADG member directory — searchable, navigable, and profile-oriented. The intended community layer of the ADG platform: studios, freelancers, agencies, and schools discoverable by the design community.

**Who it serves:**
- ADG members who want to be visible and findable as professionals
- Design community members seeking professionals by specialty or location
- Partners and clients seeking ADG-affiliated design professionals

**What problem it solves:**
The existing legacy directory is an unstructured long list — not browsable, not searchable, no specialty filters, no profile detail, no location model. The future module replaces this with a structured, navigable, filterable directory surface.

**What it must not become:**
- A commercial marketplace or lead-generation machine — no aggressive `contact now`, no conversion pressure
- A pure map view — the directory must stand on its own as a browsable/searchable surface
- A fake or overclaimed module before data and privacy are resolved
- A scraped database — no data may be inferred or scraped from external sources

**Relation to ADG/FAD member ecosystem:**
ADG-FAD is the data controller for member data. The association owns the membership database. Any use of member data in the new Directorio module format requires explicit authorization from ADG-FAD. The legacy directory's existence does not authorize the new module schema or the new use case.

**Why this contract is mandatory:**
Real people with professional and personal identifying data are involved. No consent record exists for the new module format. LOPD/GDPR compliance requires that new processing purposes be disclosed and authorized. Profile claiming requires identity verification and moderation design. Unclaimed profile visibility must be policy-defined before any data appears publicly.

---

## 5. Data Source Approval Model

**Source owner:**
ADG-FAD (the association) is the data controller for member data. The membership database, professional registrations, and contact details belong to the association.

**Explicit authorization required:**
Before any member data is used in this module, the following must be confirmed:
- ADG-FAD board or data controller authorization to use member data in the new Directorio format
- Clarification of which fields are available for the public directory vs. internal-only
- Approved export/transfer format if any import is ever authorized
- Confirmation of which fields are already "public" (e.g., voluntarily published on public ADG site) vs. fields requiring fresh consent

**Public source vs. private source:**

| Category | Examples | Authorization needed |
|---|---|---|
| Public source | Voluntarily published info on member's own website; publicly visible legacy directory entry (if confirmed by operator); public LinkedIn or professional profile | Lower — still requires source tracking and `source: "adg-public"` |
| Private source | Full membership database; contact details (email, phone); payment/membership status; internal CRM or spreadsheet | Full ADG-FAD authorization required |

**Why legacy references do not authorize the new module:**
The legacy list format was not the same use case as the new navigable/filterable module. New processing purpose (specialty filters, location model, profile claiming, richer data) = new legal basis required under LOPD/GDPR. Even legitimate interest must be assessed per the new use case.

**Source/provenance records required on all future import rows:**
- `source: "adg-public"` with `source_file` pointing to operator-approved export
- `import_batch` for traceability
- Consent provenance events in `adg_member_consent_events`

**What must remain unknown until operator/ADG approval:**
- Full member count and enumeration
- Contact details (email, phone)
- Membership type, membership status, or join date of individuals
- Any field not confirmed as already public in the legacy directory
- Profile images or logos not voluntarily published by members

**Raw member list: FORBIDDEN NOW.**
`docs/support_copys/listado_socios_onlynames.txt` must not be read or imported. No enumeration of member names. No `adg_members` seed data until all import gates are cleared.

---

## 6. Privacy / Publication Consent Model

**No public profile by default.**
All future `adg_members` rows must be created with `visibility_status: "hidden"`. No profile becomes public automatically after import or creation.

**Two-tier consent rule (DD1):**

| Profile tier | Publication rule |
|---|---|
| Individual ADG member / freelance profile | Explicit opt-in from the individual required before any public visibility. No exceptions in MVP unless ADG legal/privacy provides written authorization for a different basis. |
| Studio / agency / company / school / institution | Admin-curated publication from a confirmed public source is allowed — but **only with ADG/legal approval**. Must not proceed on assumption alone. |

**Unclaimed profile policy:**
- Unclaimed individual/freelance profiles: not shown publicly in MVP
- Unclaimed entity stubs (studio, school) from approved public source: may appear only with ADG/legal approval
- Default for all unclaimed profiles: `visibility_status: "hidden"`

**Correction/removal/erasure requirements (mandatory before activation):**
- A correction request channel must exist before any profile is published
- A removal request channel must exist before any profile is published
- Right to erasure (LOPD/GDPR): members must be able to request anonymization or hard delete of their data
- The process must be operational, not just designed, before activation

**Consent/provenance event logging:**
All consent events must be logged in `adg_member_consent_events` with:
- `event_type` (opt_in, opt_out, admin_approval, erasure_request, correction_request, removal_request)
- `event_at` timestamp
- `actor` (member or admin)
- `channel` (email, form, admin-manual)
- `notes`

**Legal/privacy review gates (all required before any public publication):**
1. Legal basis for publication confirmed (explicit opt-in mechanism, or formal Legitimate Interest Assessment for entity profiles)
2. Privacy notice updated to cover Directorio module and its data use
3. Opt-out/correction/erasure process designed and operational
4. ADG-FAD data controller authorization confirmed

---

## 7. Profile Types + Visibility Model

| Profile type | MVP or deferred | Personal data risk | Visibility default | Admin-curated from public source? | Notes |
|---|---|---|---|---|---|
| Studio / agency / company | MVP candidate | Lower — entity, not individual | `hidden` until admin-approved | Allowed only with ADG/legal approval | Company data may come from public sources; still requires authorization |
| School / institution | MVP candidate | LOW — institutional | `hidden` until admin-approved | Allowed only with ADG/legal approval | Institutional data, low personal risk |
| Freelance profile | MVP — explicit opt-in only | MEDIUM — individual (often sole trader) | `hidden` until explicit opt-in received | Not allowed — must opt in | Sole traders blur company/personal boundary; treat as individual |
| Individual ADG member | Deferred / explicit opt-in only | HIGH — personal data | `hidden` until explicit opt-in | Not allowed — must opt in | Highest privacy sensitivity; never unclaimed/public in MVP |
| Collective / other entity | Deferred | Varies | `hidden` | Operator decision needed | Not well-defined in docs; deferred |

---

## 8. Public / Private Field Boundary

| Field | Candidate visibility | Sensitivity | Consent required? | Source approval required? | Notes |
|---|---|---|---|---|---|
| `id` | Internal / admin | LOW | No | No | Stable system ID; never displayed raw |
| `display_name` | Public (conditional) | MEDIUM | Yes for individuals; lower for entities | Yes | Entities: may come from confirmed public source. Individuals: opt-in required. |
| `legal_name` | Admin only | HIGH | Yes | Yes | Never public by default. Must not differ from `display_name` in public view. |
| `profile_type` | Public | LOW | No | No | Controlled vocabulary; no personal data |
| `professional_role` | Public (conditional) | LOW–MEDIUM | Optional for entities; yes for individuals | Optional | Studio: low risk. Individual: may require consent. |
| `disciplines / specialties` | Public (conditional) | LOW | Optional | Optional (public source) | Closed controlled vocabulary required before use |
| `location_city` | Public | MEDIUM | Optional for entities; yes for individuals | Optional | City level acceptable. No street address. |
| `location_region` | Public | LOW | No (general region) | No | Region/province level; low risk |
| `website` | Public | LOW | Optional | Optional (must be member-provided or voluntarily public) | Do not infer or scrape |
| `portfolio_url` | Public | LOW | Yes — must be member-provided | Optional | Do not infer or scrape portfolio links |
| `public_email` | Public (opt-in only) | HIGH | **YES — explicit opt-in required** | Yes | Forbidden by default. Never show without consent. |
| `phone` | **FORBIDDEN for public** | HIGH | Forbidden | N/A | Never public. Admin-internal at most. |
| `social_links` | Public (opt-in) | MEDIUM | Yes — must be member-provided | Optional | Do not scrape or infer. Deferred. |
| `short_description` | Public | LOW | Optional (entities); yes (individuals) | No | Member-written bio. Defaults to empty. |
| `member_status` | Admin only | HIGH | N/A | N/A | ADG-FAD internal; never public |
| `membership_type` | Admin only | HIGH | N/A | N/A | Membership tier; never public |
| `joined_at` | Admin only | MEDIUM | N/A | N/A | ADG join date; internal only |
| `updated_at` | Admin only | LOW | N/A | N/A | Technical field; not displayed |
| `source` | Admin only | LOW | N/A | N/A | Provenance: `adg-public`, `mock`, `member-provided`, etc. |
| `source_file` | Admin only | LOW | N/A | N/A | Source file path; internal |
| `consent_status` | Admin only | MEDIUM | N/A | N/A | Tracks consent state; internal |
| `visibility_status` | Admin only | LOW | N/A | N/A | Controls public visibility; internal |
| `claimed_by` | Admin only | MEDIUM | N/A | N/A | Which account claimed this profile |
| `claimed_at` | Admin only | LOW | N/A | N/A | Timestamp of claim event |
| `is_mock` | Admin only | LOW | N/A | N/A | Never `true` in `data/public/` |
| `mock_reason` | Admin only | LOW | N/A | N/A | Only in `data/mock/` |

---

## 9. Search / Filter Schema

| Filter | MVP or deferred | Privacy risk | Controlled vocabulary needed | Operator decision needed |
|---|---|---|---|---|
| `profile_type` | **MVP** | LOW | YES — closed list | No — vocabulary from DD6 |
| `location_city` / `location_region` | **MVP** | LOW–MEDIUM | No | No |
| `disciplines / specialties` | Later — controlled vocabulary first | LOW | **YES — operator must approve closed list** | YES — vocab approval before filter is live |
| `availability / status` | DEFERRED | MEDIUM | Needs claiming flow | YES |
| `language` | DEFERRED | LOW | YES | YES |
| `services offered` | DEFERRED | LOW | YES | YES — high marketplace-drift risk |

**Specialty vocabulary rules:**
- Closed specialty list first; secondary tags later (from doc 002 §8)
- LAUS taxonomy may be referenced as input — it must not be blindly inherited
- No free-tag explosion
- Operator must approve the initial closed specialty list before the filter is activated

---

## 10. Profile Claiming / Identity Verification Model

**Self-serve claiming: DEFERRED.**

MVP = admin-curated / admin-mediated only. No self-serve claim flow. No user accounts in MVP.

**Schema modeled for future use:**
The `adg_member_claims` table is defined in this contract for schema readiness. It must not be implemented until:
- Claiming flow is designed and approved
- Identity verification method is confirmed
- Admin moderation tooling is built

**Future claiming model (not MVP):**
- Only active ADG members may claim profiles
- One claim per professional entity
- Proof of ADG membership required (email domain match or admin-confirmed)
- Admin review before claim is confirmed — no automatic activation
- All claim events logged in `adg_member_claims`
- Change requests to sensitive fields require admin approval after claim

**Deferred in MVP:**
- Self-serve claim submission flow
- Automated email/membership verification
- Public claim badge or indicator
- Multiple contacts per entity
- Malicious claim prevention tooling (admin-mediated model is sufficient for v1)

---

## 11. Moderation / Admin Model

**Initial owner:** ADG/manual operator or designated technical admin. Single v1 owner model — consistent with Alertas (doc 021) and Oportunidades (doc 022) patterns.

**No self-serve accounts in MVP.**

**Admin responsibilities:**
- Approve publication of profiles from confirmed public sources (entity profiles only, with ADG/legal authorization)
- Approve sensitive field edits
- Process correction requests
- Process removal/erasure requests
- Manage visibility suppression

**Correction and removal channel:**
A defined correction/removal channel must be operational before any profile is published. Initial channel: ADG email or manual contact form. Channel must be clearly documented and accessible to members.

**Visibility suppression:**
Admin can set any profile to `visibility_status: "suppressed"` at any time. Suppressed profiles do not appear in the public directory. Suppression reason must be logged in `adg_member_admin_notes`.

**Abuse / privacy escalation:**
A defined escalation path to ADG-FAD data controller must exist for LOPD/GDPR data subject rights complaints. Operator defines escalation contact before activation.

**Audit trail requirements:**
- All profile status changes: logged in `adg_member_visibility_events`
- All consent events: logged in `adg_member_consent_events`
- All admin actions: logged in `adg_member_admin_notes` with `created_by` + `created_at`
- Audit trail preserved anonymously after erasure

---

## 12. SQL-Ready Table Model

**Dataset:** `ds-adg-members`
**Row ID pattern:** `adg-member-NNNNN` (5-digit zero-padded; stable; never reused)
**Mock data:** FORBIDDEN in `data/public/`; `data/mock/` only if operator-approved

---

### A. `adg_members`

**Purpose:** Core member identity record — one row per professional entity.

| Field | Type | Required | Public | Notes |
|---|---|---|---|---|
| `id` | string | YES | No | `adg-member-NNNNN`; PRIMARY KEY; immutable |
| `display_name` | string | YES | Conditional | Public only with consent/admin-approval |
| `legal_name` | string | No | **Never** | Admin-only; must not appear in public schema |
| `profile_type` | string | YES | Yes | Controlled vocabulary (see §13) |
| `visibility_status` | string | YES | No | Default: `hidden` |
| `consent_status` | string | YES | No | Default: `unknown` |
| `source` | string | YES | No | Controlled vocabulary |
| `source_file` | string | Conditional | No | Required when `source = "adg-public"` |
| `is_mock` | boolean | No | No | `true` only in `data/mock/` |
| `mock_reason` | string | No | No | Required if `is_mock: true` |
| `created_at` | string | YES | No | ISO 8601 |
| `updated_at` | string | YES | No | ISO 8601 |

---

### B. `adg_member_profiles`

**Purpose:** Extended profile data — conditionally public fields.
**FK:** `member_id` → `adg_members.id`

| Field | Type | Required | Public | Notes |
|---|---|---|---|---|
| `id` | string | YES | No | `adg-profile-NNNNN` |
| `member_id` | string | YES | No | FK → `adg_members.id` |
| `short_description` | string | No | Conditional | Member-written bio; empty by default |
| `location_city` | string | No | Conditional | City level only |
| `location_region` | string | No | Conditional | Province/region |
| `website` | string | No | Conditional | Member-provided or confirmed public source only |
| `portfolio_url` | string | No | Conditional | Member-provided only; no scraping |
| `public_email` | string | No | Conditional | **Explicit opt-in required; forbidden by default** |
| `updated_at` | string | YES | No | ISO 8601 |

**Excluded from this table:** `phone` (forbidden for public); `social_links` (deferred); `legal_name` (admin-only on `adg_members`).

---

### C. `adg_member_specialties`

**Purpose:** Normalized specialty/discipline tags per member. Controlled vocabulary required before use.
**FK:** `member_id` → `adg_members.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `adg-specialty-NNNNN` |
| `member_id` | string | YES | FK → `adg_members.id` |
| `specialty_slug` | string | YES | From approved closed vocabulary; `kebab-case` |
| `specialty_label` | string | YES | Display label; separate from slug |
| `specialty_status` | string | YES | `active` or `deprecated` |
| `source` | string | YES | Provenance |

**Hard rule:** Specialty filter must not be activated before the closed vocabulary list is approved by the operator.

---

### D. `adg_member_consent_events`

**Purpose:** Immutable log of all consent events. Admin-only. Never exposed publicly.
**FK:** `member_id` → `adg_members.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `adg-consent-evt-NNNNN` |
| `member_id` | string | YES | FK → `adg_members.id` |
| `event_type` | string | YES | Controlled vocabulary (see §13) |
| `event_at` | string | YES | ISO 8601 |
| `actor` | string | YES | `member` or `admin` |
| `channel` | string | YES | `email`, `form`, `admin-manual` |
| `notes` | string | No | Free text for admin context |

---

### E. `adg_member_visibility_events`

**Purpose:** Log of all visibility status transitions. Admin-only.
**FK:** `member_id` → `adg_members.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `adg-vis-evt-NNNNN` |
| `member_id` | string | YES | FK → `adg_members.id` |
| `old_status` | string | YES | Previous `visibility_status` value |
| `new_status` | string | YES | New `visibility_status` value |
| `changed_at` | string | YES | ISO 8601 |
| `changed_by` | string | YES | Actor (admin user or system) |
| `reason` | string | No | Free text |

---

### F. `adg_member_claims`

**Purpose:** Profile claiming lifecycle. Schema modeled for future use — **implementation deferred.**
**FK:** `member_id` → `adg_members.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `adg-claim-NNNNN` |
| `member_id` | string | YES | FK → `adg_members.id` |
| `claim_status` | string | YES | Controlled vocabulary (see §13) |
| `claimed_at` | string | YES | ISO 8601 |
| `claimed_by_ref` | string | No | Identifier for claiming account (admin-only) |
| `verification_method` | string | No | Method used to verify identity |
| `verified_by` | string | No | Admin who confirmed |
| `approved_at` | string | No | ISO 8601 |

**Hard rule:** This table must not be implemented until self-serve claiming is explicitly reopened by the operator.

---

### G. `adg_member_admin_notes`

**Purpose:** Internal operator notes — moderation decisions, correction records, removal records. Admin-only.
**FK:** `member_id` → `adg_members.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `adg-note-NNNNN` |
| `member_id` | string | YES | FK → `adg_members.id` |
| `note_type` | string | YES | Controlled vocabulary (see §13) |
| `note_text` | string | YES | Internal note content |
| `created_at` | string | YES | ISO 8601 |
| `created_by` | string | YES | Admin actor |

---

### Optional / Deferred Tables

| Table | Purpose | Status |
|---|---|---|
| `adg_member_links` | Normalized social/external links per member | Deferred — until claiming is live |
| `adg_member_locations` | Normalized location records if multi-location support needed | Deferred |
| `adg_member_sources` | Tracks which data source authorized each data point | Deferred — useful for multi-source audit trail |

---

## 13. Status Vocabularies

### `profile_status`
- `draft` — created but not ready for review
- `pending_review` — submitted to admin for approval
- `published` — live and public
- `hidden` — not visible (admin or default state)
- `removed` — removed by request; data anonymized or deleted
- `rejected` — admin rejected publication

### `visibility_status`
- `hidden` — not visible to public **(default for all new entries)**
- `published` — visible to public
- `suppressed` — visibility overridden by admin action
- `pending_consent` — awaiting member consent before publication

### `consent_status`
- `unknown` — no consent record exists **(default)**
- `opted_in` — member has explicitly consented
- `opted_out` — member has explicitly opted out
- `admin_approved` — admin has approved from confirmed public source (entity profiles only, with ADG/legal authorization)
- `pending` — consent request sent, awaiting response

### `claim_status`
- `unclaimed` — no claim submitted **(default)**
- `pending` — claim submitted, awaiting admin review
- `approved` — claim approved; member owns profile
- `rejected` — claim denied
- `withdrawn` — member withdrew claim
- `revoked` — admin revoked claim (e.g., fraud, membership lapse)

### `profile_type`
- `studio` — design studio, agency, or company
- `freelance` — independent professional / freelancer
- `school` — educational institution
- `agency` — specialized agency (if distinct from `studio` — operator decision on separation)
- `collective` — design collective (deferred; operator decision on inclusion)

### `source_type` (for `source` field)
- `adg-public` — sourced from public ADG materials; `source_file` required
- `member-provided` — member submitted their own data through claiming flow
- `mock` — placeholder; `data/mock/` only; `is_mock: true` required
- `pending` — awaiting authorized data source
- `derived` — calculated from other tables; `derived_from` field required

### `moderation_status`
- `not_reviewed` — not yet reviewed by admin **(default)**
- `under_review` — admin actively reviewing
- `approved` — admin approved for publication
- `changes_requested` — admin returned for correction
- `rejected` — admin rejected

### `consent_event_type` (for `adg_member_consent_events.event_type`)
- `opt_in` — member explicitly consented
- `opt_out` — member explicitly opted out
- `admin_approval` — admin approved from confirmed public source
- `erasure_request` — LOPD/GDPR erasure request received
- `correction_request` — member requested field correction
- `removal_request` — member requested profile removal
- `reinstatement` — previously removed/opt-out member requests reinstatement

### `request_type` (for `adg_member_admin_notes.note_type`)
- `correction` — member-requested field correction
- `removal` — member-requested profile removal
- `erasure` — LOPD/GDPR erasure request
- `claiming` — profile claim event note
- `reinstatement` — reinstatement after removal
- `escalation` — privacy/legal escalation to ADG-FAD
- `other`

### `specialty_status`
- `active` — currently valid in the vocabulary
- `deprecated` — retired; `replaced_by` slug required; never deleted from registry

---

## 14. Mock Data Policy

**Mock member profiles are NOT allowed until this contract is committed and the operator explicitly authorizes.**

**Absolute prohibitions:**
- Fake real people are forbidden — never use real ADG member names, even as placeholders
- No mock member rows in `data/public/`
- No realistic profiles (real emails, phones, websites, social handles) even in test files
- No scraping or referencing real member profiles for demo purposes
- No data that could be mistaken for a real directory listing

**If future UI testing requires mock rows (after contract approval, operator-requested only):**
- `data/mock/` directory only — never inside `data/public/`
- `source: "mock"`, `is_mock: true`, `mock_reason: "..."` required on all rows
- Names must be obviously fake: `"Estudio Test"`, `"Diseñadora Ejemplo"` — not realistic ADG member names
- No real emails; use `@example.com` only where email field is required for schema testing
- No real phone numbers, portfolios, or social handles
- Schema must match the future real table schema 1:1 — no mock-only fields
- All mock rows identifiable by `source: "mock"` — a single filter removes them all

**Preferred default now:** Honest empty state. The stub card already communicates "coming soon." No mock data is needed.

---

## 15. Active Surface Boundaries

The following are active surfaces and are **out of implementation scope** in this branch. This contract does not authorize any edits to their source files, internals, routes, copy, behavior, data, or UI.

| Surface | Route | Status in this branch |
|---|---|---|
| Licitaciones / Observatorio | `licitaciones.html` | OUT OF SCOPE — do not touch |
| Estadísticas Forense | `estadisticas.html` | OUT OF SCOPE — do not touch |
| Recursos + Calculadora | `recursos.html` | OUT OF SCOPE — do not touch |
| Mapa del Diseño | `mapa.html` | OUT OF SCOPE — do not touch |
| Barómetro del Sector | toggle inside `estadisticas.html` | OUT OF SCOPE — do not touch |

Additionally: `extensions.html` is **deleted and prohibited**. It must never be recreated, referenced, linked, redirected to, or audited as a product surface.

---

## 16. Implementation Blockers / Pre-Activation Gates

All of the following must be cleared before any Directorio public profile can be published. None are optional.

| Gate | Status | Notes |
|---|---|---|
| ADG-FAD data source authorization confirmed | **BLOCKED** | Association approval not yet received |
| Legal basis for publication confirmed | **BLOCKED** | Opt-in mechanism or formal LIA not yet assessed |
| Privacy notice updated for Directorio module | **BLOCKED** | Must cover new data use before any publication |
| Correction/removal request channel operational | **BLOCKED** | Channel must exist before any data is public |
| Erasure/anonymization flow designed and operational | **BLOCKED** | Right to erasure must be implementable |
| Schema approved by operator | **BLOCKED** | This contract must be committed + operator confirms schema |
| Admin ownership confirmed | **BLOCKED** | ADG/manual operator owner must be explicitly named |
| Specialty vocabulary approved | **BLOCKED** | Closed list must be operator-approved before filter is live |
| Source/provenance/import policy approved | **BLOCKED** | Import batch format and source authorization process defined |
| Operator explicitly reopens source scope | **BLOCKED** | `directorio.html` and route creation require explicit reopen |
| Card link activation separately approved | **BLOCKED** | `card-directorio-socios` must not be linked until separately authorized |

---

## 17. Explicitly Out of Scope

The following are **not authorized by this contract** and must not be implemented:

- Creating `directorio.html`
- Activating `card-directorio-socios` (adding `href`)
- Adding a route for Directorio
- Reading or importing raw member data
- Reading `docs/support_copys/listado_socios_onlynames.txt`
- Creating any `adg_members` data files
- Creating mock member data of any kind
- Adding forms, submission flows, or profile editing flows
- Public self-serve profile claiming
- User account creation or self-serve claiming flow
- Editing any active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro)
- Editing `licitaciones.html`, `estadisticas.html`, `recursos.html`, `mapa.html`
- Resurrecting or referencing `extensions.html`
- Source implementation of any kind

---

## 18. Next Steps

**Recommended: TXT 070_audit — Branch close readiness audit**

With this contract committed, the ADG Extensions branch will have completed:
- Hub card doctrine (TXT 058)
- ID taxonomy registry (TXT 057)
- Alertas consent/delivery contract (TXT 062)
- Oportunidades process contract (TXT 065)
- Directorio data/privacy contract (TXT 069 — this doc)

A branch close readiness audit (TXT 070) should review whether the branch is ready to close, what has been accomplished, what remains deferred, and what cleanup (if any) is needed before merge or archive.

**No source implementation is authorized** until this contract is reviewed by the operator, committed, and all pre-activation gates in Section 16 are cleared. The operator must explicitly reopen source scope for any Directorio implementation work.

---

## 19. ROADMAP PRÓXIMO

- **TXT 069** — current: write Directorio data/privacy contract doc ← YOU ARE HERE
- **TXT 070** — next: branch close readiness audit — final QA before closing the extensions branch
- **TXT 071** — likely: final branch close doc or archive/hygiene plan
- **HOLD** — Directorio implementation blocked until contract committed + all 11 pre-activation gates cleared
- **HOLD** — `directorio.html` blocked until contract committed + schema approved + operator explicitly reopens source + card activation separately approved
- **HOLD** — Oportunidades source/subhub blocked until explicit source reopen
- **HOLD** — `oportunidades.html` must not be created
- **HOLD** — Freelancers/Profesional implementation blocked until deep fichas CLOSED
- **HOLD** — Alertas activation blocked by all pre-activation gates
- **HOLD** — Active surfaces (Licitaciones, Estadísticas, Recursos, Mapa, Barómetro) out of scope in this branch

---

## Stop

- No source file edits
- No data writes
- No git mutations
- This document is contract/planning only
- Operator performs all staging and commits manually
