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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures" / "fetcher"
PRIVACY_FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures" / "privacy"
DATA_FILE = REPO_ROOT / "data" / "licitaciones.json"

import tools.scheduled_fetch_merge as sfm  # noqa: E402
import tools.scheduled_run_classify as src  # noqa: E402
import tools.scheduled_candidate_policy as scp  # noqa: E402
import tools.privacy_validator as pv  # noqa: E402
import tools.canonical_tender_merge as ctm  # noqa: E402
import tools.link_check_resolver as lcr  # noqa: E402
import tools.fetch_bounds as fetch_bounds  # noqa: E402 - Prompt 323 Stage B
import fetch_licitaciones as fl  # noqa: E402 - Prompt 323 Stage B
import tools.run_receipt as run_receipt  # noqa: E402 - Prompt 324 Stage B
import tools.acquisition_staging as acquisition_staging  # noqa: E402 - WRKOPS t_20261004_adgops335

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

    # --- B21 deadline-blind lifecycle repair --------------------------------
    # WRKOPS t_20261002_adgops332 / P331 Group C (CANDIDATE-F-5): lifecycle
    # eligibility must consume the stored submission deadline (`data_limit`).
    # Deadline expiry alone must demote operational eligibility/review state
    # only -- it must never be rewritten as award, cancellation, desertion,
    # or any other official lifecycle status.

    _REF_DATE = date(2026, 10, 2)

    def test_is_deadline_expired_past_date(self):
        self.assertTrue(sfm.is_deadline_expired("2026-01-01", self._REF_DATE))

    def test_is_deadline_expired_future_date(self):
        self.assertFalse(sfm.is_deadline_expired("2027-01-01", self._REF_DATE))

    def test_is_deadline_expired_same_day_not_expired(self):
        self.assertFalse(sfm.is_deadline_expired("2026-10-02", self._REF_DATE))

    def test_is_deadline_expired_missing_value(self):
        self.assertFalse(sfm.is_deadline_expired("", self._REF_DATE))
        self.assertFalse(sfm.is_deadline_expired(None, self._REF_DATE))

    def test_is_deadline_expired_malformed_value(self):
        self.assertFalse(sfm.is_deadline_expired("not-a-date", self._REF_DATE))

    def test_classify_lifecycle_expired_vigente_no_award_demoted(self):
        rec = {"estat": "Vigente", "data_limit": "2026-01-01"}
        category, active, review = sfm.classify_lifecycle(rec, self._REF_DATE)
        self.assertEqual(category, sfm.DEADLINE_EXPIRED_CATEGORY)
        self.assertFalse(active)
        self.assertTrue(review)
        # Official status must be untouched by the demotion.
        self.assertEqual(rec["estat"], "Vigente")

    def test_classify_lifecycle_future_deadline_vigente_stays_open(self):
        rec = {"estat": "Vigente", "data_limit": "2027-01-01"}
        category, active, review = sfm.classify_lifecycle(rec, self._REF_DATE)
        self.assertEqual(category, "CLEAR_OPEN")
        self.assertTrue(active)
        self.assertFalse(review)

    def test_classify_lifecycle_expired_with_award_evidence_not_demoted(self):
        # Award evidence dominates: must classify as awarded, not deadline-expired.
        rec = {"estat": "Vigente", "data_limit": "2026-01-01", "adjudicatari": "ACME SA"}
        category, active, review = sfm.classify_lifecycle(rec, self._REF_DATE)
        self.assertEqual(category, "OPEN_WITH_AWARD_EVIDENCE")
        self.assertFalse(active)

    def test_classify_lifecycle_missing_deadline_no_false_closure(self):
        rec = {"estat": "Vigente", "data_limit": ""}
        category, active, review = sfm.classify_lifecycle(rec, self._REF_DATE)
        self.assertEqual(category, "CLEAR_OPEN")
        self.assertTrue(active)

    def test_resolve_overlap_lifecycle_expired_vigente_no_award_demoted(self):
        prod_rec = {"lifecycle_category": "CLEAR_OPEN", "active_opportunity_eligible": True}
        cand_rec = {"estat": "Vigente", "data_limit": "2026-01-01"}
        lc = sfm.resolve_overlap_lifecycle(prod_rec, cand_rec, self._REF_DATE)
        self.assertEqual(lc["category"], sfm.DEADLINE_EXPIRED_CATEGORY)
        self.assertFalse(lc["active"])
        self.assertTrue(lc["review"])

    def test_resolve_overlap_lifecycle_future_deadline_stays_open(self):
        prod_rec = {"lifecycle_category": "CLEAR_OPEN", "active_opportunity_eligible": True}
        cand_rec = {"estat": "Vigente", "data_limit": "2027-01-01"}
        lc = sfm.resolve_overlap_lifecycle(prod_rec, cand_rec, self._REF_DATE)
        self.assertEqual(lc["category"], "CLEAR_OPEN")
        self.assertTrue(lc["active"])

    def test_resolve_overlap_lifecycle_expired_with_award_evidence_not_demoted(self):
        prod_rec = {"lifecycle_category": "CLEAR_OPEN", "active_opportunity_eligible": True}
        cand_rec = {"estat": "Adjudicado", "data_limit": "2026-01-01", "adjudicatari": "ACME SA"}
        lc = sfm.resolve_overlap_lifecycle(prod_rec, cand_rec, self._REF_DATE)
        self.assertEqual(lc["category"], "CLEAR_AWARDED")
        self.assertFalse(lc["active"])

    def test_resolve_overlap_lifecycle_missing_deadline_no_false_closure(self):
        prod_rec = {"lifecycle_category": "CLEAR_OPEN", "active_opportunity_eligible": True}
        cand_rec = {"estat": "Vigente", "data_limit": ""}
        lc = sfm.resolve_overlap_lifecycle(prod_rec, cand_rec, self._REF_DATE)
        self.assertEqual(lc["category"], "CLEAR_OPEN")
        self.assertTrue(lc["active"])

    def test_merge_overlap_expired_deadline_end_to_end_preserves_estat(self):
        prod_rec = {
            "contract_folder_id": "CFID-B21-1",
            "estat": "Vigente",
            "data_limit": "2026-01-01",
            "lifecycle_category": "CLEAR_OPEN",
            "active_opportunity_eligible": True,
            "lifecycle_review_required": False,
        }
        cand_rec = {
            "contract_folder_id": "CFID-B21-1",
            "estat": "Vigente",
            "data_limit": "2026-01-01",
        }
        merged, conflicts = sfm.merge_overlap(prod_rec, cand_rec, self._REF_DATE)
        self.assertEqual(merged["lifecycle_category"], sfm.DEADLINE_EXPIRED_CATEGORY)
        self.assertFalse(merged["active_opportunity_eligible"])
        self.assertTrue(merged["lifecycle_review_required"])
        # Official status fields are never rewritten by deadline expiry alone.
        self.assertEqual(merged["estat"], "Vigente")

    def test_lifecycle_integrity_accepts_deadline_expired_category(self):
        # The new category is inactive by construction, so it must never trip
        # the OPEN_WITH_AWARD_EVIDENCE+active=True invariant guard.
        recs = [{
            "contract_folder_id": "CFID-B21-2",
            "lifecycle_category": sfm.DEADLINE_EXPIRED_CATEGORY,
            "active_opportunity_eligible": False,
        }]
        ok, issues = sfm.validate_lifecycle_integrity(recs)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    # --- B16 Atom tombstone semantics repair --------------------------------
    # WRKOPS t_20261002_adgops333 / P331-B16: the official Atom feed's
    # deleted-entry tombstone (<at:deleted-entry ref="..." when="...">) must
    # be preserved and acted on so a matched identity cannot continue to be
    # represented as an ordinary active/current opportunity solely through
    # historical carry-forward. A tombstone is source-removal evidence only
    # -- never a legal cancellation, desertion, award, or closure.

    def test_extract_tombstone_refs_basic(self):
        refs = sfm.extract_tombstone_refs({
            "tombstones": [{"ref": "A-1", "when": "2026-09-01T00:00:00Z"}]
        })
        self.assertEqual(refs, {"A-1": "2026-09-01T00:00:00Z"})

    def test_extract_tombstone_refs_drops_malformed_and_empty(self):
        refs = sfm.extract_tombstone_refs({
            "tombstones": [
                {"ref": "", "when": "2026-09-01T00:00:00Z"},
                "not-a-dict",
                {"when": "2026-09-01T00:00:00Z"},
                {"ref": "A-2"},
            ]
        })
        self.assertEqual(refs, {"A-2": ""})

    def test_extract_tombstone_refs_first_occurrence_wins(self):
        refs = sfm.extract_tombstone_refs({
            "tombstones": [
                {"ref": "A-3", "when": "first"},
                {"ref": "A-3", "when": "second"},
            ]
        })
        self.assertEqual(refs["A-3"], "first")

    def test_extract_tombstone_refs_missing_key(self):
        self.assertEqual(sfm.extract_tombstone_refs({}), {})

    def test_apply_tombstone_consequence_demotes_open_identity(self):
        rec = {
            "id": "FIX-OPEN-001",
            "estat": "vigent",
            "adjudicatari": "",
            "lifecycle_category": "CLEAR_OPEN",
            "active_opportunity_eligible": True,
            "lifecycle_review_required": False,
        }
        out = sfm.apply_tombstone_consequence(rec, "2026-09-01T00:00:00Z")
        self.assertEqual(out["lifecycle_category"], sfm.TOMBSTONE_CATEGORY)
        self.assertFalse(out["active_opportunity_eligible"])
        self.assertTrue(out["lifecycle_review_required"])
        self.assertTrue(out["tombstone_ref_matched"])
        self.assertEqual(out["tombstone_observed_at"], "2026-09-01T00:00:00Z")
        # Raw source fidelity: no legal status synthesized.
        self.assertEqual(out["estat"], "vigent")
        self.assertEqual(out["adjudicatari"], "")

    def test_apply_tombstone_consequence_idempotent_on_repeat(self):
        rec = {"id": "FIX-OPEN-001", "estat": "vigent", "lifecycle_category": "CLEAR_OPEN",
               "active_opportunity_eligible": True, "lifecycle_review_required": False}
        once = sfm.apply_tombstone_consequence(rec, "2026-09-01T00:00:00Z")
        twice = sfm.apply_tombstone_consequence(once, "2026-09-05T00:00:00Z")
        self.assertEqual(twice["lifecycle_category"], sfm.TOMBSTONE_CATEGORY)
        self.assertFalse(twice["active_opportunity_eligible"])
        # First-seen timestamp is preserved, not overwritten by a later re-application.
        self.assertEqual(twice["tombstone_observed_at"], "2026-09-01T00:00:00Z")

    def test_apply_tombstone_consequence_conservative_for_already_awarded(self):
        rec = {
            "id": "FIX-AWARD-001",
            "estat": "adjudicada",
            "adjudicatari": "Empresa Sintetica SL",
            "lifecycle_category": "CLEAR_AWARDED",
            "active_opportunity_eligible": False,
            "lifecycle_review_required": False,
        }
        out = sfm.apply_tombstone_consequence(rec, "2026-09-01T00:00:00Z")
        # Stronger existing evidence is never downgraded/relabeled.
        self.assertEqual(out["lifecycle_category"], "CLEAR_AWARDED")
        self.assertFalse(out["active_opportunity_eligible"])
        self.assertEqual(out["adjudicatari"], "Empresa Sintetica SL")
        # Provenance is still recorded.
        self.assertTrue(out["tombstone_ref_matched"])

    def test_lifecycle_integrity_rejects_unsafe_active_tombstone(self):
        bad = [{
            "contract_folder_id": "CFID-TOMB-BAD",
            "lifecycle_category": sfm.TOMBSTONE_CATEGORY,
            "active_opportunity_eligible": True,
        }]
        ok, issues = sfm.validate_lifecycle_integrity(bad)
        self.assertFalse(ok)
        self.assertTrue(issues)

    # --- B16 end-to-end: run_merge_dry_run production-only branch ----------

    def test_dryrun_tombstone_demotes_known_active_identity(self):
        out = self.tmp / "out.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_open_identity.json", out))
        merged = {r["id"]: r for r in json.loads(out.read_text(encoding="utf-8"))["data"]}
        rec = merged["FIX-OPEN-001"]
        self.assertEqual(rec["lifecycle_category"], sfm.TOMBSTONE_CATEGORY)
        self.assertFalse(rec["active_opportunity_eligible"])
        self.assertTrue(rec["lifecycle_review_required"])
        self.assertTrue(rec.get("tombstone_ref_matched"))
        # estat is raw source fidelity -- untouched, no legal state synthesized.
        self.assertEqual(rec["estat"], "vigent")
        self.assertEqual(rec["adjudicatari"], "")
        report = json.loads(sfm.REPORT_DRY_RUN.read_text(encoding="utf-8"))
        self.assertEqual(report["tombstones_applied"], 1)

    def test_dryrun_tombstone_repeated_run_is_idempotent(self):
        out1 = self.tmp / "out1.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_open_identity.json", out1))
        first = {r["id"]: r for r in json.loads(out1.read_text(encoding="utf-8"))["data"]}["FIX-OPEN-001"]

        # Second run starts from the already-tombstoned output and re-applies
        # the same tombstone ref again.
        sfm.PRODUCTION_PATH = out1
        out2 = self.tmp / "out2.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_open_identity.json", out2))
        second = {r["id"]: r for r in json.loads(out2.read_text(encoding="utf-8"))["data"]}["FIX-OPEN-001"]

        self.assertEqual(second["lifecycle_category"], sfm.TOMBSTONE_CATEGORY)
        self.assertFalse(second["active_opportunity_eligible"])
        self.assertEqual(second["tombstone_observed_at"], first["tombstone_observed_at"])

    def test_dryrun_tombstone_already_nonactive_identity_unchanged(self):
        out = self.tmp / "out.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_awarded_identity.json", out))
        merged = {r["id"]: r for r in json.loads(out.read_text(encoding="utf-8"))["data"]}
        rec = merged["FIX-AWARD-001"]
        self.assertEqual(rec["lifecycle_category"], "CLEAR_AWARDED")
        self.assertFalse(rec["active_opportunity_eligible"])
        self.assertTrue(rec.get("tombstone_ref_matched"))

    def test_dryrun_tombstone_unknown_ref_is_conservative_noop(self):
        out = self.tmp / "out.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_unknown_ref.json", out))
        merged = {r["id"]: r for r in json.loads(out.read_text(encoding="utf-8"))["data"]}
        # No ghost record was created for the unmatched ref...
        self.assertNotIn("FIX-GHOST-999", merged)
        # ...and every known identity is untouched (no tombstone fields leaked).
        self.assertEqual(len(merged), 3)
        for rec in merged.values():
            self.assertNotIn("tombstone_ref_matched", rec)
        report = json.loads(sfm.REPORT_DRY_RUN.read_text(encoding="utf-8"))
        self.assertEqual(report["tombstones_applied"], 0)

    def test_dryrun_ordinary_entries_unaffected_by_tombstone_handling(self):
        out = self.tmp / "out.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_full_success.json", out))
        merged = {sfm.get_merge_key(r): r for r in json.loads(out.read_text(encoding="utf-8"))["data"]}
        for key in ("CFID-OPEN-001", "CFID-OVERLAP-001", "CFID-NEW-001"):
            self.assertIn(key, merged)
            self.assertNotIn("tombstone_ref_matched", merged[key])

    def test_dryrun_carry_forward_cannot_resurrect_tombstoned_identity(self):
        # Run 1: tombstone FIX-OPEN-001.
        out1 = self.tmp / "out1.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_open_identity.json", out1))

        # Run 2: an ordinary later run that never mentions FIX-OPEN-001 again
        # and carries no tombstones of its own -- pure blind carry-forward.
        sfm.PRODUCTION_PATH = out1
        out2 = self.tmp / "out2.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_full_success.json", out2))

        merged = {r["id"]: r for r in json.loads(out2.read_text(encoding="utf-8"))["data"]}
        rec = merged["FIX-OPEN-001"]
        # Historical carry-forward alone must not resurrect active/public eligibility.
        self.assertEqual(rec["lifecycle_category"], sfm.TOMBSTONE_CATEGORY)
        self.assertFalse(rec["active_opportunity_eligible"])

    def test_dryrun_later_live_entry_follows_existing_overlap_rules(self):
        # Run 1: tombstone FIX-OPEN-001.
        out1 = self.tmp / "out1.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_open_identity.json", out1))

        # Run 2: the official feed explicitly republishes the same
        # ContractFolderID as an ordinary open entry (no tombstone this run).
        # This is explicit new source evidence flowing through the existing,
        # unmodified overlap rules -- not an implicit resurrection rule.
        sfm.PRODUCTION_PATH = out1
        out2 = self.tmp / "out2.json"
        sfm.run_merge_dry_run(dryrun_args(FIXTURES_DIR / "cand_tombstone_overlap_revives.json", out2))

        merged = {sfm.get_merge_key(r): r for r in json.loads(out2.read_text(encoding="utf-8"))["data"]}
        rec = merged["CFID-OPEN-001"]
        self.assertEqual(rec["lifecycle_category"], "CLEAR_OPEN")
        self.assertTrue(rec["active_opportunity_eligible"])

    # --- run_validate_production canonical-only behaviour (A2.3) -----------

    def test_validate_production_canonical_fixture_accepted(self):
        shutil.copyfile(FIXTURES_DIR / "production_canonical_min.json", self.prod_path)
        sfm.run_validate_production(types.SimpleNamespace())
        report = json.loads(sfm.REPORT_VALIDATE.read_text(encoding="utf-8"))
        self.assertEqual(report["final_verdict"], "PASS")
        self.assertEqual(report["validation_errors"], [])
        for legacy_key in ("gate_prompt", "gate_version", "gate_applied_at"):
            self.assertNotIn(legacy_key, report)

    def test_validate_production_legacy_fixture_rejected(self):
        # setUp already placed production_min.json (legacy gate marker, no
        # canonical schema) at self.prod_path.
        with self.assertRaises(SystemExit) as cm:
            sfm.run_validate_production(types.SimpleNamespace())
        self.assertEqual(cm.exception.code, 1)
        report = json.loads(sfm.REPORT_VALIDATE.read_text(encoding="utf-8"))
        self.assertEqual(report["final_verdict"], "FAIL")
        self.assertTrue(any("canonical public schema" in e for e in report["validation_errors"]))
        for legacy_key in ("gate_prompt", "gate_version", "gate_applied_at"):
            self.assertNotIn(legacy_key, report)

    def test_validate_production_canonical_missing_generation_id_rejected(self):
        canonical = load_fixture("production_canonical_min.json")
        del canonical["meta"]["generation_id"]
        self.prod_path.write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            sfm.run_validate_production(types.SimpleNamespace())
        self.assertEqual(cm.exception.code, 1)
        report = json.loads(sfm.REPORT_VALIDATE.read_text(encoding="utf-8"))
        self.assertEqual(report["final_verdict"], "FAIL")
        self.assertTrue(any("generation_id" in e for e in report["validation_errors"]))

    # --- Prompt 325 / WRKOPS t_20260925_adgops325: public-validator /
    # public-contract alignment. The canonical public projection (Prompt 289
    # STRIP) correctly omits internal lifecycle bookkeeping from every public
    # record; the production validator must accept that shape rather than
    # treating the intended absence as corruption. Internal lifecycle safety
    # (validate_lifecycle_integrity / classify_lifecycle /
    # resolve_overlap_lifecycle, exercised elsewhere in this suite) is
    # untouched by this task and unaffected by these public-artifact cases.

    def test_validate_production_stripped_lifecycle_fields_accepted(self):
        # A canonical public artifact whose records correctly omit
        # lifecycle_category / active_opportunity_eligible / lifecycle_
        # review_required -- exactly what public_record_projection.py's
        # STRIP contract produces -- must PASS when its public schema/meta/
        # hash/shape are otherwise valid.
        canonical = load_fixture("production_canonical_min.json")
        for rec in canonical["data"]:
            for field in ("lifecycle_category", "active_opportunity_eligible",
                          "lifecycle_review_required"):
                rec.pop(field, None)
        self.prod_path.write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")
        sfm.run_validate_production(types.SimpleNamespace())
        report = json.loads(sfm.REPORT_VALIDATE.read_text(encoding="utf-8"))
        self.assertEqual(report["final_verdict"], "PASS")
        self.assertEqual(report["validation_errors"], [])

    def test_validate_production_missing_lifecycle_fields_not_flagged(self):
        # Absence of lifecycle_category / active_opportunity_eligible must
        # never itself be raised as a public-validation error -- this is the
        # exact validator/public-contract skew this task corrects.
        canonical = load_fixture("production_canonical_min.json")
        for rec in canonical["data"]:
            rec.pop("lifecycle_category", None)
            rec.pop("active_opportunity_eligible", None)
        self.prod_path.write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")
        sfm.run_validate_production(types.SimpleNamespace())
        report = json.loads(sfm.REPORT_VALIDATE.read_text(encoding="utf-8"))
        for err in report["validation_errors"]:
            self.assertNotIn("missing lifecycle_category", err)
            self.assertNotIn("missing active_opportunity_eligible", err)

    def test_validate_production_still_rejects_broken_schema_with_stripped_fields(self):
        # Existing fail-closed public schema/meta behaviour is not weakened
        # by this change: an invalid schema is still rejected even when the
        # records otherwise have the correctly-stripped public shape.
        canonical = load_fixture("production_canonical_min.json")
        canonical["meta"]["schema"] = "not.a.real.schema/0"
        for rec in canonical["data"]:
            for field in ("lifecycle_category", "active_opportunity_eligible",
                          "lifecycle_review_required"):
                rec.pop(field, None)
        self.prod_path.write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            sfm.run_validate_production(types.SimpleNamespace())
        self.assertEqual(cm.exception.code, 1)
        report = json.loads(sfm.REPORT_VALIDATE.read_text(encoding="utf-8"))
        self.assertEqual(report["final_verdict"], "FAIL")
        self.assertTrue(any("canonical public schema" in e for e in report["validation_errors"]))

    # --- p294 / WRKOPS t_20260910_adgops294: internal/public state split ---
    # load_internal_state / persist_internal_state / canonicalize_and_project
    # are the new --run-live glue this prompt adds. Coverage here is narrowly
    # scoped to that new glue, not a re-test of the already-closed
    # tools.canonical_tender_merge / tools.public_record_projection
    # contracts (69/69 and their own suites already own that).

    def test_load_internal_state_missing_file_fails_closed(self):
        missing = self.tmp / "does_not_exist.json"
        with self.assertRaises(SystemExit):
            sfm.load_internal_state(missing)

    def test_load_internal_state_malformed_json_fails_closed(self):
        bad = self.tmp / "bad_internal_state.json"
        bad.write_text("{ not valid json,,, ", encoding="utf-8")
        with self.assertRaises(SystemExit):
            sfm.load_internal_state(bad)

    def test_load_internal_state_invalid_shape_fails_closed(self):
        bad = self.tmp / "no_data_key_internal_state.json"
        bad.write_text(json.dumps({"meta": {}}), encoding="utf-8")
        with self.assertRaises(SystemExit):
            sfm.load_internal_state(bad)

    def test_load_internal_state_valid_file_round_trips(self):
        valid = self.tmp / "internal_state.json"
        payload = load_fixture("production_min.json")
        valid.write_text(json.dumps(payload), encoding="utf-8")
        loaded = sfm.load_internal_state(valid)
        self.assertEqual(loaded["data"], payload["data"])
        self.assertEqual(loaded["meta"], payload["meta"])

    def test_persist_internal_state_writes_rows_and_bookkeeping(self):
        out = self.tmp / "internal_state_out.json"
        prior_meta = {"note": "prior-internal-meta"}
        rows = [{"id": "X1", "enrichment_version": "v1"}]
        wrote = sfm.persist_internal_state(out, prior_meta, [], rows)
        self.assertTrue(wrote)
        written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["data"], rows)
        self.assertEqual(written["meta"]["note"], "prior-internal-meta")
        self.assertIn("internal_state_updated_at", written["meta"])
        self.assertEqual(written["meta"]["internal_state_prompt"], "294")
        self.assertEqual(written["meta"]["internal_state_record_count"], 1)

    def test_persist_internal_state_skips_write_when_unchanged(self):
        # p294 R1 §4: a semantically no-op run must not rewrite the file —
        # rewriting on every call (even with byte-identical `rows`) would
        # bump the wall-clock `internal_state_updated_at` field every time,
        # forcing the workflow's diff-guarded private commit to fire on every
        # run regardless of content, which the handoff explicitly forbids.
        out = self.tmp / "internal_state_noop.json"
        rows = [{"id": "X1", "enrichment_version": "v1"}]
        wrote_first = sfm.persist_internal_state(out, {"note": "prior"}, [], rows)
        self.assertTrue(wrote_first)
        first_bytes = out.read_bytes()

        wrote_second = sfm.persist_internal_state(out, {"note": "prior"}, rows, rows)
        self.assertFalse(wrote_second)
        self.assertEqual(out.read_bytes(), first_bytes)

    def test_canonicalize_and_project_happy_path_strips_bookkeeping(self):
        rows = [dict(r) for r in load_fixture("production_min.json")["data"]]
        result = sfm.canonicalize_and_project(rows)
        self.assertEqual(len(result), len(rows))
        self.assertEqual({r["id"] for r in result}, {r["id"] for r in rows})
        for pub in result:
            self.assertIn("public_id", pub)
            for bookkeeping in ("enrichment_version", "lifecycle_category",
                                "active_opportunity_eligible",
                                "lifecycle_review_required",
                                "source_merge_class"):
                self.assertNotIn(bookkeeping, pub)

    def test_canonicalize_and_project_fails_closed_on_merge_error(self):
        class _StubMergeError(Exception):
            def __init__(self):
                super().__init__("invalid_id: stub")
                self.code = "invalid_id"

        class _StubCtm:
            CanonicalTenderMergeError = _StubMergeError

            @staticmethod
            def merge_canonical_tenders(rows):
                raise _StubMergeError()

        saved = sfm.ctm
        sfm.ctm = _StubCtm
        try:
            with self.assertRaises(SystemExit):
                sfm.canonicalize_and_project([])
        finally:
            sfm.ctm = saved

    def test_canonicalize_and_project_fails_closed_on_rejected_projection(self):
        class _StubPrp:
            @staticmethod
            def project_public_records(rows):
                return {"accepted": False, "rejected_reason": "duplicate_public_id", "records": []}

        saved = sfm.prp
        sfm.prp = _StubPrp
        try:
            rows = [dict(r) for r in load_fixture("production_min.json")["data"]]
            with self.assertRaises(SystemExit):
                sfm.canonicalize_and_project(rows)
        finally:
            sfm.prp = saved

    def test_run_live_requires_internal_state_path(self):
        # Must fail closed before any network/subprocess fetch is attempted.
        args = types.SimpleNamespace(allow_production_write=True, internal_state_path=None)
        with self.assertRaises(SystemExit):
            sfm.run_live(args)

    def test_run_live_requires_allow_production_write(self):
        args = types.SimpleNamespace(allow_production_write=False, internal_state_path="ignored")
        with self.assertRaises(SystemExit):
            sfm.run_live(args)


