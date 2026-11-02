You are the scribe. First, save this entire prompt, verbatim from "You are the scribe." to the end, to /tmp/cr-run.hszGdFxu/repo/outputs/subagent-prompt-01.md (create the outputs/ dir if needed).

Then, in local mode (no remote push): in the git repo /tmp/cr-run.hszGdFxu/repo, create a local orphan branch `orchestration` checked out as a git worktree at /tmp/cr-run.hszGdFxu/orchestration (do not change the checkout of /tmp/cr-run.hszGdFxu/repo). In that worktree write the two files below exactly, validate the JSON with `python3 -I /tmp/cr-run.hszGdFxu/repo/.claude/skills/tpm/scripts/tasks_check.py workstreams/search-api-round2.tasks.json` (if that script's CLI differs, read its usage and run it correctly; at minimum `python3 -I -m json.tool`), commit both as "Add search-api-round2 workstream", and do not push. Report the commit SHA and the validation command + output. If anything can't be done as specified, stop and report why. Do not spawn other agents.

File 1: workstreams/search-api-round2.md
---
# Search API, round 2 review
## Ask
User, 2026-11-02, verbatim: "Round two on the search API. [see Notes] Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."
## Scope
In: the commit range main..feature/search-api as shipped in /tmp/cr-run.hszGdFxu/repo/repo.bundle, pinned to tag round-2 = 6746708 (base main = 6a70bbd). Out: the local "eval setup" commit 5ec1bcf (harness files, not part of the user's branch); making any fixes. Target repo: the clone of repo.bundle; branch feature/search-api.
Done: (a) a fix check of each round-1 finding against its repro command, with output; (b) a fresh, independent code review of main..6746708 with findings written down; (c) a merge-readiness verdict reported to the user. Stop at: verdict reported, nothing merged.
Judged against: correctness of the search API as built (no separate spec document exists in the repo).
Deployed when: merged to main (not in scope for this workstream).
## Decisions
- 2026-11-02, user: "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent"
## Status and evidence
- (pending)
## Notes (not for reviewers)
- From the ask, user, verbatim: "The first review was of feature/search-api at tag round-1 and came back with:
  - R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
    Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
  - R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching \"100%\" also matches \"1000 done\".
    Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
  I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\\\' on both queries. Tests for both are in."
---

File 2: workstreams/search-api-round2.tasks.json
---
{
  "workstream": "search-api-round2",
  "tasks": [
    {"id": "fix-check-r1", "owner": "verifier-1", "doc_sha": null, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null, "tokens": null},
    {"id": "blind-review", "owner": "reviewer-1", "doc_sha": null, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null, "tokens": null}
  ]
}
---
(In the .md, the four backslashes in ESCAPE '\\\\' above are JSON-free plain text: write it as ESCAPE '\\' — two backslashes — matching the user's original message.)
