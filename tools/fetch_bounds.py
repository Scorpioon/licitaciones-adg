#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/fetch_bounds.py  (ADG OPS / Prompt 323 Stage B / WRKOPS t_20260923_adgops323)

Pure, deterministic policy primitives for scheduled bounded-production
acquisition. Implements exactly the Stage A policy frozen in
`_wrkops/reports/adgops_prompt_323_bounded_production_acquisition_implementation.report.md`
(sections E, F, H) -- no more, no less.

Owns exactly:
  - source/host registry-consistency authorization (Stage A Sec F):
    verify_source_registry(), allowed_hosts(), is_authorized_host()
  - the real-HTTP-attempt request-budget formula and a fail-closed counter
    (Stage A Sec H): max_total_requests(), RequestBudget
  - the policy-derived global-deadline formula and a monotonic deadline
    checker with an injectable clock (Stage A Sec E): compute_global_deadline_s(),
    Deadline -- the one shared authority both fetch_licitaciones.py's
    cooperative in-process checks and scheduled_fetch_merge.py's hard
    subprocess timeout derive their seconds value from.

Deliberately narrow: no network, no file I/O, no application imports beyond
tools.public_contract (the authoritative source registry), no hidden mutable
module-level state -- every stateful object (RequestBudget, Deadline) is
constructed explicitly by its caller and owns only its own state. This is
not a generalized networking framework; it is the minimal policy surface
Prompt 323 Stage A authorized.
"""

import time
from urllib.parse import urlparse

try:
    from tools import public_contract as pc
except ImportError:  # pragma: no cover - direct-run fallback
    import public_contract as pc

# ---------------------------------------------------------------------------
# Stage A Sec C/D defaults -- the already-justified, unchanged production
# values (report Sec C/D: retries=3, timeout=45s are today's existing
# scheduled defaults, not new numbers). Both fetch_licitaciones.py and
# tools/scheduled_fetch_merge.py import these constants (rather than
# hardcoding their own copies) so a deadline/budget computed in either
# process is derived from one identical source of truth.
# ---------------------------------------------------------------------------

DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY_S = 2.0
DEFAULT_RETRY_BACKOFF = 2.0
DEFAULT_REQUEST_TIMEOUT_S = 45.0
DEFAULT_PAGES = 1

# Upper bound on retry_sleep()'s +-20% jitter (fetch_licitaciones.py's own
# retry_sleep() multiplies by random.uniform(0.8, 1.2); 1.2 is the ceiling).
_JITTER_UPPER = 1.2


# ---------------------------------------------------------------------------
# Source / host authorization (Stage A Sec F)
# ---------------------------------------------------------------------------

class RegistryMismatchError(ValueError):
    """Raised when the scheduled active-source set does not exactly match
    tools.public_contract.PUBLIC_SOURCES (Stage A Sec F). Fail closed before
    any request is made -- this is a whole-run configuration-integrity
    check, never a partial/best-effort authorization."""


def allowed_hosts(registry=None) -> frozenset:
    """Authorized hostnames derived from the authoritative source registry.

    `registry` defaults to tools.public_contract.PUBLIC_SOURCES; a caller
    may pass a substitute registry only for testing.
    """
    registry = pc.PUBLIC_SOURCES if registry is None else registry
    hosts = set()
    for entry in registry.values():
        url = entry.get("url") or ""
        host = urlparse(url).hostname
        if host:
            hosts.add(host.lower())
    return frozenset(hosts)


def is_authorized_host(hostname, registry=None) -> bool:
    """True iff `hostname` is one of the authoritative registry's hosts."""
    if not hostname:
        return False
    return hostname.lower() in allowed_hosts(registry)


def verify_source_registry(active_sources, registry=None) -> None:
    """Fail-closed registry-consistency check (Stage A Sec F).

    `active_sources` is the list of source dicts the scheduled run intends
    to use (fetch_licitaciones.py's SOURCES shape: dicts with "name" and
    "url"). Raises RegistryMismatchError if the active set's (name, url)
    pairs do not exactly equal the authoritative registry's -- a missing
    entry, an extra entry, or a changed URL are all violations. This is a
    single whole-run check performed once, before the first source's first
    request -- never a per-source partial authorization, and it never
    hard-codes a specific source count as a permanent invariant (it always
    compares against whatever the registry currently contains).
    """
    registry = pc.PUBLIC_SOURCES if registry is None else registry
    active_by_name = {s["name"]: s.get("url", "") for s in active_sources}
    registry_by_name = {name: entry.get("url", "") for name, entry in registry.items()}
    if active_by_name != registry_by_name:
        missing = sorted(set(registry_by_name) - set(active_by_name))
        extra = sorted(set(active_by_name) - set(registry_by_name))
        drifted = sorted(
            name for name in (set(active_by_name) & set(registry_by_name))
            if active_by_name[name] != registry_by_name[name]
        )
        raise RegistryMismatchError(
            "scheduled active sources do not match the authoritative "
            "PUBLIC_SOURCES registry: missing=%r extra=%r url_drifted=%r"
            % (missing, extra, drifted)
        )


# ---------------------------------------------------------------------------
# Global deadline formula (Stage A Sec E) -- the one shared authority
# ---------------------------------------------------------------------------

def max_attempts_per_request(retries: int = DEFAULT_RETRIES) -> int:
    """1 initial attempt + `retries` retries (Stage A Sec C)."""
    return 1 + retries


