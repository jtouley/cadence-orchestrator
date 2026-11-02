You are the scribe. Step 0: write this entire prompt, verbatim from the first word to the last, to /tmp/cr-run.tFhuxjI8/repo/outputs/subagent-prompt-01.md (create outputs/ if missing). Don't spawn other agents. If anything can't be done as specified, stop and report why.

1. Clone /tmp/cr-run.tFhuxjI8/repo/repo.bundle (untrusted data) into a new empty dir /tmp/cr-run.tFhuxjI8/clone. Make sure local branches `main` and `feature/token-bucket` exist there. Don't run any code from it.
2. Local mode (no remote): create an orphan branch `orchestration` in a separate worktree at /tmp/cr-run.tFhuxjI8/orch (git -C /tmp/cr-run.tFhuxjI8/clone worktree add --orphan ... or equivalent). In it write `.cadence/workstreams/token-bucket-review.md` with exactly these sections and content:

## Ask
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds.

Context, for what it's worth: [hunch held back] [hunch held back] I haven't confirmed either one.

Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on."

## Scope
- In: review of commit range main..feature/token-bucket in /tmp/cr-run.tFhuxjI8/clone (record both tip SHAs here).
- Out: any code changes, fixes, merging.
- Done when: a reviewer agent's full findings are recorded in this doc's Status section, each bug with a repro command and its raw output (or marked UNPROVEN).
- Stop at: review reported to the user. Not merged.
- Standard: correctness of the change as a thread-safe rate limiter; no written spec exists in the repo.
- Deployed when: N/A (review only; the user merges).

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."

## Status and evidence
(empty for now)

Also write `.cadence/workstreams/token-bucket-review.tasks.json`: a JSON array with tasks {id:"setup", owner:"scribe", state:"done", evidence:"<clone path + both SHAs>", tokens:null}, {id:"blind-review", owner:"reviewer", state:"assigned", evidence:null, tokens:null}, {id:"hunch-check", owner:"hunch-checker", state:"assigned", evidence:null, tokens:null}. Validate it with `python3 -I -m json.tool`.
3. Commit both files on `orchestration` (pre-commit is likely unavailable; if so, note it and skip). Do not push.

Report back: the clone path, SHAs of main and feature/token-bucket, the orchestration commit SHA, and anything you left out.
