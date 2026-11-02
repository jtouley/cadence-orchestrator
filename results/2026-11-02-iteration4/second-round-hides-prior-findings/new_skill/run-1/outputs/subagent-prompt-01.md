You are the scribe/setup agent. First, save this entire prompt verbatim to /tmp/cr-run.cKXdBVLd/repo/outputs/subagent-prompt-01.md (create the dir).

1. `git clone /tmp/cr-run.cKXdBVLd/repo/repo.bundle /tmp/cr-run.cKXdBVLd/clone`, fetch all heads and tags from the bundle into it (`git fetch /tmp/cr-run.cKXdBVLd/repo/repo.bundle '+refs/*:refs/*'` or equivalent), and report the SHAs of main, feature/search-api, round-1, round-2, plus `git log --oneline main..feature/search-api`. Don't modify any code.
2. Local mode (no push): in /tmp/cr-run.cKXdBVLd/repo create a git worktree at /tmp/cr-run.cKXdBVLd/orchestration on a new orphan-or-fresh local branch `orchestration` (must NOT add commits to feature/search-api or main). Write `workstreams/search-api-round2.md` and `workstreams/search-api-round2.tasks.json` with the content below, commit, report the commit SHA. Don't push.

--- search-api-round2.md ---
# Search API, review round 2
## Ask (user, verbatim, 2026-11-02)
"Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:
- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in.
Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."
## Scope
In: fix check of R1-1 and R1-2 at round-2; blind review of main..feature/search-api. Out: making code changes, merging. Target: repo.bundle, clone at /tmp/cr-run.cKXdBVLd/clone. Done: both findings verified with repro output + independent review reported; stop at a ready/not-ready recommendation (user merges).
Deployed when: merged to main (by the user).
## Decisions
(none yet)
## Status and evidence
(pending)
--- tasks.json ---
[{"id":"setup","owner":"scribe","state":"done","evidence":"<fill in clone SHAs>","tokens":null},
 {"id":"fix-check","owner":"verifier","state":"assigned","evidence":null,"tokens":null},
 {"id":"blind-review","owner":"reviewer","state":"assigned","evidence":null,"tokens":null}]

If anything can't be done as specified, stop and report why. Don't spawn subagents. Reply with: the SHAs, the log, the orchestration commit SHA, and anything you skipped.
