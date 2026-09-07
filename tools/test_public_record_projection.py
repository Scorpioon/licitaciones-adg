#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/test_public_record_projection.py  (ADG OPS / p289 / v0.7.4m)

Offline/synthetic regression suite for tools/public_record_projection.py
(WRKOPS t_20260907_adgops289, F-05 / DS-11B public record contract + public
record identity — PUBLIC_CANONICAL_TENDER domain, R2 correction).

Standard-library only. No network. No file writes. Every record object used
below is a synthetic inline literal — never real feed data, never
data/licitaciones.json.

Test numbering follows the R2 corrective-pass REQUIRED TEST CORRECTION /
ADDITIONS list (R2 prompt §8) exactly, items 1-20:
  IDENTITY (canonical-tender semantics)      1-13  -> IdentityTests
  STRIP (bookkeeping / allowlist contract)   14-18 -> StripTests
  CROSS-GATE                                 19-20 -> CrossGateTests
CROSS-GATE detail:
  19 (Prompt 287 null->absence) and 20-IB4 (DocIntel contract constants) —
      proven directly below via a lightweight import/contract check against
      the unmodified tools/public_projection.py and tools/public_contract.py
      modules.
  20-F-04 (F-04 untouched) and existing Fetcher regressions remaining
      present — proven by NON-MODIFICATION: this task did not touch
      .github/workflows/fetch.yml or tools/fetcher_fixture_regression.py, so
      their own existing, unmodified suites remain the proof; duplicating
      them here would not add coverage.
  No data mutation required by tests — satisfied by construction: every
      test in this file uses an inline synthetic record, never
      data/licitaciones.json or any path under data/.

Run:
  python tools/test_public_record_projection.py [-v]

Final line:
  PUBLIC_RECORD_PROJECTION TESTS: PASS (N cases)
  PUBLIC_RECORD_PROJECTION TESTS: FAIL (N cases)
