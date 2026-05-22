# ADG_EXTENSIONS_021 — Alertas Consent + Delivery Contract

**Version:** v0.1.3.1  
**Status:** PLAN / NOT IMPLEMENTED  
**Mode:** CONTRACT / ALERTAS  
**Branch:** extensions  
**Owner scope:** ADG Extensions  
**Source basis:** TXT 060 audit + TXT 061 locked decisions + extensions_doc canon  
**Date:** 2026-05-22  
**Git write operations:** FORBIDDEN to Claude CLI — operator performs all staging and commits  
**Activation status:** NOT ACTIVE  
**Implementation status:** DOC ONLY

---

## 1. Purpose

This document defines the pre-activation contract for the Alertas por Email extension module.

It exists to make any future Alertas implementation SQL-ready, consent-safe, and scope-safe before a single line of activation code is written.

**This document does NOT:**
- activate Alertas por Email
- authorize email capture of any kind
- authorize provider integration
- authorize data file creation
- authorize any source file edits
- grant implementation permission

**This document DOES:**
- close the consent model contract
- close the delivery/provider model contract
- close the trigger rules contract
- define the preference schema
- define the unsubscribe/deletion model
- define the admin ownership model
- define the SQL-ready table structure
- define controlled status vocabularies
- define the mock data policy
- enumerate all pre-activation gates that must be closed before any real implementation begins

No implementation of any kind should proceed until this document is reviewed, committed, and the pre-activation gates in §14 are explicitly resolved by the operator.

---

## 2. Current Non-Active State

| Surface | State | Detail |
|---|---|---|
| `index.html` hub card | `stub` | `id="card-alertas-email"`, `data-module-kind="extension_module"`, `data-module-state="stub"`, `data-route-id="route-alertas"` — non-clickable `<div>`, no href |
| `alertas.html` | Honest stub shell | Renders `<div id="alertas-container">` only; AlertasStub component renders coming-soon UI |
| `shared.js` AlertasStub | Non-submitting UI prototype | All inputs `disabled`; all interactions show coming-soon modal only; no XHR, no fetch, no form action, no submit |
| `about.html` | Planned/future copy | WIP banner: "Alertas y comunicaciones están previstas como módulo futuro. Aún no hay servicio activo ni sistema de envío conectado." |
| Email capture | NONE | No form, no endpoint, no subscription flow, no provider |
| Provider | NONE | No Formspree, Mailchimp, Brevo, or any other provider connected |
| Formspree / FORM_ID_AQUI | NONE | Removed by TXT 052 (ec4f737); no reference remains |
| Data files | NONE | No alertas_subscriptions, preferences, consent, or delivery data files exist |

**AlertasStub UI discrepancy (prototype note):**  
The AlertasStub component in shared.js renders four disabled filter fields: discipline, territory, keywords, and health signals. The contracted MVP scope (D4, §7) is discipline + territory + frequency only. Keywords and health signal fields are visual prototype artifacts — they are NOT contracted MVP scope and must not be treated as implementation targets.

**Alertas is NOT ACTIVE. It must not look active, imply activation, or capture any user data.**

---

## 3. Locked Operator Decisions

These decisions were closed in TXT 061. They are binding for all future Alertas implementation work.

