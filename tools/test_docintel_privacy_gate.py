#!/usr/bin/env python3
"""
tools/test_docintel_privacy_gate.py
ADG OPS IB-4 (p273 v0.3 §14, WRKOPS t_20260906_adgops286) — synthetic
regression suite for the path-scoped DocIntel privacy/publication blocking
gate added to tools/privacy_validator.py and tools/public_contract.py.

Standard-library only. Synthetic literals only — no real production records,
raw excerpts, or copied document text. Never reads or writes data/**.

Run:
  python tools/test_docintel_privacy_gate.py [-v]
"""

import copy
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.privacy_validator as pv  # noqa: E402
import tools.public_contract as pc  # noqa: E402
import tools.public_projection as pp  # noqa: E402

_VALID_DOC_REF = pp.DOC_REF_PREFIX + "a" * pp.DOC_REF_HEX_LEN


def _valid_doc_intel():
    return {
        "schema": pp.DOC_INTEL_SCHEMA,
        "state": "analysed",
        "analysed_at": "2026-01-01T00:00:00Z",
        "fields": [
            {
                "key": "cpv",
                "type": "code_list",
                "value": ["12345678"],
                "evidence": [{"doc_ref": _VALID_DOC_REF, "page": 1}],
            }
        ],
    }


def _record_with(doc_ref=_VALID_DOC_REF, doc_intel=None):
    return {"documents": [{"url": "https://example.test/doc.pdf",
                            "doc_ref": doc_ref, "doc_intel": doc_intel}]}


def _rule_ids(findings):
    return {f.rule_id for f in findings}


def _severity_counts(findings):
    n_err = sum(1 for f in findings if f.severity == pv.ERROR)
    n_warn = sum(1 for f in findings if f.severity == pv.WARN)
    return n_err, n_warn


