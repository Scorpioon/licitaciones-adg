#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/canonical_tender_merge.py  (ADG-OPS / WRKOPS t_20260908_adgops292 / v0.7.4p)

Standalone, non-live-wired canonical-tender merge engine implementing the
merge contract formally closed by Prompt 291 (t_20260908_adgops291, R2,
CONTRACT_READY_FOR_IMPLEMENTATION, v0.7.4o) and the field laws specified by
the Prompt 292 handoff
(_wrkops/handoffs/adgops_prompt_292_canonical_tender_lossless_merge_implementation.md).

Transforms a final in-memory raw-record list (the shape of
`data/licitaciones.json`'s `data[]` array) into a deterministic in-memory
canonical-tender list: one row per logical tender `id`.

This module is NOT:
  - a replacement for internal fetch/merge history (fetch_licitaciones.py);
  - a live workflow integration;
  - a data migration;
  - a public-record projector (tools/public_record_projection.py);
  - a DocIntel projector (tools/public_projection.py);
  - a privacy validator (tools/privacy_validator.py);
  - a shard builder (tools/build_data_shards.py).

It performs no file I/O and writes no data files. It does not mint
`public_id` (that remains public_record_projection.py's responsibility, per
the Prompt 289/291 R2 identity contract).

STATUS_RANK below is copied verbatim from fetch_licitaciones.py:474-486
(v0.4.5z), NOT imported: importing fetch_licitaciones.py is unsafe for this
utility module, because that module performs `import requests` at top level
with a `sys.exit(...)` fallback if requests is missing (fetch_licitaciones.py:39-44),
in addition to argparse/network-fetcher machinery with no import guard --
none of which this pure, in-memory canonicalizer may risk pulling in
(Prompt 292 handoff §22 PRE-WRITE SOURCE AUDIT; see the Prompt 292 report for
the full audit trail). `canonicalize_document_url` IS imported from
tools/public_projection.py, which was confirmed import-safe (stdlib-only,
no network/file I/O at module scope).
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from datetime import date
from typing import Any

try:
    from tools.public_projection import canonicalize_document_url
except ImportError:
    from public_projection import canonicalize_document_url


# --------------------------------------------------------------------------- #
# Error contract (Prompt 292 handoff §8)
# --------------------------------------------------------------------------- #

class CanonicalTenderMergeError(ValueError):
    """Deterministic fail-closed error for merge_canonical_tenders().

    `code` is one of the handoff's minimum required set: invalid_record,
    invalid_id, unsupported_group_multiplicity, pair_orientation_invalid,
    identity_conflict, status_conflict, scalar_conflict, adjudicatari_conflict,
    duplicate_relations_unsupported, invalid_sequence_shape -- plus one
    addition beyond that minimum, `document_identity_conflict`, for the one
    failure shape (§16: incompatible duplicate document identity) that fits
    none of the ten precisely; documented in the Prompt 292 report's FAILURE
    MODES section as an explicit, justified addition ("at minimum distinguish"
    permits it).

    Never carries a wall-clock or random value (handoff §8)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------- #
# STATUS_RANK -- copied verbatim from fetch_licitaciones.py:474-486 (v0.4.5z)
# --------------------------------------------------------------------------- #

STATUS_RANK = {
    "FORMALIZATION": 10,
    "CONTRACT_MODIFICATION": 9,
    "AWARD": 8,
    "ADJ": 8,
    "RES": 7,
    "EV": 4,
    "PRE": 3,
    "PUB": 2,
    "PRIOR": 1,
    "CANCELLED": 0,
    "UNKNOWN": 0,
}

# Prompt 291 R2 / handoff §12: the one adjudicatari junk-placeholder value
# evidenced across all 6154 current records (4/6154 occurrences), stored
# HTML-entity-encoded exactly as shown -- not a decoded "o with acute accent".
ADJUDICATARI_SENTINEL = "Ver detalle de la adjudicaci&#243;n"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --------------------------------------------------------------------------- #
# Small shared predicates
# --------------------------------------------------------------------------- #

def _is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v == "":
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    return False


def _is_valid_date_str(v: Any) -> bool:
    """Strict repository date semantics: exactly YYYY-MM-DD, and a real
    calendar date (rejects e.g. 2026-02-30). No permissive parsing invented
    -- date.fromisoformat is stdlib's own ISO-8601 calendar validator, gated
    by an explicit regex so behaviour does not shift across Python versions
    that accept a wider ISO-8601 grammar in fromisoformat()."""
    if not isinstance(v, str) or not _DATE_RE.match(v):
        return False
    try:
        date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _effective_notice_date(row: dict):
    """Prompt 292 handoff §10: valid(last_notice_date) else valid(data_pub)
    else NONE."""
    v = row.get("last_notice_date")
    if _is_valid_date_str(v):
        return v
    v = row.get("data_pub")
    if _is_valid_date_str(v):
        return v
    return None


def _normalize_estat(v: Any) -> str:
    """Internal comparison-only normalization -- never stored/output."""
    if not isinstance(v, str):
        return ""
    return v.strip().casefold()


def _is_ck_row(row: dict) -> bool:
    return bool(row.get("canonical_key")) or bool(row.get("contract_folder_id"))


def _valid_rank(row: dict) -> bool:
    """D291-01: a row has VALID_RANK only if notice_type is present AND
    recognized. The literal value "UNKNOWN" is explicitly NOT recognized
    (handoff §10) -- it is the producer's own admission that no genuine
    notice classification was determined, not a classification itself.
    Absence of notice_type must never be silently demoted to rank 0."""
    nt = row.get("notice_type")
    if not isinstance(nt, str) or not nt or nt == "UNKNOWN":
        return False
    return nt in STATUS_RANK


def _rank_of(row: dict) -> int:
    return STATUS_RANK[row["notice_type"]]


# --------------------------------------------------------------------------- #
# Record / id validation (handoff §7, §8)
# --------------------------------------------------------------------------- #

def _validate_record(rec: Any) -> str:
    if not isinstance(rec, dict):
        raise CanonicalTenderMergeError("invalid_record", "record is not an object")
    rid = rec.get("id")
    if not isinstance(rid, str) or rid.strip() == "":
        raise CanonicalTenderMergeError("invalid_id", "record id is missing or blank")
    return rid


def _guard_duplicate_relations(row: dict, rid: str) -> None:
    """handoff §15: `duplicate_relations` has no evidenced identity law
    anywhere in source. A present-but-empty list (or an absent key) is not
    "encountered" -- nothing to reconcile, nothing to fail on. A populated
    list is "encountered" and must fail closed rather than be silently
    dropped or silently merged under an invented rule."""
    v = row.get("duplicate_relations")
    if v is None:
        return
    if not isinstance(v, list):
        raise CanonicalTenderMergeError(
            "duplicate_relations_unsupported",
            f"id {rid!r}: duplicate_relations present with non-list shape",
        )
    if len(v) > 0:
        raise CanonicalTenderMergeError(
            "duplicate_relations_unsupported",
            f"id {rid!r}: duplicate_relations populated, no identity law evidenced",
        )


# --------------------------------------------------------------------------- #
# IDENTITY_PROTECTED (handoff §9)
# --------------------------------------------------------------------------- #

def _preserve_identity_field(ck_val: Any, legacy_val: Any, field: str, rid: str):
    ck_truthy = bool(ck_val)
    legacy_truthy = bool(legacy_val)
    if ck_truthy and legacy_truthy and ck_val != legacy_val:
        raise CanonicalTenderMergeError(
            "identity_conflict", f"id {rid!r}: {field} differs between rows"
        )
    if ck_truthy:
        return ck_val
    if legacy_truthy:
        return legacy_val
    return ck_val


# --------------------------------------------------------------------------- #
# STATUS_AUTHORITY_V1 (handoff §10, D291-01) -- validated against all
# 2656 current same-id pairs in Prompt 291 R2 with zero fail-closed cases.
# --------------------------------------------------------------------------- #

def _select_status_authority(ck_row: dict, legacy_row: dict, rid: str) -> dict:
    vr_ck = _valid_rank(ck_row)
    vr_legacy = _valid_rank(legacy_row)
    ed_ck = _effective_notice_date(ck_row)
    ed_legacy = _effective_notice_date(legacy_row)
    statuses_equal = _normalize_estat(ck_row.get("estat")) == _normalize_estat(legacy_row.get("estat"))

    def later():
        if ed_ck is not None and ed_legacy is not None and ed_ck != ed_legacy:
            return ck_row if ed_ck > ed_legacy else legacy_row
        return None

    if vr_ck and vr_legacy:
        # A. BOTH VALID_RANK
        rank_ck, rank_legacy = _rank_of(ck_row), _rank_of(legacy_row)
        if rank_ck != rank_legacy:
            return ck_row if rank_ck > rank_legacy else legacy_row
        winner = later()
        if winner is not None:
            return winner
        if statuses_equal:
            return ck_row
        raise CanonicalTenderMergeError(
            "status_conflict", f"id {rid!r}: rank/date tie with differing estat"
        )

    if vr_ck != vr_legacy:
        # B. EXACTLY ONE VALID_RANK
        valid_row = ck_row if vr_ck else legacy_row
        winner = later()
        if winner is not None:
            return winner
        if statuses_equal:
            return valid_row
        raise CanonicalTenderMergeError(
            "status_conflict", f"id {rid!r}: no date authority and differing estat"
        )

    # C. NEITHER VALID_RANK
    winner = later()
    if winner is not None:
        return winner
    if statuses_equal:
        return ck_row
    raise CanonicalTenderMergeError(
        "status_conflict",
        f"id {rid!r}: neither row ranked, dates tie/missing, differing estat",
    )


# --------------------------------------------------------------------------- #
# RELLEVANCIA (handoff §11, D291-02)
# --------------------------------------------------------------------------- #

def _select_rellevancia(ck_row: dict, legacy_row: dict, rid: str):
    v_ck = ck_row.get("rellevancia")
    v_legacy = legacy_row.get("rellevancia")
    if v_ck == v_legacy:
        return v_ck
    ed_ck = _effective_notice_date(ck_row)
    ed_legacy = _effective_notice_date(legacy_row)
    if ed_ck is not None and ed_legacy is not None and ed_ck != ed_legacy:
        return v_ck if ed_ck > ed_legacy else v_legacy
    raise CanonicalTenderMergeError(
        "scalar_conflict",
        f"id {rid!r}: rellevancia differs and date authority cannot resolve uniquely",
    )


# --------------------------------------------------------------------------- #
# ADJUDICATARI (handoff §12, D291-03)
# --------------------------------------------------------------------------- #

def _sanitize_adjudicatari(v: Any) -> str:
    if not isinstance(v, str):
        return ""
    if v == ADJUDICATARI_SENTINEL:
        return ""
    return v


def _normalize_adjudicatari_variant(v: str) -> str:
    """Conservative normalization only (handoff §12): NFKC, casefold, drop
    periods, collapse whitespace. Deliberately does NOT strip other
    punctuation such as & / + -."""
    s = unicodedata.normalize("NFKC", v or "")
    s = s.casefold()
    s = s.replace(".", "")
    s = " ".join(s.split())
    return s


def _collect_award_winners(row: dict) -> set:
    out = set()
    results = row.get("award_results")
    if not isinstance(results, list):
        return out
    for item in results:
        if not isinstance(item, dict):
            continue
        name = item.get("winning_party_name")
        if isinstance(name, str) and name:
            out.add(_normalize_adjudicatari_variant(name))
    return out


def _select_adjudicatari(ck_row: dict, legacy_row: dict, rid: str) -> str:
    ck_val = _sanitize_adjudicatari(ck_row.get("adjudicatari"))
    legacy_val = _sanitize_adjudicatari(legacy_row.get("adjudicatari"))
    if ck_val and legacy_val:
        if ck_val == legacy_val:
            return ck_val
        norm_ck = _normalize_adjudicatari_variant(ck_val)
        norm_legacy = _normalize_adjudicatari_variant(legacy_val)
        if norm_ck == norm_legacy:
            winners = _collect_award_winners(ck_row) | _collect_award_winners(legacy_row)
            if norm_ck in winners:
                return ck_val
        raise CanonicalTenderMergeError(
            "adjudicatari_conflict",
            f"id {rid!r}: both rows populated and differ, "
            "no award-corroborated normalization variant",
        )
    return ck_val or legacy_val


# --------------------------------------------------------------------------- #
# Zero-conflict equality invariants (handoff §13, D291-06)
# --------------------------------------------------------------------------- #

def _select_equality_invariant(field: str, ck_row: dict, legacy_row: dict, rid: str):
    ck_val = ck_row.get(field) or ""
    legacy_val = legacy_row.get(field) or ""
    if ck_val and legacy_val and ck_val != legacy_val:
        raise CanonicalTenderMergeError(
            "scalar_conflict", f"id {rid!r}: {field} differs between rows"
        )
    return ck_val or legacy_val


# --------------------------------------------------------------------------- #
# Other canonical scalars (handoff §14)
# --------------------------------------------------------------------------- #

def _non_empty_prefer_ck(ck_val: Any, legacy_val: Any):
    if not _is_empty_value(ck_val):
        return ck_val
    if not _is_empty_value(legacy_val):
        return legacy_val
    return ck_val


def _select_no_fallback_conflict(field: str, ck_val: Any, legacy_val: Any, rid: str):
    """pressupost / tipus: NON_EMPTY_PREFER_CK, but an unexpected differing
    non-empty pair (no source-evidenced law for that case) fails closed
    rather than silently discarding LEGACY's value."""
    ck_empty = _is_empty_value(ck_val)
    legacy_empty = _is_empty_value(legacy_val)
    if not ck_empty and not legacy_empty and ck_val != legacy_val:
        raise CanonicalTenderMergeError(
            "scalar_conflict",
            f"id {rid!r}: {field} differs between rows with no source-evidenced law",
        )
    if not ck_empty:
        return ck_val
    return legacy_val


def _min_date(ck_row: dict, legacy_row: dict, field: str):
    a, b = ck_row.get(field), legacy_row.get(field)
    va, vb = _is_valid_date_str(a), _is_valid_date_str(b)
    if va and vb:
        return a if a <= b else b
    if va:
        return a
    if vb:
        return b
    return ck_row.get(field)


def _max_date(ck_row: dict, legacy_row: dict, field: str):
    a, b = ck_row.get(field), legacy_row.get(field)
    va, vb = _is_valid_date_str(a), _is_valid_date_str(b)
    if va and vb:
        return a if a >= b else b
    if va:
        return a
    if vb:
        return b
    return ck_row.get(field)


def _cpv_tokens(v: Any) -> list:
    if not v or not isinstance(v, str):
        return []
    return [t.strip() for t in v.split(",") if t.strip()]


def _select_cpv(ck_val: Any, legacy_val: Any) -> str:
    tokens = set(_cpv_tokens(ck_val)) | set(_cpv_tokens(legacy_val))
    return ",".join(sorted(tokens))


# --------------------------------------------------------------------------- #
# LOSSLESS_SEQUENCE dedupe/order keys (handoff §15) -- keys lifted from
# Prompt 291 R1 evidence (fetch_licitaciones.py::merge_master_v2), orders
# authorized by Companion/Operator decision D291-05.
# --------------------------------------------------------------------------- #

def _historial_key(e: dict):
    return (e.get("data") or "", e.get("estat") or "", e.get("nota") or "")


_historial_sort_key = _historial_key


def _notice_history_key(e: dict):
    return (e.get("notice_id") or "", e.get("notice_type") or "", e.get("issue_date") or "")


def _notice_history_sort_key(e: dict):
    return (e.get("issue_date") or "", e.get("notice_type") or "", e.get("notice_id") or "")


def _award_amount_str(e: dict) -> str:
    v = e.get("award_amount_tax_excl")
    return str(v) if v is not None else ""


def _award_key(e: dict):
    return (
        e.get("notice_id") or "",
        e.get("winning_party_name") or "",
        e.get("winning_party_nif") or "",
        _award_amount_str(e),
        e.get("contract_id") or "",
        e.get("lot_id") or "",
    )


def _award_sort_key(e: dict):
    return (
        e.get("award_date") or "",
        e.get("notice_id") or "",
        e.get("contract_id") or "",
        e.get("lot_id") or "",
        e.get("winning_party_name") or "",
        e.get("winning_party_nif") or "",
        _award_amount_str(e),
    )


def _get_validated_object_list(row: dict, field: str, rid: str):
    v = row.get(field)
    if v is None:
        return None
    if not isinstance(v, list):
        raise CanonicalTenderMergeError(
            "invalid_sequence_shape", f"id {rid!r}: {field} is not a list"
        )
    for item in v:
        if not isinstance(item, dict):
            raise CanonicalTenderMergeError(
                "invalid_sequence_shape", f"id {rid!r}: {field} entry is not an object"
            )
    return v


def _union_sorted_objects(list_a, list_b, key_fn, sort_key_fn) -> list:
    seen = set()
    result = []
    for item in (list_a or []) + (list_b or []):
        k = key_fn(item)
        if k in seen:
            continue
        seen.add(k)
        result.append(copy.deepcopy(item))
    result.sort(key=sort_key_fn)
    return result


def _merge_object_sequence(ck_row, legacy_row, field, key_fn, sort_key_fn, rid):
    ck_list = _get_validated_object_list(ck_row, field, rid)
    legacy_list = _get_validated_object_list(legacy_row, field, rid)
    if ck_list is None and legacy_list is None:
        return None
    return _union_sorted_objects(ck_list, legacy_list, key_fn, sort_key_fn)


def _get_validated_string_list(row: dict, field: str, rid: str):
    v = row.get(field)
    if v is None:
        return None
    if not isinstance(v, list):
        raise CanonicalTenderMergeError(
            "invalid_sequence_shape", f"id {rid!r}: {field} is not a list"
        )
    for item in v:
        if not isinstance(item, str):
            raise CanonicalTenderMergeError(
                "invalid_sequence_shape", f"id {rid!r}: {field} entry is not a string"
            )
    return v


def _merge_string_sequence(ck_row, legacy_row, field, rid):
    ck_list = _get_validated_string_list(ck_row, field, rid)
    legacy_list = _get_validated_string_list(legacy_row, field, rid)
    if ck_list is None and legacy_list is None:
        return None
    return sorted(set((ck_list or []) + (legacy_list or [])))


# --------------------------------------------------------------------------- #
# DOCUMENTS -- raw identity aligned to canonicalize_document_url (handoff
# §16, D291-04, Prompt 291 R1/R2 RAW_DOC_KEY_REQUIRES_ALIGNMENT), superseded
# for URL-less entries only by D292-R3-DOCIDENTITY-FALLBACK-V1 (Prompt 292
# R3 real-data correction: notice_id is not a sufficient document-level
# identity anchor for URL-less entries in current data -- see
# _has_url_identity/_content_signature/_doc_identity_key below), and further
# refined for URL-bearing entries only by D292-R4-DOCUMENT-OBSERVATION-
# IDENTITY-V1 (Prompt 292 R4 real-data correction: a global strong-URL
# forensic census found 74 same-resource groups differing ONLY in
# notice_type -- e.g. the same document URL observed once under an EV notice
# and once under an AWARD notice -- proving the four-field RESOURCE_KEY
# below is a valid document-RESOURCE identity but is too coarse as a
# lossless documents[] OBSERVATION dedupe key, since notice_type is a
# preserved source fact that can legitimately vary for one resource. See
# _url_doc_key (RESOURCE_KEY, unchanged by R4) vs _doc_identity_key's
# OBSERVATION_KEY (RESOURCE_KEY + exact notice_type, R4) below).
# --------------------------------------------------------------------------- #

def _get_validated_doc_list(row: dict, field: str, rid: str):
    return _get_validated_object_list(row, field, rid)


def _has_url_identity(item: dict) -> bool:
    """D292-R3-DOCIDENTITY-FALLBACK-V1 branch selector (R3 Sec2): True iff
    the document carries a usable URL locator -- canonicalized, or raw if
    canonicalization does not apply/succeed. Same non-emptiness test the
    pre-R3 strong identity law already used for its own fallback, now made
    explicit as the URL-bearing/URL-less branch condition."""
    raw_url = item.get("url") or ""
    canon = canonicalize_document_url(raw_url)
    return bool(canon or raw_url)


def _url_doc_key(item: dict):
    """Strong document RESOURCE_KEY for URL-bearing entries (handoff Sec16,
    D291-04) -- unchanged by D292-R3-DOCIDENTITY-FALLBACK-V1 (which
    supersedes D291-04 ONLY for URL-less entries, R3 Sec2.A) and unchanged
    by D292-R4-DOCUMENT-OBSERVATION-IDENTITY-V1 (R4 Sec3.A: "RESOURCE_KEY --
    UNCHANGED"), which layers notice_type on top of this key only at the
    OBSERVATION level -- see _doc_identity_key."""
    title = item.get("title") or ""
    raw_url = item.get("url") or ""
    canon = canonicalize_document_url(raw_url)  # never raises, per its own contract
    identity_url = canon if canon else raw_url
    return (title, identity_url, item.get("document_type") or "", item.get("notice_id") or "")


def _content_signature(item: dict) -> str:
    """D292-R3-DOCIDENTITY-FALLBACK-V1 URL-less fallback identity (R3
    Sec2.B): a deterministic canonical content signature of the full
    document object. Two URL-less entries dedupe only when every field is
    exactly equal by value -- with no URL locator, nothing proves two
    variants describe the same document, so identity must never collapse
    anything less than byte-for-byte content equality (e.g. differing
    `published_at`, `notice_type`, or `source_section` alone must keep
    entries distinct). `sort_keys=True` makes the signature independent of
    the object's own key insertion order -- not input row/array position,
    wall-clock, random, or Python object-id (R3 Sec2.C). `default=str` is a
    safety net only: every document object here originates from JSON-sourced
    data, so it is never expected to fire."""
    return json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)