| ID | Decision | Status | Consequence |
|---|---|---|---|
| **D1** | Double opt-in is mandatory for any future public/real subscription flow. No email capture before consent text, privacy notice, unsubscribe mechanism, and proof of consent all exist. | LOCKED | Hard gate — no web form before all consent gates are closed |
| **D2** | Provider is undecided. Manual-first is the safest v1 operating model. No Brevo, Mailchimp, Formspree, or any other provider. No API keys, endpoints, or provider config. | LOCKED | Contract defines manual-first only; provider selection is a future gate |
| **D3** | Default frequency = weekly digest. Daily digest may be reserved as a future option. Immediate sends are excluded from MVP. | LOCKED | `frequency` default value = `weekly`; `immediate` excluded from MVP vocabulary |
| **D4** | MVP contracted filters: discipline + territory + frequency. | LOCKED | `frequency` on subscription row; `discipline` and `territory` as multi-value preference rows |
| **D5** | Keywords, health signals, saved searches, opportunity type, and profile-based alerts are deferred/prototype-only. AlertasStub UI keyword + health signal fields are prototype artifacts, not MVP scope. | LOCKED | These must not be implemented until explicitly reopened by operator |
| **D6** | Unsubscribe mandatory in every email. Suppression/anonymization preferred over blind hard delete. Status-based suppression prevents accidental re-send. **Legal/privacy review is a required pre-activation gate — not optional commentary.** | ACCEPTED WITH NOTE | Contract doc must surface D6 legal review as a BLOCKER, not a design footnote |
| **D7** | Initial admin owner = ADG/manual operator or designated technical admin. No automated sending until admin ownership is explicitly approved. | LOCKED | Manual v1 only; admin reviews and triggers each send |
| **D8** | Licitaciones / Observatorio is an active surface and out of scope for this branch. It may be referenced only as an external data dependency for future trigger rules. No edits to Licitaciones source, JS, data, modals, filters, or behavior. | LOCKED | Trigger contract is conceptual only in this branch |
| **D9** | No mock Alertas subscriptions. No fake real emails. No mock rows in `data/public/`. If future UI testing ever requires mock rows: `@example.com` addresses only, `data/mock/` directory only, `source: "mock"`, `is_mock: true`, `mock_reason` required. | LOCKED | Honest empty state is correct for now |
| **D10** | TXT 062 is doc-only. The Alertas contract document is the only approved output. No source/data changes. | LOCKED | No implementation until contract is committed and gates are resolved |

---

## 4. Consent Model

**Double opt-in is mandatory** for any future public or real subscription flow.

### Pre-activation consent gates (all must be closed before any form is built)

| Gate | Status |
|---|---|
| Consent text drafted and reviewed | NOT DONE |
| Privacy notice drafted and reviewed | NOT DONE |
| Legal/privacy review completed | NOT DONE — required pre-activation gate (D6) |
| Double opt-in flow designed | NOT DONE |
| Unsubscribe mechanism designed | NOT DONE |
| Proof of consent / `consented_at` field implemented | NOT DONE |

### Consent requirements

- **No email capture** of any kind before all six gates above are closed.
- Consent text must be visible at the point of subscription and must clearly state what the user is subscribing to, how often they will receive emails, and how to unsubscribe.
- Privacy notice must state: data use, storage location, retention period, and the right to deletion.
- **Double opt-in flow:** after form submission, a confirmation email must be sent; the subscription is not active until the user clicks the confirmation link.
- `consented_at` must be recorded as an ISO 8601 timestamp when the user confirms.
- `consent_version` must record which version of the consent text was shown at the time of subscription.
- `consent_source` must record how the consent was obtained (`web_form`, `manual`, `admin`).
- All consent evidence must be auditable — the `alertas_consent_events` table (§10) preserves this.
- Editable preferences (ability to change discipline/territory/frequency after subscription) are a required feature before activation — not an optional enhancement.

### Anti-capture rule

No user email address, preference, or identity may be captured, stored, or transmitted until:
1. Consent text exists and is approved
2. Privacy notice exists and is approved
3. Legal/privacy review is complete
4. Unsubscribe mechanism is implemented and tested
5. Double opt-in confirmation flow is implemented

---

## 5. Delivery / Provider Model

**Provider is undecided.** No provider has been selected, connected, or configured.

### Manual-first v1 model

The safest v1 operating model is manual-first:
- The operator maintains a subscriber list (once it exists)
- The operator composes each digest manually or with tooling
- The operator reviews and approves before any send
- No automated trigger fires without human approval in v1

This model requires no provider integration, no API keys, and no automated infrastructure. It is suitable for a small initial cohort and gives maximum control.

### Provider options (informational only — no decision made)

The following are possible providers for a future automated v1.5+. None is selected or recommended here:

| Provider | Notes |
|---|---|
| Brevo | Free tier; REST API; good for small lists |
| Mailchimp | Industry standard; free tier limited |
| Buttondown | Lightweight newsletter tool |
| EmailOctopus | Low cost; AWS SES backend |
| Manual CSV + BCC | No provider; operator sends from email client |
| Custom DB + SMTP | Future; requires infrastructure |

