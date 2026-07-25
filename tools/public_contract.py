#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/public_contract.py  (ADG OPS / p252 / v0.7.1e)

Single source of truth for the ADG-OPS canonical public provenance/metadata
contract — A1 "adgops.public.licitaciones/1", LOCK-19 (anti-competition rule).

Every public contract constant and every pure derivation lives here exactly
once. The three consumers import from this module and define no competing
constant of their own:

  - tools/scheduled_fetch_merge.py  (merger — mints generation identity,
                                     builds the canonical public meta block)
  - tools/build_data_shards.py      (shard builder — propagates shared fields
                                     verbatim, never mints or re-derives)
  - .github/workflows/fetch.yml     (publication gate — verifies, fail-closed)

Discipline (A1 §9 requirements): stdlib only, deterministic, no network, no
file writes, no application imports, no fetcher/parser imports, no Git logic,
no workflow-specific side effects, no operational telemetry. Fetcher 1 merge
and retrieval behaviour never moves into this module.

Note on the public meta shape: A1's provenance content (`sources`,
`transformations`) is emitted as TOP-LEVEL meta fields, not nested inside a
`provenance` object. The published p248 consumer (app.js applyDatasetMeta)
reads `meta.sources`, `meta.pipeline` and `meta.transformations` as separate
concepts; nesting them under `provenance` is exactly the field-shape drift
p251 corrects. No `provenance` container is emitted (it would either duplicate
those arrays or be an empty, meaningless public field).
"""

import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Public schema identity (A1 §7.1)
# ---------------------------------------------------------------------------

PUBLIC_SCHEMA         = "adgops.public.licitaciones/1"
PUBLIC_SCHEMA_VERSION = 1

# Public state model — exactly one legal value in any tracked public artifact
# (A1 §6.2, LOCK-10).
PUBLICATION_STATE = "published"

# Artifact-class discriminators (A1 §10.2 `artifact` field).
ARTIFACT_MONOLITH = "monolith"
ARTIFACT_MANIFEST = "manifest"
ARTIFACT_SHARD    = "shard"

# ---------------------------------------------------------------------------
# Pipeline identity (A1 §7.1) — one constant for the whole pipeline
# ---------------------------------------------------------------------------

PIPELINE_NAME    = "adgops-licitaciones-pipeline"
PIPELINE_VERSION = "1.0.0"
PIPELINE_STAGES  = ("harvest", "merge", "shard")

TRANSFORMATIONS = (
    "relevance_scoring",
    "discipline_classification",
    "lifecycle_classification",
    "canonical_dedup_view",
)

# ---------------------------------------------------------------------------
# Public source registry (A1 §8.1, §6)
#
# Keyed by the source name the Harvester reports in requested_sources /
# completed_sources / failed_sources. Only public feed identity is ever
# published — never retry telemetry, page counts or source_errors strings.
# The public field name is `id` (A1 §6), never `source_id`.
# ---------------------------------------------------------------------------

PUBLIC_SOURCES = {
    "PLACSP-643": {
        "id": "PLACSP-643",
        "name": "PLACSP Sindicación 643",
        "url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
               "licitacionesPerfilesContratanteCompleto3.atom",
    },
    "PLACSP-1044": {
        "id": "PLACSP-1044",
        "name": "PLACSP Sindicación 1044",
        "url": "https://contrataciondelsectorpublico.gob.es/sindicacion/"
               "sindicacion_1044/PlataformasAgregadasSinMenores.atom",
    },
}

SOURCE_STATUS_OK       = "ok"
SOURCE_STATUS_DEGRADED = "degraded"
SOURCE_STATUS_FAILED   = "failed"

# Allowed keys on a public source entry (A1 §6). `retrieved_at` is present only
# on successfully-retrieved sources (A1 §7 — enforced by the merger).
PUBLIC_SOURCE_KEYS = ("id", "name", "url", "retrieved_at", "status")

# ---------------------------------------------------------------------------
# Shared meta keys (A1 §10, §12)
#
# Present and byte-identical in monolith.meta and manifest.meta. The `artifact`
# discriminator differs by class and is therefore NOT shared. `sources` and
# `transformations` are shared top-level fields (A1 provenance content, emitted
# flat — see module docstring). No `provenance` key is emitted.
# ---------------------------------------------------------------------------

SHARED_META_KEYS = (
    "schema",
    "schema_version",
    "publication_state",
    "generation_id",
    "dataset_sha256",
    "source_retrieved_at",
    "dataset_generated_at",
    "pipeline",
    "counts",
    "sources",
    "transformations",
)

# Canonical top-level key order of a monolith/manifest public meta block.
PUBLIC_META_TOP_KEYS = (
    "schema",
    "schema_version",
    "artifact",
    "publication_state",
    "generation_id",
    "dataset_sha256",
    "source_retrieved_at",
    "dataset_generated_at",
    "pipeline",
    "counts",
    "sources",
    "transformations",
)

# 9-key shard identity stub (A1 §13).
SHARD_META_KEYS = (
    "schema",
    "schema_version",
    "artifact",
    "publication_state",
    "generation_id",
    "dataset_sha256",
    "year",
    "priority",
    "record_count",
)

# ---------------------------------------------------------------------------
# Logical dataset serialization + hash (A1 §7.2)
# ---------------------------------------------------------------------------

def serialize_records(records):
    """Locked canonical serialization of the records array for hashing.

    ensure_ascii=False, separators=(",", ":"), no key reordering. This exact
    form is what the dataset hash is computed over; it must never drift, or the
    merger, shard builder and workflow gate will disagree on dataset identity.
    """
    return json.dumps(records, ensure_ascii=False, separators=(",", ":"))


def compute_dataset_sha256(records):
    """SHA-256 over the records array alone (A1 §7.2).

    Hashing the records rather than the file makes the dataset identity
    independent of metadata rewrites, so the merger can mint it before writing
    and every downstream artifact can carry and verify the same value.
    """
    return hashlib.sha256(serialize_records(records).encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Generation identity (A1 §7.2)
# ---------------------------------------------------------------------------

GENERATION_ID_RE = re.compile(r"^gen-(\d{8}T\d{6}Z)-([0-9a-f]{12})$")


def mint_generation_id(dataset_generated_at, dataset_sha256):
    """gen-<YYYYMMDDTHHMMSSZ>-<dataset_sha256[:12]> (A1 §7.2).

    Minted from a caller-supplied generation timestamp and the logical dataset
    hash — never from a temporary filename, prompt number, Git commit or local
    path. The merger is the only component that calls this.
    """
    compact = dataset_generated_at.replace("-", "").replace(":", "")
    return "gen-%s-%s" % (compact, dataset_sha256[:12])


def is_valid_generation_id(value):
    return isinstance(value, str) and GENERATION_ID_RE.match(value) is not None


def generation_id_matches(generation_id, dataset_generated_at, dataset_sha256):
    """True iff the id is well-formed and its prefix equals the compacted
    dataset_generated_at and its suffix equals dataset_sha256[:12] (A1 §7.2)."""
    m = GENERATION_ID_RE.match(generation_id or "")
    if not m:
        return False
    compact = (dataset_generated_at or "").replace("-", "").replace(":", "")
    return m.group(1) == compact and m.group(2) == (dataset_sha256 or "")[:12]

# ---------------------------------------------------------------------------
# RFC3339 UTC timestamps (A1 §7.3)
# ---------------------------------------------------------------------------

RFC3339_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def to_rfc3339_z(value):
    """Normalize a timestamp to RFC3339 UTC second precision, else None.

    Returns None when the value is absent or unparseable — never a substitute
    timestamp. Callers decide how to fail; this function does not invent time.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_rfc3339_z(value):
    return isinstance(value, str) and RFC3339_Z_RE.match(value) is not None


