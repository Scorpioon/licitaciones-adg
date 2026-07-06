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
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures" / "fetcher"
DATA_FILE = REPO_ROOT / "data" / "licitaciones.json"

import tools.scheduled_fetch_merge as sfm  # noqa: E402
import tools.scheduled_run_classify as src  # noqa: E402

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
# Runner with production-file no-touch proof
# ---------------------------------------------------------------------------

def _snapshot(path: Path):
    if not path.exists():
        return None
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return (h, path.stat().st_mtime_ns)


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])

    before = _snapshot(DATA_FILE)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    after = _snapshot(DATA_FILE)

    if before is None or after is None:
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
