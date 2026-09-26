#!/usr/bin/env python3
"""
tools/scheduled_run_classify.py
ADG OPS v0.6.44 / Prompt 190 — Scheduled fetcher operational-status classifier.

Single source of truth for the workflow "Operational summary" step. This module
was extracted verbatim (behaviour-preserving) from the inline Python heredoc in
.github/workflows/fetch.yml so that:

  - the workflow imports/calls it instead of carrying an inline heredoc, and
  - the offline regression harness (tools/fetcher_fixture_regression.py) can
    import and table-drive the exact same classification logic.

Standard-library only. No network. Never mutates production data.

Preserved semantics:
  - p186 fail-closed sub-types (FAIL_CLOSED_PARTIAL_SOURCE_OUTAGE,
    FAIL_CLOSED_PARSER_NON_ATOM, FAIL_CLOSED_VALIDATION, FAIL_CLOSED_MERGE_POLICY,
    FAIL_CLOSED_GIT_COMMIT, FAIL_CLOSED_GIT_PUSH) and the candidate_failed_closed()
    masked-exit protection (e.g. run #138 EMPTY_FAILURE).
  - p187 automation identity fields (AUTOMATION_ID/KIND/DATA_FILE/SOURCES).
  - p188 machine-readable report (ADGOPS_SCHEDULED_RUN_REPORT_V1 / schema_version 1.0).
  - p265 gate-awareness: the shard-build step (id: shards) and canonical
    public-contract-gate step (id: shardvalidate) outcomes are now classified.
    A failure or cancellation of either produces a named fail-closed status
    (FAIL_CLOSED_SHARD_BUILD / FAIL_CLOSED_PUBLIC_CONTRACT) instead of the
    prior terminal UNKNOWN. "skipped" is not a failure: unchanged/no-data,
    dry-run and guard-skipped runs legitimately skip both steps.
  - The classifier never exits non-zero: the workflow relies on the individual
    step outcomes (this step is `if: always()`), not on this script's exit code.

CLI (called from the workflow):
  python tools/scheduled_run_classify.py
    1. inspects env vars and _tmp exactly as the old heredoc did,
    2. writes the markdown summary to $GITHUB_STEP_SUMMARY if set,
    3. appends OPERATIONAL_STATUS to $GITHUB_ENV if set,
    4. writes _tmp/scheduled_run_report_<GH_RUN_NUMBER>.json,
    5. prints the markdown summary,
    6. prints OPERATIONAL_STATUS=<status>,
    7. exits 0 (preserving the old heredoc behaviour).
"""

import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from tools import scheduled_candidate_policy as scp
except ImportError:  # pragma: no cover - direct-run fallback
    import scheduled_candidate_policy as scp

# Prompt 324 Stage B / WRKOPS t_20260924_adgops324 (Stage A/R1-authorized):
# the V2 durable receipt reuses the same frozen bounded-acquisition policy
# authority (tools/fetch_bounds.py) and the authoritative source registry
# (tools/public_contract.py) already imported by run_live() -- never a
# second, independently-derived copy of either. run_receipt.py is the pure
# serialization/hash/sidecar helper (Stage A/R1 report §19.5): it owns no
# classification logic.
try:
    from tools import fetch_bounds
except ImportError:  # pragma: no cover - direct-run fallback
    import fetch_bounds

try:
    from tools import public_contract as pc
except ImportError:  # pragma: no cover - direct-run fallback
    import public_contract as pc

try:
    from tools import run_receipt as rr
except ImportError:  # pragma: no cover - direct-run fallback
    import run_receipt as rr

REPORT_SCHEMA = "ADGOPS_SCHEDULED_RUN_REPORT_V1"
REPORT_VERSION = "1.0"
WORKFLOW_NAME = "Fetch Licitaciones Scheduled Safe Merge"

# Prompt 324 Stage B: the durable V2 receipt-of-record. Evolves REPORT_SCHEMA
# above -- it is not an independent "adgops.run_receipt/1" status truth
# (Stage A/R1 report §19.5, Stage B prompt §1.1). classify()/render_summary()/
# write_outputs()'s existing V1 behaviour is unchanged by its presence.
RECEIPT_SCHEMA_V2 = "ADGOPS_SCHEDULED_RUN_REPORT_V2"
RECEIPT_VERSION_V2 = "2.0"