def timestamps_non_decreasing(*values):
    """True iff every argument is a valid RFC3339 Z string and they are in
    non-decreasing order (A1 §7.3 ordering invariant). Lexical comparison is
    exact for this fixed-width UTC format."""
    for v in values:
        if not is_rfc3339_z(v):
            return False
    return all(values[i] <= values[i + 1] for i in range(len(values) - 1))

# ---------------------------------------------------------------------------
# Forbidden public metadata keys (A1 §8.2, §15)
# ---------------------------------------------------------------------------

# Internal/legacy bookkeeping key names that must never appear at ANY depth of
# a public metadata block. Detected recursively (A1 §13).
#
# Deliberately excludes bare "version": the ONE legitimate public `version`
# key is `pipeline.version` (A1 §7.1) and only inside a canonical meta block
# (monolith.meta / manifest.meta). Because a name-only scan cannot tell
# `pipeline.version` (allowed) from `monolith.meta.version` / a source-entry
# `version` / a shard `version` (all forbidden), the `version` key is NOT
# policed here — it is policed context-aware by find_forbidden_version_paths()
# below, whose caller opts a scan site into the pipeline.version exception
# (allow_pipeline_version=True) only for the two canonical meta blocks; every
# other public `version` path is rejected.
FORBIDDEN_META_KEYS = frozenset({
    "mode", "production_write", "production_write_performed", "note",
    "backup_path", "candidate_path", "production_input",
    "candidate_109_input", "policy_110_input", "policy_111_input",
    "production_write_gate_prompt", "production_write_gate_version",
    "production_write_gate_applied_at", "production_write_gate_backup",
    "production_write_gate_note", "scheduled_merge_mode",
    "scheduled_merge_prompt", "scheduled_merge_version",
    "scheduled_merge_applied_at", "generated_at", "generated_by_prompt",
    "target_version", "canonical_source_preserved", "top_shape",
    "source", "source_sha256", "source_meta", "source_errors",
    "prompt", "patch", "patch_label", "run_id", "run_status", "run_mode",
    "is_partial", "requested_sources", "completed_sources", "failed_sources",
    "fetcher_version", "candidate_input", "policy_input",
})