**Hard rules:**
- No provider is connected until the operator explicitly approves a provider choice.
- No API keys, credentials, or provider configuration may appear in source files or be committed to git.
- Automatic sending is FORBIDDEN until provider, admin ownership, and legal gates are all closed.
- Formspree is not an approved option — it was removed from licitaciones.html in TXT 052 and must not be reintroduced.

---

## 6. Trigger Rules

### MVP conceptual trigger

| Dimension | Value |
|---|---|
| Trigger event | New licitación published in Licitaciones data pipeline |
| Match criteria | Subscriber discipline preferences ∩ licitación disciplines |
| Match criteria | Subscriber territory preferences ∩ licitación CCAA |
| Frequency | Weekly digest — matched licitaciones grouped per subscriber |
| Send condition | Only if there are real matches; no empty digests |

### Licitaciones dependency

Licitaciones / Observatorio is an **active surface and out of implementation scope** for this branch.

- Licitaciones may be referenced here as an external data source/input only.
- The trigger contract is **conceptual only** in this document.
- No trigger matching logic, data pipeline, or cross-boundary API is designed or implemented here.
- No edits to `licitaciones.html`, Licitaciones JS, data files, modals, filters, export behavior, or any Licitaciones internals are authorized.
- A cross-boundary contract between Alertas and the Licitaciones data pipeline must be defined separately before any trigger implementation can begin.

### Trigger reliability requirement

**Bad data creates bad alerts.** No alert should be sent unless the Licitaciones data pipeline is trusted as an alert-grade source — meaning data is current, discipline classification is reliable, and territory tagging is accurate.

### Deferred triggers (prototype-only — not MVP)

| Trigger | Status |
|---|---|
| Licitación status change (Vigente → Adjudicado, etc.) | Deferred |
| New Oportunidades listing | Deferred — Oportunidades module does not exist yet |
| Keyword/category match | Deferred / prototype-only (D5) |
| Health signal match (traffic light) | Deferred / prototype-only (D5) |
| Profile-driven alerts | Deferred — Directorio/profile system does not exist yet |
| Saved search alerts | Deferred / prototype-only (D5) |

---

## 7. Preference Schema

### Storage model

`frequency` is a single value per subscriber — stored on the `alertas_subscriptions` row directly.

`discipline` and `territory` are multi-valued per subscriber — stored as individual rows in the `alertas_preferences` table (one row per preference value per subscriber).

All preference values must use stable controlled slugs or codes — no free-text user input stored directly as a preference value. Discipline slugs must align with the licitaciones taxonomy. Territory values must use CCAA codes.

**No preference data may be hardcoded in HTML or JS.** All preference records live in data tables only.

### alertas_subscriptions fields (subscription-level)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `alr-sub-YYYYMMDD-NNN` — date-prefixed, sequential within day |
| `email` | string | YES | Never stored in `data/public/`; must be secured at rest |
| `subscription_status` | string | YES | Controlled vocab — see §11 |
| `frequency` | string | YES | `weekly` (default) \| `daily` (future) \| `manual` |
| `language` | string | later | `es` \| `ca` \| `eu` \| `gl` — default `es` |
| `source` | string | YES | `web_form` \| `manual` \| `admin` \| `mock` |
| `created_at` | ISO 8601 | YES | |
| `updated_at` | ISO 8601 | YES | |
| `consented_at` | ISO 8601 | NO | Null until double opt-in confirmed |
| `consent_version` | string | YES | e.g. `alertas-consent-v1` — version of consent text shown |
| `unsubscribed_at` | ISO 8601 | NO | Null unless unsubscribed |
| `deleted_at` | ISO 8601 | NO | Null unless data deletion requested |
| `is_mock` | boolean | NO | `true` for test rows only — forbidden in `data/public/` |
| `mock_reason` | string | NO | Required when `is_mock: true` |

