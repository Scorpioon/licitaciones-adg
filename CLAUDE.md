# CLAUDE.md

Project: ADG Licitaciones / ADG Plataforma Digital

## Working model
- Planning, audits, product decisions, and scope control happen outside the repo conversation flow.
- Implementation happens directly on the repo branch in Claude Code.
- Current working branch: `experimental/wip`
- Always inspect current code and latest SOT before proposing changes.
- Never assume the repo matches an older plan if code says otherwise.

## Core operating rules
- Do not redesign from scratch.
- Preserve the current modular skeleton unless explicitly approved otherwise.
- Prefer surgical edits over broad rewrites.
- Avoid drift: compare plan, code, and latest SOT before touching anything.
- If something is ambiguous, ask or summarize the ambiguity before coding.
- Keep changes phase-scoped. No free extra refactors.
- Keep historical continuity and future extensibility.

## Output / implementation style
- Default implementation mode: direct repo changes in Claude Code.
- When asked for a patch script instead, return one single self-contained `.ps1`.
- Windows-safe / PowerShell 5.1 compatible when patch mode is requested.
- ASCII-safe in comments and string literals when generating `.ps1` scripts.

## Product priorities
1. Data fidelity over visual novelty
2. Stable architecture over fast hacks
3. Clear UX hierarchy over feature sprawl
4. Preserve history, never destructively overwrite master datasets
5. Tools should reduce uncertainty for the design community

## Current architecture intent
- `index.html` = sober modular hub
- `licitaciones.html` = main opportunity / tender analysis tool
- `estadisticas.html` = statistics entry point, with Barometro as internal view/toggle
- `recursos.html` = Herramientas + Biblioteca
- `mapa.html` = territorial view
- `alertas.html` = stub for future alert system
- `about.html` = helpdesk + governance + roadmap + changelog
- `shared.js` = shared UI components layer
- `app.js` = shared data/state/i18n/utils layer

## Data / fetcher rules
- Historical dataset must be preserved and updated incrementally
- Never overwrite the master with a tiny current feed snapshot
- Multi-fetcher architecture is planned, but broad fetcher refactor is not automatic scope
- Hotfixes to preserve master/history are valid if they are narrow and urgent
- Frontend must gracefully handle missing future fields:
  - `documents[]`
  - `doc_update_metadata{}`
  - `duplicate_relations[]`
  - `barometer_signals{}`

## Shared component rules
- Shared components should be reusable and stateless where possible
- New shared UI should live in `shared.js`
- `app.js` remains primarily data/state/i18n/utils, not a dumping ground for large UI components
- Existing globals such as `DISC`, `TERR`, `ADG`, `I18N` may be intentionally used as bare globals if current codebase already depends on that pattern

## Governance / versioning
- Respect SOT workflow
- Latest SOT should be checked before major implementation phases
- File headers and visible footer version should stay aligned with current version target
- Avoid stale comments, stale filenames in headers, or stale architecture copy

## Scope discipline
Before coding, always identify:
- exact phase
- exact files touched
- what is structural vs cleanup
- validation checklist
- risks / open questions

If asked to plan only, do not code.
If asked to implement, stay within the approved phase only.