# Legacy manifest TOP-LEVEL keys (checked against manifest.keys() only, not
# recursively). The canonical manifest top level is exactly {meta, monolith,
# shards}. `schema`/`counts` are legitimate INSIDE manifest.meta but forbidden
# at the manifest root; `validation` and `source_meta` are removed in p251.
FORBIDDEN_MANIFEST_TOP_KEYS = frozenset({
    "schema", "generated_by_prompt", "target_version", "source",
    "source_sha256", "generated_at_utc", "canonical_source_preserved",
    "top_shape", "counts", "source_meta", "validation",
})


def find_forbidden_keys(node):
    """Recursively collect FORBIDDEN_META_KEYS present as dict keys at any depth.

    Returns a sorted list of offending KEY NAMES only. Values are never
    returned or logged (A1 §14 — report the family, never the value).
    """
    hits = set()

    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(k, str) and k in FORBIDDEN_META_KEYS:
                    hits.add(k)
                walk(v)
        elif isinstance(n, (list, tuple)):
            for v in n:
                walk(v)

    walk(node)
    return sorted(hits)

# ---------------------------------------------------------------------------
# Context-aware `version` rule (A1 §7.1, p252 §6-§9)
#
# `pipeline.version` is the only authorized public `version`, and only when it
# is the pipeline object's own `version` at the root of a canonical meta block
# (monolith.meta / manifest.meta). Every other public metadata `version` —
# monolith.meta.version, manifest.meta.version, a shard-meta pipeline.version,
# a manifest.monolith pipeline.version, a manifest.shards[].pipeline.version, a
# pipeline expressed as a LIST containing version, a source-entry version, a
# transformations version, or any unknown public version — is a contract
# violation.
#
# A relative-path-only rule is insufficient: the workflow scans several public
# structures independently, so a bare "allow the pipeline.version path wherever
# it appears" would wrongly admit a shard-meta pipeline.version, a
# manifest.monolith pipeline.version, or a pipeline[0].version list bypass. The
# policy is therefore made explicit at each scan site: the caller opts in to the
# exception (allow_pipeline_version=True) ONLY for the two canonical meta blocks,
# and even then the exception is granted only when `pipeline` is a dict whose own
# direct `version` key sits at the scanned root. Because the walk tracks list
# INDICES as well as dict keys, `pipeline[0].version` carries the path
# ("pipeline", 0, "version") and can never collapse into the allowed
# ("pipeline", "version") — the list bypass is structurally impossible.
# ---------------------------------------------------------------------------