def _doc_identity_key(item: dict):
    """Unified dedupe/order key implementing D292-R3-DOCIDENTITY-FALLBACK-V1
    and D292-R4-DOCUMENT-OBSERVATION-IDENTITY-V1:

    - URL-bearing entries: tagged `"url"`, keyed on OBSERVATION_KEY =
      RESOURCE_KEY (`_url_doc_key`, D291-04, unchanged) + the exact
      `notice_type` value (R4 Sec3.B). Two entries sharing one resource but
      carrying different `notice_type` values therefore land in different
      groups -- each preserved as its own documents[] entry -- while entries
      sharing both the resource AND `notice_type` still dedupe/reduce exactly
      as before (R4 Sec3.B "same resource + same notice_type" branch).
      `notice_type` is compared by exact value only (`or ""` matches this
      module's existing None/absent<->empty-string equivalence convention
      used throughout for every other document field, e.g. `document_type`
      above) -- never ranked, never chosen, never dropped.
    - URL-less entries: tagged `"content"`, keyed on the exact-content
      signature (`_content_signature`, R3 Sec2.B, unaffected by R4 -- R4 is
      explicitly scoped to URL-bearing entries only, handoff Sec3.C/R4
      Sec1 "R3 URL-less correction itself is ... not reopened by this
      pass").

    The leading tag keeps every key's first element type-uniform for
    grouping/`sort()`, and Python tuple comparison short-circuits on that
    first (differing) element whenever a `"url"`-tagged key is compared
    against a `"content"`-tagged one, so the two differently-shaped tuples
    are never compared element-by-element beyond it. Including notice_type
    in the sort key also gives multiple same-resource observations a
    deterministic relative order (content-derived, never array position/
    wall-clock/random/object-id), per R4 Sec3.D."""
    if _has_url_identity(item):
        return ("url",) + _url_doc_key(item) + (item.get("notice_type") or "",)
    return ("content", _content_signature(item))