class DocIntelGateTests(unittest.TestCase):
    """Covers scenarios A-R of the IB-4 handoff test requirements."""

    # --- A ---

    def test_a_no_doc_ref_or_doc_intel_passes(self):
        obj = {"documents": [{"url": "https://example.test/x.pdf"}]}
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        n_err, _n_warn = _severity_counts(findings)
        self.assertEqual(n_err, 0)

    # --- B ---

    def test_b_doc_ref_at_correct_path_recognized_without_global_widening(self):
        obj = {"documents": [{"doc_ref": _VALID_DOC_REF}]}
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        self.assertNotIn("SCHEMA_UNKNOWN", _rule_ids(findings))
        n_err, _n_warn = _severity_counts(findings)
        self.assertEqual(n_err, 0)
        self.assertNotIn(pv.normalize_key("doc_ref"), pv.KNOWN_PUBLIC_KEYS)

    # --- C ---

    def test_c_doc_ref_at_wrong_path_not_recognized(self):
        obj = {"doc_ref": _VALID_DOC_REF}
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        schema_unknown = [f for f in findings if f.rule_id == "SCHEMA_UNKNOWN"]
        self.assertEqual(len(schema_unknown), 1)

    # --- D ---

    def test_d_valid_cpv_analysed_doc_intel_no_docintel_error(self):
        obj = _record_with(doc_intel=_valid_doc_intel())
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        docintel_rules = {r for r in _rule_ids(findings) if r.startswith("DOCINTEL_")}
        self.assertEqual(docintel_rules, set())

    # --- E ---

    def test_e_unknown_key_inside_doc_intel(self):
        di = _valid_doc_intel()
        di["mystery_key"] = "x"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_UNKNOWN_KEY", _rule_ids(findings))
        n_err, _n_warn = _severity_counts(findings)
        self.assertGreaterEqual(n_err, 1)

    # --- F ---

    def test_f_producer_internal_key_inside_doc_intel(self):
        di = _valid_doc_intel()
        di["excerpt"] = "leaked excerpt text"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        rules = _rule_ids(findings)
        self.assertIn("DOCINTEL_INTERNAL_FIELD", rules)
        self.assertNotIn("DOCINTEL_UNKNOWN_KEY", rules)

    def test_f2_error_prefixed_internal_key(self):
        di = _valid_doc_intel()
        di["error_extract_timeout"] = "x"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_INTERNAL_FIELD", _rule_ids(findings))

    # --- G ---

    def test_g_arbitrary_free_text_cpv_value(self):
        di = _valid_doc_intel()
        di["fields"][0]["value"] = ["not-a-cpv-code"]
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_FREE_TEXT", _rule_ids(findings))

    # --- H ---

    def test_h_string_too_long(self):
        di = _valid_doc_intel()
        di["fields"][0]["key"] = "x" * 70
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_STRING_TOO_LONG", _rule_ids(findings))

    # --- I ---

    def test_i_url_anywhere_under_doc_intel(self):
        di = _valid_doc_intel()
        di["fields"][0]["key"] = "https://example.test/leak"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_URL_FORBIDDEN", _rule_ids(findings))

    # --- J ---

    def test_j_invalid_state_enum(self):
        di = _valid_doc_intel()
        di["state"] = "bogus_state"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_ENUM", _rule_ids(findings))

    def test_j2_invalid_field_type_enum(self):
        di = _valid_doc_intel()
        di["fields"][0]["type"] = "bogus_type"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_ENUM", _rule_ids(findings))

    def test_j3_invalid_reason_enum(self):
        di = {
            "schema": pp.DOC_INTEL_SCHEMA,
            "state": "unavailable",
            "reason": "bogus_reason",
        }
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_ENUM", _rule_ids(findings))

    # --- K ---

    def test_k_missing_schema(self):
        di = _valid_doc_intel()
        del di["schema"]
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_SCHEMA", _rule_ids(findings))

    def test_k2_wrong_schema(self):
        di = _valid_doc_intel()
        di["schema"] = "wrong/1"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_SCHEMA", _rule_ids(findings))

    # --- L ---

    def test_l_fields_over_cardinality_cap(self):
        di = _valid_doc_intel()
        one_field = di["fields"][0]
        di["fields"] = [dict(one_field) for _ in range(pp.MAX_FIELDS + 1)]
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_CARDINALITY", _rule_ids(findings))

    def test_l2_evidence_over_cardinality_cap(self):
        di = _valid_doc_intel()
        di["fields"][0]["evidence"] = [
            {"doc_ref": _VALID_DOC_REF, "page": p}
            for p in range(1, pp.MAX_EVIDENCE + 3)
        ]
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("DOCINTEL_CARDINALITY", _rule_ids(findings))

    # --- M ---

    def test_m_docintel_rule_ids_never_fire_outside_doc_intel(self):
        obj = {
            "schema": "x", "state": "y", "reason": "z", "fields": [],
            "documents": [{"url": "https://example.test/a.pdf"}],
        }
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        docintel_rules = {r for r in _rule_ids(findings) if r.startswith("DOCINTEL_")}
        self.assertEqual(docintel_rules, set())

    # --- N ---

    def test_n_unrelated_schema_unknown_warn_zero_error(self):
        obj = {"totally_unknown_legacy_bookkeeping_field_xyz": "value"}
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        n_err, n_warn = _severity_counts(findings)
        self.assertEqual(n_err, 0)
        self.assertGreaterEqual(n_warn, 1)
        self.assertIn("SCHEMA_UNKNOWN", _rule_ids(findings))

    # --- O ---

    def test_o_existing_hard_privacy_negative_still_errors(self):
        obj = {"password": "n0tAreal-secret-ib4-0001"}
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        n_err, _n_warn = _severity_counts(findings)
        self.assertGreaterEqual(n_err, 1)

    def test_o2_hard_rule_fires_even_inside_doc_intel(self):
        # §14.2: hard private-data rules apply "anywhere in the file",
        # including inside the DocIntel subtree.
        di = _valid_doc_intel()
        di["fields"][0]["key"] = "contacte@synthetic.test"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        self.assertIn("EMAIL_VALUE", _rule_ids(findings))

    # --- P ---

    def test_p_malformed_json_exit_one(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bad = Path(tmp.name) / "malformed.json"
        bad.write_text("{ not: valid json,,, ", encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pv.run(["--fixture", str(bad), "--surface", "public-build"])
        self.assertEqual(code, 1)

    # --- Q ---

    def test_q_deterministic_order_and_findings(self):
        di = _valid_doc_intel()
        di["mystery_key"] = "x"
        di["another_key"] = "y"
        obj = _record_with(doc_intel=di)
        findings1 = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        findings2 = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
        rows1 = [(f.rule_id, f.pointer, c) for f, c in pv._dedup(findings1)]
        rows2 = [(f.rule_id, f.pointer, c) for f, c in pv._dedup(findings2)]
        self.assertEqual(rows1, rows2)

    # --- R ---

    def test_r_no_mutation_of_scanned_object(self):
        di = _valid_doc_intel()
        obj = _record_with(doc_intel=di)
        before = copy.deepcopy(obj)
        pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        self.assertEqual(obj, before)

    def test_r2_record_scope_contract_predicates_are_pure(self):
        path = ("documents", 0, "doc_intel")
        before = tuple(path)
        pc.is_document_doc_intel_root_path(path)
        pc.is_document_doc_ref_path(path)
        pc.doc_intel_root_prefix_len(path)
        self.assertEqual(path, before)

    # --- exit-code mapping (record-scope + privacy gate together) ---

    def test_exit_code_zero_for_clean_docintel(self):
        obj = _record_with(doc_intel=_valid_doc_intel())
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        n_err, _n_warn = _severity_counts(findings)
        self.assertEqual(2 if n_err > 0 else 0, 0)

    def test_exit_code_two_for_docintel_error(self):
        di = _valid_doc_intel()
        di["state"] = "bogus_state"
        obj = _record_with(doc_intel=di)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        n_err, _n_warn = _severity_counts(findings)
        self.assertEqual(2 if n_err > 0 else 0, 2)

    # --- absent doc_intel key is the valid default (test_a); PRESENT null
    #     is a malformed present value, not an alternate spelling of it ---

    def test_present_null_doc_intel_is_docintel_schema_error(self):
        # p273 v0.3 (Companion correction R1): absence of the `doc_intel` key
        # is the valid default; a PRESENT `doc_intel: null` is a malformed
        # present value, not an alternate spelling of absence, and must fail
        # closed via DOCINTEL_SCHEMA / exit 2.
        obj = _record_with(doc_intel=None)
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        self.assertIn("DOCINTEL_SCHEMA", _rule_ids(findings))
        n_err, _n_warn = _severity_counts(findings)
        self.assertEqual(2 if n_err > 0 else 0, 2)

    def test_non_object_doc_intel_fails_closed(self):
        obj = _record_with(doc_intel="not-an-object")
        findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, production=True)
        self.assertIn("DOCINTEL_SCHEMA", _rule_ids(findings))


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    verdict = "PASS" if result.wasSuccessful() else "FAIL"
    print(f"DOCINTEL_PRIVACY_GATE_REGRESSION: {verdict} ({result.testsRun} cases)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
