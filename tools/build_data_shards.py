#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_data_shards.py  (ADG OPS / p251 / v0.7.1d)

Generate derived, per-year JSON shards from the canonical monolith
data/licitaciones.json so the static web can load recent data first and
defer older/archive data.

KEY DESIGN LAW
- Canonical data remains data/licitaciones.json. This script NEVER writes
  to the input. Shards are reproducible, derived artifacts.
- The partition is loss-less: every source record lands in exactly one
  shard; total sharded records == source records. Records are copied
  byte-for-byte in content (no field mutation, no dedupe).
- This script is NOT a metadata authority (A1 §7.2, §12). It propagates the
  canonical meta minted by tools/scheduled_fetch_merge.py verbatim. It never
  mints a generation_id, never recomputes dataset_sha256, never reinterprets a
  timestamp or a publication state, and defines no public contract constant.
  It adds only what it alone can know: the build time, the shard inventory and
  the file-level integrity hashes.

Shard shape (identity stub + records; A1 §13):
    {"meta": {...9 keys...}, "data": [ ...records... ]}

Stdlib only. No third-party dependencies.

Usage:
    python tools/build_data_shards.py \
        --input data/licitaciones.json \
        --out-dir data \
        --years 2026,2025,2024 \
        --archive-name archive \
        --manifest data/licitaciones_manifest.json \
        --pretty
"""

import argparse
import datetime
import hashlib
import json
import os
import sys

# Shared canonical public contract (A1 LOCK-19). Import works both when run
# directly (`python tools/build_data_shards.py` → tools/ on sys.path) and when
# imported as `tools.build_data_shards`.
try:
    from tools import public_contract as pc
except ImportError:  # pragma: no cover - direct-run fallback
    import public_contract as pc

# Canonical meta keys propagated verbatim from the monolith (A1 §12) come from
# the shared contract module — this builder defines no contract constant of its
# own and must never substitute a value the merger minted.
PROPAGATED_META_KEYS = pc.SHARED_META_KEYS

# Priority tiers for the progressive web loader. Lower number = load sooner.
# 2026 + 2025 are priority 1 (recent / most relevant), 2024 priority 2, the
# rest (archive) priority 3.
PRIORITY_1_YEARS = {"2026", "2025"}


def log(msg):
    print(msg, file=sys.stderr)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def year_of(value):
    """Return a 4-digit year string from an ISO-ish date, else None."""
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return value[:4]
    return None


def classify_year(rec, explicit_years):
    """
    Conservative year classification (see prompt p200 YEAR CLASSIFICATION):
      1/2. publication date already used by UI/fetcher: data_pub
      2.   last_notice_date (latest notice publication)
      3.   deadline year only if no publication year exists: data_limit
    Returns (shard_key, derived_year, had_any_year):
      - shard_key is one of explicit_years or "archive"
      - derived_year is the raw 4-digit year string or None
      - had_any_year True if any date field yielded a year
    """
    y = (
        year_of(rec.get("data_pub"))
        or year_of(rec.get("last_notice_date"))
        or year_of(rec.get("data_limit"))
    )
    had_any_year = y is not None
    if y in explicit_years:
        return y, y, had_any_year
    return "archive", y, had_any_year


def record_id(rec):
    """Mirror the web's canonical grouping key (app.js buildCanonicalRecords)."""
    return rec.get("id") or rec.get("url")


