#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/test_link_check_resolver.py  (ADG-OPS / WRKOPS t_20260914_adgops306 / v0.7.4ad)

Offline/synthetic regression suite for tools/link_check_resolver.py (IB-5
Phase A). Standard-library only. No real network, no real DNS -- every
"transport" and "DNS resolution" call in this suite is a monkeypatched stub
or an injected fake resolver function; the module's own `_open_once`,
`_probe_hop`, and `resolve_url()`'s `resolver` parameter are all designed to
be swapped out exactly for this purpose. Mirrors the repo's existing test
convention (lettered/grouped TestCase classes, a custom main() summary
line, run directly with `python tools/test_link_check_resolver.py [-v]`).

Run:
  python tools/test_link_check_resolver.py [-v]

Final line:
  LINK_CHECK_RESOLVER TESTS: PASS (N cases)
  LINK_CHECK_RESOLVER TESTS: FAIL (N cases)
"""

import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.link_check_resolver as lcr  # noqa: E402


def make_resolver(unsafe_hosts=()):
    """A `socket.getaddrinfo`-shaped fake resolver: any host in
    `unsafe_hosts` resolves to a loopback address; every other host
    resolves to a real-world-shaped public address. Never touches real
    DNS."""
    unsafe = set(unsafe_hosts)

    def resolver(host, port, *_a, **_kw):
        ip = "127.0.0.1" if host in unsafe else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]

    return resolver


def make_open_once_stub(responses):
    """responses: {(url, method): (meta_dict_or_None, body_bytes_or_None,
    err_dict_or_None)} -- matches _open_once()'s return contract exactly."""

    def stub(url, method, timeout, max_range_bytes):
        return responses[(url, method)]

    return stub


# --------------------------------------------------------------------------- #
# A. SSRF / URL safety (handoff §8)
# --------------------------------------------------------------------------- #

class AUrlSafetyTests(unittest.TestCase):

    def test_http_https_allowed(self):
        lcr.check_url_safety("http://safe.example/x", resolver=make_resolver())
        lcr.check_url_safety("https://safe.example/x", resolver=make_resolver())

    def test_unsupported_scheme_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("ftp://safe.example/x", resolver=make_resolver())
        self.assertEqual(cm.exception.reason, "unsupported_scheme")

    def test_malformed_url_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError):
            lcr.check_url_safety("not a url at all", resolver=make_resolver())
        with self.assertRaises(lcr.UrlSafetyError):
            lcr.check_url_safety("", resolver=make_resolver())

    def test_embedded_userinfo_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("https://user:pass@safe.example/x", resolver=make_resolver())
        self.assertEqual(cm.exception.reason, "embedded_userinfo")

    def test_localhost_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("http://localhost/x", resolver=make_resolver())
        self.assertEqual(cm.exception.reason, "localhost_hostname")

    def test_empty_hostname_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("http:///x", resolver=make_resolver())
        self.assertEqual(cm.exception.reason, "empty_hostname")

    def test_loopback_literal_ip_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("http://127.0.0.1/x", resolver=make_resolver())
        self.assertEqual(cm.exception.reason, "unsafe_literal_ip")

    def test_ipv6_loopback_literal_rejected(self):
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("http://[::1]/x", resolver=make_resolver())
        self.assertEqual(cm.exception.reason, "unsafe_literal_ip")

    def test_private_link_local_reserved_literal_rejected(self):
        for host in ("10.0.0.5", "172.16.0.5", "192.168.1.1", "169.254.1.1", "240.0.0.1"):
            with self.subTest(host=host):
                with self.assertRaises(lcr.UrlSafetyError) as cm:
                    lcr.check_url_safety(f"http://{host}/x", resolver=make_resolver())
                self.assertEqual(cm.exception.reason, "unsafe_literal_ip")

    def test_safe_hostname_allowed_via_mocked_resolver(self):
        lcr.check_url_safety("https://safe.example/x", resolver=make_resolver())  # no raise

    def test_dns_resolved_unsafe_address_rejected(self):
        resolver = make_resolver(unsafe_hosts=["evil.example"])
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("https://evil.example/x", resolver=resolver)
        self.assertEqual(cm.exception.reason, "unsafe_resolved_address")

    def test_dns_resolution_failure_rejected(self):
        def failing_resolver(host, port, *_a, **_kw):
            raise OSError("no such host")
        with self.assertRaises(lcr.UrlSafetyError) as cm:
            lcr.check_url_safety("https://safe.example/x", resolver=failing_resolver)
        self.assertEqual(cm.exception.reason, "dns_resolution_failed")