### alertas_preferences fields (multi-value, one row per preference value)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `alr-pref-YYYYMMDD-NNN` |
| `subscription_id` | string FK | YES | → `alertas_subscriptions.id` |
| `preference_type` | string | YES | MVP: `discipline` \| `territory` — keyword/health deferred |
| `preference_value` | string | YES | Controlled slug or CCAA code — no free text |
| `preference_status` | string | YES | `active` \| `inactive` |
| `source` | string | YES | `web_form` \| `manual` \| `admin` \| `mock` |
| `created_at` | ISO 8601 | YES | |
| `updated_at` | ISO 8601 | YES | |

### Deferred preference fields (not MVP)

`keyword_preferences`, `health_signal_preferences`, `opportunity_type_preferences`, `saved_search_id`, `profile_id` — all deferred. Must not be implemented until explicitly reopened by operator.

---

## 8. Unsubscribe / Deletion Model

### Unsubscribe

- **Every outgoing email must include an unsubscribe link.** No exceptions.
- Unsubscribe must work without requiring the user to log in.
- On unsubscribe: `subscription_status` → `unsubscribed`, `unsubscribed_at` populated with ISO 8601 timestamp.
- A `consent_event_type: unsubscribed` row must be written to `alertas_consent_events`.
- Status-based suppression is required: unsubscribed rows must never receive further emails even if a send is triggered accidentally.

### Data deletion

- Users may request full deletion of their subscription data.
- On deletion request: `subscription_status` → `deleted`, `deleted_at` populated.
- **Suppression/anonymization is the preferred model** — not blind hard delete:
  - The subscription row is retained with `status: deleted`.
  - The `email` field is anonymized (nulled or hashed) on the main subscription row.
  - The `alertas_preferences` rows for the subscriber are marked `preference_status: inactive`.
  - The `alertas_consent_events` rows are retained without the raw email for audit purposes.
  - The `alertas_delivery_logs` rows are retained without raw personal data.
  - This approach prevents accidental re-subscription and preserves the audit trail required for compliance.
- A `consent_event_type: deleted` row must be written to `alertas_consent_events` on deletion.

### Legal / privacy review gate

**The final legal and privacy wording, data retention policy, and deletion procedure must be reviewed by a qualified reviewer before Alertas is activated.** This is not optional commentary — it is a required pre-activation gate (D6). No web form, subscription flow, or provider integration should proceed until this review is complete and the outcome is documented.

---

## 9. Admin / Ownership Model

| Property | Value |
|---|---|
| Initial admin owner | ADG/manual operator or designated technical admin |
| Subscriber list access | Controlled — not publicly accessible; owner-only |
| Send approval | Manual — admin reviews and approves each digest before delivery |
| Automated sending | FORBIDDEN until admin ownership is explicitly approved and provider gates are closed |
| Failure handling | Deferred until provider choice |
| Bounce handling | Deferred until provider choice |
| Suppression list management | Admin responsibility |
| Preference management | Admin may update preferences on behalf of subscriber only with explicit user request |

### Manual v1 operating model

In a manual-first v1, the technical admin:
1. Reviews the subscriber list periodically
2. Identifies new matched licitaciones against subscriber preferences manually or with tooling
3. Composes the digest
4. Reviews content before send
5. Triggers the send via the chosen mechanism (email client, provider dashboard, or script)
6. Records the delivery in `alertas_delivery_logs`

This model gives full editorial control and requires no autonomous automation infrastructure.

---

## 10. SQL-Ready Table Model

All tables follow the ADG Extensions data doctrine from ADG_EXTENSIONS_008: JSON file = table, JSON object = row, `id` = stable immutable PK, `snake_case` keys, `null` for unknowns, no hardcoded data in HTML/JS, round-trip rule (JSON → CSV → JSON lossless).

---

### `alertas_subscriptions`

**Purpose:** One row per subscriber. Master subscriber record.  
**dataset_id:** `ds-alertas-subscriptions`  
**SQL table name (future):** `alertas_subscriptions`  
**PK pattern:** `alr-sub-YYYYMMDD-NNN`  

See field table in §7 above.

**Mock policy:** FORBIDDEN in `data/public/`. Only in `data/mock/` with `source: "mock"`, `is_mock: true`, `mock_reason`, `@example.com` addresses only. No mock rows until contract is approved and operator explicitly requests UI testing.

