#!/usr/bin/env python3
"""
tools/scheduled_candidate_policy.py
ADG OPS v0.7.1u -- Prompt 271 (D-04/F4) -- shared candidate run_status subpredicate.

Neutral pure-policy module. Owns only the truly common decision over an
already-normalized (lower-case) run_status string:

    "success" not in run_status_lower

Nothing else is owned here. In particular:

  - the is_partial identity guard (is_partial is True) stays consumer-owned, so
    each consumer keeps its historical short-circuit evaluation order. That
    order is not the same on both sides:
      * tools/scheduled_fetch_merge.py nests the whole partial branch, so it
        does not read or normalize run_status at all unless is_partial is the
        literal True;
      * tools/scheduled_run_classify.py short-circuits only the partial-branch
        lower() call. Its separate upper() FAILURE/EMPTY_FAILURE guard is
        is_partial-independent and still evaluates run_status on every call;
  - raw run_status normalization stays consumer-owned:
    tools/scheduled_fetch_merge.py uses
    str(candidate_meta.get("run_status", "")).lower() nested inside its partial
    guard, and tools/scheduled_run_classify.py uses cand_run_status.lower() as
    the right operand of a short-circuiting `and`, so a malformed (None/int)
    run_status still raises AttributeError exactly as before p271 -- this
    module does not catch or convert that;
  - the classifier's additional status-only FAILURE/EMPTY_FAILURE branch
    remains owned by
    tools/scheduled_run_classify.py:candidate_failed_closed().
"""


def run_status_lacks_success(run_status_lower: str) -> bool:
    """Return True when normalized run_status lacks the substring 'success'."""
    return "success" not in run_status_lower