def _urls_equivalent(a: Any, b: Any) -> bool:
    """Two raw url strings are equivalent if byte-identical, or if they
    canonicalize to the same target (canonicalize_document_url never
    raises). Needed because two documents sharing one `_url_doc_key`
    (identity is keyed on the CANONICALIZED url, D291-04) can still carry
    different raw `url` strings -- e.g. differing only by host case or an
    explicit default port -- and that difference must not be mistaken for a
    genuine information conflict when picking the richer duplicate below."""
    if a == b:
        return True
    ca = canonicalize_document_url(a) if isinstance(a, str) else None
    cb = canonicalize_document_url(b) if isinstance(b, str) else None
    return ca is not None and ca == cb


def _is_information_subset(a: dict, b: dict) -> bool:
    """True if every non-empty field of `a` matches the same field in `b`
    -- i.e. `a`'s information content is entirely contained in `b`. The
    `url` field is compared via canonical-URL equivalence, not raw string
    equality (see _urls_equivalent)."""
    for k, v in a.items():
        if v in (None, "", [], {}):
            continue
        if k == "url":
            if not _urls_equivalent(v, b.get("url")):
                return False
            continue
        if b.get(k) != v:
            return False
    return True


def _reduce_document_group(group: list, rid: str, key) -> dict:
    best = group[0]
    for cand in group[1:]:
        if cand == best:
            continue
        cand_subset = _is_information_subset(cand, best)
        best_subset = _is_information_subset(best, cand)
        if cand_subset and not best_subset:
            continue
        if best_subset and not cand_subset:
            best = cand
            continue
        if cand_subset and best_subset:
            continue
        raise CanonicalTenderMergeError(
            "document_identity_conflict",
            f"id {rid!r}: duplicate document identity {key!r} has incompatible variants",
        )
    return best


