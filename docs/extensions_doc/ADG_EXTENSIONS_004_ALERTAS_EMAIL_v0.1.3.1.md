# ADG EXTENSIONS — FICHA 4 CLOSED — ALERTAS POR EMAIL

Version: v0.1.3.1  
Supersedes: `ADG_EXTENSIONS_004_ALERTAS_EMAIL_v0.1.3.md`  
Status: CLOSED / CONSISTENCY-INTEGRATED  
Mode: CONSISTENCY REVIEW  
Project layer: ADGOPS_EXTENSIONS  
Extension: Alertas por Email  
Phase: Fase 7  
Current state: No existe nada  
Language: English document / Spanish working conversation  

---

Batch 1.3.1 note:
- Carried forward. No content delta from v0.1.3.
- Version bumped for batch alignment only.

## 0. What this document is

This document closes the audit ficha for the future Email Alerts ADG Extension.

It defines:
- the intended role of email alerts
- current state truth
- trigger model
- user preference model
- anti-spam doctrine
- privacy/consent direction
- relationship to licitaciones, Directorio, and Oportunidades
- MVP and future boundaries

This is not:
- an implementation prompt
- a delivery infrastructure spec
- a final email provider decision
- a production-ready consent/legal policy
- a claim that email alerts already exist

---

## 1. Current state

Phase:
- Fase 7

Current state:
- No existe nada

Type:
- service
- delivery layer
- notification utility

Important distinction:
- the ADG OPS `alertas` surface may exist as a stub/preparation surface
- Email Alerts as an ADG Extension does not yet exist as a working service

Current truth:
- no live alert logic
- no activation flow
- no delivery pipeline
- no Formspree implementation
- no automated subscription system
- no working email alert service

---

## 2. One-line doctrine

**Alertas por Email is a future ADG Extension service: it should begin as a controlled no-spam digest for relevant licitaciones, then later expand toward opportunities and profile-driven ecosystem alerts.**

---

## 3. Main role

Selected answer:
- Q4.1 = D

Role:
- first: alerts related to licitaciones
- later: expansion to opportunities, directory/profile logic, and broader ecosystem alerts

Reason:
- licitaciones is the clearest initial data source
- future ADG platform services may create additional alert triggers later

---

## 4. Main user

Selected answer:
- Q4.2 = E

Potential users:
- studios
- agencies
- freelancers
- ADG members
- interested professionals
- possibly broader users if later product strategy allows it

Interpretation:
- all users may be supported, but with different preferences
- initial focus should likely stay close to professional / member utility

---

## 5. Trigger model

Selected answer:
- Q4.3 = E

MVP trigger:
- new licitación published
- matching with discipline + territory

Future triggers may include:
- licitación status changes
- new opportunity published
- new internship/junior opportunity
- new freelance/professional opportunity
- future profile or directory-related updates

Important:
- no trigger should exist unless the underlying data source is trustworthy

---

## 6. Preference model

Selected answer:
- Q4.4 = E as MVP direction

Minimum preferences:
- discipline
- territory
- frequency
- alert type

MVP should support at least:
- discipline
- territory
- frequency

The wider model can later expand to:
- type of alert
- source module
- opportunity type
- profile-driven settings
- saved searches

---

## 7. Frequency

Selected answer:
- Q4.5 = E

Preferred initial frequency:
- weekly digest / controlled digest

Reason:
- avoids spam
- feels curated
- gives ADG editorial control
- reduces delivery pressure
- supports review/technical operation by the team

Avoid as default:
- instant notification spam
- one email per small change
- noisy automated behavior

---

## 8. No-spam doctrine

Selected answer:
- Q4.6 = E

No-spam rules:
- send only if there are real matches
- group matches into digest format
- provide clear unsubscribe
- avoid unnecessary delivery
- avoid repetitive empty emails
- avoid sending every tiny update separately

Hard rule:
**Alertas por Email must feel curated and useful, not noisy or automated for its own sake.**

---

## 9. Public visibility while inactive

Selected answer:
- Q4.7 = B

If inactive:
- may appear as a grey disabled stub in hub/home
- should not imply activation or subscription flow
- should not look like a working service
- should not promise delivery before delivery exists

---

## 10. MVP technology

Selected answer:
- Q4.8 = E

No technology is locked yet.

Not locked:
- Formspree
- Google Forms
- Mailchimp
- Brevo
- newsletter tool
- custom DB
- manual CSV
- manual digest

Rule:
**Process and data contract first; tool choice later.**

---

## 11. Consent and privacy

Selected answer:
- Q4.9 = E

Target consent/privacy model:
- double opt-in
- unsubscribe mandatory
- editable preferences

MVP may be simpler if manual, but the direction should already preserve:
- consent state
- unsubscribe mechanism
- preference management
- clear user control
- no hidden subscription behavior

Hard rule:
**No alert system without consent and unsubscribe.**

---

## 12. Relationship to licitaciones

Selected answer:
- Q4.10 = B

Initial dependency:
- depends on licitaciones first

Future:
- may expand beyond licitaciones

