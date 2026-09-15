#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/link_check_resolver.py  (ADG-OPS / WRKOPS t_20260914_adgops306 / v0.7.4ad)

IB-5 Phase A dedicated link-check resolver -- SOURCE IMPLEMENTATION ONLY.

Reads already-known public records, selects a deterministic, bounded set of
http(s) document-URL candidates, and probes each one over HTTP(S) to
produce a CANDIDATE `adgops.link_checks/1` sidecar manifest.

CLI input contract (--input): accepts EITHER a bare JSON array of
`public_id`/`id`/`documents[]` record objects (the shape
`tools.scheduled_fetch_merge.canonicalize_and_project()` produces), OR the
canonical persisted artifact envelope `{"meta": {...}, "data": [record,
...]}` -- the exact shape `tools/scheduled_fetch_merge.py`'s --run-live
writer persists to data/licitaciones.json (`{"meta": public_meta, "data":
public_records}`). Both forms yield the same record list; any other
top-level shape is rejected fail-closed with `unrecognized_input_envelope`.
Note: current production data predates `public_id` on every record, so
feeding it as --input today selects zero candidates and the run fails
closed with `no_candidates_selected` -- this resolver does not mint or
backfill `public_id`.

This module MUST NOT and does not:
  - perform a real network run as part of this task's own validation (its
    own test suite mocks/fakes transport -- see tools/test_link_check_resolver.py);
  - know how to commit or push private state;
  - write directly to data/licitaciones.json, the private
    Scorpioon/licitaciones-adg-state companion repository, or
    .github/workflows/fetch.yml.

Fail-closed SSRF/URL safety (handoff §8): only http/https, no embedded
userinfo, no empty hostname, no localhost/loopback/link-local/private/
reserved destination -- re-checked at every redirect hop before following it,
with a bounded redirect depth. `resolve_url()`'s `resolver` parameter (a
`socket.getaddrinfo`-shaped callable) is injectable so tests never perform
real DNS.

HTTP outcome classification (handoff §9) is a fixed three-way split:
REACHABLE (eligible for public `link_checked`), CONFIRMED_UNAVAILABLE
(terminal 404/410, private-sidecar-only), UNKNOWN_OR_TRANSIENT (everything
else, including a safety rejection or a circuit-breaker skip -- never
eligible for public projection).

Never persists a response body, HTML body, cookies, an Authorization header,
arbitrary response headers, or a secret/token -- only the closed
`adgops.link_checks/1` observation fields below.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    from tools.canonical_tender_merge import document_identity_key
except ImportError:
    from canonical_tender_merge import document_identity_key

try:
    from tools import public_contract as pc
except ImportError:
    import public_contract as pc

is_rfc3339_z = pc.is_rfc3339_z

VERSION = "v0.7.4ad"
SCHEMA = "adgops.link_checks/1"

ALLOWED_SCHEMES = frozenset({"http", "https"})
CLASSIFICATIONS = frozenset({"REACHABLE", "CONFIRMED_UNAVAILABLE", "UNKNOWN_OR_TRANSIENT"})
RESOLVER_METHODS = frozenset({"HEAD", "RANGE_GET", "SKIPPED", "ERROR"})

MAX_REDIRECTS = 5
MAX_RANGE_BYTES = 4096
_USER_AGENT = f"ADG-OPS-LinkCheckResolver/{VERSION}"

RUN_LEVEL_KEYS = frozenset({
    "schema", "run_id", "started_at", "completed_at", "resolver_policy",
    "counts", "observations",
})
OBSERVATION_REQUIRED_KEYS = frozenset({
    "public_id", "record_id", "document_key", "requested_url", "observed_at",
    "resolver_method", "http_status", "classification",
})
OBSERVATION_OPTIONAL_KEYS = frozenset({"final_url"})
OBSERVATION_ALLOWED_KEYS = OBSERVATION_REQUIRED_KEYS | OBSERVATION_OPTIONAL_KEYS

# Explicit, testable restatement of handoff §6's forbidden-field list. The
# closed OBSERVATION_ALLOWED_KEYS set above already makes these structurally
# impossible; this guard exists so a future accidental key addition to that
# set still fails a dedicated test rather than only "shrinking" silently.
_FORBIDDEN_OBSERVATION_FIELDS = frozenset({
    "response_body", "html_body", "body", "cookies", "authorization",
    "headers", "secrets", "token", "content", "raw_headers",
})