def _dedupe_documents(items: list, rid: str) -> list:
    groups: dict = {}
    order = []
    for item in items:
        k = _doc_identity_key(item)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(item)
    result = []
    for k in order:
        group = groups[k]
        if k[0] == "url":
            chosen = group[0] if len(group) == 1 else _reduce_document_group(group, rid, k)
        else:
            # D292-R3-DOCIDENTITY-FALLBACK-V1 (R3 Sec2.B): the group key IS
            # exact full-object content, so every member is already equal by
            # value -- no richer-subset merge is attempted or needed here.
            chosen = group[0]
        result.append(copy.deepcopy(chosen))
    result.sort(key=_doc_identity_key)
    return result


def _merge_documents(ck_row: dict, legacy_row: dict, rid: str):
    ck_list = _get_validated_doc_list(ck_row, "documents", rid)
    legacy_list = _get_validated_doc_list(legacy_row, "documents", rid)
    if ck_list is None and legacy_list is None:
        return None
    combined = list(ck_list or []) + list(legacy_list or [])
    return _dedupe_documents(combined, rid)


# --------------------------------------------------------------------------- #
# SINGLETON canonicalization (handoff §7)
# --------------------------------------------------------------------------- #

_EMPTY_ROW: dict = {}


def _canonicalize_singleton(row: dict) -> dict:
    rid = row.get("id")
    _guard_duplicate_relations(row, rid)

    out = copy.deepcopy(row)
    out["adjudicatari"] = _sanitize_adjudicatari(row.get("adjudicatari"))
    out["cpv"] = _select_cpv(row.get("cpv"), None)

    for field, key_fn, sort_key_fn in (
        ("historial", _historial_key, _historial_sort_key),
        ("notice_history", _notice_history_key, _notice_history_sort_key),
        ("award_results", _award_key, _award_sort_key),
    ):
        merged = _merge_object_sequence(row, _EMPTY_ROW, field, key_fn, sort_key_fn, rid)
        if merged is not None:
            out[field] = merged

    for field in ("related_contract_ids", "sources_seen"):
        merged = _merge_string_sequence(row, _EMPTY_ROW, field, rid)
        if merged is not None:
            out[field] = merged

    docs = _merge_documents(row, _EMPTY_ROW, rid)
    if docs is not None:
        out["documents"] = docs

    return out