# Terminal statuses that are NOT a refusal -- everything else already uses
# the existing, unchanged fail-closed/UNKNOWN taxonomy as its own bounded
# refusal-reason label (Stage B prompt §2.11).
_NON_REFUSAL_STATUSES = frozenset({
    "SUCCESS_REAL_FETCH_WRITE",
    "SUCCESS_REAL_FETCH_NO_CHANGES",
    "MANUAL_DRY_RUN_SUCCESS",
    "SKIPPED_BY_GUARD",
})

# Production public artifact path, read-only, for publication identity
# (generation_id / dataset_sha256 / monolith file SHA256) -- the same file
# tools/scheduled_fetch_merge.py's run_live() and fetch.yml's shardvalidate
# step already treat as the canonical public monolith. Never written here.
PRODUCTION_PATH_V2 = Path("data/licitaciones.json")

# Outcomes considered failures (GitHub step.outcome values).
_FAILED_OUTCOMES = ("failure", "cancelled")

# Per-source error truncation limits (preserved from the heredoc):
#   summary table -> 300 chars, machine report -> 500 chars.
SUMMARY_SOURCE_ERR_MAX = 300
REPORT_SOURCE_ERR_MAX = 500


# ---------------------------------------------------------------------------
# Env / candidate / helper-log helpers
# ---------------------------------------------------------------------------

def env_get(env: dict, key: str, default: str = "") -> str:
    """env.get with the heredoc's default semantics."""
    return env.get(key, default)


def read_helper_log(tmp_dir) -> str:
    """Read _tmp/run_helper.log (captured via tee) if present; '' otherwise."""
    log_path = Path(tmp_dir) / "run_helper.log"
    if log_path.exists():
        try:
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except Exception:
            return ""
    return ""


def load_candidate_from_tmp(tmp_dir) -> dict:
    """
    Load the most recent live candidate envelope, if the fetcher produced one.

    Mirrors the heredoc: glob _tmp/scheduled_live_candidate_*.json, take the last
    sorted match, and read meta either from a nested {"meta": {...}} envelope or
    from the top-level dict (fetcher top-level-metadata shape).
    """
    info = {
        "path": "",
        "partial": None,
        "run_status": "",
        "failed_sources": [],
        "source_errors": {},
    }
    cands = sorted(glob.glob(str(Path(tmp_dir) / "scheduled_live_candidate_*.json")))
    if not cands:
        return info
    info["path"] = cands[-1]
    try:
        with open(info["path"], encoding="utf-8") as fh:
            cj = json.load(fh)
        meta = cj.get("meta") if isinstance(cj.get("meta"), dict) else cj
        info["partial"] = meta.get("is_partial")
        info["run_status"] = str(meta.get("run_status", ""))
        info["failed_sources"] = meta.get("failed_sources", []) or []
        info["source_errors"] = meta.get("source_errors", {}) or {}
    except Exception as e:
        info["run_status"] = f"(candidate unreadable: {e})"
    return info


# ---------------------------------------------------------------------------
# Fail-closed classification helpers (p186)
# ---------------------------------------------------------------------------

def classify_source_failure(source_errors: dict, helper_log: str) -> str:
    """Distinguish a non-Atom parser failure from a generic partial source outage."""
    blob = " ".join(str(v).lower() for v in source_errors.values()) + " " + (helper_log or "").lower()
    if "non-atom" in blob:
        return "FAIL_CLOSED_PARSER_NON_ATOM"
    return "FAIL_CLOSED_PARTIAL_SOURCE_OUTAGE"


def candidate_failed_closed(cand_partial, cand_run_status: str) -> bool:
    """
    Truthful operational status must follow the candidate envelope, not just the
    helper step's exit code. If tee (or anything else) masks the helper's non-zero
    exit, a partial/EMPTY_FAILURE candidate must still classify fail-closed — it
    was never an accepted production write.
    """
    if cand_partial is True and scp.run_status_lacks_success(
        cand_run_status.lower()
    ):
        return True
    rs = cand_run_status.upper()
    if "EMPTY_FAILURE" in rs or "FAILURE" in rs:
        return True
    return False


# ---------------------------------------------------------------------------
# Core classification (behaviour-identical to the fetch.yml heredoc)
# ---------------------------------------------------------------------------

