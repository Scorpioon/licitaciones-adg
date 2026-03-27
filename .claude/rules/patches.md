# Patches / direct-change rules

## General
- Prefer direct repo edits in Claude Code when explicitly approved.
- If patch mode is requested, return exactly one `.ps1` unless the task truly requires more.
- No loose snippets when patch mode is requested.

## Patch requirements
- Self-contained
- Clear OK / WARN / ERROR logging
- File existence checks before writes
- Backups before destructive actions when appropriate
- Minimal scope only
- No unrelated cleanup outside approved phase

## Safety
- Do not delete files unless the audit has already confirmed they are orphaned or approved for removal.
- Do not change workflow/fetcher/UI in the same patch unless that combined scope was explicitly approved.
- Keep patches idempotent where practical, or at least safe for a single run with clear messages.

## Validation
Every implementation response should include:
- Expected visible changes
- Key features to check
- What to do next
