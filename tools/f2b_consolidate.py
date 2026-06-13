#!/usr/bin/env python3
"""
tools/f2b_consolidate.py  —  F2-B batch consolidator
Merges multiple f2b/1 sidecar files into a single consolidated f2b/1 artifact.
Deduplicates by candidate_id and rebuilds quality_summary.
Never reads or writes production data.
"""

import argparse
import glob as _glob_module
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

VERSION = "v0.6.0g"
SCHEMA = "f2b/1"

_SAFE_PREFIXES = [
    os.path.normpath("_tmp"),
    os.path.normpath(os.path.join("data", "fetcher2")),
]
_FORBIDDEN = {
    os.path.normpath(os.path.join("data", "licitaciones.json")),
    os.path.normpath("fetch_licitaciones.py"),
    os.path.normpath(os.path.join("tools", "scheduled_fetch_merge.py")),
}


def _check_output_safe(path, allow_outside=False):
    norm = os.path.normpath(path)
    if norm in _FORBIDDEN:
        return False, f"Output path resolves to forbidden file: {norm}"
    if not allow_outside and not any(norm.startswith(p) for p in _SAFE_PREFIXES):
        return False, "Output path outside safe area; use --allow-output-outside-safe-area to override"
    return True, None


def _clean_content_type(raw):
    if not raw:
        return "", ""
    full = raw.strip().lower()
    base = full.split(";", 1)[0].strip()
    return full, base


def _ratio(num, den):
    return round(num / den, 6) if den else 0.0


def _build_quality_summary(resolved_list):
    attempted = len(resolved_list)
    resolved_count = sum(1 for r in resolved_list if r.get("resolver_status") == "resolved")
    unresolved_count = sum(1 for r in resolved_list if r.get("resolver_status") == "unresolved")
    error_count = sum(
        1 for r in resolved_list if r.get("resolver_status") in ("error", "skipped")
    )
    pdf_count = sum(1 for r in resolved_list if r.get("resolved_is_pdf"))
    doc_count = sum(1 for r in resolved_list if r.get("resolved_is_document"))
    merge_ready = sum(1 for r in resolved_list if r.get("merge_ready_candidate"))

    ct_counts = Counter(
        _clean_content_type(r.get("content_type"))[1] or "" for r in resolved_list
    )
    method_counts = Counter(r.get("resolver_method") or "" for r in resolved_list)
    status_counts = Counter(r.get("resolver_status") or "" for r in resolved_list)
    final_domain_counts = Counter(
        r.get("final_domain") or "" for r in resolved_list if r.get("final_domain")
    )

    return {
        "candidates_attempted": attempted,
        "resolved_count": resolved_count,
        "resolved_ratio": _ratio(resolved_count, attempted),
        "unresolved_count": unresolved_count,
        "error_count": error_count,
        "resolved_document_count": doc_count,
        "resolved_document_ratio": _ratio(doc_count, attempted),
        "resolved_pdf_count": pdf_count,
        "resolved_pdf_ratio": _ratio(pdf_count, attempted),
        "resolver_error_rate": _ratio(error_count, attempted),
        "merge_ready_candidate_count": merge_ready,
        "content_type_counts": dict(ct_counts),
        "resolver_method_counts": dict(method_counts),
        "resolver_status_counts": dict(status_counts),
        "final_domain_counts": dict(final_domain_counts),
        "warnings": [],
        "duplicate_candidate_id_count": 0,
        "input_file_count": 0,
    }


def _load_f2b_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    schema = data.get("schema", "")
    if schema != "f2b/1":
        raise ValueError(f"Unexpected schema '{schema}' in {path}; expected f2b/1")
    return data


def parse_args():
    ap = argparse.ArgumentParser(
        description="F2-B consolidator — merges multiple f2b/1 sidecars (ADG OPS v0.6.0g)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--inputs", nargs="+", metavar="FILE",
                    help="One or more f2b/1 sidecar JSON files.")
    ap.add_argument("--glob", metavar="PATTERN",
                    help="Glob pattern to collect f2b/1 files (e.g. '_tmp/f2b_batch_*.json').")
    ap.add_argument("--output", required=True,
                    help="Consolidated output path (_tmp/ or data/fetcher2/).")
    ap.add_argument("--allow-output-outside-safe-area", action="store_true",
                    help="Bypass safe-area restriction on output path.")
    return ap.parse_args()