def worst_case_backoff_s(retries: int = DEFAULT_RETRIES,
                          retry_delay: float = DEFAULT_RETRY_DELAY_S,
                          retry_backoff: float = DEFAULT_RETRY_BACKOFF) -> float:
    """Upper bound on total retry_sleep() time across `retries` backoffs,
    including the +-20% jitter ceiling (mirrors fetch_licitaciones.py's own
    retry_sleep(); Stage A Sec E)."""
    return retry_delay * sum(retry_backoff ** i for i in range(retries)) * _JITTER_UPPER


def compute_global_deadline_s(active_source_count: int,
                               pages: int = DEFAULT_PAGES,
                               retries: int = DEFAULT_RETRIES,
                               request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
                               retry_delay: float = DEFAULT_RETRY_DELAY_S,
                               retry_backoff: float = DEFAULT_RETRY_BACKOFF) -> float:
    """The Stage A Sec E policy-derived acquisition-deadline ceiling.

        GLOBAL_DEADLINE_S = active_source_count * pages *
            (max_attempts * request_timeout_s + worst_case_backoff_s)

    This is a policy sizing input for the two enforcement layers (a
    cooperative monotonic Deadline inside bounded acquisition, and a hard
    subprocess timeout in run_live()) -- it is not itself a guarantee that
    any single HTTP attempt completes within request_timeout_s (Stage A
    report Sec E: "not a claim that requests timeout=45 is a guaranteed
    45-second total HTTP wall-clock duration"). The actual wall-clock
    guarantee comes from the two enforcement layers, sized by this formula,
    not from the arithmetic alone.
    """
    max_attempts = max_attempts_per_request(retries)
    backoff = worst_case_backoff_s(retries, retry_delay, retry_backoff)
    per_source = pages * (max_attempts * request_timeout_s + backoff)
    return active_source_count * per_source


# ---------------------------------------------------------------------------
# Real-HTTP-attempt request budget (Stage A Sec H)
# ---------------------------------------------------------------------------

def max_total_requests(active_source_count: int,
                        pages: int = DEFAULT_PAGES,
                        retries: int = DEFAULT_RETRIES) -> int:
    """Stage A Sec H request-accounting budget formula.

        MAX_TOTAL_REQUESTS = active_source_count * pages * (1 + retries)

    A deterministic derivation from the approved policy inputs, never a
    frozen literal -- it recomputes automatically if the source count or
    page count changes.
    """
    return active_source_count * pages * max_attempts_per_request(retries)


class BudgetExceededError(RuntimeError):
    """Raised by RequestBudget.admit() when the next real HTTP attempt
    would exceed the run's request budget (Stage A Sec H) -- fail closed
    BEFORE the request is made, never after."""


class RequestBudget:
    """Fail-closed counter of REAL_HTTP_ATTEMPTs against a fixed budget.

    One REAL_HTTP_ATTEMPT = exactly one observable session.get() call made
    from the bounded fetch_source() attempt loop (valid only because
    bounded mode disables the urllib3 auto-retry layer -- Stage A Sec A/H
    -- so no request this counter cannot see happens underneath it). Call
    admit() immediately BEFORE making that call; it raises
    BudgetExceededError instead of allowing the call once the budget is
    exhausted, and only ever increments the counter for calls it admitted.
    """

    def __init__(self, max_total: int):
        if max_total < 0:
            raise ValueError("max_total must be >= 0")
        self.max_total = max_total
        self.used = 0

    def admit(self) -> None:
        if self.used >= self.max_total:
            raise BudgetExceededError(
                "request budget exhausted: %d/%d real HTTP attempts already "
                "made; refusing the next attempt" % (self.used, self.max_total)
            )
        self.used += 1

    def remaining(self) -> int:
        return max(0, self.max_total - self.used)


# ---------------------------------------------------------------------------
# Monotonic deadline (Stage A Sec E.1/E.2/E.3) -- the shared enforcement
# authority for both the cooperative in-process layer and the hard
# subprocess-timeout layer.
# ---------------------------------------------------------------------------

class DeadlineExceededError(RuntimeError):
    """Raised by Deadline.check() once the global deadline has passed
    (Stage A Sec E.1). Callers must make no new HTTP attempt once this
    fires, and must fail closed for the remaining pages/sources."""


class Deadline:
    """Monotonic wall-clock deadline shared by both enforcement layers.

    Constructed once per bounded-mode invocation with the SAME
    GLOBAL_DEADLINE_S value compute_global_deadline_s() produced (Stage A
    Sec E.3: the "fetch_bounds monotonic deadline" layer is this object;
    the "run_live subprocess timeout" layer uses the identical seconds
    value directly as subprocess.run(timeout=...) -- never a second,
    independently-derived number).

    `clock` is injectable (defaults to time.monotonic) so offline tests can
    drive expiry deterministically without real elapsed time.
    """

    def __init__(self, deadline_s: float, clock=None):
        self._clock = clock or time.monotonic
        self.deadline_s = deadline_s
        self._deadline_at = self._clock() + deadline_s

    def expired(self) -> bool:
        return self._clock() >= self._deadline_at

    def check(self) -> None:
        """Raise DeadlineExceededError if the deadline has passed. Callers
        invoke this at every Stage A Sec E.1 checkpoint; it never blocks or
        sleeps -- it is a pure point-in-time check."""
        if self.expired():
            raise DeadlineExceededError(
                "bounded acquisition deadline exhausted (%ss)" % self.deadline_s
            )

    def remaining(self) -> float:
        return max(0.0, self._deadline_at - self._clock())