# ---------------------------------------------------------------------------
# IB-5 Phase A (WRKOPS t_20260914_adgops306 §11/§12.D): offline regression
# for scheduled_fetch_merge.py's optional --link-checks-path consumption
# path. No network. sfm.run_live() itself is not invoked here (it requires a
# live fetch subprocess) -- this exercises the exact two functions run_live()
# composes at its insertion point: canonicalize_and_project() then
# apply_link_checks_if_requested(), proving the offline overlay path without
# any real HTTP resolution.
# ---------------------------------------------------------------------------

class L1LinkChecksOfflineOverlayTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _rows_with_one_document(self):
        return [{
            "id": "FIX-LC-001",
            "titol": "Synthetic link-check tender",
            "organisme": "Ajuntament Fixticia",
            "estat": "vigent",
            "adjudicatari": "",
            "pressupost": 10000,
            "data_pub": "2026-05-01",
            "url": "https://example.invalid/fixture/lc-001",
            "historial": [],
            "award_results": [],
            "documents": [{
                "title": "Doc", "url": "https://example.invalid/fixture/lc-001.pdf",
                "document_type": "generic_doc", "notice_id": "N1", "notice_type": "PUB",
            }],
        }]

    def test_absent_path_preserves_baseline_behavior(self):
        rows = self._rows_with_one_document()
        public_records = sfm.canonicalize_and_project(rows)
        result = sfm.apply_link_checks_if_requested(public_records, None)
        self.assertEqual(result, public_records)
        self.assertIs(result, public_records)  # no-op: same object, not even a copy

    def test_valid_sidecar_overlays_expected_document(self):
        rows = self._rows_with_one_document()
        public_records = sfm.canonicalize_and_project(rows)
        doc = public_records[0]["documents"][0]
        obs = {
            "public_id": public_records[0]["public_id"],
            "record_id": public_records[0]["id"],
            "document_key": list(ctm.document_identity_key(doc)),
            "requested_url": doc["url"],
            "observed_at": "2026-06-01T00:00:00Z",
            "resolver_method": "HEAD",
            "http_status": 200,
            "classification": "REACHABLE",
        }
        sidecar = {
            "schema": lcr.SCHEMA,
            "run_id": "run-1",
            "started_at": "2026-06-01T00:00:00Z",
            "completed_at": "2026-06-01T00:00:05Z",
            "resolver_policy": {"limit": 50},
            "counts": {"candidates_attempted": 1},
            "observations": [obs],
        }
        sidecar_path = self.tmp / "link_checks.json"
        sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")

        result = sfm.apply_link_checks_if_requested(public_records, str(sidecar_path))
        result_doc = result[0]["documents"][0]
        self.assertIn("doc_intel", result_doc)
        self.assertEqual(result_doc["doc_intel"]["state"], "link_checked")
        # Original public_records list/dicts untouched.
        self.assertNotIn("doc_intel", public_records[0]["documents"][0])

    def test_malformed_sidecar_fails_before_public_write(self):
        rows = self._rows_with_one_document()
        public_records = sfm.canonicalize_and_project(rows)
        bad_path = self.tmp / "bad_link_checks.json"
        # Missing required run-level keys -- strict schema rejects it.
        bad_path.write_text(json.dumps({"schema": lcr.SCHEMA}), encoding="utf-8")
        with self.assertRaises(SystemExit):
            sfm.apply_link_checks_if_requested(public_records, str(bad_path))

    def test_missing_explicit_path_fails_closed(self):
        rows = self._rows_with_one_document()
        public_records = sfm.canonicalize_and_project(rows)
        missing = self.tmp / "does_not_exist.json"
        with self.assertRaises(SystemExit):
            sfm.apply_link_checks_if_requested(public_records, str(missing))


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

    # --- Prompt 265 / v0.7.1r — D-02 operational classifier gate-awareness ---

    def test_fail_closed_shard_build_failure(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_SHARD_BUILD")

    def test_fail_closed_shard_build_cancelled(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="cancelled")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_SHARD_BUILD")

    def test_fail_closed_public_contract_failure(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_PUBLIC_CONTRACT")

    def test_fail_closed_public_contract_cancelled(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="cancelled")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_PUBLIC_CONTRACT")

    def test_shard_and_contract_skipped_preserves_no_changes(self):
        # Legitimate no-change path: monolith unchanged, so shards/shardvalidate
        # never ran (default "skipped"). Must NOT be classified as a failure.
        self.write_candidate("cand_empty_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="false", PUSH_OUTCOME="skipped")
        self.assertEqual(self.classify(env)["status"], "SUCCESS_REAL_FETCH_NO_CHANGES")

    def test_shard_build_precedes_public_contract_when_both_fail(self):
        # Precedence rule 5: shard-build failure classified before contract-gate
        # failure when both step outcomes are failures.
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="failure",
                       SHARDVALIDATE_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_SHARD_BUILD")

    def test_public_contract_precedes_git_commit_when_both_fail(self):
        # Precedence rule 6: contract-gate failure classified before commit failure.
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="failure", COMMIT_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_PUBLIC_CONTRACT")

    def test_dry_run_unaffected_by_gate_awareness(self):
        env = base_env(DRY_RUN_MODE="true", DRYRUN_OUTCOME="success")
        self.assertEqual(self.classify(env)["status"], "MANUAL_DRY_RUN_SUCCESS")

    def test_guard_skip_unaffected_by_gate_awareness(self):
        env = base_env(RUN_FETCH="skip")
        self.assertEqual(self.classify(env)["status"], "SKIPPED_BY_GUARD")

    def test_source_parser_precedence_not_masked_by_gate_outcomes(self):
        # Existing helper-failure source/parser precedence remains authoritative
        # even when shard/contract outcomes are present in the env (they should
        # never be consulted before the helper-failure branch).
        self.write_candidate("cand_non_atom.json")
        env = base_env(HELPER_OUTCOME="success", SHARDS_OUTCOME="failure",
                       SHARDVALIDATE_OUTCOME="failure")
        self.assertEqual(self.classify(env)["status"], "FAIL_CLOSED_PARSER_NON_ATOM")

    def test_git_commit_and_push_fail_closed_unchanged(self):
        self.write_candidate("cand_full_success.json")
        env_commit = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                              DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                              SHARDVALIDATE_OUTCOME="success", COMMIT_OUTCOME="failure")
        self.assertEqual(self.classify(env_commit)["status"], "FAIL_CLOSED_GIT_COMMIT")
        env_push = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                            DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                            SHARDVALIDATE_OUTCOME="success", COMMIT_OUTCOME="success",
                            DATA_CHANGED="true", PUSH_OUTCOME="failure")
        self.assertEqual(self.classify(env_push)["status"], "FAIL_CLOSED_GIT_PUSH")

    def test_success_real_fetch_write_unchanged_with_gate_outcomes(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        self.assertEqual(self.classify(env)["status"], "SUCCESS_REAL_FETCH_WRITE")

    def test_report_contains_new_gate_outcome_fields(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        report = self.classify(env)["report"]
        self.assertIn("shard_build", report["outcomes"])
        self.assertIn("public_contract", report["outcomes"])
        self.assertEqual(report["outcomes"]["shard_build"], "success")
        self.assertEqual(report["outcomes"]["public_contract"], "success")

    def test_summary_rows_contain_new_gate_outcome_labels(self):
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="failure")
        result = self.classify(env)
        labels = {k for k, _v in result["summary_rows"]}
        self.assertIn("shard build outcome", labels)
        self.assertIn("public contract outcome", labels)

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
# Prompt 324 Stage B (WRKOPS t_20260924_adgops324) -- durable V2 receipt.
# Offline only: no network, and every publication-identity test passes an
# explicit `production_path` fixture rather than touching the real
# data/licitaciones.json (build_receipt_v2()/finalize_v2_receipt() only fall
# back to the real repo path when no production_path is given AND
# DATA_CHANGED=='true', which none of these table-driven envs set without
# also supplying a fixture path).
# ---------------------------------------------------------------------------

def _run_started_at_iso():
    return "2026-09-24T08:00:00+00:00"


class V2ReceiptTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_candidate(self, fixture_name=None, payload=None):
        dst = self.tmp / "scheduled_live_candidate_20260924T080000Z.json"
        if payload is not None:
            dst.write_text(json.dumps(payload), encoding="utf-8")
        else:
            shutil.copyfile(FIXTURES_DIR / fixture_name, dst)
        return dst

    def write_production_fixture(self, generation_id="gen-20260924T080000Z-abc123def456",
                                  dataset_sha256="a" * 64, record_count=2):
        path = self.tmp / "production.json"
        payload = {
            "meta": {
                "generation_id": generation_id,
                "dataset_sha256": dataset_sha256,
                "counts": {"records": record_count},
            },
            "data": [{"id": "x"}] * record_count,
        }
        path.write_bytes(json.dumps(payload).encode("utf-8"))
        return path

    def classify(self, env, helper_log=None):
        return src.classify(env, tmp_dir=self.tmp, helper_log=helper_log)

    def receipt(self, env, helper_log=None, production_path=None):
        result = self.classify(env, helper_log=helper_log)
        return src.build_receipt_v2(env, result,
                                     helper_log=result.get("helper_log"),
                                     production_path=production_path), result

    # --- schema / shape per state -------------------------------------

    def test_schema_identity(self):
        receipt, _ = self.receipt(base_env(RUN_FETCH="skip"))
        self.assertEqual(receipt["schema"], "ADGOPS_SCHEDULED_RUN_REPORT_V2")
        self.assertEqual(receipt["schema_version"], "2.0")

    def test_success_shape_includes_publication_and_commit(self):
        self.write_candidate("cand_full_success.json")
        prod = self.write_production_fixture()
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="success", PRIVACYREPORT_OUTCOME="success",
                       COMMIT_OUTCOME="success", DATA_CHANGED="true",
                       PUSH_OUTCOME="success", COMMIT_SHA="deadbeef" * 5,
                       GH_RUN_ATTEMPT="1", BASELINE_HEAD="cafebabe" * 5,
                       RUN_STARTED_AT=_run_started_at_iso())
        receipt, result = self.receipt(env, production_path=prod)
        self.assertEqual(result["status"], "SUCCESS_REAL_FETCH_WRITE")
        self.assertEqual(receipt["terminal"]["operational_status"], "SUCCESS_REAL_FETCH_WRITE")
        self.assertIsNone(receipt["terminal"]["refusal_reason"])
        self.assertIsNotNone(receipt["publication"])
        self.assertEqual(receipt["publication"]["generation_id"], "gen-20260924T080000Z-abc123def456")
        self.assertEqual(receipt["commit"]["decision"], "created")
        self.assertEqual(receipt["commit"]["sha"], "deadbeef" * 5)
        self.assertEqual(receipt["run_identity"]["run_attempt"], "1")
        self.assertEqual(receipt["run_identity"]["baseline_head"], "cafebabe" * 5)
        self.assertIsNotNone(receipt["run_identity"]["elapsed_s"])
        self.assertIsNotNone(receipt["bounded_policy_snapshot"])
        self.assertGreater(receipt["bounded_policy_snapshot"]["active_source_count"], 0)
        self.assertEqual(receipt["candidate"]["sha256"],
                          hashlib.sha256((FIXTURES_DIR / "cand_full_success.json").read_bytes()).hexdigest())
        self.assertNotIn("path", receipt["candidate"])
        self.assertEqual(receipt["candidate"]["filename"],
                          "scheduled_live_candidate_20260924T080000Z.json")

    def test_no_change_shape_omits_publication(self):
        self.write_candidate("cand_empty_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="false", MONOLITH_CHANGED="false", PUSH_OUTCOME="skipped")
        receipt, result = self.receipt(env)
        self.assertEqual(result["status"], "SUCCESS_REAL_FETCH_NO_CHANGES")
        self.assertIsNone(receipt["publication"])
        self.assertEqual(receipt["commit"]["decision"], "not_created")
        self.assertIsNone(receipt["commit"]["sha"])

    def test_fail_closed_shape_omits_publication_and_commit_na(self):
        env = base_env(HELPER_OUTCOME="failure")
        receipt, result = self.receipt(env, helper_log="some unrelated traceback")
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertIsNone(receipt["publication"])
        self.assertEqual(receipt["commit"]["decision"], "n/a")
        self.assertEqual(receipt["terminal"]["refusal_reason"], "FAIL_CLOSED")
        self.assertIn("FAIL_CLOSED", receipt["sanitized_error_categories"])

    # --- exact-byte identity / self-hash / naming ----------------------

    def test_receipt_bytes_match_sidecar_digest_and_no_self_hash(self):
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="skipped",
                       DATA_CHANGED="", MONOLITH_CHANGED="false", PUSH_OUTCOME="skipped")
        self.write_candidate("cand_empty_success.json")
        result = self.classify(env)
        info = src.finalize_v2_receipt(env, result, tmp_dir=self.tmp, helper_log=result.get("helper_log"))
        self.assertIsNotNone(info)
        self.assertTrue(Path(info["receipt_path"]).exists())
        self.assertTrue(Path(info["sidecar_path"]).exists())
        self.assertTrue(run_receipt.verify_receipt(info["receipt_path"], info["sidecar_path"]))
        raw = Path(info["receipt_path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), info["sha256"])
        self.assertNotIn(info["sha256"].encode("ascii"), raw)

    def test_one_byte_corruption_detected(self):
        env = base_env(RUN_FETCH="skip")
        result = self.classify(env)
        info = src.finalize_v2_receipt(env, result, tmp_dir=self.tmp, helper_log=result.get("helper_log"))
        path = Path(info["receipt_path"])
        raw = bytearray(path.read_bytes())
        raw[0] = raw[0] ^ 0xFF
        path.write_bytes(bytes(raw))
        self.assertFalse(run_receipt.verify_receipt(info["receipt_path"], info["sidecar_path"]))

    def test_naming_includes_run_number_and_attempt_no_secret(self):
        env = base_env(RUN_FETCH="skip", GH_RUN_NUMBER="777", GH_RUN_ATTEMPT="2")
        result = self.classify(env)
        info = src.finalize_v2_receipt(env, result, tmp_dir=self.tmp, helper_log=result.get("helper_log"))
        self.assertIn("777-2-", info["filename"])
        self.assertNotIn("secret", info["filename"].lower())

    def test_run_number_and_attempt_prevent_filename_collision(self):
        env_a = base_env(RUN_FETCH="skip", GH_RUN_NUMBER="777", GH_RUN_ATTEMPT="1")
        env_b = base_env(RUN_FETCH="skip", GH_RUN_NUMBER="777", GH_RUN_ATTEMPT="2")
        result_a = self.classify(env_a)
        result_b = self.classify(env_b)
        info_a = src.finalize_v2_receipt(env_a, result_a, tmp_dir=self.tmp, helper_log=None)
        info_b = src.finalize_v2_receipt(env_b, result_b, tmp_dir=self.tmp, helper_log=None)
        self.assertNotEqual(info_a["filename"], info_b["filename"])
        self.assertTrue(Path(info_a["receipt_path"]).exists())
        self.assertTrue(Path(info_b["receipt_path"]).exists())

    # --- sanitization / disclosure boundary -----------------------------

    def test_no_tmp_or_absolute_path_in_receipt(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success")
        receipt, _ = self.receipt(env)
        blob = json.dumps(receipt)
        self.assertNotIn("_tmp", blob)
        self.assertNotIn(str(self.tmp), blob)

    def test_no_raw_source_errors_or_candidate_records_leak(self):
        long_err = "SECRET-UPSTREAM-DETAIL " + ("x" * 900)
        self.write_candidate(payload={
            "meta": {"run_status": "EMPTY_FAILURE", "is_partial": True,
                     "failed_sources": ["PLACSP-643"],
                     "source_errors": {"PLACSP-643": long_err}},
            "data": [{"raw_field": "should-never-appear-in-receipt"}],
        })
        env = base_env(HELPER_OUTCOME="success")
        receipt, _ = self.receipt(env)
        blob = json.dumps(receipt)
        self.assertNotIn(long_err, blob)
        self.assertNotIn("SECRET-UPSTREAM-DETAIL", blob)
        self.assertNotIn("should-never-appear-in-receipt", blob)
        self.assertNotIn("source_errors", receipt["candidate"])
        self.assertNotIn("data", receipt)

    def test_continuity_boolean_only_no_private_state_content(self):
        self.write_candidate("cand_full_success.json")
        log = "[run-live] Internal state persisted: /some/path (3 records)\n"
        env = base_env(HELPER_OUTCOME="success")
        receipt, _ = self.receipt(env, helper_log=log)
        self.assertIs(receipt["continuity"]["state_written"], True)
        blob = json.dumps(receipt)
        self.assertNotIn("/some/path", blob)

        log_unchanged = "[run-live] Internal state unchanged, not rewritten: /x\n"
        receipt2, _ = self.receipt(base_env(HELPER_OUTCOME="success"), helper_log=log_unchanged)
        # candidate not rewritten between calls -- reuse same tmp candidate
        self.assertIs(receipt2["continuity"]["state_written"], False)

    # --- failure-path coverage -------------------------------------------

    def test_hard_subprocess_timeout_still_classifies_and_receipts(self):
        # No candidate file written at all (mirrors run_live()'s hard-timeout
        # except block, which exits before any candidate consumption).
        log = ("[ERROR] Fetcher subprocess exceeded the global acquisition "
               "deadline (123.4s); aborting bounded acquisition. No candidate consumed.")
        env = base_env(HELPER_OUTCOME="failure")
        receipt, result = self.receipt(env, helper_log=log)
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertIn("DEADLINE_EXCEEDED_HARD_TIMEOUT", receipt["sanitized_error_categories"])
        self.assertIsNone(receipt["candidate"]["filename"])
        self.assertIsNotNone(receipt["bounded_policy_snapshot"])

    def test_mocked_shard_failure_finalizes_receipt(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="failure")
        receipt, result = self.receipt(env)
        self.assertEqual(result["status"], "FAIL_CLOSED_SHARD_BUILD")
        self.assertEqual(receipt["gates"]["shard_build"], "failure")
        self.assertIsNone(receipt["publication"])

    def test_mocked_public_contract_failure_finalizes_receipt(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="failure")
        receipt, result = self.receipt(env)
        self.assertEqual(result["status"], "FAIL_CLOSED_PUBLIC_CONTRACT")
        self.assertEqual(receipt["gates"]["public_contract"], "failure")

    def test_mocked_privacy_failure_gate_recorded(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", SHARDS_OUTCOME="success",
                       SHARDVALIDATE_OUTCOME="success", PRIVACYREPORT_OUTCOME="failure",
                       COMMIT_OUTCOME="skipped")
        receipt, _result = self.receipt(env)
        self.assertEqual(receipt["gates"]["privacy"], "failure")
        self.assertIsNone(receipt["publication"])

    def test_mocked_commit_failure_finalizes_receipt(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="failure")
        receipt, result = self.receipt(env)
        self.assertEqual(result["status"], "FAIL_CLOSED_GIT_COMMIT")
        self.assertEqual(receipt["gates"]["commit"], "failure")
        self.assertEqual(receipt["commit"]["decision"], "not_created")

    def test_mocked_push_failure_finalizes_receipt(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="failure")
        receipt, result = self.receipt(env)
        self.assertEqual(result["status"], "FAIL_CLOSED_GIT_PUSH")
        self.assertEqual(receipt["gates"]["push"], "failure")

    # --- receipt-write failure is not a publication gate ------------------

    def test_receipt_write_failure_never_raises_and_v1_unaffected(self):
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        result = self.classify(env)
        step_summary = self.tmp / "step_summary.md"
        github_env = self.tmp / "github_env.txt"
        with mock.patch.object(src.rr, "write_receipt", side_effect=OSError("disk full")):
            src.write_outputs(result, tmp_dir=self.tmp, github_step_summary=str(step_summary),
                              github_env=str(github_env), env=env)
        report_path = self.tmp / "scheduled_run_report_999.json"
        self.assertTrue(report_path.exists())
        self.assertIn("OPERATIONAL_STATUS=SUCCESS_REAL_FETCH_WRITE",
                      github_env.read_text(encoding="utf-8"))
        self.assertNotIn("RECEIPT_PATH", github_env.read_text(encoding="utf-8"))

    def test_write_outputs_without_env_skips_v2_receipt(self):
        # Existing direct callers that omit `env` (as the pre-Stage-B tests
        # above already do) must keep the exact prior V1-only behaviour.
        self.write_candidate("cand_full_success.json")
        env = base_env(HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                       DIFFSUMMARY_OUTCOME="success", COMMIT_OUTCOME="success",
                       DATA_CHANGED="true", PUSH_OUTCOME="success")
        result = self.classify(env)
        src.write_outputs(result, tmp_dir=self.tmp,
                          github_step_summary=str(self.tmp / "s.md"),
                          github_env=str(self.tmp / "e.txt"))
        receipts = list(self.tmp.glob("adgops_run_receipt_*.json"))
        self.assertEqual(receipts, [])


class RunReceiptHelperTests(unittest.TestCase):
    """Pure tools/run_receipt.py coverage, independent of the classifier."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_receipt_creates_matching_digest(self):
        receipt = {"schema": "TEST", "value": 1}
        filename = run_receipt.receipt_filename("42", "1", "20260924T000000Z")
        self.assertEqual(filename, "adgops_run_receipt_42-1-20260924T000000Z.json")
        info = run_receipt.write_receipt(receipt, self.tmp, filename)
        raw = (self.tmp / filename).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), info["sha256"])
        sidecar = (self.tmp / f"{filename}.sha256").read_text(encoding="utf-8")
        self.assertIn(info["sha256"], sidecar)
        self.assertTrue(run_receipt.verify_receipt(info["receipt_path"], info["sidecar_path"]))

    def test_canonical_json_bytes_uses_binary_safe_newline(self):
        data = run_receipt.canonical_json_bytes({"a": 1})
        self.assertNotIn(b"\r\n", data)
        self.assertTrue(data.endswith(b"\n"))

    def test_receipt_filename_defaults_when_missing(self):
        name = run_receipt.receipt_filename(None, None, "20260924T000000Z")
        self.assertEqual(name, "adgops_run_receipt_unknown-unknown-20260924T000000Z.json")


# ---------------------------------------------------------------------------
# p271 / D-04 F4 — shared normalized run_status subpredicate
# ---------------------------------------------------------------------------

class _UpperOnlyRunStatus:
    """Sentinel run_status exposing upper() but deliberately not lower().

    Used to prove the classifier still short-circuits on `cand_partial is True`
    before requesting .lower(): with cand_partial=False the historical code
    reaches the separate upper-case guard without ever touching .lower().
    """

    def upper(self):
        return "PARTIAL_SUCCESS"


class CandidatePartialFailurePolicyTests(unittest.TestCase):
    """Covers tools/scheduled_candidate_policy.py:run_status_lacks_success()
    and its two consumers. The shared helper owns ONLY the substring decision
    over an already-normalized (lower-case) run_status. The `is_partial is
    True` identity guard and the raw normalization (str(...).lower() in the
    merger, cand_run_status.lower() in the classifier) stay consumer-owned so
    each consumer keeps its historical short-circuit evaluation order.
    This suite must NOT assert the merger's and classifier's complete
    policies are equal."""

    # --- shared helper: substring decision over already-normalized input ---

    def test_helper_partial_success_is_not_lacking_success(self):
        self.assertFalse(scp.run_status_lacks_success("partial_success"))

    def test_helper_partial_degraded_lacks_success(self):
        self.assertTrue(scp.run_status_lacks_success("partial_degraded"))

    def test_helper_empty_run_status_lacks_success(self):
        self.assertTrue(scp.run_status_lacks_success(""))

    def test_helper_current_substring_semantics_preserved(self):
        # "unsuccessful" contains the substring "success" — current substring
        # matching (not a new allow-list) treats this as success-like,
        # preserving pre-p271 behaviour exactly.
        self.assertFalse(scp.run_status_lacks_success("unsuccessful_partial"))

    # --- intentional complete-policy divergence (merger vs classifier) -----

    def test_non_partial_empty_failure_classifier_still_fails_closed(self):
        # Intentional preserved divergence: is_partial=False skips the partial
        # branch entirely (the merger would not refuse), but the classifier's
        # complete wrapper still classifies EMPTY_FAILURE as fail-closed via
        # its own status-only guard.
        self.assertTrue(src.candidate_failed_closed(False, "EMPTY_FAILURE"))

    def test_missing_is_partial_failure_status_classifier_still_fails_closed(self):
        self.assertTrue(src.candidate_failed_closed(None, "FAILURE"))

    # --- classifier malformed-input behaviour preservation (not shared) ----
    # Historical behaviour: with cand_partial is True, cand_run_status.lower()
    # is evaluated as the right operand of the short-circuiting `and`, so a
    # non-string run_status still raises AttributeError exactly as it did
    # before p271. The shared helper does not own or catch this — see
    # scheduled_candidate_policy.py docstring.

    def test_classifier_none_run_status_raises_attributeerror(self):
        with self.assertRaises(AttributeError):
            src.candidate_failed_closed(True, None)

    def test_classifier_non_string_run_status_raises_attributeerror(self):
        with self.assertRaises(AttributeError):
            src.candidate_failed_closed(True, 12345)

    # --- classifier short-circuit evaluation order (p271 v0.4) -------------

    def test_classifier_short_circuits_lower_when_not_partial(self):
        # The sentinel has no .lower(); reaching it would raise AttributeError.
        # Returning False proves the first branch short-circuited on
        # `cand_partial is True` and only the upper-case guard ran.
        sentinel = _UpperOnlyRunStatus()
        self.assertFalse(hasattr(sentinel, "lower"))
        self.assertNotIn("FAILURE", sentinel.upper())
        self.assertFalse(src.candidate_failed_closed(False, sentinel))

    # --- merger historical nesting (source inspection) ---------------------
    # Proves the exact pre-p271 evaluation order remains at both merger
    # refusal sites — the str(...).lower() adapter is nested INSIDE the
    # literal-True partial guard, never evaluated ahead of it — without
    # executing live merge/write behaviour here; the runtime refusal
    # behaviour itself is already exercised by L1MergeHelperTests
    # (test_empty_failure_refused, test_non_atom_refused,
    # test_partial_no_success_run_status_refused,
    # test_partial_acceptable_is_accepted, etc.).

    def test_merger_nests_str_lower_adapter_inside_both_partial_guards(self):
        merger_src = Path(sfm.__file__).read_text(encoding="utf-8")
        adapter = 'str(cand_meta.get("run_status", "")).lower()'
        block = (
            '    if cand_meta.get("is_partial") is True:\n'
            '        run_status_lower = ' + adapter + '\n'
            '        if scp.run_status_lacks_success(run_status_lower):\n'
        )
        self.assertEqual(
            merger_src.count(block), 2,
            "expected two partial-guard blocks with the str(...).lower() adapter nested inside",
        )
        self.assertEqual(
            merger_src.count(adapter), 2,
            "the str(...).lower() adapter must appear only inside the two partial guards",
        )


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


# =============================================================================
# p267 / v0.7.1t — D-03 report-only production baseline. Additive only: pins
# the production summary contract, the exit-code mapping the new workflow
# step relies on, and static text-level invariants of the `privacyreport`
# step wired into .github/workflows/fetch.yml between `shardvalidate` and
# `commit`. No existing test is modified; no privacy fixture or
# _expectations.json entry is added. Runtime-cost discipline (p267 §6.D): the
# entire block below performs exactly two complete --validate-public scans,
# both captured once in setUpClass and reused by every test_p267_a* case.
# =============================================================================

FETCH_YML_PATH = REPO_ROOT / ".github" / "workflows" / "fetch.yml"


class P267D03ReportOnlyProductionBaselineTests(unittest.TestCase):
    """p267 / D-03: production summary contract (A), exit-code mapping the
    workflow depends on (B), and workflow-shape text invariants (C)."""

    @classmethod
    def setUpClass(cls):
        # Scan 1 of 2: the exact production invocation the workflow step
        # runs. Captured once; every test_p267_a* case below reuses this.
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            cls.summary_exit = pv.run(["--validate-public", "--summary-only", "--json"])
        cls.summary_stdout = out.getvalue()
        cls.summary_payload = json.loads(cls.summary_stdout)

        # Scan 2 of 2: full (non-summary) report, solely for the bounded-
        # output size comparison in test_p267_a9 — no other assertion reads it.
        out2, err2 = io.StringIO(), io.StringIO()
        with redirect_stdout(out2), redirect_stderr(err2):
            cls.full_exit = pv.run(["--validate-public", "--json"])
        cls.full_stdout = out2.getvalue()

    # --- A. Production summary contract -------------------------------------

    def test_p267_a1_schema_exact(self):
        self.assertEqual(self.summary_payload["schema"],
                          "ADGOPS_PRIVACY_VALIDATOR_SUMMARY_V1")

    def test_p267_a2_exit_zero_on_current_production(self):
        self.assertEqual(self.summary_exit, 0)

    def test_p267_a3_error_count_zero(self):
        self.assertEqual(self.summary_payload["error_count"], 0)

    def test_p267_a4_scalar_counters_are_nonnegative_ints(self):
        for key in ("error_count", "warn_count", "distinct_count", "group_count"):
            value = self.summary_payload[key]
            self.assertIsInstance(value, int)
            self.assertNotIsInstance(value, bool)
            self.assertGreaterEqual(value, 0)

    def test_p267_a5_group_count_matches_len_groups(self):
        self.assertEqual(self.summary_payload["group_count"],
                          len(self.summary_payload["groups"]))

    def test_p267_a6_every_group_has_exact_key_set(self):
        for g in self.summary_payload["groups"]:
            self.assertEqual(set(g), {"severity", "rule_id", "source", "count"})

    def test_p267_a7_every_source_is_a_known_public_surface(self):
        for g in self.summary_payload["groups"]:
            self.assertIn(g["source"], pv.PUBLIC_SURFACES)

    def test_p267_a8_summary_output_has_no_pointer_field_or_marker(self):
        self.assertNotIn('"pointer"', self.summary_stdout)
        self.assertNotIn("$/", self.summary_stdout)

    def test_p267_a9_summary_output_materially_bounded_vs_full(self):
        # No exact warning/distinct/group count is pinned here — only that the
        # bounded summary form is substantially smaller than the full report.
        self.assertLess(len(self.summary_stdout), len(self.full_stdout))
        self.assertLess(self.summary_stdout.count("\n"), self.full_stdout.count("\n"))

    # --- B. Exit-code mapping the workflow branches on -----------------------

    def _run_fixture(self, tmp_dir, filename, content_text):
        path = Path(tmp_dir) / filename
        path.write_text(content_text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pv.run(["--fixture", str(path), "--surface", "public-build",
                           "--summary-only", "--json"])
        return code, out.getvalue(), err.getvalue(), path

    def test_p267_b1_clean_object_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _out, _err, _path = self._run_fixture(
                tmp, "p267_clean.json",
                '{"titol":"Servei de disseny","organisme":"Ajuntament sintetic"}')
            self.assertEqual(code, 0)

    def test_p267_b2_populated_credential_key_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _err, _path = self._run_fixture(
                tmp, "p267_findings.json",
                '{"password":"n0tAreal-secret-p267-0001"}')
            self.assertEqual(code, 2)
            self.assertIn("CREDENTIAL_KEY", out)
            self.assertNotIn("n0tAreal-secret-p267-0001", out)

    def test_p267_b3_malformed_json_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _out, err, _path = self._run_fixture(
                tmp, "p267_malformed.json", '{ not: valid json,,, ')
            self.assertEqual(code, 1)
            self.assertIn("[PARSE]", err)

    def test_p267_b4_exit_one_stderr_has_safe_bracketed_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            _code, _out, err, _path = self._run_fixture(
                tmp, "p267_malformed2.json", '{ not: valid json,,, ')
            self.assertRegex(err, r"\[(USAGE|STRUCTURAL|PARSE|READ)\]")

    def test_p267_b5_exit_one_stderr_no_traceback_no_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _out, err, path = self._run_fixture(
                tmp, "p267_malformed3.json", '{ not: valid json,,, ')
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", err)
            self.assertNotIn(str(path), err)
            self.assertNotIn(str(tmp), err)

    def test_p267_b6_exit_two_names_rule_not_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = "n0tAreal-p267-secret-9999"
            code, out, _err, _path = self._run_fixture(
                tmp, "p267_findings2.json", '{"password":"%s"}' % secret)
            self.assertEqual(code, 2)
            self.assertIn("CREDENTIAL_KEY", out)
            self.assertNotIn(secret, out)

    # --- C. Workflow-shape contract (static text-level invariants) -----------

    @staticmethod
    def _workflow_text():
        return FETCH_YML_PATH.read_text(encoding="utf-8")

    def test_p267_c1_privacyreport_step_id_exists(self):
        self.assertIn("id: privacyreport", self._workflow_text())

    def test_p267_c2_privacyreport_between_shardvalidate_and_commit(self):
        text = self._workflow_text()
        i_shardvalidate = text.index("id: shardvalidate")
        i_privacyreport = text.index("id: privacyreport")
        i_commit = text.index("id: commit")
        self.assertLess(i_shardvalidate, i_privacyreport)
        self.assertLess(i_privacyreport, i_commit)

    def test_p267_c3_condition_names_all_three_env_vars(self):
        text = self._workflow_text()
        i = text.index("id: privacyreport")
        window = text[i:i + 600]
        self.assertIn("RUN_FETCH", window)
        self.assertIn("DRY_RUN_MODE", window)
        self.assertIn("MONOLITH_CHANGED", window)

    def test_p267_c4_invokes_exact_validator_command(self):
        self.assertIn(
            "python tools/privacy_validator.py --validate-public --summary-only --json",
            self._workflow_text())

    def _privacyreport_step_block(self, text):
        i = text.index("id: privacyreport")
        j = text.index("id: commit")
        return text[i:j]

    def test_p267_c5_omits_report_only_flag(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertNotIn("--report-only", step_block)

    def test_p267_c6_omits_continue_on_error(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertNotIn("continue-on-error", step_block)

    def test_p267_c7_step_ends_with_result_based_exit_not_unconditional_zero(self):
        # IB-4 (p273 v0.3 §14.1): the step's own final exit must be
        # RESULT-derived (blocking), never an unconditional "exit 0" as the
        # literal last command — that was the pre-IB-4 report-only shape.
        text = self._workflow_text()
        i = text.index("id: privacyreport")
        run_start = text.index("run: |", i) + len("run: |")
        next_step = text.index("\n      - name:", run_start)
        run_body = text[run_start:next_step]
        lines = [ln.strip() for ln in run_body.splitlines() if ln.strip()]
        self.assertTrue(lines, "privacyreport run body must not be empty")
        self.assertNotEqual(lines[-1], "exit 0",
                             "step must not end on an unconditional exit 0")
        self.assertEqual(lines[-7:], [
            'if [ "$RESULT" = "NO_ERRORS" ]; then',
            "exit 0",
            'elif [ "$RESULT" = "ERROR_FINDINGS" ]; then',
            "exit 2",
            "else",
            "exit 1",
            "fi",
        ])

    def test_p267_c13_step_contains_broad_except_exception_boundary(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertIn("except Exception:", step_block)

    def test_p267_c14_step_suppresses_parser_stderr_from_actions_log(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertIn("2>/dev/null", step_block)

    def test_p267_c15_step_contains_both_fixed_failure_diagnostics(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertIn(
            'FAILURE_DIAGNOSTIC="[privacyreport] summary payload failed '
            'schema/consistency validation"',
            step_block)
        self.assertIn(
            'FAILURE_DIAGNOSTIC="[privacyreport] validator execution did '
            'not produce trustworthy summary evidence"',
            step_block)

    def test_p267_c16_failure_diagnostics_have_no_interpolation_or_path(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        assignments = re.findall(r'FAILURE_DIAGNOSTIC="([^"]*)"', step_block)
        self.assertEqual(len(assignments), 2)
        for sentence in assignments:
            self.assertNotIn("$", sentence)
            self.assertNotIn("{", sentence)
            self.assertNotIn("_tmp", sentence)
            self.assertNotIn(".json", sentence)
            self.assertNotIn(".log", sentence)

    def test_p267_c8_step_contains_three_result_labels(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        for label in ("NO_ERRORS", "ERROR_FINDINGS", "EXECUTION_FAILURE"):
            self.assertIn(label, step_block)

    def test_p267_c9_step_validates_summary_schema_identifier(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertIn("ADGOPS_PRIVACY_VALIDATOR_SUMMARY_V1", step_block)

    def test_p267_c10_operational_summary_env_block_unchanged_p265_contract(self):
        text = self._workflow_text()
        i = text.index("Operational summary")
        # WRKOPS t_20260924_adgops324 (Prompt 324 Stage B): the "Upload run
        # receipt (evidence)" step now follows "Operational summary", so the
        # scan window is bounded to this step's own YAML (up to the next
        # step) rather than "to end of file".
        j = text.index("\n      - name:", i)
        opsummary_block = text[i:j]
        for key in ("HELPER_OUTCOME", "DRYRUN_OUTCOME", "VALIDATE_OUTCOME",
                    "DIFFSUMMARY_OUTCOME", "SHARDS_OUTCOME",
                    "SHARDVALIDATE_OUTCOME", "COMMIT_OUTCOME", "PUSH_OUTCOME",
                    "GH_RUN_ATTEMPT", "BASELINE_HEAD"):
            self.assertIn(key, opsummary_block)
        # p265 originally locked this block to carry no PRIVACY-named env
        # key. WRKOPS t_20260924_adgops324 (Prompt 324 Stage B §2.9)
        # supersedes that specifically to add PRIVACYREPORT_OUTCOME (a
        # bounded step-outcome string -- success/failure/skipped/cancelled,
        # never validator findings content -- the V2 receipt's gates.privacy
        # field needs). Every OTHER env-key assignment in this block must
        # still carry no PRIVACY substring, in any spelling/casing.
        env_keys = re.findall(r"^\s*([A-Za-z0-9_]+):", opsummary_block, re.MULTILINE)
        privacy_keys = [k for k in env_keys if "PRIVACY" in k.upper()]
        self.assertEqual(privacy_keys, ["PRIVACYREPORT_OUTCOME"])

    def test_p267_c11_existing_step_order_preserved(self):
        text = self._workflow_text()
        ids = ["id: time_guard", "id: helper", "id: dryrun", "id: validate",
               "id: diffsummary", "id: shards", "id: shardvalidate",
               "id: privacyreport", "id: commit", "id: push"]
        positions = [text.index(step_id) for step_id in ids]
        self.assertEqual(positions, sorted(positions))

    def test_p267_c12_f04_no_internal_ephemeral_artifact_publication(self):
        """F-04 (ADGOPS_ROUTINE_PLATFORM_HEALTH_SECURITY_AUDIT_20260906_v0.1):
        internal/ephemeral _tmp/** diagnostics (raw live-candidate JSON, raw
        merge-conflict diagnostics, the run report, and the privacy
        validator's bounded summary/stderr) must never again be published as
        a downloadable GitHub Actions artifact from this public repository.
        The prior "Upload fail-closed diagnostics" step is removed outright
        (no already-contracted public-safe artifact existed to allowlist
        instead), so this also locks the invariant generically: neither the
        upload mechanism nor any of its former forbidden globs may silently
        reappear.

        R1 correction: the scan runs against an ACTIVE-YAML projection (full-
        line comments -- lines whose first non-whitespace character is "#" --
        excluded), not the raw workflow text. A non-executable explanatory
        comment that merely narrates the removed _tmp/** publication surface
        is prose, not executable artifact configuration, and must not itself
        trip this test; the mechanism and every former forbidden glob must
        still be absent from what actually executes."""
        text = self._workflow_text()
        active_lines = [
            line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        active_text = "\n".join(active_lines)
        # WRKOPS t_20260924_adgops324 (Prompt 324 Stage A/R1/B): a single,
        # narrowly-scoped actions/upload-artifact step IS now authorized --
        # "Upload run receipt (evidence)", uploading only the sanitized V2
        # receipt + its .sha256 sidecar. This is NOT a revival of the F-04
        # diagnostics upload removed below (that step uploaded raw
        # internal-ephemeral material wholesale); assert its shape directly
        # rather than merely asserting the mechanism's absence.
        self.assertEqual(active_text.count("actions/upload-artifact"), 1)
        self.assertIn("Upload run receipt (evidence)", active_text)
        self.assertNotIn("actions/download-artifact", active_text)
        self.assertNotIn("Upload fail-closed diagnostics", active_text)
        forbidden_fragments = (
            "_tmp/scheduled_live_candidate_*.json",
            "_tmp/scheduled_merge_conflicts_live_*.json",
            "_tmp/scheduled_run_report_*.json",
            "_tmp/privacy_summary_*.json",
            "_tmp/privacy_stderr_*.log",
            "_tmp/**",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, active_text)

    def test_p324_receipt_upload_step_allowlists_exactly_receipt_and_sidecar(self):
        """WRKOPS t_20260924_adgops324 Stage B §6.2: the artifact-upload
        step's `path:` must be an exact allowlist of the V2 receipt and its
        sidecar via RECEIPT_PATH / RECEIPT_SIDECAR_PATH env references --
        never a wildcard, never a literal _tmp path, never retention-days."""
        text = self._workflow_text()
        i = text.index("Upload run receipt (evidence)")
        f04_idx = text.index("# F-04", i)
        step_block = text[i:f04_idx]
        self.assertIn("${{ env.RECEIPT_PATH }}", step_block)
        self.assertIn("${{ env.RECEIPT_SIDECAR_PATH }}", step_block)
        self.assertIn("if-no-files-found: error", step_block)
        self.assertIn("if: always()", step_block)
        self.assertNotIn("_tmp/**", step_block)
        self.assertNotIn("retention-days", step_block)

    def test_p324_r1_upload_artifact_pinned_to_exact_immutable_sha(self):
        """WRKOPS t_20260924_adgops324 Stage B R1 §B: the upload-artifact
        `uses:` reference must be the Companion-verified exact commit SHA for
        v7.0.1, matching this file's existing exact-commit-pin convention --
        never a mutable major-version tag, and never left as a TODO."""
        text = self._workflow_text()
        i = text.index("Upload run receipt (evidence)")
        f04_idx = text.index("# F-04", i)
        step_block = text[i:f04_idx]
        self.assertIn(
            "uses: actions/upload-artifact@"
            "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1",
            step_block)
        self.assertNotIn("actions/upload-artifact@v4", step_block)
        self.assertNotIn("TODO(operator)", step_block)

    def test_p324_r1_no_actions_write_permission_added(self):
        """WRKOPS t_20260924_adgops324 Stage B R1 §B: Companion review of
        official GitHub documentation found no requirement to expand
        GITHUB_TOKEN to `actions: write` for the ordinary same-run
        upload-artifact operation used here -- the permissions block must
        remain exactly `contents: write`, least privilege preserved."""
        text = self._workflow_text()
        i = text.index("permissions:")
        j = text.index("env:", i)
        permissions_block = text[i:j]
        self.assertIn("contents: write", permissions_block)
        self.assertNotIn("actions:", permissions_block)

    def test_p324_guard_step_writes_run_started_at(self):
        """WRKOPS t_20260924_adgops324 Stage B §2.2: the V2 receipt's
        run_identity.started_at_utc is sourced from RUN_STARTED_AT, written
        by the earliest step that runs regardless of guard/dry-run outcome."""
        text = self._workflow_text()
        i = text.index("id: time_guard")
        j = text.index("id: statecheckout")
        self.assertIn("RUN_STARTED_AT=", text[i:j])

    def test_p324_commit_step_captures_commit_sha(self):
        """WRKOPS t_20260924_adgops324 Stage B §2.10: the resulting commit
        SHA is captured only inside the commit-creation branch, immediately
        after `git commit`."""
        text = self._workflow_text()
        i = text.index("id: commit")
        j = text.index("id: push")
        step_block = text[i:j]
        self.assertIn("COMMIT_SHA=$(git rev-parse HEAD)", step_block)
        commit_idx = step_block.index('git commit -m "$COMMIT_SUBJECT"')
        sha_idx = step_block.index("COMMIT_SHA=")
        self.assertLess(commit_idx, sha_idx)

    def test_fetch_workflow_contains_no_unicode_replacement_character(self):
        """R1 (Prompt 288 operator validation): the operator run transcript
        reported literal U+FFFD replacement characters in fetch.yml prose
        while other Unicode in the same terminal rendered correctly. This is
        a source-hygiene invariant only -- it forbids the replacement
        character specifically and does not restrict legitimate Unicode
        (e.g. em dashes, section signs) elsewhere in the workflow."""
        text = self._workflow_text()
        self.assertNotIn("�", text)

    def test_p267_c17_strict_scalar_gate_replaces_read_trust_path(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        # Parser stdout is redirected to the exact temp parser-output file,
        # not captured via command substitution.
        self.assertIn(
            'PARSER_OUTPUT_FILE="_tmp/privacy_parser_${GITHUB_RUN_NUMBER}.txt"',
            step_block)
        self.assertIn('> "$PARSER_OUTPUT_FILE" 2>/dev/null', step_block)
        # Parser exit status captured immediately after the parser invocation
        # (no intervening statement between the heredoc terminator and the
        # capture).
        self.assertRegex(step_block, r'PYEOF\s*\n\s*PARSER_EXIT=\$\?')
        # Raw lines loaded via mapfile, not command substitution.
        self.assertIn(
            'mapfile -t PARSER_LINES < "$PARSER_OUTPUT_FILE"', step_block)
        # The exact parser-output temp file is removed right after loading.
        self.assertIn('rm -f "$PARSER_OUTPUT_FILE"', step_block)
        # PARSER_LINE defaults safely, and is assigned only inside a guard
        # keyed off the RAW loaded line count -- the CRLF-safe scalar never
        # substitutes for the raw-line-count decision itself.
        self.assertIn('PARSER_LINE=""', step_block)
        self.assertRegex(
            step_block,
            r'PARSER_LINE=""\s*\n\s*if \[ "\$\{#PARSER_LINES\[@\]\}" = "1" \]; then\s*\n'
            r'\s*PARSER_LINE="\$\{PARSER_LINES\[0\]%\$\'\\r\'\}"\s*\n\s*fi\b')
        # Normalization strips at most one terminal carriage return via bash
        # suffix-pattern parameter expansion -- never tr -d, never xargs,
        # never a piped sed/broad whitespace trim. The forbidden-executable
        # scan runs against a comment-aware projection (blank lines and
        # lines whose first non-whitespace character is "#" excluded), not
        # against the raw step_block text, so an explanatory comment that
        # merely *names* a forbidden tool (e.g. "No tr -d, no broad trim.")
        # cannot itself trip the check -- only an executable occurrence can.
        self.assertIn(
            r'''PARSER_LINE="${PARSER_LINES[0]%$'\r'}"''', step_block)
        executable_lines = [
            line for line in step_block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        executable_step_block = "\n".join(executable_lines)
        self.assertNotIn('tr -d', executable_step_block)
        self.assertNotIn('xargs', executable_step_block)
        self.assertNotRegex(executable_step_block, r"\|\s*sed\b")
        # Acceptance requires parser exit 0, exactly one RAW loaded line
        # (from the untouched PARSER_LINES array), and an anchored
        # four-counter match against the normalized PARSER_LINE scalar --
        # never the raw, possibly CRLF-terminated PARSER_LINES[0] element.
        self.assertIn('[ "$PARSER_EXIT" = "0" ] &&', step_block)
        self.assertIn('[ "${#PARSER_LINES[@]}" = "1" ] &&', step_block)
        self.assertIn(
            r'"$PARSER_LINE" =~ ^VALID\ ([0-9]+)\ ([0-9]+)\ ([0-9]+)\ ([0-9]+)$',
            step_block)
        self.assertNotIn(
            r'"${PARSER_LINES[0]}" =~ ^VALID', step_block)

    # =========================================================================
    # IB-4 (p273 v0.3 §14, WRKOPS t_20260906_adgops286): privacyreport step
    # becomes blocking. Additive per §9.2 — does not loosen any test above.
    # =========================================================================

    def test_ib4_summary_row_says_blocking_yes(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertIn('echo "| blocking | yes |"', step_block)
        self.assertNotIn("no (report-only)", step_block)

    def test_ib4_annotations_say_publication_blocked(self):
        step_block = self._privacyreport_step_block(self._workflow_text())
        self.assertIn(
            '::error::Privacy validator reported ERROR findings; '
            'publication blocked.', step_block)
        self.assertIn(
            '::error::Privacy validator could not produce trustworthy '
            'evidence (exit code $PRIVACY_EXIT); publication blocked.',
            step_block)
        self.assertNotIn("not blocked", step_block)
        self.assertNotIn("::warning::", step_block)

    def test_ib4_result_and_exit_code_stay_distinguishable(self):
        # Execution failure and a real privacy finding must map to different
        # exit codes so the two failure modes remain distinguishable even
        # though both now block the step (proven precisely, line-by-line, by
        # test_p267_c7 above; this is a lighter substring-level guard).
        step_block = self._privacyreport_step_block(self._workflow_text())
        i_elif = step_block.index('elif [ "$RESULT" = "ERROR_FINDINGS" ]; then')
        i_else = step_block.index("\n          else\n", i_elif)
        i_fi = step_block.index("\n          fi", i_else)
        self.assertIn("exit 2", step_block[i_elif:i_else])
        self.assertIn("exit 1", step_block[i_else:i_fi])
        self.assertNotIn("exit 2", step_block[i_else:i_fi])

    def test_ib4_no_producer_or_publicprojection_step_added(self):
        text = self._workflow_text()
        self.assertNotIn("public_projection", text)
        self.assertNotIn("PublicProjection", text)

    def test_ib4_dependency_install_step_unchanged(self):
        text = self._workflow_text()
        self.assertIn(
            "python -m pip install -r requirements.txt -c constraints.txt",
            text)

    def test_ib4_privacyreport_still_before_commit_and_push(self):
        text = self._workflow_text()
        step_block = self._privacyreport_step_block(text)
        i_privacyreport = text.index("id: privacyreport")
        i_commit = text.index("id: commit")
        i_push = text.index("id: push")
        self.assertLess(i_privacyreport, i_commit)
        self.assertLess(i_commit, i_push)
        # Counters populated only from the validated BASH_REMATCH captures.
        for idx, var in enumerate(
                ("ERROR_COUNT", "WARN_COUNT", "DISTINCT_COUNT", "GROUP_COUNT"), start=1):
            self.assertIn('%s="${BASH_REMATCH[%d]}"' % (var, idx), step_block)
        # Both prior trust paths are fully removed.
        self.assertNotIn("read -r TAG", step_block)
        self.assertNotIn('PARSED="$(python', step_block)


# =============================================================================
# F-14 (WRKOPS t_20260912_adgops298): monolith content-change publication
# gate. Locks the meta.dataset_sha256-based MONOLITH_CHANGED authority that
# replaced the removed raw `git diff --quiet -- data/licitaciones.json`
# byte-diff, its fail-closed hash validation, and the commit/push gate
# predicates that now consume it (Prompt 297 R1 / F14_MONOLITH_COMMIT_GATE_V1).
#
# Static text-level checks (below) lock the workflow shape, following the
# p267/D-03 pattern above. The functional checks execute the ACTUAL
# diffsummary inline script extracted from fetch.yml -- not a
# reimplementation -- with `git show` replaced by a deterministic stub
# (tools/scheduled_fetch_merge.py is intentionally left untouched; this is a
# test-local harness only, per the task's guidance to prefer that over a new
# production module).
# =============================================================================

DIFFSUMMARY_HEREDOC_MARKER = "<<'PYEOF'\n"
DIFFSUMMARY_INDENT = " " * 10


def _load_diffsummary_source():
    """Extracts and de-indents the actual inline Python source of the F-14
    diffsummary classifier from fetch.yml, between id: diffsummary's
    <<'PYEOF' heredoc markers. Raises if a line isn't indented the way this
    workflow file's YAML block scalar requires, so a shape drift fails loudly
    instead of silently extracting the wrong text."""
    text = FETCH_YML_PATH.read_text(encoding="utf-8")
    i = text.index("id: diffsummary")
    marker_pos = text.index(DIFFSUMMARY_HEREDOC_MARKER, i)
    start = marker_pos + len(DIFFSUMMARY_HEREDOC_MARKER)
    end = text.index("\n" + DIFFSUMMARY_INDENT + "PYEOF", start)
    block = text[start:end]
    dedented = []
    for line in block.split("\n"):
        if line == "":
            dedented.append("")
        elif line.startswith(DIFFSUMMARY_INDENT):
            dedented.append(line[len(DIFFSUMMARY_INDENT):])
        else:
            raise AssertionError(f"diffsummary heredoc line under-indented: {line!r}")
    return "\n".join(dedented) + "\n"


class _StubCompletedProcess:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run_diffsummary(tmp_dir, current_text, committed_text=None,
                      git_returncode=0, git_stderr=""):
    """Executes the real diffsummary source (see _load_diffsummary_source)
    against a synthetic working-tree data/licitaciones.json, with the
    script's own `subprocess.run(["git", "show", ...])` call replaced by a
    deterministic stub so this never shells out to a real git process or
    touches the real repository. `current_text=None` leaves the working-tree
    file unwritten, to exercise the missing/unreadable-file path.

    Returns (exit_code_or_None, github_env_text, stdout_text, stderr_text,
    git_calls)."""
    source = _load_diffsummary_source()
    tmp_path = Path(tmp_dir)
    (tmp_path / "data").mkdir(exist_ok=True)
    if current_text is not None:
        (tmp_path / "data" / "licitaciones.json").write_text(current_text, encoding="utf-8")
    github_env_path = tmp_path / "github_env.txt"
    github_env_path.write_text("", encoding="utf-8")

    calls = []

    def fake_run(argv, capture_output=None, text=None):
        calls.append(list(argv))
        return _StubCompletedProcess(
            git_returncode,
            stdout=committed_text if committed_text is not None else "",
            stderr=git_stderr,
        )

    original_run = subprocess.run
    original_cwd = os.getcwd()
    original_github_env = os.environ.get("GITHUB_ENV")
    subprocess.run = fake_run
    os.chdir(tmp_path)
    os.environ["GITHUB_ENV"] = str(github_env_path)
    out, err = io.StringIO(), io.StringIO()
    exit_code = None
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                exec(compile(source, "<diffsummary>", "exec"),
                     {"__name__": "__diffsummary_under_test__"})
            except SystemExit as exc:
                exit_code = exc.code
    finally:
        subprocess.run = original_run
        os.chdir(original_cwd)
        if original_github_env is None:
            os.environ.pop("GITHUB_ENV", None)
        else:
            os.environ["GITHUB_ENV"] = original_github_env

    return exit_code, github_env_path.read_text(encoding="utf-8"), out.getvalue(), err.getvalue(), calls


class P298F14MonolithContentGateTests(unittest.TestCase):
    """F-14 / WRKOPS t_20260912_adgops298 content-change publication gate."""

    HASH_A = "a" * 64
    HASH_B = "b" * 64

    @staticmethod
    def _workflow_text():
        return FETCH_YML_PATH.read_text(encoding="utf-8")

    @staticmethod
    def _dataset(dataset_sha256, extra_meta=None, records=None):
        meta = {"dataset_sha256": dataset_sha256}
        if extra_meta:
            meta.update(extra_meta)
        return json.dumps({"meta": meta, "data": records if records is not None else []})

    # --- static workflow-shape invariants -----------------------------------

    def test_f14_raw_byte_diff_removed_as_semantic_authority(self):
        self.assertNotIn(
            "git diff --quiet -- data/licitaciones.json", self._workflow_text())

    def test_f14_diffsummary_classifies_by_dataset_sha256(self):
        text = self._workflow_text()
        i = text.index("id: diffsummary")
        j = text.index("id: shards", i)
        step_block = text[i:j]
        self.assertIn("dataset_sha256", step_block)
        self.assertIn("git diff --stat", step_block)  # kept per §3
        self.assertIn('os.environ["GITHUB_ENV"]', step_block)

    def test_f14_commit_requires_monolith_changed(self):
        text = self._workflow_text()
        i = text.index("id: commit")
        if_start = text.index("if:", i)
        if_line = text[if_start:text.index("\n", if_start)]
        self.assertIn("env.MONOLITH_CHANGED == 'true'", if_line)
        self.assertIn("env.RUN_FETCH == 'true'", if_line)
        self.assertIn("env.DRY_RUN_MODE == 'false'", if_line)

    def test_f14_push_requires_monolith_and_data_changed(self):
        text = self._workflow_text()
        i = text.index("id: push")
        if_start = text.index("if:", i)
        if_line = text[if_start:text.index("\n", if_start)]
        self.assertIn("env.MONOLITH_CHANGED == 'true'", if_line)
        self.assertIn("env.DATA_CHANGED == 'true'", if_line)
        self.assertIn("env.RUN_FETCH == 'true'", if_line)
        self.assertIn("env.DRY_RUN_MODE == 'false'", if_line)

    def test_f14_push_command_unchanged_no_force(self):
        text = self._workflow_text()
        i = text.index("id: push")
        step_block = text[i:i + 400]
        self.assertIn("git push", step_block)
        self.assertNotIn("--force", step_block)
        self.assertNotIn("-f ", step_block)

    def test_f14_six_file_staging_surface_unchanged(self):
        self.assertIn(
            "git add data/licitaciones.json data/licitaciones_manifest.json "
            "data/licitaciones_2026.json data/licitaciones_2025.json "
            "data/licitaciones_2024.json data/licitaciones_archive.json",
            self._workflow_text())

    def test_f14_no_broad_git_staging_introduced(self):
        text = self._workflow_text()
        i = text.index("id: commit")
        j = text.index("id: push", i)
        step_block = text[i:j]
        self.assertNotIn("git add -A", step_block)
        self.assertNotIn("git add .", step_block)
        self.assertNotIn("git add --all", step_block)

    def test_f14_empty_staged_diff_fails_closed_not_datachanged_false(self):
        text = self._workflow_text()
        i = text.index("id: commit")
        j = text.index("id: push", i)
        step_block = text[i:j]
        # The forbidden-executable scan runs against a comment-aware
        # projection (blank lines and lines whose first non-whitespace
        # character is "#" excluded), not against the raw step_block text,
        # so an explanatory comment that merely *names* the pre-F-14
        # behaviour (e.g. "...succeeding with DATA_CHANGED=false.") cannot
        # itself trip the check -- only an executable assignment can.
        executable_lines = [
            line for line in step_block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        executable_step_block = "\n".join(executable_lines)
        self.assertNotIn("DATA_CHANGED=false", executable_step_block)
        self.assertIn("exit 1", executable_step_block)

    def test_f14_derivative_gates_still_monolith_gated(self):
        text = self._workflow_text()
        for step_id in ("id: shards", "id: shardvalidate", "id: privacyreport"):
            i = text.index(step_id)
            if_start = text.index("if:", i)
            if_line = text[if_start:text.index("\n", if_start)]
            self.assertIn("env.MONOLITH_CHANGED == 'true'", if_line)

    def test_f14_transaction_order_unchanged(self):
        text = self._workflow_text()
        ids = ["id: time_guard", "id: statecheckout", "id: helper", "id: statepush",
               "id: validate", "id: diffsummary", "id: shards", "id: shardvalidate",
               "id: privacyreport", "id: commit", "id: push"]
        positions = [text.index(step_id) for step_id in ids]
        self.assertEqual(positions, sorted(positions))

    def test_f14_f07_concurrency_and_timeout_contract_unchanged(self):
        text = self._workflow_text()
        self.assertIn("timeout-minutes: 20", text)
        self.assertIn("timeout-minutes: 10", text)
        self.assertIn(
            "group: fetch-licitaciones-${{ inputs.dry_run == 'true' && "
            "'diagnostic' || 'production' }}",
            text)
        self.assertIn(
            "cancel-in-progress: ${{ inputs.dry_run == 'true' }}", text)

    # --- functional: executes the actual embedded classifier source --------

    def test_f14_identical_hash_different_volatile_metadata_is_unchanged(self):
        current = self._dataset(self.HASH_A, {"dataset_generated_at": "2026-09-12T00:00:00Z",
                                               "generation_id": "gen-X"})
        committed = self._dataset(self.HASH_A, {"dataset_generated_at": "2026-09-01T00:00:00Z",
                                                 "generation_id": "gen-Y"})
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, current, committed_text=committed)
            self.assertIsNone(exit_code)
            self.assertIn("MONOLITH_CHANGED=false", env_text)

    def test_f14_different_hash_classifies_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text=self._dataset(self.HASH_B))
            self.assertIsNone(exit_code)
            self.assertIn("MONOLITH_CHANGED=true", env_text)

    def test_f14_missing_current_hash_fails_closed(self):
        current = json.dumps({"meta": {}, "data": []})
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, err, _calls = _run_diffsummary(
                tmp, current, committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)
            self.assertNotIn("MONOLITH_CHANGED", env_text)
            self.assertIn("current working-tree dataset", err)

    def test_f14_missing_committed_hash_fails_closed(self):
        committed = json.dumps({"meta": {}, "data": []})
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, err, _calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text=committed)
            self.assertEqual(exit_code, 1)
            self.assertNotIn("MONOLITH_CHANGED", env_text)
            self.assertIn("committed (HEAD) dataset", err)

    def test_f14_malformed_current_hash_wrong_length_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, self._dataset("short"), committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)
            self.assertNotIn("MONOLITH_CHANGED", env_text)

    def test_f14_malformed_current_hash_non_hex_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, _env_text, _out, _err, _calls = _run_diffsummary(
                tmp, self._dataset("z" * 64), committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)

    def test_f14_current_hash_non_string_fails_closed(self):
        current = json.dumps({"meta": {"dataset_sha256": 12345}, "data": []})
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, _env_text, _out, _err, _calls = _run_diffsummary(
                tmp, current, committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)

    def test_f14_malformed_current_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, _env_text, _out, err, _calls = _run_diffsummary(
                tmp, "{ not valid json,,,", committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)
            self.assertIn("not valid JSON", err)

    def test_f14_malformed_committed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, _env_text, _out, err, _calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text="{ not valid json,,,")
            self.assertEqual(exit_code, 1)
            self.assertIn("HEAD", err)

    def test_f14_missing_current_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, err, _calls = _run_diffsummary(
                tmp, current_text=None, committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)
            self.assertNotIn("MONOLITH_CHANGED", env_text)
            self.assertIn("failed to read working-tree data/licitaciones.json", err)

    def test_f14_git_show_failure_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, err, _calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text="",
                git_returncode=128, git_stderr="fatal: bad object HEAD")
            self.assertEqual(exit_code, 1)
            self.assertNotIn("MONOLITH_CHANGED", env_text)
            self.assertIn("git show HEAD:data/licitaciones.json", err)

    def test_f14_git_show_invocation_targets_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            _exit_code, _env, _out, _err, calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text=self._dataset(self.HASH_A))
            self.assertEqual(calls, [["git", "show", "HEAD:data/licitaciones.json"]])

    # --- R1 (WRKOPS t_20260924_adgops324 Stage B R1 §A): honest DATA_CHANGED
    # plumbing on the genuine no-material-change path. These execute the
    # ACTUAL diffsummary heredoc (via _run_diffsummary), never a
    # reimplementation, proving the real workflow contract rather than only
    # a hand-supplied classify() fixture. -----------------------------------

    def test_r1_diffsummary_emits_data_changed_false_on_no_material_change(self):
        current = self._dataset(self.HASH_A, {"dataset_generated_at": "2026-09-24T08:00:00Z",
                                               "generation_id": "gen-NEW"})
        committed = self._dataset(self.HASH_A, {"dataset_generated_at": "2026-09-01T00:00:00Z",
                                                 "generation_id": "gen-OLD"})
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, current, committed_text=committed)
            self.assertIsNone(exit_code)
            self.assertIn("MONOLITH_CHANGED=false", env_text)
            self.assertIn("DATA_CHANGED=false", env_text)

    def test_r1_diffsummary_does_not_emit_data_changed_on_real_change(self):
        # A hash-changed run must NOT have diffsummary claim any DATA_CHANGED
        # value -- DATA_CHANGED=true remains exclusively the commit step's
        # commit-creation branch, set only after a commit actually exists.
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text=self._dataset(self.HASH_B))
            self.assertIsNone(exit_code)
            self.assertIn("MONOLITH_CHANGED=true", env_text)
            self.assertNotIn("DATA_CHANGED", env_text)

    def test_r1_diffsummary_fail_closed_paths_never_emit_data_changed(self):
        # Every diffsummary fail-closed exit already proven in
        # test_f14_*_fails_closed above must also never emit DATA_CHANGED --
        # a failure/skip path must never be falsely represented as a
        # successful no-change run.
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, current_text=None, committed_text=self._dataset(self.HASH_A))
            self.assertEqual(exit_code, 1)
            self.assertNotIn("DATA_CHANGED", env_text)
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                tmp, self._dataset(self.HASH_A), committed_text="",
                git_returncode=128, git_stderr="fatal: bad object HEAD")
            self.assertEqual(exit_code, 1)
            self.assertNotIn("DATA_CHANGED", env_text)

    def test_r1_data_changed_written_exactly_once_true_and_once_false(self):
        """Static shape lock: across the workflow's active (non-comment)
        text, DATA_CHANGED=true appears exactly once (inside id: commit's
        commit-creation branch) and DATA_CHANGED=false appears exactly once
        (inside id: diffsummary's no-material-change branch) -- no other
        location may ever assign either value."""
        text = self._workflow_text()
        active_lines = [
            line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        active_text = "\n".join(active_lines)
        self.assertEqual(active_text.count("DATA_CHANGED=true"), 1)
        self.assertEqual(active_text.count("DATA_CHANGED=false"), 1)

        i = active_text.index("id: commit")
        j = active_text.index("id: push", i)
        commit_block = active_text[i:j]
        self.assertIn("DATA_CHANGED=true", commit_block)
        self.assertNotIn("DATA_CHANGED=false", commit_block)

        i2 = active_text.index("id: diffsummary")
        j2 = active_text.index("id: shards", i2)
        diffsummary_block = active_text[i2:j2]
        self.assertIn("DATA_CHANGED=false", diffsummary_block)
        self.assertNotIn("DATA_CHANGED=true", diffsummary_block)

    def test_r1_integration_real_no_change_env_classifies_success_no_changes(self):
        """End-to-end R1 proof (Stage B R1 §A items 1/4/5): the exact env the
        REAL diffsummary heredoc emits on a genuine no-material-change run,
        fed unmodified through the real classify()/build_receipt_v2() in
        tools/scheduled_run_classify.py -- never a hand-authored
        DATA_CHANGED='false' fixture -- must classify as
        SUCCESS_REAL_FETCH_NO_CHANGES and the V2 receipt must record it."""
        current = self._dataset(self.HASH_A)
        committed = self._dataset(self.HASH_A)
        with tempfile.TemporaryDirectory() as diff_tmp:
            exit_code, env_text, _out, _err, _calls = _run_diffsummary(
                diff_tmp, current, committed_text=committed)
            self.assertIsNone(exit_code)
        real_env_lines = dict(
            line.split("=", 1) for line in env_text.splitlines() if "=" in line
        )
        self.assertEqual(real_env_lines.get("DATA_CHANGED"), "false")
        self.assertEqual(real_env_lines.get("MONOLITH_CHANGED"), "false")

        with tempfile.TemporaryDirectory() as classify_tmp:
            shutil.copyfile(
                FIXTURES_DIR / "cand_empty_success.json",
                Path(classify_tmp) / "scheduled_live_candidate_20260924T080000Z.json")
            env = base_env(
                HELPER_OUTCOME="success", VALIDATE_OUTCOME="success",
                DIFFSUMMARY_OUTCOME="success",
                SHARDS_OUTCOME="skipped", SHARDVALIDATE_OUTCOME="skipped",
                PRIVACYREPORT_OUTCOME="skipped",
                COMMIT_OUTCOME="skipped", PUSH_OUTCOME="skipped",
                DATA_CHANGED=real_env_lines["DATA_CHANGED"],
                MONOLITH_CHANGED=real_env_lines["MONOLITH_CHANGED"],
            )
            result = src.classify(env, tmp_dir=Path(classify_tmp))
            self.assertEqual(result["status"], "SUCCESS_REAL_FETCH_NO_CHANGES")

            receipt = src.build_receipt_v2(
                env, result, helper_log=result.get("helper_log"))
            self.assertEqual(receipt["terminal"]["operational_status"],
                              "SUCCESS_REAL_FETCH_NO_CHANGES")
            self.assertIsNone(receipt["terminal"]["refusal_reason"])
            self.assertIsNone(receipt["publication"])
            self.assertEqual(receipt["commit"]["decision"], "not_created")


# ---------------------------------------------------------------------------
# Prompt 323 Stage B (WRKOPS t_20260923_adgops323) -- bounded-production
# acquisition offline coverage. No network anywhere below: all HTTP I/O is
# replaced by _ScriptedSession/_FakeResponse, all subprocess dispatch in the
# hard-timeout tests is mocked, and every fake clock is injected rather than
# reading real wall-clock time. Authored per the Stage A/R1 report's Sec 5
# offline test plan; NOT executed by this authoring session (WRKOPS
# NO_RUNTIME) -- the operator runs this suite via
# `python tools/fetcher_fixture_regression.py -v`.
# ---------------------------------------------------------------------------

_ATOM_NS_STAGE_B = "http://www.w3.org/2005/Atom"


class _FakeResponse:
    """Minimal stand-in for a requests.Response -- only the attributes/
    methods fetch_source() actually touches."""

    def __init__(self, status_code=200, content=b"", headers=None,
                 url="https://example.invalid/feed", encoding="utf-8"):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.url = url
        self.encoding = encoding

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise requests.exceptions.HTTPError(f"{self.status_code} error", response=self)


def _atom_bytes(entries_xml: str = "", next_href: str = None) -> bytes:
    next_link = f'<link rel="next" href="{next_href}"/>' if next_href else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<feed xmlns="{_ATOM_NS_STAGE_B}">{next_link}{entries_xml}</feed>'
    ).encode("utf-8")


def _fake_atom_response(status_code: int = 200, next_href: str = None, headers=None) -> _FakeResponse:
    return _FakeResponse(status_code=status_code, content=_atom_bytes(next_href=next_href),
                          headers=headers)


class _ScriptedSession:
    """Fake matching the .get(url, timeout=, allow_redirects=) surface
    fetch_source() calls. `script` is a list consumed in order, one entry
    per .get() call -- an Exception instance is raised, anything else is
    returned as the response. Every call is recorded in `.calls`."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def get(self, url, timeout=None, allow_redirects=True):
        self.calls.append({"url": url, "timeout": timeout, "allow_redirects": allow_redirects})
        if not self._script:
            raise AssertionError("fake session.get() called more times than scripted")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _ManualClock:
    """Injectable fake monotonic clock: reads `.t` directly, advanced only
    when a test (or a patched time.sleep) explicitly mutates it -- never on
    its own, so expiry timing in a test is fully deterministic."""

    def __init__(self, start: float = 0.0):
        self.t = start

    def __call__(self):
        return self.t


class FetchBoundsUnitTests(unittest.TestCase):
    """Pure unit coverage for tools/fetch_bounds.py -- registry/host
    authorization (Stage A Sec F), the request-budget formula and
    fail-closed counter (Sec H), and the deadline formula/object (Sec E).
    No network, no file I/O."""

    # --- registry / host authorization --------------------------------

    def test_verify_source_registry_matching_passes(self):
        active = [{"name": n, "url": e["url"]} for n, e in fetch_bounds.pc.PUBLIC_SOURCES.items()]
        fetch_bounds.verify_source_registry(active)  # must not raise

    def test_verify_source_registry_missing_entry_fails_closed(self):
        registry = dict(fetch_bounds.pc.PUBLIC_SOURCES)
        active = [{"name": n, "url": e["url"]} for n, e in registry.items()][:1]
        with self.assertRaises(fetch_bounds.RegistryMismatchError):
            fetch_bounds.verify_source_registry(active, registry=registry)

    def test_verify_source_registry_extra_entry_fails_closed(self):
        registry = dict(fetch_bounds.pc.PUBLIC_SOURCES)
        active = [{"name": n, "url": e["url"]} for n, e in registry.items()]
        active.append({"name": "EXTRA-SOURCE", "url": "https://extra.invalid/feed"})
        with self.assertRaises(fetch_bounds.RegistryMismatchError):
            fetch_bounds.verify_source_registry(active, registry=registry)

    def test_verify_source_registry_url_drift_fails_closed(self):
        registry = dict(fetch_bounds.pc.PUBLIC_SOURCES)
        active = [{"name": n, "url": e["url"]} for n, e in registry.items()]
        active[0] = {"name": active[0]["name"], "url": "https://drifted.invalid/feed"}
        with self.assertRaises(fetch_bounds.RegistryMismatchError):
            fetch_bounds.verify_source_registry(active, registry=registry)

    def test_allowed_hosts_derived_from_registry(self):
        hosts = fetch_bounds.allowed_hosts()
        self.assertIn("contrataciondelestado.es", hosts)
        self.assertIn("contrataciondelsectorpublico.gob.es", hosts)

    def test_is_authorized_host(self):
        self.assertTrue(fetch_bounds.is_authorized_host("contrataciondelestado.es"))
        self.assertFalse(fetch_bounds.is_authorized_host("evil.invalid"))
        self.assertFalse(fetch_bounds.is_authorized_host(""))
        self.assertFalse(fetch_bounds.is_authorized_host(None))

    # --- WRKOPS t_20261004_adgops335 corrective C2: source-bound
    # continuation validation (distinct from the global is_authorized_host
    # set above) ----------------------------------------------------------

    def test_is_valid_continuation_url_same_host_passes(self):
        self.assertTrue(fetch_bounds.is_valid_continuation_url(
            "https://contrataciondelestado.es/sindicacion/x?page=2",
            "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom",
        ))

    def test_is_valid_continuation_url_rejects_cross_source_bleed(self):
        # Both hosts are individually authorized (test_allowed_hosts_
        # derived_from_registry above), so is_authorized_host() alone
        # cannot catch a PLACSP-643 cursor that actually resolves to
        # PLACSP-1044's host -- this is the exact gap C2 closes.
        placsp_643_url = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-643"]["url"]
        placsp_1044_next_href = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-1044"]["url"] + "?page=9"
        self.assertTrue(fetch_bounds.is_authorized_host(
            fetch_bounds.urlparse(placsp_1044_next_href).hostname
        ))
        self.assertFalse(fetch_bounds.is_valid_continuation_url(placsp_1044_next_href, placsp_643_url))

    def test_is_valid_continuation_url_rejects_empty_or_missing(self):
        self.assertFalse(fetch_bounds.is_valid_continuation_url("", "https://s1.invalid/feed"))
        self.assertFalse(fetch_bounds.is_valid_continuation_url(None, "https://s1.invalid/feed"))
        self.assertFalse(fetch_bounds.is_valid_continuation_url("https://s1.invalid/feed?p=2", ""))

    # --- WRKOPS t_20261007_adgops338 corrective (DF-1 / P331-B15 lineage):
    # source-bound continuation-host AUTHORIZATION, additive to the C2
    # same-host check above, never a replacement for it ------------------

    def test_is_valid_continuation_url_placsp1044_accepts_authorized_alt_host(self):
        placsp_1044_url = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-1044"]["url"]
        authorized_alt_href = "https://contrataciondelestado.es/_wrkops_test_fixture_feed?page=9"
        self.assertTrue(fetch_bounds.is_valid_continuation_url(
            authorized_alt_href, placsp_1044_url, source_id="PLACSP-1044",
        ))

    def test_is_valid_continuation_url_placsp1044_rejects_unrelated_host(self):
        placsp_1044_url = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-1044"]["url"]
        self.assertFalse(fetch_bounds.is_valid_continuation_url(
            "https://unrelated-host.invalid/feed?page=9", placsp_1044_url,
            source_id="PLACSP-1044",
        ))

    def test_is_valid_continuation_url_placsp643_accepts_own_host(self):
        placsp_643_url = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-643"]["url"]
        self.assertTrue(fetch_bounds.is_valid_continuation_url(
            "https://contrataciondelestado.es/_wrkops_test_fixture_feed?page=2",
            placsp_643_url, source_id="PLACSP-643",
        ))

    def test_is_valid_continuation_url_placsp643_rejects_host_authorized_only_for_placsp1044(self):
        # PLACSP-1044's own registered host happens to be the exact host
        # PLACSP-643 already resolves same-host against, so this proves the
        # authorization lookup is keyed strictly by source_id: PLACSP-643
        # gets no benefit from an entry that exists only under "PLACSP-1044"
        # in tools.public_contract.CONTINUATION_HOST_AUTHORIZATIONS.
        placsp_643_url = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-643"]["url"]
        placsp_1044_host_href = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-1044"]["url"] + "?page=9"
        self.assertFalse(fetch_bounds.is_valid_continuation_url(
            placsp_1044_host_href, placsp_643_url, source_id="PLACSP-643",
        ))

    def test_is_valid_continuation_url_unknown_source_id_rejects_unauthorized_host(self):
        self.assertFalse(fetch_bounds.is_valid_continuation_url(
            "https://contrataciondelestado.es/_wrkops_test_fixture_feed?page=9",
            "https://unregistered-source.invalid/feed", source_id="UNKNOWN-SOURCE-999",
        ))

    def test_is_valid_continuation_url_rejects_non_https(self):
        placsp_1044_url = fetch_bounds.pc.PUBLIC_SOURCES["PLACSP-1044"]["url"]
        # http:// (not https://) to the otherwise-authorized alt host --
        # malformed/unsafe continuation must still fail closed.
        self.assertFalse(fetch_bounds.is_valid_continuation_url(
            "http://contrataciondelestado.es/_wrkops_test_fixture_feed?page=9",
            placsp_1044_url, source_id="PLACSP-1044",
        ))

    def test_is_valid_continuation_url_alt_host_authorization_is_additive_not_override(self):
        # host_authorizations seam lets a test substitute the registry
        # without touching tools.public_contract's real one; proves the
        # same-host match still passes even when the substitute registry
        # has no entry at all for that source_id (additive, never a
        # replacement for the base same-host check).
        self.assertTrue(fetch_bounds.is_valid_continuation_url(
            "https://s1.invalid/feed?p=2", "https://s1.invalid/feed",
            source_id="S1", host_authorizations={},
        ))
        self.assertFalse(fetch_bounds.is_valid_continuation_url(
            "https://s2.invalid/feed?p=2", "https://s1.invalid/feed",
            source_id="S1", host_authorizations={"S1": frozenset({"s3.invalid"})},
        ))
        self.assertTrue(fetch_bounds.is_valid_continuation_url(
            "https://s3.invalid/feed?p=2", "https://s1.invalid/feed",
            source_id="S1", host_authorizations={"S1": frozenset({"s3.invalid"})},
        ))

    # --- request-budget formula -----------------------------------------

    def test_max_total_requests_formula_not_a_frozen_literal(self):
        # Stage A Sec H: MAX_TOTAL_REQUESTS = sources * pages * (1+retries),
        # never a hard-coded 8 -- prove it recomputes for different inputs.
        self.assertEqual(fetch_bounds.max_total_requests(2, pages=1, retries=3), 8)
        self.assertEqual(fetch_bounds.max_total_requests(3, pages=1, retries=3), 12)
        self.assertEqual(fetch_bounds.max_total_requests(2, pages=2, retries=3), 16)
        self.assertEqual(fetch_bounds.max_total_requests(2, pages=1, retries=0), 2)

    def test_request_budget_admits_up_to_max_then_fails_closed(self):
        budget = fetch_bounds.RequestBudget(3)
        budget.admit()
        budget.admit()
        budget.admit()
        self.assertEqual(budget.used, 3)
        self.assertEqual(budget.remaining(), 0)
        with self.assertRaises(fetch_bounds.BudgetExceededError):
            budget.admit()
        self.assertEqual(budget.used, 3)  # the refused call is never counted

    def test_request_budget_rejects_negative_max(self):
        with self.assertRaises(ValueError):
            fetch_bounds.RequestBudget(-1)

    # --- deadline formula --------------------------------------------

    def test_compute_global_deadline_s_matches_stage_a_worked_example(self):
        # Stage A/R1 report Sec E worked example: 2 sources, pages=1,
        # retries=3, timeout=45s, delay=2.0, backoff=2.0 -> approx 394s.
        value = fetch_bounds.compute_global_deadline_s(
            active_source_count=2, pages=1, retries=3,
            request_timeout_s=45.0, retry_delay=2.0, retry_backoff=2.0)
        self.assertAlmostEqual(value, 393.6, places=1)

    def test_compute_global_deadline_s_scales_with_inputs(self):
        base = fetch_bounds.compute_global_deadline_s(active_source_count=1)
        doubled_sources = fetch_bounds.compute_global_deadline_s(active_source_count=2)
        self.assertAlmostEqual(doubled_sources, base * 2)

    def test_worst_case_backoff_matches_retry_sleep_upper_bound(self):
        value = fetch_bounds.worst_case_backoff_s(retries=3, retry_delay=2.0, retry_backoff=2.0)
        self.assertAlmostEqual(value, 2.0 * (1 + 2 + 4) * 1.2)

    # --- Deadline object (fake clock) ------------------------------------

    def test_deadline_not_expired_before_horizon(self):
        clock = _ManualClock(start=0.0)
        d = fetch_bounds.Deadline(10.0, clock=clock)
        self.assertFalse(d.expired())
        clock.t = 9.999
        self.assertFalse(d.expired())
        d.check()  # must not raise

    def test_deadline_expired_at_and_after_horizon(self):
        clock = _ManualClock(start=0.0)
        d = fetch_bounds.Deadline(10.0, clock=clock)
        clock.t = 10.0
        self.assertTrue(d.expired())
        with self.assertRaises(fetch_bounds.DeadlineExceededError):
            d.check()
        clock.t = 999.0
        self.assertTrue(d.expired())

    def test_deadline_remaining_never_negative(self):
        clock = _ManualClock(start=0.0)
        d = fetch_bounds.Deadline(5.0, clock=clock)
        clock.t = 100.0
        self.assertEqual(d.remaining(), 0.0)


class BoundedSessionConstructionTests(unittest.TestCase):
    """Stage A Sec A: build_bounded_session() must mount a non-retrying
    transport adapter (Retry(total=0)), while build_session() (every other
    call site) is unchanged. No network -- inspects only the constructed
    Session's mounted adapter configuration."""

    def test_build_session_retains_current_retry_adapter(self):
        s = fl.build_session()
        adapter = s.get_adapter("https://contrataciondelestado.es/x")
        self.assertEqual(adapter.max_retries.total, 3)
        self.assertEqual(adapter.max_retries.connect, 3)
        self.assertEqual(adapter.max_retries.read, 3)

    def test_build_bounded_session_disables_transport_retries(self):
        s = fl.build_bounded_session()
        adapter = s.get_adapter("https://contrataciondelestado.es/x")
        self.assertEqual(adapter.max_retries.total, 0)

    def test_build_bounded_session_still_sets_headers(self):
        s = fl.build_bounded_session()
        self.assertEqual(s.headers.get("User-Agent"), fl.HEADERS["User-Agent"])


class BoundedFetchSourceTests(unittest.TestCase):
    """fetch_source() bounded-mode coverage -- single-layer retry/attempt
    accounting, failure classification (Stage A Sec B), redirect policy
    (Sec G), the volume-sanity ceiling (Sec J), and the seven Stage A
    Sec E.1 deadline checkpoints. All network I/O is replaced by
    _ScriptedSession; retry backoff sleep and its jitter are mocked out so
    these tests run instantly and deterministically."""

    def setUp(self):
        self._sleep_patch = mock.patch.object(fl.time, "sleep", lambda secs: None)
        self._sleep_patch.start()
        self._jitter_patch = mock.patch("random.uniform", return_value=1.0)
        self._jitter_patch.start()
        # fetch_source() funnels every progress line through fl.pprint(); several of
        # those lines are unconditional (not gated by _QUIET/_NO_PROGRESS) and contain
        # non-ASCII glyphs (e.g. U+2193 DOWNWARDS ARROW), which raise UnicodeEncodeError
        # on a cp1252 Windows stdout. Silence the funnel itself for these direct
        # fetch_source() calls rather than toggling the CLI flags, which do not cover
        # every call site.
        self._pprint_patch = mock.patch.object(fl, "pprint", lambda *a, **kw: None)
        self._pprint_patch.start()

    def tearDown(self):
        self._pprint_patch.stop()
        self._jitter_patch.stop()
        self._sleep_patch.stop()

    def _source(self, name="S1", url="https://example.invalid/feed"):
        return {"name": name, "ccaa": None, "url": url}

    # --- legacy compatibility (no bounded params) -------------------------

    def test_legacy_call_omits_bounded_params_preserves_redirects_true(self):
        session = _ScriptedSession([_fake_atom_response()])
        fl.fetch_source(session, self._source(), max_pages=1, min_score=20)
        self.assertEqual(session.calls[0]["allow_redirects"], True)
        self.assertEqual(session.calls[0]["timeout"], fl.TIMEOUT)

    def test_legacy_call_has_no_deadline_or_budget_enforcement(self):
        session = _ScriptedSession([
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
            _fake_atom_response(),
        ])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=3)
        self.assertFalse(result["had_error"])
        self.assertEqual(len(session.calls), 3)
        self.assertFalse(result["deadline_exhausted"])
        self.assertFalse(result["budget_exhausted"])

    # --- single-layer retry / attempt accounting (Sec A/H) ----------------

    def test_budget_counts_exactly_each_real_attempt(self):
        session = _ScriptedSession([
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
            _fake_atom_response(),
        ])
        budget = fetch_bounds.RequestBudget(10)
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  retries=3, budget=budget)
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(budget.used, 3)
        self.assertEqual(result["retry_count"], 2)
        self.assertFalse(result["had_error"])

    def test_retries_bounded_at_max_attempts_then_terminal(self):
        session = _ScriptedSession([
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
        ])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=3)
        # retries=3 -> at most 4 total attempts (1 initial + 3 retries).
        self.assertEqual(len(session.calls), 4)
        self.assertTrue(result["had_error"])

    def test_budget_prevents_attempt_before_network_call(self):
        session = _ScriptedSession([
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
            _fake_atom_response(),  # never reached -- budget exhausted first
        ])
        budget = fetch_bounds.RequestBudget(2)
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  retries=3, budget=budget)
        self.assertEqual(len(session.calls), 2)  # 3rd attempt never made
        self.assertTrue(result["budget_exhausted"])
        self.assertTrue(result["had_error"])

    # --- failure classification (Stage A Sec B) --------------------------

    def test_retryable_connect_error_recovers(self):
        session = _ScriptedSession([requests.exceptions.ConnectionError("x"), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])
        self.assertEqual(len(session.calls), 2)

    def test_retryable_timeout_recovers(self):
        session = _ScriptedSession([requests.exceptions.Timeout("x"), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_retryable_ssl_error_recovers(self):
        session = _ScriptedSession([requests.exceptions.SSLError("x"), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_retryable_chunked_encoding_error_recovers(self):
        session = _ScriptedSession([requests.exceptions.ChunkedEncodingError("x"), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_retryable_http_429_recovers(self):
        session = _ScriptedSession([_FakeResponse(status_code=429), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_retryable_http_5xx_recovers(self):
        session = _ScriptedSession([_FakeResponse(status_code=503), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_retryable_malformed_non_atom_body_recovers(self):
        session = _ScriptedSession([_FakeResponse(status_code=200, content=b"<html>oops</html>"),
                                     _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_retryable_xml_parse_error_recovers(self):
        session = _ScriptedSession([_FakeResponse(status_code=200, content=b"<feed><entry>"),
                                     _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=1)
        self.assertFalse(result["had_error"])

    def test_terminal_other_4xx_not_retried(self):
        session = _ScriptedSession([_FakeResponse(status_code=404), _fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=3)
        self.assertTrue(result["had_error"])
        self.assertEqual(len(session.calls), 1)  # never retried

    def test_terminal_redirect_blocked_when_bounded(self):
        session = _ScriptedSession([
            _FakeResponse(status_code=302, headers={"Location": "https://elsewhere.invalid/"}),
            _fake_atom_response(),
        ])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20, retries=3,
                                  allow_redirects=False)
        self.assertTrue(result["had_error"])
        self.assertEqual(len(session.calls), 1)  # never retried, never followed
        self.assertIn("redirect blocked", result["error_msg"])

    def test_redirect_kwarg_passed_through_when_not_bounded(self):
        session = _ScriptedSession([_fake_atom_response()])
        fl.fetch_source(session, self._source(), max_pages=1, min_score=20, allow_redirects=True)
        self.assertEqual(session.calls[0]["allow_redirects"], True)

    # --- volume-sanity ceiling (Stage A Sec J) ----------------------------

    def test_max_source_records_none_means_unlimited(self):
        session = _ScriptedSession([_fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  max_source_records=None)
        self.assertFalse(result["had_error"])

    def test_max_source_records_ceiling_aborts_never_truncates(self):
        # An empty <feed> yields 0 accepted records; a ceiling of -1 is
        # always exceeded once any non-negative count is reached, so this
        # deterministically exercises the fail-closed abort path without
        # depending on the scoring pipeline accepting synthetic entries.
        session = _ScriptedSession([_fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  max_source_records=-1)
        self.assertTrue(result["had_error"])
        self.assertIn("volume ceiling exceeded", result["error_msg"])

    # --- deadline checkpoints (Stage A Sec E.1) ---------------------------

    def test_deadline_already_expired_admits_no_attempt(self):
        clock = _ManualClock(start=100.0)
        deadline = fetch_bounds.Deadline(1.0, clock=clock)
        clock.t = 200.0  # already past deadline_at=101.0
        session = _ScriptedSession([_fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  deadline=deadline)
        self.assertTrue(result["deadline_exhausted"])
        self.assertEqual(len(session.calls), 0)

    def test_deadline_expiry_during_backoff_prevents_next_attempt(self):
        clock = _ManualClock(start=0.0)
        deadline = fetch_bounds.Deadline(1.0, clock=clock)
        session = _ScriptedSession([requests.exceptions.ConnectionError("boom")])
        with mock.patch.object(fl.time, "sleep", lambda secs: setattr(clock, "t", clock.t + secs)):
            result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                      retries=3, retry_delay=2.0, retry_backoff=2.0,
                                      deadline=deadline)
        # retry_delay(2.0) * backoff**(1-1)(=1) * jitter(1.0) = 2.0s sleep,
        # which alone exceeds the 1.0s deadline -- no second real attempt.
        self.assertTrue(result["deadline_exhausted"])
        self.assertEqual(len(session.calls), 1)

    def test_deadline_expiry_prevents_next_page(self):
        # R2 (Prompt 323 Stage B R2, WRKOPS t_20260923_adgops323): the shared
        # Deadline is now checked immediately on response return, before
        # non-Atom inspection / XML parsing / page-completion accounting.
        # Expiry on response return therefore prevents completion of the
        # current page as well as advancement to the next page -- pages_done
        # stays 0, not 1, because the response that arrived after expiry is
        # rejected before it is ever parsed or counted.
        clock = _ManualClock(start=0.0)
        deadline = fetch_bounds.Deadline(5.0, clock=clock)
        call_count = [0]

        def _advance_and_return(url, timeout=None, allow_redirects=True):
            call_count[0] += 1
            clock.t += 6.0  # exceeds the 5.0s deadline after this one response
            return _fake_atom_response(next_href="https://example.invalid/feed?page=2")

        session = _ScriptedSession([])
        session.get = _advance_and_return
        result = fl.fetch_source(session, self._source(), max_pages=2, min_score=20,
                                  deadline=deadline)
        self.assertTrue(result["deadline_exhausted"])
        self.assertEqual(result["pages_done"], 0)
        self.assertEqual(call_count[0], 1)  # no request for page 2

    def test_deadline_expiry_prevents_next_source(self):
        clock = _ManualClock(start=0.0)
        deadline = fetch_bounds.Deadline(10.0, clock=clock)

        session1 = _ScriptedSession([_fake_atom_response()])
        result1 = fl.fetch_source(session1, self._source("S1"), max_pages=1, min_score=20,
                                   deadline=deadline)
        self.assertFalse(result1["deadline_exhausted"])
        self.assertEqual(len(session1.calls), 1)

        clock.t = 11.0  # past the shared deadline before the next source starts

        session2 = _ScriptedSession([_fake_atom_response()])
        result2 = fl.fetch_source(session2, self._source("S2"), max_pages=1, min_score=20,
                                   deadline=deadline)
        self.assertTrue(result2["deadline_exhausted"])
        self.assertEqual(len(session2.calls), 0)


class StagedAcquisitionFetchSourceTests(unittest.TestCase):
    """WRKOPS t_20261004_adgops335 (P331-B15 D1/D4): fetch_source()'s new
    start_url/exhausted/next_url contract -- the minimal per-call primitive
    the acquisition-staging continuation design resumes from. No network."""

    def setUp(self):
        self._pprint_patch = mock.patch.object(fl, "pprint", lambda *a, **kw: None)
        self._pprint_patch.start()

    def tearDown(self):
        self._pprint_patch.stop()

    def _source(self, name="S1", url="https://example.invalid/feed"):
        return {"name": name, "ccaa": None, "url": url}

    def test_start_url_overrides_source_base_url(self):
        session = _ScriptedSession([_fake_atom_response()])
        fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                         start_url="https://example.invalid/feed?resume=p7")
        self.assertEqual(session.calls[0]["url"], "https://example.invalid/feed?resume=p7")

    def test_start_url_none_uses_source_base_url(self):
        session = _ScriptedSession([_fake_atom_response()])
        fl.fetch_source(session, self._source(url="https://example.invalid/base"),
                         max_pages=1, min_score=20, start_url=None)
        self.assertEqual(session.calls[0]["url"], "https://example.invalid/base")

    def test_start_url_empty_string_uses_source_base_url(self):
        session = _ScriptedSession([_fake_atom_response()])
        fl.fetch_source(session, self._source(url="https://example.invalid/base"),
                         max_pages=1, min_score=20, start_url="")
        self.assertEqual(session.calls[0]["url"], "https://example.invalid/base")

    def test_exhausted_true_on_natural_feed_termination(self):
        session = _ScriptedSession([_fake_atom_response()])  # no next link at all
        result = fl.fetch_source(session, self._source(), max_pages=5, min_score=20)
        self.assertTrue(result["exhausted"])
        self.assertEqual(result["next_url"], "")
        self.assertEqual(result["pages_done"], 1)

    def test_exhausted_false_on_ceiling_hit_with_pending_next_link(self):
        session = _ScriptedSession([
            _fake_atom_response(next_href="https://example.invalid/feed?page=2"),
        ])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20)
        self.assertFalse(result["exhausted"])
        self.assertEqual(result["next_url"], "https://example.invalid/feed?page=2")
        self.assertEqual(result["pages_done"], 1)

    def test_exhausted_false_on_had_error(self):
        session = _ScriptedSession([_FakeResponse(status_code=404)])
        result = fl.fetch_source(session, self._source(), max_pages=5, min_score=20, retries=0)
        self.assertTrue(result["had_error"])
        self.assertFalse(result["exhausted"])

    def test_exhausted_false_on_deadline_exhausted(self):
        clock = _ManualClock(start=100.0)
        deadline = fetch_bounds.Deadline(1.0, clock=clock)
        clock.t = 200.0
        session = _ScriptedSession([_fake_atom_response()])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  deadline=deadline)
        self.assertTrue(result["deadline_exhausted"])
        self.assertFalse(result["exhausted"])

    def test_next_url_resumes_across_two_calls_to_natural_exhaustion(self):
        # First call: ceiling hit at page 1 with a pending next link.
        session1 = _ScriptedSession([
            _fake_atom_response(next_href="https://example.invalid/feed?page=2"),
        ])
        result1 = fl.fetch_source(session1, self._source(), max_pages=1, min_score=20)
        self.assertFalse(result1["exhausted"])
        self.assertEqual(result1["next_url"], "https://example.invalid/feed?page=2")

        # Second call resumes from that exact cursor and reaches exhaustion.
        session2 = _ScriptedSession([_fake_atom_response()])  # no further next link
        result2 = fl.fetch_source(session2, self._source(), max_pages=1, min_score=20,
                                   start_url=result1["next_url"])
        self.assertEqual(session2.calls[0]["url"], "https://example.invalid/feed?page=2")
        self.assertTrue(result2["exhausted"])
        self.assertEqual(result2["next_url"], "")

    def test_next_url_unchanged_on_failed_attempt(self):
        # A failed attempt must not advance the cursor -- the caller's
        # staging-update logic relies on next_url reflecting only genuinely
        # completed progress (fetch_source() itself, not a caller-side
        # special case).
        session = _ScriptedSession([_FakeResponse(status_code=404)])
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  retries=0, start_url="https://example.invalid/feed?page=5")
        self.assertTrue(result["had_error"])
        self.assertEqual(result["next_url"], "https://example.invalid/feed?page=5")


class DedupMergeItemsTests(unittest.TestCase):
    """WRKOPS t_20261004_adgops335: dedup_merge_items() -- the acquisition-
    staging accumulation precedence (status_rank then rellevancia), proven
    standalone against fetch_licitaciones.py's own STATUS_RANK table. No
    network, no file I/O."""

    def _item(self, key, notice_type="PUB", rellevancia=20):
        return {"canonical_key": key, "id": key, "notice_type": notice_type,
                "rellevancia": rellevancia}

    def test_new_identity_appended(self):
        existing = [self._item("A")]
        merged = fl.dedup_merge_items(existing, [self._item("B")])
        self.assertEqual([i["canonical_key"] for i in merged], ["A", "B"])

    def test_higher_status_rank_wins(self):
        existing = [self._item("A", notice_type="PUB")]        # rank 2
        merged = fl.dedup_merge_items(existing, [self._item("A", notice_type="AWARD")])  # rank 8
        self.assertEqual(merged[0]["notice_type"], "AWARD")

    def test_lower_status_rank_never_overwrites(self):
        existing = [self._item("A", notice_type="AWARD")]       # rank 8
        merged = fl.dedup_merge_items(existing, [self._item("A", notice_type="PUB")])    # rank 2
        self.assertEqual(merged[0]["notice_type"], "AWARD")

    def test_tie_break_by_rellevancia(self):
        existing = [self._item("A", notice_type="PUB", rellevancia=20)]
        merged = fl.dedup_merge_items(existing, [self._item("A", notice_type="PUB", rellevancia=45)])
        self.assertEqual(merged[0]["rellevancia"], 45)

    def test_idempotent_replay(self):
        existing = [self._item("A")]
        new = [self._item("A")]
        once = fl.dedup_merge_items(existing, new)
        twice = fl.dedup_merge_items(once, new)
        self.assertEqual(once, twice)
        self.assertEqual(len(twice), 1)

    def test_preserves_position_of_existing_identity(self):
        existing = [self._item("A"), self._item("B")]
        merged = fl.dedup_merge_items(existing, [self._item("A", notice_type="AWARD")])
        self.assertEqual([i["canonical_key"] for i in merged], ["A", "B"])
        self.assertEqual(merged[0]["notice_type"], "AWARD")


class DedupTombstoneListTests(unittest.TestCase):
    """WRKOPS t_20261004_adgops335: _dedup_tombstone_list() -- accumulation
    by ref, first occurrence wins (mirrors main()'s own per-run tombstone
    dedup). No network."""

    def test_dedup_by_ref_first_occurrence_wins(self):
        existing = [{"ref": "R1", "when": "2026-01-01"}]
        merged = fl._dedup_tombstone_list(
            existing, [{"ref": "R1", "when": "2026-02-02"}, {"ref": "R2", "when": ""}]
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual(next(t for t in merged if t["ref"] == "R1")["when"], "2026-01-01")


class AcquisitionStagingModuleTests(unittest.TestCase):
    """WRKOPS t_20261004_adgops335: tools/acquisition_staging.py -- shape
    validation, fresh-cycle fallback rules, atomic write, and rotation. No
    network."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_cycle_shape(self):
        staging = acquisition_staging.new_cycle(["S1", "S2"])
        self.assertEqual(staging["schema"], acquisition_staging.SCHEMA)
        self.assertEqual(set(staging["sources"].keys()), {"S1", "S2"})
        self.assertEqual(staging["data"], [])
        self.assertEqual(staging["tombstones"], [])
        self.assertFalse(staging["sources"]["S1"]["exhausted"])
        self.assertIsNone(staging["sources"]["S1"]["next_url"])

    def test_load_or_new_absent_file_starts_fresh(self):
        staging, fresh, reason = acquisition_staging.load_or_new(self.tmp / "missing.json", ["S1"])
        self.assertTrue(fresh)
        self.assertEqual(reason, "ABSENT")
        self.assertEqual(set(staging["sources"].keys()), {"S1"})

    def test_load_or_new_malformed_json_starts_fresh(self):
        bad = self.tmp / "bad.json"
        bad.write_text("{ not valid json", encoding="utf-8")
        staging, fresh, reason = acquisition_staging.load_or_new(bad, ["S1"])
        self.assertTrue(fresh)
        self.assertEqual(reason, "MALFORMED_JSON")

    def test_load_or_new_registry_drift_starts_fresh(self):
        path = self.tmp / "staging.json"
        acquisition_staging.write_atomic(path, acquisition_staging.new_cycle(["S1", "S2"]))
        staging, fresh, reason = acquisition_staging.load_or_new(path, ["S1", "S3"])
        self.assertTrue(fresh)
        self.assertEqual(reason, "INVALID_SHAPE_OR_REGISTRY_DRIFT")
        self.assertEqual(set(staging["sources"].keys()), {"S1", "S3"})

    def test_load_or_new_valid_round_trips(self):
        path = self.tmp / "staging.json"
        original = acquisition_staging.new_cycle(["S1"])
        original["sources"]["S1"]["next_url"] = "https://example.invalid/feed?p=2"
        original["data"] = [{"id": "X1"}]
        acquisition_staging.write_atomic(path, original)
        loaded, fresh, reason = acquisition_staging.load_or_new(path, ["S1"])
        self.assertFalse(fresh)
        self.assertIsNone(reason)
        self.assertEqual(loaded["cycle_id"], original["cycle_id"])
        self.assertEqual(loaded["sources"]["S1"]["next_url"], "https://example.invalid/feed?p=2")
        self.assertEqual(loaded["data"], [{"id": "X1"}])

    def test_new_cycle_stores_source_url_fingerprint(self):
        # WRKOPS t_20261004_adgops335 corrective C2: each source's record
        # carries the registry URL it was created with, not just its name.
        sources = [{"name": "S1", "url": "https://s1.invalid/feed"},
                   {"name": "S2", "url": "https://s2.invalid/feed"}]
        staging = acquisition_staging.new_cycle(sources)
        self.assertEqual(staging["sources"]["S1"]["source_url"], "https://s1.invalid/feed")
        self.assertEqual(staging["sources"]["S2"]["source_url"], "https://s2.invalid/feed")

    def test_load_or_new_accepts_dict_shaped_registry(self):
        # tools.public_contract.PUBLIC_SOURCES shape: a dict keyed by name
        # with "url"-bearing entries, as used by scheduled_fetch_merge.py's
        # rotate() call.
        registry = {"S1": {"id": "S1", "url": "https://s1.invalid/feed"}}
        staging, fresh, reason = acquisition_staging.load_or_new(self.tmp / "missing.json", registry)
        self.assertTrue(fresh)
        self.assertEqual(staging["sources"]["S1"]["source_url"], "https://s1.invalid/feed")

    def test_load_or_new_source_url_drift_same_name_starts_fresh(self):
        # C2: the human-visible source name is unchanged but its
        # underlying feed URL drifted in the registry -- the old cycle
        # must be treated as stale/incompatible, exactly like a name-set
        # mismatch, not silently reused.
        sources_v1 = [{"name": "S1", "url": "https://s1-old.invalid/feed"}]
        path = self.tmp / "staging.json"
        acquisition_staging.write_atomic(path, acquisition_staging.new_cycle(sources_v1))

        sources_v2 = [{"name": "S1", "url": "https://s1-new.invalid/feed"}]
        staging, fresh, reason = acquisition_staging.load_or_new(path, sources_v2)
        self.assertTrue(fresh)
        self.assertEqual(reason, "INVALID_SHAPE_OR_REGISTRY_DRIFT")
        self.assertEqual(staging["sources"]["S1"]["source_url"], "https://s1-new.invalid/feed")

    def test_all_sources_exhausted_requires_every_source(self):
        staging = acquisition_staging.new_cycle(["S1", "S2"])
        self.assertFalse(acquisition_staging.all_sources_exhausted(staging))
        staging["sources"]["S1"]["exhausted"] = True
        self.assertFalse(acquisition_staging.all_sources_exhausted(staging))
        staging["sources"]["S2"]["exhausted"] = True
        self.assertTrue(acquisition_staging.all_sources_exhausted(staging))

    def test_write_atomic_leaves_no_temp_file_behind(self):
        path = self.tmp / "staging.json"
        acquisition_staging.write_atomic(path, acquisition_staging.new_cycle(["S1"]))
        leftovers = [p for p in self.tmp.glob("*") if ".tmp-" in p.name]
        self.assertEqual(leftovers, [])
        self.assertTrue(path.exists())

    def test_rotate_resets_to_fresh_empty_cycle(self):
        path = self.tmp / "staging.json"
        staging = acquisition_staging.new_cycle(["S1"])
        staging["sources"]["S1"]["exhausted"] = True
        staging["data"] = [{"id": "X1"}]
        acquisition_staging.write_atomic(path, staging)
        old_cycle_id = staging["cycle_id"]

        acquisition_staging.rotate(path, ["S1"])
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertNotEqual(reloaded["cycle_id"], old_cycle_id)
        self.assertEqual(reloaded["data"], [])
        self.assertFalse(reloaded["sources"]["S1"]["exhausted"])


class DownstreamMergeSemanticsUnchangedTests(unittest.TestCase):
    """WRKOPS t_20261004_adgops335 -- P334 §13 regression item 7: an
    executable differential proof (not merely code-reading inference) that
    get_merge_key()/build_index()/merge_overlap() produce a byte-identical
    result for a row common to both a 'single-page-shaped' candidate
    population and a much larger 'multi-page accumulated' population. No
    network."""

    def test_shared_key_merges_identically_regardless_of_population_size(self):
        prod_rec = {
            "id": "SHARED-1", "contract_folder_id": "CFID-SHARED",
            "canonical_key": "CFID-SHARED", "estat": "vigent",
            "adjudicatari": "", "lifecycle_category": "CLEAR_OPEN",
            "active_opportunity_eligible": True, "lifecycle_review_required": False,
        }
        shared_cand_rec = {
            "id": "SHARED-1", "contract_folder_id": "CFID-SHARED",
            "canonical_key": "CFID-SHARED", "estat": "adjudicado",
            "adjudicatari": "Empresa X", "award_results": [],
        }
        single_page_pop = [shared_cand_rec]
        multi_page_pop = [shared_cand_rec] + [
            {"id": f"OTHER-{i}", "contract_folder_id": f"CFID-OTHER-{i}",
             "canonical_key": f"CFID-OTHER-{i}", "estat": "vigent"}
            for i in range(50)
        ]

        idx_single = sfm.build_index(single_page_pop)
        idx_multi = sfm.build_index(multi_page_pop)
        key = sfm.get_merge_key(prod_rec)
        self.assertIn(key, idx_single)
        self.assertIn(key, idx_multi)

        result_single, conflicts_single = sfm.merge_overlap(dict(prod_rec), idx_single[key])
        result_multi, conflicts_multi = sfm.merge_overlap(dict(prod_rec), idx_multi[key])

        self.assertEqual(result_single, result_multi)
        self.assertEqual(conflicts_single, conflicts_multi)


class BoundedDeadlineCheckpointOrderingR2Tests(unittest.TestCase):
    """Prompt 323 Stage B R2 (WRKOPS t_20260923_adgops323) -- exact-diff review
    finding: the R1 cooperative deadline checkpoint #3 ("immediately after each
    response or raised request exception") was control-flow-positioned after
    several `break` exits, so it never fired on the bounded 3xx / terminal 4xx /
    non-retryable-exception / successful-Atom-parse paths. These three tests
    are written to fail against the R1 implementation and pass only once the
    checkpoint is the first statement in both the except- and else-branches of
    the session.get() try block. No network; a fake clock and a fake
    session.get() are the only inputs. Not executed by this authoring session
    (WRKOPS NO_RUNTIME) -- the operator runs this suite."""

    def setUp(self):
        self._pprint_patch = mock.patch.object(fl, "pprint", lambda *a, **kw: None)
        self._pprint_patch.start()

    def tearDown(self):
        self._pprint_patch.stop()

    def _source(self, name="S1", url="https://example.invalid/feed"):
        return {"name": name, "ccaa": None, "url": url}

    def test_deadline_checked_before_response_classification_on_success(self):
        """Test 1 (handoff Sec 6): a fake session.get() advances the clock past
        the deadline and then returns a valid Atom response. The R1 checkpoint
        sat after the success `break`, so it never fired here and
        parse_atom_entries() ran on an already-expired acquisition. Corrected
        order must raise DeadlineExceededError before any response
        classification/parsing, so parse_atom_entries() is never reached."""
        clock = _ManualClock(start=0.0)
        deadline = fetch_bounds.Deadline(1.0, clock=clock)
        calls = []

        def _expired_then_valid(url, timeout=None, allow_redirects=True):
            calls.append(1)
            clock.t = 2.0  # expire the deadline once control returns from session.get()
            return _fake_atom_response()

        session = _ScriptedSession([])
        session.get = _expired_then_valid
        with mock.patch.object(fl, "parse_atom_entries") as parse_mock:
            result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                      deadline=deadline)
        self.assertTrue(result["deadline_exhausted"])
        self.assertEqual(len(calls), 1)  # no further HTTP attempt
        parse_mock.assert_not_called()  # response content never parsed/processed after expiry

    def test_deadline_checked_before_exception_classification(self):
        """Test 2 (handoff Sec 6): a fake session.get() advances the clock past
        the deadline and then raises a retryable request exception. The
        checkpoint must fire before is_retryable_fetch_error() classification,
        so no retry is admitted and deadline exhaustion is not converted into
        an ordinary network failure."""
        clock = _ManualClock(start=0.0)
        deadline = fetch_bounds.Deadline(1.0, clock=clock)
        calls = []

        def _expired_then_raise(url, timeout=None, allow_redirects=True):
            calls.append(1)
            clock.t = 2.0
            raise requests.exceptions.ConnectionError("boom")

        session = _ScriptedSession([])
        session.get = _expired_then_raise
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  retries=3, deadline=deadline)
        self.assertTrue(result["deadline_exhausted"])
        self.assertEqual(len(calls), 1)  # no second attempt/retry admitted
        self.assertEqual(result["retry_count"], 0)

    def test_deadline_checked_before_terminal_response_break(self):
        """Test 3 (handoff Sec 6): a fake session.get() advances the clock past
        the deadline and then returns a terminal (non-429) 4xx response. Under
        R1 the terminal-response `break` (from the HTTPError classification)
        exited the loop before the post-block checkpoint ever ran, so
        deadline_exhausted stayed False and the outcome was misreported as an
        ordinary terminal HTTP failure. Corrected order must raise
        DeadlineExceededError before raise_for_status()/status classification,
        so the terminal-response break can no longer bypass it."""
        clock = _ManualClock(start=0.0)
        deadline = fetch_bounds.Deadline(1.0, clock=clock)
        calls = []

        def _expired_then_terminal(url, timeout=None, allow_redirects=True):
            calls.append(1)
            clock.t = 2.0
            return _FakeResponse(status_code=404)

        session = _ScriptedSession([])
        session.get = _expired_then_terminal
        result = fl.fetch_source(session, self._source(), max_pages=1, min_score=20,
                                  retries=3, deadline=deadline)
        self.assertTrue(result["deadline_exhausted"])
        self.assertEqual(len(calls), 1)  # terminal-response break did not bypass the checkpoint


class ConsoleEncodingCompatibilityTests(unittest.TestCase):
    """Prompt 323 Stage B R4 (WRKOPS t_20260923_adgops323): the first live
    Windows bounded-sandbox run crashed with UnicodeEncodeError from
    fl.pprint()'s startup-banner print() call, before any bounded
    acquisition network attempt could occur -- a strict cp1252-encoded
    redirected stdout cannot represent this module's box-drawing/arrow
    glyphs (U+2550, U+2193, etc.). fl.pprint() now falls back to a
    backslash-escaped, encoding-safe representation instead of crashing.
    No network; a strict-encoding in-memory text stream is constructed
    directly here rather than depending on the actual host console
    encoding."""

    def test_strict_cp1252_stream_falls_back_to_escaped_representation(self):
        buf = io.BytesIO()
        stream = io.TextIOWrapper(buf, encoding="cp1252", errors="strict", newline="")
        message = "═ ↓"  # BOX DRAWINGS DOUBLE HORIZONTAL + DOWNWARDS ARROW
        with mock.patch.object(sys, "stdout", stream):
            fl.pprint(message)
            stream.flush()
        written = buf.getvalue().decode("cp1252")
        self.assertNotIn("═", written)  # the raw glyph must never reach the strict stream
        self.assertNotIn("↓", written)
        self.assertIn("\\u2550", written)    # deterministic escaped representation instead
        self.assertIn("\\u2193", written)

    def test_ascii_message_unchanged_on_normal_stream(self):
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fl.pprint("ASCII control")
        self.assertEqual(buf.getvalue(), "ASCII control\n")


class BoundedMainEnvelopeStatusTests(unittest.TestCase):
    """Proves main()'s bounded-mode status wiring end-to-end: when any
    source reports deadline/budget exhaustion, the written envelope carries
    is_partial=True and a run_status that the EXISTING
    scp.run_status_lacks_success() refusal predicate already treats as
    lacking success -- no new refusal mechanism, reusing run_live()'s
    established gate. fetch_source() itself is stubbed here (already
    covered directly by BoundedFetchSourceTests above); SOURCES and
    registry verification are patched so no real PUBLIC_SOURCES/network
    coupling is required. No network, no file writes outside a temp dir."""

    def _run_main_with_stub(self, stub_result):
        tmp = Path(tempfile.mkdtemp())
        try:
            out_path = tmp / "candidate.json"
            fake_sources = [{"name": "S1", "ccaa": None, "url": "https://example.invalid/feed"}]

            def _stub_fetch_source(session, source, max_pages, min_score, **kwargs):
                return dict(stub_result)

            argv = ["fetch_licitaciones.py", "--output", str(out_path),
                    "--bounded-mode", "--global-deadline", "1.0", "--no-progress"]
            with mock.patch.object(fl, "SOURCES", fake_sources), \
                 mock.patch.object(fl, "fetch_source", _stub_fetch_source), \
                 mock.patch.object(fl, "build_bounded_session", lambda: object()), \
                 mock.patch.object(fetch_bounds, "verify_source_registry",
                                    lambda active_sources, registry=None: None), \
                 mock.patch.object(sys, "argv", argv), \
                 redirect_stdout(io.StringIO()):
                fl.main()

            return json.loads(out_path.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_deadline_exhaustion_produces_partial_nonsuccess_envelope(self):
        written = self._run_main_with_stub({
            "results": [], "pages_done": 0, "had_error": True,
            "error_msg": "bounded acquisition deadline exhausted",
            "retry_count": 0, "retried_pages": [], "retry_errors": [],
            "deadline_exhausted": True, "budget_exhausted": False,
        })
        self.assertTrue(written["is_partial"])
        self.assertEqual(written["run_status"], "DEADLINE_EXHAUSTED")
        self.assertTrue(written["deadline_exhausted"])
        self.assertTrue(scp.run_status_lacks_success(str(written["run_status"]).lower()))

    def test_budget_exhaustion_produces_partial_nonsuccess_envelope(self):
        written = self._run_main_with_stub({
            "results": [], "pages_done": 0, "had_error": True,
            "error_msg": "request budget exhausted",
            "retry_count": 0, "retried_pages": [], "retry_errors": [],
            "deadline_exhausted": False, "budget_exhausted": True,
        })
        self.assertTrue(written["is_partial"])
        self.assertEqual(written["run_status"], "REQUEST_BUDGET_EXHAUSTED")
        self.assertTrue(written["budget_exhausted"])
        self.assertTrue(scp.run_status_lacks_success(str(written["run_status"]).lower()))


class RunLiveHardTimeoutTests(unittest.TestCase):
    """Stage A Sec E.2/E.4: run_live()'s hard subprocess-timeout layer must
    fail closed before any candidate consumption, and must share exactly one
    GLOBAL_DEADLINE_S value with the --global-deadline flag passed to the
    bounded fetcher subprocess. subprocess.run itself is mocked to raise
    subprocess.TimeoutExpired without ever spawning a real process; no
    network, no real filesystem writes outside a temp TMP_DIR redirect."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._saved_tmp_dir = sfm.TMP_DIR
        sfm.TMP_DIR = self.tmp

    def tearDown(self):
        sfm.TMP_DIR = self._saved_tmp_dir
        self._tmp.cleanup()

    def _args(self):
        return types.SimpleNamespace(
            allow_production_write=True,
            internal_state_path=str(self.tmp / "unreadable-should-never-be-opened.json"),
            link_checks_path=None,
        )

    def test_timeout_expired_fails_closed_before_any_candidate_consumption(self):
        with mock.patch.object(
                sfm.subprocess, "run",
                side_effect=sfm.subprocess.TimeoutExpired(cmd="fetch_licitaciones.py", timeout=1.0)) as run_mock, \
             mock.patch.object(sfm, "load_json") as load_json_mock, \
             mock.patch.object(sfm, "load_internal_state") as load_state_mock, \
             mock.patch.object(sfm, "canonicalize_and_project") as canon_mock, \
             mock.patch.object(sfm, "write_json") as write_json_mock:
            with self.assertRaises(SystemExit) as cm:
                sfm.run_live(self._args())
        self.assertIn("global acquisition deadline", str(cm.exception))
        run_mock.assert_called_once()
        load_json_mock.assert_not_called()
        load_state_mock.assert_not_called()
        canon_mock.assert_not_called()
        write_json_mock.assert_not_called()

    def test_subprocess_timeout_equals_cli_global_deadline_flag(self):
        captured = {}

        def _fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["timeout"] = kwargs.get("timeout")
            raise sfm.subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

        with mock.patch.object(sfm.subprocess, "run", side_effect=_fake_run):
            with self.assertRaises(SystemExit):
                sfm.run_live(self._args())
        cmd = captured["cmd"]
        self.assertIn("--bounded-mode", cmd)
        idx = cmd.index("--global-deadline")
        cli_deadline = float(cmd[idx + 1])
        self.assertEqual(cli_deadline, captured["timeout"])
        expected = fetch_bounds.compute_global_deadline_s(
            active_source_count=len(sfm.pc.PUBLIC_SOURCES),
            pages=fetch_bounds.DEFAULT_PAGES, retries=fetch_bounds.DEFAULT_RETRIES,
            request_timeout_s=fetch_bounds.DEFAULT_REQUEST_TIMEOUT_S,
            retry_delay=fetch_bounds.DEFAULT_RETRY_DELAY_S,
            retry_backoff=fetch_bounds.DEFAULT_RETRY_BACKOFF,
        )
        self.assertAlmostEqual(cli_deadline, expected)


# ---------------------------------------------------------------------------
# WRKOPS t_20261004_adgops335 (P331-B15 D1/D4) -- P334 §13 deterministic
# regression contract items 1,2,3,4,5,6 (multi-page/multi-run accumulation)
# exercised end-to-end through fl.main()'s real staged-acquisition code
# path, and item 8 (the D4 ceiling-hit fail-closed gate) exercised end-to-
# end through sfm.run_live(). No network anywhere below: _ScriptedSession
# fakes every HTTP call and subprocess.run is faked to write a real
# candidate JSON file so the real validate_structure()/
# normalize_candidate_envelope() code paths are exercised too, not stubbed
# away.
# ---------------------------------------------------------------------------

def _design_entry_xml(eid: str, cfid: str = None, status: str = "PUB") -> str:
    """A minimal Atom <entry> that clears title_passes_gate()/score_item()'s
    min_score=20 gate (two TITLE_DESIGN_KW matches in the title alone = 20)
    and carries a ContractFolderID + ContractFolderStatusCode so identity/
    status-rank precedence (STATUS_RANK/dedup_merge_items) is exercisable."""
    return (
        "<entry>"
        f"<id>urn:test:{eid}</id>"
        f"<title>Diseño gráfico y comunicación visual {eid}</title>"
        "<content type=\"html\">Contrato de diseño gráfico y comunicación visual.</content>"
        f"<ContractFolderID>{cfid or eid}</ContractFolderID>"
        f"<ContractFolderStatusCode>{status}</ContractFolderStatusCode>"
        "</entry>"
    )


class StagedAcquisitionMainIntegrationTests(unittest.TestCase):
    """P334 §13 items 1, 2, 3, 4, 5, 6 -- a real on-disk staging file shared
    across separate fl.main() invocations, each simulating one scheduled
    run with its own _ScriptedSession. fetch_bounds.verify_source_registry
    is bypassed with a fake single-source SOURCES list, mirroring the
    existing BoundedMainEnvelopeStatusTests pattern above."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._pprint_patch = mock.patch.object(fl, "pprint", lambda *a, **kw: None)
        self._pprint_patch.start()
        # Real per-page retry/inter-page sleeps would otherwise introduce
        # real wall-clock delay (retry_delay/backoff defaults) into an
        # offline, deterministic test -- mirrors BoundedFetchSourceTests'
        # own setUp() pattern above.
        self._sleep_patch = mock.patch.object(fl.time, "sleep", lambda secs: None)
        self._sleep_patch.start()

    def tearDown(self):
        self._sleep_patch.stop()
        self._pprint_patch.stop()
        self._tmp.cleanup()

    # NOTE (post-C2 corrective): main()'s staged resume-cursor check is now
    # fetch_bounds.is_valid_continuation_url(next_url, src["url"]) -- it
    # compares a stored next_url's hostname against THIS source's OWN
    # fake URL below, not against the real tools.public_contract.
    # PUBLIC_SOURCES registry, so any fake hostname would work. It still
    # uses a real authorized hostname (contrataciondelestado.es) with a
    # synthetic path/query only for historical/readability continuity with
    # earlier passes of this task.
    _FAKE_BASE_URL = "https://contrataciondelestado.es/_wrkops_test_fixture_feed"

    def _run(self, session, staging_path, out_path, pages=1):
        fake_sources = [{"name": "S1", "ccaa": None, "url": self._FAKE_BASE_URL}]
        argv = ["fetch_licitaciones.py", "--output", str(out_path),
                "--bounded-mode", "--global-deadline", "60.0", "--no-progress",
                "--pages", str(pages),
                "--acquisition-staging-path", str(staging_path)]
        with mock.patch.object(fl, "SOURCES", fake_sources), \
             mock.patch.object(fl, "build_bounded_session", lambda: session), \
             mock.patch.object(fetch_bounds, "verify_source_registry",
                                lambda active_sources, registry=None: None), \
             mock.patch.object(sys, "argv", argv), \
             redirect_stdout(io.StringIO()):
            fl.main()
        return json.loads(out_path.read_text(encoding="utf-8"))

    def test_two_run_cycle_accumulates_pages_and_tombstone_then_completes(self):
        staging_path = self.tmp / "staging.json"

        page1 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-1"),
            next_href=self._FAKE_BASE_URL + "?page=2",
        ))
        written1 = self._run(_ScriptedSession([page1]), staging_path, self.tmp / "candidate_1.json")
        self.assertFalse(written1["acquisition_complete"])
        self.assertEqual(len(written1["data"]), 1)
        self.assertEqual(written1["data"][0]["contract_folder_id"], "CFID-1")

        page2 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=(
                _design_entry_xml("E2", cfid="CFID-2")
                + '<deleted-entry ref="E-OLD" when="2026-01-15T00:00:00Z"/>'
            ),
        ))  # no further next link -- natural exhaustion
        written2 = self._run(_ScriptedSession([page2]), staging_path, self.tmp / "candidate_2.json")

        # Item 1: both pages' entries are present in the final candidate.
        self.assertTrue(written2["acquisition_complete"])
        cfids = {d["contract_folder_id"] for d in written2["data"]}
        self.assertEqual(cfids, {"CFID-1", "CFID-2"})
        # Item 4: the page-2 tombstone is captured in the final candidate.
        self.assertEqual([t["ref"] for t in written2["tombstones"]], ["E-OLD"])

    def test_identity_observed_across_runs_resolves_to_stronger_evidence(self):
        # Item 2: a fixed identity (CFID-1) appears in run 1 ("page 1", open
        # status), then again in run 2 ("page 2" of the same traversal, now
        # with award evidence) -- identity resolution in the accumulated
        # candidate must reflect the stronger evidence regardless of which
        # run/page it arrived on.
        staging_path = self.tmp / "staging.json"
        page1 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-1", status="PUB"),
            next_href=self._FAKE_BASE_URL + "?page=2",
        ))
        self._run(_ScriptedSession([page1]), staging_path, self.tmp / "c1.json")

        page2 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1-upd", cfid="CFID-1", status="ADJ"),
        ))
        written2 = self._run(_ScriptedSession([page2]), staging_path, self.tmp / "c2.json")

        self.assertTrue(written2["acquisition_complete"])
        matches = [d for d in written2["data"] if d["contract_folder_id"] == "CFID-1"]
        self.assertEqual(len(matches), 1)  # no duplicate identity
        self.assertEqual(matches[0]["estat"], "Adjudicado")  # stronger evidence won

    def test_duplicate_identity_within_same_accumulated_cycle_collapses(self):
        # Item 3: the SAME identity observed twice (once per run) collapses
        # to one record in the accumulated candidate, never duplicated.
        staging_path = self.tmp / "staging.json"
        page1 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-DUP", status="PUB"),
            next_href=self._FAKE_BASE_URL + "?page=2",
        ))
        self._run(_ScriptedSession([page1]), staging_path, self.tmp / "c1.json")
        page2 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1-again", cfid="CFID-DUP", status="PUB"),
        ))
        written2 = self._run(_ScriptedSession([page2]), staging_path, self.tmp / "c2.json")
        matches = [d for d in written2["data"] if d["contract_folder_id"] == "CFID-DUP"]
        self.assertEqual(len(matches), 1)

    def test_mid_cycle_attempt_failure_leaves_cursor_and_data_untouched(self):
        # Item 5 (cross-run shape): a whole run whose SINGLE page-1 attempt
        # fails outright (retries exhausted) leaves that source's staged
        # cursor/accumulated data exactly as it was before the attempt --
        # the next run retries the SAME position, never silently skipping
        # ahead or losing already-staged progress. This is the "retry the
        # last position" case; see
        # test_mid_pagination_failure_within_one_run_retains_completed_page_and_resumes_at_failed_page
        # below (WRKOPS t_20261004_adgops335 corrective C3) for the
        # distinct "page 1 succeeds, page 2 fails, both within the SAME
        # run" shape P334's item 5 also requires.
        staging_path = self.tmp / "staging.json"
        page1 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-1"),
            next_href=self._FAKE_BASE_URL + "?page=2",
        ))
        self._run(_ScriptedSession([page1]), staging_path, self.tmp / "c1.json")
        before = json.loads(staging_path.read_text(encoding="utf-8"))

        failing_session = _ScriptedSession([
            _FakeResponse(status_code=503), _FakeResponse(status_code=503),
            _FakeResponse(status_code=503), _FakeResponse(status_code=503),
        ])
        written2 = self._run(failing_session, staging_path, self.tmp / "c2.json")
        after = json.loads(staging_path.read_text(encoding="utf-8"))

        self.assertFalse(written2["acquisition_complete"])
        self.assertTrue(written2["failed_sources"])
        self.assertEqual(after["sources"]["S1"]["next_url"], before["sources"]["S1"]["next_url"])
        self.assertEqual(after["data"], before["data"])
        self.assertEqual(after["sources"]["S1"]["exhausted"], before["sources"]["S1"]["exhausted"])

    def test_mid_pagination_failure_within_one_run_retains_completed_page_and_resumes_at_failed_page(self):
        # Item 5 (in-run shape, WRKOPS t_20261004_adgops335 corrective C3):
        # a SINGLE run configured for up to 2 pages where page 1 succeeds
        # and page 2 then fails after exhausting all retries. Asserts the
        # actual documented policy fetch_source()/main() already implement:
        # "retain only fully completed pages, resume at the first failed
        # page" (NOT whole-attempt rollback) --
        #   - page 1's entry IS present in the staged candidate (not rolled
        #     back);
        #   - the staged cursor for this source is exactly page 2's own
        #     href (the page that failed), never skipped past it and never
        #     reset to page 1;
        #   - exhausted stays False and acquisition_complete is False (D4
        #     fail-closed signal, distinct from is_partial/run_status);
        #   - no duplicate publication and no canonical/public artifact
        #     mutation result from this run (this test only exercises
        #     fl.main()'s own candidate/staging output; sfm.run_live()'s
        #     separate fail-closed gate, proven in
        #     AcquisitionCompletenessGateTests below, is what actually
        #     refuses canonicalize_and_project()/persist_internal_state()/
        #     the public write for acquisition_complete=False).
        staging_path = self.tmp / "staging.json"
        page2_href = self._FAKE_BASE_URL + "?page=2"
        page1 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-1"),
            next_href=page2_href,
        ))
        page2_failures = [_FakeResponse(status_code=503) for _ in range(4)]  # 1 + default 3 retries
        written = self._run(
            _ScriptedSession([page1] + page2_failures), staging_path, self.tmp / "c1.json", pages=2,
        )
        staged = json.loads(staging_path.read_text(encoding="utf-8"))

        self.assertFalse(written["acquisition_complete"])
        self.assertTrue(written["failed_sources"])
        self.assertEqual([d["contract_folder_id"] for d in written["data"]], ["CFID-1"])
        self.assertEqual(staged["sources"]["S1"]["next_url"], page2_href)
        self.assertFalse(staged["sources"]["S1"]["exhausted"])
        self.assertEqual([d["contract_folder_id"] for d in staged["data"]], ["CFID-1"])

    def test_repeated_completing_run_is_idempotent(self):
        # Item 6: re-observing an already-exhausted source on a later run
        # (simulating a crash before rotation, so the next run re-starts
        # before the staging cycle was ever reset) makes zero new HTTP
        # calls and produces byte-identical accumulated data.
        staging_path = self.tmp / "staging.json"
        page1 = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-1"),
        ))  # naturally exhausts in one page, no next link
        written1 = self._run(_ScriptedSession([page1]), staging_path, self.tmp / "c1.json")
        self.assertTrue(written1["acquisition_complete"])

        written2 = self._run(_ScriptedSession([]), staging_path, self.tmp / "c2.json")
        self.assertTrue(written2["acquisition_complete"])
        self.assertEqual(written1["data"], written2["data"])


class CrossSourceCursorIsolationTests(unittest.TestCase):
    """WRKOPS t_20261004_adgops335 corrective C1/C2, end-to-end through
    fl.main(): a staged cursor whose `next_url` actually belongs to a
    DIFFERENT (but still globally-authorized) source must not be silently
    resumed under the wrong source, and discovering it must discard the
    WHOLE acquisition cycle -- not a per-source page-1 reset that quietly
    retains the rest of the cycle's accumulated data/tombstones (C1), and
    the detection itself must be bound to the source's OWN host, not the
    global authorized-host set (C2)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._pprint_patch = mock.patch.object(fl, "pprint", lambda *a, **kw: None)
        self._pprint_patch.start()
        self._sleep_patch = mock.patch.object(fl.time, "sleep", lambda secs: None)
        self._sleep_patch.start()

    def tearDown(self):
        self._sleep_patch.stop()
        self._pprint_patch.stop()
        self._tmp.cleanup()

    _URL_A = "https://source-a.invalid/feed"
    _URL_B = "https://source-b.invalid/feed"

    def test_cross_source_cursor_triggers_whole_cycle_discard(self):
        fake_sources = [
            {"name": "SA", "ccaa": None, "url": self._URL_A},
            {"name": "SB", "ccaa": None, "url": self._URL_B},
        ]
        staging_path = self.tmp / "staging.json"

        # Hand-craft a staging cycle whose SA cursor actually points at
        # SB's host -- the exact cross-source-bleed shape C2 names
        # ("PLACSP-643 staging cannot silently resume through a
        # continuation that belongs to PLACSP-1044").
        corrupt = acquisition_staging.new_cycle(fake_sources)
        corrupt["sources"]["SA"]["next_url"] = self._URL_B + "?page=7"
        corrupt["data"] = [{"id": "STALE", "contract_folder_id": "CFID-STALE"}]
        corrupt["tombstones"] = [{"ref": "STALE-REF", "when": "2026-01-01"}]
        acquisition_staging.write_atomic(staging_path, corrupt)
        old_cycle_id = corrupt["cycle_id"]

        page_a = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("EA", cfid="CFID-A"),
        ))
        page_b = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("EB", cfid="CFID-B"),
        ))
        session = _ScriptedSession([page_a, page_b])
        out_path = self.tmp / "candidate.json"
        argv = ["fetch_licitaciones.py", "--output", str(out_path),
                "--bounded-mode", "--global-deadline", "60.0", "--no-progress",
                "--acquisition-staging-path", str(staging_path)]
        with mock.patch.object(fl, "SOURCES", fake_sources), \
             mock.patch.object(fl, "build_bounded_session", lambda: session), \
             mock.patch.object(fetch_bounds, "verify_source_registry",
                                lambda active_sources, registry=None: None), \
             mock.patch.object(sys, "argv", argv), \
             redirect_stdout(io.StringIO()):
            fl.main()
        written = json.loads(out_path.read_text(encoding="utf-8"))
        staged = json.loads(staging_path.read_text(encoding="utf-8"))

        # Both sources were fetched from their OWN base URL this run --
        # the corrupted cursor was never resumed under either source.
        self.assertEqual([c["url"] for c in session.calls], [self._URL_A, self._URL_B])
        # The whole cycle was discarded -- a new cycle_id, and the stale
        # data/tombstones from the corrupted cycle are gone entirely, not
        # merely the one offending source's cursor.
        self.assertNotEqual(staged["cycle_id"], old_cycle_id)
        self.assertNotIn("CFID-STALE", [d.get("contract_folder_id") for d in staged["data"]])
        self.assertEqual(staged.get("tombstones", []), [])
        # Forward progress still happened: this run's own fresh fetch for
        # both sources is present in the new cycle and the candidate.
        self.assertEqual({d["contract_folder_id"] for d in written["data"]}, {"CFID-A", "CFID-B"})
        self.assertEqual({d["contract_folder_id"] for d in staged["data"]}, {"CFID-A", "CFID-B"})

    # --- WRKOPS t_20261007_adgops338 (DF-1 / P331-B15 lineage): PLACSP-1044's
    # explicitly authorized alternate pagination host must resume normally
    # through this exact C1 whole-cycle-discard seam, never falling into it;
    # an unrelated host for the same source must still fall into it. Source
    # url below is a synthetic placeholder (verify_source_registry is
    # bypassed, as in every other test in this class) -- only the source
    # NAME "PLACSP-1044" need be real, since tools.public_contract.
    # CONTINUATION_HOST_AUTHORIZATIONS is keyed by source id, and only the
    # resumed continuation host below is a real, already-public hostname
    # (P337 §12), with a synthetic path/query, per this class's and
    # StagedAcquisitionMainIntegrationTests' existing convention.
    _PLACSP1044_SYNTHETIC_URL = "https://source-placsp1044.invalid/feed"
    _PLACSP1044_AUTHORIZED_ALT_HREF = (
        "https://contrataciondelestado.es/_wrkops_test_fixture_feed?page=9"
    )

    def test_placsp1044_authorized_alt_host_resumes_without_whole_cycle_discard(self):
        fake_sources = [{"name": "PLACSP-1044", "ccaa": None, "url": self._PLACSP1044_SYNTHETIC_URL}]
        staging_path = self.tmp / "staging.json"

        staging = acquisition_staging.new_cycle(fake_sources)
        staging["sources"]["PLACSP-1044"]["next_url"] = self._PLACSP1044_AUTHORIZED_ALT_HREF
        staging["data"] = [{"id": "PRIOR", "contract_folder_id": "CFID-PRIOR"}]
        acquisition_staging.write_atomic(staging_path, staging)
        old_cycle_id = staging["cycle_id"]

        page = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-NEW"),
        ))  # no further next link -- natural exhaustion
        session = _ScriptedSession([page])
        out_path = self.tmp / "candidate.json"
        argv = ["fetch_licitaciones.py", "--output", str(out_path),
                "--bounded-mode", "--global-deadline", "60.0", "--no-progress",
                "--acquisition-staging-path", str(staging_path)]
        with mock.patch.object(fl, "SOURCES", fake_sources), \
             mock.patch.object(fl, "build_bounded_session", lambda: session), \
             mock.patch.object(fetch_bounds, "verify_source_registry",
                                lambda active_sources, registry=None: None), \
             mock.patch.object(sys, "argv", argv), \
             redirect_stdout(io.StringIO()):
            fl.main()
        written = json.loads(out_path.read_text(encoding="utf-8"))
        staged = json.loads(staging_path.read_text(encoding="utf-8"))

        # The cycle was RESUMED, not discarded: same cycle_id, prior
        # accumulated data retained, and the real HTTP call went to the
        # staged continuation href itself, not a page-1 reset to the
        # source's own base URL.
        self.assertEqual(staged["cycle_id"], old_cycle_id)
        self.assertEqual([c["url"] for c in session.calls], [self._PLACSP1044_AUTHORIZED_ALT_HREF])
        self.assertIn("CFID-PRIOR", [d.get("contract_folder_id") for d in staged["data"]])
        self.assertTrue(written["acquisition_complete"])
        self.assertEqual(
            {d["contract_folder_id"] for d in written["data"]}, {"CFID-PRIOR", "CFID-NEW"},
        )

    def test_placsp1044_unrelated_host_still_triggers_whole_cycle_discard(self):
        fake_sources = [{"name": "PLACSP-1044", "ccaa": None, "url": self._PLACSP1044_SYNTHETIC_URL}]
        staging_path = self.tmp / "staging.json"

        staging = acquisition_staging.new_cycle(fake_sources)
        staging["sources"]["PLACSP-1044"]["next_url"] = "https://unrelated-host.invalid/feed?page=9"
        staging["data"] = [{"id": "STALE", "contract_folder_id": "CFID-STALE"}]
        acquisition_staging.write_atomic(staging_path, staging)
        old_cycle_id = staging["cycle_id"]

        page = _FakeResponse(status_code=200, content=_atom_bytes(
            entries_xml=_design_entry_xml("E1", cfid="CFID-FRESH"),
        ))
        session = _ScriptedSession([page])
        out_path = self.tmp / "candidate.json"
        argv = ["fetch_licitaciones.py", "--output", str(out_path),
                "--bounded-mode", "--global-deadline", "60.0", "--no-progress",
                "--acquisition-staging-path", str(staging_path)]
        with mock.patch.object(fl, "SOURCES", fake_sources), \
             mock.patch.object(fl, "build_bounded_session", lambda: session), \
             mock.patch.object(fetch_bounds, "verify_source_registry",
                                lambda active_sources, registry=None: None), \
             mock.patch.object(sys, "argv", argv), \
             redirect_stdout(io.StringIO()):
            fl.main()
        staged = json.loads(staging_path.read_text(encoding="utf-8"))

        # Discard semantics preserved: new cycle_id, stale data gone, and
        # the real HTTP call went to the source's OWN base URL (page 1),
        # never to the unauthorized stored href.
        self.assertNotEqual(staged["cycle_id"], old_cycle_id)
        self.assertEqual([c["url"] for c in session.calls], [self._PLACSP1044_SYNTHETIC_URL])
        self.assertNotIn("CFID-STALE", [d.get("contract_folder_id") for d in staged["data"]])


class AcquisitionCompletenessGateTests(unittest.TestCase):
    """P334 §13 item 8 -- all four required properties of the new
    acquisition_complete fail-closed gate in sfm.run_live(): (1) the signal
    is set false, (2) distinct from is_partial/run_status, (3) refusal
    occurs before persist_internal_state()/canonicalize_and_project()/public
    write, (4) both production surfaces remain byte-identical before/after.
    subprocess.run is faked to write a real candidate JSON file (not merely
    mocked away), so normalize_candidate_envelope()/validate_structure() run
    for real too. No network; nothing is ever written outside a temp dir
    (PRODUCTION_PATH/TMP_DIR are both redirected for the duration of this
    class)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._saved_tmp_dir = sfm.TMP_DIR
        sfm.TMP_DIR = self.tmp
        self._saved_prod_path = sfm.PRODUCTION_PATH
        self.prod_path = self.tmp / "licitaciones.json"
        self.prod_path.write_text(json.dumps({"meta": {"sentinel": True}, "data": []}), encoding="utf-8")
        sfm.PRODUCTION_PATH = self.prod_path
        self.internal_state_path = self.tmp / "internal_state.json"
        self.internal_state_path.write_text(
            json.dumps({"meta": {"sentinel": True}, "data": []}), encoding="utf-8"
        )
        # run_live()'s backup step hardcodes Path("data/_backup") relative to
        # CWD (not derived from PRODUCTION_PATH) and always mkdir(exist_ok=
        # True)s it even though shutil.copy2 into it is mocked below -- track
        # whether this repo-relative directory pre-existed so the "proceeds"
        # test can remove it again afterward rather than leaving a stray
        # empty directory behind (gitignored, but still an unrequested
        # filesystem side effect outside this test's own temp dir).
        self._real_backup_dir = Path("data/_backup")
        self._backup_dir_preexisted = self._real_backup_dir.exists()

    def tearDown(self):
        sfm.PRODUCTION_PATH = self._saved_prod_path
        sfm.TMP_DIR = self._saved_tmp_dir
        self._tmp.cleanup()
        if not self._backup_dir_preexisted and self._real_backup_dir.exists():
            self._real_backup_dir.rmdir()  # fails loudly if unexpectedly non-empty

    def _args(self, acquisition_staging_path):
        return types.SimpleNamespace(
            allow_production_write=True,
            internal_state_path=str(self.internal_state_path),
            link_checks_path=None,
            acquisition_staging_path=acquisition_staging_path,
        )

    @staticmethod
    def _fake_subprocess_run(candidate_payload):
        def _run(cmd, **kwargs):
            out_idx = cmd.index("--output")
            candidate_path = Path(cmd[out_idx + 1])
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text(json.dumps(candidate_payload), encoding="utf-8")
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        return _run

    @staticmethod
    def _incomplete_candidate():
        return {
            "generated_at": "2026-10-05T00:00:00Z",
            "is_partial": False,
            "run_status": "FULL_SUCCESS",
            "failed_sources": [],
            "source_errors": {},
            "requested_sources": ["S1"],
            "completed_sources": ["S1"],
            "acquisition_complete": False,
            "data": [],
        }

    def test_refuses_distinct_from_is_partial_before_any_state_mutation(self):
        staging_path = self.tmp / "staging.json"
        before_prod = self.prod_path.read_bytes()
        before_state = self.internal_state_path.read_bytes()

        with mock.patch.object(sfm.subprocess, "run",
                                side_effect=self._fake_subprocess_run(self._incomplete_candidate())), \
             mock.patch.object(sfm, "load_internal_state") as load_state_mock, \
             mock.patch.object(sfm, "canonicalize_and_project") as canon_mock, \
             mock.patch.object(sfm, "write_json") as write_json_mock, \
             mock.patch.object(acquisition_staging, "rotate") as rotate_mock:
            with self.assertRaises(SystemExit) as cm:
                sfm.run_live(self._args(str(staging_path)))

        # (1)+(2): the message names the new signal, not is_partial -- this
        # candidate's is_partial is False/run_status FULL_SUCCESS, so only
        # the NEW gate's own code path can have produced this refusal.
        self.assertIn("Acquisition incomplete", str(cm.exception))
        self.assertIn("acquisition_complete", str(cm.exception))
        # (3): refused before any of the three state-mutating calls.
        load_state_mock.assert_not_called()
        canon_mock.assert_not_called()
        write_json_mock.assert_not_called()
        rotate_mock.assert_not_called()
        # (4): both production surfaces byte-identical.
        self.assertEqual(self.prod_path.read_bytes(), before_prod)
        self.assertEqual(self.internal_state_path.read_bytes(), before_state)

    def test_proceeds_and_rotates_when_acquisition_complete_true(self):
        staging_path = self.tmp / "staging.json"
        complete_candidate = dict(self._incomplete_candidate())
        complete_candidate["acquisition_complete"] = True

        with mock.patch.object(sfm.subprocess, "run",
                                side_effect=self._fake_subprocess_run(complete_candidate)), \
             mock.patch.object(sfm, "load_internal_state",
                                return_value={"data": [], "meta": {}}) as load_state_mock, \
             mock.patch.object(sfm, "canonicalize_and_project", return_value=[]) as canon_mock, \
             mock.patch.object(sfm.shutil, "copy2") as copy2_mock, \
             mock.patch.object(acquisition_staging, "rotate") as rotate_mock:
            sfm.run_live(self._args(str(staging_path)))

        load_state_mock.assert_called_once()
        canon_mock.assert_called_once()
        copy2_mock.assert_called_once()  # backup step neutralized, not skipped silently
        rotate_mock.assert_called_once()
        written = json.loads(self.prod_path.read_bytes())
        self.assertEqual(written["data"], [])

    def test_legacy_mode_without_staging_path_skips_new_gate(self):
        # Backward compatibility: omitting --acquisition-staging-path
        # entirely must preserve the exact pre-existing behavior -- an
        # acquisition_complete=false candidate is NOT refused by the new
        # gate when the D1 staging authority is not in play for this call.
        with mock.patch.object(sfm.subprocess, "run",
                                side_effect=self._fake_subprocess_run(self._incomplete_candidate())), \
             mock.patch.object(sfm, "load_internal_state",
                                return_value={"data": [], "meta": {}}) as load_state_mock, \
             mock.patch.object(sfm, "canonicalize_and_project",
                                side_effect=RuntimeError("reached-canonicalize-probe")) as canon_mock:
            with self.assertRaises(RuntimeError):
                sfm.run_live(self._args(None))
        load_state_mock.assert_called_once()
        canon_mock.assert_called_once()

    def test_subprocess_cmd_carries_staging_flag_only_when_set(self):
        captured = {}

        def _run(cmd, **kwargs):
            captured["cmd"] = cmd
            raise sfm.subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

        with mock.patch.object(sfm.subprocess, "run", side_effect=_run):
            with self.assertRaises(SystemExit):
                sfm.run_live(self._args(str(self.tmp / "staging.json")))
        self.assertIn("--acquisition-staging-path", captured["cmd"])
        idx = captured["cmd"].index("--acquisition-staging-path")
        self.assertEqual(captured["cmd"][idx + 1], str(self.tmp / "staging.json"))

        with mock.patch.object(sfm.subprocess, "run", side_effect=_run):
            with self.assertRaises(SystemExit):
                sfm.run_live(self._args(None))
        self.assertNotIn("--acquisition-staging-path", captured["cmd"])


# ---------------------------------------------------------------------------
# Prompt 327 (WRKOPS t_20260925_adgops327): write_json() exact-byte contract.
# Bounded and synthetic -- exercises tools.scheduled_fetch_merge.write_json()
# directly (the real production implementation, not a duplicated serializer)
# against a small in-memory payload written to a temp path. Never reads
# data/licitaciones.json.
# ---------------------------------------------------------------------------

class WriteJsonByteDeterminismTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _payload(self):
        return {"meta": {"a": 1, "b": "café ☃"}, "data": [{"x": 1}, {"y": [1, 2]}]}

    def test_output_bytes_equal_deterministic_expected_serialization(self):
        out = self.tmp / "out.json"
        payload = self._payload()
        sfm.write_json(out, payload)
        expected = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.assertEqual(out.read_bytes(), expected)

    def test_line_separators_are_lf(self):
        out = self.tmp / "out.json"
        sfm.write_json(out, self._payload())
        raw = out.read_bytes()
        self.assertIn(b"\n", raw)
        self.assertNotIn(b"\r\n", raw)

    def test_no_bom(self):
        out = self.tmp / "out.json"
        sfm.write_json(out, self._payload())
        raw = out.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))

    def test_json_remains_parseable_and_semantically_equivalent(self):
        out = self.tmp / "out.json"
        payload = self._payload()
        sfm.write_json(out, payload)
        reloaded = json.loads(out.read_bytes().decode("utf-8"))
        self.assertEqual(reloaded, payload)


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
