#!/usr/bin/env python3
"""
tools/f2_quality_gate.py — F2 quality gate: artifact verdict + merge-blocker report.
Gate version: v0.5.0o
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

GATE_VERSION = "v0.5.0o"
REPORT_SCHEMA = "f2_quality_gate/1"

SAFE_OUTPUT_DIRS = ("_tmp", os.path.join("data", "fetcher2"))

GENERIC_TITLES = frozenset([
    "documento pdf",
    "documento html",
    "documento xml",
    "ver",
    "deferred modules",
])

NAV_LIKE_LABELS = frozenset([
    "public organizations",
    "verify csv",
    "statistics",
    "open data",
    "contact",
    "buscador",
    "information",
    "home",
    "search",
    "companies",
    "contractor profile",
    "welcome",
    "bienvenidos",
    "ongi etorri",
    "benvinguts",
    "benvidos",
    "bienvenue",
])

V2_REQUIRED_FIELDS = [
    "candidate_id",
    "canonical_key",
    "normalized_url",
    "normalized_title",
    "source_domain",
    "source_adapter",
    "needs_resolver",
    "merge_ready",
]

SAMPLE_LIMIT = 20


def parse_args():
    p = argparse.ArgumentParser(
        description="F2 quality gate — artifact verdict + merge-blocker report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input", required=True, metavar="PATH", help="F2-A manifest JSON path.")
    p.add_argument("--output", required=True, metavar="PATH", help="Output report JSON path.")
    p.add_argument("--artifact-error-rate-max", type=float, default=0.05, metavar="FLOAT",
                   help="Max error rate for ARTIFACT_OK PASS.")
    p.add_argument("--merge-error-rate-max", type=float, default=0.01, metavar="FLOAT",
                   help="Max error rate for MERGE_OK PASS.")
    p.add_argument("--merge-generic-title-ratio-max", type=float, default=0.10, metavar="FLOAT",
                   help="Max generic title ratio for MERGE_OK PASS.")
    p.add_argument("--merge-unresolved-gateway-ratio-max", type=float, default=0.10, metavar="FLOAT",
                   help="Max unresolved-gateway ratio for MERGE_OK PASS.")
    p.add_argument("--merge-nav-title-count-max", type=int, default=0, metavar="INT",
                   help="Max nav_title_count for MERGE_OK PASS.")
    p.add_argument("--merge-unknown-kind-ratio-max", type=float, default=0.05, metavar="FLOAT",
                   help="Max unknown-kind ratio for MERGE_OK PASS.")
    p.add_argument("--allow-output-outside-safe-area", action="store_true", default=False,
                   help="Allow writing report outside _tmp/ or data/fetcher2/.")

    try:
        p.add_argument("--print-report", action=argparse.BooleanOptionalAction, default=True,
                       help="Print compact terminal report after writing.")
    except AttributeError:
        g = p.add_mutually_exclusive_group()
        g.add_argument("--print-report", dest="print_report", action="store_true", default=True,
                       help="Print compact terminal report (default).")
        g.add_argument("--no-print-report", dest="print_report", action="store_false",
                       help="Suppress terminal report.")

    return p.parse_args()


def fail(msg):
    print(f"[F2-GATE] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def is_safe_output(path: Path) -> bool:
    try:
        resolved = path.resolve()
        cwd = Path.cwd().resolve()
        rel = resolved.relative_to(cwd)
        parts = rel.parts
        if parts and parts[0] == "_tmp":
            return True
        if len(parts) >= 2 and parts[0] == "data" and parts[1] == "fetcher2":
            return True
        return False
    except ValueError:
        return False


def _candidate_sample(c):
    return {
        "candidate_id": c.get("candidate_id"),
        "canonical_key": c.get("canonical_key"),
        "title": c.get("title"),
        "normalized_title": c.get("normalized_title"),
        "url": c.get("url"),
        "source_domain": c.get("source_domain"),
        "kind": c.get("kind"),
        "confidence": c.get("confidence"),
        "extension": c.get("extension"),
        "needs_resolver": c.get("needs_resolver"),
    }


def _error_sample(rec):
    return {
        "id": rec.get("id"),
        "canonical_key": rec.get("canonical_key"),
        "url": rec.get("url"),
        "error": rec.get("error"),
        "http_status": rec.get("http_status"),
    }


def compute_metrics(manifest):
    qs = manifest.get("quality_summary", {})
    records = manifest.get("records", [])

    records_attempted = qs.get("records_attempted", len(records))

    all_candidates = [c for rec in records for c in rec.get("candidates", [])]
    candidates_after_filter = len(all_candidates)

    candidates_before_filter = qs.get("candidates_before_filter", candidates_after_filter)
    records_with_candidates = qs.get(
        "records_with_candidates",
        sum(1 for rec in records if rec.get("candidates")),
    )
    error_count = qs.get(
        "error_count",
        sum(1 for rec in records if rec.get("error")),
    )

    error_rate = error_count / records_attempted if records_attempted else 0.0
    records_with_candidates_ratio = records_with_candidates / records_attempted if records_attempted else 0.0

    # Generic titles — recompute from candidates for validation
    generic_title_count = sum(
        1 for c in all_candidates if c.get("normalized_title", "").lower() in GENERIC_TITLES
    )
    generic_title_ratio = generic_title_count / candidates_after_filter if candidates_after_filter else 0.0

    nav_title_count = qs.get("nav_title_count", 0)

    # Gate's own nav-like detection (independent of F2-A nav filter)
    nav_like_survivor_list = [
        c for c in all_candidates if c.get("normalized_title", "").lower() in NAV_LIKE_LABELS
    ]

    # Unresolved gateway: extension == "gateway" OR needs_resolver is True
    unresolved_gateway_list = [
        c for c in all_candidates
        if c.get("extension") == "gateway" or c.get("needs_resolver") is True
    ]
    unresolved_gateway_count = len(unresolved_gateway_list)
    unresolved_gateway_ratio = unresolved_gateway_count / candidates_after_filter if candidates_after_filter else 0.0

    unknown_kind_list = [c for c in all_candidates if c.get("kind") == "unknown"]
    unknown_kind_count = len(unknown_kind_list)
    unknown_kind_ratio = unknown_kind_count / candidates_after_filter if candidates_after_filter else 0.0

    conf_counts = qs.get("confidence_counts", {})
    high_confidence_count = conf_counts.get(
        "high", sum(1 for c in all_candidates if c.get("confidence") == "high")
    )
    medium_confidence_count = conf_counts.get(
        "medium", sum(1 for c in all_candidates if c.get("confidence") == "medium")
    )
    low_confidence_count = conf_counts.get(
        "low", sum(1 for c in all_candidates if c.get("confidence") == "low")
    )
    high_confidence_ratio = high_confidence_count / candidates_after_filter if candidates_after_filter else 0.0

    # Missing v2 fields
    missing_v2_field_count = 0
    missing_v2_examples = []
    for c in all_candidates:
        missing = [f for f in V2_REQUIRED_FIELDS if f not in c]
        if missing:
            missing_v2_field_count += 1
            if len(missing_v2_examples) < SAMPLE_LIMIT:
                s = _candidate_sample(c)
                s["missing_fields"] = missing
                missing_v2_examples.append(s)

    merge_ready_true_count = sum(1 for c in all_candidates if c.get("merge_ready") is True)
    merge_ready_false_count = sum(1 for c in all_candidates if not c.get("merge_ready"))

    per_domain_counts = qs.get("per_domain_counts") or dict(
        Counter(c.get("source_domain", "") for c in all_candidates)
    )
    kind_counts = qs.get("kind_counts") or dict(
        Counter(c.get("kind", "") for c in all_candidates)
    )
    extension_counts = qs.get("extension_counts") or dict(
        Counter(c.get("extension", "") for c in all_candidates)
    )
    title_counts_top = qs.get("title_counts_top", {})
    skipped_counts = qs.get("skipped_counts", {})

    error_records = [rec for rec in records if rec.get("error")]

    metrics = {
        "records_attempted": records_attempted,
        "records_with_candidates": records_with_candidates,
        "candidates_before_filter": candidates_before_filter,
        "candidates_after_filter": candidates_after_filter,
        "error_count": error_count,
        "error_rate": round(error_rate, 8),
        "records_with_candidates_ratio": round(records_with_candidates_ratio, 6),
        "generic_title_count": generic_title_count,
        "generic_title_ratio": round(generic_title_ratio, 6),
        "nav_title_count": nav_title_count,
        "nav_like_survivor_count": len(nav_like_survivor_list),
        "unresolved_gateway_count": unresolved_gateway_count,
        "unresolved_gateway_ratio": round(unresolved_gateway_ratio, 6),
        "unknown_kind_count": unknown_kind_count,
        "unknown_kind_ratio": round(unknown_kind_ratio, 6),
        "high_confidence_count": high_confidence_count,
        "high_confidence_ratio": round(high_confidence_ratio, 6),
        "medium_confidence_count": medium_confidence_count,
        "low_confidence_count": low_confidence_count,
        "missing_v2_field_count": missing_v2_field_count,
        "merge_ready_true_count": merge_ready_true_count,
        "merge_ready_false_count": merge_ready_false_count,
        "per_domain_counts": per_domain_counts,
        "kind_counts": kind_counts,
        "extension_counts": extension_counts,
        "title_counts_top": title_counts_top,
        "skipped_counts": skipped_counts,
    }

    samples = {
        "nav_like_survivors": [_candidate_sample(c) for c in nav_like_survivor_list[:SAMPLE_LIMIT]],
        "generic_title_examples": [
            _candidate_sample(c) for c in all_candidates
            if c.get("normalized_title", "").lower() in GENERIC_TITLES
        ][:SAMPLE_LIMIT],
        "unresolved_gateway_examples": [
            _candidate_sample(c) for c in unresolved_gateway_list[:SAMPLE_LIMIT]
        ],
        "unknown_kind_examples": [_candidate_sample(c) for c in unknown_kind_list[:SAMPLE_LIMIT]],
        "error_records": [_error_sample(rec) for rec in error_records[:SAMPLE_LIMIT]],
        "missing_v2_field_examples": missing_v2_examples,
    }

    return metrics, samples


def evaluate_verdicts(metrics, thresholds):
    artifact_blocking = []
    artifact_warnings = []
    merge_blocking = []

    # ARTIFACT_OK
    if metrics["error_rate"] > thresholds["artifact_error_rate_max"]:
        artifact_blocking.append(
            f"error_rate {metrics['error_rate']:.6f} > {thresholds['artifact_error_rate_max']}"
        )
    if metrics["candidates_after_filter"] == 0:
        artifact_blocking.append("candidates_after_filter is zero — no output produced")

    if metrics["missing_v2_field_count"] > 0:
        artifact_warnings.append(
            f"missing_v2_field_count: {metrics['missing_v2_field_count']} candidates lack v2 model fields"
        )
    if metrics["generic_title_ratio"] > 0.30:
        artifact_warnings.append(
            f"generic_title_ratio {metrics['generic_title_ratio']:.4f} is high"
        )
    if metrics["unresolved_gateway_ratio"] > 0.30:
        artifact_warnings.append(
            f"unresolved_gateway_ratio {metrics['unresolved_gateway_ratio']:.4f} is high"
        )
    if metrics["nav_like_survivor_count"] > 0:
        artifact_warnings.append(
            f"nav_like_survivors: {metrics['nav_like_survivor_count']} suspicious nav-like titles found in kept candidates"
        )
    if metrics["unknown_kind_ratio"] > 0.10:
        artifact_warnings.append(
            f"unknown_kind_ratio {metrics['unknown_kind_ratio']:.4f} is high"
        )
    if metrics["records_with_candidates_ratio"] < 0.50:
        artifact_warnings.append(
            f"records_with_candidates_ratio {metrics['records_with_candidates_ratio']:.4f} is low"
        )

    artifact_ok = "PASS" if not artifact_blocking else "FAIL"

    # MERGE_OK — all conditions must hold
    if artifact_ok == "FAIL":
        merge_blocking.append("ARTIFACT_OK is FAIL — merge requires a valid artifact")
    if metrics["error_rate"] > thresholds["merge_error_rate_max"]:
        merge_blocking.append(
            f"error_rate {metrics['error_rate']:.6f} > {thresholds['merge_error_rate_max']}"
        )
    if metrics["generic_title_ratio"] > thresholds["merge_generic_title_ratio_max"]:
        merge_blocking.append(
            f"generic_title_ratio {metrics['generic_title_ratio']:.4f} > "
            f"{thresholds['merge_generic_title_ratio_max']} — too many unresolved generic titles"
        )
    if metrics["unresolved_gateway_ratio"] > thresholds["merge_unresolved_gateway_ratio_max"]:
        merge_blocking.append(
            f"unresolved_gateway_ratio {metrics['unresolved_gateway_ratio']:.4f} > "
            f"{thresholds['merge_unresolved_gateway_ratio_max']} — too many gateway/needs_resolver candidates"
        )
    if metrics["nav_title_count"] > thresholds["merge_nav_title_count_max"]:
        merge_blocking.append(
            f"nav_title_count {metrics['nav_title_count']} > {thresholds['merge_nav_title_count_max']}"
        )
    if metrics["nav_like_survivor_count"] > 0:
        merge_blocking.append(
            f"nav_like_survivors: {metrics['nav_like_survivor_count']} suspicious nav-like titles found in kept candidates"
        )
    if metrics["unknown_kind_ratio"] > thresholds["merge_unknown_kind_ratio_max"]:
        merge_blocking.append(
            f"unknown_kind_ratio {metrics['unknown_kind_ratio']:.4f} > "
            f"{thresholds['merge_unknown_kind_ratio_max']}"
        )
    if metrics["missing_v2_field_count"] > 0:
        merge_blocking.append(
            f"missing_v2_field_count: {metrics['missing_v2_field_count']} candidates lack required v2 model fields"
        )
    if metrics["merge_ready_true_count"] == 0:
        merge_blocking.append(
            "merge_ready_true_count is zero — no candidates are marked merge-ready"
        )

    merge_ok = "PASS" if not merge_blocking else "FAIL"

    return {
        "ARTIFACT_OK": {
            "status": artifact_ok,
            "blocking_rules": artifact_blocking,
            "warnings": artifact_warnings,
        },
        "MERGE_OK": {
            "status": merge_ok,
            "blocking_rules": merge_blocking,
            "warnings": [],
        },
    }


def build_recommendation(verdicts, metrics):
    merge_ok = verdicts["MERGE_OK"]["status"]
    artifact_ok = verdicts["ARTIFACT_OK"]["status"]
    notes = []

    if merge_ok == "PASS":
        next_step = "Manifest is merge-ready. Proceed with F2-B or scheduled merge."
    elif artifact_ok == "PASS":
        next_step = "Manifest is artifact-safe but not merge-ready. Resolve blockers before merging."
        if metrics["unresolved_gateway_ratio"] > 0.5:
            notes.append(
                "High gateway ratio: F2-B resolver required to resolve gateway URLs before merge."
            )
        if metrics["generic_title_ratio"] > 0.5:
            notes.append("High generic title ratio: title enrichment or resolver needed.")
        if metrics["nav_like_survivor_count"] > 0:
            notes.append(
                f"Nav-like survivors ({metrics['nav_like_survivor_count']}) detected: "
                "expand F2-A filter or add gate pre-filter step."
            )
        if metrics["merge_ready_true_count"] == 0:
            notes.append(
                "No candidates have merge_ready=True. Run F2-B resolver to produce merge-ready candidates."
            )
    else:
        next_step = "Manifest is invalid. Fix F2-A run before reprocessing."

    return {"next_step": next_step, "notes": notes}


def main():
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        fail(f"Input file not found: {input_path}")

    if not args.allow_output_outside_safe_area and not is_safe_output(output_path):
        fail(
            f"Output path '{output_path}' is outside the safe area (_tmp/, data/fetcher2/). "
            "Pass --allow-output-outside-safe-area to override."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(input_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"Input JSON is not parseable: {e}")
    except OSError as e:
        fail(f"Cannot read input file: {e}")

    if not isinstance(manifest.get("records"), list):
        fail("Manifest missing 'records' list — malformed or wrong schema.")

    input_schema = manifest.get("schema", "")
    if not input_schema.startswith("f2a/"):
        fail(f"Unexpected manifest schema '{input_schema}'. Expected f2a/1 or compatible.")

    metrics, samples = compute_metrics(manifest)

    thresholds = {
        "artifact_error_rate_max": args.artifact_error_rate_max,
        "merge_error_rate_max": args.merge_error_rate_max,
        "merge_generic_title_ratio_max": args.merge_generic_title_ratio_max,
        "merge_unresolved_gateway_ratio_max": args.merge_unresolved_gateway_ratio_max,
        "merge_nav_title_count_max": args.merge_nav_title_count_max,
        "merge_unknown_kind_ratio_max": args.merge_unknown_kind_ratio_max,
    }

    verdicts = evaluate_verdicts(metrics, thresholds)
    recommendation = build_recommendation(verdicts, metrics)

    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_version": GATE_VERSION,
        "input": {
            "path": str(input_path),
            "schema": manifest.get("schema"),
            "version": manifest.get("version"),
            "generated_at": manifest.get("generated_at"),
        },
        "thresholds": thresholds,
        "metrics": metrics,
        "verdicts": verdicts,
        "samples": samples,
        "recommendation": recommendation,
    }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    except OSError as e:
        fail(f"Cannot write output report: {e}")

    if args.print_report:
        ao = verdicts["ARTIFACT_OK"]["status"]
        mo = verdicts["MERGE_OK"]["status"]
        m = metrics
        print(f"[F2-GATE] input: {input_path}")
        print(f"[F2-GATE] schema: {manifest.get('schema')} version: {manifest.get('version')}")
        print(
            f"[F2-GATE] candidates: {m['candidates_after_filter']}  "
            f"records: {m['records_attempted']}  "
            f"errors: {m['error_count']}  "
            f"rate: {m['error_rate']:.6f}"
        )
        print(f"[F2-GATE] ARTIFACT_OK: {ao}")
        if verdicts["ARTIFACT_OK"]["warnings"]:
            print("[F2-GATE] artifact warnings:")
            for w in verdicts["ARTIFACT_OK"]["warnings"]:
                print(f"  - {w}")
        print(f"[F2-GATE] MERGE_OK: {mo}")
        if mo == "FAIL":
            print("[F2-GATE] blocking:")
            for b in verdicts["MERGE_OK"]["blocking_rules"]:
                print(f"  - {b}")
        print(f"[F2-GATE] report -> {output_path}")


if __name__ == "__main__":
    main()
