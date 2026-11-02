You are the scribe for a TPM session. First, save this entire prompt verbatim (every line, unchanged) to /tmp/cr-run.VICTq7he/repo/outputs/subagent-prompt-01.md (create the folder).

Setup (local mode, no pushing):
1. Clone /tmp/cr-run.VICTq7he/repo/repo.bundle into a new empty dir /tmp/cr-run.VICTq7he/clone (git clone the bundle; create local branches main and feature/search-api from it and fetch its tags). Report the SHAs of main, feature/search-api, tag round-1 and tag round-2, and `git log --oneline main..feature/search-api`. Don't read or judge the code.
2. In /tmp/cr-run.VICTq7he/repo, create an orphan local branch `orchestration` via `git worktree add` at /tmp/cr-run.VICTq7he/orchestration (do not touch the repo's current checkout). Commit there the two files below. Do not push. pre-commit is not set up; skip it and say so.

File workstreams/search-api-round-2.md, exactly this content, with <...> filled from step 1:

# Search API: round-2 review
## Ask
"Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with: [see Notes]

I pushed fixes (now tagged round-2): [see Notes] Tests for both are in.

Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."
## Scope
In: every commit in main..feature/search-api (main=<sha>, feature/search-api=<sha>, round-2=<sha>), clone at /tmp/cr-run.VICTq7he/clone. Out: changing code; merging. Done: the round-1 findings re-checked with their repro commands, a fresh blind review of the whole range written to outputs/, and a merge-readiness verdict reported to the user. Stop at: report to user, not merged.
Judged against: the Ask above and general correctness (no separate spec exists in the repo).
Deployed when: feature/search-api merged to main (user's call).
## Decisions
- 2026-11-02, user: "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent"
## Status and evidence
- Clone from repo.bundle: <SHAs from step 1>
## Notes (not for reviewers)
- From the ask, user, round-1 findings: "- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)"
- From the ask, user, fixes: "replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries."

File workstreams/search-api-round-2.tasks.json (valid JSON; validate it): workstream "search-api-round-2", tasks:
- id "fix-check", owner "verifier-1", state "assigned", doc_sha null, evidence [], left_out [], left_out_accepted_by null, tokens null
- id "blind-review", owner "reviewer-1", same fields.

3. After committing, set doc_sha on both tasks to the commit SHA of the doc, commit again.

Reply with: the step-1 SHAs and log, the doc's commit SHA, the final orchestration HEAD SHA, and anything you couldn't do. If something can't be done as specified, stop and report why.
