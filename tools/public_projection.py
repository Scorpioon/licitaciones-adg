#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/public_projection.py  (ADG OPS / p285 / v0.7.4i)

PublicProjection — IB-3 doc_ref minting and DocIntel construct-only projector,
corrected to consume the real producer input plus a read-only production
monolith join (WRKOPS t_20260905_adgops282, corrective continuation of
t_20260905_adgops281), with the normative per-record 64 KiB DocIntel cap
restored and the generated_at_utc -> analysed_at mapping's source semantics
recorded (WRKOPS t_20260905_adgops283, IB-3 normative correction), the
per-record cap corrected to arithmetic over the EFFECTIVE FINAL production
record -- pre-existing doc_intel on documents this run does not touch now
participates in the cap sum, and a cap rejection clears doc_intel on every
document of the record, not only the newly-added one (WRKOPS
t_20260906_adgops284, IB-3 effective-final-record cap correction) -- and the
cap check moved into one common per-record finalization step applied to
EVERY exit path once a production record is matched, not only the
success-path attach, so a record already over cap from pre-existing
doc_intel alone still fail-closes even when this run adds no valid CPV
(WRKOPS t_20260906_adgops285, IB-3 all-exit-path record cap correction).

Scope:
  - mint_doc_ref(): unchanged from p281 — derives a stable public document
    identity from a `url` string, per the frozen doc_ref conformance
    authority (tools/fixtures/doc_ref_conformance_v1.json).
  - build_doc_intel() / validate_doc_intel(): unchanged construct-only
    DocIntel kernel (p281 §7-§9). CPV-only for this lane.
  - project_manifest(): CORRECTED entry point. Consumes the actual
    appendix_pcap_ppt/1 manifest produced by
    tools/pcap_ppt_appendix_extractor.py, joined read-only against a
    production-monolith object shaped like fetch_licitaciones.py's output
    envelope (fetch_licitaciones.py:1880-1913).

Producer acceptance for this lane is exactly one schema string:
`appendix_pcap_ppt/1` (tools/pcap_ppt_appendix_extractor.py:49). `appendix/1`
is a known, explicitly unsupported producer schema and is rejected, never
merged or reconciled with the accepted schema. `docread/1` is named as a
future schema by p273 v0.3 §13 and is not implemented here; an
unknown/unsupported schema (including `appendix/1` and `docread/1`) rejects
the whole producer envelope.

Real producer record shape consumed by this lane
(tools/pcap_ppt_appendix_extractor.py:519-535, 736-750):

  producer_manifest = {
      "schema": "appendix_pcap_ppt/1",
      "production_write_performed": False,
      "generated_at_utc": <str>,             # this run's own timestamp; used
                                              # as the DocIntel analysed_at
      "records": [
          {
              "canonical_key": <str>,        # copied verbatim from the
                                              # production record this run
                                              # analysed — see
                                              # tools/document_source_targeting.py:246
              "fields": {
                  "cpv": {
                      "value": <str>,        # single raw candidate code
                                              # (tools/pcap_ppt_appendix_extractor.py:494-512)
                      "evidence": [{
                          "source_url": <str>,  # == the production
                                                 # documents[].url this field
                                                 # was found on
                          "page": <int>,
                          ...                    # excerpt/heading/sha256/etc.
                                                  # ignored — never emitted
                      }],
                  },
                  ...  # every other field key is ignored: this lane is
                       # CPV-only (§3 normative adjudication, unchanged)
              },
          },
          ...
      ],
  }

Read-only production monolith object consumed for inventory joining only
(never mutated, never written; shape per fetch_licitaciones.py:1880-1913 and
the per-document catalogue built by extract_document_catalogue_xml,
fetch_licitaciones.py:673-719):

  production_monolith = {
      "data": [
          {
              "canonical_key": <str>,
              "documents": [ {"url": <str>, ...}, ... ],
              ...  # every other production key ignored
          },
          ...
      ],
  }

Join rule (WRKOPS t_20260905_adgops282 §4, established from source, never
invented):
  1. record:   producer_record["canonical_key"] must equal exactly one
               production record's canonical_key.
  2. document: the cpv field's evidence["source_url"] (stripped) must equal,
               by exact string match, exactly one documents[].url (stripped)
               within that SAME production record — never a
               canonicalized/normalized match. canonicalize_document_url()
               is reserved for doc_ref minting only (p281 §6); this repo's
               own document-matching code compares raw stored URLs (see
               tools/document_source_targeting.py:353,421,461).