def build(args):
    input_path = args.input
    out_dir = args.out_dir
    explicit_years = [y.strip() for y in args.years.split(",") if y.strip()]
    explicit_set = set(explicit_years)
    archive_name = args.archive_name
    pretty = args.pretty and not args.compact

    if not os.path.isfile(input_path):
        log("ERROR: input not found: %s" % input_path)
        return 2

    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        source_records = raw.get("data") or []
        source_meta = raw.get("meta") or {}
        top_shape = "object"
    elif isinstance(raw, list):
        source_records = raw
        source_meta = {}
        top_shape = "list"
    else:
        log("ERROR: unexpected top-level JSON type: %s" % type(raw).__name__)
        return 2

    source_count = len(source_records)
    source_sha = sha256_file(input_path)
    generated_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Partition --------------------------------------------------------------
    buckets = {y: [] for y in explicit_years}
    buckets[archive_name] = []
    missing_year_records = 0
    for rec in source_records:
        key, _yr, had_year = classify_year(rec, explicit_set)
        if not had_year:
            missing_year_records += 1
        if key in explicit_set:
            buckets[key].append(rec)
        else:
            buckets[archive_name].append(rec)

    sharded_records = sum(len(v) for v in buckets.values())

    # Duplicate-id audit (informational): source already contains dup ids that
    # the web collapses at runtime. We assert the partition introduces none.
    src_ids = [record_id(r) for r in source_records]
    src_id_multiset = sorted(i for i in src_ids if i is not None)
    shard_ids = []
    for y in explicit_years + [archive_name]:
        shard_ids.extend(record_id(r) for r in buckets[y])
    shard_id_multiset = sorted(i for i in shard_ids if i is not None)
    duplicate_ids = len(src_ids) - len(set(i for i in src_ids if i is not None))

    # Validation -------------------------------------------------------------
    errors = []
    if sharded_records != source_count:
        errors.append(
            "record count mismatch: source=%d sharded=%d" % (source_count, sharded_records)
        )
    if src_id_multiset != shard_id_multiset:
        errors.append("id multiset changed: partition lost/duplicated records")
    # priority-1 sanity: 2026 and 2025 must be present in the year set
    for need in ("2026", "2025"):
        if need not in explicit_set:
            errors.append("priority-1 year missing from --years: %s" % need)
    # archive must contain only <min(explicit) or unknown-year records
    min_year = min(int(y) for y in explicit_years) if explicit_years else 0
    for rec in buckets[archive_name]:
        _k, yr, _h = classify_year(rec, explicit_set)
        if yr is not None and int(yr) >= min_year and yr in explicit_set:
            errors.append("archive contains in-range year record: %s" % yr)
            break

    # Canonical contract preconditions (A1 §12): the monolith must already carry
    # the meta minted by the merger. If it does not, this build refuses rather
    # than inventing an identity — that is the merger's job, never this script's.
    missing_meta = [k for k in PROPAGATED_META_KEYS if source_meta.get(k) is None]
    if missing_meta:
        errors.append(
            "monolith meta is not canonical: missing %s "
            "(regenerate via tools/scheduled_fetch_merge.py --run-live)"
            % ", ".join(missing_meta)
        )

    declared_records = (source_meta.get("counts") or {}).get("records")
    if declared_records is not None and declared_records != source_count:
        errors.append(
            "monolith meta.counts.records %s != actual record count %d"
            % (declared_records, source_count)
        )

    dataset_sha256 = source_meta.get("dataset_sha256")
    generation_id = source_meta.get("generation_id")

    if errors:
        for e in errors:
            log("VALIDATION ERROR: %s" % e)
        if args.strict:
            return 1

    # Build manifest + shard payloads ---------------------------------------
    shard_order = explicit_years + [archive_name]
    shard_entries = []
    payloads = {}  # path -> (bytes, count)

    indent = 2 if pretty else None
    separators = None if pretty else (",", ":")

    for key in shard_order:
        records = buckets[key]
        is_archive = key == archive_name
        priority = 3 if is_archive else (1 if key in PRIORITY_1_YEARS else 2)
        fname = "licitaciones_%s.json" % key
        rel_path = "data/%s" % fname
        out_path = os.path.join(out_dir, fname)
        # 9-key identity stub (A1 §13). A shard is authoritative for nothing;
        # the stub exists so a stale shard left by an interrupted build is
        # detectable instead of being silently ingested. No self-hash: a file
        # cannot contain the hash of its own bytes — shard integrity lives in
        # the manifest's shards[].sha256.
        shard_meta = {
            "schema": source_meta.get("schema"),
            "schema_version": source_meta.get("schema_version"),
            "artifact": pc.ARTIFACT_SHARD,
            "publication_state": source_meta.get("publication_state"),
            "generation_id": generation_id,
            "dataset_sha256": dataset_sha256,
            "year": key,
            "priority": priority,
            "record_count": len(records),
        }
        shard_obj = {"meta": shard_meta, "data": records}
        body = json.dumps(shard_obj, ensure_ascii=False, indent=indent, separators=separators)
        body_bytes = body.encode("utf-8")
        payloads[out_path] = (body_bytes, len(records))
        shard_entries.append(
            {
                "year": key,
                "path": rel_path,
                "priority": priority,
                "record_count": len(records),
                "bytes": len(body_bytes),
                "sha256": hashlib.sha256(body_bytes).hexdigest(),
            }
        )

    # Canonical manifest (A1 §11). `meta` mirrors the monolith's canonical block
    # verbatim (every shared field from pc.SHARED_META_KEYS) and adds only the
    # one manifest-scope timestamp it alone can know. The legacy raw
    # `source_meta` envelope — which republished the monolith's internal paths
    # on the smallest, most-fetched public artifact — is gone, not renamed.
    #
    # No public `validation` block and no `validated_at`: the workflow gate is
    # the actual cross-artifact validator and runs only AFTER this script exits
    # (A1 §8 / p251 §8). Emitting builder-local reconciliation booleans here
    # would overclaim proof the builder never produced and would imply the gate
    # already ran. The builder therefore publishes no validation claim at all.
    manifest_meta = {"schema": source_meta.get("schema")}
    manifest_meta["schema_version"]      = source_meta.get("schema_version")
    manifest_meta["artifact"]            = pc.ARTIFACT_MANIFEST
    manifest_meta["publication_state"]   = source_meta.get("publication_state")
    manifest_meta["generation_id"]       = generation_id
    manifest_meta["dataset_sha256"]      = dataset_sha256
    manifest_meta["source_retrieved_at"] = source_meta.get("source_retrieved_at")
    manifest_meta["dataset_generated_at"] = source_meta.get("dataset_generated_at")
    manifest_meta["artifacts_built_at"]  = generated_at
    manifest_meta["pipeline"]            = source_meta.get("pipeline")
    manifest_meta["counts"]              = source_meta.get("counts")
    manifest_meta["sources"]             = source_meta.get("sources")
    manifest_meta["transformations"]     = source_meta.get("transformations")

    manifest = {
        "meta": manifest_meta,
        "monolith": {
            # Public artifact path only — never the caller's --input path, which
            # may be an absolute or temporary local location.
            "path": "data/%s" % os.path.basename(input_path),
            "record_count": source_count,
            "bytes": os.path.getsize(input_path),
            # Byte hash of the finished monolith FILE (distinct from the logical
            # dataset_sha256 over the records array). Verified by the workflow
            # gate against a fresh recomputation (A1 §15 / p251 §15).
            "file_sha256": source_sha,
        },
        "shards": shard_entries,
    }
    manifest_body = json.dumps(manifest, ensure_ascii=False, indent=indent, separators=separators)
    manifest_bytes = manifest_body.encode("utf-8")

    # Report -----------------------------------------------------------------
    log("source            : %s" % input_path)
    log("generation_id     : %s" % generation_id)
    log("dataset_sha256    : %s" % dataset_sha256)
    log("monolith_sha256   : %s" % source_sha)
    log("source_records    : %d" % source_count)
    log("sharded_records   : %d" % sharded_records)
    # Build diagnostics — internal only, never published (A1 §11).
    log("top_shape(int)    : %s" % top_shape)
    log("duplicate_ids(src): %d" % duplicate_ids)
    log("missing_year      : %d" % missing_year_records)
    log("artifacts_built_at: %s" % generated_at)
    log("-" * 56)
    for e in shard_entries:
        log(
            "shard %-8s p%d  %5d recs  %9d bytes  %s"
            % (e["year"], e["priority"], e["record_count"], e["bytes"], e["path"])
        )
    log("manifest                       %9d bytes  %s" % (len(manifest_bytes), args.manifest))

    if args.dry_run:
        log("DRY-RUN: no files written.")
        return 0 if not errors else (1 if args.strict else 0)

    # Write ------------------------------------------------------------------
    os.makedirs(out_dir, exist_ok=True)
    for out_path, (body_bytes, _c) in payloads.items():
        with open(out_path, "wb") as f:
            f.write(body_bytes)
    with open(args.manifest, "wb") as f:
        f.write(manifest_bytes)
    log("WROTE %d shard files + manifest." % len(payloads))

    return 0 if not errors else (1 if args.strict else 0)


def parse_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def main(argv=None):
    p = argparse.ArgumentParser(description="Build per-year JSON shards from licitaciones.json")
    p.add_argument("--input", default="data/licitaciones.json")
    p.add_argument("--out-dir", default="data")
    p.add_argument("--years", default="2026,2025,2024")
    p.add_argument("--archive-name", default="archive")
    p.add_argument("--manifest", default="data/licitaciones_manifest.json")
    p.add_argument("--pretty", dest="pretty", action="store_true", default=False)
    p.add_argument("--compact", dest="compact", action="store_true", default=False)
    p.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    p.add_argument("--strict", dest="strict", type=parse_bool, default=True)
    args = p.parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