def classify(env: dict, tmp_dir="_tmp", helper_log: str | None = None) -> dict:
    """
    Compute the operational status and the full p188 report from env + _tmp state.

    Returns a result dict:
      {
        "status": <OPERATIONAL_STATUS>,
        "summary_rows": [(label, value), ...],
        "source_errors": {...},          # raw, for the summary "Source errors" block
        "run_number": <str>,
        "report": <ADGOPS_SCHEDULED_RUN_REPORT_V1 dict>,
      }
    """
    run_fetch = env_get(env, "RUN_FETCH", "")
    dry_mode = env_get(env, "DRY_RUN_MODE", "false")
    helper_out = env_get(env, "HELPER_OUTCOME", "skipped")
    dryrun_out = env_get(env, "DRYRUN_OUTCOME", "skipped")
    validate_out = env_get(env, "VALIDATE_OUTCOME", "skipped")
    diff_out = env_get(env, "DIFFSUMMARY_OUTCOME", "skipped")
    shards_out = env_get(env, "SHARDS_OUTCOME", "skipped")
    shardvalidate_out = env_get(env, "SHARDVALIDATE_OUTCOME", "skipped")
    commit_out = env_get(env, "COMMIT_OUTCOME", "skipped")
    push_out = env_get(env, "PUSH_OUTCOME", "skipped")
    data_changed = env_get(env, "DATA_CHANGED", "")  # 'true' / 'false' / ''

    cand = load_candidate_from_tmp(tmp_dir)
    cand_path = cand["path"]
    cand_partial = cand["partial"]
    cand_run_status = cand["run_status"]
    failed_sources = cand["failed_sources"]
    source_errors = cand["source_errors"]

    if helper_log is None:
        helper_log = read_helper_log(tmp_dir)

    helper_ran = helper_out not in ("skipped", "")
    failed = _FAILED_OUTCOMES

    if run_fetch == "skip":
        status = "SKIPPED_BY_GUARD"
    elif dry_mode == "true":
        status = "MANUAL_DRY_RUN_SUCCESS" if dryrun_out == "success" else "FAIL_CLOSED_VALIDATION"
    elif helper_out in failed:
        # Helper (fetch + lifecycle-safe merge) failed — classify the fail-closed cause.
        lg = helper_log.lower()
        if "lifecycle integrity failed" in lg:
            status = "FAIL_CLOSED_MERGE_POLICY"
        elif "candidate invalid" in lg or "production invalid" in lg:
            status = "FAIL_CLOSED_VALIDATION"
        elif "refusing production write" in lg or "partial/failed candidate" in lg:
            status = classify_source_failure(source_errors, helper_log)
        elif cand_partial is True and "success" not in cand_run_status.lower():
            status = classify_source_failure(source_errors, helper_log)
        else:
            status = "FAIL_CLOSED"
    elif candidate_failed_closed(cand_partial, cand_run_status):
        # Helper step reported success but the live candidate is partial/failed —
        # treat as fail-closed (e.g. run #138: EMPTY_FAILURE + ConnectTimeout while
        # the step exit was masked). Checked BEFORE the success branch.
        status = classify_source_failure(source_errors, helper_log)
    elif helper_out == "success":
        # Helper wrote production; account for failures in the steps that follow it.
        if validate_out in failed:
            status = "FAIL_CLOSED_VALIDATION"
        elif diff_out in failed:
            status = "FAIL_CLOSED_VALIDATION"
        elif shards_out in failed:
            # Shard-build failure/cancellation (id: shards) classified before the
            # contract gate and before commit/push (p265 precedence rules 5-6).
            status = "FAIL_CLOSED_SHARD_BUILD"
        elif shardvalidate_out in failed:
            # Canonical public-contract-gate failure/cancellation (id: shardvalidate).
            status = "FAIL_CLOSED_PUBLIC_CONTRACT"
        elif commit_out in failed:
            status = "FAIL_CLOSED_GIT_COMMIT"
        elif data_changed == "true" and push_out != "success":
            # Changes committed but push did not succeed (failed/cancelled/unexpectedly skipped).
            status = "FAIL_CLOSED_GIT_PUSH"
        elif data_changed == "true" and push_out == "success":
            status = "SUCCESS_REAL_FETCH_WRITE"
        elif data_changed == "false":
            status = "SUCCESS_REAL_FETCH_NO_CHANGES"
        else:
            status = "UNKNOWN"
    else:
        status = "UNKNOWN"

    def yn(v):
        return "yes" if v else "no"

    # candidate accepted: was the live candidate eligible for a production write?
    # A partial/EMPTY_FAILURE candidate is refused (fail-closed), so it is never
    # "accepted" even if the helper step exit was masked.
    if dry_mode == "true" or run_fetch == "skip" or not helper_ran:
        candidate_accepted = "n/a"
    elif candidate_failed_closed(cand_partial, cand_run_status):
        candidate_accepted = "no"
    elif cand_partial is None:
        candidate_accepted = "n/a"
    else:
        candidate_accepted = "yes"

    # data write: production was (re)written iff the live helper succeeded AND the
    # candidate was not failed-closed. A masked helper exit on an EMPTY_FAILURE
    # candidate must NOT report "yes".
    if dry_mode == "true" or run_fetch == "skip":
        data_write = "n/a"
    elif candidate_failed_closed(cand_partial, cand_run_status):
        data_write = "no"
    elif helper_out == "success":
        data_write = "yes"
    elif helper_out in failed:
        data_write = "no"
    else:
        data_write = "n/a"

    # commit pushed: yes only when data changed AND push succeeded.
    if data_changed == "true" and push_out == "success":
        commit_pushed = "yes"
    elif data_changed == "false":
        commit_pushed = "no"
    else:
        commit_pushed = "n/a"

    rows = [
        ("automation id",    env_get(env, "AUTOMATION_ID") or "n/a"),
        ("automation kind",  env_get(env, "AUTOMATION_KIND") or "n/a"),
        ("data file",        env_get(env, "AUTOMATION_DATA_FILE") or "n/a"),
        ("sources",          env_get(env, "AUTOMATION_SOURCES") or "n/a"),
        ("event",            env_get(env, "GUARD_EVENT") or env_get(env, "GH_EVENT_NAME") or "n/a"),
        ("schedule",         env_get(env, "GUARD_SCHEDULE") or "(manual / none)"),
        ("Madrid time",      f"{env_get(env, 'GUARD_MADRID') or 'n/a'} ({env_get(env, 'GUARD_OFFSET') or '?'})"),
        ("guard reason",     env_get(env, "GUARD_REASON") or "n/a"),
        ("RUN_FETCH",        run_fetch or "n/a"),
        ("dry_run input",    env_get(env, "GUARD_DRY_RUN_INPUT", "false")),
        ("force_run input",  env_get(env, "GUARD_FORCE", "false")),
        ("helper ran",       yn(helper_ran)),
        ("candidate path",   cand_path or "n/a"),
        ("candidate partial", "n/a" if cand_partial is None else yn(cand_partial)),
        ("candidate run_status", cand_run_status or "n/a"),
        ("candidate accepted", candidate_accepted),
        ("source failures",  ", ".join(failed_sources) if failed_sources else "none"),
        ("validate outcome", validate_out),
        ("diff summary outcome", diff_out),
        ("shard build outcome", shards_out),
        ("public contract outcome", shardvalidate_out),
        ("commit outcome",   commit_out),
        ("push outcome",     push_out),
        ("data write",       data_write),
        ("commit pushed",    commit_pushed),
        ("run number",       f"#{env_get(env, 'GH_RUN_NUMBER')}"),
    ]

    # ------------------------------------------------------------------
    # Machine-readable run report (p188 / v0.6.42). Truncate each source error
    # so the report stays diagnostic but bounded; never embed raw helper log.
    report_source_errors = {
        str(k): str(v)[:REPORT_SOURCE_ERR_MAX] for k, v in source_errors.items()
    }
    report = {
        "schema": REPORT_SCHEMA,
        "schema_version": REPORT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "automation": {
            "id": env_get(env, "AUTOMATION_ID") or None,
            "kind": env_get(env, "AUTOMATION_KIND") or None,
            "data_file": env_get(env, "AUTOMATION_DATA_FILE") or None,
            "sources": [s.strip() for s in env_get(env, "AUTOMATION_SOURCES").split(",") if s.strip()],
        },
        "github": {
            "event": env_get(env, "GUARD_EVENT") or env_get(env, "GH_EVENT_NAME") or None,
            "run_number": env_get(env, "GH_RUN_NUMBER") or None,
            "workflow": WORKFLOW_NAME,
        },
        "guard": {
            "run_fetch": run_fetch or None,
            "dry_run_input": env_get(env, "GUARD_DRY_RUN_INPUT", "false"),
            "force_run_input": env_get(env, "GUARD_FORCE", "false"),
            "schedule": env_get(env, "GUARD_SCHEDULE") or "manual",
            "madrid_time": env_get(env, "GUARD_MADRID") or None,
            "utc_offset": env_get(env, "GUARD_OFFSET") or None,
            "reason": env_get(env, "GUARD_REASON") or None,
        },
        "operational": {
            "status": status,
            "helper_ran": helper_ran,
            "candidate_accepted": candidate_accepted,
            "data_write": data_write,
            "commit_pushed": commit_pushed,
        },
        "candidate": {
            "path": cand_path or None,
            "partial": cand_partial,
            "run_status": cand_run_status or None,
            "failed_sources": failed_sources,
            "source_errors": report_source_errors,
        },
        "outcomes": {
            "helper": helper_out,
            "dryrun": dryrun_out,
            "validate": validate_out,
            "diff_summary": diff_out,
            "shard_build": shards_out,
            "public_contract": shardvalidate_out,
            "commit": commit_out,
            "push": push_out,
        },
        "data": {
            "data_changed": data_changed,
            "write_intent": data_write,
            "target_file": env_get(env, "AUTOMATION_DATA_FILE") or "data/licitaciones.json",
        },
    }

    return {
        "status": status,
        "summary_rows": rows,
        "source_errors": source_errors,
        "run_number": env_get(env, "GH_RUN_NUMBER"),
        "report": report,
        # Prompt 324 Stage B: carried through so write_outputs()/build_receipt_v2()
        # never need to re-read _tmp/run_helper.log a second time.
        "helper_log": helper_log,
    }