A producer record with zero or more than one matching production record, or
a cpv field whose evidence resolves to zero, more than one, or a different
record's documents[] entry, is rejected fail-closed: the field is dropped
but the matched production record's document inventory (and doc_ref) is
preserved unchanged.

No producer/internal identifier (canonical_key, source_url, final_url,
doc_sha256, notice_id, excerpt, heading) is ever emitted into public
DocIntel; only `doc_ref` (minted from the production document's own `url`)
and the closed CPV code/evidence-page pair cross into the public shape.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

# Import discipline mirrors tools/build_data_shards.py and
# tools/scheduled_fetch_merge.py: works both when run directly
# (`python tools/public_projection.py` -> tools/ on sys.path) and when
# imported as `tools.public_projection` with the repo root on sys.path.
try:
    from tools import public_contract as pc
except ImportError:
    import public_contract as pc

is_rfc3339_z = pc.is_rfc3339_z
to_rfc3339_z = pc.to_rfc3339_z

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

ACCEPTED_PRODUCER_SCHEMA = "appendix_pcap_ppt/1"
UNSUPPORTED_PRODUCER_SCHEMAS = frozenset({"appendix/1"})

DOC_INTEL_SCHEMA = "adgops.public.docintel/1"

DOC_REF_PREFIX = "d-"
DOC_REF_HEX_LEN = 32

VALID_STATES = frozenset({"link_checked", "analysed", "unavailable", "stale"})
VALID_REASONS = frozenset({"source_unreachable", "source_not_readable"})
VALID_FIELD_TYPES = frozenset({"money", "count", "boolean", "duration", "code_list"})

CPV_CODE_RE = re.compile(r"^[0-9]{8}(-[0-9])?$")

MAX_FIELDS = 30
MIN_EVIDENCE = 1
MAX_EVIDENCE = 3
MAX_STRING_LEN = 64
MAX_DOCINTEL_BYTES = 8 * 1024
# p273 v0.3 §13: a rejection threshold over the EFFECTIVE FINAL per-record
# DocIntel payload (every document's doc_intel in the record, summed) — not
# merely the newly-added field — so the cap holds even once a record can
# carry doc_intel on more than one of its documents at once.
MAX_RECORD_DOCINTEL_BYTES = 64 * 1024

DOC_INTEL_TOP_KEYS = ("schema", "state", "reason", "analysed_at", "link_checked_at", "fields")
FIELD_KEYS = ("key", "type", "value", "evidence")
EVIDENCE_KEYS = ("doc_ref", "page")


class RejectedCandidate(Exception):
    """Raised for any malformed/non-conformant candidate. Carries a stable,
    non-sensitive reason code only — never a raw producer value (A1 §14
    discipline, reused here for the same reporting reason)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- #
# doc_ref minting (WRKOPS 281 §6)
# --------------------------------------------------------------------------- #

_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):(.*)$", re.DOTALL)
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _split_authority(rest_after_scheme: str):
    """rest_after_scheme is everything after 'scheme:'. Returns
    (authority, remainder) if it is an absolute authority-form URL
    ('//authority[/path][?query][#fragment]'), else None."""
    if not rest_after_scheme.startswith("//"):
        return None
    body = rest_after_scheme[2:]
    end = len(body)
    for i, ch in enumerate(body):
        if ch in "/?#":
            end = i
            break
    authority = body[:end]
    remainder = body[end:]
    if not authority:
        return None
    return authority, remainder


def _split_host_port(authority: str):
    """Returns (host, port_str_or_None), or None if the authority form is
    outside the supported (no-userinfo, non-bracketed) host set."""
    if "@" in authority or authority.startswith("["):
        return None
    if ":" in authority:
        host, _, port_str = authority.partition(":")
    else:
        host, port_str = authority, None
    if not host:
        return None
    if port_str is not None:
        if not port_str.isdigit():
            return None
    return host, port_str


def _idna_lower_host(host: str):
    try:
        encoded = host.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        return None
    return encoded.lower()


def _split_path_query_fragment(remainder: str):
    """Splits remainder into (path, query_or_None, fragment_or_None), where
    None means the '?' / '#' separator was not present at all (as opposed to
    an empty string, which means the separator WAS present with nothing
    after it — this distinction is required to preserve an empty query /
    empty fragment marker, WRKOPS 281 §6)."""
    frag_idx = remainder.find("#")
    if frag_idx != -1:
        before_frag = remainder[:frag_idx]
        fragment = remainder[frag_idx + 1:]
    else:
        before_frag = remainder
        fragment = None

    q_idx = before_frag.find("?")
    if q_idx != -1:
        path = before_frag[:q_idx]
        query = before_frag[q_idx + 1:]
    else:
        path = before_frag
        query = None

    return path, query, fragment


def canonicalize_document_url(raw_url: Any):
    """Returns the canonical URL string, or None if `raw_url` mints nothing
    (WRKOPS 281 §6). Never raises."""
    if not isinstance(raw_url, str):
        return None
    trimmed = raw_url.strip()
    if not trimmed:
        return None

    m = _SCHEME_RE.match(trimmed)
    if not m:
        return None
    scheme = m.group(1).lower()
    if scheme not in _DEFAULT_PORTS:
        return None

    split = _split_authority(m.group(2))
    if split is None:
        return None
    authority, remainder = split

    hp = _split_host_port(authority)
    if hp is None:
        return None
    host, port_str = hp

    host_final = _idna_lower_host(host)
    if not host_final:
        return None

    default_port = _DEFAULT_PORTS[scheme]
    if port_str is not None:
        port = int(port_str)
        port_out = "" if port == default_port else (":" + str(port))
    else:
        port_out = ""

    path, query, fragment = _split_path_query_fragment(remainder)

    canonical = scheme + "://" + host_final + port_out + path
    if query is not None:
        canonical += "?" + query
    if fragment is not None:
        canonical += "#" + fragment
    return canonical


def mint_doc_ref(raw_url: Any):
    """Mints the public doc_ref for a producer document's `url`, or returns
    None for a negative vector (WRKOPS 281 §6). Identity is derived ONLY from
    `raw_url`; nothing else is ever consulted."""
    canonical = canonicalize_document_url(raw_url)
    if canonical is None:
        return None
    import hashlib
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return DOC_REF_PREFIX + digest[:DOC_REF_HEX_LEN]


# --------------------------------------------------------------------------- #
# DocIntel structural validation (WRKOPS 281 §7-§9)
#
# Pure, construct-only validator: accepts an already-shaped dict and enforces
# every DocIntel invariant. Used both as the last step of build_doc_intel()
# and directly against hand-built (possibly malformed) dicts, so malformed-
# input handling can be exercised without going through the candidate
# builder.
# --------------------------------------------------------------------------- #

def _check_string_caps(node):
    """Recursively rejects any string leaf longer than MAX_STRING_LEN
    (WRKOPS 281 §9). Caps reject, never truncate."""
    if isinstance(node, str):
        if len(node) > MAX_STRING_LEN:
            raise RejectedCandidate("string_cap_exceeded")
    elif isinstance(node, dict):
        for v in node.values():
            _check_string_caps(v)
    elif isinstance(node, list):
        for v in node:
            _check_string_caps(v)


def _validate_evidence(evidence, doc_ref):
    if not isinstance(evidence, list):
        raise RejectedCandidate("evidence_not_list")
    if not (MIN_EVIDENCE <= len(evidence) <= MAX_EVIDENCE):
        raise RejectedCandidate("evidence_count_out_of_range")
    prev_page = -1
    for item in evidence:
        if not isinstance(item, dict):
            raise RejectedCandidate("evidence_malformed")
        if set(item.keys()) != set(EVIDENCE_KEYS):
            raise RejectedCandidate("evidence_unknown_keys")
        item_doc_ref = item.get("doc_ref")
        page = item.get("page")
        if not isinstance(item_doc_ref, str) or item_doc_ref != doc_ref:
            raise RejectedCandidate("evidence_wrong_owning_document")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise RejectedCandidate("evidence_invalid_page")
        if page <= prev_page:
            raise RejectedCandidate("evidence_page_order")
        prev_page = page


def _validate_fields(fields, doc_ref):
    if not isinstance(fields, list):
        raise RejectedCandidate("fields_not_list")
    if not (1 <= len(fields) <= MAX_FIELDS):
        raise RejectedCandidate("fields_count_out_of_range")
    for field in fields:
        if not isinstance(field, dict) or set(field.keys()) != set(FIELD_KEYS):
            raise RejectedCandidate("field_unknown_keys")
        key = field.get("key")
        ftype = field.get("type")
        value = field.get("value")
        evidence = field.get("evidence")
        if ftype not in VALID_FIELD_TYPES:
            raise RejectedCandidate("field_invalid_type")
        # This lane emits CPV only.
        if key != "cpv" or ftype != "code_list":
            raise RejectedCandidate("field_not_cpv_only")
        if not isinstance(value, list) or not value:
            raise RejectedCandidate("field_value_invalid")
        for code in value:
            if not isinstance(code, str) or not CPV_CODE_RE.match(code):
                raise RejectedCandidate("field_value_invalid_cpv_code")
        _validate_evidence(evidence, doc_ref)


def validate_doc_intel(doc_intel: Any, doc_ref: str) -> None:
    """Enforces the full DocIntel contract on an already-shaped dict
    (WRKOPS 281 §7-§9). Raises RejectedCandidate on any violation."""
    if not isinstance(doc_intel, dict):
        raise RejectedCandidate("not_an_object")

    unknown = set(doc_intel.keys()) - set(DOC_INTEL_TOP_KEYS)
    if unknown:
        raise RejectedCandidate("unknown_top_level_keys")

    if doc_intel.get("schema") != DOC_INTEL_SCHEMA:
        raise RejectedCandidate("invalid_schema")

    state = doc_intel.get("state")
    if state not in VALID_STATES:
        raise RejectedCandidate("invalid_state")

    has_reason = "reason" in doc_intel
    has_analysed_at = "analysed_at" in doc_intel
    has_link_checked_at = "link_checked_at" in doc_intel
    has_fields = "fields" in doc_intel

    if state == "unavailable":
        if not has_reason or doc_intel.get("reason") not in VALID_REASONS:
            raise RejectedCandidate("reason_required_for_unavailable")
    elif has_reason:
        raise RejectedCandidate("reason_outside_unavailable")

    if state in ("analysed", "stale"):
        if not has_analysed_at or not is_rfc3339_z(doc_intel.get("analysed_at")):
            raise RejectedCandidate("analysed_at_required")
    elif has_analysed_at:
        raise RejectedCandidate("analysed_at_outside_allowed_states")

    if state == "link_checked":
        if not has_link_checked_at or not is_rfc3339_z(doc_intel.get("link_checked_at")):
            raise RejectedCandidate("undated_link_checked")
    elif has_link_checked_at:
        raise RejectedCandidate("link_checked_at_outside_allowed_state")

    if state == "stale" and has_fields:
        raise RejectedCandidate("stale_carries_fields")

    if has_fields:
        if state != "analysed":
            raise RejectedCandidate("fields_outside_analysed")
        _validate_fields(doc_intel.get("fields"), doc_ref)

    _check_string_caps(doc_intel)

    serialized = json.dumps(doc_intel, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    if len(serialized.encode("utf-8")) > MAX_DOCINTEL_BYTES:
        raise RejectedCandidate("docintel_size_cap_exceeded")


def compute_record_docintel_bytes(documents: list) -> int:
    """Sums the serialized-UTF-8 byte size of every present `doc_intel`
    object across all documents belonging to one record (p273 v0.3 §13
    per-record cap; WRKOPS t_20260905_adgops283 §2.1). Uses the identical
    canonical serialization discipline as the per-document cap in
    `validate_doc_intel` (json.dumps, ensure_ascii=False, compact separators,
    no key sort), so this is the effective final per-record payload — every
    document's doc_intel counted, not only a newly-added one."""
    total = 0
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        di = doc.get("doc_intel")
        if di is None:
            continue
        serialized = json.dumps(di, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        total += len(serialized.encode("utf-8"))
    return total


# --------------------------------------------------------------------------- #
# DocIntel construction (construct-only builder)
# --------------------------------------------------------------------------- #

def build_doc_intel(candidate: dict, doc_ref: str) -> dict:
    """Builds a DocIntel object from literal permitted primitives only
    (WRKOPS 281 §8 STRICT CONSTRUCT-ONLY) and validates it before returning.
    Raises RejectedCandidate on any violation; never passes the candidate
    dict through directly."""
    if not isinstance(candidate, dict):
        raise RejectedCandidate("candidate_not_an_object")

    state = candidate.get("state")
    reason = candidate.get("reason")
    analysed_at = candidate.get("analysed_at")
    link_checked_at = candidate.get("link_checked_at")
    cpv_codes = candidate.get("cpv_codes")
    cpv_evidence = candidate.get("cpv_evidence")

    obj: dict = {"schema": DOC_INTEL_SCHEMA}

    if state not in VALID_STATES:
        raise RejectedCandidate("invalid_state")
    obj["state"] = state

    if state == "unavailable":
        if reason not in VALID_REASONS:
            raise RejectedCandidate("invalid_reason")
        obj["reason"] = reason
    elif reason is not None:
        raise RejectedCandidate("reason_outside_unavailable")

    if state in ("analysed", "stale"):
        if not is_rfc3339_z(analysed_at):
            raise RejectedCandidate("analysed_at_required")
        obj["analysed_at"] = analysed_at
    elif analysed_at is not None:
        raise RejectedCandidate("analysed_at_outside_allowed_states")

    if state == "link_checked":
        if not is_rfc3339_z(link_checked_at):
            raise RejectedCandidate("undated_link_checked")
        obj["link_checked_at"] = link_checked_at
    elif link_checked_at is not None:
        raise RejectedCandidate("link_checked_at_outside_allowed_state")

    if state == "analysed":
        valid_codes = [
            c for c in (cpv_codes or [])
            if isinstance(c, str) and CPV_CODE_RE.match(c)
        ]
        if valid_codes:
            if not cpv_evidence:
                raise RejectedCandidate("evidence_required_for_field")
            evidence = []
            for item in cpv_evidence:
                if not isinstance(item, dict):
                    raise RejectedCandidate("evidence_malformed")
                ev_doc_ref = item.get("doc_ref")
                page = item.get("page")
                if ev_doc_ref != doc_ref:
                    raise RejectedCandidate("evidence_wrong_owning_document")
                evidence.append({"doc_ref": ev_doc_ref, "page": page})
            obj["fields"] = [{
                "key": "cpv",
                "type": "code_list",
                "value": valid_codes,
                "evidence": evidence,
            }]
        elif cpv_evidence:
            raise RejectedCandidate("evidence_without_valid_field")
    else:
        if cpv_codes or cpv_evidence:
            raise RejectedCandidate("fields_outside_analysed")

    validate_doc_intel(obj, doc_ref)
    return obj


# --------------------------------------------------------------------------- #
# Production monolith join (WRKOPS t_20260905_adgops282 §4/§6)
#
# Read-only. Nothing here ever mutates production_monolith or any record/
# document dict pulled from it; every value copied out is a plain str/int
# used only to mint a doc_ref or to compare against producer evidence.
# --------------------------------------------------------------------------- #

def _index_production_records(production_monolith: Any):
    """Groups production_monolith["data"] records by canonical_key. A
    canonical_key shared by more than one production record is preserved as
    an ambiguous bucket rather than collapsed, so the record join can reject
    it explicitly instead of guessing."""
    index: dict = {}
    if not isinstance(production_monolith, dict):
        return index
    records = production_monolith.get("data")
    if not isinstance(records, list):
        return index
    for rec in records:
        if isinstance(rec, dict):
            index.setdefault(rec.get("canonical_key"), []).append(rec)
    return index


def _find_production_record(canonical_key: Any, index: dict):
    """Returns (record, None) on an exact single match, else (None, reason)."""
    matches = index.get(canonical_key, [])
    if len(matches) == 0:
        return None, "production_record_missing"
    if len(matches) > 1:
        return None, "production_record_ambiguous"
    return matches[0], None


def _find_production_document(source_url: Any, own_record: dict, all_records: list):
    """Locates the exactly-one documents[] entry named by producer evidence,
    scoped to own_record first (WRKOPS 282 §4 join rule, item 2). A URL that
    resolves nowhere in own_record but does resolve in a different production
    record is reported distinctly (evidence_cross_record) rather than folded
    into the generic missing case, per p273 v0.3 line 805 ("a dangling or
    cross-record pointer => rejection")."""
    su = source_url.strip() if isinstance(source_url, str) else ""
    if not su:
        return None, "evidence_source_url_missing"

    own_docs = own_record.get("documents")
    own_docs = own_docs if isinstance(own_docs, list) else []
    same_record_matches = [
        d for d in own_docs
        if isinstance(d, dict) and str(d.get("url") or "").strip() == su
    ]
    if len(same_record_matches) == 1:
        return same_record_matches[0], None
    if len(same_record_matches) > 1:
        return None, "evidence_document_ambiguous"

    for rec in all_records:
        if rec is own_record:
            continue
        other_docs = rec.get("documents")
        other_docs = other_docs if isinstance(other_docs, list) else []
        if any(isinstance(d, dict) and str(d.get("url") or "").strip() == su for d in other_docs):
            return None, "evidence_cross_record"

    return None, "evidence_document_missing"


def _project_production_document(prod_doc: Any) -> dict:
    """Mints doc_ref for one read-only production documents[] entry
    (item D), and carries forward that document's own pre-existing
    `doc_intel` value unchanged (WRKOPS t_20260906_adgops284 §2/§6): a
    document this run does not touch keeps whatever doc_intel the real
    production record already holds, so the record's effective-final
    DocIntel cap arithmetic reflects real production state, not merely an
    always-empty reconstruction. Never reads or copies any other key."""
    url = prod_doc.get("url") if isinstance(prod_doc, dict) else None
    existing_doc_intel = prod_doc.get("doc_intel") if isinstance(prod_doc, dict) else None
    return {"url": url, "doc_ref": mint_doc_ref(url), "doc_intel": existing_doc_intel}


def _extract_cpv_candidate(record_candidate: dict):
    """Returns (code, source_url, page) for a usable cpv field, or None.

    Any malformed shape or a code failing the closed CPV pattern silently
    suppresses the field (item H) rather than rejecting the record: this
    lane's own capture regex is looser (6-8 digits) than the public closed
    pattern (exactly 8), so a short capture is an expected, non-exceptional
    case, not a producer contract violation."""
    fields = record_candidate.get("fields")
    if not isinstance(fields, dict):
        return None
    cpv = fields.get("cpv")
    if not isinstance(cpv, dict):
        return None
    value = cpv.get("value")
    if not isinstance(value, str) or not CPV_CODE_RE.match(value):
        return None
    evidence = cpv.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != 1:
        return None
    ev = evidence[0]
    if not isinstance(ev, dict):
        return None
    source_url = ev.get("source_url")
    page = ev.get("page")
    if not isinstance(source_url, str) or not source_url.strip():
        return None
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        return None
    return value, source_url, page


def _finalize_projected_record(canonical_key: Any, projected_docs: list, rejected_reason) -> dict:
    """Common finalization step (WRKOPS t_20260906_adgops285 §2-§3) for EVERY
    producer record that resolved to exactly one matched production record,
    regardless of what business outcome preceded it (new CPV attached, no CPV,
    malformed CPV, missing/ambiguous/cross-record evidence, missing
    analysed_at, an unminted doc_ref, or a build_doc_intel rejection). The
    p273 v0.3 §13 per-record 64 KiB cap is a final-record invariant, not a
    success-path-only check: a record already over cap from pre-existing
    doc_intel this run never touched must fail-closed even when this run
    attaches nothing new.

    If the effective final per-record payload exceeds the cap, clears
    doc_intel on every document in the record (never truncates), preserves
    every doc_ref, and returns the stable reason `record_docintel_cap_exceeded`
    -- overriding whatever `rejected_reason` was supplied, since the cap
    dominates any prior business outcome. Otherwise returns the supplied
    `rejected_reason` (success or prior business rejection) unchanged.

    Pure: no I/O, clock, network, producer reads, or mutation of source
    inputs; only the `projected_docs` list passed in (already a fresh
    per-record projection, never the caller's production_monolith) is
    mutated in place."""
    if compute_record_docintel_bytes(projected_docs) > MAX_RECORD_DOCINTEL_BYTES:
        for pd in projected_docs:
            pd["doc_intel"] = None
        return {"canonical_key": canonical_key, "rejected_reason": "record_docintel_cap_exceeded",
                "documents": projected_docs}
    return {"canonical_key": canonical_key, "rejected_reason": rejected_reason, "documents": projected_docs}


def _project_producer_record(record_candidate: Any, analysed_at, prod_index: dict, all_prod_records: list) -> dict:
    """Projects one producer record: joins it to exactly one production
    record (item C), mints doc_ref for every document already on file for
    that production record (item D, item I), then — only if this record
    carries a usable, evidence-resolvable cpv field — attaches doc_intel to
    the exact production document named by that evidence (items E-G).

    Once `projected_docs` exists (a production record was matched), every
    exit path routes through the common `_finalize_projected_record` step
    (WRKOPS t_20260906_adgops285 §2), so the per-record cap is enforced
    identically whether this record ends in a new CPV, no CPV, an invalid
    CPV, missing evidence, missing analysed_at, or any other pre-cap
    rejection branch. `rejected_reason` describes the business outcome
    before finalization; it never means the inventory below is incomplete
    or altered — `documents` always reflects every documents[] entry of the
    matched production record (or is empty only when no production record
    could be identified at all, since no inventory can be attributed without
    one, and that unmatched/ambiguous case has no safely attributable
    inventory to finalize, so it returns before this step)."""
    if not isinstance(record_candidate, dict):
        return {"canonical_key": None, "rejected_reason": "record_candidate_not_an_object", "documents": []}

    canonical_key = record_candidate.get("canonical_key")
    prod_record, reason = _find_production_record(canonical_key, prod_index)
    if prod_record is None:
        return {"canonical_key": canonical_key, "rejected_reason": reason, "documents": []}

    prod_docs = prod_record.get("documents")
    prod_docs = prod_docs if isinstance(prod_docs, list) else []
    projected_docs = [_project_production_document(d) for d in prod_docs]

    cpv_candidate = _extract_cpv_candidate(record_candidate)
    if cpv_candidate is None:
        return _finalize_projected_record(canonical_key, projected_docs, None)
    code, source_url, page = cpv_candidate

    target_doc, doc_reason = _find_production_document(source_url, prod_record, all_prod_records)
    if target_doc is None:
        return _finalize_projected_record(canonical_key, projected_docs, doc_reason)

    if analysed_at is None:
        return _finalize_projected_record(canonical_key, projected_docs, "producer_generated_at_missing")

    target_doc_ref = mint_doc_ref(target_doc.get("url"))
    if target_doc_ref is None:
        return _finalize_projected_record(canonical_key, projected_docs, "doc_ref_not_minted_for_evidence_document")

    candidate = {
        "state": "analysed",
        "analysed_at": analysed_at,
        "cpv_codes": [code],
        "cpv_evidence": [{"doc_ref": target_doc_ref, "page": page}],
    }
    try:
        doc_intel = build_doc_intel(candidate, target_doc_ref)
    except RejectedCandidate as exc:
        return _finalize_projected_record(canonical_key, projected_docs, exc.reason)

    for pd in projected_docs:
        if pd["doc_ref"] == target_doc_ref:
            pd["doc_intel"] = doc_intel

    return _finalize_projected_record(canonical_key, projected_docs, None)


# --------------------------------------------------------------------------- #
# Producer envelope / manifest projection
# --------------------------------------------------------------------------- #

def validate_producer_envelope(producer_input: Any) -> None:
    """Enforces the producer contract gate (WRKOPS 281 §10, offline test
    matrix B). Raises RejectedCandidate on any violation."""
    if not isinstance(producer_input, dict):
        raise RejectedCandidate("producer_envelope_not_an_object")
    schema = producer_input.get("schema")
    if schema in UNSUPPORTED_PRODUCER_SCHEMAS:
        raise RejectedCandidate("unsupported_producer_schema")
    if schema != ACCEPTED_PRODUCER_SCHEMA:
        raise RejectedCandidate("unknown_producer_schema")
    if producer_input.get("production_write_performed") is not False:
        raise RejectedCandidate("production_write_performed_not_false")


def validate_production_monolith(production_monolith: Any) -> None:
    """Fail-closed shape gate for the read-only production monolith (item B).
    Only ever inspects the container shape, never a document/record value."""
    if not isinstance(production_monolith, dict):
        raise RejectedCandidate("production_monolith_not_an_object")
    if not isinstance(production_monolith.get("data"), list):
        raise RejectedCandidate("production_monolith_data_not_a_list")


def project_manifest(producer_input: dict, production_monolith: dict) -> dict:
    """Top-level entry point (WRKOPS t_20260905_adgops282 correction).

    Validates the producer envelope and the read-only production monolith
    shape, then joins and projects every producer record against it. Neither
    argument is ever mutated. Returns a deterministic, implementation-
    internal patch/application structure (§7): the only public mutation
    surface represented anywhere in the result is documents[].doc_ref/
    doc_intel."""
    try:
        validate_producer_envelope(producer_input)
        validate_production_monolith(production_monolith)
    except RejectedCandidate as exc:
        return {"accepted": False, "rejected_reason": exc.reason, "records": []}

    records_in = producer_input.get("records", [])
    if not isinstance(records_in, list):
        return {"accepted": False, "rejected_reason": "records_not_a_list", "records": []}

    # WRKOPS t_20260905_adgops283 §2.2, source-proven (A-D): generated_at_utc
    # is minted by the appendix_pcap_ppt/1 producer's own build_manifest()
    # (pcap_ppt_appendix_extractor.py:839) in the same main() execution that
    # already ran the process_record pass over every record (:1079-1094) --
    # a fresh producer-side UTC clock read, never copied from the upstream
    # feedxml probe input and never a projector/publication timestamp. It is
    # therefore this producer run's own analysis timestamp and MAY be
    # normalized into public analysed_at. PublicProjection itself never reads
    # the clock: malformed/missing input yields None here (to_rfc3339_z never
    # substitutes), which the join below suppresses the CPV field for --
    # never inventing a replacement time.
    analysed_at = to_rfc3339_z(producer_input.get("generated_at_utc"))
    prod_index = _index_production_records(production_monolith)
    all_prod_records = [rec for recs in prod_index.values() for rec in recs]

    return {
        "accepted": True,
        "rejected_reason": None,
        "records": [
            _project_producer_record(r, analysed_at, prod_index, all_prod_records)
            for r in records_in
        ],
    }


# --------------------------------------------------------------------------- #
# Pure patch-application helper (WRKOPS t_20260906_adgops284 §3)
#
# project_manifest() remains the projection/patch producer, returning an
# implementation-internal structure. apply_projection() proves what applying
# that structure to production means: it is a PURE function over an in-memory
# copy of production_monolith, so the patch's real semantics -- including
# effective-final-record cap correctness -- are directly testable rather than
# only inferable from the internal structure's shape.
# --------------------------------------------------------------------------- #

def apply_projection(production_monolith: dict, projection_result: dict) -> dict:
    """Applies a project_manifest() result onto a deep copy of
    production_monolith and returns that copy. Mutates neither argument.

    The only paths that may ever differ between production_monolith and the
    returned value are documents[].doc_ref and documents[].doc_intel; every
    other record/document/meta key at any depth survives structurally
    unchanged. No file I/O, no data/** access, no clock, no network -- pure
    in-memory transformation only.

    Matching is positional within each matched record: projection_result's
    per-record `documents` list is produced by project_manifest() as a 1:1,
    order-preserving projection of that same production record's own
    documents[] (see _project_producer_record), so corresponding entries are
    paired by position rather than by re-deriving a URL/doc_ref lookup."""
    applied = copy.deepcopy(production_monolith)
    if not isinstance(applied, dict) or not isinstance(applied.get("data"), list):
        return applied

    index = _index_production_records(applied)

    for proj_rec in projection_result.get("records", []):
        matches = index.get(proj_rec.get("canonical_key"), [])
        if len(matches) != 1:
            continue
        target_docs = matches[0].get("documents")
        if not isinstance(target_docs, list):
            continue
        proj_docs = proj_rec.get("documents", [])
        if not isinstance(proj_docs, list):
            continue
        for doc, proj_doc in zip(target_docs, proj_docs):
            if not isinstance(doc, dict) or not isinstance(proj_doc, dict):
                continue
            doc["doc_ref"] = proj_doc.get("doc_ref")
            doc["doc_intel"] = proj_doc.get("doc_intel")

    return applied