class LinkCheckContractError(ValueError):
    """Fail-closed error for any resolver-owned contract violation: a
    malformed --input argument, or a produced sidecar failing its own
    self-validation. Carries a stable, non-sensitive reason code only."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class UrlSafetyError(ValueError):
    """Raised by check_url_safety() for any SSRF/URL-safety violation.
    Carries a stable, non-sensitive reason code only."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- #
# SSRF / URL safety (handoff §8)
# --------------------------------------------------------------------------- #

def _is_safe_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        addr.is_loopback or addr.is_link_local or addr.is_private
        or addr.is_reserved or addr.is_multicast or addr.is_unspecified
    )


def _resolve_host_addresses(host: str, resolver):
    """Returns a list of resolved IP address strings, or None on a genuine
    resolution failure (never treated as a safety pass)."""
    try:
        infos = resolver(host, None)
    except (socket.gaierror, OSError):
        return None
    addrs = []
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            addrs.append(sockaddr[0])
    return addrs


def check_url_safety(url: str, resolver=socket.getaddrinfo):
    """Fail-closed SSRF/URL safety check for one URL (handoff §8). Raises
    UrlSafetyError with a stable reason on any violation; returns the parsed
    urllib.parse.SplitResult on success. `resolver` is injectable (a
    `socket.getaddrinfo`-shaped callable) so tests never perform real DNS."""
    if not isinstance(url, str) or not url:
        raise UrlSafetyError("malformed_url")
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        raise UrlSafetyError("malformed_url")

    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlSafetyError("unsupported_scheme")

    try:
        userinfo_present = parsed.username is not None or parsed.password is not None
    except ValueError:
        raise UrlSafetyError("malformed_url")
    if userinfo_present:
        raise UrlSafetyError("embedded_userinfo")

    try:
        host = parsed.hostname
    except ValueError:
        raise UrlSafetyError("malformed_url")
    if not host:
        raise UrlSafetyError("empty_hostname")

    host_l = host.lower()
    if host_l == "localhost" or host_l.endswith(".localhost"):
        raise UrlSafetyError("localhost_hostname")

    literal_ip = None
    try:
        literal_ip = ipaddress.ip_address(host_l)
    except ValueError:
        literal_ip = None
    if literal_ip is not None and not _is_safe_ip(str(literal_ip)):
        raise UrlSafetyError("unsafe_literal_ip")

    addrs = _resolve_host_addresses(host_l, resolver)
    if addrs is None:
        raise UrlSafetyError("dns_resolution_failed")
    if not addrs:
        raise UrlSafetyError("dns_resolution_empty")
    for a in addrs:
        if not _is_safe_ip(a):
            raise UrlSafetyError("unsafe_resolved_address")

    return parsed


# --------------------------------------------------------------------------- #
# Network probing (HEAD first, bounded Range GET fallback -- handoff §7)
#
# A dedicated no-follow redirect handler always returns the bare 3xx
# response (never auto-follows) so every redirect target can be safety
# checked BEFORE being followed (handoff §8) -- the invariant a stdlib
# default opener would silently bypass.
# --------------------------------------------------------------------------- #

class _NoFollowRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoFollowRedirectHandler)


def _open_once(url, method, timeout, max_range_bytes):
    """Issues one HTTP request. Returns (meta, body, err); `err` is
    populated only for a genuine transport-level exception -- an HTTP status
    (including 3xx/4xx/5xx) is always a `meta`, never an `err`, since a
    status code is a meaningful response, not a transport failure."""
    headers = {"User-Agent": _USER_AGENT, "Accept": "*/*"}
    if method == "GET":
        headers["Range"] = f"bytes=0-{max_range_bytes - 1}"
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with _NO_REDIRECT_OPENER.open(req, timeout=timeout) as resp:
            body = resp.read(max_range_bytes) if method == "GET" else b""
            meta = {
                "http_status": getattr(resp, "status", None) or resp.getcode(),
                "headers": resp.headers,
                "final_url": resp.geturl(),
            }
            return meta, body, None
    except urllib.error.HTTPError as e:
        meta = {
            "http_status": e.code,
            "headers": e.headers,
            "final_url": e.url if getattr(e, "url", None) else url,
        }
        return meta, b"", None
    except Exception as e:  # transport-level: timeout, DNS, TLS, connection reset, ...
        return None, None, {"error_type": type(e).__name__, "error_message": str(e)[:300]}