# ---------------------------------------------------------------------------
# Rendering / output
# ---------------------------------------------------------------------------

def render_summary(result: dict) -> str:
    """Render the markdown Operational Summary (identical to the heredoc output)."""
    status = result["status"]
    rows = result["summary_rows"]
    source_errors = result.get("source_errors", {}) or {}

    lines = [
        "## Scheduled Fetcher — Operational Summary",
        "",
        f"**Final operational status:** `{status}`",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for k, v in rows:
        v = str(v).replace("|", "\\|")
        lines.append(f"| {k} | {v} |")

    if source_errors:
        lines.append("")
        lines.append("### Source errors")
        for k, v in source_errors.items():
            lines.append(f"- **{k}**: {str(v)[:SUMMARY_SOURCE_ERR_MAX]}")

    return "\n".join(lines) + "\n"


def write_outputs(result: dict, tmp_dir="_tmp", github_step_summary: str | None = None,
                  github_env: str | None = None, env: dict | None = None) -> None:
    """
    Write the markdown summary to $GITHUB_STEP_SUMMARY (if set), append
    OPERATIONAL_STATUS to $GITHUB_ENV (if set), and write the machine-readable
    report JSON to <tmp_dir>/scheduled_run_report_<run>.json.

    Prompt 324 Stage B: when `env` is supplied (main() always supplies the
    full run env; existing direct callers that omit it keep the exact prior
    V1-only behaviour), also finalizes the durable V2 receipt + `.sha256`
    sidecar in `tmp_dir` and appends RECEIPT_PATH/RECEIPT_SIDECAR_PATH to
    $GITHUB_ENV (if set) for the workflow's artifact-upload step to consume.
    A receipt-write failure never affects the V1 outputs above, which have
    already been written by the time this is attempted.
    """
    out = render_summary(result)
    status = result["status"]

    if github_step_summary:
        with open(github_step_summary, "a", encoding="utf-8") as fh:
            fh.write(out)

    if github_env:
        with open(github_env, "a", encoding="utf-8") as fh:
            fh.write(f"OPERATIONAL_STATUS={status}\n")

    # Machine-readable run report (p188). Wrapped in try/except so a report-write
    # failure can never block the summary.
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        report_path = os.path.join(str(tmp_dir), f"scheduled_run_report_{result.get('run_number', '')}.json")
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(result["report"], fh, sort_keys=True, indent=2)
            fh.write("\n")
        print(f"[report] wrote {report_path}")
    except Exception as e:
        print(f"[report] WARNING: failed to write run report JSON: {e}")

    if env is not None:
        info = finalize_v2_receipt(env, result, tmp_dir=tmp_dir, helper_log=result.get("helper_log"))
        if info and github_env:
            with open(github_env, "a", encoding="utf-8") as fh:
                fh.write(f"RECEIPT_PATH={info['receipt_path']}\n")
                fh.write(f"RECEIPT_SIDECAR_PATH={info['sidecar_path']}\n")


# ---------------------------------------------------------------------------
# Prompt 324 Stage B (WRKOPS t_20260924_adgops324) -- V2 durable receipt.
#
# Single-authority evolution of the V1 report above (Stage A/R1 report
# §19.5): every field below is either copied verbatim from `result["report"]`
# (already computed by classify(), never reclassified) or derived from
# evidence already available to THIS process in the same job/runner --
# the candidate file classify() already located, the already-frozen
# tools/fetch_bounds.py policy formulas, the already-persisted
# data/licitaciones.json, and _tmp/run_helper.log's own printed lines. No
# new ephemeral evidence fragment is required from tools/scheduled_fetch_merge.py
# (Stage B prompt §3): every fact below is honestly obtainable at the
# workflow-level finalizer alone.
# ---------------------------------------------------------------------------

def read_candidate_evidence(cand_path) -> dict | None:
    """Exact-byte identity (bytes/SHA256) plus bounded, already-safe
    acquisition-outcome fields read directly from the candidate file this
    same job's helper step wrote earlier -- never the raw `source_errors`/
    `retry_errors_by_source` text or the candidate's own `data` array."""
    if not cand_path:
        return None
    try:
        with open(cand_path, "rb") as fh:
            raw = fh.read()
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    meta = parsed.get("meta") if isinstance(parsed.get("meta"), dict) else parsed
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "requested_sources": meta.get("requested_sources") or [],
        "completed_sources": meta.get("completed_sources") or [],
        "completed_pages_by_source": meta.get("completed_pages_by_source") or {},
        "deadline_exhausted": meta.get("deadline_exhausted"),
        "budget_exhausted": meta.get("budget_exhausted"),
    }


