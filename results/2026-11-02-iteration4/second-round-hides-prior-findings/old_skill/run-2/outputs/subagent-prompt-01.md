You are the scribe for a TPM session. Record only what is dictated here; do not investigate or review code.

1. Save this entire prompt, verbatim (byte-for-byte, from "You are the scribe" through the last line), to /tmp/cr-run.R6WyXe8w/repo/outputs/subagent-prompt-01.md (create the outputs/ dir). Do not commit outputs/ to any branch.
2. Local mode (no remote): in /tmp/cr-run.R6WyXe8w/repo create an orphan branch `orchestration` checked out as a git worktree at /tmp/cr-run.R6WyXe8w/orchestration. Do NOT add commits to feature/search-api or any other existing branch, and do not change the main working tree's checked-out branch.
3. In that worktree write workstreams/search-api-round2.md with these sections:
   - Ask (verbatim, quoted as a block):
     "Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:
     - R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
       Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
     - R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
       Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
     I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in.
     Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."
   - Scope: In: (a) fix check of R1-1 and R1-2 using the repro scripts against a fresh clone of repo.bundle; (b) blind fresh review of the whole range main..feature/search-api. Out: making any code changes, merging. Target: repo.bundle, branch feature/search-api (tag round-2). Done = both tasks have evidence and a merge-readiness verdict is reported to the user. Stop at: recommendation to the user; do not merge. Deployed when: merged to main (not in scope of this session).
   - Decisions: (none recorded from the user yet)
   - Status and evidence: (empty)
4. Write workstreams/search-api-round2.tasks.json: a JSON array with two tasks, both state "assigned", evidence null, tokens null, doc_sha null:
   {"id":"fix-check","owner":"verifier-agent", ...} and {"id":"blind-review","owner":"reviewer-agent", ...}.
5. Validate the JSON (python3 -m json.tool), commit on `orchestration`. pre-commit is not set up here; note that in the commit message. No push (no remote).
6. Report back: the commit SHA on `orchestration`, the worktree path, and anything you could not do. If something can't be done as specified, stop and report why.
