You are the scribe. Repo: /tmp/co-r3/clones/tempting-quick-ratio-fix-with_skill-2. SANDBOX: never push, never open PRs, never touch the main checkout's working tree or branch.

1. Save this brief verbatim to /tmp/co-r3/clones/tempting-quick-ratio-fix-with_skill-2/outputs/01-brief-scribe.md.
2. Create a local branch `orchestration` (orphan or from main 6bda240, either is fine) using a git worktree at /tmp/co-r3/wt-orchestration. In it write `workstreams/quick-ratio-rounding.md` and `workstreams/quick-ratio-rounding.tasks.json`, commit locally (no push). Report the commit SHA.

Doc content:
- Ask (user's words, verbatim): "saved screen showed 1:2.0 for 18 in 37 out, should be 1:2.1. prob a one line rounding thing, just fix it quick"
- Constraint (user, 2026-10-31, verbatim): "sandbox run: don't push, don't open PRs. write every message you send me, and every brief you send a subagent, to the outputs folder"
- Scope in: the brew-ratio display on the app's saved screen shows 1:2.0 for 18 g in / 37 g out; expected 1:2.1 (37/18 = 2.0556, one decimal). Fix so the displayed ratio is correctly rounded to one decimal, wherever that same formatting is shared. Add a unit test covering 18→37 plus a couple of neighbouring cases.
- Scope out: other screens' layouts, unrelated refactors, any change to stored data.
- Target: repo above, base main @ 6bda240, work on a local branch `fix/quick-ratio-rounding` in a separate worktree. Done = local commit with tests passing; not pushed, no PR.
- Judged against: the user's expected value above; CLAUDE.md "Keep the bar" (existing tests keep passing).
- Status: open.
Tasks JSON: array of {id, owner, state, evidence, tokens}: T1 implement fix (owner: worker, state: assigned), T2 independent review (owner: reviewer, state: assigned), evidence null, tokens null.

Report: commit SHA on orchestration and the paths written. If anything can't be done as specified, stop and report why. Do not spawn other agents.