def bounded_policy_snapshot() -> dict:
    """The actual bounded-acquisition policy in force for this run, copied
    from tools/fetch_bounds.py's already-frozen Prompt-323 formulas and
    defaults over the authoritative source registry -- never a second,
    independently re-derived number (Stage A report §4/§11, Stage B prompt
    §2.4). Redirect policy is a fixed bounded-mode constant
    (fetch_licitaciones.py: `allow_redirects = not bounded`, i.e. disabled
    whenever bounded mode is on) -- a literal fact, not a formula, and not
    re-derived here."""
    active_source_count = len(pc.PUBLIC_SOURCES)
    pages = fetch_bounds.DEFAULT_PAGES
    retries = fetch_bounds.DEFAULT_RETRIES
    timeout_s = fetch_bounds.DEFAULT_REQUEST_TIMEOUT_S
    return {
        "active_source_count": active_source_count,
        "pages": pages,
        "retries": retries,
        "max_attempts_per_request": fetch_bounds.max_attempts_per_request(retries),
        "request_timeout_s": timeout_s,
        "global_deadline_s": fetch_bounds.compute_global_deadline_s(
            active_source_count=active_source_count,
            pages=pages,
            retries=retries,
            request_timeout_s=timeout_s,
            retry_delay=fetch_bounds.DEFAULT_RETRY_DELAY_S,
            retry_backoff=fetch_bounds.DEFAULT_RETRY_BACKOFF,
        ),
        "max_total_requests": fetch_bounds.max_total_requests(active_source_count, pages, retries),
        "redirect_policy": "disabled",
    }