# The one authorized public `version` location, expressed as its path WITHIN a
# scanned meta block: `pipeline` (a dict) sits at the meta-block root and
# `version` is the semver directly under it. A pipeline represented as a list
# yields a path with an intervening integer index and therefore never matches.
_ALLOWED_VERSION_PATH = ("pipeline", "version")


def _render_version_path(path):
    """Render a tracked key/index path as an auditable dotted string.

    Dict keys join with '.'; list indices render as '[i]' so a list-nested
    version (e.g. pipeline[0].version) is visibly positional and never collapses
    to the allowed pipeline.version. Only structural keys/indices appear — never
    a value (A1 §14, p252 §7.10).
    """
    out = ""
    for seg in path:
        if isinstance(seg, int):
            out += "[%d]" % seg
        else:
            out += ("." if out else "") + seg
    return out


def find_forbidden_version_paths(node, *, allow_pipeline_version=False):
    """Recursively collect the paths of every public `version` key that is NOT
    an authorized pipeline.version (A1 §7.1, p252 §7).

    Policy (explicit, never implicit — pass it at every scan site):

      - default (allow_pipeline_version=False): EVERY key named `version` is a
        violation. Use for shard metadata, manifest.monolith, manifest.shards,
        sources, transformations and any unknown public container.
      - allow_pipeline_version=True: the single path ("pipeline", "version") is
        permitted — and only that path. Use ONLY for a canonical meta block
        (monolith.meta / manifest.meta). The exception is granted iff `pipeline`
        is a dict at the scanned root and `version` is its own direct key; a
        pipeline LIST, a nested pipeline.version, or any other version path is
        still reported.

    The walk tracks dict keys AND list indices, so list positions are preserved
    (`sources[0].version`, `pipeline[0].version`) and never discarded into a bare
    key path. `schema_version` is a different key and is never treated as
    `version`.

    Returns a sorted list of dotted KEY/INDEX PATHS only. Values are never
    returned or logged (A1 §14 — report the path, never the value).
    """
    hits = set()

    def walk(n, path):
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(k, str):
                    key_path = path + (k,)
                    if k == "version":
                        allowed = (allow_pipeline_version
                                   and key_path == _ALLOWED_VERSION_PATH)
                        if not allowed:
                            hits.add(_render_version_path(key_path))
                    walk(v, key_path)
                else:
                    walk(v, path)
        elif isinstance(n, (list, tuple)):
            for i, v in enumerate(n):
                walk(v, path + (i,))

    walk(node, ())
    return sorted(hits)

# ---------------------------------------------------------------------------
# Internal path / host family detection (A1 §14)
# ---------------------------------------------------------------------------

# Generic Windows absolute path: a single drive letter + ':' + slash, NOT
# preceded by another letter. The negative lookbehind excludes URL schemes
# ("https://" — the 's:' is preceded by 't'), which are legitimate public
# values (source feed URLs). This avoids the naive `[A-Za-z]:/` match that
# produced tens of thousands of false positives on URLs (A1 §2.6).
_WIN_ABS_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")

# UNC path: two consecutive backslashes. Metadata strings (ids, names, URLs,
# timestamps, repo-relative paths) never legitimately contain a double
# backslash — matched structurally, never on a JSON-escaped blob.
_UNC_RE = re.compile(r"\\{2}")

# Path substring families. Scoped to metadata blocks only (never record
# payloads). These are genuine path fragments — never IP prefixes. Private /
# link-local hosts and addresses are handled separately by host_family_hits()
# (bounded `ipaddress` recognition), NOT by substring matching: a naive
# "192.168." / "169.254." / "127.0.0.1" / "::1" substring false-positives on
# unrelated decimal or hex text and cannot express whole CIDR ranges
# (10.0.0.0/8, 172.16.0.0/12, fc00::/7, fe80::/10).
_PATH_SUBSTRING_FAMILIES = (
    ("tmp_path",     "_tmp/"),
    ("backup_path",  "_backup"),
    ("file_uri",     "file://"),
    ("unix_home",    "/home/"),
    ("unix_users",   "/Users/"),
)

# `localhost` as a whole host token — bounded so it never matches inside a
# longer word and never fires on the public PLACSP feed hostnames.
_LOCALHOST_RE = re.compile(r"(?<![0-9A-Za-z.-])localhost(?![0-9A-Za-z.-])",
                           re.IGNORECASE)

