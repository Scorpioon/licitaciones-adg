#!/usr/bin/env python3
"""
tools/run_receipt.py
ADG OPS — Prompt 324 Stage B / WRKOPS t_20260924_adgops324.

Pure serialization / exact-byte-hash / digest-sidecar helpers for the V2
scheduled-run receipt written by tools/scheduled_run_classify.py. Owns no
classification logic and no status taxonomy (Stage A/R1 report §19.5,
Stage B prompt §1.1): tools/scheduled_run_classify.py remains the single
receipt-finalization authority. This module is limited to:

  - canonical_json_bytes(): one deterministic UTF-8 byte serialization;
  - sha256_hex(): exact-byte SHA256 over those bytes;
  - receipt_filename(): collision-safe naming from run_number + run_attempt
    + a UTC timestamp suffix (Stage A/R1 report §10, Stage B prompt §5);
  - write_receipt(): binary write of the receipt bytes, then a sibling
    `<filename>.sha256` sidecar hashing that SAME bytes object -- never a
    re-read, never a second serialization (the exact-byte pattern Stage A
    report §5 / Stage B prompt §4 requires);
  - verify_receipt(): read a receipt + sidecar back from disk and confirm
    the sidecar digest matches a fresh hash of the file's actual bytes.

Standard-library only. No network, no classification, no side effects
beyond the two files write_receipt() is asked to write.
"""

import hashlib
import json
from pathlib import Path


def canonical_json_bytes(obj) -> bytes:
    """One deterministic UTF-8 byte serialization: sorted keys, explicit
    ensure_ascii=False, a single trailing newline. This exact bytes object
    is both what gets hashed and what gets written to disk -- it is never
    independently re-derived from a second serialization pass."""
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt_filename(run_number, run_attempt, timestamp: str) -> str:
    """Collision-safe receipt identity (Stage A/R1 report §10, Stage B
    prompt §5): run_number + run_attempt are the mandatory components (a
    manual re-run of the same run increments run_attempt, never
    run_number) -- the UTC timestamp suffix is retained for human
    sortability, but collision safety never depends on the timestamp
    alone."""
    run_number = str(run_number) if run_number not in (None, "") else "unknown"
    run_attempt = str(run_attempt) if run_attempt not in (None, "") else "unknown"
    return f"adgops_run_receipt_{run_number}-{run_attempt}-{timestamp}.json"


def write_receipt(receipt: dict, out_dir, filename: str) -> dict:
    """Write the receipt's exact bytes (binary mode) and a sibling
    `<filename>.sha256` sidecar hashing those SAME bytes -- never a
    pre-write text string subject to newline translation, never a second
    independent serialization, and never the receipt's own digest embedded
    inside itself (Stage A report §5 / Stage B prompt §4: the self-hash
    problem).

    Returns {"receipt_path", "sidecar_path", "bytes", "sha256"} (str paths).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(receipt)
    digest = sha256_hex(data)

    receipt_path = out_dir / filename
    sidecar_path = out_dir / f"{filename}.sha256"

    with open(receipt_path, "wb") as fh:
        fh.write(data)
    with open(sidecar_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{digest}  {filename}\n")

    return {
        "receipt_path": str(receipt_path),
        "sidecar_path": str(sidecar_path),
        "bytes": len(data),
        "sha256": digest,
    }


def verify_receipt(receipt_path, sidecar_path) -> bool:
    """Independently re-derive the receipt file's SHA256 from its on-disk
    bytes and compare it against the sidecar's recorded digest. Returns
    True iff they match -- the corruption/tampering-detection proof Stage B
    prompt §8 item 7 requires."""
    with open(receipt_path, "rb") as fh:
        data = fh.read()
    actual = sha256_hex(data)
    with open(sidecar_path, encoding="utf-8") as fh:
        sidecar_line = fh.readline().strip()
    recorded = sidecar_line.split()[0] if sidecar_line else ""
    return bool(recorded) and recorded == actual