def continuity_state_written(helper_log: str):
    """Whether persist_internal_state() wrote/skipped the private
    continuity state this run, read honestly from the two exact print()
    lines run_live() already emits (scheduled_fetch_merge.py's own
    "Internal state persisted"/"Internal state unchanged, not rewritten"
    messages, captured into _tmp/run_helper.log) -- never the private
    state's own contents. Returns True/False/None (unknown -- helper did
    not reach that point, or did not run at all)."""
    log = helper_log or ""
    if "[run-live] Internal state persisted:" in log:
        return True
    if "[run-live] Internal state unchanged, not rewritten:" in log:
        return False
    return None


def read_publication_identity(production_path=None) -> dict | None:
    """Existing authoritative public identity (generation_id/dataset_sha256)
    plus the exact-byte monolith file SHA256, read directly from the
    already-written public artifact -- never a new competing content
    identity (Stage B prompt §2.8). Read-only; this never writes
    data/licitaciones.json."""
    path = Path(production_path) if production_path else PRODUCTION_PATH_V2
    try:
        with open(path, "rb") as fh:
            monolith_bytes = fh.read()
        monolith = json.loads(monolith_bytes.decode("utf-8"))
    except Exception:
        return None
    meta = monolith.get("meta") if isinstance(monolith.get("meta"), dict) else {}
    counts = meta.get("counts") if isinstance(meta.get("counts"), dict) else {}
    return {
        "generation_id": meta.get("generation_id"),
        "dataset_sha256": meta.get("dataset_sha256"),
        "monolith_file_sha256": hashlib.sha256(monolith_bytes).hexdigest(),
        "monolith_bytes": len(monolith_bytes),
        "record_count": counts.get("records"),
    }