def _probe_hop(url, timeout, max_range_bytes):
    """One HEAD-first, bounded-GET-fallback attempt at one URL (no redirect
    following here -- that is resolve_url()'s job). Falls back to a Range GET
    when HEAD fails at the transport level, or when HEAD reports 405 Method
    Not Allowed."""
    meta, _body, err = _open_once(url, "HEAD", timeout, max_range_bytes)
    method = "HEAD"
    if err or (meta is not None and meta["http_status"] == 405):
        meta2, _body2, err2 = _open_once(url, "GET", timeout, max_range_bytes)
        if err2:
            # Both attempts failed at the transport level -- report the
            # closed RESOLVER_METHODS "ERROR" outcome, not the method name
            # of whichever attempt happened to run last.
            final_err = err if err is not None else err2
            return "ERROR", None, None, None, final_err["error_type"], final_err["error_message"]
        meta, method = meta2, "RANGE_GET"

    # Past this point meta is always populated: either the original HEAD
    # succeeded outright (err was falsy, status != 405), or the GET
    # fallback above succeeded (meta reassigned to meta2).
    return method, meta["http_status"], meta.get("headers"), meta.get("final_url"), None, None


def _classify(http_status):
    if http_status in (200, 206):
        return "REACHABLE"
    if http_status in (404, 410):
        return "CONFIRMED_UNAVAILABLE"
    return "UNKNOWN_OR_TRANSIENT"


def resolve_url(url, timeout, resolver=socket.getaddrinfo, max_range_bytes=MAX_RANGE_BYTES,
                 max_redirects=MAX_REDIRECTS):
    """Resolves one URL end to end: safety check, probe, and (bounded,
    per-hop-safety-checked) redirect follow.

    Returns (resolver_method, http_status, final_url, classification,
    error_type, error_message). `error_type`/`error_message` are populated
    only for a safety rejection or a genuine transport exception --
    `resolver_method == "ERROR"` marks the latter specifically."""
    current = url
    depth = 0
    while True:
        try:
            check_url_safety(current, resolver)
        except UrlSafetyError as e:
            return "SKIPPED", None, current, "UNKNOWN_OR_TRANSIENT", "UrlSafetyError", e.reason

        method, status, headers, final_url, err_type, err_msg = _probe_hop(
            current, timeout, max_range_bytes
        )
        if err_type is not None:
            return method, None, current, "UNKNOWN_OR_TRANSIENT", err_type, err_msg

        if status in (301, 302, 303, 307, 308):
            location = headers.get("Location") if headers is not None else None
            if not location:
                return method, status, current, "UNKNOWN_OR_TRANSIENT", "RedirectMissingLocation", None
            depth += 1
            if depth > max_redirects:
                return method, status, current, "UNKNOWN_OR_TRANSIENT", "RedirectDepthExceeded", None
            current = urllib.parse.urljoin(current, location)
            continue

        return method, status, (final_url or current), _classify(status), None, None


# --------------------------------------------------------------------------- #
# Deterministic candidate selection (handoff §7)
# --------------------------------------------------------------------------- #