# Candidate IPv4 dotted-quad, anchored so it is not part of a longer
# alphanumeric/dotted token (a Spanish budget "192.168.500,00" has only two
# dots and cannot match; a longer decimal run is excluded by the lookarounds).
# The token is still validated through `ipaddress` before it is ever reported.
_IPV4_TOKEN_RE = re.compile(
    r"(?<![0-9A-Za-z.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9A-Za-z.])"
)

# Candidate IPv6 token: at least two colon-separated hextet groups (so single
# `:` — RFC3339 time separators, URL host:port — cannot match) followed by
# `ipaddress` validation. Matches compressed forms (`::1`, `fe80::1`, `fc00::`)
# and bracketed URL hosts (`http://[fe80::1]/…`). Anything that is not a real
# IPv6 address (e.g. an RFC3339 "16:19:31" tail) fails validation and is
# dropped.
_IPV6_TOKEN_RE = re.compile(
    r"(?<![0-9A-Za-z:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![0-9A-Za-z:.])"
)


# Explicit contract networks for internal-host classification (A1 §14,
# p252 §10-§11). The classifier does NOT use `ipaddress.is_private`: that
# property is a broad, version-dependent superset that (in Python ≥3.12) folds
# in the documentation ranges 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 and
# 2001:db8::/32 — none of which A1 classifies as internal/private (they appear
# nowhere in the A1 forbidden set). Enumerating the exact networks the contract
# means makes classification deterministic and identical across Python versions,
# with no dependency added.
#
# Ordered most-specific-first so precedence is explicit: unspecified, then
# loopback, then link-local, then private. The listed networks do not overlap,
# but the order is stated rather than left to chance.
_IPV4_CONTRACT_NETWORKS = (
    ("unspecified_ipv4", ipaddress.ip_network("0.0.0.0/32")),
    ("loopback_ipv4",    ipaddress.ip_network("127.0.0.0/8")),
    ("linklocal_ipv4",   ipaddress.ip_network("169.254.0.0/16")),
    ("private_ipv4",     ipaddress.ip_network("10.0.0.0/8")),
    ("private_ipv4",     ipaddress.ip_network("172.16.0.0/12")),
    ("private_ipv4",     ipaddress.ip_network("192.168.0.0/16")),
)

_IPV6_CONTRACT_NETWORKS = (
    ("unspecified_ipv6", ipaddress.ip_network("::/128")),
    ("loopback_ipv6",    ipaddress.ip_network("::1/128")),
    ("linklocal_ipv6",   ipaddress.ip_network("fe80::/10")),
    ("private_ipv6",     ipaddress.ip_network("fc00::/7")),
)


def _ip_family(ip):
    """Stable family name for a private / loopback / link-local / unspecified IP
    address (`ipaddress.IPv4Address` or `IPv6Address`), or None for any address
    outside the explicit A1 §14 internal-host networks (global/public addresses
    and the documentation ranges, which are NOT contract-private).

    Membership is tested against the explicit contract networks in
    most-specific-first order — never against the generic `is_private` property.
    """
    networks = _IPV4_CONTRACT_NETWORKS if ip.version == 4 else _IPV6_CONTRACT_NETWORKS
    for fam, net in networks:
        if ip in net:
            return fam
    return None


def host_family_hits(value):
    """Return the set of internal/private host & IP family names in a string.

    Bounded recognition (A1 §14, p251 §7): candidate IPv4/IPv6 tokens are
    extracted with anchored patterns — never naive substring matching — and
    validated through the stdlib `ipaddress` module; only genuine private,
    loopback, link-local or unspecified addresses are reported. The literal host
    `localhost` is matched as a whole token. The public PLACSP feed hostnames
    parse as neither an IP nor `localhost`, so they never false-positive.

    Never returns the offending value itself (A1 §14 — report family only).
    """
    if not isinstance(value, str) or not value:
        return set()
    fams = set()
    if _LOCALHOST_RE.search(value):
        fams.add("localhost")
    for tok in _IPV4_TOKEN_RE.findall(value):
        try:
            fam = _ip_family(ipaddress.IPv4Address(tok))
        except ValueError:
            continue
        if fam:
            fams.add(fam)
    for tok in _IPV6_TOKEN_RE.findall(value):
        try:
            fam = _ip_family(ipaddress.IPv6Address(tok))
        except ValueError:
            continue
        if fam:
            fams.add(fam)
    return fams


