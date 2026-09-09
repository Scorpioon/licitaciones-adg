#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/test_canonical_tender_merge.py  (ADG-OPS / WRKOPS t_20260908_adgops292 / v0.7.4p)

Offline/synthetic regression suite for tools/canonical_tender_merge.py.

Standard-library only (unittest). No network. No file writes. No reads of
data/** -- every record used below is a synthetic inline literal, never real
feed data. Mirrors the repo's existing test convention
(tools/test_public_projection.py): lettered TestCase groups, a custom
main() summary line, run directly with `python tools/test_canonical_tender_merge.py [-v]`.

Per the Prompt 292 handoff and boundary law NO_RUNTIME, this suite is
NOT executed by Claude as part of this task -- it is written for later
OPERATOR validation.

Run:
  python tools/test_canonical_tender_merge.py [-v]

Final line:
  CANONICAL_TENDER_MERGE TESTS: PASS (N cases)
  CANONICAL_TENDER_MERGE TESTS: FAIL (N cases)
"""

import copy
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.canonical_tender_merge as ctm  # noqa: E402


# --------------------------------------------------------------------------- #
# Synthetic fixture builders
#
# CK and LEGACY defaults deliberately agree on every field neither test group
# is exercising (estat, rellevancia, pressupost, tipus, ccaa/lloc/titol,
# adjudicatari) so that a test focused on one field law never trips an
# unrelated fail-closed path. CK carries notice_type="PUB" (VALID_RANK) and a
# later effective_notice_date than LEGACY by default, matching the
# overwhelmingly typical real-data pair shape (Prompt 291 R1/R2); tests that
# specifically exercise STATUS_AUTHORITY_V1 override these explicitly.
# --------------------------------------------------------------------------- #

def base_ck_row(**overrides):
    row = {
        "id": "https://example.org/tender/1",
        "canonical_key": "CK-1",
        "contract_folder_id": "CFID-1",
        "notice_type": "PUB",
        "estat": "Vigente",
        "estat_raw": "PUB",
        "data_pub": "2026-01-10",
        "data_limit": "2026-02-10",
        "first_pub_date": "2026-01-10",
        "last_notice_date": "2026-01-10",
        "organisme": "Test Org CK",
        "pressupost": 1000.0,
        "url": "https://ck.example/notice",
        "font": "PLACSP-1044",
        "tipus": "Servicios",
        "disciplines": ["branding"],
        "kw": ["kw1"],
        "cpv": "12345678",
        "ccaa": "CT",
        "lloc": "Catalunya",
        "titol": "Test tender",
        "rellevancia": 50,
        "adjudicatari": "",
        "historial": [{"data": "2026-01-10", "estat": "Vigente", "nota": "Publicación"}],
        "notice_history": [{"notice_id": "N1", "notice_type": "PUB", "issue_date": "2026-01-10"}],
        "award_results": [],
        "documents": [],
        "related_contract_ids": [],
        "internal_bookkeeping_marker": "ck-only-internal-value",
    }
    row.update(overrides)
    return row


def base_legacy_row(**overrides):
    row = {
        "id": "https://example.org/tender/1",
        "estat": "Vigente",
        "estat_raw": "EV",
        "data_pub": "2026-01-05",
        "organisme": "Test Org Legacy",
        "pressupost": 1000.0,
        "url": "https://legacy.example/notice",
        "font": "PLACSP-643",
        "tipus": "Servicios",
        "disciplines": [],
        "kw": [],
        "cpv": "",
        "ccaa": "CT",
        "lloc": "Catalunya",
        "titol": "Test tender",
        "rellevancia": 50,
        "adjudicatari": "",
        "historial": [{"data": "2026-01-05", "estat": "Vigente", "nota": "Publicación"}],
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# A. input / record validation (list items 1-3)
# --------------------------------------------------------------------------- #

class AInputValidationTests(unittest.TestCase):

    def test_invalid_record_not_a_dict(self):
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders(["not-a-dict"])
        self.assertEqual(cm.exception.code, "invalid_record")

    def test_missing_id(self):
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([{"titol": "no id here"}])
        self.assertEqual(cm.exception.code, "invalid_id")

    def test_blank_id(self):
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([base_ck_row(id="   ")])
        self.assertEqual(cm.exception.code, "invalid_id")

    def test_records_argument_not_a_list(self):
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders("not-a-list")
        self.assertEqual(cm.exception.code, "invalid_record")


# --------------------------------------------------------------------------- #
# B. singleton (list items 4-7)
# --------------------------------------------------------------------------- #

class BSingletonTests(unittest.TestCase):

    def test_singleton_deep_copy_not_aliased(self):
        row = base_ck_row()
        result = ctm.merge_canonical_tenders([row])
        result[0]["historial"][0]["nota"] = "MUTATED"
        self.assertEqual(row["historial"][0]["nota"], "Publicación")

    def test_singleton_idempotence(self):
        row = base_ck_row(
            historial=[
                {"data": "2026-01-10", "estat": "Vigente", "nota": "Publicación"},
                {"data": "2026-01-01", "estat": "Vigente", "nota": "Publicación"},
            ]
        )
        once = ctm.merge_canonical_tenders([row])
        twice = ctm.merge_canonical_tenders(once)
        self.assertEqual(once, twice)

    def test_singleton_sentinel_normalization(self):
        row = base_ck_row(adjudicatari=ctm.ADJUDICATARI_SENTINEL)
        result = ctm.merge_canonical_tenders([row])
        self.assertEqual(result[0]["adjudicatari"], "")

    def test_lexical_output_ordering(self):
        rows = [
            base_ck_row(id="https://example.org/tender/b"),
            base_ck_row(id="https://example.org/tender/a"),
            base_ck_row(id="https://example.org/tender/c"),
        ]
        result = ctm.merge_canonical_tenders(rows)
        ids = [r["id"] for r in result]
        self.assertEqual(ids, sorted(ids))


# --------------------------------------------------------------------------- #
# C. pair identity / orientation (list items 8-13)
# --------------------------------------------------------------------------- #

class CPairIdentityTests(unittest.TestCase):

    def test_pair_identity_merges_to_one_row(self):
        ck = base_ck_row()
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], ck["id"])

    def test_pair_orientation_both_ck_fails_closed(self):
        ck1 = base_ck_row()
        ck2 = base_ck_row(canonical_key="CK-2", contract_folder_id="CFID-2")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck1, ck2])
        self.assertEqual(cm.exception.code, "pair_orientation_invalid")

    def test_pair_orientation_neither_ck_fails_closed(self):
        l1 = base_legacy_row()
        l2 = base_legacy_row(url="https://legacy.example/other")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([l1, l2])
        self.assertEqual(cm.exception.code, "pair_orientation_invalid")

    def test_multiplicity_greater_than_two_fails_closed(self):
        rows = [base_ck_row(), base_legacy_row(), base_legacy_row(url="https://legacy.example/third")]
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders(rows)
        self.assertEqual(cm.exception.code, "unsupported_group_multiplicity")

    def test_canonical_key_preserved_from_ck_row(self):
        ck = base_ck_row(canonical_key="CK-XYZ")
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["canonical_key"], "CK-XYZ")

    def test_contract_folder_id_preserved_from_ck_row(self):
        ck = base_ck_row(contract_folder_id="CFID-XYZ")
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["contract_folder_id"], "CFID-XYZ")

    def test_protected_identity_conflict_helper(self):
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm._preserve_identity_field("A", "B", "canonical_key", "id-1")
        self.assertEqual(cm.exception.code, "identity_conflict")


# --------------------------------------------------------------------------- #
# D. STATUS_AUTHORITY_V1 (list items 14-21)
# --------------------------------------------------------------------------- #

class DStatusAuthorityTests(unittest.TestCase):

    def test_both_valid_rank_higher_rank_wins(self):
        ck = base_ck_row(notice_type="AWARD", estat="Adjudicado", estat_raw="ADJ", data_pub="2026-01-01")
        legacy = base_legacy_row(notice_type="PUB", estat="Vigente", estat_raw="PUB", data_pub="2026-06-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Adjudicado")
        self.assertEqual(result[0]["estat_raw"], "ADJ")

    def test_both_valid_rank_tie_uses_later_date(self):
        ck = base_ck_row(notice_type="PUB", estat="Vigente", estat_raw="CK-PUB", data_pub="2026-01-01")
        legacy = base_legacy_row(notice_type="PUB", estat="Vigente", estat_raw="LEGACY-PUB", data_pub="2026-06-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat_raw"], "LEGACY-PUB")

    def test_both_valid_rank_tie_and_date_tie_and_differing_status_fails_closed(self):
        # R1 fixture correction: base_ck_row() defaults last_notice_date to
        # "2026-01-10", and effective_notice_date() prefers last_notice_date
        # over data_pub (handoff Sec10) -- overriding only data_pub left the
        # CK row's effective date at the un-overridden default, so the two
        # rows were never actually date-tied (Operator R1 evidence: no
        # exception raised). last_notice_date must be overridden too so both
        # rows' effective dates genuinely tie on "2026-01-01".
        ck = base_ck_row(
            notice_type="PUB", estat="Vigente", estat_raw="PUB",
            data_pub="2026-01-01", last_notice_date="2026-01-01",
        )
        legacy = base_legacy_row(notice_type="PUB", estat="Adjudicado", estat_raw="ADJ", data_pub="2026-01-01")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "status_conflict")

    def test_later_legacy_status_wins_when_only_ck_ranked(self):
        # Mirrors the 8 real Prompt 291 R1/R2 cases: CK is VALID_RANK but
        # earlier; LEGACY has no notice_type but a later date and a more
        # advanced real-world status.
        ck = base_ck_row(notice_type="PUB", estat="Vigente", estat_raw="PUB", data_pub="2026-01-01")
        legacy = base_legacy_row(estat="Adjudicado", estat_raw="RES", data_pub="2026-06-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Adjudicado")
        self.assertEqual(result[0]["estat_raw"], "RES")

    def test_later_ck_status_wins_when_only_ck_ranked(self):
        ck = base_ck_row(notice_type="AWARD", estat="Adjudicado", estat_raw="ADJ", data_pub="2026-06-01")
        legacy = base_legacy_row(estat="Vigente", estat_raw="EV", data_pub="2026-01-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Adjudicado")
        self.assertEqual(result[0]["estat_raw"], "ADJ")

    def test_equal_date_compatible_status_passes(self):
        # R2 fixture correction: as originally written this test only
        # overrode data_pub on the CK row, leaving base_ck_row()'s default
        # last_notice_date="2026-01-10" in place. effective_notice_date()
        # prefers last_notice_date over data_pub (handoff Sec10), so CK's
        # effective date was actually "2026-01-10" -- genuinely later than
        # LEGACY's "2026-01-01" -- meaning this test passed via the
        # exactly-one-valid-rank "later date wins" branch, not the
        # dates-equal/statuses-compatible branch its name claims (R1/R2
        # finding). last_notice_date must be overridden too so the effective
        # dates genuinely tie.
        ck = base_ck_row(
            notice_type="PUB", estat="Vigente", estat_raw="PUB",
            data_pub="2026-01-01", last_notice_date="2026-01-01",
        )
        legacy = base_legacy_row(estat="Vigente", estat_raw="EV", data_pub="2026-01-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Vigente")
        self.assertEqual(result[0]["estat_raw"], "PUB")

    def test_equal_date_conflicting_status_fails_closed(self):
        # R1 fixture correction: see test_both_valid_rank_tie_and_date_tie_
        # and_differing_status_fails_closed above -- same root cause. CK's
        # default last_notice_date ("2026-01-10") outranked the overridden
        # data_pub, so the rows were never actually date-tied.
        ck = base_ck_row(
            notice_type="PUB", estat="Vigente", estat_raw="PUB",
            data_pub="2026-01-01", last_notice_date="2026-01-01",
        )
        legacy = base_legacy_row(estat="Adjudicado", estat_raw="ADJ", data_pub="2026-01-01")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "status_conflict")

    def test_neither_ranked_equal_status_passes(self):
        # R2 fixture correction: as originally written this test left
        # base_ck_row()'s default last_notice_date="2026-01-10" in place
        # while only overriding data_pub, so CK's effective date was
        # genuinely later than LEGACY's "2026-01-01" -- this test passed via
        # the neither-ranked "later date wins" branch, not the
        # dates-equal/statuses-equal branch its name claims (R1/R2 finding).
        # last_notice_date must be overridden too so the effective dates
        # genuinely tie.
        ck = base_ck_row(
            notice_type="UNKNOWN", estat="Desierta", estat_raw="ANUL",
            data_pub="2026-01-01", last_notice_date="2026-01-01",
        )
        legacy = base_legacy_row(estat="Desierta", estat_raw="ANUL", data_pub="2026-01-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Desierta")

    def test_unknown_notice_type_is_not_valid_rank(self):
        self.assertFalse(ctm._valid_rank({"notice_type": "UNKNOWN"}))
        self.assertFalse(ctm._valid_rank({}))
        self.assertTrue(ctm._valid_rank({"notice_type": "PUB"}))

    def test_estat_raw_follows_status_row_even_when_estat_text_unchanged(self):
        # Mirrors the real .../19100601 R2 finding: estat text identical on
        # both rows, but the authoritative ROW flips by date, so estat_raw
        # must flip with it rather than staying CK-preferred.
        ck = base_ck_row(notice_type="PUB", estat="Vigente", estat_raw="PUB", data_pub="2026-01-01")
        legacy = base_legacy_row(estat="Vigente", estat_raw="EV", data_pub="2026-06-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Vigente")
        self.assertEqual(result[0]["estat_raw"], "EV")

    def test_both_valid_rank_tie_date_tie_equal_status_passes(self):
        # R2 new direct coverage: isolates STATUS_AUTHORITY_V1 rule A's
        # rank-tie + date-tie + statuses-equal sub-branch
        # (`if statuses_equal: return ck_row`), previously only confirmed by
        # source inspection (R1 CONTRACT RECHECK), never directly executed
        # by a dedicated fixture.
        ck = base_ck_row(
            notice_type="PUB", estat="Vigente", estat_raw="CK-PUB",
            data_pub="2026-01-01", last_notice_date="2026-01-01",
        )
        legacy = base_legacy_row(
            notice_type="PUB", estat="Vigente", estat_raw="LEGACY-PUB",
            data_pub="2026-01-01",
        )
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["estat"], "Vigente")
        self.assertEqual(result[0]["estat_raw"], "CK-PUB")

    def test_neither_ranked_equal_date_conflicting_status_fails_closed(self):
        # R2 new direct coverage: isolates STATUS_AUTHORITY_V1 rule C's
        # date-tie + statuses-differ fail-closed sub-branch, previously only
        # confirmed by source inspection (R1 CONTRACT RECHECK), never
        # directly executed by a dedicated fixture.
        ck = base_ck_row(
            notice_type="UNKNOWN", estat="Vigente", estat_raw="EV",
            data_pub="2026-01-01", last_notice_date="2026-01-01",
        )
        legacy = base_legacy_row(estat="Adjudicado", estat_raw="ADJ", data_pub="2026-01-01")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "status_conflict")


# --------------------------------------------------------------------------- #
# E. RELLEVANCIA (list items 22-23)
# --------------------------------------------------------------------------- #

class ERellevanciaTests(unittest.TestCase):

    def test_latest_date_wins(self):
        ck = base_ck_row(rellevancia=80, data_pub="2026-01-01", last_notice_date="2026-01-01")
        legacy = base_legacy_row(rellevancia=40, data_pub="2026-06-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["rellevancia"], 40)

    def test_ambiguous_conflict_fails_closed(self):
        ck = base_ck_row(rellevancia=80, data_pub="2026-01-01", last_notice_date="2026-01-01")
        legacy = base_legacy_row(rellevancia=40, data_pub="2026-01-01")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "scalar_conflict")


# --------------------------------------------------------------------------- #
# F. ADJUDICATARI (list items 24-27)
# --------------------------------------------------------------------------- #

class FAdjudicatariTests(unittest.TestCase):

    def test_sentinel_normalized_to_blank(self):
        ck = base_ck_row(adjudicatari=ctm.ADJUDICATARI_SENTINEL)
        legacy = base_legacy_row(adjudicatari="")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["adjudicatari"], "")

    def test_one_sided_nonblank_kept(self):
        ck = base_ck_row(adjudicatari="Real Company SL")
        legacy = base_legacy_row(adjudicatari="")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["adjudicatari"], "Real Company SL")

    def test_punctuation_variant_with_award_corroboration_resolves(self):
        ck = base_ck_row(
            adjudicatari="Mintta Software SL",
            award_results=[{
                "notice_id": "N1", "winning_party_name": "Mintta Software SL",
                "winning_party_nif": "", "award_amount_tax_excl": 100,
                "contract_id": "", "lot_id": "",
            }],
        )
        legacy = base_legacy_row(adjudicatari="MINTTA SOFTWARE. S.L.")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["adjudicatari"], "Mintta Software SL")

    def test_real_conflict_without_corroboration_fails_closed(self):
        ck = base_ck_row(adjudicatari="Company A SL")
        legacy = base_legacy_row(adjudicatari="Company B SL")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "adjudicatari_conflict")


# --------------------------------------------------------------------------- #
# G. multi-winner award preservation (list item 28)
# --------------------------------------------------------------------------- #

class GMultiWinnerTests(unittest.TestCase):

    def test_multiple_distinct_winners_all_preserved(self):
        ck = base_ck_row(
            adjudicatari="Winner One",
            award_results=[
                {"notice_id": "N1", "winning_party_name": "Winner One", "winning_party_nif": "",
                 "award_amount_tax_excl": 100, "contract_id": "", "lot_id": "L1"},
                {"notice_id": "N1", "winning_party_name": "Winner Two", "winning_party_nif": "",
                 "award_amount_tax_excl": 200, "contract_id": "", "lot_id": "L2"},
            ],
        )
        legacy = base_legacy_row(adjudicatari="")
        result = ctm.merge_canonical_tenders([ck, legacy])
        winners = {a["winning_party_name"] for a in result[0]["award_results"]}
        self.assertEqual(winners, {"Winner One", "Winner Two"})
        self.assertEqual(result[0]["adjudicatari"], "Winner One")


# --------------------------------------------------------------------------- #
# H. zero-conflict equality invariants (list items 29-31)
# --------------------------------------------------------------------------- #

class HEqualityInvariantTests(unittest.TestCase):

    def test_ccaa_equal_preserved(self):
        ck = base_ck_row(ccaa="CT")
        legacy = base_legacy_row(ccaa="CT")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["ccaa"], "CT")

    def test_lloc_one_blank_preserved(self):
        ck = base_ck_row(lloc="")
        legacy = base_legacy_row(lloc="Catalunya")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["lloc"], "Catalunya")

    def test_titol_differing_nonblank_fails_closed(self):
        ck = base_ck_row(titol="Title A")
        legacy = base_legacy_row(titol="Title B")
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "scalar_conflict")


# --------------------------------------------------------------------------- #
# I. other canonical scalars (list items 32-34, plus pressupost)
# --------------------------------------------------------------------------- #

class IOtherScalarTests(unittest.TestCase):

    def test_data_limit_preserved_non_empty_prefer_ck(self):
        ck = base_ck_row(data_limit="")
        legacy = base_legacy_row(data_limit="2026-03-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["data_limit"], "2026-03-01")

    def test_min_first_pub_date(self):
        ck = base_ck_row(first_pub_date="2026-03-01")
        legacy = base_legacy_row(first_pub_date="2026-01-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["first_pub_date"], "2026-01-01")

    def test_max_last_notice_date(self):
        ck = base_ck_row(last_notice_date="2026-01-01")
        legacy = base_legacy_row(last_notice_date="2026-03-01")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["last_notice_date"], "2026-03-01")

    def test_pressupost_conflict_fails_closed(self):
        ck = base_ck_row(pressupost=1000.0)
        legacy = base_legacy_row(pressupost=2000.0)
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "scalar_conflict")


# --------------------------------------------------------------------------- #
# J. cpv / disciplines / kw (list items 35-37)
# --------------------------------------------------------------------------- #

class JAtomicAndSetScalarTests(unittest.TestCase):

    def test_cpv_union_dedupe_sort(self):
        ck = base_ck_row(cpv="30192000, 10101010")
        legacy = base_legacy_row(cpv="10101010, 20202020")
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["cpv"], "10101010,20202020,30192000")

    def test_disciplines_atomic_not_unioned(self):
        ck = base_ck_row(disciplines=["branding"])
        legacy = base_legacy_row(disciplines=["editorial", "impressio"])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["disciplines"], ["branding"])

    def test_disciplines_falls_back_to_legacy_when_ck_empty(self):
        ck = base_ck_row(disciplines=[])
        legacy = base_legacy_row(disciplines=["editorial"])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["disciplines"], ["editorial"])

    def test_kw_atomic_not_unioned(self):
        ck = base_ck_row(kw=["alpha"])
        legacy = base_legacy_row(kw=["beta", "gamma"])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["kw"], ["alpha"])


# --------------------------------------------------------------------------- #
# K. LOSSLESS_SEQUENCE fields (list items 38-42)
# --------------------------------------------------------------------------- #

class KSequenceTests(unittest.TestCase):

    def test_historial_union_and_order(self):
        ck = base_ck_row(historial=[
            {"data": "2026-02-01", "estat": "Adjudicado", "nota": "Adjudicado a X"},
        ])
        legacy = base_legacy_row(historial=[
            {"data": "2026-01-01", "estat": "Vigente", "nota": "Publicación"},
        ])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual([h["data"] for h in result[0]["historial"]], ["2026-01-01", "2026-02-01"])

    def test_historial_dedupe_exact_duplicate(self):
        entry = {"data": "2026-01-01", "estat": "Vigente", "nota": "Publicación"}
        ck = base_ck_row(historial=[entry])
        legacy = base_legacy_row(historial=[dict(entry)])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(len(result[0]["historial"]), 1)

    def test_notice_history_union_and_order(self):
        ck = base_ck_row(notice_history=[
            {"notice_id": "N2", "notice_type": "AWARD", "issue_date": "2026-02-01"},
            {"notice_id": "N1", "notice_type": "PUB", "issue_date": "2026-01-01"},
        ])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        issue_dates = [n["issue_date"] for n in result[0]["notice_history"]]
        self.assertEqual(issue_dates, sorted(issue_dates))

    def test_award_results_union_and_order(self):
        ck = base_ck_row(award_results=[
            {"notice_id": "N1", "winning_party_name": "B Co", "winning_party_nif": "",
             "award_amount_tax_excl": 50, "contract_id": "", "lot_id": "", "award_date": "2026-02-01"},
            {"notice_id": "N1", "winning_party_name": "A Co", "winning_party_nif": "",
             "award_amount_tax_excl": 50, "contract_id": "", "lot_id": "", "award_date": "2026-01-01"},
        ])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        dates = [a["award_date"] for a in result[0]["award_results"]]
        self.assertEqual(dates, sorted(dates))

    def test_related_contract_ids_union_and_sort(self):
        ck = base_ck_row(related_contract_ids=["C2", "C1"])
        legacy = base_legacy_row(related_contract_ids=["C3", "C1"])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["related_contract_ids"], ["C1", "C2", "C3"])

    def test_sources_seen_union_and_sort(self):
        ck = base_ck_row(sources_seen=["S2"])
        legacy = base_legacy_row(sources_seen=["S1"])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["sources_seen"], ["S1", "S2"])

    def test_sequence_absent_on_both_not_invented(self):
        ck = base_ck_row()
        ck.pop("related_contract_ids", None)
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertNotIn("related_contract_ids", result[0])

    def test_invalid_sequence_shape_fails_closed(self):
        ck = base_ck_row(historial="not-a-list")
        legacy = base_legacy_row()
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "invalid_sequence_shape")


# --------------------------------------------------------------------------- #
# L. duplicate_relations (list item 43)
# --------------------------------------------------------------------------- #

class LDuplicateRelationsTests(unittest.TestCase):

    def test_duplicate_relations_populated_fails_closed(self):
        ck = base_ck_row(duplicate_relations=[{"related_id": "X"}])
        legacy = base_legacy_row()
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "duplicate_relations_unsupported")

    def test_duplicate_relations_absent_or_empty_passes(self):
        ck = base_ck_row(duplicate_relations=[])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(len(result), 1)


# --------------------------------------------------------------------------- #
# M. documents (list items 44-47)
# --------------------------------------------------------------------------- #

class MDocumentTests(unittest.TestCase):

    def test_document_canonical_url_dedupe(self):
        doc_a = {"title": "Doc", "url": "https://Example.org:443/path",
                 "document_type": "generic_doc", "notice_id": "N1"}
        doc_b = {"title": "Doc", "url": "https://example.org/path",
                 "document_type": "generic_doc", "notice_id": "N1"}
        ck = base_ck_row(documents=[doc_a])
        legacy = base_legacy_row(documents=[doc_b])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(len(result[0]["documents"]), 1)

    def test_document_deterministic_order(self):
        doc1 = {"title": "B Doc", "url": "https://example.org/b",
                "document_type": "generic_doc", "notice_id": "N1"}
        doc2 = {"title": "A Doc", "url": "https://example.org/a",
                "document_type": "generic_doc", "notice_id": "N1"}
        ck = base_ck_row(documents=[doc1, doc2])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        titles = [d["title"] for d in result[0]["documents"]]
        self.assertEqual(titles, sorted(titles))

    def test_document_richer_object_preserved(self):
        sparse = {"title": "Doc", "url": "https://example.org/x",
                  "document_type": "generic_doc", "notice_id": "N1"}
        richer = dict(sparse, mime_hint="application/pdf", http_status=200)
        ck = base_ck_row(documents=[sparse])
        legacy = base_legacy_row(documents=[richer])
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(len(result[0]["documents"]), 1)
        self.assertEqual(result[0]["documents"][0]["mime_hint"], "application/pdf")

    def test_incompatible_duplicate_document_fails_closed(self):
        variant_a = {"title": "Doc", "url": "https://example.org/x", "document_type": "generic_doc",
                     "notice_id": "N1", "mime_hint": "application/pdf"}
        variant_b = {"title": "Doc", "url": "https://example.org/x", "document_type": "generic_doc",
                     "notice_id": "N1", "mime_hint": "text/html"}
        ck = base_ck_row(documents=[variant_a])
        legacy = base_legacy_row(documents=[variant_b])
        with self.assertRaises(ctm.CanonicalTenderMergeError) as cm:
            ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(cm.exception.code, "document_identity_conflict")

    def test_urlless_same_notice_distinct_variants_preserved_exact_duplicates_deduped(self):
        # D292-R3-DOCIDENTITY-FALLBACK-V1 (Prompt 292 R3): mirrors the
        # real-data shape the R3 forensic census found at tender suffix
        # 18521453 -- five URL-less document entries sharing one notice_id,
        # three distinct published_at variants, two of the five exact
        # duplicates. notice_id alone is not a sufficient document-level
        # identity anchor for URL-less entries in current data; identity
        # must fall back to exact full-object content.
        def urlless_doc(published_at):
            return {
                "title": "", "url": "", "document_type": "",
                "notice_id": "N1",
                "source_section": "additionalpublicationdocumentreference",
                "published_at": published_at,
            }

        ck = base_ck_row(documents=[
            urlless_doc("2025-12-03"),
            urlless_doc("2026-05-08"),
            urlless_doc("2026-05-08"),
            urlless_doc("2026-05-22"),
            urlless_doc("2026-05-22"),
        ])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        docs = result[0]["documents"]
        self.assertEqual(len(docs), 3)
        self.assertEqual(
            sorted(d["published_at"] for d in docs),
            ["2025-12-03", "2026-05-08", "2026-05-22"],
        )

    def test_urlless_same_notice_notice_type_variants_preserved(self):
        # D292-R3-DOCIDENTITY-FALLBACK-V1: two URL-less entries sharing
        # notice_id and published_at but differing only by notice_type must
        # remain distinct preserved entries, not collapse into one.
        ck = base_ck_row(documents=[
            {"title": "", "url": "", "document_type": "", "notice_id": "N1",
             "published_at": "2026-01-01", "notice_type": "EV"},
            {"title": "", "url": "", "document_type": "", "notice_id": "N1",
             "published_at": "2026-01-01", "notice_type": "AWARD"},
        ])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        docs = result[0]["documents"]
        self.assertEqual(len(docs), 2)
        self.assertEqual({d["notice_type"] for d in docs}, {"EV", "AWARD"})

    def test_urlbearing_same_resource_distinct_notice_type_observations_preserved(self):
        # D292-R4-DOCUMENT-OBSERVATION-IDENTITY-V1 (Prompt 292 R4): mirrors
        # the real-data shape the R4 strong-URL forensic census found at
        # tender suffix 19407571 -- same title/url/document_type/notice_id/
        # source_section/format_hint/mime_hint/provenance/published_at,
        # differing ONLY in notice_type (EV vs AWARD). The pre-R4
        # RESOURCE_KEY alone would collapse these into one document and
        # silently discard one notice_type; OBSERVATION_KEY (RESOURCE_KEY +
        # exact notice_type) must instead preserve both as separate
        # documents[] entries with no document_identity_conflict.
        def urlbearing_doc(notice_type):
            return {
                "title": "Doc", "url": "https://example.org/doc",
                "document_type": "generic_doc", "notice_id": "N1",
                "source_section": "additionalpublicationdocumentreference",
                "format_hint": "pdf", "mime_hint": "application/pdf",
                "provenance": "CK", "published_at": "2026-01-01",
                "notice_type": notice_type,
            }

        ck = base_ck_row(documents=[urlbearing_doc("EV"), urlbearing_doc("AWARD")])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        docs = result[0]["documents"]
        self.assertEqual(len(docs), 2)
        self.assertEqual({d["notice_type"] for d in docs}, {"EV", "AWARD"})
        self.assertEqual(
            [d["url"] for d in docs],
            ["https://example.org/doc", "https://example.org/doc"],
        )

    def test_urlbearing_same_resource_notice_observation_exact_duplicates_deduped(self):
        # D292-R4-DOCUMENT-OBSERVATION-IDENTITY-V1: within one notice_type
        # observation, exact-duplicate reduction remains active (unchanged
        # by R4); across the two distinct notice_type observations sharing
        # one resource, both survive as separate entries. Deterministic
        # ordering (R4 Sec3.D) falls out of _doc_identity_key's tuple sort:
        # with every other field tied, notice_type alone orders the pair
        # ("AWARD" < "EV" lexically), never array position/encounter order.
        def urlbearing_doc(notice_type):
            return {
                "title": "Doc", "url": "https://example.org/doc",
                "document_type": "generic_doc", "notice_id": "N1",
                "source_section": "additionalpublicationdocumentreference",
                "format_hint": "pdf", "mime_hint": "application/pdf",
                "provenance": "CK", "published_at": "2026-01-01",
                "notice_type": notice_type,
            }

        ck = base_ck_row(documents=[
            urlbearing_doc("EV"), urlbearing_doc("EV"),
            urlbearing_doc("AWARD"), urlbearing_doc("AWARD"),
        ])
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        docs = result[0]["documents"]
        self.assertEqual(len(docs), 2)
        self.assertEqual({d["notice_type"] for d in docs}, {"EV", "AWARD"})
        self.assertEqual([d["notice_type"] for d in docs], ["AWARD", "EV"])


# --------------------------------------------------------------------------- #
# N. source non-mutation (list items 48-49)
# --------------------------------------------------------------------------- #

class NNonMutationTests(unittest.TestCase):

    def test_nested_structures_not_mutated(self):
        ck = base_ck_row(historial=[{"data": "2026-01-10", "estat": "Vigente", "nota": "Publicación"}])
        legacy = base_legacy_row()
        frozen_ck = copy.deepcopy(ck)
        frozen_legacy = copy.deepcopy(legacy)
        ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(ck, frozen_ck)
        self.assertEqual(legacy, frozen_legacy)

    def test_output_mutation_cannot_mutate_input(self):
        ck = base_ck_row(documents=[
            {"title": "Doc", "url": "https://example.org/d", "document_type": "generic_doc", "notice_id": "N1"}
        ])
        legacy = base_legacy_row()
        frozen_ck = copy.deepcopy(ck)
        result = ctm.merge_canonical_tenders([ck, legacy])
        result[0]["documents"][0]["title"] = "MUTATED"
        result[0]["disciplines"].append("hacked")
        self.assertEqual(ck, frozen_ck)


# --------------------------------------------------------------------------- #
# O. order independence / idempotence (list items 50-51)
# --------------------------------------------------------------------------- #

class OOrderIndependenceTests(unittest.TestCase):

    def test_pair_order_independence(self):
        ck = base_ck_row()
        legacy = base_legacy_row()
        result_a = ctm.merge_canonical_tenders([ck, legacy])
        result_b = ctm.merge_canonical_tenders([legacy, ck])
        self.assertEqual(result_a, result_b)

    def test_full_dataset_idempotence(self):
        ck = base_ck_row(historial=[
            {"data": "2026-01-10", "estat": "Vigente", "nota": "Publicación"},
            {"data": "2026-02-01", "estat": "Adjudicado", "nota": "Adjudicado a X"},
        ])
        legacy = base_legacy_row()
        once = ctm.merge_canonical_tenders([ck, legacy])
        twice = ctm.merge_canonical_tenders(once)
        self.assertEqual(once, twice)


# --------------------------------------------------------------------------- #
# P. identity boundary / internal bookkeeping (list items 52-53)
# --------------------------------------------------------------------------- #

class PBookkeepingTests(unittest.TestCase):

    def test_no_public_id_minted(self):
        ck = base_ck_row()
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertNotIn("public_id", result[0])

    def test_internal_bookkeeping_retained_from_ck_base(self):
        ck = base_ck_row(internal_bookkeeping_marker="keep-me")
        legacy = base_legacy_row()
        result = ctm.merge_canonical_tenders([ck, legacy])
        self.assertEqual(result[0]["internal_bookkeeping_marker"], "keep-me")


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    n = result.testsRun
    passed = result.wasSuccessful()
    verdict = "PASS" if passed else "FAIL"
    print(f"CANONICAL_TENDER_MERGE TESTS: {verdict} ({n} cases)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