# --------------------------------------------------------------------------- #
# B. HTTP outcome classification (handoff §9)
# --------------------------------------------------------------------------- #

class BClassificationTests(unittest.TestCase):

    def test_200_206_reachable(self):
        self.assertEqual(lcr._classify(200), "REACHABLE")
        self.assertEqual(lcr._classify(206), "REACHABLE")

    def test_404_410_confirmed_unavailable(self):
        self.assertEqual(lcr._classify(404), "CONFIRMED_UNAVAILABLE")
        self.assertEqual(lcr._classify(410), "CONFIRMED_UNAVAILABLE")

    def test_401_403_429_5xx_unknown_or_transient(self):
        for status in (401, 403, 429, 500, 503):
            with self.subTest(status=status):
                self.assertEqual(lcr._classify(status), "UNKNOWN_OR_TRANSIENT")


# --------------------------------------------------------------------------- #
# C. HEAD-first / bounded Range GET fallback (handoff §7)
# --------------------------------------------------------------------------- #

class CProbeHopTests(unittest.TestCase):

    def setUp(self):
        self._saved_open_once = lcr._open_once

    def tearDown(self):
        lcr._open_once = self._saved_open_once

    def test_head_reachable_no_fallback(self):
        url = "https://safe.example/doc.pdf"
        lcr._open_once = make_open_once_stub({
            (url, "HEAD"): ({"http_status": 200, "headers": {}, "final_url": url}, b"", None),
        })
        method, status, _headers, _final_url, err_type, _err_msg = lcr._probe_hop(
            url, 20.0, lcr.MAX_RANGE_BYTES)
        self.assertEqual(method, "HEAD")
        self.assertEqual(status, 200)
        self.assertIsNone(err_type)

    def test_head_transport_error_falls_back_to_range_get(self):
        url = "https://safe.example/doc.pdf"
        lcr._open_once = make_open_once_stub({
            (url, "HEAD"): (None, None, {"error_type": "URLError", "error_message": "boom"}),
            (url, "GET"): ({"http_status": 200, "headers": {}, "final_url": url}, b"%PDF-", None),
        })
        method, status, _headers, _final_url, err_type, _err_msg = lcr._probe_hop(
            url, 20.0, lcr.MAX_RANGE_BYTES)
        self.assertEqual(method, "RANGE_GET")
        self.assertEqual(status, 200)
        self.assertIsNone(err_type)

    def test_head_405_falls_back_to_range_get(self):
        url = "https://safe.example/doc.pdf"
        lcr._open_once = make_open_once_stub({
            (url, "HEAD"): ({"http_status": 405, "headers": {}, "final_url": url}, b"", None),
            (url, "GET"): ({"http_status": 200, "headers": {}, "final_url": url}, b"", None),
        })
        method, status, *_rest = lcr._probe_hop(url, 20.0, lcr.MAX_RANGE_BYTES)
        self.assertEqual(method, "RANGE_GET")
        self.assertEqual(status, 200)

    def test_both_head_and_get_transport_error_reports_error(self):
        url = "https://safe.example/doc.pdf"
        lcr._open_once = make_open_once_stub({
            (url, "HEAD"): (None, None, {"error_type": "TimeoutError", "error_message": "timed out"}),
            (url, "GET"): (None, None, {"error_type": "TimeoutError", "error_message": "timed out"}),
        })
        _method, status, _headers, _final_url, err_type, _err_msg = lcr._probe_hop(
            url, 20.0, lcr.MAX_RANGE_BYTES)
        self.assertIsNone(status)
        self.assertEqual(err_type, "TimeoutError")