# --------------------------------------------------------------------------- #
# PAIR canonicalization (handoff §7, §9-§16)
# --------------------------------------------------------------------------- #

def _merge_pair(row_x: dict, row_y: dict, rid: str) -> dict:
    x_is_ck = _is_ck_row(row_x)
    y_is_ck = _is_ck_row(row_y)
    if x_is_ck and not y_is_ck:
        ck_row, legacy_row = row_x, row_y
    elif y_is_ck and not x_is_ck:
        ck_row, legacy_row = row_y, row_x
    else:
        raise CanonicalTenderMergeError(
            "pair_orientation_invalid",
            f"id {rid!r}: pair does not have exactly one CK_ROW and one LEGACY_ROW",
        )

    _guard_duplicate_relations(ck_row, rid)
    _guard_duplicate_relations(legacy_row, rid)

    # §17: start from a deep copy of CK_ROW; internal/non-public fields may
    # remain from that base untouched; do not strip anything here.
    out = copy.deepcopy(ck_row)

    out["id"] = ck_row["id"]
    out["canonical_key"] = _preserve_identity_field(
        ck_row.get("canonical_key"), legacy_row.get("canonical_key"), "canonical_key", rid
    )
    out["contract_folder_id"] = _preserve_identity_field(
        ck_row.get("contract_folder_id"), legacy_row.get("contract_folder_id"),
        "contract_folder_id", rid,
    )

    status_row = _select_status_authority(ck_row, legacy_row, rid)
    out["estat"] = status_row.get("estat")
    out["estat_raw"] = status_row.get("estat_raw")  # D: same row as estat, never independent

    out["rellevancia"] = _select_rellevancia(ck_row, legacy_row, rid)
    out["adjudicatari"] = _select_adjudicatari(ck_row, legacy_row, rid)

    for field in ("ccaa", "lloc", "titol"):
        out[field] = _select_equality_invariant(field, ck_row, legacy_row, rid)

    for field in ("data_pub", "data_limit", "organisme", "url", "font"):
        out[field] = _non_empty_prefer_ck(ck_row.get(field), legacy_row.get(field))

    for field in ("disciplines", "kw"):
        out[field] = copy.deepcopy(_non_empty_prefer_ck(ck_row.get(field), legacy_row.get(field)))

    out["pressupost"] = _select_no_fallback_conflict(
        "pressupost", ck_row.get("pressupost"), legacy_row.get("pressupost"), rid
    )
    out["tipus"] = _select_no_fallback_conflict(
        "tipus", ck_row.get("tipus"), legacy_row.get("tipus"), rid
    )

    out["first_pub_date"] = _min_date(ck_row, legacy_row, "first_pub_date")
    out["last_notice_date"] = _max_date(ck_row, legacy_row, "last_notice_date")

    out["cpv"] = _select_cpv(ck_row.get("cpv"), legacy_row.get("cpv"))

    for field, key_fn, sort_key_fn in (
        ("historial", _historial_key, _historial_sort_key),
        ("notice_history", _notice_history_key, _notice_history_sort_key),
        ("award_results", _award_key, _award_sort_key),
    ):
        merged = _merge_object_sequence(ck_row, legacy_row, field, key_fn, sort_key_fn, rid)
        if merged is not None:
            out[field] = merged

    for field in ("related_contract_ids", "sources_seen"):
        merged = _merge_string_sequence(ck_row, legacy_row, field, rid)
        if merged is not None:
            out[field] = merged

    docs = _merge_documents(ck_row, legacy_row, rid)
    if docs is not None:
        out["documents"] = docs

    return out


