#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/public_record_projection.py  (ADG OPS / p289 / v0.7.4m)

PublicRecordProjection — F-05 / DS-11B public record contract + public
record identity (WRKOPS t_20260907_adgops289).

Standalone, construct-only per-record public projector. Mirrors the design
discipline already established for the document-level lane in
tools/public_projection.py (IB-3): pure, stdlib-only, no I/O, no network, no
clock reads, never mutates its input. Not wired into any live merge/build
call path here — exactly like tools/public_projection.py, this is the
SOURCE-IMPLEMENTED contract; wiring it into the scheduled merge / shard
build pipeline is IB-2 Integration/Readiness territory and is explicitly out
of scope for this task (handoff §0 roadmap).

--------------------------------------------------------------------------
R2 CORRECTION — PUBLIC_CANONICAL_TENDER identity domain (supersedes the
first-pass PUBLIC_RAW_RECORD candidate; full evidence in the WRKOPS
execution report's R1/R2 sections)
--------------------------------------------------------------------------
R1's read-only audit proved that `app.js::buildCanonicalRecords` already
groups raw records into logical tenders strictly by `r.id || r.url` (the
`url` tier is unreachable in current data: `id` is present on all 6154
records). Every one of the 2656 duplicate-`id` groups in the current
production monolith is exactly a pair of raw rows representing ONE product-
level tender — one row carries a `canonical_key`, the other does not.

The first-pass candidate anchored `public_id` on `canonical_key if present
else id`, which is unique across all 6154 raw rows but — because the two
rows in each pair have different anchors (one's own `canonical_key`, the
other the shared `id`) — silently assigned TWO different `public_id` values
to 2656 of the 3498 (75.99%) canonical tenders the product already treats
as one. Operator/Companion decision (R2): `public_id` must name the
PUBLIC_CANONICAL_TENDER, not the raw pipeline row, because a public
identifier must not fork into two identities for the same tender merely
because the internal monolith currently holds two raw representations of
it.

Corrected anchor: `record["id"]` ONLY. `canonical_key` is deliberately EXCLUDED
from public_id derivation (it remains a passthrough public field in
RECORD_PUBLIC_ALLOWED_FIELDS, unrelated to identity). `id` is exactly the
field `buildCanonicalRecords` already groups on, so this reproduces the
product's own existing canonical-tender semantics 1:1 rather than inventing
a new one — proven present-on-all-6154 and unique-per-canonical-group
(3498/3498) by direct census, and structurally pinned after first capture by
`fetch_licitaciones.py`'s merge-preservation logic (`prev.get("id") or
item.get("id")` always prefers the previously-stored value over a freshly
re-fetched one).

Uniqueness semantics under this domain: ONE public_id identifies ONE
canonical tender. Two raw rows sharing the same (validated) `id` are
REQUIRED to share the same `public_id` — that is not a collision. Two raw
rows with DIFFERENT `id` values that happened to mint the same `public_id`
IS a collision and fails closed (see `project_public_records`).

--------------------------------------------------------------------------
CRITICAL TECHNICAL IDS — never read for mutation, never overwritten
--------------------------------------------------------------------------
canonical_key, contract_folder_id, id, url, documents[].doc_ref,
documents[].doc_intel, notice_id (award_results[]/notice_history[] scope),
generation_id (dataset-generation domain, not touched here).

--------------------------------------------------------------------------
BOOKKEEPING DISPOSITION (preserved from the first pass; unchanged by R2)
--------------------------------------------------------------------------
This module is an ALLOWLIST (construct-only) projector, not a denylist
stripper: RECORD_PUBLIC_ALLOWED_FIELDS below is the complete, closed set of
top-level record keys carried into public output (plus the newly-minted
`public_id`). Any key not in that allowlist is omitted by construction —
including every internal-bookkeeping family named in handoff §4
(merge_*, delta_*, recovery_*, dry_run_*, provenance_note*,
source_gate_reason, action, lifecycle/enrichment/production-only/source-
merge-class bookkeeping) AND every additional orphaned bookkeeping family
found by direct census of the current production data with no current
producer in tools/*.py (action, merge_key/merge_key_source/
merge_key_missing/merge_action/merge_added_at/merge_prompt/merge_source,
delta_added_at/delta_audit_prompt/delta_prompt/delta_reason/delta_source/
delta_strategy, recovery_added_at/recovery_bucket/
recovery_operator_decision/recovery_policy_version/recovery_prerequisite/
recovery_prompt/recovery_reason/recovery_source, source_bucket_reason/
source_gate_reason/source_score/source_score_discs/source_score_kws/
source_zip_name, enrichment_needed, has_adjudicatari/has_award_results/
has_disciplines/has_documents/has_historial/has_kw/has_rellevancia,
production_matched, provenance_note/provenance_note_delta) — this is the
DS-11B "legacy record-level unknown-key debt" named in
tools/public_contract.py's own docstring (p273 §15.2). None of these
families appear anywhere in app.js (grepped directly): they are pipeline-
internal or orphaned, never a frontend/product consumer.

`titulo` (a duplicate/legacy Spanish-language mirror of `titol`, tracked by
tools/scheduled_fetch_merge.py's SCALAR_CONFLICT_FIELDS but never read by
app.js) is confirmed by R1/R2 as STRIP / LEGACY_ALIAS_NOT_PUBLIC_CONTRACT
and is deliberately left OUT of the allowlist.
"""

from __future__ import annotations

import hashlib
from typing import Any

# --------------------------------------------------------------------------- #
# Public identity constants (RECORD_PUBLIC / PUBLIC_CANONICAL_TENDER
# namespace, handoff §6.1; domain corrected by R2 §2)
# --------------------------------------------------------------------------- #

PUBLIC_ID_PREFIX = "adgops_rec_"
PUBLIC_ID_HEX_LEN = 32
PUBLIC_ID_DERIVATION_DOMAIN = "adgops.public.record/v1\0"

# --------------------------------------------------------------------------- #
# Closed allowlist of top-level public record fields (handoff §4/§7).
# Everything else is omitted by construction, including every internal-
# bookkeeping family and any future/unknown field this module has never
# been told about. `canonical_key` remains a passthrough public field here —
# it is simply excluded from public_id derivation (R2 §2).
# --------------------------------------------------------------------------- #

RECORD_PUBLIC_ALLOWED_FIELDS = frozenset({
    "id", "titol", "organisme", "adjudicatari", "tipus", "pressupost",
    "disciplines", "ccaa", "lloc", "data_pub", "data_limit", "estat",
    "estat_raw", "rellevancia", "url", "font", "kw", "cpv", "historial",
    "contract_folder_id", "canonical_key", "notice_type", "notice_type_code",
    "status_rank", "first_pub_date", "last_notice_date",
    "related_contract_ids", "sources_seen", "award_results", "documents",
    "notice_history", "duplicate_relations",
})

PUBLIC_ID_FIELD = "public_id"


class RejectedRecord(Exception):
    """Raised for a record whose public_id cannot be safely minted. Carries a
    stable, non-sensitive reason code only — never a raw record value (same
    reporting discipline as tools/public_projection.py's RejectedCandidate)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- #
# Anchor resolution + public_id minting (handoff §6.2/§6.3, domain corrected
# by R2 §2)
# --------------------------------------------------------------------------- #

def record_anchor(record: dict):
    """Resolve the stable PUBLIC_CANONICAL_TENDER anchor: `id` if it is a
    non-empty string, else None.

    R2 correction: `canonical_key` is deliberately NOT part of public identity
    derivation. `id` is exactly the field app.js::buildCanonicalRecords
    already groups raw records on (`r.id || r.url`, with the `url` tier
    unreachable in current data), so two raw rows sharing the same `id`
    intentionally resolve to the same anchor — and therefore the same
    public_id — because they represent one product-level tender, not two.
    Never reads, mutates, or returns canonical_key/contract_folder_id by
    side effect — this is a pure lookup.
    """
    if not isinstance(record, dict):
        return None
    rid = record.get("id")
    if isinstance(rid, str) and rid.strip():
        return rid
    return None


def mint_public_id(anchor: Any):
    """Mints public_id from a stable anchor (handoff §6.3), or returns None
    for an invalid/empty/non-string anchor. Never raises; callers decide how
    to fail. Identity is derived ONLY from `anchor` — nothing else."""
    if not isinstance(anchor, str) or not anchor.strip():
        return None
    payload = PUBLIC_ID_DERIVATION_DOMAIN + anchor
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return PUBLIC_ID_PREFIX + digest[:PUBLIC_ID_HEX_LEN]


# --------------------------------------------------------------------------- #
# Per-record projection (construct-only, handoff §6/§7)
# --------------------------------------------------------------------------- #

def project_public_record(record: dict) -> dict:
    """Builds one public record from an internal record: the closed
    allowlist of public fields, verbatim, plus a freshly-minted `public_id`.

    Construct-only (never copy.deepcopy + strip): only keys explicitly in
    RECORD_PUBLIC_ALLOWED_FIELDS are ever read from `record`, so an unknown
    or bookkeeping field can never silently pass through regardless of what
    it is named (handoff §7). Never mutates `record`. Raises
    RejectedRecord("public_id_anchor_missing_or_invalid") if no usable
    anchor exists — never falls back to array position, title, url,
    canonical_key, generation_id, or a random/wall-clock value (handoff
    §6.4; canonical_key exclusion is the R2 §2 domain correction).
    """
    if not isinstance(record, dict):
        raise RejectedRecord("record_not_an_object")

    anchor = record_anchor(record)
    public_id = mint_public_id(anchor)
    if public_id is None:
        raise RejectedRecord("public_id_anchor_missing_or_invalid")

    out: dict = {}
    for key in RECORD_PUBLIC_ALLOWED_FIELDS:
        if key in record:
            out[key] = record[key]
    out[PUBLIC_ID_FIELD] = public_id
    return out


def project_public_records(records: list) -> dict:
    """Projects every record in `records` and enforces the fail-closed
    PUBLIC_CANONICAL_TENDER collision rule (handoff §6.4, domain-corrected by
    R2 §3): a repeated `public_id` across distinct array entries is allowed
    — and required — when both entries share the same canonical-tender
    anchor (`id`), since that is the intended "same tender, multiple raw
    rows" case (R2 §3/§4). It is a fail-closed collision only when two
    entries with DIFFERENT anchors mint the same `public_id`.

    Returns {"accepted": bool, "rejected_reason": str | None,
             "records": [...] }.
    On success, "records" is the list of projected public records
    (RECORD_PUBLIC_ALLOWED_FIELDS + public_id), same order and length as the
    input, including intentional same-tender duplicates. On rejection,
    "records" is [] — never a partial result — and "rejected_reason" is one
    of:
      "records_not_a_list"
      "public_id_anchor_missing_or_invalid" (surfaced from the first
        record that failed to mint a public_id)
      "duplicate_public_id" (two DIFFERENT anchors minted the same
        public_id)

    Pure: no I/O, no clock, no network, no mutation of `records` or any
    record within it. Does not dedupe rows or change array cardinality
    (R2 §4 — cardinality/canonicalization remain IB-2 Integration/Readiness
    scope).
    """
    if not isinstance(records, list):
        return {"accepted": False, "rejected_reason": "records_not_a_list", "records": []}

    projected = []
    seen_public_ids: dict = {}  # public_id -> anchor that minted it
    for rec in records:
        anchor = record_anchor(rec) if isinstance(rec, dict) else None
        try:
            pub = project_public_record(rec)
        except RejectedRecord as exc:
            return {"accepted": False, "rejected_reason": exc.reason, "records": []}
        pid = pub[PUBLIC_ID_FIELD]
        if pid in seen_public_ids:
            if seen_public_ids[pid] != anchor:
                return {"accepted": False, "rejected_reason": "duplicate_public_id", "records": []}
            # Same canonical-tender anchor: intentional shared public_id
            # across multiple raw rows for the same logical tender — not a
            # collision (R2 §3).
        else:
            seen_public_ids[pid] = anchor
        projected.append(pub)

    return {"accepted": True, "rejected_reason": None, "records": projected}