def sanitized_error_categories_for(status: str, helper_log: str) -> list:
    """Bounded category labels only -- never raw error text, never a
    traceback (Stage B prompt §2.5/§2.11). The terminal status itself is
    already a bounded, closed-taxonomy label (classify()'s own FAIL_CLOSED*
    vocabulary); the hard-subprocess-timeout case is detected via the same
    already-established helper_log substring-matching mechanism
    classify_source_failure() uses, without altering `status` itself."""
    categories = []
    if status and status != "UNKNOWN" and status not in _NON_REFUSAL_STATUSES:
        categories.append(status)
    if "exceeded the global acquisition deadline" in (helper_log or "").lower():
        categories.append("DEADLINE_EXCEEDED_HARD_TIMEOUT")
    return categories


def build_receipt_v2(env: dict, result: dict, helper_log: str | None = None,
                      production_path=None) -> dict:
    """Assemble the V2 receipt from `result` (classify()'s already-computed
    V1 output -- never reclassified) plus the additional Stage-B fields.
    Every field is either copied from `result["report"]` or derived from
    evidence already available to this process (Stage A/R1 report §19.5)."""
    v1 = result["report"]
    status = result["status"]
    if helper_log is None:
        helper_log = result.get("helper_log")

    run_number = env_get(env, "GH_RUN_NUMBER") or None
    run_attempt = env_get(env, "GH_RUN_ATTEMPT") or None
    baseline_head = env_get(env, "BASELINE_HEAD") or None
    started_at = env_get(env, "RUN_STARTED_AT") or None
    finished_at = datetime.now(timezone.utc).isoformat()
    elapsed_s = None
    if started_at:
        try:
            start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            finish_dt = datetime.fromisoformat(finished_at)
            elapsed_s = round((finish_dt - start_dt).total_seconds(), 3)
        except Exception:
            elapsed_s = None

    helper_ran = bool(v1["operational"]["helper_ran"])
    cand_path = v1["candidate"]["path"] or None
    cand_evidence = read_candidate_evidence(cand_path) if cand_path else None

    data_changed = env_get(env, "DATA_CHANGED", "") or None
    monolith_changed = env_get(env, "MONOLITH_CHANGED", "") or None

    publication = None
    if data_changed == "true":
        publication = read_publication_identity(production_path)

    gates = {
        "helper": v1["outcomes"]["helper"],
        "validate": v1["outcomes"]["validate"],
        "diff_summary": v1["outcomes"]["diff_summary"],
        "shard_build": v1["outcomes"]["shard_build"],
        "public_contract": v1["outcomes"]["public_contract"],
        "privacy": env_get(env, "PRIVACYREPORT_OUTCOME", "skipped"),
        "commit": v1["outcomes"]["commit"],
        "push": v1["outcomes"]["push"],
    }

    commit_sha = env_get(env, "COMMIT_SHA") or None
    commit_out = v1["outcomes"]["commit"]
    if data_changed == "true":
        commit_decision = "created"
    elif commit_out == "skipped" and monolith_changed != "false":
        # Commit was never reached because an earlier gate (or the run
        # itself) never got that far -- not the same as a legitimate
        # no-material-change refusal to commit.
        commit_decision = "n/a"
    else:
        commit_decision = "not_created"

    receipt = {
        "schema": RECEIPT_SCHEMA_V2,
        "schema_version": RECEIPT_VERSION_V2,
        "generated_at_utc": finished_at,
        "run_identity": {
            "workflow": v1["github"]["workflow"],
            "event": v1["github"]["event"],
            "run_number": run_number,
            "run_attempt": run_attempt,
            "baseline_head": baseline_head,
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
            "elapsed_s": elapsed_s,
        },
        "automation": dict(v1["automation"]),
        "guard": dict(v1["guard"]),
        "bounded_policy_snapshot": bounded_policy_snapshot() if helper_ran else None,
        "acquisition_outcome": {
            "requested_sources": (cand_evidence or {}).get("requested_sources") or v1["automation"]["sources"],
            "completed_sources": (cand_evidence or {}).get("completed_sources") or [],
            "failed_sources": v1["candidate"]["failed_sources"],
            "completed_pages_by_source": (cand_evidence or {}).get("completed_pages_by_source") or {},
            "candidate_run_status": v1["candidate"]["run_status"] or None,
            "candidate_partial": v1["candidate"]["partial"],
            "deadline_exhausted": (cand_evidence or {}).get("deadline_exhausted"),
            "budget_exhausted": (cand_evidence or {}).get("budget_exhausted"),
            "total_real_http_attempts": None,
        },
        "candidate": {
            "filename": Path(cand_path).name if cand_path else None,
            "bytes": (cand_evidence or {}).get("bytes"),
            "sha256": (cand_evidence or {}).get("sha256"),
            "run_status": v1["candidate"]["run_status"] or None,
            "is_partial": v1["candidate"]["partial"],
            "identity_note": (
                "run-time attestation only; raw candidate bytes are not retained "
                "durably" if cand_evidence else None
            ),
        },
        "continuity": {
            "state_written": continuity_state_written(helper_log) if helper_ran else None,
        },
        "material_change": {
            "monolith_changed": monolith_changed,
            "data_changed": data_changed,
        },
        "publication": publication,
        "gates": gates,
        "commit": {
            "decision": commit_decision,
            "sha": commit_sha,
            "push_outcome": v1["outcomes"]["push"],
        },
        "terminal": {
            "operational_status": status,
            "refusal_reason": None if status in _NON_REFUSAL_STATUSES else status,
        },
        "sanitized_error_categories": sanitized_error_categories_for(status, helper_log),
    }
    return receipt