# --------------------------------------------------------------------------- #
# D. resolve_url(): redirect safety + depth bound (handoff §8), transport
# failure classification (handoff §9)
# --------------------------------------------------------------------------- #

class DResolveUrlTests(unittest.TestCase):

    def setUp(self):
        self._saved_probe_hop = lcr._probe_hop

    def tearDown(self):
        lcr._probe_hop = self._saved_probe_hop

    def test_timeout_dns_tls_transport_is_unknown_or_transient(self):
        lcr._probe_hop = lambda url, timeout, max_range_bytes: (
            "ERROR", None, None, None, "TimeoutError", "timed out")
        method, _status, _final_url, classification, err_type, _err_msg = lcr.resolve_url(
            "https://safe.example/x", 20.0, resolver=make_resolver())
        self.assertEqual(method, "ERROR")
        self.assertEqual(classification, "UNKNOWN_OR_TRANSIENT")
        self.assertEqual(err_type, "TimeoutError")

    def test_safety_rejection_never_reaches_probe(self):
        calls = []

        def stub(url, timeout, max_range_bytes):
            calls.append(url)
            return "HEAD", 200, {}, url, None, None
        lcr._probe_hop = stub

        method, _status, _final_url, classification, err_type, _err_msg = lcr.resolve_url(
            "http://localhost/x", 20.0, resolver=make_resolver())
        self.assertEqual(method, "SKIPPED")
        self.assertEqual(classification, "UNKNOWN_OR_TRANSIENT")
        self.assertEqual(err_type, "UrlSafetyError")
        self.assertEqual(calls, [])

    def test_redirect_target_safety_checked_before_follow(self):
        def stub(url, timeout, max_range_bytes):
            if url == "https://safe.example/start":
                return "HEAD", 302, {"Location": "https://evil.example/target"}, url, None, None
            self.fail("must never probe an unsafe redirect target")
        lcr._probe_hop = stub

        resolver = make_resolver(unsafe_hosts=["evil.example"])
        method, status, final_url, classification, err_type, _err_msg = lcr.resolve_url(
            "https://safe.example/start", 20.0, resolver=resolver)
        # The unsafe target is rejected BEFORE any request is issued against
        # it, so the outcome is a SKIPPED safety rejection carrying no status
        # of its own -- not the 302 of the (safe) hop that merely pointed at
        # it. The stub's self.fail() above is what proves the unsafe hop was
        # never probed; these assertions pin the reported outcome.
        self.assertEqual(method, "SKIPPED")
        self.assertIsNone(status)
        self.assertEqual(final_url, "https://evil.example/target")
        self.assertEqual(classification, "UNKNOWN_OR_TRANSIENT")
        self.assertEqual(err_type, "UrlSafetyError")

    def test_redirect_depth_bounded(self):
        def stub(url, timeout, max_range_bytes):
            n = int(url.rsplit("/", 1)[-1])
            return "HEAD", 302, {"Location": f"https://safe.example/{n + 1}"}, url, None, None
        lcr._probe_hop = stub

        _method, status, _final_url, classification, err_type, _err_msg = lcr.resolve_url(
            "https://safe.example/0", 20.0, resolver=make_resolver(), max_redirects=3)
        self.assertEqual(status, 302)
        self.assertEqual(classification, "UNKNOWN_OR_TRANSIENT")
        self.assertEqual(err_type, "RedirectDepthExceeded")

    def test_successful_redirect_chain_resolves_reachable(self):
        def stub(url, timeout, max_range_bytes):
            if url == "https://safe.example/a":
                return "HEAD", 302, {"Location": "https://safe.example/b"}, url, None, None
            if url == "https://safe.example/b":
                return "HEAD", 200, {}, url, None, None
            self.fail(f"unexpected url {url!r}")
        lcr._probe_hop = stub

        _method, status, _final_url, classification, err_type, _err_msg = lcr.resolve_url(
            "https://safe.example/a", 20.0, resolver=make_resolver())
        self.assertEqual(status, 200)
        self.assertEqual(classification, "REACHABLE")
        self.assertIsNone(err_type)

    def test_redirect_missing_location_is_unknown_or_transient(self):
        lcr._probe_hop = lambda url, timeout, max_range_bytes: ("HEAD", 302, {}, url, None, None)
        _method, status, _final_url, classification, err_type, _err_msg = lcr.resolve_url(
            "https://safe.example/x", 20.0, resolver=make_resolver())
        self.assertEqual(status, 302)
        self.assertEqual(classification, "UNKNOWN_OR_TRANSIENT")
        self.assertEqual(err_type, "RedirectMissingLocation")