"""

import copy
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.public_record_projection as prp  # noqa: E402


def sample_record(**overrides) -> dict:
    rec = {
        "id": "https://example.test/feed/12345",
        "canonical_key": "CK-STABLE-0001",
        "contract_folder_id": "CFID-STABLE-0001",
        "titol": "Sample tender title",
        "organisme": "Sample org",
        "url": "https://example.test/detail/1",
        "documents": [
            {"url": "https://example.test/doc/1", "doc_ref": "d-" + "a" * 32},
        ],
        # Internal bookkeeping families that must never survive projection.
        "action": "INJECTED_FROM_091",
        "merge_key": "https://example.test/feed/12345",
        "merge_key_source": "id",
        "merge_key_missing": False,
        "merge_action": "APPENDED",
        "merge_added_at": "2026-01-01T00:00:00Z",
        "merge_prompt": "091",
        "merge_source": "candidate",
        "delta_added_at": "2026-01-01T00:00:00Z",
        "delta_audit_prompt": "091",
        "delta_prompt": "091",
        "delta_reason": "backfill",
        "delta_source": "candidate",
        "delta_strategy": "append",
        "recovery_added_at": "2026-01-01T00:00:00Z",
        "recovery_bucket": "A",
        "recovery_operator_decision": "keep",
        "recovery_policy_version": "1",
        "recovery_prerequisite": "none",
        "recovery_prompt": "091",
        "recovery_reason": "manual",
        "recovery_source": "operator",
        "source_bucket_reason": "no_cfid",
        "source_gate_reason": "ok",
        "source_score": 0.9,
        "source_score_discs": 0.5,
        "source_score_kws": 0.4,
        "source_zip_name": "archive.zip",
        "enrichment_needed": False,
        "enrichment_preserved": True,
        "enrichment_version": "0.4.4r",
        "enrichment_rules": ["ENR_DISC_002"],
        "has_adjudicatari": True,
        "has_award_results": False,
        "has_disciplines": True,
        "has_documents": True,
        "has_historial": True,
        "has_kw": True,
        "has_rellevancia": True,
        "production_matched": True,
        "provenance_note": "note",
        "provenance_note_delta": "note-delta",
        "source_merge_class": "PRODUCTION_ONLY_PRESERVED",
        "lifecycle_category": "CLEAR_AWARDED",
        "active_opportunity_eligible": False,
        "lifecycle_review_required": False,
        "production_only_preserved": True,
        "dry_run_mode": True,
        "dry_run_note": "note",
        "dry_run_lifecycle_note": "note",
        "dry_run_recommended_status": "open",
        "dry_run_rs_criteria": ["(a) x"],
        "status_provenance": "source",
        "winner_provenance": "source",
        # Ambiguous field, deliberately NOT in the allowlist.
        "titulo": "Sample tender title (es)",
    }
    rec.update(overrides)
    return rec


BOOKKEEPING_FAMILY_KEYS = [
    "action", "merge_key", "merge_key_source", "merge_key_missing",
    "merge_action", "merge_added_at", "merge_prompt", "merge_source",
    "delta_added_at", "delta_audit_prompt", "delta_prompt", "delta_reason",
    "delta_source", "delta_strategy", "recovery_added_at", "recovery_bucket",
    "recovery_operator_decision", "recovery_policy_version",
    "recovery_prerequisite", "recovery_prompt", "recovery_reason",
    "recovery_source", "source_bucket_reason", "source_gate_reason",
    "source_score", "source_score_discs", "source_score_kws",
    "source_zip_name", "enrichment_needed", "enrichment_preserved",
    "enrichment_version", "enrichment_rules", "has_adjudicatari",
    "has_award_results", "has_disciplines", "has_documents", "has_historial",
    "has_kw", "has_rellevancia", "production_matched", "provenance_note",
    "provenance_note_delta", "source_merge_class", "lifecycle_category",
    "active_opportunity_eligible", "lifecycle_review_required",
    "production_only_preserved", "dry_run_mode", "dry_run_note",
    "dry_run_lifecycle_note", "dry_run_recommended_status",
    "dry_run_rs_criteria", "status_provenance", "winner_provenance",
]


# --------------------------------------------------------------------------- #
# IDENTITY 1-13 (PUBLIC_CANONICAL_TENDER semantics, R2 §8)
# --------------------------------------------------------------------------- #

class IdentityTests(unittest.TestCase):

    def test_01_same_id_no_canonical_key_stable_across_repeated_projection(self):
        rec = sample_record(canonical_key=None, contract_folder_id=None)
        out1 = prp.project_public_record(rec)
        out2 = prp.project_public_record(rec)
        self.assertEqual(out1["public_id"], out2["public_id"])

    def test_02_same_id_one_with_ck_one_without_same_public_id(self):
        shared_id = "https://example.test/feed/PAIR-0001"
        a = prp.project_public_record(sample_record(id=shared_id, canonical_key="CK-PAIRED"))
        b = prp.project_public_record(
            sample_record(id=shared_id, canonical_key=None, contract_folder_id=None)
        )
        self.assertEqual(a["public_id"], b["public_id"])

    def test_03_same_id_different_canonical_key_values_same_public_id(self):
        # canonical_key is explicitly NOT part of public identity (R2 §2).
        shared_id = "https://example.test/feed/PAIR-0002"
        a = prp.project_public_record(sample_record(id=shared_id, canonical_key="CK-A"))
        b = prp.project_public_record(sample_record(id=shared_id, canonical_key="CK-B"))
        self.assertEqual(a["public_id"], b["public_id"])

    def test_04_distinct_id_values_distinct_public_id(self):
        a = prp.project_public_record(sample_record(id="https://example.test/feed/AAAA"))
        b = prp.project_public_record(sample_record(id="https://example.test/feed/BBBB"))
        self.assertNotEqual(a["public_id"], b["public_id"])

    def test_05_missing_id_fails_closed_even_with_canonical_key(self):
        rec = sample_record(id=None)
        self.assertTrue(rec.get("canonical_key"))  # canonical_key present but must not rescue anchor
        with self.assertRaises(prp.RejectedRecord) as cm:
            prp.project_public_record(rec)
        self.assertEqual(cm.exception.reason, "public_id_anchor_missing_or_invalid")

    def test_06_blank_non_string_id_fails_closed(self):
        for bad_id in ("", "   ", 12345, [], {}):
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(prp.RejectedRecord) as cm:
                    prp.project_public_record(sample_record(id=bad_id))
                self.assertEqual(cm.exception.reason, "public_id_anchor_missing_or_invalid")

    def test_07_exact_format_and_prefix(self):
        out = prp.project_public_record(sample_record())
        pid = out["public_id"]
        self.assertTrue(pid.startswith(prp.PUBLIC_ID_PREFIX))
        hexpart = pid[len(prp.PUBLIC_ID_PREFIX):]
        self.assertEqual(len(hexpart), prp.PUBLIC_ID_HEX_LEN)
        int(hexpart, 16)  # raises ValueError if not valid lowercase hex
        self.assertEqual(hexpart, hexpart.lower())

    def test_08_public_id_stable_deterministic(self):
        rec = sample_record()
        self.assertEqual(
            prp.mint_public_id(prp.record_anchor(rec)),
            prp.mint_public_id(prp.record_anchor(rec)),
        )
        out1 = prp.project_public_record(rec)
        out2 = prp.project_public_record(rec)
        self.assertEqual(out1["public_id"], out2["public_id"])

    def test_09_batch_allows_repeated_public_id_same_anchor(self):
        shared_id = "https://example.test/feed/PAIR-0003"
        rec1 = sample_record(id=shared_id, canonical_key="CK-ONE", url="https://example.test/a")
        rec2 = sample_record(
            id=shared_id, canonical_key=None, contract_folder_id=None, url="https://example.test/b"
        )
        result = prp.project_public_records([rec1, rec2])
        self.assertTrue(result["accepted"])
        self.assertIsNone(result["rejected_reason"])
        self.assertEqual(len(result["records"]), 2)  # no dedupe / no cardinality change (R2 §4)
        self.assertEqual(result["records"][0]["public_id"], result["records"][1]["public_id"])

    def test_10_batch_fails_closed_different_anchor_same_public_id(self):
        # Narrow test seam (R2 §8 item 10): force a collision via a
        # monkeypatched mint_public_id so the DIFFERENT-anchor fail-closed
        # path is exercised without weakening the real SHA-256 derivation
        # used by every other test in this file.
        original = prp.mint_public_id

        def forced_collision(anchor):
            if not isinstance(anchor, str) or not anchor.strip():
                return None
            return prp.PUBLIC_ID_PREFIX + "0" * prp.PUBLIC_ID_HEX_LEN

        prp.mint_public_id = forced_collision
        try:
            rec1 = sample_record(id="https://example.test/feed/CCCC")
            rec2 = sample_record(id="https://example.test/feed/DDDD")
            result = prp.project_public_records([rec1, rec2])
        finally:
            prp.mint_public_id = original

        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "duplicate_public_id")
        self.assertEqual(result["records"], [])

    def test_11_technical_id_fields_unchanged(self):
        rec = sample_record()
        out = prp.project_public_record(rec)
        self.assertEqual(out["canonical_key"], rec["canonical_key"])
        self.assertEqual(out["contract_folder_id"], rec["contract_folder_id"])
        self.assertEqual(out["id"], rec["id"])
        for technical in (out["canonical_key"], out["contract_folder_id"], out["id"]):
            self.assertNotEqual(out["public_id"], technical)

    def test_12_input_not_mutated(self):
        rec = sample_record()
        frozen = copy.deepcopy(rec)
        prp.project_public_record(rec)
        self.assertEqual(rec, frozen)

    def test_13_document_doc_ref_doc_intel_untouched(self):
        rec = sample_record()
        out = prp.project_public_record(rec)
        self.assertEqual(out["documents"], rec["documents"])
        self.assertEqual(out["documents"][0]["doc_ref"], rec["documents"][0]["doc_ref"])


# --------------------------------------------------------------------------- #
# STRIP 14-18 (bookkeeping / allowlist contract, preserved from first pass
# per R2 §7, plus the canonical `titulo` disposition confirmed by R1/R2)
# --------------------------------------------------------------------------- #

class StripTests(unittest.TestCase):

    def test_14_titulo_stripped(self):
        out = prp.project_public_record(sample_record())
        self.assertNotIn("titulo", out)

    def test_15_bookkeeping_families_stripped(self):
        out = prp.project_public_record(sample_record())
        for key in BOOKKEEPING_FAMILY_KEYS:
            self.assertNotIn(key, out, f"{key!r} must not survive projection")

    def test_15b_internal_input_retains_bookkeeping_fields(self):
        rec = sample_record()
        prp.project_public_record(rec)
        for key in BOOKKEEPING_FAMILY_KEYS:
            self.assertIn(key, rec, f"{key!r} must remain on the internal record")
        self.assertIn("titulo", rec)

    def test_16_legitimate_public_fields_survive_unchanged(self):
        rec = sample_record()
        out = prp.project_public_record(rec)
        for key in ("titol", "organisme", "url"):
            self.assertEqual(out[key], rec[key])

    def test_17_unknown_field_cannot_silently_escape(self):
        rec = sample_record(some_future_internal_field_never_seen_before="x")
        out = prp.project_public_record(rec)
        self.assertNotIn("some_future_internal_field_never_seen_before", out)

    def test_18_repeated_projection_deterministic_idempotent(self):
        rec = sample_record()
        out1 = prp.project_public_record(rec)
        out2 = prp.project_public_record(rec)
        self.assertEqual(out1, out2)


# --------------------------------------------------------------------------- #
# CROSS-GATE 19-20 (see module docstring for the F-04/regression rationale)
# --------------------------------------------------------------------------- #

class CrossGateTests(unittest.TestCase):

    def test_19_prompt287_null_to_absence_contract_unaffected(self):
        import tools.public_projection as ppj
        doc = ppj._project_production_document({"url": "https://example.test/x"})
        self.assertNotIn("doc_intel", doc)  # true absence, never a present null

    def test_20_ib4_docintel_contract_constants_unaffected(self):
        import tools.public_contract as pc
        import tools.public_projection as ppj
        self.assertTrue(pc.is_document_doc_ref_path(("documents", 0, "doc_ref")))
        self.assertEqual(ppj.DOC_INTEL_SCHEMA, "adgops.public.docintel/1")

    def test_batch_result_shape_on_success(self):
        result = prp.project_public_records([sample_record()])
        self.assertEqual(set(result.keys()), {"accepted", "rejected_reason", "records"})
        self.assertTrue(result["accepted"])
        self.assertIsNone(result["rejected_reason"])
        self.assertEqual(len(result["records"]), 1)

    def test_non_list_input_rejected(self):
        result = prp.project_public_records({"not": "a list"})
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejected_reason"], "records_not_a_list")


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    n = result.testsRun
    passed = result.wasSuccessful()
    verdict = "PASS" if passed else "FAIL"
    print(f"PUBLIC_RECORD_PROJECTION TESTS: {verdict} ({n} cases)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
