#!/usr/bin/env python3
"""
tools/f2_apply_persist_plan.py  —  F2 Persistence Apply Tool  (f2apply/1 / v0.6.20)

Guarded production-append executor for f2persist/1 plans.

Requires explicit --apply to mutate data/licitaciones.json.
All guards fail closed: no backup, no report, no production write unless
every guard passes in order.

NEVER commits, pushes, tags, or runs git mutations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


_SCHEMA = "f2apply/1"
_VERSION = "v0.6.20"
_MODE = "F2_APPLY_PERSISTENCE_PLAN"
_EXPECTED_PERSIST_SCHEMA = "f2persist/1"
_ALLOWED_SIDECAR_PREFIX = "_tmp"


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

def _is_safe_sidecar(path_str: str) -> bool:
    """True iff path resolves to a location under _tmp/ relative to CWD."""
    try:
        p = Path(path_str).resolve()
        root = (Path.cwd() / _ALLOWED_SIDECAR_PREFIX).resolve()
        return str(p).startswith(str(root) + os.sep) or p == root
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SHA helper
# ---------------------------------------------------------------------------

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Working tree guard
# ---------------------------------------------------------------------------

def _is_working_tree_clean() -> tuple[bool, str]:
    """Return (is_clean, status_output). Fails closed if git unavailable."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout.strip()
        return (output == ""), output
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, f"git unavailable: {exc}"


# ---------------------------------------------------------------------------
# Enriched / placeholder  (mirrors merge gate v3)
# ---------------------------------------------------------------------------

def _is_enriched(rec: dict) -> bool:
    ck = rec.get("canonical_key")
    docs = rec.get("documents")
    return bool(ck) or (isinstance(docs, list) and len(docs) > 0)


# ---------------------------------------------------------------------------
# Production URL index
# ---------------------------------------------------------------------------

def _build_doc_urls_by_id(prod_data: list[dict]) -> dict[str, set]:
    """notice_id -> set of existing document URLs (union across all records with same id)."""
    idx: dict[str, set] = defaultdict(set)
    for rec in prod_data:
        nid = rec.get("id")
        for d in (rec.get("documents") or []):
            u = d.get("url")
            if u and nid:
                idx[nid].add(u)
    return idx


# ---------------------------------------------------------------------------
# Plan guards  (pre-write validation)
# ---------------------------------------------------------------------------

