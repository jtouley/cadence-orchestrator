You are the scribe. Repo: /tmp/co-r3/clones/ambiguous-grind-advice-in-app-with_skill-2. Sandbox run: never push, never open PRs.

1. Create a local branch `orchestration` (from main) in a separate git worktree at /tmp/co-r3/clones/ambiguous-grind-advice-in-app-with_skill-2-orch (don't touch the main checkout's branch or its uncommitted .gitignore change). Commit there, locally only.
2. In it write `workstreams/grind-advice.md` with exactly these sections:
   - **Ask** (user's words, verbatim, 2026-10-31): "can the app tell me what to change after a shot? like the cli does"
   - **Scope**: Phase 1 = investigation only, no code changes: what post-shot advice the CLI gives (inputs, rules, where the logic lives), whether the app already offers anything like it, and what it would take to expose it in the app. Out: any implementation, until the user decides. Target repo: this one, base `main` at the current commit SHA (record it). Done for phase 1 = findings appended to this doc with repro commands and their output. Stop: no push, no PR (sandbox run). Judged against: CLAUDE.md (note its "heuristics are measured, not argued" section applies if advice rules change).
   - **Decisions**: "none yet".
   - **Status and evidence**: empty.
3. Write `workstreams/grind-advice.tasks.json`: [{"id":"investigate","owner":"investigator-1","state":"assigned","evidence":null,"tokens":null,"doc_sha":null}].
4. Commit, then set doc_sha to that commit's SHA and commit again.
5. Also write, in /tmp/co-r3/clones/ambiguous-grind-advice-in-app-with_skill-2/outputs/, the file `01-brief-scribe.md` containing this entire prompt verbatim (the outputs folder is a log of every brief and message).
Report: the worktree path, branch, both commit SHAs, and anything you skipped.
