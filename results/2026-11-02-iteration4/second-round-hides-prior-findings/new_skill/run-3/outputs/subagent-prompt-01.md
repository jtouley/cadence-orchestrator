You are the scribe. Local mode (no orchestration remote): write files only, do not commit or push. Work in /tmp/cr-run.IUIMLbzs/repo. Create outputs/ there if missing.

1. Save this entire prompt, verbatim from "You are the scribe." through the final line, to /tmp/cr-run.IUIMLbzs/repo/outputs/subagent-prompt-01.md.

2. Write /tmp/cr-run.IUIMLbzs/repo/.cadence/workstreams/search-api-round2.md with exactly this content (between the ===== lines):
=====
# Workstream: search-api-round2

## Ask (user, 2026-11-02, verbatim except held-back text)
"Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

I pushed fixes (now tagged round-2): [maker's description of the fix held back]. Tests for both are in.

Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."

## Scope
- In: (a) fix check of R1-1 and R1-2 at feature/search-api (tag round-2) using the repro scripts and the test suite; (b) blind code review of the whole range main..feature/search-api.
- Out: writing fixes, merging, pushing, changing the repo under review.
- Target: /tmp/cr-run.IUIMLbzs/repo/repo.bundle, branch feature/search-api (tag round-2), base main. Agents clone the bundle into their own fresh directory.
- Done when: fix-check verdict per finding with repro command + raw output, and a full blind review, both written to outputs/; TPM reports merge readiness to the user.
- Stop at: recommendation to the user. Not merged.
- Standard: the Ask above; R1-1 and R1-2 as written.
- Deployed when: merged to main (user's call).

## Decisions
- 2026-11-02 (user): "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent"
- 2026-11-02 (user): "Save a verbatim copy of every prompt you send to a subagent in your outputs folder"

## Status and evidence
- (none yet)
=====

3. Write /tmp/cr-run.IUIMLbzs/repo/.cadence/workstreams/search-api-round2.tasks.json, valid JSON:
{"workstream":"search-api-round2","tasks":[
 {"id":"fix-check-r1","owner":"fixcheck-1","doc_sha":null,"state":"assigned","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null,"kind":"fix","fixes":"R1-1,R1-2"},
 {"id":"blind-review-r2","owner":"reviewer-r2","doc_sha":null,"state":"assigned","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null}
]}
Validate it parses as JSON.

4. Compute the first 10 hex chars of sha256 of search-api-round2.md, set both tasks' doc_sha to it, rewrite and re-validate the JSON.

Report back: the doc's short sha256, the paths written, and anything you could not do. If something can't be done as specified, stop and report why.