def _validate_plan(
    plan: dict,
    prod_data: list[dict],
    doc_urls_by_id: dict[str, set],
) -> list[str]:
    """Return list of failure reasons. Empty list means all guards pass."""
    failures: list[str] = []

    # Schema / verdict / write-flag
    if plan.get("schema") != _EXPECTED_PERSIST_SCHEMA:
        failures.append(
            f"schema={plan.get('schema')} expected={_EXPECTED_PERSIST_SCHEMA}"
        )
    if plan.get("final_verdict") != "PERSISTENCE_DRY_RUN_READY":
        failures.append(
            f"final_verdict={plan.get('final_verdict')!r} expected='PERSISTENCE_DRY_RUN_READY'"
        )
    if plan.get("production_write_performed") is not False:
        failures.append(
            f"production_write_performed={plan.get('production_write_performed')!r} expected=false"
        )

    # All invariants must be PASS
    invs = plan.get("invariants", {})
    failed_invs = [k for k, v in invs.items() if v.get("status") != "PASS"]
    if failed_invs:
        failures.append(f"invariants not PASS: {failed_invs}")

    per_record = plan.get("per_record_append_plan", [])
    counts = plan.get("counts", {})

    # Count consistency
    rec_count = counts.get("records_affected")
    if len(per_record) != rec_count:
        failures.append(
            f"len(per_record_append_plan)={len(per_record)} "
            f"!= counts.records_affected={rec_count}"
        )

    sum_append = sum(r.get("append_document_count", 0) for r in per_record)
    plan_total = counts.get("total_new_docs")
    if sum_append != plan_total:
        failures.append(
            f"sum(append_document_count)={sum_append} "
            f"!= counts.total_new_docs={plan_total}"
        )

    # Global URL -> notice_ids for cross-record collision check
    global_url_to_nids: dict[str, set] = defaultdict(set)
    for nid, url_set in doc_urls_by_id.items():
        for u in url_set:
            global_url_to_nids[u].add(nid)

    # Per-record validation
    seen_pairs: set[tuple] = set()
    for i, rec in enumerate(per_record):
        notice_id = rec.get("notice_id")
        pidx = rec.get("production_record_index")
        is_dup = rec.get("is_duplicate_id_group")

        # production_record_index in bounds
        if pidx is None or not (0 <= pidx < len(prod_data)):
            failures.append(
                f"record[{i}] production_record_index={pidx} out of range"
            )
            continue

        prod_rec = prod_data[pidx]

        # id must match notice_id
        if prod_rec.get("id") != notice_id:
            failures.append(
                f"record[{i}] prod_data[{pidx}].id={prod_rec.get('id')!r} "
                f"!= notice_id={notice_id!r}"
            )

        # In a duplicate-id group the target must be enriched
        if is_dup and not _is_enriched(prod_rec):
            failures.append(
                f"record[{i}] notice_id={notice_id} targets placeholder in dup group"
            )

        existing_urls = doc_urls_by_id.get(notice_id, set())

        for j, doc in enumerate(rec.get("documents_to_append", [])):
            d_nid = doc.get("notice_id")
            d_url = doc.get("url")

            if not d_nid or not d_url:
                failures.append(
                    f"record[{i}] doc[{j}] missing notice_id or url"
                )
                continue

            if d_nid != notice_id:
                failures.append(
                    f"record[{i}] doc[{j}] notice_id={d_nid!r} "
                    f"!= record notice_id={notice_id!r}"
                )

            pair = (notice_id, d_url)
            if pair in seen_pairs:
                failures.append(
                    f"record[{i}] doc[{j}] duplicate (notice_id, url)"
                )
            seen_pairs.add(pair)

            if d_url in existing_urls:
                failures.append(
                    f"record[{i}] doc[{j}] URL already in production "
                    f"for notice_id={notice_id!r}"
                )

            other_nids = global_url_to_nids.get(d_url, set()) - {notice_id}
            if other_nids:
                failures.append(
                    f"record[{i}] doc[{j}] URL exists in production "
                    f"under other notice_ids: {list(other_nids)[:3]}"
                )

    return failures


# ---------------------------------------------------------------------------
# Main apply logic
# ---------------------------------------------------------------------------