def finalize_v2_receipt(env: dict, result: dict, tmp_dir="_tmp", helper_log: str | None = None,
                         production_path=None) -> dict | None:
    """Build and durably write the V2 receipt + `.sha256` sidecar to
    `tmp_dir` via tools/run_receipt.py's exact-byte pattern. Never raises:
    a receipt-write failure must never affect anything else this script
    does (mirrors write_outputs()'s existing V1-report try/except, Stage B
    prompt §1.6). Returns run_receipt.write_receipt()'s info dict (plus
    "filename") on success, or None on failure (a warning is printed, same
    as the V1 report's own failure mode)."""
    try:
        receipt = build_receipt_v2(env, result, helper_log=helper_log,
                                    production_path=production_path)
        run_number = env_get(env, "GH_RUN_NUMBER") or "unknown"
        run_attempt = env_get(env, "GH_RUN_ATTEMPT") or "unknown"
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = rr.receipt_filename(run_number, run_attempt, ts)
        info = rr.write_receipt(receipt, tmp_dir, filename)
        info["filename"] = filename
        print(f"[receipt] wrote {info['receipt_path']} (sha256={info['sha256'][:12]}...)")
        return info
    except Exception as e:
        print(f"[receipt] WARNING: failed to write V2 receipt: {e}")
        return None


def main() -> int:
    env = dict(os.environ)
    tmp_dir = "_tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    result = classify(env, tmp_dir=tmp_dir)
    write_outputs(
        result,
        tmp_dir=tmp_dir,
        github_step_summary=env.get("GITHUB_STEP_SUMMARY"),
        github_env=env.get("GITHUB_ENV"),
        env=env,
    )

    print(render_summary(result))
    print(f"OPERATIONAL_STATUS={result['status']}")
    # Preserve heredoc behaviour: the classifier never exits non-zero. The workflow
    # relies on the individual step outcomes, not on this script's exit code.
    return 0


if __name__ == "__main__":
    sys.exit(main())