# --------------------------------------------------------------------------- #
# E. adgops.link_checks/1 sidecar contract (handoff §6): strict, fail-closed
# --------------------------------------------------------------------------- #

class ESidecarContractTests(unittest.TestCase):

    def _valid_sidecar(self):
        return {
            "schema": lcr.SCHEMA,
            "run_id": "run-1",
            "started_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:00:05Z",
            "resolver_policy": {"limit": 50},
            "counts": {"candidates_attempted": 1},
            "observations": [{
                "public_id": "pid-1",
                "record_id": "rec-1",
                "document_key": ["url", "Doc", "https://example.org/d", "generic_doc", "N1", "PUB"],
                "requested_url": "https://example.org/d",
                "observed_at": "2026-01-01T00:00:03Z",
                "resolver_method": "HEAD",
                "http_status": 200,
                "classification": "REACHABLE",
            }],
        }

    def test_valid_sidecar_passes(self):
        lcr.validate_link_check_sidecar(self._valid_sidecar())  # must not raise

    def test_unknown_top_level_key_rejected(self):
        sc = self._valid_sidecar()
        sc["mystery"] = 1
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "unknown_top_level_keys")

    def test_missing_top_level_key_rejected(self):
        sc = self._valid_sidecar()
        del sc["counts"]
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "missing_top_level_keys")

    def test_unknown_observation_key_rejected(self):
        sc = self._valid_sidecar()
        sc["observations"][0]["mystery"] = 1
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "observation_unknown_keys")

    def test_missing_observation_key_rejected(self):
        sc = self._valid_sidecar()
        del sc["observations"][0]["http_status"]
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "observation_missing_keys")

    def test_forbidden_fields_rejected(self):
        for field in ("headers", "cookies", "authorization", "response_body", "token"):
            with self.subTest(field=field):
                sc = self._valid_sidecar()
                sc["observations"][0][field] = "x"
                with self.assertRaises(lcr.LinkCheckContractError):
                    lcr.validate_link_check_sidecar(sc)

    def test_invalid_classification_rejected(self):
        sc = self._valid_sidecar()
        sc["observations"][0]["classification"] = "BOGUS"
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "observation_invalid_classification")

    def test_invalid_resolver_method_rejected(self):
        sc = self._valid_sidecar()
        sc["observations"][0]["resolver_method"] = "BOGUS"
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "observation_invalid_resolver_method")

    def test_malformed_observed_at_rejected(self):
        sc = self._valid_sidecar()
        sc["observations"][0]["observed_at"] = "not-a-timestamp"
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "observation_invalid_observed_at")

    def test_document_key_empty_shape_rejected(self):
        sc = self._valid_sidecar()
        sc["observations"][0]["document_key"] = []
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.validate_link_check_sidecar(sc)
        self.assertEqual(cm.exception.reason, "observation_invalid_document_key")

    def test_load_missing_file_fails_closed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        missing = Path(tmp.name) / "does_not_exist.json"
        with self.assertRaises(lcr.LinkCheckContractError):
            lcr.load_link_check_sidecar(str(missing))

    def test_load_valid_file_round_trips(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "sidecar.json"
        path.write_text(json.dumps(self._valid_sidecar()), encoding="utf-8")
        loaded = lcr.load_link_check_sidecar(str(path))
        self.assertEqual(loaded["schema"], lcr.SCHEMA)


# --------------------------------------------------------------------------- #
# F0. Input-envelope normalization (Prompt 309 §4.A): the resolver's --input
# must accept both the pre-existing bare-list form and the canonical
# persisted artifact envelope. The envelope fixture below mirrors the exact
# shape `tools/scheduled_fetch_merge.py`'s --run-live writer persists to
# data/licitaciones.json: `{"meta": public_meta, "data": public_records}`
# (see tools/scheduled_fetch_merge.py, write_json(PRODUCTION_PATH, {"meta":
# public_meta, "data": public_records})). This is a test of the resolver's
# input contract, not a modification of that writer.
# --------------------------------------------------------------------------- #

class F0InputEnvelopeTests(unittest.TestCase):

    def _record(self, pid, rid, urls):
        return {
            "public_id": pid, "id": rid,
            "documents": [{"title": "D", "url": u, "document_type": "generic_doc",
                           "notice_id": "N", "notice_type": "PUB"} for u in urls],
        }

    def test_bare_list_accepted(self):
        recs = [self._record("pid-1", "rec-1", ["https://example.org/a"])]
        self.assertEqual(lcr.normalize_link_check_input(recs), recs)

    def test_canonical_envelope_matches_writer_shape_and_yields_same_selection(self):
        recs = [self._record("pid-1", "rec-1", ["https://example.org/a"])]
        envelope = {
            "meta": {"schema": "adgops.public.licitaciones/1", "generation_id": "g1"},
            "data": recs,
        }
        normalized = lcr.normalize_link_check_input(envelope)
        self.assertEqual(normalized, recs)
        self.assertEqual(
            lcr.select_candidates(normalized, 50),
            lcr.select_candidates(recs, 50),
        )
        # normalize_link_check_input() must not mutate its input.
        self.assertIn("data", envelope)
        self.assertEqual(envelope["data"], recs)

    def test_envelope_missing_data_rejected(self):
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.normalize_link_check_input({"meta": {}})
        self.assertEqual(cm.exception.reason, "unrecognized_input_envelope")

    def test_envelope_non_list_data_rejected(self):
        with self.assertRaises(lcr.LinkCheckContractError) as cm:
            lcr.normalize_link_check_input({"meta": {}, "data": {"not": "a list"}})
        self.assertEqual(cm.exception.reason, "unrecognized_input_envelope")

    def test_arbitrary_top_level_shapes_rejected(self):
        for bad in ("a string", 42, None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(lcr.LinkCheckContractError) as cm:
                    lcr.normalize_link_check_input(bad)
                self.assertEqual(cm.exception.reason, "unrecognized_input_envelope")


# --------------------------------------------------------------------------- #
# F. Deterministic candidate selection (handoff §7)
# --------------------------------------------------------------------------- #

class FSelectCandidatesTests(unittest.TestCase):

    def _record(self, pid, rid, urls):
        return {
            "public_id": pid, "id": rid,
            "documents": [{"title": "D", "url": u, "document_type": "generic_doc",
                           "notice_id": "N", "notice_type": "PUB"} for u in urls],
        }

    def test_default_limit_is_50(self):
        args = lcr.build_arg_parser().parse_args(["--input", "x", "--output", "y"])
        self.assertEqual(args.limit, 50)

    def test_skips_non_http_schemes_and_missing_url(self):
        rec = self._record("pid-1", "rec-1", ["ftp://example.org/x", ""])
        rec["documents"].append({"title": "D2"})  # no url key at all
        self.assertEqual(lcr.select_candidates([rec], 50), [])

    def test_skips_records_without_public_id_or_id(self):
        recs = [
            {"id": "rec-1", "documents": [{"url": "https://example.org/a"}]},          # no public_id
            {"public_id": "pid-1", "documents": [{"url": "https://example.org/a"}]},   # no id
        ]
        self.assertEqual(lcr.select_candidates(recs, 50), [])

    def test_deterministic_order_independent_of_input_order(self):
        rec_a = self._record("pid-b", "rec-b", ["https://example.org/z"])
        rec_b = self._record("pid-a", "rec-a", ["https://example.org/a"])
        order1 = lcr.select_candidates([rec_a, rec_b], 50)
        order2 = lcr.select_candidates([rec_b, rec_a], 50)
        self.assertEqual([c[0] for c in order1], [c[0] for c in order2])
        self.assertEqual([c[0] for c in order1], ["pid-a", "pid-b"])

    def test_limit_truncates(self):
        rec = self._record("pid-1", "rec-1", [f"https://example.org/{i}" for i in range(5)])
        self.assertEqual(len(lcr.select_candidates([rec], 2)), 2)

    def test_top_level_non_list_raises(self):
        with self.assertRaises(lcr.LinkCheckContractError):
            lcr.select_candidates("not-a-list", 50)


# --------------------------------------------------------------------------- #
# G. main()/CLI: dry-run, circuit breakers, sidecar shape (handoff §7/§12.A)
# --------------------------------------------------------------------------- #

class GMainCliTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._saved_resolve_url = lcr.resolve_url

    def tearDown(self):
        lcr.resolve_url = self._saved_resolve_url
        self._tmp.cleanup()

    def _write_input(self, n=3):
        records = [{
            "public_id": f"pid-{i}", "id": f"rec-{i}",
            "documents": [{"title": "D", "url": f"https://example.org/doc-{i}.pdf",
                           "document_type": "generic_doc", "notice_id": f"N{i}",
                           "notice_type": "PUB"}],
        } for i in range(n)]
        path = self.tmp / "input.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        return path

    def test_dry_run_makes_no_network_call(self):
        calls = []

        def fake_resolve(url, timeout, resolver=None, max_range_bytes=None, max_redirects=None):
            calls.append(url)
            return "HEAD", 200, url, "REACHABLE", None, None
        lcr.resolve_url = fake_resolve

        input_path = self._write_input(3)
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(input_path), "--output", str(output_path), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])  # resolve_url() itself was never invoked

        sidecar = json.loads(output_path.read_text(encoding="utf-8"))
        for obs in sidecar["observations"]:
            self.assertEqual(obs["resolver_method"], "SKIPPED")
        lcr.validate_link_check_sidecar(sidecar)  # self-consistent output

    def test_circuit_breaker_stop_error_rate_aborts(self):
        def always_unreachable(url, timeout, resolver=None, max_range_bytes=None, max_redirects=None):
            return "HEAD", 500, url, "UNKNOWN_OR_TRANSIENT", None, None
        lcr.resolve_url = always_unreachable

        input_path = self._write_input(5)
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(input_path), "--output", str(output_path),
                          "--stop-error-rate", "0.0", "--sleep", "0"])
        self.assertEqual(code, 2)
        sidecar = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertLess(len(sidecar["observations"]), 5)

    def test_circuit_breaker_consecutive_errors_aborts(self):
        def always_error(url, timeout, resolver=None, max_range_bytes=None, max_redirects=None):
            return "ERROR", None, None, "UNKNOWN_OR_TRANSIENT", "TimeoutError", "boom"
        lcr.resolve_url = always_error

        input_path = self._write_input(5)
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(input_path), "--output", str(output_path),
                          "--stop-consecutive-errors", "2", "--stop-error-rate", "1.0",
                          "--sleep", "0"])
        self.assertEqual(code, 2)
        sidecar = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(len(sidecar["observations"]), 2)

    def test_produced_sidecar_never_carries_forbidden_or_unknown_fields(self):
        def fake_resolve(url, timeout, resolver=None, max_range_bytes=None, max_redirects=None):
            return "HEAD", 200, url, "REACHABLE", None, None
        lcr.resolve_url = fake_resolve

        input_path = self._write_input(2)
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(input_path), "--output", str(output_path), "--sleep", "0"])
        self.assertEqual(code, 0)
        sidecar = json.loads(output_path.read_text(encoding="utf-8"))
        for obs in sidecar["observations"]:
            self.assertEqual(set(obs.keys()) - lcr.OBSERVATION_ALLOWED_KEYS, set())
        lcr.validate_link_check_sidecar(sidecar)

    def test_malformed_input_exits_nonzero_without_writing_output(self):
        bad_path = self.tmp / "bad.json"
        bad_path.write_text("{ not valid json,,,", encoding="utf-8")
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(bad_path), "--output", str(output_path)])
        self.assertEqual(code, 1)
        self.assertFalse(output_path.exists())

    def test_unrecognized_envelope_exits_nonzero_without_writing_output(self):
        bad_path = self.tmp / "bad_envelope.json"
        bad_path.write_text(json.dumps({"meta": {}}), encoding="utf-8")
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(bad_path), "--output", str(output_path)])
        self.assertEqual(code, 1)
        self.assertFalse(output_path.exists())

    def test_canonical_envelope_reaches_normal_candidate_processing(self):
        """CLI/main fed the canonical {meta,data} artifact envelope with a
        valid projected record reaches normal candidate processing directly
        -- no separate adapter file is required (Prompt 309 §4.A/§5.5)."""
        def fake_resolve(url, timeout, resolver=None, max_range_bytes=None, max_redirects=None):
            return "HEAD", 200, url, "REACHABLE", None, None
        lcr.resolve_url = fake_resolve

        records = json.loads(self._write_input(2).read_text(encoding="utf-8"))
        envelope_path = self.tmp / "envelope_input.json"
        envelope_path.write_text(
            json.dumps({"meta": {"schema": "adgops.public.licitaciones/1"}, "data": records}),
            encoding="utf-8",
        )
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(envelope_path), "--output", str(output_path), "--sleep", "0"])
        self.assertEqual(code, 0)
        sidecar = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(len(sidecar["observations"]), 2)
        lcr.validate_link_check_sidecar(sidecar)

    def test_envelope_records_missing_public_id_fails_closed_no_candidates(self):
        """A canonical envelope whose records lack `public_id` (as current
        production data does, pending Option C) must fail closed with
        `no_candidates_selected`, non-zero exit, and no output sidecar --
        never a schema-valid empty sidecar / exit 0 false-green."""
        records = [{
            "id": "rec-0",
            "documents": [{"title": "D", "url": "https://example.org/doc-0.pdf",
                           "document_type": "generic_doc", "notice_id": "N0",
                           "notice_type": "PUB"}],
        }]
        envelope_path = self.tmp / "no_public_id.json"
        envelope_path.write_text(
            json.dumps({"meta": {"schema": "adgops.public.licitaciones/1"}, "data": records}),
            encoding="utf-8",
        )
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(envelope_path), "--output", str(output_path)])
        self.assertEqual(code, 1)
        self.assertFalse(output_path.exists())

    def test_bare_list_zero_candidates_fails_closed_no_sidecar(self):
        """Any other zero-candidate selection path (here: no usable http(s)
        document URL) likewise cannot exit 0 with an empty sidecar."""
        records = [{"public_id": "pid-0", "id": "rec-0", "documents": []}]
        input_path = self.tmp / "no_urls.json"
        input_path.write_text(json.dumps(records), encoding="utf-8")
        output_path = self.tmp / "out.json"
        code = lcr.main(["--input", str(input_path), "--output", str(output_path)])
        self.assertEqual(code, 1)
        self.assertFalse(output_path.exists())


def main() -> int:
    verbose = any(a in ("-v", "--verbose") for a in sys.argv[1:])
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    n = result.testsRun
    passed = result.wasSuccessful()
    verdict = "PASS" if passed else "FAIL"
    print(f"LINK_CHECK_RESOLVER TESTS: {verdict} ({n} cases)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
