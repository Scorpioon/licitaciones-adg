#!/usr/bin/env python3
"""
tools/f2_merge_gate.py  —  F2 merge gate (DRY-RUN ONLY)
Reads an F2-B resolver manifest (schema f2b/1) and, optionally, the originating
F2-A manifest (schema f2a/1). Produces a dry-run plan of which resolved
candidates WOULD be eligible for a future production merge into
data/licitaciones.json.

This tool NEVER writes production data. It NEVER modifies, backs up, or stages
data/licitaciones.json. It only emits a sidecar plan (schema f2merge/1) so an
operator can review what a real merge would do.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

VERSION = "v0.6.0a"
SCHEMA = "f2merge/1"

_SAFE_PREFIXES = [
    os.path.normpath("_tmp"),
    os.path.normpath(os.path.join("data", "fetcher2")),
]
_FORBIDDEN = {
    os.path.normpath(os.path.join("data", "licitaciones.json")),
    os.path.normpath("fetch_licitaciones.py"),
    os.path.normpath(os.path.join("tools", "scheduled_fetch_merge.py")),
}

SAMPLE_LIMIT = 25


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


def _proposed_document_object(r):
    """Build the explicit document object a real merge WOULD append (not applied)."""
    title = r.get("original_title") or r.get("inferred_filename") or r.get("normalized_title")
    return {
        "url": r.get("final_url"),
        "title": title,
        "filename": r.get("inferred_filename"),
        "extension": r.get("inferred_extension"),
        "kind": r.get("original_kind"),
        "confidence": r.get("original_confidence"),
        "content_type": r.get("content_type"),
        "content_length": r.get("content_length"),
        "source_domain": r.get("source_domain"),
        "final_domain": r.get("final_domain"),
        "canonical_key": r.get("canonical_key"),
        "candidate_id": r.get("candidate_id"),
        "provenance": "f2b_resolver",
        "discovery_method": "detail_html_link_scan+f2b_resolve",
        "no_binary_download": True,
        "merge_ready": True,
    }


def _sample_addition(r):
    return {
        "canonical_key": r.get("canonical_key"),
        "candidate_id": r.get("candidate_id"),
        "title": r.get("original_title"),
        "inferred_filename": r.get("inferred_filename"),
        "final_url": r.get("final_url"),
        "source_domain": r.get("source_domain"),
        "final_domain": r.get("final_domain"),
        "content_type": r.get("content_type"),
        "content_length": r.get("content_length"),
        "kind": r.get("original_kind"),
        "confidence": r.get("original_confidence"),
        "proposed_document_object": _proposed_document_object(r),
    }


def _blocked_sample(r, reason):
    return {
        "canonical_key": r.get("canonical_key"),
        "candidate_id": r.get("candidate_id"),
        "final_url": r.get("final_url"),
        "source_domain": r.get("source_domain"),
        "content_type": r.get("content_type"),
        "resolver_status": r.get("resolver_status"),
        "resolved_is_document": r.get("resolved_is_document"),
        "block_reason": reason,
        "merge_blockers": r.get("merge_blockers"),
    }


def parse_args():
    ap = argparse.ArgumentParser(
        description="F2 merge gate (DRY-RUN ONLY) — plan a future merge; never writes production (ADG OPS v0.6.0a)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--input", default=None, help="F2-A manifest (schema f2a/1) — optional but recommended.")
    ap.add_argument("--resolved-input", required=True, help="F2-B resolver manifest (schema f2b/1) — required.")
    ap.add_argument("--output", required=True, help="Dry-run plan output path (_tmp/ or data/fetcher2/).")
    ap.add_argument("--domain", default=None, help="Restrict to candidates whose source/final domain contains DOMAIN.")
    ap.add_argument("--limit", type=int, default=100, help="Max resolved candidates to consider.")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="Dry-run only (always on). No production write occurs.")
    ap.add_argument("--allow-output-outside-safe-area", action="store_true",
                    help="Bypass safe-area restriction on output path.")
    return ap.parse_args()


def main():
    args = parse_args()

    ok, msg = _check_output_safe(args.output, args.allow_output_outside_safe_area)
    if not ok:
        print(f"[F2-MERGE BLOCKED] {msg}", file=sys.stderr)
        return 1

    f2b = _load_json(args.resolved_input, "F2-B manifest")
    if not str(f2b.get("schema", "")).startswith("f2b/"):
        print(f"[F2-MERGE BLOCKED] Unexpected resolved schema '{f2b.get('schema')}'. Expected f2b/1.", file=sys.stderr)
        return 1
    resolved = f2b.get("resolved_candidates", [])
    if not isinstance(resolved, list):
        print("[F2-MERGE BLOCKED] F2-B manifest missing 'resolved_candidates' list.", file=sys.stderr)
        return 1

    warnings = []
    f2a = None
    f2a_records_total = None
    existing_doc_urls = set()
    if args.input:
        f2a = _load_json(args.input, "F2-A manifest")
        if not str(f2a.get("schema", "")).startswith("f2a/"):
            print(f"[F2-MERGE BLOCKED] Unexpected F2-A schema '{f2a.get('schema')}'. Expected f2a/1.", file=sys.stderr)
            return 1
        f2a_records = f2a.get("records", [])
        f2a_records_total = len(f2a_records)
        # F2-A records carry only existing_documents_count (not URLs); note the
        # dedupe limitation so the operator knows production-side dedupe is pending.
        warnings.append(
            "F2-A manifest carries no existing-document URLs; cross-checking against "
            "production data/licitaciones.json is deferred to the real merge step."
        )
    else:
        warnings.append("F2-A input not provided; record context and dedupe coverage are reduced.")

    # Domain filter + limit.
    def _domain_match(r):
        if not args.domain:
            return True
        d = args.domain.lower()
        return d in (r.get("source_domain") or "").lower() or d in (r.get("final_domain") or "").lower()

    considered = [r for r in resolved if _domain_match(r)][: args.limit]

    additions = []
    blocked_samples = []
    blocker_counter = Counter()
    seen_final_urls = set()
    duplicates_skipped = 0
    documents_to_add = []

    for r in considered:
        if not r.get("merge_ready_candidate"):
            reason = "not_merge_ready"
            blocker_counter[reason] += 1
            for b in (r.get("merge_blockers") or ["unspecified"]):
                blocker_counter[f"blocker:{b}"] += 1
            if len(blocked_samples) < SAMPLE_LIMIT:
                blocked_samples.append(_blocked_sample(r, reason))
            continue

        final_url = r.get("final_url")
        dup_key = (r.get("canonical_key"), final_url)
        if dup_key in seen_final_urls or final_url in existing_doc_urls:
            duplicates_skipped += 1
            blocker_counter["duplicate_in_batch"] += 1
            if len(blocked_samples) < SAMPLE_LIMIT:
                blocked_samples.append(_blocked_sample(r, "duplicate"))
            continue

        seen_final_urls.add(dup_key)
        documents_to_add.append(r)
        if len(additions) < SAMPLE_LIMIT:
            additions.append(_sample_addition(r))

    records_considered_keys = {r.get("canonical_key") for r in considered if r.get("canonical_key")}
    add_by_key = Counter(r.get("canonical_key") for r in documents_to_add)

    if any(r.get("content_length") is None for r in documents_to_add):
        warnings.append("Some merge-ready candidates have no content_length (streaming gateway); acceptable but noted.")

    # Conservative verdict: this tool NEVER greenlights a production write.
    merge_verdict = {
        "MERGE_OK": "FAIL",
        "reason": (
            "Dry-run merge gate does not authorize production writes. A real merge "
            "requires operator review and a dedicated apply step with production-side "
            "dedupe against data/licitaciones.json."
        ),
        "documents_would_add": len(documents_to_add),
    }

    merge_plan = {
        "action": "append_documents_to_records",
        "target": os.path.join("data", "licitaciones.json"),
        "production_write_performed": False,
        "dry_run": True,
        "documents_to_add_count": len(documents_to_add),
        "distinct_records_affected": len(add_by_key),
        "additions_per_canonical_key": dict(add_by_key.most_common(SAMPLE_LIMIT)),
        "note": "No data was written. Proposed document objects are illustrative only.",
    }

    report = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "mode": "F2_MERGE_GATE_DRY_RUN",
        "production_write_performed": False,
        "input_f2a": {
            "path": args.input,
            "schema": f2a.get("schema") if f2a else None,
            "version": f2a.get("version") if f2a else None,
            "records_total": f2a_records_total,
        },
        "input_f2b": {
            "path": args.resolved_input,
            "schema": f2b.get("schema"),
            "version": f2b.get("version"),
            "source_f2a_version": f2b.get("source_f2a_version"),
        },
        "filter_params": {
            "domain": args.domain,
            "limit": args.limit,
        },
        "records_considered": len(records_considered_keys),
        "candidates_considered": len(considered),
        "documents_to_add_count": len(documents_to_add),
        "duplicates_skipped_count": duplicates_skipped,
        "blocked_count": sum(1 for r in considered if not r.get("merge_ready_candidate")),
        "verdict": merge_verdict,
        "sample_additions": additions,
        "blocked_samples": blocked_samples,
        "blockers": dict(blocker_counter),
        "warnings": warnings,
        "merge_plan": merge_plan,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[F2-MERGE] DRY-RUN | considered={len(considered)} "
          f"would_add={len(documents_to_add)} dupes={duplicates_skipped} "
          f"blocked={report['blocked_count']}")
    print(f"[F2-MERGE] MERGE_OK: {merge_verdict['MERGE_OK']} (production_write_performed=False)")
    if blocker_counter:
        print(f"[F2-MERGE] blockers: {dict(blocker_counter)}")
    print(f"[F2-MERGE] plan -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
