You are the scribe. Work in /tmp/cr-run.t8cHjpMu/repo. Do not modify code, do not commit, do not spawn agents. If anything below can't be done, stop and report why.

1. Save this entire prompt you are reading, verbatim from "You are the scribe." to the end, as outputs/subagent-prompt-01.md (create outputs/).

2. Save the text between the markers PROMPT-02-START / PROMPT-02-END below, verbatim (excluding the marker lines), as outputs/subagent-prompt-02.md, and the text between PROMPT-03-START / PROMPT-03-END as outputs/subagent-prompt-03.md.

3. Write .cadence/workstreams/search-api-round-2.md (local mode: not pushed) with sections:
- Ask (verbatim): "Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:\n\n- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.\n  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)\n- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching \"100%\" also matches \"1000 done\".\n  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)\n\nI pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\\\' on both queries. Tests for both are in.\n\nPlease get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."
- Scope: in = fix check of R1-1 and R1-2 at round-2, and a blind review of main..feature/search-api from repo.bundle. Out = making code changes, merging. Done = both reports back with command output; stop at a merge recommendation to the user, not a merge. Deployed when: merged to main (user's call).
- Decisions: 2026-11-02 (user): "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent".
- Mode: local mode, no remote; no shared orchestration branch, no pre-commit.
- Status and evidence: empty for now.
Also write .cadence/workstreams/search-api-round-2.tasks.json: a JSON array with tasks {"id":"fix-check","owner":"verifier-agent","state":"assigned","evidence":null,"tokens":null,"prompt":"outputs/subagent-prompt-02.md"} and {"id":"blind-review","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null,"prompt":"outputs/subagent-prompt-03.md"}. Validate it with python -m json.tool.

4. Report the paths written and `git hash-object` of the workstream doc.

PROMPT-02-START
Fix check, no code changes, don't spawn agents. Clone /tmp/cr-run.t8cHjpMu/repo/repo.bundle into a fresh empty directory. For each finding below, run its repro (the scripts are in /tmp/cr-run.t8cHjpMu/repo/repro/; run them with `python -I`) against the clone checked out at tag round-1, at tag round-2, and at the tip of feature/search-api, and run the project's test suite at round-2 and at the tip. Judge only these findings: for each, give FIXED or NOT FIXED with the exact commands and raw output. Also report whether round-2 and the feature/search-api tip differ (and the diff if so), and anything you skipped or couldn't run. If it can't be done as specified, stop and report why.

Findings, verbatim from the round-1 review:
- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
PROMPT-02-END

PROMPT-03-START
/code-review high on main..feature/search-api, in a fresh clone of /tmp/cr-run.t8cHjpMu/repo/repo.bundle in a new empty directory (work only inside that clone). Return the full review: each finding with severity, file:line and evidence (a command and its output where you can run one), plus what you didn't cover. Don't modify the code and don't spawn agents; if it can't be done, stop and report why.
PROMPT-03-END