# --------------------------------------------------------------------------- #
# Public API (handoff §6)
# --------------------------------------------------------------------------- #

def merge_canonical_tenders(records: list) -> list:
    """Transforms a raw-record list into a deterministic canonical-tender
    list, one row per logical `id` (handoff §6-§7).

    - `records` and every record dict in it are never mutated.
    - Retained nested structures are deep-copied, never aliased.
    - Output is deterministic and independent of input row order.
    - Output rows are sorted lexically ascending by validated `id`
      (Companion/Operator decision, handoff §6).
    - Repeated canonicalization of already-canonical output is idempotent.

    Raises CanonicalTenderMergeError (see its docstring for the `code`
    surface) on any unsupported or ambiguous input; never resolves an
    ambiguity by invented default.
    """
    if not isinstance(records, list):
        raise CanonicalTenderMergeError("invalid_record", "input is not a list")

    groups: dict = {}
    order: list = []
    for rec in records:
        rid = _validate_record(rec)
        if rid not in groups:
            groups[rid] = []
            order.append(rid)
        groups[rid].append(rec)

    output = []
    for rid in order:
        rows = groups[rid]
        if len(rows) == 1:
            output.append(_canonicalize_singleton(rows[0]))
        elif len(rows) == 2:
            output.append(_merge_pair(rows[0], rows[1], rid))
        else:
            raise CanonicalTenderMergeError(
                "unsupported_group_multiplicity",
                f"id {rid!r} has {len(rows)} rows; only 1 or 2 are currently supported",
            )

    output.sort(key=lambda r: r["id"])
    return output
