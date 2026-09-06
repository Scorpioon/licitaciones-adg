#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/test_public_projection.py  (ADG OPS / p285 / v0.7.4i)

Offline/synthetic regression suite for tools/public_projection.py
(WRKOPS t_20260905_adgops282, IB-3 real-input + inventory join correction;
inherits the p281 construct-only kernel suite unchanged; extended by
WRKOPS t_20260905_adgops283 for the restored per-record 64 KiB cap and the
generated_at_utc -> analysed_at source-semantic proof; extended by WRKOPS
t_20260906_adgops284 for the effective-final-record cap correction -- a
matched production record's pre-existing doc_intel now participates in cap
arithmetic, a cap rejection clears doc_intel record-wide, and the pure
apply_projection() patch-application helper is proven directly; extended by
WRKOPS t_20260906_adgops285 for the all-exit-path record cap correction --
the 64 KiB cap now fires identically whether the record ends in no CPV, a
malformed/short CPV, missing/ambiguous/cross-record evidence, or a missing
generated_at_utc, not only on the CPV-attach success path).

Standard-library only. No network. No file writes. Reads only the tracked
conformance fixture (tools/fixtures/doc_ref_conformance_v1.json) and the
public_projection / public_contract source text (for the static safety
scan). Every producer manifest and production monolith object used below is
a synthetic inline literal — never real feed data, never data/**, never the
real production monolith.

Run:
  python tools/test_public_projection.py [-v]

Final line:
  PUBLIC_PROJECTION TESTS: PASS (N cases)
  PUBLIC_PROJECTION TESTS: FAIL (N cases)
"""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.public_projection as ppj  # noqa: E402

FIXTURE_PATH = REPO_ROOT / "tools" / "fixtures" / "doc_ref_conformance_v1.json"

# Frozen by the Companion authority artifact
# (_wrkops/reports/ADGOPS_IB3_DOCREF_CONFORMANCE_AUTHORITY_v1.json). The
# tracked fixture must reproduce this hash exactly (WRKOPS 281 §3.1).
FROZEN_AUTHORITY_SHA256 = (
    "7eb8298e0ae878c399530e3c851424f4f3879cfc1a86dd3888f011f9a20370f1"
)


def _fixture_sha256() -> str:
    import hashlib
    return hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# A. fixture authority
# --------------------------------------------------------------------------- #

class AFixtureAuthorityTests(unittest.TestCase):

    def test_fixture_sha256_matches_frozen_authority(self):
        self.assertEqual(_fixture_sha256(), FROZEN_AUTHORITY_SHA256)

    def test_15_of_15_vectors_exact(self):
        data = _load_fixture()
        vectors = data["vectors"]
        self.assertEqual(len(vectors), 15)
        for v in vectors:
            got = ppj.mint_doc_ref(v["input"])
            if v["expect_mint"]:
                self.assertEqual(
                    got, v["expected_doc_ref"],
                    msg=f"vector {v['id']!r} minted {got!r}")
            else:
                self.assertIsNone(
                    got, msg=f"vector {v['id']!r} should mint nothing, got {got!r}")

    def test_positives_mint_exact_doc_ref(self):
        for v in _load_fixture()["vectors"]:
            if v["expect_mint"]:
                self.assertEqual(ppj.mint_doc_ref(v["input"]), v["expected_doc_ref"])

    def test_negatives_mint_none(self):
        for v in _load_fixture()["vectors"]:
            if not v["expect_mint"]:
                self.assertIsNone(ppj.mint_doc_ref(v["input"]))

    def test_repeated_evaluation_deterministic(self):
        for v in _load_fixture()["vectors"]:
            first = ppj.mint_doc_ref(v["input"])
            second = ppj.mint_doc_ref(v["input"])
            self.assertEqual(first, second)


# --------------------------------------------------------------------------- #
# B. producer contract
# --------------------------------------------------------------------------- #

EMPTY_MONOLITH = {"data": []}


class BProducerContractTests(unittest.TestCase):

    def test_appendix_pcap_ppt_accepted(self):
        result = ppj.project_manifest({
            "schema": "appendix_pcap_ppt/1",
            "production_write_performed": False,
            "records": [],
        }, EMPTY_MONOLITH)
        self.assertTrue(result["accepted"])
        self.assertIsNone(result["rejected_reason"])

    def test_appendix_1_rejected(self):
        result = ppj.project_manifest({
            "schema": "appendix/1",
            "production_write_performed": False,
            "records": [],
        }, EMPTY_MONOLITH)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "unsupported_producer_schema")

    def test_unknown_schema_rejected(self):
        result = ppj.project_manifest({
            "schema": "feedxml_probe/1",
            "production_write_performed": False,
            "records": [],
        }, EMPTY_MONOLITH)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "unknown_producer_schema")

    def test_docread_1_not_yet_supported_rejected(self):
        result = ppj.project_manifest({
            "schema": "docread/1",
            "production_write_performed": False,
            "records": [],
        }, EMPTY_MONOLITH)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "unknown_producer_schema")

    def test_production_write_performed_true_rejected(self):
        result = ppj.project_manifest({
            "schema": "appendix_pcap_ppt/1",
            "production_write_performed": True,
            "records": [],
        }, EMPTY_MONOLITH)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "production_write_performed_not_false")

    def test_production_write_performed_missing_rejected(self):
        result = ppj.project_manifest({
            "schema": "appendix_pcap_ppt/1",
            "records": [],
        }, EMPTY_MONOLITH)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "production_write_performed_not_false")

    def test_production_monolith_not_object_rejected(self):
        result = ppj.project_manifest({
            "schema": "appendix_pcap_ppt/1",
            "production_write_performed": False,
            "records": [],
        }, ["not", "a", "dict"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "production_monolith_not_an_object")

    def test_production_monolith_data_not_a_list_rejected(self):
        result = ppj.project_manifest({
            "schema": "appendix_pcap_ppt/1",
            "production_write_performed": False,
            "records": [],
        }, {"data": "nope"})
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "production_monolith_data_not_a_list")


# --------------------------------------------------------------------------- #
# Shared synthetic building blocks
# --------------------------------------------------------------------------- #

URL_A = "https://example.com/expediente/a"
URL_B = "https://example.com/expediente/b"
DOC_REF_A = ppj.mint_doc_ref(URL_A)
DOC_REF_B = ppj.mint_doc_ref(URL_B)


def analysed_candidate(doc_ref, codes=("12345678",), page=1, url=URL_A):
    return {
        "url": url,
        "state": "analysed",
        "analysed_at": "2026-09-05T10:00:00Z",
        "cpv_codes": list(codes),
        "cpv_evidence": [{"doc_ref": doc_ref, "page": page}],
    }


# --------------------------------------------------------------------------- #
# C. construct-only
# --------------------------------------------------------------------------- #

class CConstructOnlyTests(unittest.TestCase):

    def test_exact_allowed_keys(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A), DOC_REF_A)
        self.assertTrue(set(obj.keys()) <= set(ppj.DOC_INTEL_TOP_KEYS))
        field = obj["fields"][0]
        self.assertEqual(set(field.keys()), set(ppj.FIELD_KEYS))
        ev = field["evidence"][0]
        self.assertEqual(set(ev.keys()), set(ppj.EVIDENCE_KEYS))

    def test_injected_producer_keys_do_not_pass_through(self):
        candidate = analysed_candidate(DOC_REF_A)
        candidate.update({
            "excerpt": "some extracted prose that must never appear publicly",
            "final_url": "https://internal.example/redirect",
            "sha256": "deadbeef",
            "notice_id": "N-1",
        })
        obj = ppj.build_doc_intel(candidate, DOC_REF_A)
        serialized = json.dumps(obj)
        for forbidden in ("excerpt", "final_url", "sha256", "notice_id",
                          "some extracted prose", "internal.example", "deadbeef"):
            self.assertNotIn(forbidden, serialized)

    def test_no_arbitrary_prose_free_text(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A), DOC_REF_A)
        field = obj["fields"][0]
        self.assertEqual(field["type"], "code_list")
        for code in field["value"]:
            self.assertRegex(code, r"^[0-9]{8}(-[0-9])?$")

    def test_no_url_under_doc_intel(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A), DOC_REF_A)
        serialized = json.dumps(obj)
        self.assertNotIn("url", obj)
        self.assertNotIn("http://", serialized)
        self.assertNotIn("https://", serialized)

    def test_no_bare_version_key(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A), DOC_REF_A)

        def walk(node):
            if isinstance(node, dict):
                self.assertNotIn("version", node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(obj)


# --------------------------------------------------------------------------- #
# D. CPV
# --------------------------------------------------------------------------- #

class DCpvTests(unittest.TestCase):

    def test_valid_8_digit(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A, codes=("45233120",)), DOC_REF_A)
        self.assertEqual(obj["fields"][0]["value"], ["45233120"])

    def test_valid_check_digit(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A, codes=("45233120-3",)), DOC_REF_A)
        self.assertEqual(obj["fields"][0]["value"], ["45233120-3"])

    def test_invalid_short_capture_suppressed(self):
        candidate = {
            "url": URL_A,
            "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "cpv_codes": ["123456", "4523312"],  # 6 and 7 digits: too short
        }
        obj = ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertNotIn("fields", obj)

    def test_evidence_must_point_to_owning_document(self):
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.build_doc_intel(analysed_candidate(DOC_REF_B), DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "evidence_wrong_owning_document")

    def test_no_non_cpv_field_emitted(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA,
            "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "objeto",
                "type": "duration",
                "value": ["P30D"],
                "evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "field_not_cpv_only")


# --------------------------------------------------------------------------- #
# E. states
# --------------------------------------------------------------------------- #

class EStatesTests(unittest.TestCase):

    def test_valid_analysed(self):
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A), DOC_REF_A)
        self.assertEqual(obj["state"], "analysed")

    def test_valid_unavailable(self):
        candidate = {"url": URL_A, "state": "unavailable", "reason": "source_unreachable"}
        obj = ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertEqual(obj["state"], "unavailable")
        self.assertEqual(obj["reason"], "source_unreachable")

    def test_valid_stale(self):
        candidate = {"url": URL_A, "state": "stale", "analysed_at": "2026-08-01T00:00:00Z"}
        obj = ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertEqual(obj["state"], "stale")
        self.assertNotIn("fields", obj)

    def test_valid_link_checked(self):
        candidate = {"url": URL_A, "state": "link_checked",
                     "link_checked_at": "2026-09-05T09:00:00Z"}
        obj = ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertEqual(obj["state"], "link_checked")

    def test_undated_link_checked_rejected(self):
        candidate = {"url": URL_A, "state": "link_checked"}
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "undated_link_checked")

    def test_fields_outside_analysed_rejected(self):
        candidate = {
            "url": URL_A, "state": "unavailable", "reason": "source_unreachable",
            "cpv_codes": ["12345678"],
            "cpv_evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "fields_outside_analysed")

    def test_reason_outside_unavailable_rejected(self):
        candidate = dict(analysed_candidate(DOC_REF_A))
        candidate["reason"] = "source_unreachable"
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.build_doc_intel(candidate, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "reason_outside_unavailable")

    def test_stale_with_fields_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA,
            "state": "stale",
            "analysed_at": "2026-08-01T00:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "stale_carries_fields")


# --------------------------------------------------------------------------- #
# F. malformed / caps
# --------------------------------------------------------------------------- #

class FMalformedCapsTests(unittest.TestCase):

    def test_unknown_top_level_key_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "unavailable",
            "reason": "source_unreachable", "confidence": "high",
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "unknown_top_level_keys")

    def test_unknown_field_key_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
                "confidence": "high",
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "field_unknown_keys")

    def test_unknown_evidence_key_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [{"doc_ref": DOC_REF_A, "page": 1, "excerpt": "x"}],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "evidence_unknown_keys")

    def test_invalid_enum_state_rejected(self):
        bad = {"schema": ppj.DOC_INTEL_SCHEMA, "state": "parsed"}
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "invalid_state")

    def test_invalid_field_type_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "prose", "value": ["12345678"],
                "evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "field_invalid_type")

    def test_missing_required_member_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{"key": "cpv", "type": "code_list", "value": ["12345678"]}],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "field_unknown_keys")

    def test_malformed_timestamp_rejected(self):
        bad = {"schema": ppj.DOC_INTEL_SCHEMA, "state": "stale", "analysed_at": "not-a-date"}
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "analysed_at_required")

    def test_evidence_page_disorder_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [
                    {"doc_ref": DOC_REF_A, "page": 3},
                    {"doc_ref": DOC_REF_A, "page": 2},
                ],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "evidence_page_order")

    def test_dangling_wrong_document_evidence_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [{"doc_ref": DOC_REF_B, "page": 1}],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "evidence_wrong_owning_document")

    def test_more_than_30_fields_rejected(self):
        one_field = {
            "key": "cpv", "type": "code_list", "value": ["12345678"],
            "evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
        }
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [dict(one_field) for _ in range(31)],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "fields_count_out_of_range")

    def test_more_than_3_evidence_rejected(self):
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [
                    {"doc_ref": DOC_REF_A, "page": 1},
                    {"doc_ref": DOC_REF_A, "page": 2},
                    {"doc_ref": DOC_REF_A, "page": 3},
                    {"doc_ref": DOC_REF_A, "page": 4},
                ],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "evidence_count_out_of_range")

    def test_doc_intel_over_8kib_rejected_not_truncated(self):
        many_codes = ["12345678"] * 800  # forces serialized size past 8 KiB
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": many_codes,
                "evidence": [{"doc_ref": DOC_REF_A, "page": 1}],
            }],
        }
        serialized = json.dumps(bad, ensure_ascii=False, separators=(",", ":"))
        self.assertGreater(len(serialized.encode("utf-8")), ppj.MAX_DOCINTEL_BYTES)
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, DOC_REF_A)
        self.assertEqual(ctx.exception.reason, "docintel_size_cap_exceeded")

    def test_string_cap_exceeded_rejected_not_truncated(self):
        long_ref = "d-" + ("a" * 100)  # > 64 chars, used consistently
        bad = {
            "schema": ppj.DOC_INTEL_SCHEMA, "state": "analysed",
            "analysed_at": "2026-09-05T10:00:00Z",
            "fields": [{
                "key": "cpv", "type": "code_list", "value": ["12345678"],
                "evidence": [{"doc_ref": long_ref, "page": 1}],
            }],
        }
        with self.assertRaises(ppj.RejectedCandidate) as ctx:
            ppj.validate_doc_intel(bad, long_ref)
        self.assertEqual(ctx.exception.reason, "string_cap_exceeded")


# --------------------------------------------------------------------------- #
# G. determinism / idempotence
# --------------------------------------------------------------------------- #

class GDeterminismTests(unittest.TestCase):

    def test_two_equal_runs_byte_identical(self):
        c1 = analysed_candidate(DOC_REF_A)
        c2 = analysed_candidate(DOC_REF_A)
        o1 = ppj.build_doc_intel(c1, DOC_REF_A)
        o2 = ppj.build_doc_intel(c2, DOC_REF_A)
        s1 = json.dumps(o1, ensure_ascii=False, separators=(",", ":"))
        s2 = json.dumps(o2, ensure_ascii=False, separators=(",", ":"))
        self.assertEqual(s1, s2)

    def test_reproject_already_projected_synthetic_input_byte_identical(self):
        # "Re-projecting" an already-valid public DocIntel object must be a
        # no-op: validate_doc_intel neither mutates nor rejects a conformant
        # object it is handed a second time.
        obj = ppj.build_doc_intel(analysed_candidate(DOC_REF_A), DOC_REF_A)
        before = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        ppj.validate_doc_intel(obj, DOC_REF_A)
        ppj.validate_doc_intel(obj, DOC_REF_A)
        after = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        self.assertEqual(before, after)


# --------------------------------------------------------------------------- #
# H. safety
# --------------------------------------------------------------------------- #

class HSafetyTests(unittest.TestCase):

    def test_no_network_capability(self):
        src = (REPO_ROOT / "tools" / "public_projection.py").read_text(encoding="utf-8")
        for forbidden in ("socket", "urllib.request", "http.client",
                          "requests", "ftplib", "smtplib"):
            self.assertNotIn(forbidden, src)

    def test_no_raw_text_input_mode(self):
        src = (REPO_ROOT / "tools" / "public_projection.py").read_text(encoding="utf-8")
        for forbidden in ("open(", "argparse", "subprocess", "os.system"):
            self.assertNotIn(forbidden, src)

    def test_no_local_input_root_disallowed_paths_are_synthetic_only(self):
        # The module performs no filesystem or network I/O at all (proven
        # above), so it has no local-input-root concept to disallow; every
        # code/URL path exercised by this suite is a synthetic in-memory
        # literal, never a real filesystem or network path.
        for v in _load_fixture()["vectors"]:
            self.assertIsInstance(v["input"], (str, type(None)))

    def test_no_wall_clock_call(self):
        # p273 v0.3 §13: "The projector never calls the clock itself."
        # WRKOPS t_20260905_adgops283 item J: static source assertion.
        src = (REPO_ROOT / "tools" / "public_projection.py").read_text(encoding="utf-8")
        for forbidden in ("datetime.now(", "time.time(", ".utcnow(", "import time"):
            self.assertNotIn(forbidden, src)


# --------------------------------------------------------------------------- #
# I. real-input / production join (WRKOPS t_20260905_adgops282 §8)
#
# Synthetic inline objects only, shaped like the ACTUAL
# appendix_pcap_ppt/1 producer manifest (tools/pcap_ppt_appendix_extractor.py
# :519-535, 736-750) and the ACTUAL production monolith inventory
# (fetch_licitaciones.py:673-719, 1880-1913). No new fixture files.
# --------------------------------------------------------------------------- #

URL_PROD_A = "https://example.com/expediente/a"
URL_PROD_A2 = "https://example.com/expediente/a2"
URL_PROD_B = "https://example.com/expediente/b"

PRODUCTION_MONOLITH = {
    "data": [
        {
            "canonical_key": "CK-1",
            "titol": "Record one",
            "documents": [
                {"url": URL_PROD_A, "title": "Doc A"},
                {"url": URL_PROD_A2, "title": "Doc A2"},
            ],
        },
        {
            "canonical_key": "CK-2",
            "titol": "Record two",
            "documents": [
                {"url": URL_PROD_B, "title": "Doc B"},
            ],
        },
    ],
}

DUPLICATE_CANONICAL_KEY_MONOLITH = {
    "data": [
        {"canonical_key": "CK-DUP", "documents": [{"url": "https://example.com/expediente/x"}]},
        {"canonical_key": "CK-DUP", "documents": [{"url": "https://example.com/expediente/y"}]},
    ],
}

AMBIGUOUS_DOCUMENT_MONOLITH = {
    "data": [
        {
            "canonical_key": "CK-AMB",
            "documents": [
                {"url": "https://example.com/expediente/dup"},
                {"url": "https://example.com/expediente/dup"},
            ],
        },
    ],
}


def producer_manifest(records, generated_at_utc="2026-09-05T10:00:00Z"):
    return {
        "schema": "appendix_pcap_ppt/1",
        "production_write_performed": False,
        "generated_at_utc": generated_at_utc,
        "records": records,
    }


def cpv_record(canonical_key, code="12345678", source_url=URL_PROD_A, page=1, evidence_extra=None):
    evidence = {"source_url": source_url, "page": page}
    if evidence_extra:
        evidence.update(evidence_extra)
    return {
        "canonical_key": canonical_key,
        "fields": {
            "cpv": {"value": code, "evidence": [evidence]},
        },
    }


class IRealInputJoinTests(unittest.TestCase):

    # 1. actual-shape appendix_pcap_ppt/1 accepted
    def test_actual_shape_manifest_accepted(self):
        manifest = producer_manifest([cpv_record("CK-1")], generated_at_utc="2026-09-05T10:00:00.123456+00:00")
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        self.assertTrue(result["accepted"])
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        doc_a = next(d for d in rec["documents"] if d["url"] == URL_PROD_A)
        self.assertEqual(doc_a["doc_intel"]["analysed_at"], "2026-09-05T10:00:00Z")

    # 2. appendix/1 rejected -- see BProducerContractTests.test_appendix_1_rejected

    # 3. production_write_performed true/missing rejected -- see
    #    BProducerContractTests.test_production_write_performed_true_rejected /
    #    test_production_write_performed_missing_rejected

    # 4. exact producer-record -> production-record join
    # 11. CPV field lands on evidence-named document, not another document in record
    def test_record_join_exact_and_field_lands_on_named_document_only(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["canonical_key"], "CK-1")
        self.assertIsNone(rec["rejected_reason"])
        doc_a = next(d for d in rec["documents"] if d["url"] == URL_PROD_A)
        doc_a2 = next(d for d in rec["documents"] if d["url"] == URL_PROD_A2)
        self.assertIsNotNone(doc_a["doc_intel"])
        self.assertEqual(doc_a["doc_intel"]["fields"][0]["value"], ["12345678"])
        self.assertIsNone(doc_a2["doc_intel"])
        self.assertIsNotNone(doc_a2["doc_ref"])  # inventory still minted

    # 5. missing record join rejects
    def test_record_join_missing(self):
        manifest = producer_manifest([cpv_record("CK-NOPE")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "production_record_missing")
        self.assertEqual(rec["documents"], [])

    # 6. ambiguous record join rejects
    def test_record_join_ambiguous(self):
        manifest = producer_manifest([cpv_record("CK-DUP", source_url="https://example.com/expediente/x")])
        result = ppj.project_manifest(manifest, DUPLICATE_CANONICAL_KEY_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "production_record_ambiguous")
        self.assertEqual(rec["documents"], [])

    # 7. exact evidence -> production documents[] join
    def test_document_join_exact(self):
        manifest = producer_manifest([cpv_record("CK-1", source_url=URL_PROD_A2)])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        doc_a2 = next(d for d in rec["documents"] if d["url"] == URL_PROD_A2)
        self.assertIsNotNone(doc_a2["doc_intel"])

    # 8. missing document join rejects field
    def test_document_join_missing(self):
        manifest = producer_manifest([cpv_record("CK-1", source_url="https://example.com/expediente/nowhere")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "evidence_document_missing")
        self.assertEqual(len(rec["documents"]), 2)
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))
        self.assertTrue(all(d["doc_ref"] is not None for d in rec["documents"]))

    # 9. ambiguous document join rejects field
    def test_document_join_ambiguous(self):
        manifest = producer_manifest([
            cpv_record("CK-AMB", source_url="https://example.com/expediente/dup")
        ])
        result = ppj.project_manifest(manifest, AMBIGUOUS_DOCUMENT_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "evidence_document_ambiguous")
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))

    # 10. cross-record evidence rejects
    def test_document_join_cross_record_rejected(self):
        manifest = producer_manifest([cpv_record("CK-1", source_url=URL_PROD_B)])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "evidence_cross_record")
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))

    # 12. doc_ref minted from production documents[].url only
    def test_doc_ref_minted_from_production_url_only(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        doc_a = next(d for d in rec["documents"] if d["url"] == URL_PROD_A)
        self.assertEqual(doc_a["doc_ref"], ppj.mint_doc_ref(URL_PROD_A))

    # 13. producer final_url cannot influence doc_ref
    def test_final_url_cannot_influence_doc_ref(self):
        manifest = producer_manifest([
            cpv_record("CK-1", evidence_extra={"final_url": "https://attacker.example/evil"})
        ])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        doc_a = next(d for d in rec["documents"] if d["url"] == URL_PROD_A)
        self.assertEqual(doc_a["doc_ref"], ppj.mint_doc_ref(URL_PROD_A))
        self.assertNotEqual(doc_a["doc_ref"], ppj.mint_doc_ref("https://attacker.example/evil"))

    # 14. producer internal IDs never appear under doc_intel
    # 15. excerpt/heading/value-window/hash never cross
    def test_producer_internal_identifiers_excluded_from_doc_intel(self):
        manifest = producer_manifest([
            cpv_record("CK-1", evidence_extra={
                "doc_sha256": "deadbeef",
                "notice_id": "N-1",
                "canonical_key": "CK-1",
                "excerpt": "some extracted prose that must never appear publicly",
                "heading": "CPV",
                "extraction_method": "regex",
            })
        ])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        doc_a = next(d for d in rec["documents"] if d["url"] == URL_PROD_A)
        serialized = json.dumps(doc_a["doc_intel"])
        for forbidden in ("deadbeef", "N-1", "some extracted prose", "notice_id",
                          "doc_sha256", "excerpt", "heading", "canonical_key"):
            self.assertNotIn(forbidden, serialized)

    # 16. invalid CPV suppresses field
    def test_invalid_short_cpv_suppressed(self):
        manifest = producer_manifest([cpv_record("CK-1", code="1234567")])  # 7 digits
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))
        self.assertTrue(all(d["doc_ref"] is not None for d in rec["documents"]))

    # 17. unrelated production record keys structurally unchanged
    # 18. unrelated existing documents[] keys unchanged
    def test_unrelated_production_keys_untouched(self):
        monolith = json.loads(json.dumps(PRODUCTION_MONOLITH))  # deep copy for mutation-safety check
        manifest = producer_manifest([cpv_record("CK-1")])
        ppj.project_manifest(manifest, monolith)
        self.assertEqual(monolith, PRODUCTION_MONOLITH)

    # 19. second projection byte-identical/idempotent
    def test_second_projection_byte_identical(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        r1 = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        r2 = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        self.assertEqual(json.dumps(r1, sort_keys=True), json.dumps(r2, sort_keys=True))

    # 20. same inputs produce byte-identical output
    def test_fresh_equal_inputs_produce_byte_identical_output(self):
        r1 = ppj.project_manifest(producer_manifest([cpv_record("CK-1")]), PRODUCTION_MONOLITH)
        r2 = ppj.project_manifest(producer_manifest([cpv_record("CK-1")]), PRODUCTION_MONOLITH)
        self.assertEqual(json.dumps(r1, sort_keys=True), json.dumps(r2, sort_keys=True))

    # 21. fixture authority remains byte-identical -- see
    #     AFixtureAuthorityTests.test_fixture_sha256_matches_frozen_authority

    # 22. old projection-kernel construct-only/state/cap/malformed tests still
    #     pass -- see classes C-H (unchanged by this task's correction)

    # Additional coverage for this task's own new code paths.
    def test_missing_generated_at_utc_suppresses_cpv(self):
        manifest = producer_manifest([cpv_record("CK-1")], generated_at_utc=None)
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "producer_generated_at_missing")
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))

    def test_malformed_cpv_evidence_shape_suppresses_field(self):
        rec_in = cpv_record("CK-1")
        rec_in["fields"]["cpv"]["evidence"] = []
        manifest = producer_manifest([rec_in])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))

    def test_no_cpv_field_present_is_not_a_rejection(self):
        manifest = producer_manifest([{"canonical_key": "CK-1"}])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        self.assertEqual(len(rec["documents"]), 2)
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))


# --------------------------------------------------------------------------- #
# Effective-final-record cap fixtures (WRKOPS t_20260906_adgops284 §7)
#
# This fixed doc_intel shape (analysed, single evidence entry, standard
# 34-char doc_ref, the "2026-09-05T10:00:00Z" analysed_at literal used
# throughout this suite, page 1) serializes to an exact, deterministic byte
# count: 218 + 11*n_codes for n_codes >= 1 identical 8-digit CPV codes (the
# n_codes=700 case below is independently confirmed under the 8 KiB
# per-document cap, matching the pre-existing JRecordCapAndAnalysedAtTests
# sizing proof this fixture block extends).
# --------------------------------------------------------------------------- #

def _preexisting_docs_totaling(total_bytes, prefix, max_count=50):
    """Builds distinct pre-existing production documents, each carrying a
    valid analysed doc_intel comfortably under the 8 KiB per-document cap,
    whose doc_intel byte sizes sum to EXACTLY `total_bytes`. Not every
    (total_bytes, document-count) pair is reachable by this fixed shape (its
    serialized size is always 218 + 11*n_codes), so this searches for a
    feasible document count itself rather than assuming one, then
    re-measures the real serialized output to confirm the target was hit
    exactly -- programmatic construction of exact-threshold synthetic
    vectors, per WRKOPS t_20260906_adgops284 §7 item 3."""
    base, per_code, per_doc_cap_codes = 218, 11, 700  # 700 codes = 7,918 B, well under 8 KiB
    for count in range(1, max_count):
        remainder = total_bytes - count * base
        if remainder < count or remainder % per_code != 0:
            continue
        total_codes = remainder // per_code
        if not (count <= total_codes <= count * per_doc_cap_codes):
            continue
        codes_each, extra = divmod(total_codes, count)
        docs = []
        for i in range(count):
            n = codes_each + (1 if i < extra else 0)
            url = f"https://example.com/expediente/{prefix}-{i}"
            doc_ref = ppj.mint_doc_ref(url)
            di = ppj.build_doc_intel(
                analysed_candidate(doc_ref, codes=("12345678",) * n, url=url), doc_ref)
            docs.append({"url": url, "title": f"pre-existing {i}", "doc_intel": di})
        actual_total = sum(
            len(json.dumps(d["doc_intel"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            for d in docs)
        if actual_total != total_bytes:
            continue  # pragma: no cover -- defensive; formula is exact
        return docs
    raise AssertionError(f"no feasible pre-existing document split for total_bytes={total_bytes}")


def _nine_preexisting_over_cap_docs(prefix="over-cap"):
    """Reproduces the OPERATOR synthetic probe's exact scenario (handoff
    §binding-defect): nine individually-valid pre-existing doc_intel objects,
    each 700 CPV codes / 7,918 bytes (independently under the 8 KiB
    per-document cap), summing to 71,262 bytes -- over the 64 KiB (65,536
    byte) per-record cap on their own, before this run adds anything."""
    docs = []
    for i in range(9):
        url = f"https://example.com/expediente/{prefix}-{i}"
        doc_ref = ppj.mint_doc_ref(url)
        di = ppj.build_doc_intel(
            analysed_candidate(doc_ref, codes=("12345678",) * 700, url=url), doc_ref)
        docs.append({"url": url, "title": f"pre-existing {i}", "doc_intel": di})
    return docs


# --------------------------------------------------------------------------- #
# J. per-record 64 KiB cap / analysed_at source semantics
# (WRKOPS t_20260905_adgops283 §6, items A-J)
#
# G, H are already covered and are not duplicated here:
#   G. generated_at_utc valid => analysed_at exactly normalized -- see
#      IRealInputJoinTests.test_actual_shape_manifest_accepted
#   H. missing generated_at_utc => suppressed, no invented time -- see
#      IRealInputJoinTests.test_missing_generated_at_utc_suppresses_cpv
#   J. static no-wall-clock-call assertion -- see
#      HSafetyTests.test_no_wall_clock_call
# --------------------------------------------------------------------------- #

class JRecordCapAndAnalysedAtTests(unittest.TestCase):

    # A. per-record effective payload <= 64 KiB passes
    def test_effective_total_under_cap_passes(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        doc_a = next(d for d in rec["documents"] if d["url"] == URL_PROD_A)
        self.assertIsNotNone(doc_a["doc_intel"])
        total = ppj.compute_record_docintel_bytes(rec["documents"])
        self.assertGreater(total, 0)
        self.assertLessEqual(total, ppj.MAX_RECORD_DOCINTEL_BYTES)

    # C. cap counts PRE-EXISTING valid doc_intel objects in an
    # already-projected production record, not just the newly-added CPV
    def test_compute_record_bytes_sums_multiple_preexisting_objects_past_cap(self):
        # Nine independently-valid doc_intel objects, each individually well
        # under the 8 KiB per-document cap (700 CPV codes each serializes to
        # 218 + 11*700 = 7,918 bytes, computed from the fixed construct-only
        # shape build_doc_intel emits)...
        docs = []
        for i in range(9):
            url = f"https://example.com/expediente/multi-{i}"
            doc_ref = ppj.mint_doc_ref(url)
            di = ppj.build_doc_intel(
                analysed_candidate(doc_ref, codes=("12345678",) * 700, url=url), doc_ref)
            single = json.dumps(di, ensure_ascii=False, separators=(",", ":"))
            self.assertLess(len(single.encode("utf-8")), ppj.MAX_DOCINTEL_BYTES)
            docs.append({"url": url, "doc_ref": doc_ref, "doc_intel": di})
        # ...but summed across the record (9 * 7,918 = 71,262 bytes), the
        # effective total exceeds the 64 KiB (65,536 byte) per-record cap --
        # proving the function counts every object present, not just one.
        total = ppj.compute_record_docintel_bytes(docs)
        self.assertGreater(total, ppj.MAX_RECORD_DOCINTEL_BYTES)

    # B. >64 KiB effective record payload rejects DocIntel without truncation
    # D. inventory/doc_ref and unrelated document/record keys survive
    #    record-cap rejection
    def test_record_cap_rejects_without_truncation_and_preserves_inventory(self):
        # Drives the real join pipeline with the cap temporarily lowered so
        # the single CPV field this producer can add in one run already
        # exceeds it -- exercising the rejection wiring itself (not only the
        # summation helper above), fail-closed, never truncating.
        manifest = producer_manifest([cpv_record("CK-1")])
        original_cap = ppj.MAX_RECORD_DOCINTEL_BYTES
        ppj.MAX_RECORD_DOCINTEL_BYTES = 1
        try:
            result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        finally:
            ppj.MAX_RECORD_DOCINTEL_BYTES = original_cap
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(rec["canonical_key"], "CK-1")
        self.assertEqual(len(rec["documents"]), 2)
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))
        self.assertTrue(all(d["doc_ref"] is not None for d in rec["documents"]))
        serialized = json.dumps(result)
        self.assertNotIn("12345678", serialized)  # no leaked payload value

    # F. second projection after a cap rejection remains deterministic
    def test_record_cap_rejection_deterministic_across_runs(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        original_cap = ppj.MAX_RECORD_DOCINTEL_BYTES
        ppj.MAX_RECORD_DOCINTEL_BYTES = 1
        try:
            r1 = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
            r2 = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        finally:
            ppj.MAX_RECORD_DOCINTEL_BYTES = original_cap
        self.assertEqual(json.dumps(r1, sort_keys=True), json.dumps(r2, sort_keys=True))

    # E. second projection after an accepted record is byte-identical -- see
    #    IRealInputJoinTests.test_second_projection_byte_identical (same
    #    accepted-record scenario this class's cap tests reuse)

    # I. malformed generated_at_utc => no invented analysed_at / CPV
    # DocIntel suppressed
    def test_malformed_generated_at_utc_suppresses_cpv_no_invented_time(self):
        manifest = producer_manifest([cpv_record("CK-1")], generated_at_utc="not-a-timestamp")
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "producer_generated_at_missing")
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))
        self.assertTrue(all(d["doc_ref"] is not None for d in rec["documents"]))

    # ----------------------------------------------------------------- #
    # WRKOPS t_20260906_adgops284 §7 -- effective-final-record cap
    # correction. These replace the split proof's insufficiency (the old
    # probe only proved the internal patch structure was under cap, never
    # the effective final production record) with true end-to-end tests
    # driven through project_manifest() at the real 64 KiB constant, plus
    # apply_projection() proof of what the patch means once applied.
    # ----------------------------------------------------------------- #

    # 1. REAL 64 KiB CONSTANT -- no monkeypatch. Reproduces the OPERATOR
    # probe exactly: nine pre-existing 7,918-byte doc_intel objects (71,262
    # bytes total) already over cap before this run's own CPV field is
    # even considered.
    def test_real_cap_rejects_preexisting_over_cap_no_monkeypatch(self):
        target_url = "https://example.com/expediente/over-cap-target"
        monolith = {
            "data": [{
                "canonical_key": "CK-OVERCAP",
                "titol": "Record with nine pre-existing DocIntel objects",
                "documents": _nine_preexisting_over_cap_docs() + [
                    {"url": target_url, "title": "Target doc"},
                ],
            }],
        }
        preexisting_total = sum(
            len(json.dumps(d["doc_intel"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            for d in monolith["data"][0]["documents"] if d.get("doc_intel"))
        self.assertEqual(preexisting_total, 71262)
        self.assertGreater(preexisting_total, ppj.MAX_RECORD_DOCINTEL_BYTES)

        frozen = json.loads(json.dumps(monolith))
        manifest = producer_manifest([cpv_record("CK-OVERCAP", source_url=target_url)])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]

        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(ppj.compute_record_docintel_bytes(rec["documents"]), 0)
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))
        self.assertEqual(len(rec["documents"]), 10)
        self.assertTrue(all(d["doc_ref"] is not None for d in rec["documents"]))
        serialized = json.dumps(result)
        self.assertNotIn("12345678", serialized)  # no leaked payload value

        # patch application proves the effective final record: zero bytes,
        # every unrelated key preserved, input untouched.
        applied = ppj.apply_projection(monolith, result)
        applied_rec = applied["data"][0]
        self.assertEqual(ppj.compute_record_docintel_bytes(applied_rec["documents"]), 0)
        self.assertEqual(applied_rec["titol"], "Record with nine pre-existing DocIntel objects")
        for orig_doc, applied_doc in zip(monolith["data"][0]["documents"], applied_rec["documents"]):
            self.assertEqual(applied_doc["url"], orig_doc["url"])
            self.assertEqual(applied_doc["title"], orig_doc["title"])
        self.assertEqual(monolith, frozen)  # project_manifest never mutated production_monolith

    # 2. Under-cap pre-existing state: pre-existing doc_intel on another
    # document, plus this run's new CPV, stays <=64 KiB -- final state
    # preserves the pre-existing object and adds the evidence-named one.
    def test_preexisting_under_cap_preserved_alongside_new_field(self):
        pre_url = "https://example.com/expediente/under-cap-pre"
        target_url = "https://example.com/expediente/under-cap-target"
        pre_doc_ref = ppj.mint_doc_ref(pre_url)
        pre_doc_intel = ppj.build_doc_intel(analysed_candidate(pre_doc_ref, url=pre_url), pre_doc_ref)
        monolith = {
            "data": [{
                "canonical_key": "CK-UNDERCAP",
                "documents": [
                    {"url": pre_url, "doc_intel": pre_doc_intel},
                    {"url": target_url},
                ],
            }],
        }
        manifest = producer_manifest([cpv_record("CK-UNDERCAP", source_url=target_url)])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]

        self.assertIsNone(rec["rejected_reason"])
        pre_out = next(d for d in rec["documents"] if d["url"] == pre_url)
        target_out = next(d for d in rec["documents"] if d["url"] == target_url)
        self.assertEqual(
            json.dumps(pre_out["doc_intel"], sort_keys=True),
            json.dumps(pre_doc_intel, sort_keys=True))
        self.assertIsNotNone(target_out["doc_intel"])
        total = ppj.compute_record_docintel_bytes(rec["documents"])
        self.assertLessEqual(total, ppj.MAX_RECORD_DOCINTEL_BYTES)
        self.assertGreater(total, 0)

    # 3. Exact-threshold case: effective final bytes == 65536 passes;
    # one 11-byte quantum over rejects. Synthetic doc_intel sizes are
    # constructed programmatically to land exactly on the boundary.
    def test_effective_final_bytes_exact_threshold(self):
        target_url = "https://example.com/expediente/exact-target"
        target_doc_ref = ppj.mint_doc_ref(target_url)
        new_doc_intel = ppj.build_doc_intel(
            analysed_candidate(target_doc_ref, url=target_url), target_doc_ref)
        new_size = len(json.dumps(
            new_doc_intel, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

        preexisting_docs = _preexisting_docs_totaling(
            ppj.MAX_RECORD_DOCINTEL_BYTES - new_size, "exact")
        monolith = {
            "data": [{
                "canonical_key": "CK-EXACT",
                "documents": preexisting_docs + [{"url": target_url, "title": "target"}],
            }],
        }
        manifest = producer_manifest([cpv_record("CK-EXACT", source_url=target_url)])

        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        self.assertEqual(
            ppj.compute_record_docintel_bytes(rec["documents"]), ppj.MAX_RECORD_DOCINTEL_BYTES)

        # One more CPV code (+11 bytes, the smallest quantum this shape can
        # move by) on a pre-existing document pushes the effective final
        # total one byte-quantum past the cap.
        bumped_first = monolith["data"][0]["documents"][0]
        bumped_ref = ppj.mint_doc_ref(bumped_first["url"])
        bumped_codes = tuple(bumped_first["doc_intel"]["fields"][0]["value"]) + ("12345678",)
        monolith_over = json.loads(json.dumps(monolith))
        monolith_over["data"][0]["documents"][0]["doc_intel"] = ppj.build_doc_intel(
            analysed_candidate(bumped_ref, codes=bumped_codes, url=bumped_first["url"]), bumped_ref)

        result_over = ppj.project_manifest(manifest, monolith_over)
        rec_over = result_over["records"][0]
        self.assertEqual(rec_over["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(ppj.compute_record_docintel_bytes(rec_over["documents"]), 0)

    # 4. Cap counts replacement semantics correctly: if the evidence-named
    # target document already carries doc_intel, the effective final total
    # counts the proposed replacement once, never old+new.
    def test_replacement_counted_once_not_old_plus_new(self):
        target_url = "https://example.com/expediente/replace-target"
        target_doc_ref = ppj.mint_doc_ref(target_url)
        old_doc_intel = ppj.build_doc_intel(
            analysed_candidate(target_doc_ref, codes=("87654321",), url=target_url), target_doc_ref)
        old_size = len(json.dumps(
            old_doc_intel, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        monolith = {
            "data": [{
                "canonical_key": "CK-REPLACE",
                "documents": [{"url": target_url, "doc_intel": old_doc_intel}],
            }],
        }
        manifest = producer_manifest([cpv_record("CK-REPLACE", source_url=target_url)])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]

        self.assertIsNone(rec["rejected_reason"])
        target_out = next(d for d in rec["documents"] if d["url"] == target_url)
        new_size = len(json.dumps(
            target_out["doc_intel"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        total = ppj.compute_record_docintel_bytes(rec["documents"])
        self.assertEqual(total, new_size)
        self.assertNotEqual(total, old_size + new_size)
        # the replacement carries the NEW field's code, not the old one
        self.assertEqual(target_out["doc_intel"]["fields"][0]["value"], ["12345678"])

    # 5. Cap-rejection idempotence: re-applying the same projection to an
    # already cap-rejected effective-final monolith is byte-identical.
    def test_apply_projection_twice_on_cap_rejected_result_is_idempotent(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        original_cap = ppj.MAX_RECORD_DOCINTEL_BYTES
        ppj.MAX_RECORD_DOCINTEL_BYTES = 1
        try:
            result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        finally:
            ppj.MAX_RECORD_DOCINTEL_BYTES = original_cap
        self.assertEqual(result["records"][0]["rejected_reason"], "record_docintel_cap_exceeded")

        once = ppj.apply_projection(PRODUCTION_MONOLITH, result)
        twice = ppj.apply_projection(once, result)
        self.assertEqual(json.dumps(once, sort_keys=True), json.dumps(twice, sort_keys=True))


# --------------------------------------------------------------------------- #
# K. patch-application semantics (WRKOPS t_20260906_adgops284 §3/§7 items 6-7)
# --------------------------------------------------------------------------- #

def _diff_paths(before, after, path=()):
    """Yields path tuples where `before` and `after` differ, recursing into
    matching dict/list structure. Used to prove apply_projection() changes
    nothing outside documents[].doc_ref / documents[].doc_intel."""
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                yield path + (key,)
            else:
                yield from _diff_paths(before[key], after[key], path + (key,))
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            yield path + ("__len__",)
        for i, (b, a) in enumerate(zip(before, after)):
            yield from _diff_paths(b, a, path + (i,))
    else:
        if before != after:
            yield path


class KPatchApplicationTests(unittest.TestCase):

    # 6. Patch application surface: only documents[].doc_ref / doc_intel
    # paths may ever differ between input and applied output.
    def test_only_doc_ref_and_doc_intel_paths_change(self):
        monolith = json.loads(json.dumps(PRODUCTION_MONOLITH))
        monolith["data"][0]["meta"] = {"unrelated": "value", "nested": [1, 2, 3]}
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, monolith)
        applied = ppj.apply_projection(monolith, result)

        for diff_path in _diff_paths(monolith, applied):
            self.assertTrue(
                "doc_ref" in diff_path or "doc_intel" in diff_path,
                msg=f"unexpected changed path: {diff_path}")

        self.assertEqual(applied["data"][0]["meta"], {"unrelated": "value", "nested": [1, 2, 3]})
        self.assertEqual(applied["data"][0]["titol"], "Record one")
        self.assertEqual(applied["data"][1]["canonical_key"], "CK-2")

    # 7. apply_projection mutates neither input argument.
    def test_apply_projection_mutates_neither_argument(self):
        monolith = json.loads(json.dumps(PRODUCTION_MONOLITH))
        monolith_frozen = json.loads(json.dumps(monolith))
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, monolith)
        result_frozen = json.loads(json.dumps(result))

        ppj.apply_projection(monolith, result)

        self.assertEqual(monolith, monolith_frozen)
        self.assertEqual(result, result_frozen)

    def test_apply_projection_returns_new_object_not_same_reference(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        applied = ppj.apply_projection(PRODUCTION_MONOLITH, result)
        self.assertIsNot(applied, PRODUCTION_MONOLITH)
        self.assertIsNot(applied["data"], PRODUCTION_MONOLITH["data"])

    def test_apply_projection_sets_doc_ref_and_accepted_doc_intel(self):
        manifest = producer_manifest([cpv_record("CK-1")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        applied = ppj.apply_projection(PRODUCTION_MONOLITH, result)
        applied_doc_a = next(d for d in applied["data"][0]["documents"] if d["url"] == URL_PROD_A)
        self.assertEqual(applied_doc_a["doc_ref"], ppj.mint_doc_ref(URL_PROD_A))
        self.assertIsNotNone(applied_doc_a["doc_intel"])
        self.assertEqual(applied_doc_a["doc_intel"]["fields"][0]["value"], ["12345678"])


# --------------------------------------------------------------------------- #
# L. all-exit-path record cap correction (WRKOPS t_20260906_adgops285 §6)
#
# Every producer record that matches exactly one production record must
# enforce the 64 KiB per-record cap through ONE common finalization step,
# regardless of which pre-cap business outcome preceded it. These tests
# drive the real join pipeline at the REAL 64 KiB constant (no monkeypatch)
# against a production record already carrying nine pre-existing valid
# doc_intel objects (71,262 bytes -- from _nine_preexisting_over_cap_docs(),
# already proven over MAX_RECORD_DOCINTEL_BYTES by
# JRecordCapAndAnalysedAtTests.test_real_cap_rejects_preexisting_over_cap_no_monkeypatch),
# so the record is over cap before this run's own CPV outcome is even
# considered.
# --------------------------------------------------------------------------- #

def _over_cap_monolith_with_target(target_url, prefix):
    return {
        "data": [{
            "canonical_key": "CK-ALLEXIT",
            "titol": "Record with nine pre-existing over-cap DocIntel objects",
            "documents": _nine_preexisting_over_cap_docs(prefix=prefix) + [
                {"url": target_url, "title": "Target doc"},
            ],
        }],
    }


class LAllExitPathRecordCapTests(unittest.TestCase):

    # A. no CPV field at all in producer record -- cap must still fire.
    def test_no_cpv_field_cap_still_enforced(self):
        target_url = "https://example.com/expediente/allexit-a-target"
        monolith = _over_cap_monolith_with_target(target_url, prefix="a")
        manifest = producer_manifest([{"canonical_key": "CK-ALLEXIT"}])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(ppj.compute_record_docintel_bytes(rec["documents"]), 0)
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))
        self.assertTrue(all(d["doc_ref"] is not None for d in rec["documents"]))

        applied = ppj.apply_projection(monolith, result)
        self.assertEqual(
            ppj.compute_record_docintel_bytes(applied["data"][0]["documents"]), 0)

    # B. malformed/short CPV that produces no public field -- cap still
    # enforced (same pre-cap branch as A, reached via a different producer
    # shape: a present-but-unusable cpv field rather than none at all).
    def test_malformed_short_cpv_cap_still_enforced(self):
        target_url = "https://example.com/expediente/allexit-b-target"
        monolith = _over_cap_monolith_with_target(target_url, prefix="b")
        manifest = producer_manifest(
            [cpv_record("CK-ALLEXIT", code="1234567", source_url=target_url)])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(ppj.compute_record_docintel_bytes(rec["documents"]), 0)
        self.assertTrue(all(d["doc_intel"] is None for d in rec["documents"]))

    # C. evidence document missing -- cap enforced, cap reason dominates.
    def test_evidence_document_missing_cap_dominates(self):
        target_url = "https://example.com/expediente/allexit-c-target"
        monolith = _over_cap_monolith_with_target(target_url, prefix="c")
        manifest = producer_manifest([
            cpv_record("CK-ALLEXIT", source_url="https://example.com/expediente/allexit-c-nowhere")
        ])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(ppj.compute_record_docintel_bytes(rec["documents"]), 0)

    # D. missing generated_at_utc -- cap enforced, cap reason dominates.
    def test_missing_generated_at_utc_cap_dominates(self):
        target_url = "https://example.com/expediente/allexit-d-target"
        monolith = _over_cap_monolith_with_target(target_url, prefix="d")
        manifest = producer_manifest(
            [cpv_record("CK-ALLEXIT", source_url=target_url)], generated_at_utc=None)
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")
        self.assertEqual(ppj.compute_record_docintel_bytes(rec["documents"]), 0)

    # E. normal under-cap no-CPV record -- no new rejection; pre-existing
    # under-cap DocIntel preserved unchanged.
    def test_under_cap_no_cpv_preserves_preexisting(self):
        pre_url = "https://example.com/expediente/allexit-e-pre"
        pre_doc_ref = ppj.mint_doc_ref(pre_url)
        pre_doc_intel = ppj.build_doc_intel(analysed_candidate(pre_doc_ref, url=pre_url), pre_doc_ref)
        monolith = {
            "data": [{
                "canonical_key": "CK-ALLEXIT-E",
                "documents": [{"url": pre_url, "doc_intel": pre_doc_intel}],
            }],
        }
        manifest = producer_manifest([{"canonical_key": "CK-ALLEXIT-E"}])
        result = ppj.project_manifest(manifest, monolith)
        rec = result["records"][0]
        self.assertIsNone(rec["rejected_reason"])
        pre_out = next(d for d in rec["documents"] if d["url"] == pre_url)
        self.assertEqual(
            json.dumps(pre_out["doc_intel"], sort_keys=True),
            json.dumps(pre_doc_intel, sort_keys=True))

    # F. common finalizer keeps the prior non-cap rejection reason when the
    # effective final total stays <= 64 KiB.
    def test_under_cap_prior_rejection_reason_preserved(self):
        manifest = producer_manifest(
            [cpv_record("CK-1", source_url="https://example.com/expediente/nowhere")])
        result = ppj.project_manifest(manifest, PRODUCTION_MONOLITH)
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "evidence_document_missing")
        self.assertLessEqual(
            ppj.compute_record_docintel_bytes(rec["documents"]), ppj.MAX_RECORD_DOCINTEL_BYTES)

    # G. apply_projection after a cap-triggered early-path result (no CPV
    # branch): clears every effective doc_intel, preserves unrelated keys
    # and doc_ref inventory, mutates neither input, deterministic/idempotent.
    def test_apply_projection_after_early_path_cap_rejection(self):
        target_url = "https://example.com/expediente/allexit-g-target"
        monolith = _over_cap_monolith_with_target(target_url, prefix="g")
        frozen = json.loads(json.dumps(monolith))
        manifest = producer_manifest([{"canonical_key": "CK-ALLEXIT"}])
        result = ppj.project_manifest(manifest, monolith)
        result_frozen = json.loads(json.dumps(result))
        rec = result["records"][0]
        self.assertEqual(rec["rejected_reason"], "record_docintel_cap_exceeded")

        applied_once = ppj.apply_projection(monolith, result)
        applied_twice = ppj.apply_projection(applied_once, result)

        for applied in (applied_once, applied_twice):
            applied_docs = applied["data"][0]["documents"]
            self.assertEqual(ppj.compute_record_docintel_bytes(applied_docs), 0)
            self.assertTrue(all(d["doc_intel"] is None for d in applied_docs))
            self.assertTrue(all(d["doc_ref"] is not None for d in applied_docs))
            self.assertEqual(
                applied["data"][0]["titol"],
                "Record with nine pre-existing over-cap DocIntel objects")
            for orig_doc, applied_doc in zip(monolith["data"][0]["documents"], applied_docs):
                self.assertEqual(applied_doc["url"], orig_doc["url"])

        self.assertEqual(
            json.dumps(applied_once, sort_keys=True), json.dumps(applied_twice, sort_keys=True))
        self.assertEqual(monolith, frozen)  # project_manifest never mutated production_monolith
        self.assertEqual(result, result_frozen)  # apply_projection never mutated its result argument


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    n = result.testsRun
    passed = result.wasSuccessful()
    verdict = "PASS" if passed else "FAIL"
    print(f"PUBLIC_PROJECTION TESTS: {verdict} ({n} cases)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