def normalize_link_check_input(raw: Any) -> list:
    """Normalizes the resolver's --input JSON into a list of public records
    (Prompt 309, IB-5 Phase A-bis input-contract correction). Accepts either:

      1. a bare list: `[record, ...]`
      2. the canonical persisted artifact envelope:
         `{"meta": {...}, "data": [record, ...]}`
         -- the exact shape `tools/scheduled_fetch_merge.py`'s --run-live
         writer persists (`{"meta": public_meta, "data": public_records}`).

    Records are never derived from any other key. Any other top-level shape
    -- including an object missing `data`, or whose `data` is not a list --
    is rejected fail-closed with the stable reason
    `unrecognized_input_envelope`. Never mutates `raw`."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, list):
            return data
    raise LinkCheckContractError("unrecognized_input_envelope")


def select_candidates(public_records: Any, limit: int) -> list:
    """Returns up to `limit` (public_id, record_id, doc, url) tuples,
    deterministically ordered by (public_id, document_identity_key(doc)) --
    never by array position, wall clock, or randomness. Skips any record
    missing a usable public_id/id, and any document without a syntactically
    http(s) url; the full SSRF safety check runs later, per candidate, in
    resolve_url()."""
    if not isinstance(public_records, list):
        raise LinkCheckContractError("public_records_not_a_list")

    candidates = []
    for rec in public_records:
        if not isinstance(rec, dict):
            continue
        pid = rec.get("public_id")
        rid = rec.get("id")
        if not isinstance(pid, str) or not pid:
            continue
        if not isinstance(rid, str) or not rid:
            continue
        docs = rec.get("documents")
        if not isinstance(docs, list):
            continue
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            url = doc.get("url")
            if not isinstance(url, str) or not url:
                continue
            try:
                scheme = urllib.parse.urlsplit(url).scheme.lower()
            except ValueError:
                continue
            if scheme not in ALLOWED_SCHEMES:
                continue
            candidates.append((pid, rid, doc, url))

    candidates.sort(key=lambda t: (t[0], list(document_identity_key(t[2]))))
    return candidates[:max(limit, 0)]


# --------------------------------------------------------------------------- #
# Sidecar contract (handoff §6): strict, fail-closed parser/validator.
# Defined here (not a separate helper module) per handoff §6's own
# permission ("The resolver may define this contract in
# tools/link_check_resolver.py").
# --------------------------------------------------------------------------- #

def _validate_observation(item: Any) -> None:
    if not isinstance(item, dict):
        raise LinkCheckContractError("observation_not_an_object")
    keys = set(item.keys())

    unknown = keys - OBSERVATION_ALLOWED_KEYS
    if unknown:
        raise LinkCheckContractError("observation_unknown_keys")
    missing = OBSERVATION_REQUIRED_KEYS - keys
    if missing:
        raise LinkCheckContractError("observation_missing_keys")
    if keys & _FORBIDDEN_OBSERVATION_FIELDS:
        raise LinkCheckContractError("observation_forbidden_field_present")

    if not isinstance(item.get("public_id"), str) or not item["public_id"]:
        raise LinkCheckContractError("observation_invalid_public_id")
    if not isinstance(item.get("record_id"), str) or not item["record_id"]:
        raise LinkCheckContractError("observation_invalid_record_id")

    doc_key = item.get("document_key")
    if (not isinstance(doc_key, list) or not doc_key
            or not all(isinstance(x, str) for x in doc_key)):
        raise LinkCheckContractError("observation_invalid_document_key")
    # Deterministic JSON-compatible round trip (handoff §6): never a
    # runtime-specific/opaque tuple serialization.
    if json.loads(json.dumps(doc_key)) != doc_key:
        raise LinkCheckContractError("observation_document_key_not_round_trippable")

    if not isinstance(item.get("requested_url"), str) or not item["requested_url"]:
        raise LinkCheckContractError("observation_invalid_requested_url")
    if not is_rfc3339_z(item.get("observed_at")):
        raise LinkCheckContractError("observation_invalid_observed_at")
    if item.get("resolver_method") not in RESOLVER_METHODS:
        raise LinkCheckContractError("observation_invalid_resolver_method")

    http_status = item.get("http_status")
    if http_status is not None and (
            not isinstance(http_status, int) or isinstance(http_status, bool)):
        raise LinkCheckContractError("observation_invalid_http_status")

    if item.get("classification") not in CLASSIFICATIONS:
        raise LinkCheckContractError("observation_invalid_classification")

    if "final_url" in item and not isinstance(item["final_url"], str):
        raise LinkCheckContractError("observation_invalid_final_url")


def validate_link_check_sidecar(obj: Any) -> None:
    """Strict, fail-closed validator for one `adgops.link_checks/1` sidecar
    (handoff §6). Rejects unknown top-level/observation keys rather than
    tolerating them. Raises LinkCheckContractError with a stable reason on
    any violation."""
    if not isinstance(obj, dict):
        raise LinkCheckContractError("sidecar_not_an_object")

    keys = set(obj.keys())
    unknown = keys - RUN_LEVEL_KEYS
    if unknown:
        raise LinkCheckContractError("unknown_top_level_keys")
    missing = RUN_LEVEL_KEYS - keys
    if missing:
        raise LinkCheckContractError("missing_top_level_keys")

    if obj.get("schema") != SCHEMA:
        raise LinkCheckContractError("invalid_schema")
    if not isinstance(obj.get("run_id"), str) or not obj["run_id"]:
        raise LinkCheckContractError("invalid_run_id")
    if not is_rfc3339_z(obj.get("started_at")):
        raise LinkCheckContractError("invalid_started_at")
    if not is_rfc3339_z(obj.get("completed_at")):
        raise LinkCheckContractError("invalid_completed_at")
    if not isinstance(obj.get("resolver_policy"), dict):
        raise LinkCheckContractError("invalid_resolver_policy")
    if not isinstance(obj.get("counts"), dict):
        raise LinkCheckContractError("invalid_counts")

    observations = obj.get("observations")
    if not isinstance(observations, list):
        raise LinkCheckContractError("observations_not_a_list")
    for item in observations:
        _validate_observation(item)


def load_link_check_sidecar(path) -> dict:
    """Reads and strictly validates one `adgops.link_checks/1` sidecar file.
    Raises LinkCheckContractError (malformed JSON is wrapped the same way)
    on any violation; never returns a partially-trusted object."""
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise LinkCheckContractError(f"cannot_read_sidecar: {e}")
    validate_link_check_sidecar(obj)
    return obj


# --------------------------------------------------------------------------- #
# CLI / main
# --------------------------------------------------------------------------- #

def _now_z() -> str:
    return pc.to_rfc3339_z(datetime.now(timezone.utc).isoformat())


def _build_counts(observations: list, candidates_considered: int) -> dict:
    method_counts: dict = {}
    classification_counts: dict = {}
    for obs in observations:
        method_counts[obs["resolver_method"]] = method_counts.get(obs["resolver_method"], 0) + 1
        classification_counts[obs["classification"]] = (
            classification_counts.get(obs["classification"], 0) + 1
        )
    attempted = len(observations)
    errors = classification_counts.get("UNKNOWN_OR_TRANSIENT", 0)
    return {
        "candidates_considered": candidates_considered,
        "candidates_attempted": attempted,
        "resolver_method_counts": method_counts,
        "classification_counts": classification_counts,
        "resolver_error_rate": round(errors / attempted, 6) if attempted else 0.0,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="link_check_resolver.py",
        description=(
            f"IB-5 Phase A link-check resolver (ADG-OPS {VERSION}). Reads "
            "already-known public records (public_id/id/documents[]) as "
            "either a bare JSON array or the canonical {meta,data} artifact "
            f"envelope, and produces a CANDIDATE {SCHEMA} sidecar. Never "
            "commits, pushes, or writes production/private state."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--input", required=True, metavar="PATH",
                     help="Path to a JSON array of already-known public records, "
                          "or the canonical {meta,data} artifact envelope "
                          "(e.g. data/licitaciones.json's persisted shape).")
    ap.add_argument("--output", required=True, metavar="PATH",
                     help="Output path for the CANDIDATE sidecar manifest.")
    ap.add_argument("--limit", type=int, default=50,
                     help="Max candidates to resolve after deterministic selection.")
    ap.add_argument("--timeout", type=float, default=20.0,
                     help="HTTP request timeout (seconds).")
    ap.add_argument("--sleep", type=float, default=0.25,
                     help="Sleep between candidates (seconds).")
    ap.add_argument("--stop-error-rate", type=float, default=0.05, dest="stop_error_rate",
                     help="Abort once the running UNKNOWN_OR_TRANSIENT rate exceeds this.")
    ap.add_argument("--stop-consecutive-errors", type=int, default=10,
                     dest="stop_consecutive_errors",
                     help="Abort after N consecutive transport-level (ERROR) attempts.")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                     help="Make no network call at all; every candidate is recorded SKIPPED.")
    return ap


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        with open(args.input, encoding="utf-8") as f:
            raw_input = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[LINK-CHECK BLOCKED] cannot read --input: {e}", file=sys.stderr)
        return 1

    try:
        public_records = normalize_link_check_input(raw_input)
    except LinkCheckContractError as e:
        print(f"[LINK-CHECK BLOCKED] {e.reason}", file=sys.stderr)
        return 1

    try:
        candidates = select_candidates(public_records, args.limit)
    except LinkCheckContractError as e:
        print(f"[LINK-CHECK BLOCKED] {e.reason}", file=sys.stderr)
        return 1

    if not candidates:
        # Prompt 309 §4.B: a zero-candidate run is never a false-green
        # success -- fail closed before any network execution, with a
        # stable reason token, non-zero exit, and no sidecar written,
        # regardless of *why* selection produced zero candidates (missing
        # public_id, missing/invalid id, missing/invalid documents, no
        # usable http(s) URL, ...).
        print("[LINK-CHECK BLOCKED] no_candidates_selected", file=sys.stderr)
        return 1

    run_id = uuid.uuid4().hex
    started_at = _now_z()
    observations: list = []
    consecutive_transport_errors = 0
    aborted = False

    for i, (pid, rid, doc, url) in enumerate(candidates):
        doc_key = list(document_identity_key(doc))

        if args.dry_run:
            method, status, final_url, classification = "SKIPPED", None, None, "UNKNOWN_OR_TRANSIENT"
        else:
            method, status, final_url, classification, _err_type, _err_msg = resolve_url(
                url, args.timeout,
            )

        obs = {
            "public_id": pid,
            "record_id": rid,
            "document_key": doc_key,
            "requested_url": url,
            "observed_at": _now_z(),
            "resolver_method": method,
            "http_status": status,
            "classification": classification,
        }
        if final_url and final_url != url:
            obs["final_url"] = final_url
        observations.append(obs)

        print(f"  [{i + 1}/{len(candidates)}] {pid} {method} status={status} -> {classification}")

        if not args.dry_run:
            # f2b convention (tools/fetch_documents_f2b.py): only a genuine
            # transport-level ERROR resets/increments the consecutive-error
            # streak; a SKIPPED (safety-rejected) candidate resets it to 0
            # but still counts toward the overall error rate below.
            consecutive_transport_errors = consecutive_transport_errors + 1 if method == "ERROR" else 0

            n = len(observations)
            error_n = sum(1 for o in observations if o["classification"] == "UNKNOWN_OR_TRANSIENT")
            error_rate = error_n / n
            if error_rate > args.stop_error_rate:
                print(f"[LINK-CHECK ABORT] error_rate={error_rate:.4f} "
                      f"> threshold={args.stop_error_rate}", file=sys.stderr)
                aborted = True
                break
            if consecutive_transport_errors >= args.stop_consecutive_errors:
                print(f"[LINK-CHECK ABORT] consecutive_errors={consecutive_transport_errors}",
                      file=sys.stderr)
                aborted = True
                break

            if i < len(candidates) - 1:
                time.sleep(args.sleep)

    completed_at = _now_z()
    sidecar = {
        "schema": SCHEMA,
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "resolver_policy": {
            "version": VERSION,
            "limit": args.limit,
            "timeout": args.timeout,
            "sleep": args.sleep,
            "stop_error_rate": args.stop_error_rate,
            "stop_consecutive_errors": args.stop_consecutive_errors,
            "dry_run": args.dry_run,
            "max_redirects": MAX_REDIRECTS,
        },
        "counts": _build_counts(observations, len(candidates)),
        "observations": observations,
    }

    try:
        validate_link_check_sidecar(sidecar)
    except LinkCheckContractError as e:
        print(f"[LINK-CHECK BLOCKED] produced sidecar failed self-validation: {e.reason}",
              file=sys.stderr)
        return 1

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, ensure_ascii=False, indent=2)

    print(f"[LINK-CHECK] done: attempted={len(observations)} candidates={len(candidates)} "
          f"-> {args.output}")
    return 2 if aborted else 0


if __name__ == "__main__":
    sys.exit(main())
