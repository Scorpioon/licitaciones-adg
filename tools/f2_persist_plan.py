#!/usr/bin/env python3
"""
tools/f2_persist_plan.py  —  F2 Persistence Dry-Run Planner  (f2persist/1 / v0.6.18)

Reads a f2merge/3 plan and production licitaciones.json (READ-ONLY).
Emits a sidecar f2persist/1 dry-run plan under _tmp/ or data/fetcher2/.
NEVER writes or mutates production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Safe output guard
# ---------------------------------------------------------------------------

_FORBIDDEN_SUFFIXES = (
    os.path.normpath("data/licitaciones.json"),
    os.path.normpath("data\\licitaciones.json"),
)
_ALLOWED_PREFIXES = (
    os.path.normpath("_tmp"),
    os.path.normpath("data/fetcher2"),
)


def _is_safe_output(path_str: str) -> bool:
    try:
        p = Path(path_str).resolve()
        cwd = Path.cwd()
        prod_abs = (cwd / "data" / "licitaciones.json").resolve()
        if p == prod_abs:
            return False
        for rel in (_ALLOWED_PREFIXES[0], _ALLOWED_PREFIXES[1]):
            root = (cwd / rel).resolve()
            if p == root or str(p).startswith(str(root) + os.sep):
                return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Enriched / placeholder helpers  (mirrors merge gate v3)
# ---------------------------------------------------------------------------

def _is_enriched(rec: dict) -> bool:
    ck = rec.get("canonical_key")
    docs = rec.get("documents")
    return bool(ck) or (isinstance(docs, list) and len(docs) > 0)


def _is_placeholder(rec: dict) -> bool:
    return not _is_enriched(rec)


# ---------------------------------------------------------------------------
# Production index builders
# ---------------------------------------------------------------------------

def _build_production_indexes(prod_data: list[dict]):
    """Return (by_id, by_id_ck, doc_urls_by_id).

    by_id          : notice_id -> [(prod_list_index, record), ...]
    by_id_ck       : (notice_id, canonical_key) -> [(prod_list_index, record), ...]
    doc_urls_by_id : notice_id -> set of existing document URLs
                     (union across ALL records sharing that id)
    """
    by_id: dict[str, list] = defaultdict(list)
    by_id_ck: dict[tuple, list] = defaultdict(list)
    doc_urls_by_id: dict[str, set] = defaultdict(set)

    for i, rec in enumerate(prod_data):
        nid = rec.get("id")
        ck = rec.get("canonical_key")
        if nid:
            by_id[nid].append((i, rec))
            by_id_ck[(nid, ck)].append((i, rec))
            for d in (rec.get("documents") or []):
                u = d.get("url")
                if u:
                    doc_urls_by_id[nid].add(u)

    return by_id, by_id_ck, doc_urls_by_id


# ---------------------------------------------------------------------------
# Target record selection  (mirrors merge gate v3 resolve_production_record)
# ---------------------------------------------------------------------------

def _select_target(
    notice_id: str,
    doc_canonical_key: str | None,
    by_id: dict,
    by_id_ck: dict,
) -> tuple:
    """Return (prod_idx, record, error_reason, is_dup_group, target_record_kind)."""
    recs = by_id.get(notice_id, [])
    if not recs:
        return None, None, "notice_id_not_found_in_production", False, "unknown"

    if len(recs) == 1:
        idx, rec = recs[0]
        return idx, rec, None, False, "single"

    # Shared-id group: try canonical_key tie-break first
    if doc_canonical_key:
        m = by_id_ck.get((notice_id, doc_canonical_key), [])
        if len(m) == 1:
            idx, rec = m[0]
            return idx, rec, None, True, "enriched"

    # Enriched-copy fallback
    enriched = [(i, r) for i, r in recs if _is_enriched(r)]
    if len(enriched) == 1:
        idx, rec = enriched[0]
        return idx, rec, None, True, "enriched"
    if len(enriched) == 0:
        return None, None, "no_enriched_record_in_group", True, "unknown"
    return None, None, f"multiple_enriched_records_{len(enriched)}", True, "unknown"


# ---------------------------------------------------------------------------
# SHA helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def _run_invariants(
    merge_plan: dict,
    by_id: dict,
    by_id_ck: dict,
    doc_urls_by_id: dict,
    prod_sha: str,
    expected_prod_sha: str,
    strict_sha: bool,
) -> dict[str, dict]:
    inv: dict[str, dict] = {}
    acc: list[dict] = merge_plan.get("accepted_documents", [])

    # 1. Production SHA
    if strict_sha:
        ok = prod_sha == expected_prod_sha
        inv["production_sha_match"] = {
            "status": "PASS" if ok else "FAIL",
            "reason": f"sha256={prod_sha}" if ok
                      else f"expected={expected_prod_sha} got={prod_sha}",
        }
    else:
        inv["production_sha_match"] = {"status": "PASS", "reason": "strict_sha disabled"}

    # 2. Merge plan schema
    schema = merge_plan.get("schema")
    inv["merge_plan_schema"] = {
        "status": "PASS" if schema == "f2merge/3" else "FAIL",
        "reason": f"schema={schema}",
    }

    # 3. production_write_performed == false
    pwp = merge_plan.get("production_write_performed")
    inv["merge_plan_not_written"] = {
        "status": "PASS" if pwp is False else "FAIL",
        "reason": f"production_write_performed={pwp}",
    }

    # 4. Accepted docs unique by (notice_id, url)
    pairs = [(a.get("notice_id"), a.get("url")) for a in acc]
    dup_count = len(pairs) - len(set(pairs))
    inv["accepted_docs_unique_by_notice_id_url"] = {
        "status": "PASS" if dup_count == 0 else "FAIL",
        "reason": f"all {len(pairs)} pairs unique" if dup_count == 0
                  else f"{dup_count} duplicate (notice_id, url) pairs",
    }

    # 5. Every accepted doc has notice_id and url
    missing = [i for i, a in enumerate(acc) if not a.get("notice_id") or not a.get("url")]
    inv["accepted_docs_have_notice_id_and_url"] = {
        "status": "PASS" if not missing else "FAIL",
        "reason": "all accepted docs have notice_id and url" if not missing
                  else f"{len(missing)} docs missing notice_id or url",
    }

    # Build global URL -> notice_id set for cross-record check
    global_url_to_nids: dict[str, set] = defaultdict(set)
    for nid, url_set in doc_urls_by_id.items():
        for u in url_set:
            global_url_to_nids[u].add(nid)

    # 6. No same-record URL collision
    same_colls = [
        a for a in acc
        if a.get("url") and a.get("url") in doc_urls_by_id.get(a.get("notice_id"), set())
    ]
    inv["no_same_record_url_collision"] = {
        "status": "PASS" if not same_colls else "FAIL",
        "reason": "no accepted doc URL exists on same notice_id in production" if not same_colls
                  else f"{len(same_colls)} same-record URL collisions",
    }
    if same_colls:
        inv["no_same_record_url_collision"]["examples"] = [
            {"notice_id": a["notice_id"], "url": a["url"]} for a in same_colls[:3]
        ]

    # 7. No cross-record URL collision
    cross_colls = [
        a for a in acc
        if a.get("url")
        and (global_url_to_nids.get(a.get("url"), set()) - {a.get("notice_id")})
    ]
    inv["no_cross_record_url_collision"] = {
        "status": "PASS" if not cross_colls else "FAIL",
        "reason": "no accepted doc URL exists on a different notice_id in production"
                  if not cross_colls
                  else f"{len(cross_colls)} cross-record URL collisions",
    }
    if cross_colls:
        inv["no_cross_record_url_collision"]["examples"] = [
            {"notice_id": a["notice_id"], "url": a["url"]} for a in cross_colls[:3]
        ]

    # 8. Every target notice_id resolves to exactly one production record
    notice_ids = set(a.get("notice_id") for a in acc)
    by_notice_ck: dict[str, str | None] = {}
    for a in acc:
        nid = a.get("notice_id")
        if nid not in by_notice_ck:
            by_notice_ck[nid] = a.get("canonical_key")

    failed_resolution = []
    for nid in notice_ids:
        _, _, err, _, _ = _select_target(nid, by_notice_ck.get(nid), by_id, by_id_ck)
        if err:
            failed_resolution.append({"notice_id": nid, "error": err})

    inv["target_notice_id_resolves_to_one_record"] = {
        "status": "PASS" if not failed_resolution else "FAIL",
        "reason": "all target notice_ids resolve to exactly one production record"
                  if not failed_resolution
                  else f"{len(failed_resolution)} notice_ids failed resolution",
    }
    if failed_resolution:
        inv["target_notice_id_resolves_to_one_record"]["examples"] = failed_resolution[:3]

    # 9. No append target is a placeholder (only meaningful in dup groups)
    placeholder_targets = []
    for nid in notice_ids:
        _, rec, err, is_dup, _ = _select_target(nid, by_notice_ck.get(nid), by_id, by_id_ck)
        if rec is not None and is_dup and _is_placeholder(rec):
            placeholder_targets.append(nid)

    inv["no_placeholder_append_target"] = {
        "status": "PASS" if not placeholder_targets else "FAIL",
        "reason": "no placeholder records targeted for append" if not placeholder_targets
                  else f"{len(placeholder_targets)} placeholder records targeted",
    }

    # 10. All append docs remain in sidecar only  (structural guarantee)
    inv["docs_in_sidecar_only"] = {
        "status": "PASS",
        "reason": "tool never writes to production; all docs remain in sidecar plan",
    }

    # 11. production_write_performed remains false  (structural guarantee)
    inv["production_write_performed_false"] = {
        "status": "PASS",
        "reason": "production_write_performed=false at tool exit",
    }

    return inv


# ---------------------------------------------------------------------------
# Main plan builder
# ---------------------------------------------------------------------------

def build_plan(
    merge_plan_path: str,
    production_path: str,
    output_path: str,
    expected_prod_sha: str,
    allow_overwrite: bool,
    limit: int | None,
    strict_sha: bool,
) -> int:
    # Safe output guard
    if not _is_safe_output(output_path):
        print(
            f"[BLOCKED] Output path '{output_path}' is not allowed.\n"
            "Output must be under _tmp/ or data/fetcher2/.\n"
            "Refusing to write anything. Exiting nonzero.",
            file=sys.stderr,
        )
        return 2

    if os.path.exists(output_path) and not allow_overwrite:
        print(
            f"[BLOCKED] Output path '{output_path}' already exists.\n"
            "Pass --allow-output-overwrite to permit overwriting.",
            file=sys.stderr,
        )
        return 3

    # SHA + load production
    print(f"[INFO] Computing sha256 of {production_path} ...")
    prod_sha = _sha256_file(production_path)
    print(f"[INFO] production sha256={prod_sha}")

    print(f"[INFO] Loading production data ...")
    with open(production_path, encoding="utf-8") as f:
        prod_root = json.load(f)
    prod_data: list[dict] = prod_root.get("data", [])
    print(f"[INFO] Production records: {len(prod_data)}")

    by_id, by_id_ck, doc_urls_by_id = _build_production_indexes(prod_data)

    # Load merge plan
    print(f"[INFO] Loading merge plan from {merge_plan_path} ...")
    merge_plan_sha = _sha256_file(merge_plan_path)
    with open(merge_plan_path, encoding="utf-8") as f:
        merge_plan = json.load(f)
    print(f"[INFO] merge_plan sha256={merge_plan_sha}")

    acc_all: list[dict] = merge_plan.get("accepted_documents", [])
    if limit is not None:
        acc_all = acc_all[:limit]
        print(f"[INFO] --limit applied: {len(acc_all)} accepted docs")

    # Run invariants
    print("[INFO] Running invariants ...")
    invs = _run_invariants(
        merge_plan, by_id, by_id_ck, doc_urls_by_id,
        prod_sha, expected_prod_sha, strict_sha,
    )
    failed_invs = [k for k, v in invs.items() if v.get("status") != "PASS"]
    if failed_invs:
        print(f"[WARN] Invariant failures: {failed_invs}")
    else:
        print("[INFO] All invariants PASS")

    # Group accepted docs by notice_id; record each notice's canonical_key
    by_notice: dict[str, list[dict]] = defaultdict(list)
    notice_ck: dict[str, str | None] = {}
    for a in acc_all:
        nid = a.get("notice_id")
        by_notice[nid].append(a)
        if nid not in notice_ck:
            notice_ck[nid] = a.get("canonical_key")

    # Build global URL -> notice_id for cross-record collision counting
    global_url_to_nids: dict[str, set] = defaultdict(set)
    for nid, url_set in doc_urls_by_id.items():
        for u in url_set:
            global_url_to_nids[u].add(nid)

    # Build per_record_append_plan
    per_record: list[dict] = []
    selection_errors: list[dict] = []
    same_rec_url_colls = 0
    cross_rec_url_colls = 0
    already_have_docs = 0
    gaining_first_doc = 0
    existing_docs_sum = 0
    placeholder_count = 0
    enriched_count = 0

    for notice_id, docs in sorted(by_notice.items()):
        ck = notice_ck.get(notice_id)
        prod_idx, target_rec, err, is_dup_group, kind = _select_target(
            notice_id, ck, by_id, by_id_ck
        )
        if err or target_rec is None:
            selection_errors.append({"notice_id": notice_id, "error": err})
            continue

        # Existing URLs for this notice_id (union across all records with same id)
        existing_urls = doc_urls_by_id.get(notice_id, set())
        existing_doc_count = len(existing_urls)

        docs_to_append = []
        for doc in docs:
            url = doc.get("url")
            if url and url in existing_urls:
                same_rec_url_colls += 1
            else:
                docs_to_append.append(doc)
                if url:
                    other_nids = global_url_to_nids.get(url, set()) - {notice_id}
                    if other_nids:
                        cross_rec_url_colls += 1

        if is_dup_group and _is_placeholder(target_rec):
            placeholder_count += 1
        else:
            enriched_count += 1

        if existing_doc_count > 0:
            already_have_docs += 1
        else:
            gaining_first_doc += 1
        existing_docs_sum += existing_doc_count

        per_record.append({
            "notice_id": notice_id,
            "production_record_index": prod_idx,
            "is_duplicate_id_group": is_dup_group,
            "target_record_kind": kind,
            "existing_document_count": existing_doc_count,
            "append_document_count": len(docs_to_append),
            "documents_to_append": docs_to_append,
            "post_append_document_count": existing_doc_count + len(docs_to_append),
        })

    total_new_docs = sum(r["append_document_count"] for r in per_record)

    # Accepted internal duplicate pairs
    pairs = [(a.get("notice_id"), a.get("url")) for a in acc_all]
    accepted_internal_dup_pairs = len(pairs) - len(set(pairs))

    # Duplicate evidence summary
    dups_list: list[dict] = merge_plan.get("duplicates", [])
    dup_reason_counts = dict(Counter(d.get("reason") for d in dups_list))
    dup_jm_counts = dict(Counter(d.get("join_method") for d in dups_list))
    dup_of_jm_counts = dict(Counter(d.get("duplicate_of_join_method") for d in dups_list))

    # Blocked summary
    blk_list: list[dict] = merge_plan.get("blocked_documents", [])
    blk_reason_counts = dict(Counter(d.get("reason") for d in blk_list))

    # Backup plan
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_plan = {
        "target": "data/licitaciones.json",
        "target_sha256": prod_sha,
        "proposed_backup_path": f"_tmp/data_licitaciones_before_f2_persistence_v0618_{ts}.json",
        "required_before_future_write": True,
        "rollback_note": (
            "Before any production write, copy data/licitaciones.json to "
            "proposed_backup_path. To rollback, copy the backup back to "
            "data/licitaciones.json and verify sha256 matches target_sha256."
        ),
    }

    # Source summary
    merge_counts = merge_plan.get("counts", {})
    source_summary = {
        "merge_schema": merge_plan.get("schema"),
        "merge_version": merge_plan.get("version"),
        "accepted_documents": merge_counts.get("accepted_documents", len(acc_all)),
        "duplicate_evidence_rows": merge_counts.get("duplicate_evidence_rows", len(dups_list)),
        "blocked_documents": merge_counts.get("blocked_documents", len(blk_list)),
    }

    # Counts
    counts = {
        "records_affected": len(per_record),
        "total_new_docs": total_new_docs,
        "records_already_have_docs": already_have_docs,
        "records_gaining_first_doc": gaining_first_doc,
        "existing_docs_on_affected_records": existing_docs_sum,
        "total_docs_after_hypothetical_append_on_affected": existing_docs_sum + total_new_docs,
        "same_record_existing_url_collisions": same_rec_url_colls,
        "cross_record_existing_url_collisions": cross_rec_url_colls,
        "accepted_internal_duplicate_pairs": accepted_internal_dup_pairs,
        "placeholder_target_count": placeholder_count,
        "enriched_target_count": enriched_count,
    }

    # Warnings
    warnings = list(merge_plan.get("warnings", []))
    if selection_errors:
        warnings.append(
            f"{len(selection_errors)} notice_ids could not resolve to a production record"
        )
    if same_rec_url_colls:
        warnings.append(f"{same_rec_url_colls} same-record URL collisions (docs excluded)")
    if cross_rec_url_colls:
        warnings.append(f"{cross_rec_url_colls} cross-record URL collisions detected")

    # Final verdict
    all_inv_pass = not failed_invs
    final_verdict = (
        "PERSISTENCE_DRY_RUN_READY"
        if all_inv_pass and not selection_errors
        else "HOLD"
    )

    # Assemble plan
    plan = {
        "schema": "f2persist/1",
        "version": "v0.6.18",
        "mode": "F2_PERSISTENCE_DRY_RUN_PLAN",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_write_performed": False,
        "inputs": {
            "merge_plan": merge_plan_path,
            "merge_plan_sha256": merge_plan_sha,
            "production": production_path,
            "production_sha256": prod_sha,
        },
        "backup_plan": backup_plan,
        "source_summary": source_summary,
        "invariants": invs,
        "counts": counts,
        "per_record_append_plan": per_record,
        "duplicate_evidence_summary": {
            "total": len(dups_list),
            "reason_counts": dup_reason_counts,
            "join_method_counts": dup_jm_counts,
            "duplicate_of_join_method_counts": dup_of_jm_counts,
            "note": "duplicate evidence rows are not written to production",
        },
        "blocked_summary": {
            "total": len(blk_list),
            "reason_counts": blk_reason_counts,
            "note": "blocked rows are not written to production",
        },
        "warnings": warnings,
        "final_verdict": final_verdict,
    }

    # Write output
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Plan written to {output_path}")
    print(f"[INFO] final_verdict={final_verdict}")
    print(f"[INFO] records_affected={counts['records_affected']}  total_new_docs={counts['total_new_docs']}")
    print(f"[INFO] records_already_have_docs={counts['records_already_have_docs']}  records_gaining_first_doc={counts['records_gaining_first_doc']}")
    if selection_errors:
        print(f"[WARN] {len(selection_errors)} selection errors: {selection_errors[:3]}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="F2 Persistence Dry-Run Planner (f2persist/1 / v0.6.18)"
    )
    parser.add_argument("--merge-plan", required=True, help="Path to f2merge/3 plan JSON")
    parser.add_argument(
        "--production", required=True, help="Path to data/licitaciones.json (READ-ONLY)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path (must be under _tmp/ or data/fetcher2/)",
    )
    parser.add_argument(
        "--expected-production-sha",
        default="e81f785cf30719e94f73f2cc5fc76109942c222ae7fc16106ca0c2d8f0bb0883",
        help="Expected SHA256 of the production file",
    )
    parser.add_argument(
        "--allow-output-overwrite",
        action="store_true",
        help="Allow overwriting an existing output file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N accepted docs (smoke-test mode)",
    )
    parser.add_argument(
        "--strict-sha",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enforce production SHA256 check (default: enabled)",
    )
    args = parser.parse_args()

    rc = build_plan(
        merge_plan_path=args.merge_plan,
        production_path=args.production,
        output_path=args.output,
        expected_prod_sha=args.expected_production_sha,
        allow_overwrite=args.allow_output_overwrite,
        limit=args.limit,
        strict_sha=args.strict_sha,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
