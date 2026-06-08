#!/usr/bin/env python3
"""
tools/scheduled_fetch_merge.py
ADG OPS v0.5.0a — Lifecycle-safe scheduled append/merge helper for Fetcher 1.
Prompt 135. Hotfix: accept Fetcher 1 candidate envelopes with top-level metadata.
(v0.4.5aq / Prompt 119: corrected 118 overlap lifecycle precedence bug.)

Usage:
  --check
      Inspect production data, validate shape, report counts. No write.

  --validate-production
      Strict validation of data/licitaciones.json: envelope, lifecycle field
      presence/distribution, OPEN_WITH_AWARD_EVIDENCE safety check.

  --merge-dry-run --candidate <path> --output <path>
      Lifecycle-safe merge of production + candidate. Writes output only to
      provided path (must not be production path). No live fetch.

  --run-live --allow-production-write
      Live fetch → _tmp candidate → lifecycle-safe merge → validate → backup
      → write data/licitaciones.json. Exits non-zero on any failure.
      NOT to be executed in prompt 119.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PRODUCTION_PATH = Path("data/licitaciones.json")
FETCHER_SCRIPT  = Path("fetch_licitaciones.py")
TMP_DIR         = Path("_tmp")
VERSION         = "0.5.0a"
PROMPT_NUM      = "135"
# v0.5.0a - Accept fetcher candidate envelopes with top-level metadata by normalizing candidate meta before validation.

REPORT_CHECK     = TMP_DIR / f"scheduled_merge_check_{PROMPT_NUM}_{VERSION}.json"
REPORT_VALIDATE  = TMP_DIR / f"scheduled_merge_validation_{PROMPT_NUM}_{VERSION}.json"
REPORT_DRY_RUN   = TMP_DIR / f"scheduled_merge_dry_run_{PROMPT_NUM}_{VERSION}.json"
REPORT_CONFLICTS = TMP_DIR / f"scheduled_merge_conflicts_{PROMPT_NUM}_{VERSION}.json"

# Enrichment/UI fields set by the ADG pipeline — always preserved from production.
ENRICHMENT_FIELDS = [
    "enrichment_version",
    "enrichment_rules",
    "rellevancia",
    "kw",
    "cpv",
    "ccaa",
    "lloc",
    "tipus",
]

# Gate envelope fields — always preserved from production, never from candidate.
GATE_FIELDS = frozenset({
    "production_write_gate_prompt",
    "production_write_gate_version",
    "production_write_gate_applied_at",
    "production_write_gate_backup",
})

# Lifecycle decision fields — resolved by overlap precedence in resolve_overlap_lifecycle(),
# not blindly preserved. (Prompt 119 correction: 118 preserved these unconditionally.)
LIFECYCLE_DECISION_FIELDS = frozenset({
    "active_opportunity_eligible",
    "lifecycle_review_required",
    "lifecycle_category",
    "dry_run_recommended_status",
    "dry_run_lifecycle_note",
})

# Lists that are safely unioned (production values preserved, candidate values appended).
LIST_UNION_FIELDS = [
    "historial",
    "notice_history",
    "award_results",
    "documents",
    "related_contract_ids",
    "sources_seen",
    "duplicate_relations",
]

# Fields where value changes are logged to the conflicts report.
SCALAR_CONFLICT_FIELDS = {
    "estat", "status",
    "adjudicatari", "adjudicatario",
    "pressupost", "budget",
    "data_pub", "data_limit",
    "organisme",
    "titol", "title", "titulo",
    "url",
}

PROVENANCE_PREFIXES = ("recovery_", "delta_", "merge_")

# Status keyword sets (module-level so both classify_lifecycle and
# resolve_overlap_lifecycle use the same definitions).
_OPEN_KWS   = ("vigent", "en plazo", "activ", "publicad", "anunciad", "open", "actiu")
_CLOSED_KWS = ("adjudicad", "award", "desiert", "deserta", "closed", "cancelad",
               "resolt", "resolut", "terminad", "finalizad", "archivad")

# Fields skipped when iterating the candidate in merge_overlap.
# LIFECYCLE_DECISION_FIELDS are excluded here — set by resolve_overlap_lifecycle().
_SKIP_FROM_CANDIDATE = set(ENRICHMENT_FIELDS) | GATE_FIELDS | LIFECYCLE_DECISION_FIELDS | {"source_merge_class"}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def ts_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        sys.exit(f"[ERROR] File not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[ERROR] Invalid JSON in {path}: {exc}")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"  wrote: {path}")


# ---------------------------------------------------------------------------
# Merge-key resolution (priority: contract_folder_id > canonical_key > id > url)
# ---------------------------------------------------------------------------

def get_merge_key(rec: dict) -> str | None:
    return (
        rec.get("contract_folder_id")
        or rec.get("canonical_key")
        or rec.get("id")
        or rec.get("url")
        or None
    )


def build_index(records: list) -> dict:
    idx: dict = {}
    for rec in records:
        key = get_merge_key(rec)
        if key and key not in idx:
            idx[key] = rec
    return idx


def is_provenance_field(key: str) -> bool:
    return any(key.startswith(p) for p in PROVENANCE_PREFIXES)


# ---------------------------------------------------------------------------
# Lifecycle classification for candidate-only records
# ---------------------------------------------------------------------------

def classify_lifecycle(rec: dict) -> tuple[str, bool, bool]:
    """Return (lifecycle_category, active_opportunity_eligible, lifecycle_review_required)."""
    estat = (rec.get("estat") or rec.get("status") or "").lower()
    adjudicatari = rec.get("adjudicatari") or rec.get("adjudicatario") or ""
    award_results = rec.get("award_results") or []
    has_award = bool(adjudicatari) or bool(award_results)

    is_open   = any(k in estat for k in _OPEN_KWS)
    is_closed = any(k in estat for k in _CLOSED_KWS)

    if is_open and not has_award:
        return "CLEAR_OPEN", True, False
    if is_open and has_award:
        return "OPEN_WITH_AWARD_EVIDENCE", False, True
    if is_closed or has_award:
        return "CLEAR_AWARDED", False, False
    return "UNKNOWN_LIFECYCLE", False, True


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def resolve_overlap_lifecycle(prod_rec: dict, cand_rec: dict) -> dict:
    """
    Determine lifecycle fields for an overlap (production + candidate) record.

    Candidate evidence takes precedence when it is stronger than the preserved
    production state. This corrects the 118 bug where lifecycle fields were
    blindly preserved even when the candidate brought closed/awarded evidence.

    Precedence rules:
      1. Candidate clearly closed/awarded/deserted → CLEAR_AWARDED, active=False.
      2. Candidate open-like but has award evidence → OPEN_WITH_AWARD_EVIDENCE, active=False.
      3. Candidate has award evidence, status unclear → CLEAR_AWARDED, active=False.
      4. Candidate clearly open, no award evidence → preserve production if stronger
         (CLEAR_AWARDED/OWA); otherwise CLEAR_OPEN, active=True.
      5. Candidate unclear → preserve production if stronger; else UNKNOWN_LIFECYCLE.

    Returns dict: category, active, review, and optionally note, recommended_status.
    """
    estat        = (cand_rec.get("estat") or cand_rec.get("status") or "").lower()
    adjudicatari = cand_rec.get("adjudicatari") or cand_rec.get("adjudicatario") or ""
    award_results = cand_rec.get("award_results") or []
    has_award    = bool(adjudicatari) or bool(award_results)

    is_open   = any(k in estat for k in _OPEN_KWS)
    is_closed = any(k in estat for k in _CLOSED_KWS)

    prod_lc     = prod_rec.get("lifecycle_category")
    prod_review = bool(prod_rec.get("lifecycle_review_required", False))

    # Rule 1: Candidate clearly closed/awarded/deserted → override to CLEAR_AWARDED.
    if is_closed:
        raw = (cand_rec.get("estat") or cand_rec.get("status") or "").strip()
        return {
            "category": "CLEAR_AWARDED",
            "active":   False,
            "review":   False,
            "recommended_status": raw or None,
        }

    # Rule 2: Candidate open-like with award evidence → OPEN_WITH_AWARD_EVIDENCE.
    if is_open and has_award:
        return {
            "category": "OPEN_WITH_AWARD_EVIDENCE",
            "active":   False,
            "review":   True,
            "note": (
                "Scheduled candidate has open-like status with award evidence; "
                "do not display as active opportunity."
            ),
        }

    # Rule 3: Award evidence present, status unclear → treat as awarded.
    if has_award and not is_open and not is_closed:
        return {"category": "CLEAR_AWARDED", "active": False, "review": False}

    # Rule 4: Candidate clearly open, no award evidence.
    if is_open and not has_award:
        if prod_lc in ("CLEAR_AWARDED", "OPEN_WITH_AWARD_EVIDENCE"):
            # Production is more conservative — preserve it.
            return {"category": prod_lc, "active": False, "review": prod_review}
        return {"category": "CLEAR_OPEN", "active": True, "review": False}

    # Rule 5: Candidate status unclear, no award evidence.
    if prod_lc in ("CLEAR_AWARDED", "OPEN_WITH_AWARD_EVIDENCE"):
        return {"category": prod_lc, "active": False, "review": prod_review}
    if prod_lc == "CLEAR_OPEN":
        return {"category": "CLEAR_OPEN", "active": True, "review": False}
    return {"category": "UNKNOWN_LIFECYCLE", "active": False, "review": True}


def merge_overlap(prod_rec: dict, cand_rec: dict) -> tuple[dict, list]:
    """
    Start from production record. Update with candidate's fresh-fetch fields.

    Lifecycle decision fields (category, active, review) are resolved by
    resolve_overlap_lifecycle() rather than blindly preserved from production.
    Enrichment, gate, provenance, and source_merge_class are always from production.
    LIST_UNION_FIELDS are safely unioned. Scalar conflicts are logged.
    """
    result: dict = dict(prod_rec)
    conflicts: list = []

    for key, cand_val in cand_rec.items():
        if key in _SKIP_FROM_CANDIDATE:
            continue
        if is_provenance_field(key):
            continue
        if key in LIST_UNION_FIELDS:
            continue  # handled below

        prod_val = result.get(key)
        if key in SCALAR_CONFLICT_FIELDS and key in result and prod_val != cand_val:
            conflicts.append({"key": key, "production": prod_val, "candidate": cand_val})

        result[key] = cand_val

    # Safely union list fields (production values preserved, candidate values appended).
    for field in LIST_UNION_FIELDS:
        prod_list = result.get(field) if isinstance(result.get(field), list) else []
        cand_list = cand_rec.get(field) if isinstance(cand_rec.get(field), list) else []
        if prod_list or cand_list:
            merged_list = list(prod_list)
            for item in cand_list:
                if item not in merged_list:
                    merged_list.append(item)
            result[field] = merged_list

    # Resolve lifecycle via candidate evidence precedence (119 correction).
    lc = resolve_overlap_lifecycle(prod_rec, cand_rec)
    result["lifecycle_category"]          = lc["category"]
    result["active_opportunity_eligible"] = lc["active"]
    result["lifecycle_review_required"]   = lc["review"]
    if lc.get("note"):
        result["dry_run_lifecycle_note"]     = lc["note"]
    if lc.get("recommended_status"):
        result["dry_run_recommended_status"] = lc["recommended_status"]

    return result, conflicts


def build_candidate_record(cand_rec: dict) -> dict:
    """Assign lifecycle classification to a candidate-only (new) record."""
    result = dict(cand_rec)
    lc_cat, active, review = classify_lifecycle(cand_rec)
    result["lifecycle_category"] = lc_cat
    result["active_opportunity_eligible"] = active
    result["lifecycle_review_required"] = review
    result["source_merge_class"] = "SCHEDULED_CANDIDATE_ADDED"
    # Enforce: OPEN_WITH_AWARD_EVIDENCE must never be active.
    if lc_cat == "OPEN_WITH_AWARD_EVIDENCE":
        result["active_opportunity_eligible"] = False
    return result


# ---------------------------------------------------------------------------
# Candidate envelope normalization
# ---------------------------------------------------------------------------

def normalize_candidate_envelope(candidate_data: dict, label: str = "candidate") -> dict:
    """
    Accept either canonical {meta, data} or fetcher top-level-metadata + data.
    Shape A: {"meta": {...}, "data": [...]} — returned unchanged.
    Shape B: {"generated_at": ..., "data": [...], ...} — top-level keys except
             "data" are moved into meta, returning {"meta": {...}, "data": [...]}.
    Non-dict or missing "data" inputs are returned as-is for validate_structure to catch.
    Never applied to production data.
    """
    if not isinstance(candidate_data, dict):
        return candidate_data
    if not isinstance(candidate_data.get("data"), list):
        return candidate_data
    if isinstance(candidate_data.get("meta"), dict):
        return candidate_data
    meta = {k: v for k, v in candidate_data.items() if k != "data"}
    return {"meta": meta, "data": candidate_data["data"]}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_structure(data: dict, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        errors.append(f"{label}: root is not a dict")
        return errors
    if "data" not in data:
        errors.append(f"{label}: missing 'data' key")
    elif not isinstance(data["data"], list):
        errors.append(f"{label}: 'data' is not a list")
    if "meta" not in data:
        errors.append(f"{label}: missing 'meta' key")
    return errors


def validate_lifecycle_integrity(records: list) -> tuple[bool, list[str]]:
    """OPEN_WITH_AWARD_EVIDENCE must not have active_opportunity_eligible=True."""
    issues: list[str] = []
    for i, rec in enumerate(records):
        key = get_merge_key(rec) or f"index:{i}"
        if (
            rec.get("lifecycle_category") == "OPEN_WITH_AWARD_EVIDENCE"
            and rec.get("active_opportunity_eligible") is True
        ):
            issues.append(
                f"{key}: OPEN_WITH_AWARD_EVIDENCE has active_opportunity_eligible=True (UNSAFE)"
            )
    return (len(issues) == 0), issues


def count_lifecycle(records: list) -> dict:
    return {
        "total": len(records),
        "active_true": sum(1 for r in records if r.get("active_opportunity_eligible") is True),
        "review_true": sum(1 for r in records if r.get("lifecycle_review_required") is True),
        "rs_count": sum(1 for r in records if r.get("lifecycle_category") == "OPEN_WITH_AWARD_EVIDENCE"),
        "clear_open": sum(1 for r in records if r.get("lifecycle_category") == "CLEAR_OPEN"),
        "clear_awarded": sum(1 for r in records if r.get("lifecycle_category") == "CLEAR_AWARDED"),
        "unknown": sum(1 for r in records if r.get("lifecycle_category") == "UNKNOWN_LIFECYCLE"),
        "no_lc": sum(1 for r in records if not r.get("lifecycle_category")),
    }


# ---------------------------------------------------------------------------
# Report scaffold
# ---------------------------------------------------------------------------

def base_report(mode: str, prod_count: int) -> dict:
    return {
        "mode": mode,
        "version": VERSION,
        "prompt": PROMPT_NUM,
        "generated_at": ts_now(),
        "production_write_performed": False,
        "production_count_before": prod_count,
        "candidate_count": 0,
        "merged_count": 0,
        "overlap_count": 0,
        "production_only_preserved": 0,
        "candidate_only_added": 0,
        "active_true": 0,
        "review_true": 0,
        "rs_count": 0,
        "lifecycle_preservation_pass": True,
        "final_verdict": "PENDING",
    }


# ---------------------------------------------------------------------------
# Mode: --check
# ---------------------------------------------------------------------------

def run_check(args) -> None:
    print(f"\n[check] Loading {PRODUCTION_PATH}...")
    prod_data = load_json(PRODUCTION_PATH)
    errs = validate_structure(prod_data, "production")
    if errs:
        for e in errs:
            print(f"  [FAIL] {e}")
        sys.exit(1)

    rows   = prod_data["data"]
    meta   = prod_data.get("meta", {})
    counts = count_lifecycle(rows)
    lc_ok, lc_issues = validate_lifecycle_integrity(rows)
    gate   = meta.get("production_write_gate_prompt", "N/A")

    print(f"  records      : {counts['total']}")
    print(f"  gate         : {gate}")
    print(f"  active_true  : {counts['active_true']}")
    print(f"  review_true  : {counts['review_true']}")
    print(f"  rs_count     : {counts['rs_count']}")
    print(f"  clear_open   : {counts['clear_open']}")
    print(f"  clear_awarded: {counts['clear_awarded']}")
    print(f"  unknown      : {counts['unknown']}")
    print(f"  no_lc        : {counts['no_lc']}")
    print(f"  lc_pass      : {lc_ok}")
    for issue in lc_issues[:5]:
        print(f"  [ISSUE] {issue}")

    verdict = "PASS" if lc_ok else "FAIL: lifecycle integrity issues"
    report = base_report("check", len(rows))
    report.update({
        "gate_prompt": gate,
        "active_true": counts["active_true"],
        "review_true": counts["review_true"],
        "rs_count": counts["rs_count"],
        "lifecycle_counts": counts,
        "lifecycle_preservation_pass": lc_ok,
        "lifecycle_issues": lc_issues,
        "final_verdict": verdict,
    })
    write_json(REPORT_CHECK, report)
    print(f"\n[check] verdict: {verdict}")
    if not lc_ok:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Mode: --validate-production
# ---------------------------------------------------------------------------

def run_validate_production(args) -> None:
    print(f"\n[validate-production] Loading {PRODUCTION_PATH}...")
    prod_data = load_json(PRODUCTION_PATH)
    errs = validate_structure(prod_data, "production")
    if errs:
        for e in errs:
            print(f"  [FAIL] {e}")
        sys.exit(1)

    rows   = prod_data["data"]
    meta   = prod_data.get("meta", {})
    counts = count_lifecycle(rows)
    lc_ok, lc_issues = validate_lifecycle_integrity(rows)
    gate   = meta.get("production_write_gate_prompt")

    validation_errors: list[str] = []

    if not gate:
        validation_errors.append("meta.production_write_gate_prompt missing")

    missing_lc = sum(1 for r in rows if not r.get("lifecycle_category"))
    if missing_lc:
        validation_errors.append(f"{missing_lc} records missing lifecycle_category")

    missing_active = sum(1 for r in rows if "active_opportunity_eligible" not in r)
    if missing_active:
        validation_errors.append(f"{missing_active} records missing active_opportunity_eligible")

    if not lc_ok:
        validation_errors.extend(lc_issues)

    for msg in validation_errors:
        print(f"  [ISSUE] {msg}")

    print(f"  records      : {counts['total']}")
    print(f"  gate         : {gate}")
    print(f"  active_true  : {counts['active_true']}")
    print(f"  review_true  : {counts['review_true']}")
    print(f"  rs_count     : {counts['rs_count']}")
    print(f"  no_lc        : {counts['no_lc']}")
    print(f"  lc_pass      : {lc_ok}")

    verdict = "PASS" if not validation_errors else "FAIL"
    print(f"\n[validate-production] verdict: {verdict}")

    report = base_report("validate-production", len(rows))
    report.update({
        "gate_prompt": gate,
        "gate_version": meta.get("production_write_gate_version"),
        "gate_applied_at": meta.get("production_write_gate_applied_at"),
        "active_true": counts["active_true"],
        "review_true": counts["review_true"],
        "rs_count": counts["rs_count"],
        "missing_lifecycle_category_count": missing_lc,
        "missing_active_eligible_count": missing_active,
        "lifecycle_counts": counts,
        "lifecycle_preservation_pass": lc_ok,
        "validation_errors": validation_errors,
        "final_verdict": verdict,
    })
    write_json(REPORT_VALIDATE, report)

    if validation_errors:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Mode: --merge-dry-run
# ---------------------------------------------------------------------------

def run_merge_dry_run(args) -> None:
    if not args.candidate:
        sys.exit("[ERROR] --merge-dry-run requires --candidate <path>")
    if not args.output:
        sys.exit("[ERROR] --merge-dry-run requires --output <path>")

    output_path = Path(args.output)

    # Safety: never write to production in dry-run mode.
    try:
        if output_path.resolve() == PRODUCTION_PATH.resolve():
            sys.exit("[ERROR] --output cannot target data/licitaciones.json in dry-run mode.")
    except Exception:
        pass

    candidate_path = Path(args.candidate)

    print(f"\n[merge-dry-run] Loading production from {PRODUCTION_PATH}...")
    prod_data = load_json(PRODUCTION_PATH)
    errs = validate_structure(prod_data, "production")
    if errs:
        for e in errs:
            print(f"  [FAIL] {e}")
        sys.exit(1)

    print(f"[merge-dry-run] Loading candidate from {candidate_path}...")
    cand_data = load_json(candidate_path)
    cand_data = normalize_candidate_envelope(cand_data, "candidate")
    errs = validate_structure(cand_data, "candidate")
    if errs:
        for e in errs:
            print(f"  [FAIL] {e}")
        sys.exit(1)

    # Refuse partial/failed candidate unless explicitly overridden.
    cand_meta = cand_data.get("meta", {})
    if cand_meta.get("is_partial") is True:
        rs = str(cand_meta.get("run_status", "")).lower()
        if "success" not in rs:
            sys.exit(
                "[ERROR] Candidate has is_partial=True and run_status is not success-like. "
                "Refusing merge. Use an explicit override flag if this is intentional."
            )

    prod_rows  = prod_data["data"]
    cand_rows  = cand_data["data"]
    prod_meta  = prod_data.get("meta", {})

    prod_index = build_index(prod_rows)
    cand_index = build_index(cand_rows)

    merged_rows: list = []
    all_conflicts: list = []
    overlap_keys: list = []
    candidate_only_keys: list = []

    # Process production records: merge overlaps, preserve production-only.
    for rec in prod_rows:
        key = get_merge_key(rec)
        if key and key in cand_index:
            merged_rec, conflicts = merge_overlap(rec, cand_index[key])
            merged_rows.append(merged_rec)
            if conflicts:
                all_conflicts.extend({"merge_key": key, **c} for c in conflicts)
            overlap_keys.append(key)
        else:
            merged_rows.append(dict(rec))

    # Append candidate-only records (not in production).
    for cand_rec in cand_rows:
        key = get_merge_key(cand_rec)
        if not key or key not in prod_index:
            merged_rows.append(build_candidate_record(cand_rec))
            candidate_only_keys.append(key)

    prod_only_count = len(prod_rows) - len(overlap_keys)
    merged_counts = count_lifecycle(merged_rows)
    lc_ok, lc_issues = validate_lifecycle_integrity(merged_rows)

    # Build merged output envelope (never modify production_write_gate fields).
    output_meta = dict(prod_meta)
    output_meta.update({
        "scheduled_merge_mode": "dry-run",
        "scheduled_merge_prompt": PROMPT_NUM,
        "scheduled_merge_version": VERSION,
        "scheduled_merge_generated_at": ts_now(),
        "production_write_performed": False,
        "candidate_path": str(candidate_path),
        "overlap_count": len(overlap_keys),
        "candidate_only_added": len(candidate_only_keys),
        "production_only_preserved": prod_only_count,
    })
    write_json(output_path, {"meta": output_meta, "data": merged_rows})

    # Dry-run summary report.
    verdict = "PASS" if lc_ok else "FAIL: lifecycle integrity issues after merge"
    report = base_report("merge-dry-run", len(prod_rows))
    report.update({
        "candidate_count": len(cand_rows),
        "merged_count": len(merged_rows),
        "overlap_count": len(overlap_keys),
        "production_only_preserved": prod_only_count,
        "candidate_only_added": len(candidate_only_keys),
        "active_true": merged_counts["active_true"],
        "review_true": merged_counts["review_true"],
        "rs_count": merged_counts["rs_count"],
        "lifecycle_counts": merged_counts,
        "lifecycle_preservation_pass": lc_ok,
        "lifecycle_issues": lc_issues,
        "conflict_count": len(all_conflicts),
        "output_path": str(output_path),
        "final_verdict": verdict,
    })
    write_json(REPORT_DRY_RUN, report)

    if all_conflicts:
        write_json(REPORT_CONFLICTS, {
            "mode": "merge-dry-run",
            "generated_at": ts_now(),
            "conflict_count": len(all_conflicts),
            "conflicts": all_conflicts,
        })

    print(f"\n  production records  : {len(prod_rows)}")
    print(f"  candidate records   : {len(cand_rows)}")
    print(f"  overlap merged      : {len(overlap_keys)}")
    print(f"  candidate only added: {len(candidate_only_keys)}")
    print(f"  production preserved: {prod_only_count}")
    print(f"  merged total        : {len(merged_rows)}")
    print(f"  active_true         : {merged_counts['active_true']}")
    print(f"  review_true         : {merged_counts['review_true']}")
    print(f"  rs_count            : {merged_counts['rs_count']}")
    print(f"  conflicts logged    : {len(all_conflicts)}")
    print(f"  lc_pass             : {lc_ok}")
    for issue in lc_issues:
        print(f"  [ISSUE] {issue}")
    print(f"\n[merge-dry-run] verdict: {verdict}")

    if not lc_ok:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Mode: --run-live  (NOT executed in prompt 118)
# ---------------------------------------------------------------------------

def run_live(args) -> None:
    """
    Live fetch → _tmp candidate → lifecycle-safe merge → validate → backup
    → write data/licitaciones.json.

    Requires --allow-production-write. NOT to be executed in prompt 118.
    Authorized only after operator review of prompt 119+ commit gate.
    """
    if not args.allow_production_write:
        sys.exit(
            "[ERROR] --run-live requires --allow-production-write.\n"
            "This mode must NOT be executed in prompt 118.\n"
            "Authorized only in prompt 119+ after operator commit gate approval."
        )

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate_path = TMP_DIR / f"scheduled_live_candidate_{ts}.json"

    # Safety: ensure candidate never resolves to production path.
    try:
        if candidate_path.resolve() == PRODUCTION_PATH.resolve():
            sys.exit("[ERROR] Candidate path resolves to production path. Aborting.")
    except Exception:
        pass

    print(f"[run-live] Fetching to: {candidate_path}")
    result = subprocess.run(
        [
            sys.executable, str(FETCHER_SCRIPT),
            "--output", str(candidate_path),
            "--min-score", "20",
            "--no-progress",
        ],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout[-3000:])
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr[-1000:], file=sys.stderr)
        sys.exit(f"[ERROR] Fetcher exited with code {result.returncode}")

    # Validate candidate.
    cand_data = load_json(candidate_path)
    cand_data = normalize_candidate_envelope(cand_data, "candidate")
    errs = validate_structure(cand_data, "candidate")
    if errs:
        sys.exit(f"[ERROR] Candidate invalid: {errs}")

    cand_meta = cand_data.get("meta", {})
    if cand_meta.get("is_partial") is True:
        rs = str(cand_meta.get("run_status", "")).lower()
        if "success" not in rs:
            sys.exit(
                "[ERROR] Partial/failed candidate — refusing production write. "
                "Investigate fetcher output before re-running."
            )

    # Load production.
    prod_data = load_json(PRODUCTION_PATH)
    errs = validate_structure(prod_data, "production")
    if errs:
        sys.exit(f"[ERROR] Production invalid: {errs}")

    prod_rows  = prod_data["data"]
    cand_rows  = cand_data["data"]
    prod_index = build_index(prod_rows)
    cand_index = build_index(cand_rows)

    merged_rows: list = []
    all_conflicts: list = []
    overlap_keys: list = []
    candidate_only_keys: list = []

    for rec in prod_rows:
        key = get_merge_key(rec)
        if key and key in cand_index:
            merged_rec, conflicts = merge_overlap(rec, cand_index[key])
            merged_rows.append(merged_rec)
            if conflicts:
                all_conflicts.extend({"merge_key": key, **c} for c in conflicts)
            overlap_keys.append(key)
        else:
            merged_rows.append(dict(rec))

    for cand_rec in cand_rows:
        key = get_merge_key(cand_rec)
        if not key or key not in prod_index:
            merged_rows.append(build_candidate_record(cand_rec))
            candidate_only_keys.append(key)

    lc_ok, lc_issues = validate_lifecycle_integrity(merged_rows)
    if not lc_ok:
        sys.exit(f"[ERROR] Lifecycle integrity failed before write: {lc_issues[:3]}")

    # Backup production before write.
    backup_dir = Path("data/_backup")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"licitaciones_{ts}_pre_scheduled.json"
    shutil.copy2(PRODUCTION_PATH, backup_path)
    print(f"[run-live] Backup: {backup_path}")

    # Write production.
    prod_meta = dict(prod_data.get("meta", {}))
    prod_meta.update({
        "scheduled_merge_mode": "run-live",
        "scheduled_merge_prompt": PROMPT_NUM,
        "scheduled_merge_version": VERSION,
        "scheduled_merge_applied_at": ts_now(),
        "production_write_performed": True,
        "backup_path": str(backup_path),
    })
    write_json(PRODUCTION_PATH, {"meta": prod_meta, "data": merged_rows})
    print(f"[run-live] Written: {PRODUCTION_PATH} ({len(merged_rows)} records)")

    if all_conflicts:
        conflict_path = TMP_DIR / f"scheduled_merge_conflicts_live_{ts}.json"
        write_json(conflict_path, {
            "mode": "run-live",
            "generated_at": ts_now(),
            "conflict_count": len(all_conflicts),
            "conflicts": all_conflicts,
        })

    merged_counts = count_lifecycle(merged_rows)
    print(
        f"[run-live] merged={len(merged_rows)} "
        f"overlap={len(overlap_keys)} added={len(candidate_only_keys)} "
        f"active={merged_counts['active_true']} review={merged_counts['review_true']} "
        f"rs={merged_counts['rs_count']}"
    )
    print("[run-live] verdict: PASS")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        prog="scheduled_fetch_merge.py",
        description=f"ADG OPS scheduled append/merge helper v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tools/scheduled_fetch_merge.py --check\n"
            "  python tools/scheduled_fetch_merge.py --validate-production\n"
            "  python tools/scheduled_fetch_merge.py --merge-dry-run "
            "--candidate _tmp/fixture.json --output _tmp/out.json\n"
            "  python tools/scheduled_fetch_merge.py --run-live --allow-production-write\n"
        ),
    )
    ap.add_argument("--check",                  action="store_true",
                    help="Inspect production data and report counts.")
    ap.add_argument("--validate-production",    action="store_true", dest="validate_production",
                    help="Strict validation of data/licitaciones.json.")
    ap.add_argument("--merge-dry-run",          action="store_true", dest="merge_dry_run",
                    help="Lifecycle-safe merge dry run (no production write).")
    ap.add_argument("--run-live",               action="store_true", dest="run_live",
                    help="Live fetch + merge + write (requires --allow-production-write).")
    ap.add_argument("--candidate",              metavar="PATH",
                    help="Candidate JSON path for --merge-dry-run.")
    ap.add_argument("--output",                 metavar="PATH",
                    help="Output path for merged JSON (--merge-dry-run).")
    ap.add_argument("--allow-production-write", action="store_true", dest="allow_production_write",
                    help="Required flag for --run-live to permit production write.")

    args = ap.parse_args()

    active_modes = [args.check, args.validate_production, args.merge_dry_run, args.run_live]
    if sum(active_modes) != 1:
        ap.print_help()
        sys.exit(1)

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    if args.check:
        run_check(args)
    elif args.validate_production:
        run_validate_production(args)
    elif args.merge_dry_run:
        run_merge_dry_run(args)
    elif args.run_live:
        run_live(args)


if __name__ == "__main__":
    main()
