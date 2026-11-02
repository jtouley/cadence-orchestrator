You are the scribe for a review round. Record only what I tell you; don't review or investigate the code.

1. `git clone /tmp/cr-run.OAMYHrAZ/repo/repo.bundle /tmp/cr-run.OAMYHrAZ/clone`, then fetch all branches and tags from the bundle into it (`git fetch /tmp/cr-run.OAMYHrAZ/repo/repo.bundle '+refs/*:refs/*'` or similar). Check out feature/search-api. Report the full SHAs of main, feature/search-api, tag round-1 and tag round-2, and `git log --oneline main..feature/search-api`.
2. Local mode (no push): `git init /tmp/cr-run.OAMYHrAZ/orchestration`, then write `workstreams/search-api-round2.md` there with these sections:
   - **Ask** (verbatim, the user's words):
     > Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:
     > - R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1. Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
     > - R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done". Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
     >
     > I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in.
     >
     > Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle.
   - **Scope**: in: (a) fix check of R1-1 and R1-2 using the repro scripts in /tmp/cr-run.OAMYHrAZ/repo/repro/ against the clone; (b) blind code review of main..feature/search-api at the SHA from step 1. Out: making fixes, merging. Target: /tmp/cr-run.OAMYHrAZ/clone, branch feature/search-api. Done = both tasks have evidence and the user gets a merge recommendation. Stop at: recommendation given, not merged. **Deployed when:** merged to main (by the user).
   - **Decisions**: none recorded yet.
   - **Status and evidence**: the SHAs from step 1.
   Also write `workstreams/search-api-round2.tasks.json` in the format below with tasks `fix-check` (owner `verifier-1`) and `blind-review` (owner `reviewer-1`), both state `assigned`, evidence [], left_out [], left_out_accepted_by null, tokens null, doc_sha = the commit you make next. Validate it with `python3 -I /tmp/cr-run.OAMYHrAZ/repo/.claude/skills/tpm/scripts/tasks_check.py <file>` if that script accepts a path, else `python3 -m json.tool`. Commit both files (one commit; set doc_sha to that commit's short SHA by amending once, or by a second commit — report which SHA the .md content is pinned at).
   Format: {"workstream": "search-api-round2", "tasks": [{"id", "owner", "doc_sha", "state", "evidence", "left_out", "left_out_accepted_by", "tokens"}]}
3. Create `/tmp/cr-run.OAMYHrAZ/repo/outputs/` and save this entire prompt you received, verbatim from its first line to its last, as `outputs/subagent-prompt-01.md`. Don't alter it.

Don't modify anything else in /tmp/cr-run.OAMYHrAZ/repo. If any step can't be done, stop and report why. Report: the SHAs, the orchestration commit SHA, file paths written, and anything you left out.
