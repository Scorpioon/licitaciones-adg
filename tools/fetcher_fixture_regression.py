#!/usr/bin/env python3
"""
tools/fetcher_fixture_regression.py
ADG OPS v0.6.44 / Prompt 190 — Offline scheduled-fetcher regression harness.

Standard-library only. No live network. No GitHub Actions dispatch. Never mutates
data/licitaciones.json.

Exercises the two layers that decide scheduled-fetcher behaviour, entirely offline:

  L1 — tools/scheduled_fetch_merge.py helper semantics
       (candidate envelope normalization, structure validation, partial/failed
       refusal policy, PARTIAL_SUCCESS acceptance, lifecycle integrity guard).
       Production paths are monkeypatched to a temp copy of a synthetic fixture;
       run_live (which would hit the network) is never called.

  L2 — tools/scheduled_run_classify.py operational-status classifier/report
       (the module extracted from the fetch.yml heredoc): table-driven env +
       temp candidate/helper-log scenarios mapped to expected OPERATIONAL_STATUS
       and the ADGOPS_SCHEDULED_RUN_REPORT_V1 report shape.

Run:
  python tools/fetcher_fixture_regression.py [-v]

A sha256+mtime snapshot of the real data/licitaciones.json is taken before the
suite runs and re-checked after, so the run proves the production data file was
not touched. Final line:
  REGRESSION: PASS (N cases, data file untouched: yes)
  REGRESSION: FAIL (N cases, data file untouched: no/unknown)
"""

import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures" / "fetcher"
PRIVACY_FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures" / "privacy"
DATA_FILE = REPO_ROOT / "data" / "licitaciones.json"

import tools.scheduled_fetch_merge as sfm  # noqa: E402
import tools.scheduled_run_classify as src  # noqa: E402
import tools.privacy_validator as pv  # noqa: E402

