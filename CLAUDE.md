# CLAUDE.md — ADG Extensions

## 1. Project Identity

- **Project:** ADG OPS / ADG Extensions
- **Lane:** extensions (this worktree only)
- **Branch:** extensions
- **Recovered HEAD:** ae0df39
- **Version context:** v0.1.3.1
- **Worktree path:** `K:\DEVKIT\projects\adg-ops\adg-ops_extensions`

---

## 2. Absolute Boundary Laws

- Work only inside `adg-ops_extensions`. Never touch `adg-ops_main`, `adg-ops_dev`, `K:\DEVKIT\projects\adg-ops\extensions`, or `CCOS/KAIA/ccos_controller`.
- Never read `docs/support_copys/**` contents. Docs are private by default. Do not publish any doc unless explicitly marked public.
- Never run `git add .` or `git add -A`. Claude must not stage, commit, push, or tag. Operator performs all git mutations.
- No `checkout / reset / restore / clean / prune / repair` unless a dedicated recovery prompt explicitly authorizes it.
- No `npm / build / dev / server` commands unless explicitly authorized per prompt.
- No line-ending normalization and no `.gitattributes` changes unless explicitly authorized. (`core.autocrlf=true` is load-bearing; do not touch.)
- No public/member/personal data activation without a privacy/consent gate.

---

## 3. Current Recovery Status

| Prompt | Result |
|--------|--------|
| TXT 139 | Relink readiness: SAFE_WITH_PRE_SNAPSHOT |
| TXT 140 | Snapshot + pointer-only relink completed |
| TXT 141 | Post-relink validation clean |
| TXT 142 | Opus global status audit accepted |
| TXT 143 | Root CLAUDE.md governance population (this file) |

- Git foundation restored: branch `extensions`, HEAD `ae0df39`.
- Snapshot preserved at: `K:\DEVKIT\projects\adg-ops\_old\adg-ops_extensions_predrelink_snapshot_20260614_020054`
- 5 SAFE_LOCAL untracked docs artifacts remain untouched (4 `docs/extensions_doc/` + 1 `docs/`).
- `core.autocrlf=true` explains TXT 139 byte-level divergence; do not normalize.

---

## 4. Reading Path

1. Read this `CLAUDE.md` first.
2. Read `docs/extensions_doc/ADG_EXTENSIONS_020_ID_TAXONOMY_REGISTRY_v0.1.3.1.md` if ID/route taxonomy is needed.
3. Read `docs/extensions_doc/ADG_EXTENSIONS_029_SHARED_BASE_v0.1.3.1.md` if foundation rules are needed.
4. Read `docs/extensions_doc/ADG_EXTENSIONS_030_MODULE_OVERLAY_MATRIX_v0.1.3.1.md` if module status is needed.
5. Read relevant module contract docs only as needed.
6. `docs/wrkops/` contains local/private protocol context; use for WRKOPS interpretation only, do not publish.
7. Never read `support_copys` contents.

---

## 5. Module Status Summary

| Module | Status |
|--------|--------|
| Hub | Active / honest |
| Licitaciones | Active / honest |
| Mapa | Active / honest |
| Recursos | Active / honest |
| Estadísticas | Active / honest |
| Barómetro | Tombstone / safe hold |
| LAUS Tracker | Partial — baseline verify next; expansion gated |
| Oportunidades / Prácticas | Shell ready; no intake/data activation yet |
| Freelancers / Profesional | HOLD_PROCESS — deep ficha required first |
| Directorio / mapa_socios | HOLD_PRIVACY — gates required |
| Alertas | DEFERRED — consent/delivery/legal gates required (final lane) |
| Shared base + ID taxonomy | Active canon; sync required later |
| Public hygiene / PANOPTES | Required before any push or public readiness |

---

## 6. Construction Model

**Standard lane:**
`Contract → Model → Source → Shell → Adapter → Binding → Validation → Hardening → Closure`

**No real data/process/privacy gate:**
`Contract → Shell → Honest HOLD State → QA → Closure`

---

## 7. Next Roadmap

| Prompt | Task |
|--------|------|
| TXT 143 | Root CLAUDE.md governance population ← **current** |
| TXT 144 | LAUS JSON baseline verification audit |
| TXT 145 | Route/module registry + doc 030 sync |
| TXT 146 | PANOPTES/GRC public hygiene audit |
| TXT 147 | Active-surface QA batch |
| Alertas | Final lane (after all gates) |
| Directorio / mapa_socios | Privacy hold (gates required) |

---

## 8. Required Claude Behavior

- Always state touched-file scope before implementation. Stop if scope expands.
- Always classify feedback as `blocker / debt / later / interesting / not-now` before acting.
- Always preserve roadmap continuity. Do not skip or merge lanes without explicit operator approval.
- Always include `CLEAN STATUS` line in audit/dev status reports.
- Recommend `/clear` after long or high-context audit lanes before the next prompt.
