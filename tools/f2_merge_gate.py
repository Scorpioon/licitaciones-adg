#!/usr/bin/env python3
"""
tools/f2_merge_gate.py  —  F2 merge gate v2 (DRY-RUN ONLY)

Resolved-aware dry-run merge gate. Reads:
  * an F2-B resolver manifest (schema f2b/1, consolidated) via --resolved-input
  * the originating F2-A manifest (schema f2a/1) via --input
  * the production dataset data/licitaciones.json via --production (READ-ONLY)

It produces a safe f2merge/2 dry-run plan describing which resolved F2-B
documents WOULD be accepted as merge-ready document-layer candidates, which are
blocked (and why), which are duplicates against existing production documents,
and which cannot be joined back to a production record.

This tool NEVER writes production data. It NEVER modifies, backs up, or stages
data/licitaciones.json. It only emits a sidecar plan so an operator can review
what a real merge would do. production_write_performed is ALWAYS false.

Join path (robust, id-first):
  F2-B candidate_id -> F2-A candidate -> F2-A record id -> production record id.
When a production id is shared by multiple production records (placeholder vs
enriched copies), the F2-A record canonical_key is used only as a same-id
tie-breaker. canonical_key-only joins are never used.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

VERSION = "v0.6.0m"
SCHEMA = "f2merge/2"

_SAFE_PREFIXES = [
    os.path.normpath("_tmp"),
    os.path.normpath(os.path.join("data", "fetcher2")),
]
_FORBIDDEN = {
    os.path.normpath(os.path.join("data", "licitaciones.json")),
    os.path.normpath("fetch_licitaciones.py"),
    os.path.normpath(os.path.join("tools", "scheduled_fetch_merge.py")),
}

# Status thresholds for F2B_RESOLUTION_OK.
F2B_MAX_RESOLVER_ERROR_RATE = 0.05
F2B_MIN_RESOLVED_DOCUMENT_RATIO = 0.95


def _check_output_safe(path, allow_outside):
    norm = os.path.normpath(path)
    if norm in _FORBIDDEN:
        return False, f"Output path resolves to forbidden file: {norm}"
    if not allow_outside and not any(norm.startswith(p) for p in _SAFE_PREFIXES):
        return False, "Output path outside safe area; use --allow-output-outside-safe-area to override"
    return True, None


def _load_json(path, label):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[F2-MERGE BLOCKED] Cannot read {label} '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _content_type_base(raw):
    if not raw:
        return ""
    return str(raw).strip().lower().split(";", 1)[0].strip()


def build_f2a_bridge(f2a):
    """candidate_id -> {record_id, canonical_key} bridge from the F2-A manifest.

    candidate_id is unique across F2-A and nests under exactly one record, so the
    bridge is unambiguous. Also builds canonical_key -> set(record_id) for
    ambiguity reporting only (never used as a primary join key).
    """
    bridge = {}
    ck_to_record_ids = defaultdict(set)
    records = f2a.get("records", [])
    for rec in records:
        rid = rec.get("id")
        rck = rec.get("canonical_key")
        if rck:
            ck_to_record_ids[rck].add(rid)
        for c in rec.get("candidates", []):
            cid = c.get("candidate_id")
            if not cid:
                continue
            bridge[cid] = {
                "record_id": rid,
                "canonical_key": rck,
                "record_title": rec.get("title"),
            }
    ambiguous_canonical_keys = sum(1 for ids in ck_to_record_ids.values() if len(ids) > 1)
    return bridge, ambiguous_canonical_keys, len(records)


def build_production_index(prod):
    """Build read-only production indexes. Never mutates production data.

    Returns by_id (id -> [records]), by_id_ck ((id, canonical_key) -> [records]),
    doc_urls_by_id (id -> set(documents[].url)) and a shape summary.
    """
    if isinstance(prod, dict):
        data = prod.get("data")
        top_keys = list(prod.keys())
    elif isinstance(prod, list):
        data = prod
        top_keys = ["<list>"]
    else:
        data = None
        top_keys = []
    if not isinstance(data, list):
        return None, None, None, None, None

    by_id = defaultdict(list)
    by_id_ck = defaultdict(list)
    doc_urls_by_id = defaultdict(set)
    records_with_id = 0
    records_with_ck = 0
    records_with_docs = 0
    existing_doc_url_count = 0

    for rec in data:
        rid = rec.get("id")
        rck = rec.get("canonical_key")
        if rid:
            records_with_id += 1
        if rck:
            records_with_ck += 1
        by_id[rid].append(rec)
        by_id_ck[(rid, rck)].append(rec)
        docs = rec.get("documents")
        if isinstance(docs, list) and docs:
            records_with_docs += 1
            for d in docs:
                if isinstance(d, dict) and d.get("url"):
                    doc_urls_by_id[rid].add(d.get("url"))
                    existing_doc_url_count += 1

    shape_summary = {
        "top_level_keys": top_keys,
        "total_records": len(data),
        "records_with_id": records_with_id,
        "records_with_canonical_key": records_with_ck,
        "records_with_documents": records_with_docs,
        "existing_document_url_count": existing_doc_url_count,
    }
    return by_id, by_id_ck, doc_urls_by_id, shape_summary, len(data)


def resolve_production_record(record_id, record_ck, by_id, by_id_ck):
    """Resolve an F2-A record id to exactly one production record.

    id-first; canonical_key is only a same-id tie-breaker. Returns
    (record, reason): record is None when reason is set.
    """
    recs = by_id.get(record_id) or []
    if not recs:
        return None, "production_record_not_found"
    if len(recs) == 1:
        return recs[0], None
    # Shared production id (placeholder vs enriched copies): disambiguate by the
    # F2-A record canonical_key, scoped to the same id.
    if record_ck:
        m = by_id_ck.get((record_id, record_ck)) or []
        if len(m) == 1:
            return m[0], None
    return None, "ambiguous_record_join"


def best_title(c):
    return (
        c.get("original_title")
        or c.get("normalized_title")
        or c.get("inferred_filename")
        or c.get("final_url")
        or ""
    )


def build_document_object(c, production_record_id):
    """Production-compatible document object a real merge WOULD append (not applied)."""
    return {
        "notice_id": production_record_id,
        "notice_type": "",
        "document_type": c.get("original_kind") or c.get("inferred_extension") or "",
        "source_section": "f2_document_evidence",
        "title": best_title(c),
        "url": c.get("final_url"),
        "original_url": c.get("normalized_url") or c.get("original_url"),
        "mime_hint": c.get("content_type"),
        "format_hint": c.get("inferred_extension"),
        "published_at": "",
        "provenance": "f2b_resolver",
        "candidate_id": c.get("candidate_id"),
        "canonical_key": c.get("canonical_key"),
        "resolver_method": c.get("resolver_method"),
        "http_status": c.get("http_status"),
        "content_length": c.get("content_length"),
        "no_binary_download": True,
    }


def _blocked_entry(c, reason, record_id=None):
    return {
        "reason": reason,
        "candidate_id": c.get("candidate_id"),
        "canonical_key": c.get("canonical_key"),
        "record_id": record_id,
        "final_url": c.get("final_url"),
        "source_domain": c.get("source_domain"),
        "content_type": c.get("content_type"),
        "resolved_is_document": c.get("resolved_is_document"),
        "merge_ready_candidate": c.get("merge_ready_candidate"),
        "merge_blockers": c.get("merge_blockers"),
    }


def _duplicate_entry(c, reason, record_id=None, existing_match=None):
    e = {
        "reason": reason,
        "candidate_id": c.get("candidate_id"),
        "record_id": record_id,
        "canonical_key": c.get("canonical_key"),
        "final_url": c.get("final_url"),
    }
    if existing_match is not None:
        e["existing_document_match"] = existing_match
    return e


def parse_args():
    ap = argparse.ArgumentParser(
        description="F2 merge gate v2 (DRY-RUN ONLY) — resolved-aware plan; never writes production (ADG OPS v0.6.0m)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--resolved-input", required=True,
                    help="F2-B consolidated resolver manifest (schema f2b/1) — required.")
    ap.add_argument("--input", required=True,
                    help="F2-A manifest (schema f2a/1) — required in v2 for the candidate->record bridge.")
    ap.add_argument("--production", required=True,
                    help="Production dataset (data/licitaciones.json) — required in v2, READ-ONLY.")
    ap.add_argument("--output", required=True,
                    help="Dry-run plan output path (_tmp/ or data/fetcher2/).")
    ap.add_argument("--domain", default=None,
                    help="Restrict to candidates whose source/final domain contains DOMAIN.")
    ap.add_argument("--limit", type=int, default=100, help="Max resolved candidates to consider.")
    ap.add_argument("--allow-output-outside-safe-area", action="store_true",
                    help="Bypass safe-area restriction on output path.")
    return ap.parse_args()


def main():
    args = parse_args()

    ok, msg = _check_output_safe(args.output, args.allow_output_outside_safe_area)
    if not ok:
        print(f"[F2-MERGE BLOCKED] {msg}", file=sys.stderr)
        return 1

    # ---- Load F2-B resolved input -------------------------------------------------
    f2b = _load_json(args.resolved_input, "F2-B manifest")
    if not str(f2b.get("schema", "")).startswith("f2b/"):
        print(f"[F2-MERGE BLOCKED] Unexpected resolved schema '{f2b.get('schema')}'. Expected f2b/1.", file=sys.stderr)
        return 1
    resolved = f2b.get("resolved_candidates", [])
    if not isinstance(resolved, list):
        print("[F2-MERGE BLOCKED] F2-B manifest missing 'resolved_candidates' list.", file=sys.stderr)
        return 1

    # ---- Load F2-A manifest + build bridge ----------------------------------------
    f2a = _load_json(args.input, "F2-A manifest")
    if not str(f2a.get("schema", "")).startswith("f2a/"):
        print(f"[F2-MERGE BLOCKED] Unexpected F2-A schema '{f2a.get('schema')}'. Expected f2a/1.", file=sys.stderr)
        return 1
    if not isinstance(f2a.get("records"), list):
        print("[F2-MERGE BLOCKED] F2-A manifest missing 'records' list.", file=sys.stderr)
        return 1
    bridge, ambiguous_canonical_keys, f2a_records_total = build_f2a_bridge(f2a)

    # ---- Load production (READ-ONLY) + build indexes ------------------------------
    prod = _load_json(args.production, "production dataset")
    by_id, by_id_ck, doc_urls_by_id, production_shape_summary, prod_records_total = build_production_index(prod)
    if by_id is None:
        print("[F2-MERGE BLOCKED] Production dataset has no 'data' list (unexpected shape).", file=sys.stderr)
        return 1

    warnings = []

    # ---- Domain filter + limit ----------------------------------------------------
    def _domain_match(r):
        if not args.domain:
            return True
        d = args.domain.lower()
        return d in (r.get("source_domain") or "").lower() or d in (r.get("final_domain") or "").lower()

    considered = [r for r in resolved if _domain_match(r)][: args.limit]

    # ---- Per-row classification ---------------------------------------------------
    accepted_documents = []
    blocked_documents = []
    duplicates = []
    reason_counter = Counter()

    seen_candidate_ids = set()
    accepted_url_by_record = defaultdict(set)  # record_id -> set(final_url) accepted in this batch

    candidate_id_matched_to_f2a = 0
    candidate_id_missing_in_f2a = 0
    production_records_matched = 0
    production_records_missing = 0
    merge_ready_seen = 0

    for c in considered:
        if c.get("merge_ready_candidate"):
            merge_ready_seen += 1

        cid = c.get("candidate_id")
        if not cid:
            reason_counter["missing_candidate_id"] += 1
            blocked_documents.append(_blocked_entry(c, "missing_candidate_id"))
            continue
        if cid in seen_candidate_ids:
            reason_counter["duplicate_candidate_id"] += 1
            duplicates.append(_duplicate_entry(c, "duplicate_candidate_id"))
            continue
        seen_candidate_ids.add(cid)

        if not c.get("canonical_key"):
            reason_counter["missing_canonical_key"] += 1
            blocked_documents.append(_blocked_entry(c, "missing_canonical_key"))
            continue
        if not c.get("final_url"):
            reason_counter["missing_final_url"] += 1
            blocked_documents.append(_blocked_entry(c, "missing_final_url"))
            continue
        if _content_type_base(c.get("content_type")).startswith("text/html"):
            reason_counter["html_page"] += 1
            blocked_documents.append(_blocked_entry(c, "html_page"))
            continue
        if not c.get("resolved_is_document"):
            reason_counter["not_document"] += 1
            blocked_documents.append(_blocked_entry(c, "not_document"))
            continue
        if not c.get("merge_ready_candidate"):
            reason_counter["not_merge_ready"] += 1
            blocked_documents.append(_blocked_entry(c, "not_merge_ready"))
            continue
        if c.get("merge_blockers"):
            reason_counter["merge_blockers_present"] += 1
            blocked_documents.append(_blocked_entry(c, "merge_blockers_present"))
            continue

        # F2-A bridge
        b = bridge.get(cid)
        if b is None:
            candidate_id_missing_in_f2a += 1
            reason_counter["f2a_candidate_not_found"] += 1
            blocked_documents.append(_blocked_entry(c, "f2a_candidate_not_found"))
            continue
        candidate_id_matched_to_f2a += 1
        record_id = b.get("record_id")
        if not record_id:
            reason_counter["f2a_record_id_missing"] += 1
            blocked_documents.append(_blocked_entry(c, "f2a_record_id_missing"))
            continue

        # Production join (id-first, canonical_key tie-break)
        prod_rec, join_reason = resolve_production_record(
            record_id, b.get("canonical_key"), by_id, by_id_ck
        )
        if join_reason == "production_record_not_found":
            production_records_missing += 1
            reason_counter["production_record_not_found"] += 1
            blocked_documents.append(_blocked_entry(c, "production_record_not_found", record_id))
            continue
        if join_reason == "ambiguous_record_join":
            reason_counter["ambiguous_record_join"] += 1
            blocked_documents.append(_blocked_entry(c, "ambiguous_record_join", record_id))
            continue
        production_records_matched += 1

        final_url = c.get("final_url")

        # Duplicate against existing production documents on the matched record.
        if final_url in doc_urls_by_id.get(record_id, set()):
            reason_counter["existing_document_url"] += 1
            duplicates.append(_duplicate_entry(
                c, "existing_document_url", record_id,
                existing_match={"record_id": record_id, "url": final_url},
            ))
            continue

        # Duplicate final_url for the same record within this batch.
        if final_url in accepted_url_by_record[record_id]:
            reason_counter["duplicate_final_url_for_record"] += 1
            duplicates.append(_duplicate_entry(c, "duplicate_final_url_for_record", record_id))
            continue

        # Accept.
        accepted_url_by_record[record_id].add(final_url)
        accepted_documents.append(build_document_object(c, record_id))

    if any(d.get("content_length") is None for d in accepted_documents):
        warnings.append(
            "Some accepted documents have no content_length (streamed gateway PDFs); acceptable but noted."
        )

    # ---- Layered statuses ---------------------------------------------------------
    qs = f2b.get("quality_summary", {})
    resolver_error_rate = qs.get("resolver_error_rate", 0.0) or 0.0
    resolved_document_ratio = qs.get("resolved_document_ratio", 0.0) or 0.0
    merge_ready_candidate_count = qs.get("merge_ready_candidate_count", 0) or 0

    # F2A_ARTIFACT_OK — structural artifact validity (NOT pre-resolution MERGE_OK).
    f2a_qs = f2a.get("quality_summary", {})
    f2a_error_rate = f2a_qs.get("error_rate")
    f2a_candidate_total = sum(len(r.get("candidates", [])) for r in f2a.get("records", []))
    f2a_reasons = []
    f2a_status = "PASS"
    if f2a_records_total <= 0:
        f2a_status = "FAIL"
        f2a_reasons.append("f2a_records_total is zero")
    if f2a_candidate_total <= 0:
        f2a_status = "FAIL"
        f2a_reasons.append("f2a candidate total is zero")
    if isinstance(f2a_error_rate, (int, float)) and f2a_error_rate > 0.05:
        f2a_status = "FAIL"
        f2a_reasons.append(f"f2a error_rate {f2a_error_rate} > 0.05")
    if f2a_status == "PASS":
        f2a_reasons.append(
            f"f2a artifact valid: records={f2a_records_total} candidates={f2a_candidate_total}"
        )

    # F2B_RESOLUTION_OK
    f2b_reasons = []
    f2b_status = "PASS"
    if resolver_error_rate > F2B_MAX_RESOLVER_ERROR_RATE:
        f2b_status = "FAIL"
        f2b_reasons.append(
            f"resolver_error_rate {resolver_error_rate} > {F2B_MAX_RESOLVER_ERROR_RATE}"
        )
    if resolved_document_ratio < F2B_MIN_RESOLVED_DOCUMENT_RATIO:
        f2b_status = "FAIL"
        f2b_reasons.append(
            f"resolved_document_ratio {resolved_document_ratio} < {F2B_MIN_RESOLVED_DOCUMENT_RATIO}"
        )
    if merge_ready_candidate_count <= 0:
        f2b_status = "FAIL"
        f2b_reasons.append("merge_ready_candidate_count is zero")
    if f2b_status == "PASS":
        f2b_reasons.append(
            f"resolver_error_rate={resolver_error_rate} resolved_document_ratio={resolved_document_ratio} "
            f"merge_ready_candidate_count={merge_ready_candidate_count}"
        )

    # DOCUMENT_MERGE_READY — honest; do not force PASS on poor join coverage.
    accepted_rows = len(accepted_documents)
    join_incomplete = (
        reason_counter.get("ambiguous_record_join", 0)
        + reason_counter.get("production_record_not_found", 0)
        + reason_counter.get("f2a_candidate_not_found", 0)
        + reason_counter.get("f2a_record_id_missing", 0)
    )
    dmr_reasons = []
    if accepted_rows == 0:
        dmr_status = "FAIL"
        dmr_reasons.append("no documents accepted as merge-ready")
    elif f2b_status != "PASS":
        dmr_status = "FAIL"
        dmr_reasons.append("F2B_RESOLUTION_OK is not PASS")
    elif join_incomplete > 0:
        dmr_status = "WARN"
        dmr_reasons.append(
            f"join coverage incomplete: {join_incomplete} rows could not be joined to a unique "
            f"production record (ambiguous_record_join="
            f"{reason_counter.get('ambiguous_record_join', 0)}, "
            f"production_record_not_found={reason_counter.get('production_record_not_found', 0)}, "
            f"f2a_candidate_not_found={reason_counter.get('f2a_candidate_not_found', 0)})"
        )
        dmr_reasons.append(f"{accepted_rows} documents are cleanly merge-ready for a future dry-run persistence plan")
    else:
        dmr_status = "PASS"
        dmr_reasons.append(f"{accepted_rows} documents cleanly merge-ready; no join invariant failures")

    layered_statuses = {
        "F2A_ARTIFACT_OK": {"status": f2a_status, "reasons": f2a_reasons},
        "F2B_RESOLUTION_OK": {"status": f2b_status, "reasons": f2b_reasons},
        "DOCUMENT_MERGE_READY": {"status": dmr_status, "reasons": dmr_reasons},
        "PRODUCTION_WRITE_OK": {"status": "FAIL", "reasons": ["production_write_disabled_in_v0.6.0m"]},
    }

    # ---- Summaries ----------------------------------------------------------------
    html_non_doc_blocked = reason_counter.get("html_page", 0) + reason_counter.get("not_document", 0)
    unmatched_rows = (
        reason_counter.get("production_record_not_found", 0)
        + reason_counter.get("ambiguous_record_join", 0)
        + reason_counter.get("f2a_candidate_not_found", 0)
        + reason_counter.get("f2a_record_id_missing", 0)
    )

    join_summary = {
        "resolved_rows_seen": len(considered),
        "candidate_id_matched_to_f2a": candidate_id_matched_to_f2a,
        "candidate_id_missing_in_f2a": candidate_id_missing_in_f2a,
        "production_records_matched": production_records_matched,
        "production_records_missing": production_records_missing,
        "ambiguous_canonical_keys": ambiguous_canonical_keys,
        "unmatched_rows": unmatched_rows,
        "blocked_rows": len(blocked_documents),
        "duplicate_rows": len(duplicates),
        "accepted_rows": accepted_rows,
    }

    counts = {
        "resolved_seen": len(considered),
        "accepted_documents": len(accepted_documents),
        "blocked_documents": len(blocked_documents),
        "duplicates": len(duplicates),
        "html_non_doc_blocked": html_non_doc_blocked,
        "merge_ready_seen": merge_ready_seen,
    }

    # ---- Backup plan (planned only; nothing is written here) ----------------------
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    try:
        target_sha256 = _sha256_file(args.production)
    except OSError as e:
        target_sha256 = None
        warnings.append(f"Could not compute production sha256: {e}")

    backup_plan = {
        "target": os.path.join("data", "licitaciones.json").replace(os.sep, "/"),
        "target_sha256": target_sha256,
        "proposed_backup_path": f"_tmp/data_licitaciones_before_f2_document_merge_v060m_{ts}.json",
        "required_before_future_write": True,
    }

    production_shape_str = (
        f"dict{{{','.join(production_shape_summary['top_level_keys'])}}} "
        f"data[{production_shape_summary['total_records']}]"
    )

    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "F2_MERGE_GATE_V2_DRY_RUN",
        "production_write_performed": False,
        "inputs": {
            "resolved_input": args.resolved_input,
            "f2a_input": args.input,
            "production": args.production,
        },
        "traceability": {
            "merge_gate_version": VERSION,
            "resolved_schema": f2b.get("schema"),
            "resolved_version": f2b.get("version"),
            "f2a_schema": f2a.get("schema"),
            "f2a_version": f2a.get("version"),
            "production_shape": production_shape_str,
            "domain_filter": args.domain,
            "limit": args.limit,
        },
        "layered_statuses": layered_statuses,
        "join_summary": join_summary,
        "counts": counts,
        "production_shape_summary": production_shape_summary,
        "accepted_documents": accepted_documents,
        "blocked_documents": blocked_documents,
        "duplicates": duplicates,
        "block_reason_counts": dict(reason_counter),
        "backup_plan": backup_plan,
        "warnings": warnings,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(
        f"[F2-MERGE v2] DRY-RUN | seen={counts['resolved_seen']} "
        f"accepted={counts['accepted_documents']} blocked={counts['blocked_documents']} "
        f"dupes={counts['duplicates']}"
    )
    print(
        f"[F2-MERGE v2] F2A_ARTIFACT_OK={f2a_status} F2B_RESOLUTION_OK={f2b_status} "
        f"DOCUMENT_MERGE_READY={dmr_status} PRODUCTION_WRITE_OK=FAIL "
        f"(production_write_performed=False)"
    )
    if reason_counter:
        print(f"[F2-MERGE v2] block/dup reasons: {dict(reason_counter)}")
    print(f"[F2-MERGE v2] plan -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