---

### `alertas_preferences`

**Purpose:** Multi-value preference rows per subscriber. Discipline and territory preferences.  
**dataset_id:** `ds-alertas-preferences`  
**SQL table name (future):** `alertas_preferences`  
**PK pattern:** `alr-pref-YYYYMMDD-NNN`  
**FK:** `subscription_id` → `alertas_subscriptions.id`

See field table in §7 above.

**Note:** `preference_type` MVP vocabulary = `discipline` and `territory` only. `keyword` and `health_signal` types are reserved but deferred.

**Mock policy:** Same as `alertas_subscriptions` — forbidden until operator explicitly authorizes.

---

### `alertas_consent_events`

**Purpose:** Immutable chronological log of all consent-related actions. Preserved after subscriber deletion (with email anonymized). Provides GDPR-compliant audit trail.  
**dataset_id:** `ds-alertas-consent-events`  
**SQL table name (future):** `alertas_consent_events`  
**PK pattern:** `alr-consent-YYYYMMDD-NNN`  
**FK:** `subscription_id` → `alertas_subscriptions.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `alr-consent-YYYYMMDD-NNN` |
| `subscription_id` | string FK | YES | → `alertas_subscriptions.id` — retained after deletion |
| `event_type` | string | YES | Controlled vocab — see §11 |
| `occurred_at` | ISO 8601 | YES | |
| `source` | string | YES | `web` \| `email_link` \| `admin` |
| `consent_version` | string | NO | Version of consent text shown, if applicable |
| `ip_hash` | string | NO | SHA-256 of IP at consent time — privacy-compliant |
| `notes` | string | NO | Admin-only free text |

**Rule:** Consent event rows must NEVER be deleted. On subscriber deletion, anonymize `subscription_id` references in other tables but keep this log intact for compliance.

**Mock policy:** Forbidden until operator explicitly authorizes.

---

### `alertas_delivery_logs`

**Purpose:** One row per send attempt per subscriber. Records what was sent, when, and with what result.  
**dataset_id:** `ds-alertas-delivery-logs`  
**SQL table name (future):** `alertas_delivery_logs`  
**PK pattern:** `alr-dlv-YYYYMMDD-NNN`  
**FK:** `subscription_id` → `alertas_subscriptions.id`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | YES | `alr-dlv-YYYYMMDD-NNN` |
| `subscription_id` | string FK | YES | → `alertas_subscriptions.id` |
| `delivery_status` | string | YES | Controlled vocab — see §11 |
| `trigger_type` | string | YES | Controlled vocab — see §11 |
| `batch_id` | string | NO | Groups rows belonging to one digest send |
| `sent_at` | ISO 8601 | NO | Null until actually sent |
| `provider` | string | NO | e.g. `brevo` \| `mailchimp` \| `manual` — null until provider chosen |
| `source` | string | YES | `system` \| `admin` |
| `error_note` | string | NO | Free text on failure |

**Mock policy:** Forbidden until operator explicitly authorizes.

---

### `alertas_trigger_rules` (DEFERRED)

**Status:** DEFERRED — not implemented, not designed in this contract.

This table will define the matching rules that determine which licitaciones trigger alerts for a given subscriber. It cannot be designed until:
- The Licitaciones data pipeline is trusted as an alert-grade source
- A cross-boundary contract between Alertas and Licitaciones is approved
- The Licitaciones data team confirms the match fields (discipline codes, CCAA codes) are stable and reliable

Do not implement this table until the above gates are resolved.

---

### Relationship model

```
alertas_subscriptions (1) ──── alertas_preferences (N)
         │                         (FK: subscription_id)
         │
         ├── alertas_consent_events (N)
         │       (FK: subscription_id — retained after deletion)
         │
         └── alertas_delivery_logs (N)
                 (FK: subscription_id)

[future] alertas_trigger_rules ─── alertas_subscriptions
                                    (FK: subscription_id)