Reason:
- licitaciones provides the clearest starting trigger surface
- data reliability is essential before alerting

Important:
- bad data creates bad alerts
- alerting depends on trustworthy procurement data

---

## 13. Relationship to Directorio de Socios

Selected answer:
- Q4.11 = D

Future relationship:
- member profile may store alert preferences
- claimed profiles may later manage alert settings
- organization/member context may help tailor alerts

Condition:
- only when Directorio/profile system exists and is trustworthy

Do not fake profile-based preferences before profiles exist.

---

## 14. Relationship to Oportunidades ADG

Selected answer:
- Q4.12 = D

Future relationship:
- alerts for new internships/opportunities
- alerts by opportunity type
- alerts by user/profile preference

Status:
- later
- not MVP unless Oportunidades data and publication flow exist

Do not alert opportunities before their moderation/publication model is stable.

---

## 15. Email output format

Selected answer:
- Q4.13 = D

Preferred output:
- brief editorial digest
- cards with useful details

Likely content:
- title
- discipline
- territory
- deadline
- source/module
- short description
- CTA to view item

Tone:
- curated
- useful
- editorial
- not raw automated dump

Important user note:
- the technical team will probably manage this system

Operational implication:
- the first version can be designed for technical-team handling, review, and delivery control
- avoid assuming fully autonomous automation too early

---

## 16. Activation model

Selected answer:
- Q4.14 = D

Activation is not decided yet.

Possible future directions:
- public form with validation
- ADG-managed invite/addition
- profile-based subscription
- manual subscription list
- controlled beta

No activation model should be locked before:
- consent model
- data contract
- delivery workflow
- technical-team operating model

---

## 17. Minimum data contract

Selected answer:
- Q4.15 = D

Minimum useful data contract:
- email
- discipline preference
- territory preference
- frequency
- consent state
- unsubscribe state/mechanism
- source/trigger
- send date
- send state

Additional future fields:
- profile ID if linked
- opportunity type
- saved search ID
- preferred language
- last sent digest
- bounce/error state
- manual review status

---

## 18. MVP boundary

MVP should include:
- non-active grey stub until ready
- clear process/data contract before provider choice
- licitaciones-based alert logic
- discipline + territory matching
- weekly/digest frequency
- no-spam doctrine
- consent/unsubscribe preserved
- technical-team managed operation possible
- no fake automation claims

MVP should not include:
- instant alerts by default
- profile-based settings before profiles exist
- opportunity alerts before Oportunidades exists
- automated delivery before data trust exists
- Formspree/Mailchimp/Brevo decision before process is defined
- public subscription if consent/unsubscribe is not solved

---

## 19. Strong version boundary

Strong version may include:
- editable alert preferences
- double opt-in
- profile-linked subscriptions
- saved searches
- multiple alert types
- opportunity alerts
- digest customization
- language preferences
- admin dashboard
- send logs
- delivery error handling
- unsubscribe management
- technical-team control panel

---

## 20. Risks

Main risks:
- spam
- false promises of automation
- bad data causing bad alerts
- no unsubscribe
- weak consent
- over-automating too early
- confusing alertas surface stub with real email service
- choosing a provider too early
- sending opportunity alerts before Oportunidades is stable
- profile preference logic before Directorio profiles exist

---

## 21. Locked conclusions

- Alertas por Email is an ADG Extension in Fase 7.
- Current state is No existe nada.
- It should start with licitaciones-related alerts.
- It may later expand to Oportunidades, Directorio/profile preferences, and broader ecosystem alerts.
- MVP trigger is new licitación + discipline/territory match.
- MVP preferences should include discipline, territory, and frequency.
- Weekly/digest behavior is preferred first to avoid spam.
- No-spam means real matches, grouped digest, and clear unsubscribe.
- If inactive, it can appear only as a grey disabled stub.
- No MVP technology is locked.
- Process/data contract comes before provider choice.
- Target consent model includes double opt-in, unsubscribe, and editable preferences.
- Email output should feel curated/editorial, with useful cards.
- Technical team will probably manage the first operational model.
- Activation method is not decided yet.
- Minimum data contract includes email, preferences, consent, unsubscribe, source/trigger, send date, and send state.

---

## 22. Delta hooks

Future deltas should define:
- exact MVP operating model
- manual vs semi-automated vs automated delivery
- provider/tool decision
- consent and unsubscribe implementation
- email template
- language handling
- data trigger contract
- admin/technical-team workflow
- relationship to profile preferences
- relationship to Oportunidades alerts

---

## 23. Delta log

### v0.1.3 → v0.1.3.1

- No content change. Version bumped for Batch 1.3.1 alignment.

### v0.1.2 → v0.1.3

- Replaces `ADG_EXTENSIONS_004_ALERTAS_EMAIL_v0.1.2_closed.md` as active closed ficha.
- Pending doc (`_v0.1.2_PENDING`) removed from active batch.

---

## 24. One-line closure

**Closed: Alertas por Email is a future no-spam, curated, technical-team-manageable digest service that should begin from reliable licitaciones matching and only later expand into profile and opportunity-based alerts.**
