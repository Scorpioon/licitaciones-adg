#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/acquisition_staging.py
ADG OPS — P331-B15 D1/D4 acquisition-staging authority
(WRKOPS t_20261004_adgops335, OPERATOR DECISION ADDENDUM "D1 APPROVED").

Dedicated, private, acquisition-layer-ONLY persistence for a bounded
multi-page acquisition cycle that spans more than one scheduled run. Strictly
separate from the canonical internal-continuity state
(tools.scheduled_fetch_merge.load_internal_state/persist_internal_state,
state/licitaciones.json) -- never read by merge/lifecycle/canonicalization
code, and never a substitute for that fail-closed contract.

Staging absence or corruption is NEVER fatal here, unlike
load_internal_state()'s canonical-state contract: losing staged progress
only costs some additional scheduled runs' worth of re-walking already-
public feed pages from page 1 for the affected source(s) -- it is never a
correctness or duplicate-publication risk, because the separate
`acquisition_complete` signal and tools.scheduled_fetch_merge.run_live()'s
fail-closed publication gate are what actually prevent an incomplete
candidate from reaching production, not this module's own durability.

Owns exactly: cycle shape/validation, fresh-cycle construction, atomic local
load/write, and cycle rotation after a successful publish. Owns no fetch
policy, no HTTP, no dedup/merge precedence (that is fetch_licitaciones.py's
STATUS_RANK-based policy, applied by the caller before updating this
module's per-source records) -- this module is a dumb, validated state
container plus atomic I/O.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "adgops.acquisition_staging/1"


def _ts_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_sources(sources) -> dict:
    """Returns the deterministic {name: source_url_or_None} fingerprint this
    module binds staged per-source progress to (WRKOPS t_20261004_adgops335
    corrective C2). Accepts any of the three shapes callers actually use:
    a dict keyed by name with "url"-bearing entries (tools.public_contract.
    PUBLIC_SOURCES), a list of dicts with "name"/"url" keys
    (fetch_licitaciones.py's SOURCES/active_sources), or a bare list of name
    strings (tests only -- url fingerprint is then None, which still
    detects a name-set change but not a same-name URL drift)."""
    if isinstance(sources, dict):
        return {
            name: ((entry.get("url") if isinstance(entry, dict) else None))
            for name, entry in sources.items()
        }
    out = {}
    for s in sources:
        if isinstance(s, str):
            out[s] = None
        else:
            out[s["name"]] = s.get("url")
    return out


def new_cycle(sources) -> dict:
    """A fresh, empty acquisition cycle for exactly `sources` (see
    _normalize_sources() for accepted shapes). Each source's record carries
    `source_url`, the registry fingerprint stale/incompatible-cycle
    detection binds against (C2)."""
    by_name = _normalize_sources(sources)
    now = _ts_now()
    return {
        "schema": SCHEMA,
        "cycle_id": f"ACQ-{uuid.uuid4().hex}",
        "status": "IN_PROGRESS",
        "created_at": now,
        "updated_at": now,
        "attempt_count": 0,
        "sources": {
            name: {
                "source_url": url,
                "next_url": None,
                "exhausted": False,
                "pages_fetched_cycle": 0,
                "last_attempt_at": None,
                "last_attempt_status": "NOT_STARTED",
            }
            for name, url in by_name.items()
        },
        "data": [],
        "tombstones": [],
    }


def _is_valid_shape(staging, sources) -> bool:
    """Structural validation only -- never raises; returns False for
    anything load_or_new() should treat as 'start fresh' (malformed JSON,
    wrong schema, missing keys, a source-name set that no longer matches
    the authoritative registry, or -- C2 -- a source whose persisted
    `source_url` fingerprint no longer matches the active registry's URL
    for that same name, i.e. the human-visible source name is unchanged but
    its underlying feed URL drifted. Either case is stale/incompatible-
    cycle detection, never a partial per-source fixup."""
    by_name = _normalize_sources(sources)
    if not isinstance(staging, dict):
        return False
    if staging.get("schema") != SCHEMA:
        return False
    if not isinstance(staging.get("cycle_id"), str) or not staging["cycle_id"]:
        return False
    if not isinstance(staging.get("data"), list):
        return False
    if not isinstance(staging.get("tombstones"), list):
        return False
    recs = staging.get("sources")
    if not isinstance(recs, dict):
        return False
    if set(recs.keys()) != set(by_name.keys()):
        return False
    for name, rec in recs.items():
        if not isinstance(rec, dict):
            return False
        if not isinstance(rec.get("exhausted"), bool):
            return False
        next_url = rec.get("next_url")
        if next_url is not None and not isinstance(next_url, str):
            return False
        if rec.get("source_url") != by_name[name]:
            return False
    return True


def load_or_new(path: Path, sources):
    """Returns (staging_dict, started_fresh: bool, reason: str|None).

    Absent file, unreadable/malformed JSON, or an invalid/stale/
    registry-incompatible shape (including a same-name source_url drift,
    C2) all start a fresh cycle -- never fatal, unlike
    load_internal_state()'s canonical-state contract. `reason` is a short
    machine-readable label for the run's own diagnostics, None when an
    existing valid cycle was loaded unchanged."""
    if not path.exists():
        return new_cycle(sources), True, "ABSENT"
    try:
        raw = path.read_text(encoding="utf-8")
        staging = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return new_cycle(sources), True, "MALFORMED_JSON"
    if not _is_valid_shape(staging, sources):
        return new_cycle(sources), True, "INVALID_SHAPE_OR_REGISTRY_DRIFT"
    return staging, False, None


def all_sources_exhausted(staging: dict) -> bool:
    sources = staging.get("sources") or {}
    return bool(sources) and all(rec.get("exhausted") is True for rec in sources.values())


def write_atomic(path: Path, staging: dict) -> None:
    """Atomic local write: serialize to a sibling temp file, then
    os.replace() into place. A process death before the replace leaves the
    previously-persisted staging file exactly as it was -- never a
    half-written/corrupt file (Stage A-equivalent atomicity requirement for
    this acquisition-layer authority)."""
    staging["updated_at"] = _ts_now()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + f".tmp-{os.getpid()}")
    serialized = json.dumps(staging, ensure_ascii=False, indent=2)
    tmp_path.write_bytes(serialized.encode("utf-8"))
    os.replace(tmp_path, path)


def rotate(path: Path, sources) -> None:
    """Resets the staging file to a fresh, empty cycle. Call only AFTER a
    cycle's accumulated candidate has been successfully consumed into a
    completed, published merge (tools.scheduled_fetch_merge.run_live(),
    strictly after the public write succeeds) -- never from the fetch side,
    and never before a write is confirmed, so a failure between acquisition
    completion and successful publication leaves the staged cycle intact
    for the next run to retry the merge/publish step alone (no re-fetch)."""
    write_atomic(path, new_cycle(sources))