AUTOMATION_ID = "ADGOPS_AUTO_FETCHER1_SCHEDULED"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def fixture_text(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def load_fixture(name: str) -> dict:
    return json.loads(fixture_text(name))


def dryrun_args(candidate: Path, output: Path) -> types.SimpleNamespace:
    """Minimal args object matching what run_merge_dry_run reads."""
    return types.SimpleNamespace(candidate=str(candidate), output=str(output))


# ---------------------------------------------------------------------------
# L1 — scheduled_fetch_merge helper semantics
# ---------------------------------------------------------------------------

class L1MergeHelperTests(unittest.TestCase):
    """Helper-level tests with production paths redirected to a temp sandbox."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

        # Temp production = copy of the synthetic production fixture.
        self.prod_path = self.tmp / "production.json"
        shutil.copyfile(FIXTURES_DIR / "production_min.json", self.prod_path)

        # Save and redirect every module global that decides a write target so the
        # helper can never write to the repo (real production, repo _tmp, reports).
        self._saved = {
            "PRODUCTION_PATH": sfm.PRODUCTION_PATH,
            "TMP_DIR": sfm.TMP_DIR,
            "REPORT_CHECK": sfm.REPORT_CHECK,
            "REPORT_VALIDATE": sfm.REPORT_VALIDATE,
            "REPORT_DRY_RUN": sfm.REPORT_DRY_RUN,
            "REPORT_CONFLICTS": sfm.REPORT_CONFLICTS,
        }
        sfm.PRODUCTION_PATH = self.prod_path
        sfm.TMP_DIR = self.tmp
        sfm.REPORT_CHECK = self.tmp / "report_check.json"
        sfm.REPORT_VALIDATE = self.tmp / "report_validate.json"
        sfm.REPORT_DRY_RUN = self.tmp / "report_dry_run.json"
        sfm.REPORT_CONFLICTS = self.tmp / "report_conflicts.json"

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(sfm, k, v)
        self._tmp.cleanup()

    # --- normalization -----------------------------------------------------

    def test_normalize_accepts_nested_meta_shape(self):
        data = load_fixture("cand_full_success.json")
        out = sfm.normalize_candidate_envelope(data, "candidate")
        self.assertIsInstance(out.get("meta"), dict)
        self.assertIsInstance(out.get("data"), list)
        # Shape A is returned unchanged.
        self.assertEqual(out["meta"].get("run_status"), "FULL_SUCCESS")

    def test_normalize_accepts_fetcher_top_level_shape(self):
        data = load_fixture("cand_fetcher_shape.json")
        self.assertNotIn("meta", data)  # fixture is the top-level (fetcher) shape
        out = sfm.normalize_candidate_envelope(data, "candidate")
        self.assertIsInstance(out.get("meta"), dict)
        self.assertEqual(out["meta"].get("run_status"), "FULL_SUCCESS")
        self.assertNotIn("data", out["meta"])  # 'data' stays at top level only
        self.assertEqual(len(out["data"]), 1)
        errs = sfm.validate_structure(out, "candidate")
        self.assertEqual(errs, [])

    # --- malformed / missing data rejection --------------------------------

    def test_malformed_json_rejected(self):
        with self.assertRaises(SystemExit):
            sfm.load_json(FIXTURES_DIR / "cand_malformed.json")

    def test_missing_data_rejected(self):
        data = load_fixture("cand_missing_data.json")
        out = sfm.normalize_candidate_envelope(data, "candidate")
        errs = sfm.validate_structure(out, "candidate")
        self.assertTrue(any("missing 'data' key" in e for e in errs))

    # --- partial/failed refusal policy -------------------------------------

    def _assert_dryrun_refuses(self, fixture_name):
        out = self.tmp / "out.json"
        with self.assertRaises(SystemExit):
            sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / fixture_name, out))
        # Refused before any merged output is written.
        self.assertFalse(out.exists())

    def test_empty_failure_refused(self):
        self._assert_dryrun_refuses("cand_empty_failure.json")

    def test_non_atom_refused(self):
        self._assert_dryrun_refuses("cand_non_atom.json")

    def test_partial_no_success_run_status_refused(self):
        # Synthetic partial candidate whose run_status lacks "success".
        cand = self.tmp / "cand_partial_nosuccess.json"
        cand.write_text(json.dumps({
            "meta": {"run_status": "PARTIAL_DEGRADED", "is_partial": True,
                     "failed_sources": ["PLACSP-643"], "source_errors": {}},
            "data": [],
        }), encoding="utf-8")
        out = self.tmp / "out.json"
        with self.assertRaises(SystemExit):
            sfm.run_merge_dry_run(dryrun_args(cand, out))
        self.assertFalse(out.exists())

    # --- PARTIAL_SUCCESS acceptance (current locked policy) ----------------

    def test_partial_acceptable_is_accepted(self):
        out = self.tmp / "out.json"
        # Must NOT raise: is_partial=true but run_status contains "success".
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_partial_acceptable.json", out))
        self.assertTrue(out.exists())
        merged = json.loads(out.read_text(encoding="utf-8"))
        self.assertIsInstance(merged.get("data"), list)
        # The candidate-only record was appended to the 3 production records.
        self.assertEqual(len(merged["data"]), 4)
        keys = {sfm.get_merge_key(r) for r in merged["data"]}
        self.assertIn("CFID-NEW-002", keys)

    def test_full_success_merge_appends_new_and_merges_overlap(self):
        out = self.tmp / "out.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_full_success.json", out))
        merged = json.loads(out.read_text(encoding="utf-8"))
        # 3 production + 1 candidate-only (overlap merged in place) = 4.
        self.assertEqual(len(merged["data"]), 4)
        keys = {sfm.get_merge_key(r) for r in merged["data"]}
        self.assertIn("CFID-NEW-001", keys)
        self.assertIn("CFID-OVERLAP-001", keys)

    # --- lifecycle integrity guard -----------------------------------------

    def test_lifecycle_integrity_detects_unsafe_active_award(self):
        bad = [{
            "contract_folder_id": "CFID-BAD-1",
            "lifecycle_category": "OPEN_WITH_AWARD_EVIDENCE",
            "active_opportunity_eligible": True,
        }]
        ok, issues = sfm.validate_lifecycle_integrity(bad)
        self.assertFalse(ok)
        self.assertTrue(issues)

    def test_lifecycle_integrity_passes_valid_records(self):
        prod = load_fixture("production_min.json")
        ok, issues = sfm.validate_lifecycle_integrity(prod["data"])
        self.assertTrue(ok)
        self.assertEqual(issues, [])


# ---------------------------------------------------------------------------
# L2 — scheduled_run_classify operational-status classifier / report
# ---------------------------------------------------------------------------

def base_env(**overrides) -> dict:
    env = {
        "AUTOMATION_ID": AUTOMATION_ID,
        "AUTOMATION_KIND": "fetcher1-scheduled",
        "AUTOMATION_DATA_FILE": "data/licitaciones.json",
        "AUTOMATION_SOURCES": "PLACSP-643, PLACSP-1044",
        "GH_EVENT_NAME": "schedule",
        "GH_RUN_NUMBER": "999",
        "RUN_FETCH": "true",
        "DRY_RUN_MODE": "false",
    }
    env.update(overrides)
    return env


class L2ClassifierTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_candidate(self, fixture_name=None, payload=None):
        """Place a scheduled_live_candidate_*.json into the temp dir."""
        dst = self.tmp / "scheduled_live_candidate_20260625T060000Z.json"
        if payload is not None:
            dst.write_text(json.dumps(payload), encoding="utf-8")
        else:
            shutil.copyfile(FIXTURES_DIR / fixture_name, dst)
        return dst

    def classify(self, env, helper_log=None):
        return src.classify(env, tmp_dir=self.tmp, helper_log=helper_log)

    # --- table-driven status scenarios -------------------------------------

    def test_skipped_by_guard(self):
        env = base_env(RUN_FETCH="skip")
        self.assertEqual(self.classify(env)["status"], "SKIPPED_BY_GUARD")

    def test_manual_dry_run_success(self):
        env = base_env(DRY_RUN_MODE="true", DRYRUN_OUTCOME="success")
        self.assertEqual(self.classify(env)["status"], "MANUAL_DRY_RUN_SUCCESS")

    def test_dry_run_validation_failure(self):
        env = base_env(DRY_RUN_MODE="true", DRYRUN_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_VALIDATION")

    def test_success_real_fetch_write(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        r = self.classify(env)
        self.assertEqual(r["status"], "SUCCESS_REAL_FETCH_WRITE")
        self.assertEqual(r["report"]["operational"]["candidate_accepted"], "yes")
        self.assertEqual(r["report"]["operational"]["data_write"], "yes")
        self.assertEqual(r["report"]["operational"]["commit_pushed"], "yes")

    def test_success_real_fetch_no_changes(self):
        self.write_candidate("cand_empty_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="false", PUSH_OUTCOME="skipped")
        self.assertEqual(self.classify(env)["status"], "SUCCESS_REAL_FETCH_NO_CHANGES")

    def test_fail_closed_partial_source_outage_masked_exit(self):
        # #138-like: helper step exit masked (success) but EMPTY_FAILURE candidate.
        self.write_candidate("cand_empty_failure.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success")
        r = self.classify(env)
        self.assertEqual(r["status"], "FAIL_CLOSED_PARTIAL_SOURCE_OUTAGE")
        self.assertEqual(r["report"]["operational"]["candidate_accepted"], "no")
        self.assertEqual(r["report"]["operational"]["data_write"], "no")

    def test_fail_closed_parser_non_atom(self):
        self.write_candidate("cand_non_atom.json")
        env = base_env(HELPER_OUTCOME="success")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_PARSER_NON_ATOM")

    def test_fail_closed_validation_helper_log(self):
        env = base_env(HELPER_OUTCOME="failure")
        log = "[ERROR] Candidate invalid: ['candidate: missing data key']"
        self.assertEqual(self.classify(env, helper_log=log)["status"], "FAIL_CLOSED_VALIDATION")

    def test_fail_closed_merge_policy(self):
        env = base_env(HELPER_OUTCOME="failure")
        log = "[ERROR] Lifecycle integrity failed before write: [...]"
        self.assertEqual(self.classify(env, helper_log=log)["status"], "FAIL_CLOSED_MERGE_POLICY")

    def test_fail_closed_git_commit(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_GIT_COMMIT")

    def test_fail_closed_git_push(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_GIT_PUSH")

    def test_fail_closed_generic(self):
        # Helper failed with no recognizable marker and no candidate envelope.
        env = base_env(HELPER_OUTCOME="failure")
        self.assertEqual(self.classify(env, helper_log="some unrelated traceback")["status"],
                         "FAIL_CLOSED")

    def test_known_cases_never_unknown(self):
        # All explicit scenarios above resolve to a named status, never UNKNOWN.
        scenarios = [
            base_env(RUN_FETCH="skip"),
            base_env(DRY_RUN_MODE="true", DRYRUN_OUTCOME="success"),
            base_env(HELPER_OUTCOME="failure"),
        ]
        for env in scenarios:
            self.assertNotEqual(self.classify(env, helper_log="x")["status"], "UNKNOWN")

    # --- report shape ------------------------------------------------------

    def test_report_schema_and_top_level_shape(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        report = self.classify(env)["report"]
        self.assertEqual(report["schema"], "ADGOPS_SCHEDULED_RUN_REPORT_V1")
        self.assertEqual(report["schema_version"], "1.0")
        for key in ("automation", "github", "guard", "operational",
                    "candidate", "outcomes", "data"):
            self.assertIn(key, report)
        self.assertEqual(report["operational"]["status"], "SUCCESS_REAL_FETCH_WRITE")
        self.assertEqual(report["automation"]["id"], AUTOMATION_ID)

    def test_source_errors_truncated_to_500(self):
        long_err = "x" * 1200
        self.write_candidate(payload={
            "meta": {"run_status": "EMPTY_FAILURE", "is_partial": True,
                     "failed_sources": ["PLACSP-643"],
                     "source_errors": {"PLACSP-643": long_err}},
            "data": [],
        })
        env = base_env(HELPER_OUTCOME="success")
        report = self.classify(env)["report"]
        for v in report["candidate"]["source_errors"].values():
            self.assertLessEqual(len(v), 500)

    def test_write_outputs_writes_report_json(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        result = self.classify(env)
        step_summary = self.tmp / "step_summary.md"
        github_env = self.tmp / "github_env.txt"
        src.write_outputs(result, tmp_dir=self.tmp,
                          github_step_summary=str(step_summary),
                          github_env=str(github_env))
        report_path = self.tmp / "scheduled_run_report_999.json"
        self.assertTrue(report_path.exists())
        written = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(written["schema"], "ADGOPS_SCHEDULED_RUN_REPORT_V1")
        self.assertIn("OPERATIONAL_STATUS=SUCCESS_REAL_FETCH_WRITE",
                      github_env.read_text(encoding="utf-8"))
        summary = step_summary.read_text(encoding="utf-8")
        self.assertIn("Scheduled Fetcher — Operational Summary", summary)
        self.assertIn("SUCCESS_REAL_FETCH_WRITE", summary)


# ---------------------------------------------------------------------------
# L3 — privacy_validator (Prompt 246 foundation): synthetic fixtures + surface policy
# ---------------------------------------------------------------------------

def _severity_counts(findings):
    n_err = sum(1 for f in findings if f.severity == pv.ERROR)
    n_warn = sum(1 for f in findings if f.severity == pv.WARN)
    return n_err, n_warn


class L3PrivacyValidatorTests(unittest.TestCase):
    """Privacy regression layer. Read-only; asserts fail-closed on hard classes,
    report-only (WARN) on current-production hygiene, and no raw-value echo."""

    @classmethod
    def setUpClass(cls):
        manifest = json.loads(
            (PRIVACY_FIXTURES_DIR / "_expectations.json").read_text(encoding="utf-8")
        )
        cls.expectations = manifest["fixtures"]

    def _validate_fixture(self, entry, production=False):
        path = PRIVACY_FIXTURES_DIR / entry["file"]
        findings = pv.validate_path_read_only(path, entry["surface"], production=production)
        return _severity_counts(findings)

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pv.run(argv)
        return code, out.getvalue(), err.getvalue()

    # --- every fixture resolves to its declared outcome --------------------

    def test_every_fixture_matches_expectation(self):
        for entry in self.expectations:
            with self.subTest(fixture=entry["file"]):
                n_err, n_warn = self._validate_fixture(entry)
                expect = entry["expect"]
                if expect == "FAIL":
                    self.assertGreaterEqual(n_err, 1, f"{entry['file']} expected ERROR")
                elif expect == "WARN":
                    self.assertEqual(n_err, 0, f"{entry['file']} must not ERROR")
                    self.assertGreaterEqual(n_warn, 1, f"{entry['file']} expected WARN")
                else:  # PASS — F11: a PASS fixture must be clean of ERROR *and* WARN
                    self.assertEqual(n_err, 0, f"{entry['file']} must not ERROR")
                    self.assertEqual(n_warn, 0, f"{entry['file']} must not WARN")

    def test_fixture_cli_exit_codes(self):
        # FAIL -> 2, PASS/WARN -> 0 through the real CLI path.
        for entry in self.expectations:
            with self.subTest(fixture=entry["file"]):
                path = PRIVACY_FIXTURES_DIR / entry["file"]
                code, _out, _err = self.run_cli(
                    ["--fixture", str(path), "--surface", entry["surface"]]
                )
                expected = 2 if entry["expect"] == "FAIL" else 0
                self.assertEqual(code, expected)

    # --- recursion, normalization, false positives ------------------------

    def test_recursive_arrays_and_objects(self):
        obj = {"a": [[{"b": [{"c": {"password": "n0tAreal"}}]}]]}
        n_err, _ = _severity_counts(
            pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
        self.assertGreaterEqual(n_err, 1)

    def test_key_normalization_variants(self):
        for key in ("email", "E-Mail", "e_mail", "API KEY", "api_key", "apiKey",
                    "Auth-Token"):
            obj = {key: "value-present"}
            n_err, _ = _severity_counts(
                pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
            self.assertGreaterEqual(n_err, 1, f"{key!r} should normalize to a forbidden key")

    def test_false_positive_resistance(self):
        for text in ("Secretaria de Estado", "Servei de tokenizacion de pagaments",
                     "gestio de password recovery"):
            obj = {"organisme": text, "titol": text}
            n_err, _ = _severity_counts(
                pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
            self.assertEqual(n_err, 0, f"{text!r} must not trip a hard rule")

    def test_populated_nif_fails_empty_ok(self):
        bad = {"award_results": [{"winning_party_nif": "X1234567Z"}]}
        good_empty = {"award_results": [{"winning_party_nif": ""}]}
        good_null = {"award_results": [{"winning_party_nif": None}]}
        self.assertGreaterEqual(
            _severity_counts(pv.validate_json_object(bad, pv.SURFACE_PUBLIC))[0], 1)
        self.assertEqual(
            _severity_counts(pv.validate_json_object(good_empty, pv.SURFACE_PUBLIC))[0], 0)
        self.assertEqual(
            _severity_counts(pv.validate_json_object(good_null, pv.SURFACE_PUBLIC))[0], 0)

    # --- surface policy ----------------------------------------------------

    def test_ephemeral_suppresses_hygiene_keeps_hard(self):
        ok = self._validate_fixture(
            {"file": "ephemeral_candidate_ok.json", "surface": "internal-ephemeral"})
        self.assertEqual(ok[0], 0)  # no hard ERROR
        bad = self._validate_fixture(
            {"file": "ephemeral_secret.json", "surface": "internal-ephemeral"})
        self.assertGreaterEqual(bad[0], 1)  # secret still ERROR even ephemeral

    def test_public_hard_paths_are_error_on_public_only(self):
        obj = {"url": "K:\\DEVKIT\\x\\y.pdf"}
        self.assertGreaterEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 1)
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_INTERNAL))[0], 0)

    # --- diagnostics never echo raw values --------------------------------

    def test_no_raw_value_in_output(self):
        # Secret-bearing fixtures; their raw sensitive tokens must never appear.
        checks = [
            ("populated_winning_party_nif.json", "public-build", "X1234567Z"),
            ("credential_token.json", "public-build", "aB3dEf6hIj9kLmN0pQrS"),
            ("forbidden_top_key.json", "public-build", "contacte@synthetic.test"),
            ("unix_home_path.json", "public-build", "/home/operador"),
            ("windows_absolute_path.json", "public-build", "DEVKIT"),
        ]
        for fname, surface, secret in checks:
            with self.subTest(fixture=fname):
                path = PRIVACY_FIXTURES_DIR / fname
                _code, out, err = self.run_cli(
                    ["--fixture", str(path), "--surface", surface, "--json"])
                self.assertNotIn(secret, out)
                self.assertNotIn(secret, err)
                # plain text form too
                _code, out2, _e = self.run_cli(
                    ["--fixture", str(path), "--surface", surface])
                self.assertNotIn(secret, out2)

    def test_deterministic_ordering(self):
        path = PRIVACY_FIXTURES_DIR / "relative_tmp_meta.json"
        _c1, out1, _e1 = self.run_cli(["--fixture", str(path), "--surface", "public-build"])
        _c2, out2, _e2 = self.run_cli(["--fixture", str(path), "--surface", "public-build"])
        self.assertEqual(out1, out2)

    # --- F1: compound / camelCase sensitive keys ---------------------------

    def test_f1_compound_sensitive_keys_detected(self):
        for key in ("contact_phone", "database_password", "github_token",
                    "operator_dni", "config_private_key", "contactEmail",
                    "accessToken"):
            with self.subTest(key=key):
                obj = {key: "value-present-0001"}
                n_err, _ = _severity_counts(
                    pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
                self.assertGreaterEqual(n_err, 1, f"{key!r} must be detected")

    def test_f1_benign_key_tokens_not_flagged(self):
        # Schema keys that merely contain a sensitive substring/token must pass.
        for key in ("canonical_key", "status_key", "estat_raw",
                    "status_code_raw", "winning_party_name", "source_merge_class",
                    "source_records"):
            with self.subTest(key=key):
                obj = {key: "value-present-0001"}
                n_err, _ = _severity_counts(
                    pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
                self.assertEqual(n_err, 0, f"{key!r} must not be flagged")

    # --- F2: unicode / accented aliases ------------------------------------

    def test_f2_accented_keys_detected(self):
        for key in ("teléfono", "telèfon", "correo_electrónico", "contraseña"):
            with self.subTest(key=key):
                obj = {key: "value-present-0002"}
                n_err, _ = _severity_counts(
                    pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
                self.assertGreaterEqual(n_err, 1, f"{key!r} must be detected")

    # --- F3: phone value under an innocent key -----------------------------

    def test_f3_phone_value_detected(self):
        obj = {"nota": "Contacte: +34 612 345 678 per consultes"}
        self.assertGreaterEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 1)

    def test_f3_phone_false_positives(self):
        for text in ("02.07.01.01 2099/11-SS", "2026-01-05",
                     "2026-01-05T06:00:00Z", "1.234.567,89 EUR", "79822500",
                     "612 345 678", "DECRETO 2099 0318 241031"):
            with self.subTest(text=text):
                obj = {"nota": text, "titol": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a phone rule")

    # --- F4: DNI/NIE value under an innocent key ---------------------------

    def test_f4_dni_nie_value_detected(self):
        for val in ("titular 12345678Z present", "suplent X1234567L present"):
            with self.subTest(val=val):
                obj = {"nota": val}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{val!r} must be detected")

    def test_f4_dni_nie_false_positives(self):
        # Synthetic contract/reference identifiers (checksum-invalid, zero-padded,
        # slash/dash-delimited, CIF shape, CPV) must not be flagged.
        for text in ("2099/00000777A", "2099/SYNTH0902/00000850E", "B12345678",
                     "79822500", "X1234567Z", "REF-12345678A"):
            with self.subTest(text=text):
                obj = {"nota": text, "canonical_key": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a personal-id rule")

    def test_f4_winning_party_nif_key_unconditional(self):
        # The KEY rule flags any populated value regardless of value checksum.
        obj = {"award_results": [{"winning_party_nif": "X1234567Z"}]}
        self.assertGreaterEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 1)

    # --- F5: raw carriers + internal/public boundary -----------------------

    def test_f5_public_raw_carriers_error(self):
        for key in ("content", "response", "source_errors", "traceback",
                    "exception", "helper_log"):
            with self.subTest(key=key):
                obj = {key: "populated diagnostic carrier body"}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"public carrier {key!r} must ERROR")

    def test_f5_internal_carriers_suppressed_but_hard_applies(self):
        carrier = {"source_errors": {"S": "boom"}, "content": "raw body"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(carrier, pv.SURFACE_INTERNAL))[0], 0)
        secret = {"content": "AKIA0000EXAMPLE00000"}
        self.assertGreaterEqual(
            _severity_counts(pv.validate_json_object(secret, pv.SURFACE_INTERNAL))[0], 1)

    # --- F6: URI scheme + host coverage ------------------------------------

    def test_f6_dangerous_and_private_uris(self):
        for url in ("data:,synthetic", "file:C:/synthetic.txt",
                    "ftp://user:pass@127.0.0.1/x", "http://localhost./x",
                    "javascript:alert(1)", "mailto:x@synthetic.test",
                    "http://10.0.0.5/x", "https://user:pass@host.test/x"):
            with self.subTest(url=url):
                obj = {"url": url}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{url!r} must be rejected")

    def test_f6_ordinary_text_and_https_pass(self):
        # Ordinary colon-prose under a non-url-like key never trips a URL
        # rule. (Under a url-like key it is held to the stricter absolute
        # http/https contract — see test_p246_v04_f1_*.)
        for text in ("Data: 2026-01-01", "file: expedient 3/26", "Horari: 9-14"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a URL rule")
        obj = {"url": "https://exemple-gov.test/doc/1.pdf"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    # --- F7: sensitive key names redacted in pointers ----------------------

    def test_f7_sensitive_key_name_redacted_cli(self):
        path = PRIVACY_FIXTURES_DIR / "sensitive_key_name_redaction.json"
        for argv in (["--fixture", str(path), "--surface", "public-build"],
                     ["--fixture", str(path), "--surface", "public-build", "--json"]):
            code, out, err = self.run_cli(argv)
            self.assertEqual(code, 2)
            self.assertNotIn("responsable@synthetic.test", out)
            self.assertNotIn("responsable@synthetic.test", err)
            self.assertIn("redacted_key", out)

    def test_f7_email_shaped_key_absent_from_pointer(self):
        obj = {"john@example.com": "Authorization: Bearer abcdef1234567890xyz"}
        for f in pv.validate_json_object(obj, pv.SURFACE_PUBLIC):
            self.assertNotIn("john@example.com", f.pointer)

    # --- F8: no raw-derived digest in diagnostics --------------------------

    def test_f8_no_raw_derived_digest(self):
        checks = [
            ("populated_winning_party_nif.json", "public-build", "X1234567Z"),
            ("credential_token.json", "public-build", "aB3dEf6hIj9kLmN0pQrS"),
        ]
        for fname, surface, raw in checks:
            with self.subTest(fixture=fname):
                path = PRIVACY_FIXTURES_DIR / fname
                digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
                for argv in (["--fixture", str(path), "--surface", surface],
                             ["--fixture", str(path), "--surface", surface, "--json"]):
                    _c, out, _e = self.run_cli(argv)
                    self.assertNotIn(digest, out,
                                     f"{fname}: raw-derived digest must not appear")

    # --- F9: fixture-not-found must not echo an operator path --------------

    def test_f9_missing_fixture_no_path_echo(self):
        secret_dir = "K:\\DEVKIT\\_private_synthetic_dir\\hidden"
        fake = secret_dir + "\\does_not_exist_synthetic.json"
        code, out, err = self.run_cli(["--fixture", fake, "--surface", "public-build"])
        self.assertEqual(code, 1)
        blob = out + err
        for leak in ("_private_synthetic_dir", "DEVKIT", secret_dir, "hidden"):
            self.assertNotIn(leak, blob, f"{leak!r} must not be echoed")

    # --- F10: safe source attribution + source-aware dedup -----------------

    def test_f10_source_present_in_findings(self):
        findings = pv.validate_json_object(
            {"email": "x@synthetic.test"}, pv.SURFACE_PUBLIC, source="alpha.json")
        self.assertTrue(findings)
        self.assertTrue(all(f.source == "alpha.json" for f in findings))

    def test_f10_identical_pointer_two_sources_distinct(self):
        # A single-rule record whose key is NOT itself redacted, so the pointer
        # is stable: the same rule + same pointer emitted from two source labels
        # must dedup to two distinct rows (not be merged together).
        obj = {"content": "raw upstream body retained"}
        fa = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, source="alpha.json")
        fb = pv.validate_json_object(obj, pv.SURFACE_PUBLIC, source="beta.json")
        self.assertEqual(len(fa), 1)  # exactly one finding per source
        self.assertEqual(fa[0].pointer, "$/content")
        rows = pv._dedup(fa + fb)
        self.assertEqual({f.source for f, _c in rows}, {"alpha.json", "beta.json"})
        self.assertEqual(len(rows), 2)  # same rule+pointer, two sources -> not merged
        self.assertTrue(all(f.pointer == "$/content" for f, _c in rows))

    # --- malformed input + structural failures ----------------------------

    def test_malformed_json_exit_1(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bad = Path(tmp.name) / "malformed.json"
        bad.write_text("{ not: valid json,,, ", encoding="utf-8")
        code, _out, err = self.run_cli(["--fixture", str(bad), "--surface", "public-build"])
        self.assertEqual(code, 1)
        self.assertIn("[PARSE]", err)

    def test_missing_fixture_exit_1(self):
        code, _out, _err = self.run_cli(
            ["--fixture", str(PRIVACY_FIXTURES_DIR / "does_not_exist.json"),
             "--surface", "public-build"])
        self.assertEqual(code, 1)

    def test_usage_conflict_exit_1(self):
        code, _out, _err = self.run_cli(["--validate-public", "--fixture", "x.json"])
        self.assertEqual(code, 1)

    # --- current public production: WARN-only, exit 0 ---------------------

    def test_validate_public_report_only_exit_zero(self):
        code, out, _err = self.run_cli(["--validate-public", "--report-only"])
        self.assertEqual(code, 0, "current public production must not contain a hard ERROR")
        self.assertIn("errors=0", out)

    def test_validate_public_creates_no_files(self):
        before = _snapshot_many(pv.public_surface_paths())
        self.run_cli(["--validate-public", "--report-only"])
        self.run_cli(["--validate-public", "--json"])
        after = _snapshot_many(pv.public_surface_paths())
        self.assertEqual(before, after, "public validation must not modify any scanned file")

    # =========================================================================
    # Prompt 246 foundation FINAL CORRECTION (v0.3): F1-F9. These test method
    # names are prefixed test_p246_ to avoid colliding with the F1-F10 labels
    # already used above for the prior baseline round.
    # =========================================================================

    # --- P246 F1: value-shaped dictionary KEYS are redacted + flagged ------

    def test_p246_f1_value_shaped_keys_redacted_and_flagged(self):
        checks = [
            ("dni_shaped_key.json", "12345678Z"),
            ("credential_shaped_key.json", "AKIA0000000000000000"),
            ("absolute_path_shaped_key.json", "K:\\DEVKIT\\private_synthetic\\secret.txt"),
        ]
        for fname, raw_key in checks:
            with self.subTest(fixture=fname):
                path = PRIVACY_FIXTURES_DIR / fname
                for argv in (["--fixture", str(path), "--surface", "public-build"],
                             ["--fixture", str(path), "--surface", "public-build", "--json"]):
                    code, out, err = self.run_cli(argv)
                    self.assertEqual(code, 2)
                    self.assertNotIn(raw_key, out)
                    self.assertNotIn(raw_key, err)
                    self.assertIn("redacted_key", out)

    def test_p246_f1_canonical_schema_key_names_unaffected(self):
        # Canonical safe key names (winning_party_nif, content, source_errors,
        # email, password) keep their existing rule label / redaction path;
        # this correction does not change their behaviour.
        for key in ("winning_party_nif", "content", "source_errors", "email", "password"):
            with self.subTest(key=key):
                obj = {key: "value-present-p246-f1"}
                n_err, _ = _severity_counts(
                    pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
                self.assertGreaterEqual(n_err, 1, f"{key!r} must still be flagged")

    # --- P246 F2: source label sanitization enforced by the library API ----

    def test_p246_f2_source_sanitization(self):
        cases = [
            ("K:\\DEVKIT\\private_synthetic\\report.json", "report.json"),
            ("/home/operador_synthetic/private/report.json", "report.json"),
            ("AKIA0000000000000000.json", "<source>"),
            ("data/licitaciones.json", "data/licitaciones.json"),
            ("clean_minimal.json", "clean_minimal.json"),
        ]
        for raw_source, expected in cases:
            with self.subTest(raw_source=raw_source):
                findings = pv.validate_json_object(
                    {"email": "x@synthetic.test"}, pv.SURFACE_PUBLIC, source=raw_source)
                self.assertTrue(findings)
                for f in findings:
                    self.assertEqual(f.source, expected)
                    self.assertNotIn("DEVKIT", f.source)
                    self.assertNotIn("operador_synthetic", f.source)

    # --- P246 F3: forward-slash Windows absolute paths ----------------------

    def test_p246_f3_forward_slash_windows_path_detected(self):
        for text in ("C:/Users/Operator/file.json", "K:/DEVKIT/private_synthetic/file.txt"):
            with self.subTest(text=text):
                obj = {"url": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{text!r} must be detected as a Windows absolute path")

    def test_p246_f3_drive_relative_text_not_flagged(self):
        for text in ("Drive C: is full", "Section C:1.2 addendum", "Ratio A:B only"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not be flagged as an absolute path")

    # --- P246 F4: context-aware URI policy ----------------------------------

    def test_p246_f4_dangerous_scheme_embedded_anywhere(self):
        cases = [
            "See javascript:alert(1)",
            "Document: data:text/plain,x",
            "Mirror ftp://example.test/file",
            "Internal http://127.0.0.1/x",
            "Internal http://[::1]/x",
        ]
        for text in cases:
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{text!r} must be rejected regardless of key context")

    def test_p246_f4_url_like_key_requires_valid_http(self):
        for value in ("custom:payload", "http:payload"):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{value!r} under a url-like key must be rejected")

    def test_p246_f4_ordinary_colon_prose_still_passes(self):
        obj = {"nota": "Data: 2026-01-01", "canonical_key": "Expedient:123"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    # --- P246 F5: unknown trust surface fails closed ------------------------

    def test_p246_f5_invalid_surface_raises(self):
        with self.assertRaises(pv.PrivacyValidatorUsageError):
            pv.validate_json_object({"a": "b"}, "public_build")  # typo, not a real surface

    # --- P246 F6: structural exceptions fail closed, no traceback/path -----

    def test_p246_f6_invalid_utf8_exit_1_no_traceback(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bad = Path(tmp.name) / "badenc.json"
        bad.write_bytes(b'{"a": "\xff\xfe bad bytes"}')
        code, _out, err = self.run_cli(["--fixture", str(bad), "--surface", "public-build"])
        self.assertEqual(code, 1)
        self.assertIn("[PARSE]", err)
        self.assertNotIn(str(bad), err)
        self.assertNotIn("Traceback", err)

    def test_p246_f6_recursion_depth_exit_1_no_traceback(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        deep = Path(tmp.name) / "deep.json"
        n = 4000
        deep.write_text(("{\"a\":" * n) + "1" + ("}" * n), encoding="utf-8")
        code, _out, err = self.run_cli(["--fixture", str(deep), "--surface", "public-build"])
        self.assertEqual(code, 1)
        self.assertIn("[STRUCTURAL]", err)
        self.assertNotIn(str(deep), err)
        self.assertNotIn("Traceback", err)

    def test_p246_f6_unexpected_exception_fail_closed(self):
        class _BoomError(Exception):
            pass

        def _boom(*_a, **_kw):
            raise _BoomError("synthetic secret K:\\DEVKIT\\private_synthetic\\leak.txt")

        fixture = PRIVACY_FIXTURES_DIR / "clean_minimal.json"
        orig = pv.validate_json_object
        pv.validate_json_object = _boom
        try:
            code, _out, err = self.run_cli(
                ["--fixture", str(fixture), "--surface", "public-build"])
        finally:
            pv.validate_json_object = orig
        self.assertEqual(code, 1)
        self.assertIn("[STRUCTURAL]", err)
        self.assertIn("_BoomError", err)  # exception class only
        self.assertNotIn("secret", err)
        self.assertNotIn("leak.txt", err)
        self.assertNotIn("DEVKIT", err)

    # --- P246 F7: contextual phone/DNI-NIE detection under a label ---------

    def test_p246_f7_labeled_phone_without_plus_detected(self):
        for text in ("Tel: 612 345 678", "Contacte 612 345 678"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 1)

    def test_p246_f7_unlabeled_national_number_still_passes(self):
        obj = {"nota": "612 345 678", "canonical_key": "612 345 678"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    def test_p246_f7_labeled_dni_nie_variants_detected(self):
        for text in ("DNI-12345678Z", "NIE: X1234567Z"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 1)

    def test_p246_f7_unlabeled_reference_code_still_passes(self):
        obj = {"nota": "2099/SYNTH0777/00004284E", "canonical_key": "2099/SYNTH0777/00004284E"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    # --- P246 F9: bounded --summary-only reporting --------------------------

    def _mixed_severity_fixture(self):
        # ERROR (CREDENTIAL_KEY: password) + WARN (RELATIVE_TMP_PATH) in one
        # small synthetic object, so full vs. summary-mode comparisons don't
        # need a --validate-public production scan (P246 v0.4 F4).
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        fixture = Path(tmp.name) / "mixed_severity.json"
        fixture.write_text(json.dumps({
            "password": "n0tAreal-secret-0001",
            "nota": "backup ref data/_backup/2026 file",
        }), encoding="utf-8")
        return fixture

    def test_p246_f9_summary_only_matches_totals_and_exit_code(self):
        # P246 v0.4 F4: replaces the prior version of this test, which
        # invoked --validate-public twice (an expensive repeated production
        # scan). Uses a synthetic fixture instead.
        fixture = self._mixed_severity_fixture()
        argv = ["--fixture", str(fixture), "--surface", "public-build"]
        code_full, out_full, _e1 = self.run_cli(argv)
        code_summary, out_summary, _e2 = self.run_cli(argv + ["--summary-only"])
        self.assertEqual(code_full, code_summary)
        self.assertEqual(code_full, 2)
        m_full = re.search(r"errors=(\d+) warnings=(\d+)", out_full)
        m_summary = re.search(r"errors=(\d+) warnings=(\d+)", out_summary)
        self.assertIsNotNone(m_full)
        self.assertIsNotNone(m_summary)
        self.assertEqual(m_full.groups(), m_summary.groups())
        self.assertEqual(m_full.groups(), ("1", "1"))
        self.assertLessEqual(out_summary.count("\n"), out_full.count("\n"))

    def test_p246_f9_summary_only_no_raw_values_or_pointers(self):
        path = PRIVACY_FIXTURES_DIR / "credential_token.json"
        code, out, _err = self.run_cli(
            ["--fixture", str(path), "--surface", "public-build", "--summary-only"])
        self.assertEqual(code, 2)
        self.assertNotIn("aB3dEf6hIj9kLmN0pQrS", out)
        self.assertNotIn("$/", out)  # no JSON-pointer detail in bounded mode

    def test_p246_f9_summary_only_json_shape(self):
        path = PRIVACY_FIXTURES_DIR / "credential_token.json"
        code, out, _err = self.run_cli(
            ["--fixture", str(path), "--surface", "public-build",
             "--summary-only", "--json"])
        self.assertEqual(code, 2)
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "ADGOPS_PRIVACY_VALIDATOR_SUMMARY_V1")
        self.assertIn("groups", payload)
        # P246 v0.4 F4: bounded JSON summary also carries distinct_count /
        # group_count (in addition to error_count / warn_count / groups).
        self.assertIn("distinct_count", payload)
        self.assertIn("group_count", payload)
        self.assertEqual(payload["group_count"], len(payload["groups"]))
        for g in payload["groups"]:
            self.assertEqual(set(g), {"severity", "rule_id", "source", "count"})

    def test_p246_v04_f4_summary_text_fields_present(self):
        path = PRIVACY_FIXTURES_DIR / "credential_token.json"
        code, out, _err = self.run_cli(
            ["--fixture", str(path), "--surface", "public-build", "--summary-only"])
        self.assertEqual(code, 2)
        self.assertIn("errors=", out)
        self.assertIn("warnings=", out)
        self.assertIn("distinct=", out)
        self.assertIn("groups=", out)

    def test_p246_v04_f4_distinct_and_group_counts_match_detail(self):
        fixture = self._mixed_severity_fixture()
        findings = pv.validate_path_read_only(fixture, pv.SURFACE_PUBLIC)
        expected_rows = pv._dedup(findings)
        expected_groups = pv._grouped_summary(findings)

        code, out, _err = self.run_cli(
            ["--fixture", str(fixture), "--surface", "public-build",
             "--summary-only", "--json"])
        self.assertEqual(code, 2)
        payload = json.loads(out)
        self.assertEqual(payload["distinct_count"], len(expected_rows))
        self.assertEqual(payload["group_count"], len(expected_groups))
        self.assertEqual(payload["group_count"], len(payload["groups"]))

    def test_p246_f9_summary_only_does_not_change_exit_code(self):
        for fname, surface, expect in (("clean_minimal.json", "public-build", 0),
                                        ("public_warning_only.json", "public-build", 0),
                                        ("credential_token.json", "public-build", 2)):
            with self.subTest(fixture=fname):
                path = PRIVACY_FIXTURES_DIR / fname
                code_full, _o1, _e1 = self.run_cli(
                    ["--fixture", str(path), "--surface", surface])
                code_summary, _o2, _e2 = self.run_cli(
                    ["--fixture", str(path), "--surface", surface, "--summary-only"])
                self.assertEqual(code_full, expect)
                self.assertEqual(code_summary, expect)

    # =========================================================================
    # Prompt 246 v0.4 MICRO-CORRECTION: four remaining contract gaps found by
    # static companion review of the v0.3 implementation. Test names are
    # prefixed test_p246_v04_ to avoid colliding with the test_p246_f1..f9
    # names already used above for the prior (v0.3) correction round.
    # =========================================================================

    # --- P246 v0.4 F1: url-like fields must be a valid absolute http(s) URL

    def test_p246_v04_f1_url_like_field_rejects_non_url_forms(self):
        for value in ("example.test/file", "not a url", "http://", "http:///path"):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{value!r} under a url-like key must be rejected")

    def test_p246_v04_f1_url_like_field_accepts_valid_https(self):
        obj = {"url": "https://example.test/path"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    def test_p246_v04_f1_url_like_field_empty_or_null_still_allowed(self):
        for value in ("", None):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    def test_p246_v04_f1_dangerous_url_in_prose_still_detected(self):
        # F1 must not weaken scanning of dangerous URLs embedded in ordinary
        # non-url-like text.
        obj = {"nota": "See javascript:alert(1)"}
        self.assertGreaterEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 1)

    # --- P246 v0.4 F2: any credible data: scheme token is dangerous --------

    def test_p246_v04_f2_data_scheme_without_comma_detected(self):
        for text in ("data:payload", "See data:payload"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{text!r} must be detected as a dangerous data: token")

    def test_p246_v04_f2_data_label_prose_still_passes(self):
        obj = {"nota": "Data: 2026-01-01"}
        self.assertEqual(
            _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0], 0)

    # --- P246 v0.4 F3: private-host classification covers all non-public
    # IP classes (IPv4 + IPv6) ------------------------------------------------

    def test_p246_v04_f3_all_nonpublic_ip_classes_rejected(self):
        for url in ("http://0.0.0.0/x", "http://240.0.0.1/x",
                    "http://[::]/x", "http://[ff02::1]/x"):
            with self.subTest(url=url):
                obj = {"url": url}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{url!r} must be rejected as a non-public host")

    def test_p246_v04_f3_hostname_protections_unaffected(self):
        for url in ("http://localhost/x", "http://localhost./x",
                    "http://sub.localhost/x", "http://svc.local/x",
                    "http://svc.internal/x"):
            with self.subTest(url=url):
                obj = {"url": url}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{url!r} must still be rejected")

    # =========================================================================
    # Prompt 246 v0.5 MICRO-CORRECTION: static audit proved urlsplit() alone
    # does not validate authority syntax, so a url-like field with a
    # malformed authority slipped past v0.4 F1. Test names are prefixed
    # test_p246_v05_ to avoid colliding with the v0.4 names above.
    # =========================================================================

    # --- P246 v0.5 F1: url-like fields must have a syntactically valid
    # authority (no embedded whitespace/backslash, valid host, valid port) --

    def test_p246_v05_f1_url_like_field_rejects_malformed_authority(self):
        for value in (
            "https://not a url",
            "https://exa mple.com/path",
            "https://example.com extra",
            "https://.",
            "https://-bad-.com",
            "https://example..com",
            "https://example.com:abc/x",
            "https://example.com\\evil",
        ):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{value!r} under a url-like key must be rejected")

    def test_p246_v05_f1_url_like_field_accepts_well_formed_authority(self):
        for value in (
            "https://example.test/path",
            "https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930",
            "https://8.8.8.8/path",
        ):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{value!r} under a url-like key must not be a hard error")

    def test_p246_v05_f1_private_host_detection_unaffected(self):
        for url in ("http://127.0.0.1/x", "http://[::1]/x", "http://localhost./x"):
            with self.subTest(url=url):
                obj = {"url": url}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{url!r} must still be rejected as a non-public host")

    # =========================================================================
    # Prompt 246 v0.6 MICRO-CORRECTION: static audit proved the v0.5 whitespace/
    # control-character loop ran over `value.strip()` rather than the original
    # `value`, so leading/trailing whitespace (and non-Cc format characters
    # such as U+200B) were normalized away before inspection. Test names are
    # prefixed test_p246_v06_ to avoid colliding with the v0.4/v0.5 names above.
    # =========================================================================

    # --- P246 v0.6 F1: forbidden raw-value characters must be checked on the
    # original (unstripped) value, and the "C*" Unicode category band -------

    def test_p246_v06_f1_url_like_field_rejects_raw_whitespace_and_format_chars(self):
        zwsp = chr(0x200B)  # ZERO WIDTH SPACE, Unicode category Cf
        for value in (
            " https://example.test/path",
            "https://example.test/path ",
            "https://example.test/path\t",
            "https://example.test/path\n",
            "https://example.test/" + zwsp + "path",
            "https://exam" + zwsp + "ple.test/path",
        ):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{value!r} under a url-like key must be rejected")

    def test_p246_v06_f1_url_like_field_accepts_clean_values(self):
        for value in (
            "https://example.test/path",
            "https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930",
            "https://8.8.8.8/path",
        ):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{value!r} under a url-like key must not be a hard error")

    # =========================================================================
    # Prompt 246 v0.7 CORRECTION: static audit proved private/loopback hosts
    # written as browser-canonicalized IPv4 forms (decimal-integer,
    # octal-looking, hex, shortened, leading-zero) or with Unicode dot/
    # full-width-digit separators were classified as public DNS by the
    # Python-only raw-host checks. Test names are prefixed test_p246_v07_ to
    # avoid colliding with the v0.4/v0.5/v0.6 names above.
    # =========================================================================

    # --- P246 v0.7 F1: canonicalized/obfuscated IPv4 hosts must be rejected,
    # under both a url-like field and embedded in ordinary text -------------

    def test_p246_v07_f1_url_like_field_rejects_canonicalized_ipv4(self):
        ideographic_dot = chr(0x3002)       # U+3002 IDEOGRAPHIC FULL STOP
        fullwidth_dot = chr(0xFF0E)         # U+FF0E FULLWIDTH FULL STOP
        halfwidth_dot = chr(0xFF61)         # U+FF61 HALFWIDTH IDEOGRAPHIC FULL STOP
        fw1, fw2, fw7, fw0 = chr(0xFF11), chr(0xFF12), chr(0xFF17), chr(0xFF10)
        fullwidth_127 = fw1 + fw2 + fw7
        for value in (
            "http://2130706433/",
            "http://017700000001/",
            "http://0x7f000001/",
            "http://127.1/",
            "http://127.0.1/",
            "http://127.0.0.01/",
            "http://0300.0250.0001.0001/",
            "http://0xc0.0xa8.0x1.0x1/",
            "http://127" + ideographic_dot + "0" + ideographic_dot + "0"
            + ideographic_dot + "1/",
            "http://127" + fullwidth_dot + "0" + fullwidth_dot + "0"
            + fullwidth_dot + "1/",
            "http://127" + halfwidth_dot + "0" + halfwidth_dot + "0"
            + halfwidth_dot + "1/",
            "http://" + fullwidth_127 + "." + fw0 + "." + fw0 + "." + fw1 + "/",
            "http://localhost" + ideographic_dot + "/",
        ):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{value!r} under a url-like key must be rejected")

    def test_p246_v07_f1_embedded_canonicalized_ipv4_rejected(self):
        ideographic_dot = chr(0x3002)
        for text in (
            "Internal http://2130706433/x",
            "Internal http://127" + ideographic_dot + "0" + ideographic_dot
            + "0" + ideographic_dot + "1/x",
            "Internal http://localhost" + ideographic_dot + "/x",
        ):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{text!r} embedded in ordinary text must be rejected")

    def test_p246_v07_f1_url_like_field_accepts_valid_public_hosts(self):
        u_umlaut = chr(0x00FC)  # U+00FC LATIN SMALL LETTER U WITH DIAERESIS
        for value in (
            "https://example.test/path",
            "https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930",
            "https://8.8.8.8/path",
            "https://[2001:4860:4860::8888]/path",
            "https://b" + u_umlaut + "cher.de/path",
            "https://example.com./path",
            "https://123.com/path",
        ):
            with self.subTest(value=value):
                obj = {"url": value}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{value!r} under a url-like key must not be a hard error")

    def test_p246_v07_f1_private_host_detection_unaffected(self):
        for url in (
            "http://127.0.0.1/x", "http://[::1]/x",
            "http://0.0.0.0/x", "http://240.0.0.1/x",
            "http://[::]/x", "http://[ff02::1]/x",
            "http://localhost./x", "http://svc.local/x", "http://svc.internal/x",
        ):
            with self.subTest(url=url):
                obj = {"url": url}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{url!r} must still be rejected as a non-public host")

    # =========================================================================
    # Prompt 246 v0.8 FINAL CORRECTION: static audit proved _EMBEDDED_HTTP_RE
    # only recognized the exact "http://"/"https://" separator, so a private
    # host embedded via browser/WHATWG special-URL-canonicalized zero/one/
    # three-or-more slash/backslash forms ("http:127.0.0.1/x",
    # "http:\\127.0.0.1\\x", ...) produced zero hard finding. Test names are
    # prefixed test_p246_v08_ to avoid colliding with the v0.4-v0.7 names.
    # =========================================================================

    # --- P246 v0.8: bounded embedded private-host matrix (2 schemes x 14
    # separator forms x 5 private/unsafe host forms = 140 cases) ------------

    def test_p246_v08_embedded_private_special_http_matrix(self):
        ideographic_dot = chr(0x3002)  # U+3002 IDEOGRAPHIC FULL STOP
        separators = [
            "", "/", "//", "///", "////",
            "\\", "\\\\", "/\\", "\\/", "/\\\\", "\\//", "//\\", "\\\\/",
            "////\\",
        ]
        hosts = [
            "127.0.0.1",
            "2130706433",
            "0x7f000001",
            "127" + ideographic_dot + "0" + ideographic_dot + "0"
            + ideographic_dot + "1",
            "localhost" + ideographic_dot,
        ]
        for scheme in ("http", "https"):
            for sep in separators:
                for host in hosts:
                    token = f"{scheme}:{sep}{host}/x"
                    with self.subTest(token=token):
                        obj = {"nota": f"Internal {token}"}
                        n_err, _ = _severity_counts(
                            pv.validate_json_object(obj, pv.SURFACE_PUBLIC))
                        self.assertGreaterEqual(
                            n_err, 1, f"{token!r} must produce a hard ERROR")

    # --- P246 v0.8: public embedded hosts under odd special-scheme
    # separators must NOT create a false privacy finding -------------------

    def test_p246_v08_embedded_public_retention(self):
        u_umlaut = chr(0x00FC)  # U+00FC LATIN SMALL LETTER U WITH DIAERESIS
        for text in (
            "Internal http://example.test/x",
            "Internal http:example.test/x",
            "Internal http:/example.test/x",
            "Internal http:///example.test/x",
            "Internal http:\\example.test\\x",
            "Internal https:8.8.8.8/x",
            "Internal https:///b" + u_umlaut + "cher.de/x",
        ):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a URL rule")

    # --- P246 v0.8: invalid authority / embedded-credential forms ----------

    def test_p246_v08_invalid_and_credential_forms_rejected(self):
        for text in (
            "Internal http:////",
            "Internal http:/user:pass@127.0.0.1/x",
            "Internal http:\\user:pass@127.0.0.1\\x",
            "Internal https:///example.com:abc/x",
        ):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{text!r} must be rejected")

    # --- P246 v0.8: ordinary "HTTP: " prose must remain clean --------------

    def test_p246_v08_prose_false_positives_still_pass(self):
        for text in ("HTTP: 2026 status", "HTTPS: servei actiu",
                     "Nota HTTP: document pendent"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a URL rule")

    # --- P246 v0.8: dictionary keys shaped like an embedded private token --

    def test_p246_v08_key_shaped_embedded_tokens_flagged_and_redacted(self):
        ideographic_dot = chr(0x3002)
        keys = [
            "Internal http:2130706433/x",
            "Internal http:/127" + ideographic_dot + "0" + ideographic_dot
            + "0" + ideographic_dot + "1/x",
        ]
        for key_text in keys:
            with self.subTest(key=key_text):
                obj = {key_text: "value-present"}
                findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
                n_err, _ = _severity_counts(findings)
                self.assertGreaterEqual(n_err, 1, f"{key_text!r} must be detected")
                for f in findings:
                    self.assertNotIn(key_text, f.pointer)

    # =========================================================================
    # Prompt 246 v0.8.1 MICRO-CORRECTION: static audit proved the v0.8
    # boundary set `(?:^|(?<=[\s"'(<,;]))` missed credible embedded HTTP(S)
    # tokens preceded by other non-word punctuation (":", "-", "=", "[",
    # "|", ...). Test names are prefixed test_p246_v081_ to avoid colliding
    # with the v0.8 names above.
    # =========================================================================

    # --- P246 v0.8.1: non-word-punctuation-preceded tokens now detected ----

    def test_p246_v081_private_boundary_forms_rejected(self):
        ideographic_dot = chr(0x3002)
        for text in (
            "Internal:http://127.0.0.1/x",
            "Internal-http://127.0.0.1/x",
            "ref=https:///2130706433/x",
            "[https:/127" + ideographic_dot + "0" + ideographic_dot + "0"
            + ideographic_dot + "1/x]",
            "key|http:\\localhost" + ideographic_dot + "\\x",
            "(http:0x7f000001/x)",
            "\"https:\\\\127.0.0.1\\x\"",
        ):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertGreaterEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    1, f"{text!r} must be rejected")

    # --- P246 v0.8.1: same boundary forms with a public host stay clean ----

    def test_p246_v081_public_boundary_forms_retained(self):
        u_umlaut = chr(0x00FC)
        for text in (
            "Internal:http://example.test/x",
            "Internal-http://example.test/x",
            "ref=https:///8.8.8.8/x",
            "[https:/b" + u_umlaut + "cher.de/x]",
            "key|http:\\example.test\\x",
        ):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a URL rule")

    # --- P246 v0.8.1: scheme glued into a word/identifier is not a token ---

    def test_p246_v081_word_glued_pseudo_tokens_not_matched(self):
        for text in (
            "abchttp://127.0.0.1/x",
            "foo_https://127.0.0.1/x",
            "123http:127.0.0.1/x",
        ):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not be treated as an embedded HTTP token")

    # --- P246 v0.8.1: ordinary "HTTP: " prose remains clean ----------------

    def test_p246_v081_prose_still_retained(self):
        for text in ("HTTP: 2026 status", "HTTPS: servei actiu",
                     "Nota HTTP: document pendent"):
            with self.subTest(text=text):
                obj = {"nota": text}
                self.assertEqual(
                    _severity_counts(pv.validate_json_object(obj, pv.SURFACE_PUBLIC))[0],
                    0, f"{text!r} must not trip a URL rule")

    # --- P246 v0.8.1: key-shaped boundary forms flagged + redacted ---------

    def test_p246_v081_key_shaped_boundary_forms_flagged_and_redacted(self):
        ideographic_dot = chr(0x3002)
        keys = [
            "Internal:http://2130706433/x",
            "ref-https:/127" + ideographic_dot + "0" + ideographic_dot + "0"
            + ideographic_dot + "1/x",
        ]
        for key_text in keys:
            with self.subTest(key=key_text):
                obj = {key_text: "value-present"}
                findings = pv.validate_json_object(obj, pv.SURFACE_PUBLIC)
                n_err, _ = _severity_counts(findings)
                self.assertGreaterEqual(n_err, 1, f"{key_text!r} must be detected")
                for f in findings:
                    self.assertNotIn(key_text, f.pointer)


# ---------------------------------------------------------------------------
# Runner with production-file no-touch proof
# ---------------------------------------------------------------------------

def _snapshot(path: Path):
    if not path.exists():
        return None
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return (h, path.stat().st_mtime_ns)


def _snapshot_many(paths):
    return {str(p): _snapshot(p) for p in paths}


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])

    # No-touch proof covers every production JSON file the suite reads: the
    # scheduled-fetcher data file plus every public surface the privacy
    # validator scans (sha256 + mtime, before and after).
    proof_paths = list(dict.fromkeys([DATA_FILE, *pv.public_surface_paths()]))
    before = _snapshot_many(proof_paths)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    after = _snapshot_many(proof_paths)

    if any(v is None for v in before.values()) or any(v is None for v in after.values()):
        untouched = "unknown"
    elif before == after:
        untouched = "yes"
    else:
        untouched = "no"

    n = result.testsRun
    passed = result.wasSuccessful() and untouched == "yes"
    verdict = "PASS" if passed else "FAIL"
    print(f"REGRESSION: {verdict} ({n} cases, data file untouched: {untouched})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
