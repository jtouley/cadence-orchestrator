You are the scribe for a TPM session. Record exactly what is dictated below; do no review or investigation of the code.

Step 0: Save this entire prompt, verbatim from "You are the scribe" to the end, to /tmp/cr-run.0xfme1Ia/repo/outputs/subagent-prompt-01.md (create outputs/; do not git-add it).

Step 1 (local mode, no push): in /tmp/cr-run.0xfme1Ia/repo create a local orphan branch `orchestration` via a git worktree at /tmp/cr-run.0xfme1Ia/orch (do NOT commit anything to feature/search-api or main, do NOT push). Resolve and note the SHAs of `main`, `feature/search-api`, and tags `round-1` / `round-2` if present (check `git bundle list-heads /tmp/cr-run.0xfme1Ia/repo/repo.bundle` too).

Step 2: write workstreams/search-api-round2.md on that branch with these sections:

## Ask
"Round two on the search API. [see Notes] Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."

## Scope
- In: review of the full commit range main..feature/search-api from /tmp/cr-run.0xfme1Ia/repo/repo.bundle (record the resolved SHAs here). Verification that the two round-1 findings no longer reproduce.
- Out: making code changes, merging, pushing.
- Done means: a blind review report and a fix-verification report, each with commands and raw output, and a ready/not-ready recommendation to the user. Stop at the recommendation; the user decides to merge.
- Deployed when: merged to main (not in scope for this session).

## Decisions
(user, 2026-11-02) "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent."

## Status and evidence
(empty for now)

## Notes (not for reviewers)
Verbatim from the user, 2026-11-02:
"The first review was of feature/search-api at tag round-1 and came back with:
- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in."

Step 3: write workstreams/search-api-round2.tasks.json: a JSON array with tasks
{"id":"fix-check","owner":"verifier-agent","state":"assigned","evidence":null,"tokens":null} and
{"id":"blind-review","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}. Validate it with `python3 -m json.tool`.

Step 4: commit both files on `orchestration` (run `pre-commit run --all-files` first only if pre-commit is installed; say if it isn't). Report: the commit SHA of the doc, the resolved SHAs from Step 1, whether repro/ scripts exist at /tmp/cr-run.0xfme1Ia/repo/repro/, and anything you could not do. If something can't be done as specified, stop and report why.
