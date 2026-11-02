You are the scribe. Work in /tmp/cr-run.4ESX4jKb/repo. Local mode (no orchestration remote): write files, do not commit or push, do not touch any git branch.

1. Save this entire prompt, verbatim, character for character, to outputs/subagent-prompt-01.md (create outputs/).
2. Clone repo.bundle into a fresh empty dir /tmp/cr-run.4ESX4jKb/scribe-clone (`git clone repo.bundle <dir>`), and record the SHAs of tags round-1 and round-2, branch feature/search-api, and main (use `git ls-remote repo.bundle`).
3. Write .cadence/workstreams/search-api-round-2.md with these sections:
   - Ask (verbatim): the text between the BEGIN/END markers below.
   - Scope: in = fix check of R1-1 and R1-2 at round-2 using the repro scripts; blind code review of the whole range main..feature/search-api from repo.bundle. Out = making any code changes, merging. Target: repo.bundle, branch feature/search-api, tag round-2 (fill in the SHAs). Done = fix-check verdicts with repro output + review written to outputs/; TPM gives the user a merge/no-merge recommendation. Stop at: recommendation, not merged. Deployed when: merged to main by the user.
   - Decisions: "2026-11-02, user: review the whole branch main..feature/search-api with a fresh reviewer agent; report whether ready to merge." and "2026-11-02, user: save a verbatim copy of every subagent prompt in outputs/ as subagent-prompt-NN.md."
   - Status and evidence: empty for now.
4. Write .cadence/workstreams/search-api-round-2.tasks.json: a JSON array with tasks {"id":"T1-fix-check","owner":"verifier-agent","state":"assigned","evidence":null,"tokens":null} and {"id":"T2-blind-review","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}. Validate with `python3 -I -m json.tool`.
5. Reply with: the SHAs, and `sha256sum` of the .md doc. If anything can't be done, stop and report why.

BEGIN ASK
Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with:

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

I pushed fixes (now tagged round-2): replaced the offset cursor with keyset pagination on (created_at, id) with an id tie-breaker, and added an escape_like() helper plus ESCAPE '\\' on both queries. Tests for both are in.

Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle.

Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on.

Input files: repo.bundle, repro/r1_1_cursor_gap.py, repro/r1_2_like_wildcard.py
END ASK
