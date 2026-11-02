You are the scribe. First, save this entire prompt verbatim to /tmp/cr-run.tARSGHsD/repo/outputs/subagent-prompt-01.md (create the folder). Then, in local mode (no push, no commit), write /tmp/cr-run.tARSGHsD/repo/.cadence/workstreams/search-api-round2.md and search-api-round2.tasks.json with: Ask (verbatim, below), Scope (review main..feature/search-api from /tmp/cr-run.tARSGHsD/repo/repo.bundle; done = fix-check + blind review reported; stop at a merge recommendation, no merge; Deployed when: merged to main), tasks T1 fix-check (owner: verifier agent, state assigned) and T2 blind review of main..feature/search-api (owner: reviewer agent, state assigned). Also run `git bundle list-heads` on the bundle and report the refs and SHAs (main, feature/search-api, tags round-1, round-2) in the doc and in your reply. If something can't be done, stop and report why. Don't spawn agents.

Ask (verbatim):
"""
Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in.

Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle.
"""