def main():
    args = parse_args()

    ok, msg = _check_output_safe(args.output, args.allow_output_outside_safe_area)
    if not ok:
        print(f"[F2B-CONSOLIDATE BLOCKED] {msg}", file=sys.stderr)
        return 1

    # Collect input files from --inputs and/or --glob
    input_files = []
    if args.inputs:
        input_files.extend(args.inputs)
    if args.glob:
        matched = sorted(_glob_module.glob(args.glob))
        if not matched:
            print(f"[F2B-CONSOLIDATE] Warning: --glob '{args.glob}' matched no files.", file=sys.stderr)
        input_files.extend(matched)

    # Deduplicate while preserving order
    seen_paths = set()
    unique_files = []
    for p in input_files:
        if p not in seen_paths:
            seen_paths.add(p)
            unique_files.append(p)
    input_files = unique_files

    if not input_files:
        print("[F2B-CONSOLIDATE BLOCKED] No input files specified (use --inputs or --glob).", file=sys.stderr)
        return 1

    print(f"[F2B-CONSOLIDATE] input_files={len(input_files)}")

    # Load and merge
    all_resolved = []
    seen_ids = set()
    duplicate_count = 0
    source_f2a_inputs = set()
    warnings = []

    for path in input_files:
        try:
            data = _load_f2b_file(path)
        except (OSError, json.JSONDecodeError, ValueError) as e:
            print(f"[F2B-CONSOLIDATE BLOCKED] Cannot load '{path}': {e}", file=sys.stderr)
            return 1

        src = data.get("input") or data.get("source_f2a_input")
        if src:
            source_f2a_inputs.add(src)

        candidates = data.get("resolved_candidates", [])
        file_dupes = 0
        for c in candidates:
            cid = c.get("candidate_id")
            if cid and cid in seen_ids:
                duplicate_count += 1
                file_dupes += 1
                continue
            if cid:
                seen_ids.add(cid)
            all_resolved.append(c)

        dupe_note = f" ({file_dupes} dupes skipped)" if file_dupes else ""
        print(f"  loaded: {path} -> {len(candidates)} candidates{dupe_note}")

    quality_summary = _build_quality_summary(all_resolved)
    quality_summary["duplicate_candidate_id_count"] = duplicate_count
    quality_summary["input_file_count"] = len(input_files)

    if duplicate_count:
        warnings.append(f"{duplicate_count} duplicate candidate_ids deduplicated across input files")

    source_f2a_input = None
    if len(source_f2a_inputs) == 1:
        source_f2a_input = list(source_f2a_inputs)[0]
    elif len(source_f2a_inputs) > 1:
        warnings.append(f"Multiple source_f2a_inputs found: {sorted(source_f2a_inputs)}")

    quality_summary["warnings"] = warnings

    out = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "mode": "F2-B_CONSOLIDATED",
        "input_files": input_files,
        "source_f2a_input": source_f2a_input,
        "counts": {
            "input_files": len(input_files),
            "candidates_attempted": len(all_resolved),
            "duplicate_candidate_id_count": duplicate_count,
            "resolved_count": quality_summary["resolved_count"],
            "merge_ready_candidate_count": quality_summary["merge_ready_candidate_count"],
        },
        "resolved_candidates": all_resolved,
        "quality_summary": quality_summary,
        "warnings": warnings,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    qs = quality_summary
    print(f"[F2B-CONSOLIDATE] done: inputs={len(input_files)} candidates={len(all_resolved)} "
          f"duplicates_removed={duplicate_count} resolved={qs['resolved_count']} "
          f"docs={qs['resolved_document_count']} merge_ready={qs['merge_ready_candidate_count']}")
    print(f"[F2B-CONSOLIDATE] manifest -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
