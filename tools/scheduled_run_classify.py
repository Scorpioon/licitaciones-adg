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
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORT_SCHEMA = "ADGOPS_SCHEDULED_RUN_REPORT_V1"
REPORT_VERSION = "1.0"
WORKFLOW_NAME = "Fetch Licitaciones Scheduled Safe Merge"

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
    if cand_partial is True and "success" not in cand_run_status.lower():
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
                  github_env: str | None = None) -> None:
    """
    Write the markdown summary to $GITHUB_STEP_SUMMARY (if set), append
    OPERATIONAL_STATUS to $GITHUB_ENV (if set), and write the machine-readable
    report JSON to <tmp_dir>/scheduled_run_report_<run>.json.
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
    )

    print(render_summary(result))
    print(f"OPERATIONAL_STATUS={result['status']}")
    # Preserve heredoc behaviour: the classifier never exits non-zero. The workflow
    # relies on the individual step outcomes, not on this script's exit code.
    return 0


if __name__ == "__main__":
    sys.exit(main())
