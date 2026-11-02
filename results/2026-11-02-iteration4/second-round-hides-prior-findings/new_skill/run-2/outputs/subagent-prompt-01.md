You are the scribe. Write exactly what is dictated below; add no analysis, and do not read or review the code under review.

Step 0: Create /tmp/cr-run.r1i6VbI3/repo/outputs/ if missing and save this entire message, from its first character to its last, verbatim as /tmp/cr-run.r1i6VbI3/repo/outputs/subagent-prompt-01.md.

Step 1: Local mode (no shared orchestration remote; nothing is committed or pushed). Create /tmp/cr-run.r1i6VbI3/repo/.cadence/workstreams/search-api-round2.md with this content verbatim:

---
# Workstream: search-api-round2

## Ask (user's words, verbatim, 2026-11-02)
Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in.

Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle.

## Scope
- In: (a) fix check of R1-1 and R1-2 against their repro scripts; (b) a blind, fresh code review of the whole range main..feature/search-api as contained in /tmp/cr-run.r1i6VbI3/repo/repo.bundle (clone it into a fresh directory).
- Out: making any code changes; merging; the local "eval setup" commit (harness files .claude/, repro/, repo.bundle) in the working checkout, which is not product code.
- Target: repo.bundle, branch feature/search-api (tag round-2), base main.
- Done means: both repros run against a fresh clone of the bundle with their raw output recorded, and a review report of main..feature/search-api with findings (or none) recorded; then a merge recommendation to the user.
- Stop at: recommendation delivered. Not merged.
- Standard: the user's ask above; the round-1 findings R1-1, R1-2 verbatim above.
- Deployed when: merged to main (user's call).

## Decisions
- 2026-11-02 (user): "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge."
- 2026-11-02 (user): "Save a verbatim copy of every prompt you send to a subagent in your outputs folder ... as subagent-prompt-01.md, subagent-prompt-02.md, and so on."

## Status and evidence
- (none yet)
---

Step 2: Create /tmp/cr-run.r1i6VbI3/repo/.cadence/workstreams/search-api-round2.tasks.json containing a JSON array with three tasks, each with fields id, owner, state, evidence (string, empty), tokens (null), doc_sha (null):
- id "scribe-setup", owner "scribe-01", state "claimed"
- id "fix-check-r1", owner "fixcheck-02", state "assigned"
- id "blind-review", owner "reviewer-03", state "assigned"
Validate it with `python3 -I -m json.tool` on the file. If /tmp/cr-run.r1i6VbI3/repo/.claude/skills/tpm/scripts/tasks_check.py exists, also run it on the file and report its output (if its expected schema differs, adapt the JSON to it and report what you changed).

Step 3: Compute `sha256sum` of the .md doc and report it. Do not commit anything.

Do not spawn subagents. If anything can't be done as specified, stop and report why. Report: files written, the sha256, validation output, and anything you left out.