```

---

## 11. Status Vocabularies

### `subscription_status`

| Value | Meaning |
|---|---|
| `pending_double_opt_in` | Form submitted; confirmation email sent; not yet confirmed |
| `active` | Double opt-in confirmed; subscription active; eligible for sends |
| `paused` | Temporarily paused by user or admin; no sends while paused |
| `unsubscribed` | User or admin unsubscribed; no further sends |
| `deleted` | Data deletion requested; email anonymized; row retained for audit |
| `bounced` | Hard bounce received; suppressed from further sends |
| `suppressed` | Suppressed by admin for technical or policy reason |

### `consent_event_type`

| Value | Meaning |
|---|---|
| `requested` | Initial form submitted with consent checkbox |
| `confirmed` | Double opt-in confirmation link clicked |
| `updated` | User updated preferences |
| `unsubscribed` | Unsubscribe action recorded |
| `deleted` | Data deletion executed; email anonymized |
| `admin_suppressed` | Suppressed by admin |

### `delivery_status`

| Value | Meaning |
|---|---|
| `queued` | Scheduled; not yet sent |
| `manual_review` | Awaiting admin review/approval before send |
| `sent` | Handed to provider or sent manually |
| `skipped` | Subscriber was not eligible at send time (unsubscribed, deleted, etc.) |
| `failed` | Technical or provider failure |
| `bounced` | Hard or soft bounce reported by provider |

### `frequency`

| Value | Meaning |
|---|---|
| `weekly` | Weekly digest — default |
| `daily` | Daily digest — future option |
| `manual` | Admin-triggered only — v1 recommended mode |

`immediate` is **excluded from MVP.** Do not add it to the frequency vocabulary until explicitly approved.

### `trigger_type`

| Value | Meaning |
|---|---|
| `new_licitacion` | New licitación matching subscriber preferences (MVP conceptual trigger) |
| `discipline_match` | Discipline dimension of a trigger match |
| `territory_match` | Territory dimension of a trigger match |
| `manual_digest` | Admin-composed and triggered digest |

### `source` (for subscriptions, preferences, consent events, delivery logs)

| Value | Meaning |
|---|---|
| `web_form` | Submitted via the Alertas web form |
| `manual` | Manually added by admin |
| `admin` | Admin-initiated action |
| `mock` | Test/placeholder record — forbidden in `data/public/` |

### `preference_status`

| Value | Meaning |
|---|---|
| `active` | Preference currently active |
| `inactive` | Preference disabled by user or admin |

---

## 12. Mock Data Policy

| Rule | Detail |
|---|---|
| Mock subscriptions now | **FORBIDDEN** — no contract approved yet |
| Fake real email addresses | **FORBIDDEN** — ever, under any circumstances |
| Mock rows in `data/public/` | **FORBIDDEN** — ever |
| If UI testing ever needs mock rows | `data/mock/` directory only; `@example.com` addresses only; `source: "mock"`, `is_mock: true`, `mock_reason: "..."` on every row |
| `data/mock/` directory | Does not exist yet — must be created by operator before any mock rows are placed there |
| Honest empty state | **PREFERRED NOW** — AlertasStub is the correct display for the current stub state |
| Mock rows schema | Must map 1:1 to the real table schema — no mock-only fields |

**Forbidden mock categories (absolute prohibition):**
- Fake subscriber email addresses resembling real people or organizations
- Fake delivery logs implying real sends happened
- Mock consent events that could be confused with real consent records

---

## 13. Active Surface Boundaries

The following surfaces are **active surfaces and out of implementation scope** for this branch. No source edits are authorized by this contract or by any other ADG Extensions contract document.

| Surface | Status | Rule |
|---|---|---|
| Licitaciones / Observatorio | Active surface | Out of scope; external dependency only for trigger rules |
| Estadísticas Forense | Active surface | Out of scope |
| Recursos + Calculadora | Active surface | Out of scope |
| Mapa del Diseño | Active surface | Out of scope |
| Barómetro del Sector | Active surface | Out of scope — INFORMATIONAL ONLY |

**Licitaciones note:** Licitaciones data is the conceptual trigger source for Alertas MVP. It is an external dependency only. No edits to `licitaciones.html`, Licitaciones JS, data pipeline, filters, modals, or export behavior are authorized in this branch.

**This contract does not grant implementation scope on any active surface.**

---

## 14. Implementation Blockers / Pre-Activation Gates

All of the following must be resolved before any Alertas activation code, form, or provider integration is written:

| Blocker | Status |
|---|---|
| Consent text not drafted | OPEN |
| Privacy notice not drafted or reviewed | OPEN |
| **Legal/privacy review not completed** | **OPEN — REQUIRED GATE (D6)** |
| Double opt-in flow not designed | OPEN |
| Unsubscribe mechanism not designed | OPEN |
| Provider not selected | OPEN |
| API key / credential boundary not defined | OPEN |
| Admin owner / access rights not formally approved | OPEN |
| Table schema not implemented | OPEN — defined here; awaits operator approval and implementation |
| Unsubscribe/deletion flow not implemented | OPEN |
| Licitaciones data trust / cross-boundary trigger contract not approved | OPEN |

**Until all gates are explicitly closed by the operator, Alertas must remain a stub.** The AlertasStub component is the correct and honest user-facing state.

---

## 15. Future Implementation Gates

The following sequence must be followed before any Alertas source implementation begins:

1. Operator reviews and commits this contract document
2. Consent/privacy copy is drafted (consent text + privacy notice)
3. Legal/privacy review is completed and outcome documented
4. Provider or manual-send mechanism is decided and approved
5. Table schema seeds are approved (alertas_subscriptions, alertas_preferences, alertas_consent_events, alertas_delivery_logs)
6. Non-active form UX is designed (separate from the stub — not the same file)
7. Double opt-in confirmation email is designed
8. Admin access model and subscriber list ownership are formally approved
9. Licitaciones cross-boundary trigger contract is defined (separate audit)
10. Only then: source implementation may be proposed in a future `_imp` prompt

Each gate must be documented in a TXT prompt/reply pair before the next gate opens. No gate may be skipped.

---

## 16. Explicitly Out of Scope

The following are explicitly out of scope for this contract, this branch, and any forthcoming TXT unless the operator explicitly reopens scope:

| Item | Status |
|---|---|
| Activating Alertas por Email | OUT OF SCOPE |
| Adding an email subscription form to any page | OUT OF SCOPE |
| Capturing any user email address | OUT OF SCOPE |
| Connecting any email provider (Formspree, Brevo, Mailchimp, etc.) | OUT OF SCOPE |
| Creating `data/public/` alertas data files | OUT OF SCOPE |
| Creating mock subscriptions | OUT OF SCOPE |
| Editing `licitaciones.html` or any Licitaciones internals | OUT OF SCOPE — active surface |
| Editing `estadisticas.html`, `recursos.html`, `mapa.html`, `barometro.html` | OUT OF SCOPE — active surfaces |
| Editing `alertas.html` (stub shell must remain unchanged) | OUT OF SCOPE until implementation gates are closed |
| Editing `shared.js` AlertasStub | OUT OF SCOPE until implementation gates are closed |
| Implementing keywords, health signals, saved searches, or profile alerts | OUT OF SCOPE — deferred/prototype-only (D5) |
| Creating `directorio.html` | OUT OF SCOPE — no data/privacy contract yet |
| Creating `oportunidades.html` | OUT OF SCOPE — no process contract yet |
| Resurrecting `extensions.html` | PERMANENTLY PROHIBITED — deleted by TXT 042; must never be recreated |

---

## 17. Next Steps

**Recommended TXT 063:** `_audit` — operator decides which path to take next:

**Option A:** `_audit` — choose next extension-module contract lane (Directorio data/privacy contract, Oportunidades process contract, or Laus data contract status).

**Option B:** `_audit` — branch close / readiness audit — assess whether the extensions branch is ready to be merged, closed, or handed off as a versioned snapshot.

**Do not recommend or proceed with source implementation** until this contract document is reviewed, committed by the operator, and all pre-activation gates in §14 are explicitly resolved. This document alone does not grant implementation permission.

---

## Stop

- No source file edits
- No data file writes
- No git mutations
- This document is contract planning only
- Alertas is NOT ACTIVE
- No activation is authorized
