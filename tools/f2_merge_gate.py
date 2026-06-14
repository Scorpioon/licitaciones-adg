#!/usr/bin/env python3
"""
tools/f2_merge_gate.py  —  F2 merge gate v3 (DRY-RUN ONLY)

Resolved-aware dry-run merge gate. Reads:
  * an F2-B resolver manifest (schema f2b/1, consolidated) via --resolved-input
  * the originating F2-A manifest (schema f2a/1) via --input
  * the production dataset data/licitaciones.json via --production (READ-ONLY)

It produces a safe f2merge/3 dry-run plan describing which resolved F2-B
documents WOULD be accepted as merge-ready document-layer candidates, which are
blocked (and why), which are duplicates against existing production documents,
and which cannot be joined back to a production record.

This tool NEVER writes production data. It NEVER modifies, backs up, or stages
data/licitaciones.json. It only emits a sidecar plan so an operator can review
what a real merge would do. production_write_performed is ALWAYS false.

Join path (robust, id-first, with enriched-copy fallback):
  F2-B candidate_id -> F2-A candidate -> F2-A record id -> production record id.

Join resolution order:
  1. strict_id: production id maps to exactly one record.
  2. strict_id_canonical_key: shared id group; F2-A canonical_key disambiguates.
  3. enriched_copy_fallback: shared id group, CK tie-break fails, but invariant
     holds (exactly one enriched copy, all others placeholder, no collisions).
  If none resolve, block as ambiguous_record_join.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

VERSION = "v0.6.0o"
SCHEMA = "f2merge/3"

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


# ---------------------------------------------------------------------------
# Enriched / placeholder classification helpers
# ---------------------------------------------------------------------------

def _is_enriched(rec):
    """A production record is enriched if it has a canonical_key or non-empty documents list."""
    ck = rec.get("canonical_key")
    docs = rec.get("documents")
    return bool(ck) or (isinstance(docs, list) and len(docs) > 0)


def _is_placeholder(rec):
    """A production record is placeholder if it has neither canonical_key nor documents."""
    return not _is_enriched(rec)


def _check_enriched_copy_invariant(recs):
    """Evaluate the enriched-copy invariant on a production id group.

    Invariant (all must hold):
      a. group size >= 2
      b. exactly one record is enriched
      c. all other records are placeholders
      d. no non-empty canonical_key collision in the group

    Returns (selected_record | None, invariant_failed_reason | None).
    If selected_record is not None the invariant passed and that record should be used.
    If invariant_failed_reason is set the invariant failed; keep blocking.
    """
    if len(recs) < 2:
        return None, f"group_size_{len(recs)}_less_than_2"

    enriched = [r for r in recs if _is_enriched(r)]
    placeholders = [r for r in recs if _is_placeholder(r)]

    if len(enriched) == 0:
        return None, "no_enriched_record_in_group"
    if len(enriched) > 1:
        return None, f"multiple_enriched_records_{len(enriched)}"
    if len(placeholders) != len(recs) - 1:
        return None, "mixed_classification_in_group"

    # Non-empty canonical_key collision check within the group.
    non_empty_cks = [r.get("canonical_key") for r in recs if r.get("canonical_key")]
    if len(non_empty_cks) != len(set(non_empty_cks)):
        return None, "non_empty_canonical_key_collision_in_group"

    return enriched[0], None


# ---------------------------------------------------------------------------
# F2-A bridge + production index
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Production record resolver (v3: id-first + CK tie-break + enriched fallback)
# ---------------------------------------------------------------------------

def resolve_production_record(record_id, record_ck, by_id, by_id_ck):
    """Resolve an F2-A record id to exactly one production record.

    Returns (record, join_method, block_reason, join_debug).
      record      — matched production record or None
      join_method — "strict_id" | "strict_id_canonical_key" |
                    "enriched_copy_fallback" | None
      block_reason — reason string when record is None
      join_debug   — dict with debug info when blocked, else None
    """
    recs = by_id.get(record_id) or []
    if not recs:
        return None, None, "production_record_not_found", None
    if len(recs) == 1:
        return recs[0], "strict_id", None, None

    # Shared production id: try canonical_key tie-break (same-id scope only).
    if record_ck:
        m = by_id_ck.get((record_id, record_ck)) or []
        if len(m) == 1:
            return m[0], "strict_id_canonical_key", None, None

    # Enriched-copy fallback (v3).
    enriched_rec, invariant_reason = _check_enriched_copy_invariant(recs)
    if enriched_rec is not None:
        return enriched_rec, "enriched_copy_fallback", None, None

    enriched = [r for r in recs if _is_enriched(r)]
    placeholders = [r for r in recs if _is_placeholder(r)]
    join_debug = {
        "production_id_group_size": len(recs),
        "enriched_candidates_count": len(enriched),
        "placeholder_candidates_count": len(placeholders),
        "invariant_failed_reason": invariant_reason,
    }
    return None, None, "ambiguous_record_join", join_debug


# ---------------------------------------------------------------------------
# Document / blocked / duplicate builders
# ---------------------------------------------------------------------------

def best_title(c):
    return (
        c.get("original_title")
        or c.get("normalized_title")
        or c.get("inferred_filename")
        or c.get("final_url")
        or ""
    )


def build_document_object(c, production_record_id, join_method=None):
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
        "join_method": join_method,
        "production_record_selector": join_method,
    }


def _blocked_entry(c, reason, record_id=None, join_debug=None):
    e = {
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
    if join_debug is not None:
        e["join_debug"] = join_debug
    return e


def _duplicate_entry(c, reason, record_id=None, existing_match=None,
                     join_method=None, duplicate_of_join_method=None):
    e = {
        "reason": reason,
        "candidate_id": c.get("candidate_id"),
        "record_id": record_id,
        "canonical_key": c.get("canonical_key"),
        "final_url": c.get("final_url"),
    }
    if join_method is not None:
        e["join_method"] = join_method
    if duplicate_of_join_method is not None:
        e["duplicate_of_join_method"] = duplicate_of_join_method
    if existing_match is not None:
        e["existing_document_match"] = existing_match
    return e


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(
        description="F2 merge gate v3 (DRY-RUN ONLY) — enriched-copy-aware plan; never writes production (ADG OPS v0.6.0o)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--resolved-input", required=True,
                    help="F2-B consolidated resolver manifest (schema f2b/1) — required.")
    ap.add_argument("--input", required=True,
                    help="F2-A manifest (schema f2a/1) — required for the candidate->record bridge.")
    ap.add_argument("--production", required=True,
                    help="Production dataset (data/licitaciones.json) — required, READ-ONLY.")
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
    # Global within-batch URL dedup keyed by (production record_id, final_url).
    # Tracks which join_method first accepted the URL so duplicate entries can
    # report duplicate_of_join_method for operator inspection.
    accepted_url_by_record = defaultdict(dict)  # record_id -> {final_url: join_method}

    candidate_id_matched_to_f2a = 0
    candidate_id_missing_in_f2a = 0
    production_records_matched = 0
    production_records_missing = 0
    merge_ready_seen = 0

    # v3 join-method counters
    resolved_via_strict_id = 0
    resolved_via_strict_id_canonical_key = 0
    resolved_via_enriched_fallback = 0
    enriched_fallback_invariant_failed = 0
    invariant_failed_reasons_counter = Counter()

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

        # Production join (v3: id-first -> CK tie-break -> enriched-copy fallback)
        prod_rec, join_method, join_reason, join_debug = resolve_production_record(
            record_id, b.get("canonical_key"), by_id, by_id_ck
        )
        if join_reason == "production_record_not_found":
            production_records_missing += 1
            reason_counter["production_record_not_found"] += 1
            blocked_documents.append(_blocked_entry(c, "production_record_not_found", record_id))
            continue
        if join_reason == "ambiguous_record_join":
            enriched_fallback_invariant_failed += 1
            reason_counter["ambiguous_record_join"] += 1
            if join_debug and join_debug.get("invariant_failed_reason"):
                invariant_failed_reasons_counter[join_debug["invariant_failed_reason"]] += 1
            blocked_documents.append(_blocked_entry(c, "ambiguous_record_join", record_id, join_debug))
            continue
        production_records_matched += 1

        if join_method == "strict_id":
            resolved_via_strict_id += 1
        elif join_method == "strict_id_canonical_key":
            resolved_via_strict_id_canonical_key += 1
        elif join_method == "enriched_copy_fallback":
            resolved_via_enriched_fallback += 1

        final_url = c.get("final_url")

        # Duplicate against existing production documents on the matched record.
        if final_url in doc_urls_by_id.get(record_id, set()):
            reason_counter["existing_document_url"] += 1
            duplicates.append(_duplicate_entry(
                c, "existing_document_url", record_id,
                existing_match={"record_id": record_id, "url": final_url},
            ))
            continue

        # Global within-batch URL dedup by (production record_id, final_url).
        # If an enriched_copy_fallback candidate reaches a URL already accepted
        # via strict_id or strict_id_canonical_key, it is duplicate evidence —
        # the same document is being targeted from the placeholder F2-A path.
        # Classified separately so operators can inspect without hiding the overlap.
        if final_url in accepted_url_by_record[record_id]:
            original_jm = accepted_url_by_record[record_id][final_url]
            if join_method == "enriched_copy_fallback":
                reason_counter["duplicate_evidence_final_url_for_record"] += 1
                duplicates.append(_duplicate_entry(
                    c, "duplicate_evidence_final_url_for_record", record_id,
                    join_method=join_method,
                    duplicate_of_join_method=original_jm,
                ))
            else:
                reason_counter["duplicate_final_url_for_record"] += 1
                duplicates.append(_duplicate_entry(c, "duplicate_final_url_for_record", record_id))
            continue
        accepted_url_by_record[record_id][final_url] = join_method

        # Accept.
        accepted_documents.append(build_document_object(c, record_id, join_method))

    if any(d.get("content_length") is None for d in accepted_documents):
        warnings.append(
            "Some accepted documents have no content_length (streamed gateway PDFs); acceptable but noted."
        )

    # ---- Layered statuses ---------------------------------------------------------
    qs = f2b.get("quality_summary", {})
    resolver_error_rate = qs.get("resolver_error_rate", 0.0) or 0.0
    resolved_document_ratio = qs.get("resolved_document_ratio", 0.0) or 0.0
    merge_ready_candidate_count = qs.get("merge_ready_candidate_count", 0) or 0

    # F2A_ARTIFACT_OK
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

    # DOCUMENT_MERGE_READY — v3: PASS when all joins resolved, no residual ambiguity,
    # and duplicate evidence is explicitly classified (not hidden).
    unique_append_docs = len(accepted_documents)
    duplicate_evidence_rows = reason_counter.get("duplicate_evidence_final_url_for_record", 0)
    ambiguous_remaining = reason_counter.get("ambiguous_record_join", 0)
    join_incomplete = (
        ambiguous_remaining
        + reason_counter.get("production_record_not_found", 0)
        + reason_counter.get("f2a_candidate_not_found", 0)
        + reason_counter.get("f2a_record_id_missing", 0)
    )
    accepted_rows = unique_append_docs
    dmr_reasons = []
    if unique_append_docs == 0:
        dmr_status = "FAIL"
        dmr_reasons.append("no documents accepted as merge-ready")
    elif f2b_status != "PASS":
        dmr_status = "FAIL"
        dmr_reasons.append("F2B_RESOLUTION_OK is not PASS")
    elif join_incomplete > 0:
        dmr_status = "WARN"
        dmr_reasons.append(
            f"join coverage incomplete: {join_incomplete} rows could not be joined to a unique "
            f"production record (ambiguous_record_join_remaining={ambiguous_remaining}, "
            f"production_record_not_found={reason_counter.get('production_record_not_found', 0)}, "
            f"f2a_candidate_not_found={reason_counter.get('f2a_candidate_not_found', 0)})"
        )
        dmr_reasons.append(f"{unique_append_docs} documents are cleanly merge-ready for a future dry-run persistence plan")
    else:
        dmr_status = "PASS"
        dmr_reasons.append(
            f"{unique_append_docs} unique appendable documents; {duplicate_evidence_rows} duplicate evidence rows "
            f"classified (not hidden); no join invariant failures"
        )

    layered_statuses = {
        "F2A_ARTIFACT_OK": {"status": f2a_status, "reasons": f2a_reasons},
        "F2B_RESOLUTION_OK": {"status": f2b_status, "reasons": f2b_reasons},
        "DOCUMENT_MERGE_READY": {"status": dmr_status, "reasons": dmr_reasons},
        "PRODUCTION_WRITE_OK": {"status": "FAIL", "reasons": ["production_write_disabled_in_v0.6.0o"]},
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
        # v3 additions
        "resolved_via_strict_id": resolved_via_strict_id,
        "resolved_via_strict_id_canonical_key": resolved_via_strict_id_canonical_key,
        "resolved_via_enriched_fallback": resolved_via_enriched_fallback,
        "enriched_fallback_invariant_failed": enriched_fallback_invariant_failed,
        "ambiguous_record_join_remaining": ambiguous_remaining,
        "duplicate_evidence_rows": duplicate_evidence_rows,
    }

    counts = {
        "resolved_seen": len(considered),
        "resolved_evidence_rows": production_records_matched,
        "merge_ready_evidence_rows": merge_ready_seen,
        "unique_append_documents": unique_append_docs,
        "accepted_documents": unique_append_docs,
        "duplicate_evidence_rows": duplicate_evidence_rows,
        "blocked_documents": len(blocked_documents),
        "duplicates": len(duplicates),
        "html_non_doc_blocked": html_non_doc_blocked,
        "merge_ready_seen": merge_ready_seen,
    }

    enriched_fallback_summary = {
        "groups_examined": resolved_via_enriched_fallback + enriched_fallback_invariant_failed,
        "groups_resolved": resolved_via_enriched_fallback,
        "groups_blocked": enriched_fallback_invariant_failed,
        "invariant_failed_reasons": dict(invariant_failed_reasons_counter),
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
        "proposed_backup_path": f"_tmp/data_licitaciones_before_f2_document_merge_v060o_{ts}.json",
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
        "mode": "F2_MERGE_GATE_V3_DRY_RUN",
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
        "enriched_fallback_summary": enriched_fallback_summary,
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
        f"[F2-MERGE v3] DRY-RUN | seen={counts['resolved_seen']} "
        f"unique_append={counts['unique_append_documents']} "
        f"blocked={counts['blocked_documents']} "
        f"dup_evidence={counts['duplicate_evidence_rows']} "
        f"dupes_other={counts['duplicates'] - counts['duplicate_evidence_rows']}"
    )
    print(
        f"[F2-MERGE v3] F2A_ARTIFACT_OK={f2a_status} F2B_RESOLUTION_OK={f2b_status} "
        f"DOCUMENT_MERGE_READY={dmr_status} PRODUCTION_WRITE_OK=FAIL "
        f"(production_write_performed=False)"
    )
    print(
        f"[F2-MERGE v3] join_methods: strict_id={resolved_via_strict_id} "
        f"ck={resolved_via_strict_id_canonical_key} "
        f"enriched_fallback={resolved_via_enriched_fallback} "
        f"ambiguous_remaining={ambiguous_remaining} "
        f"dup_evidence={duplicate_evidence_rows}"
    )
    if reason_counter:
        print(f"[F2-MERGE v3] block/dup reasons: {dict(reason_counter)}")
    print(f"[F2-MERGE v3] plan -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