def path_family_hits(value):
    """Return the set of internal path AND private-host family names in a string.

    Unions the path-fragment families (tmp/backup/file-uri/unix/Windows/UNC)
    with the bounded private-host families from host_family_hits(). Never
    returns the offending value itself (A1 §14 — report family only).
    """
    if not isinstance(value, str) or not value:
        return set()
    fams = set()
    for fam, needle in _PATH_SUBSTRING_FAMILIES:
        if needle in value:
            fams.add(fam)
    if _WIN_ABS_RE.search(value):
        fams.add("windows_abs_path")
    if _UNC_RE.search(value):
        fams.add("unc_path")
    fams |= host_family_hits(value)
    return fams


# ---------------------------------------------------------------------------
# Canonical consumer record count (A1 §8.1, p254, corrected p254 corrections
# 01 and 02)
#
# app.js buildCanonicalRecords() is the published consumer-facing grouping: it
# answers "how many distinct records does the public UI actually render",
# which is a different question from build_index()'s merge-operation key
# (contract_folder_id > canonical_key > id > url — used only to decide what
# the merger overwrites or appends). compute_canonical_record_count()
# reproduces buildCanonicalRecords()'s exact grouping key so that
# counts.canonical_records is a truthful statement of the consumer view. It
# answers only the grouping question a count needs; it never selects a "best"
# record per group (that is app.js pickCanonicalEntry(), irrelevant to a
# count).
#
# Supported container + identity domain (exact JS semantics reproduced):
#   - the records container itself must be a JSON array / Python list — an
#     EMPTY list is the true zero-record case and returns 0; app.js calls
#     `.forEach()` directly on `records`, which has no defined behavior for a
#     non-array container, so a dict/tuple/string/int/None container is
#     malformed input, not an empty dataset, and must never silently count
#     as 0;
#   - every element of that list must be a dict/object;
#   - id/url, if JS-truthy, is a JSON scalar: str, bool, int, or float
#     (int/float share one numeric namespace, matching JS's single Number
#     type — 1 and 1.0 are the same key; bool is its own namespace, so
#     true != 1; str is its own namespace, so "1" != 1);
#   - the '__idx__N' fallback string shares the SAME string namespace as a
#     real string id/url, because app.js builds it by string concatenation
#     ('__idx__' + idx) — a real id/url equal to that literal string collides
#     with the fallback in app.js, and must collide here too.
# Outside that domain — a non-list container, a non-dict element, or a
# JS-truthy id/url that is a list/dict (JS Map keys objects by reference
# identity, unrecoverable from JSON structure) — compute_canonical_record_count()
# / canonical_record_identity() fail closed by raising
# UnsupportedCanonicalIdentityError rather than approximating.
# ---------------------------------------------------------------------------

def _is_js_truthy(value) -> bool:
    """Mimic JS truthiness for the scalar values app.js keys grouping on.

    Falsy in JS: undefined, null, false, NaN, 0 (incl. -0.0), "". Every other
    value — including any non-empty string, non-zero number, list or dict —
    is truthy (JS objects/arrays are truthy even when empty).
    """
    if value is None or value is False:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value != value:  # NaN
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value != ""
    return True


class UnsupportedCanonicalIdentityError(ValueError):
    """Raised when a record's app.js grouping key falls outside the exact
    JS-semantics domain this module can faithfully reproduce (p254 correction
    01) — a non-object record, or a JS-truthy `id`/`url` that is a list/dict.

    JS Map keys a list/dict value by object reference identity, which cannot
    be recovered from JSON structure: two structurally identical objects are
    distinct Map keys in JS, but indistinguishable once serialized. Raising
    here — instead of falling back to a structural JSON key — is a deliberate
    fail-closed choice: it is safer to reject the count than to silently
    assert a JavaScript identity relationship this module cannot verify.
    """