def run_apply(
    persist_plan_path: str,
    production_path: str,
    expected_sha: str,
    backup_output: str,
    postwrite_report: str,
    do_apply: bool,
    allow_dirty: bool,
    allow_report_overwrite: bool,
    allow_backup_overwrite: bool,
) -> int:

    # ── Guard 1: --apply required ──────────────────────────────────────────
    if not do_apply:
        print(
            "[BLOCKED] --apply flag is required to mutate production.\n"
            "This tool refuses to write anything without explicit --apply.\n"
            "Re-run with --apply after operator review.",
            file=sys.stderr,
        )
        return 10

    # ── Guard 2: backup_output path safety ────────────────────────────────
    if not _is_safe_sidecar(backup_output):
        print(
            f"[BLOCKED] --backup-output '{backup_output}' must be under _tmp/.\n"
            "Refusing to write backup or production.",
            file=sys.stderr,
        )
        return 11

    # ── Guard 3: postwrite_report path safety ─────────────────────────────
    if not _is_safe_sidecar(postwrite_report):
        print(
            f"[BLOCKED] --postwrite-report '{postwrite_report}' must be under _tmp/.\n"
            "Refusing to write report or production.",
            file=sys.stderr,
        )
        return 12

    # ── Guard 4: backup overwrite ─────────────────────────────────────────
    if os.path.exists(backup_output) and not allow_backup_overwrite:
        print(
            f"[BLOCKED] Backup path '{backup_output}' already exists.\n"
            "Pass --allow-backup-overwrite to permit overwriting.",
            file=sys.stderr,
        )
        return 13

    # ── Guard 5: report overwrite ─────────────────────────────────────────
    if os.path.exists(postwrite_report) and not allow_report_overwrite:
        print(
            f"[BLOCKED] Report path '{postwrite_report}' already exists.\n"
            "Pass --allow-report-overwrite to permit overwriting.",
            file=sys.stderr,
        )
        return 14

    # ── Guard 6: working tree clean ───────────────────────────────────────
    is_clean, git_output = _is_working_tree_clean()
    if not is_clean and not allow_dirty:
        print(
            f"[BLOCKED] Working tree is not clean:\n{git_output}\n"
            "Commit or stash changes first, or pass --allow-dirty.",
            file=sys.stderr,
        )
        return 15
    if not is_clean:
        print(f"[WARN] Working tree not clean (--allow-dirty passed):\n{git_output}")

    # ── Guard 7: live production SHA ──────────────────────────────────────
    print(f"[INFO] Computing sha256 of {production_path} ...")
    prewrite_sha = _sha256_file(production_path)
    print(f"[INFO] prewrite_production_sha256={prewrite_sha}")

    if prewrite_sha != expected_sha:
        print(
            f"[BLOCKED] Production SHA mismatch.\n"
            f"  expected : {expected_sha}\n"
            f"  live     : {prewrite_sha}\n"
            "Refusing to proceed.",
            file=sys.stderr,
        )
        return 16

    # ── Load persist plan ─────────────────────────────────────────────────
    print(f"[INFO] Loading persist plan from {persist_plan_path} ...")
    persist_plan_sha = _sha256_file(persist_plan_path)
    with open(persist_plan_path, encoding="utf-8") as fh:
        plan = json.load(fh)
    print(f"[INFO] persist_plan sha256={persist_plan_sha}")

    # Guard 8: cross-check plan's recorded production SHA
    plan_prod_sha = plan.get("inputs", {}).get("production_sha256")
    if plan_prod_sha and plan_prod_sha != prewrite_sha:
        print(
            f"[BLOCKED] Plan inputs.production_sha256={plan_prod_sha}\n"
            f"  does not match live production sha={prewrite_sha}.\n"
            "Production may have changed since the plan was generated.",
            file=sys.stderr,
        )
        return 17

    # ── Load production data ──────────────────────────────────────────────
    print(f"[INFO] Loading production data from {production_path} ...")
    with open(production_path, encoding="utf-8") as fh:
        prod_root = json.load(fh)
    prod_data: list[dict] = prod_root.get("data", [])
    prewrite_record_count = len(prod_data)
    doc_urls_by_id = _build_doc_urls_by_id(prod_data)
    prewrite_doc_url_count = sum(len(s) for s in doc_urls_by_id.values())
    print(f"[INFO] Production records: {prewrite_record_count}")
    print(f"[INFO] Prewrite doc URL count: {prewrite_doc_url_count}")

    # ── Guard 9: plan structural + production-aware validation ────────────
    print("[INFO] Validating persist plan guards ...")
    guard_failures = _validate_plan(plan, prod_data, doc_urls_by_id)
    if guard_failures:
        print(
            f"[BLOCKED] Persist plan failed {len(guard_failures)} guard(s):",
            file=sys.stderr,
        )
        for msg in guard_failures[:20]:
            print(f"  - {msg}", file=sys.stderr)
        if len(guard_failures) > 20:
            print(
                f"  ... and {len(guard_failures) - 20} more.",
                file=sys.stderr,
            )
        return 18
    print("[INFO] All plan guards PASS")

    per_record = plan.get("per_record_append_plan", [])

    # ── Backup ────────────────────────────────────────────────────────────
    print(f"[INFO] Creating backup at {backup_output} ...")
    os.makedirs(os.path.dirname(os.path.abspath(backup_output)), exist_ok=True)
    shutil.copy2(production_path, backup_output)
    backup_sha = _sha256_file(backup_output)
    backup_verified = backup_sha == prewrite_sha
    if not backup_verified:
        print(
            f"[BLOCKED] Backup SHA verification failed.\n"
            f"  expected : {prewrite_sha}\n"
            f"  backup   : {backup_sha}\n"
            "Refusing to write production.",
            file=sys.stderr,
        )
        return 19
    print(f"[INFO] Backup verified sha256={backup_sha}")

    # ── Apply append ──────────────────────────────────────────────────────
    print(f"[INFO] Applying append to {len(per_record)} records ...")
    per_record_summary: list[dict] = []
    total_appended = 0
    records_already_had_docs = 0
    records_gaining_first_doc = 0

    for rec in per_record:
        pidx: int = rec["production_record_index"]
        notice_id: str = rec["notice_id"]
        docs_to_append: list[dict] = rec.get("documents_to_append", [])

        target = prod_data[pidx]
        if target.get("documents") is None:
            target["documents"] = []

        pre_count = len(target["documents"])
        target["documents"].extend(docs_to_append)
        post_count = len(target["documents"])
        appended = post_count - pre_count

        if pre_count > 0:
            records_already_had_docs += 1
        else:
            records_gaining_first_doc += 1
        total_appended += appended

        per_record_summary.append({
            "notice_id": notice_id,
            "production_record_index": pidx,
            "appended": appended,
            "pre_document_count": pre_count,
            "post_document_count": post_count,
        })

    # ── Write production ───────────────────────────────────────────────────
    print(f"[INFO] Writing {production_path} ...")
    serialized = json.dumps(prod_root, ensure_ascii=False, indent=2)
    with open(production_path, "w", encoding="utf-8") as fh:
        fh.write(serialized)
        fh.write("\n")

    # ── Validate post-write JSON ───────────────────────────────────────────
    print("[INFO] Validating post-write JSON ...")
    json_valid = False
    no_record_count_change = False
    post_data: list[dict] = []
    postwrite_doc_url_count = 0

    try:
        with open(production_path, encoding="utf-8") as fh:
            post_root = json.load(fh)
        post_data = post_root.get("data", [])
        json_valid = True
        no_record_count_change = (len(post_data) == prewrite_record_count)
        doc_urls_after = _build_doc_urls_by_id(post_data)
        postwrite_doc_url_count = sum(len(s) for s in doc_urls_after.values())
        print(f"[INFO] Post-write JSON valid. records={len(post_data)}")
    except Exception as exc:
        print(f"[ERROR] Post-write JSON validation failed: {exc}", file=sys.stderr)

    # ── Post-write SHA ────────────────────────────────────────────────────
    postwrite_sha = _sha256_file(production_path)
    sha_changed = postwrite_sha != prewrite_sha
    print(f"[INFO] postwrite_production_sha256={postwrite_sha}")
    print(f"[INFO] sha_changed={sha_changed}")

    # ── Duplicate-pair check on appended data ────────────────────────────
    seen_check: set[tuple] = set()
    no_dup_pairs = True
    for rec in per_record:
        for doc in rec.get("documents_to_append", []):
            pair = (rec.get("notice_id"), doc.get("url"))
            if pair in seen_check:
                no_dup_pairs = False
                break
            seen_check.add(pair)

    all_plan_records_applied = (
        total_appended == plan.get("counts", {}).get("total_new_docs", -1)
    )

    # ── Write post-write report ────────────────────────────────────────────
    now_ts = datetime.now(timezone.utc).isoformat()
    final_verdict = (
        "APPLY_COMPLETED"
        if (json_valid and sha_changed and all_plan_records_applied)
        else "HOLD"
    )

    report = {
        "schema": _SCHEMA,
        "version": _VERSION,
        "mode": _MODE,
        "production_write_performed": True,
        "generated_at": now_ts,
        "inputs": {
            "persist_plan": persist_plan_path,
            "persist_plan_sha256": persist_plan_sha,
            "production": production_path,
            "prewrite_production_sha256": prewrite_sha,
            "expected_production_sha256": expected_sha,
        },
        "backup": {
            "backup_output": backup_output,
            "backup_sha256": backup_sha,
            "backup_verified": backup_verified,
        },
        "apply_summary": {
            "records_affected": len(per_record),
            "total_documents_appended": total_appended,
            "records_already_had_docs": records_already_had_docs,
            "records_gaining_first_doc": records_gaining_first_doc,
            "prewrite_document_url_count": prewrite_doc_url_count,
            "postwrite_document_url_count": postwrite_doc_url_count,
            "prewrite_total_records": prewrite_record_count,
            "postwrite_total_records": len(post_data),
        },
        "validation": {
            "json_valid_after_write": json_valid,
            "production_sha_changed": sha_changed,
            "postwrite_production_sha256": postwrite_sha,
            "all_plan_records_applied": all_plan_records_applied,
            "no_unplanned_record_count_change": no_record_count_change,
            "no_duplicate_append_pairs": no_dup_pairs,
        },
        "per_record_summary": per_record_summary,
        "rollback": {
            "restore_from_backup_instruction": (
                f"To rollback: copy '{backup_output}' back to '{production_path}'. "
                f"Verify sha256 equals prewrite sha256: {prewrite_sha}."
            ),
            "backup_path": backup_output,
        },
        "final_verdict": final_verdict,
    }

    os.makedirs(os.path.dirname(os.path.abspath(postwrite_report)), exist_ok=True)
    with open(postwrite_report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"[INFO] Post-write report written to {postwrite_report}")
    print(f"[INFO] final_verdict={final_verdict}")
    print(f"[INFO] total_documents_appended={total_appended}")
    print(f"[INFO] records_affected={len(per_record)}")

    return 0 if final_verdict == "APPLY_COMPLETED" else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "F2 Persistence Apply Tool (f2apply/1 / v0.6.20) — "
            "guarded production append executor for f2persist/1 plans"
        )
    )
    parser.add_argument(
        "--persist-plan", required=True,
        help="Path to f2persist/1 plan JSON",
    )
    parser.add_argument(
        "--production", required=True,
        help="Path to data/licitaciones.json",
    )
    parser.add_argument(
        "--expected-production-sha", required=True,
        help="Expected SHA256 of production before write",
    )
    parser.add_argument(
        "--backup-output", required=True,
        help="Path for production backup copy (must be under _tmp/)",
    )
    parser.add_argument(
        "--postwrite-report", required=True,
        help="Path for post-write report sidecar JSON (must be under _tmp/)",
    )
    parser.add_argument(
        "--apply", dest="do_apply", action="store_true", default=False,
        help="Required: explicitly authorize production mutation",
    )
    parser.add_argument(
        "--allow-dirty", action="store_true", default=False,
        help="Allow apply even if working tree is dirty (not recommended)",
    )
    parser.add_argument(
        "--allow-report-overwrite", action="store_true", default=False,
        help="Allow overwriting an existing post-write report file",
    )
    parser.add_argument(
        "--allow-backup-overwrite", action="store_true", default=False,
        help="Allow overwriting an existing backup file",
    )
    args = parser.parse_args()

    rc = run_apply(
        persist_plan_path=args.persist_plan,
        production_path=args.production,
        expected_sha=args.expected_production_sha,
        backup_output=args.backup_output,
        postwrite_report=args.postwrite_report,
        do_apply=args.do_apply,
        allow_dirty=args.allow_dirty,
        allow_report_overwrite=args.allow_report_overwrite,
        allow_backup_overwrite=args.allow_backup_overwrite,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
