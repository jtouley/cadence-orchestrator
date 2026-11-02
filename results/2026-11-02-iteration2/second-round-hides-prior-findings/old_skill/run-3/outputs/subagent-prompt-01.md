You are the scribe/setup agent for a review round. Do only what is listed; don't review or analyse the code. If any step can't be done, stop and report why.

1. Create /tmp/cr-run.UrOA8FEV/repo/outputs/ and save this entire prompt, verbatim, as outputs/subagent-prompt-01.md.
2. Clone /tmp/cr-run.UrOA8FEV/repo/repo.bundle into a new directory /tmp/cr-run.UrOA8FEV/clone (fetch all branches and tags from the bundle). Report: every ref in the bundle with its SHA; whether a `main` branch exists; whether tags round-1 and round-2 exist and their SHAs; whether round-2 equals the tip of feature/search-api; `git log --oneline main..feature/search-api` (or note if main is missing and what the merge base would be).
3. Local mode (no remote): write /tmp/cr-run.UrOA8FEV/repo/.cadence/workstreams/search-api-round2.md and search-api-round2.tasks.json, don't commit. Doc contents:
   - Ask (verbatim): "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge."
   - Round-1 findings (user's words, verbatim): 
     "R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1. Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)"
     "R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching \"100%\" also matches \"1000 done\". Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)"
   - Scope: in = fix check of R1-1/R1-2 and a blind review of main..feature/search-api at the SHA from step 2; out = making any code changes. Done = both results recorded with commands and output; stop at a merge recommendation to the user, not merging. Deployed when: merged to main (by the user).
   - Tasks JSON: T1 fix-check (owner: verifier agent, state assigned), T2 blind review (owner: reviewer agent, state assigned), evidence empty, tokens null.
Report the refs/SHAs and the paths you wrote.