def _js_scalar_key_repr(value, index: int, field: str):
    """Hashable representation of a JS **scalar** Map key, or raise.

    JS has a single Number type, so 1 and 1.0 are the same Map key; int and
    float both normalize to a tagged float here to reproduce that. Booleans
    and strings keep their own tagged namespace so they never collide with a
    numeric value or each other (JS Map treats true and 1 as distinct keys).
    Raises UnsupportedCanonicalIdentityError for any non-scalar value — see
    that class's docstring for why this is fail-closed, not a fallback.
    """
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, str):
        return ("str", value)
    raise UnsupportedCanonicalIdentityError(
        "record at index %d: %s value of type %s is outside the supported "
        "public identity domain (JSON scalar id/url only)"
        % (index, field, type(value).__name__))


def canonical_record_identity(record, index: int):
    """Reproduce app.js buildCanonicalRecords()'s exact grouping key.

    `var key = r.id || r.url || ('__idx__' + idx);` — id wins if JS-truthy,
    else url if JS-truthy, else the string `'__idx__' + idx`. The fallback
    key MUST inhabit the same string-key namespace as a real string id/url:
    JS builds it via string concatenation, so a record with no id/url at
    index 0 and a record whose real id/url happens to equal the literal
    string "__idx__0" are the SAME Map key in app.js and collapse into one
    canonical group. Tagging the fallback ("idx", index) instead — a
    separate Python namespace with no JS analogue — would report that
    collision as two groups, silently understating the true collapse.

    A non-dict entry has no `.id`/`.url` to read; app.js's own behavior for
    such an entry (bracket access on a non-object) is not something this
    module can safely assert without running V8, so it fails closed rather
    than guessing (p254 correction 01, REQUIRED CORRECTION §4).
    """
    if not isinstance(record, dict):
        raise UnsupportedCanonicalIdentityError(
            "record at index %d is not an object" % index)
    id_val = record.get("id")
    if _is_js_truthy(id_val):
        return _js_scalar_key_repr(id_val, index, "id")
    url_val = record.get("url")
    if _is_js_truthy(url_val):
        return _js_scalar_key_repr(url_val, index, "url")
    return ("str", "__idx__%d" % index)


def compute_canonical_record_count(records) -> int:
    """The exact canonical consumer-view record count (A1 §8.1).

    Counts the number of distinct groups app.js buildCanonicalRecords() would
    produce over `records` — the number of rows the public UI actually
    renders, not build_index()'s merge-operation key. build_index() and this
    function intentionally answer different questions: build_index() decides
    what the merger overwrites or appends; this counts what the consumer
    displays. Pure, stdlib-only, deterministic, no I/O, no mutation.

    Raises UnsupportedCanonicalIdentityError (fail-closed, not caught here) if
    `records` itself is not a list, if any record is a non-object, or if any
    record has a JS-truthy id/url that is a list/dict — outside the
    exact-semantics domain this module can reproduce. A non-list `records`
    (dict, tuple, string, int, None, ...) is not app.js's empty-array case:
    app.js calls `.forEach()` directly on `records`, which throws for any
    non-array value rather than behaving as zero rows, so returning 0 here
    would misrepresent malformed input as a legitimate empty dataset. Only an
    actual empty list (`[]`) is the true zero-record case and returns 0.
    Callers that must publish a count rather than crash the process are
    expected to catch this explicitly; this module does not soften it.
    """
    if not isinstance(records, list):
        raise UnsupportedCanonicalIdentityError(
            "records container is not a list (got %s); app.js "
            "buildCanonicalRecords() calls .forEach() on an array and has no "
            "defined behavior for a non-array container" % type(records).__name__)
    seen = set()
    for index, record in enumerate(records):
        seen.add(canonical_record_identity(record, index))
    return len(seen)


def find_forbidden_paths(node):
    """Recursively walk a structure (dict keys + values, lists) collecting the
    set of internal path/host family names present in any string.

    Structural traversal — never serialize to a JSON blob first (that doubles
    every backslash and fabricates UNC matches, A1 §14). Values are never
    returned or logged; only family names are surfaced.
    """
    fams = set()

    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                walk(k)
                walk(v)
        elif isinstance(n, (list, tuple)):
            for v in n:
                walk(v)
        elif isinstance(n, str):
            fams.update(path_family_hits(n))

    walk(node)
    return sorted(fams)
