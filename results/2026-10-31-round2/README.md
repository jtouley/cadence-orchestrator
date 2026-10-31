# Round 2, 2026-10-31: INVALID (recorded, not evidence)

A copy of coffee-data-tracker `.claude/skills/tpm-workspace/iteration-2/` as the runner left it: transcripts and
run outputs, including patches of the shared branches in each run's `outputs/`. It was not graded,
and it must not be graded or cited as evidence about the skill, in either direction. It is kept so the failures
can be inspected.

Why it is invalid (facts from the runner; where noted, also visible in the files):
- **Stale skill.** The runs used the skill at commit 8f6f9bd (`worktree_setup.log`), which main had already
  superseded.
- **build-finish-bag-screen/with_skill is incomplete.** The child sessions inherited
  `CLAUDE_AUTO_BACKGROUND_TASKS=true`, so the Agent calls ran in the background. `claude -p` then stopped them at
  its 10-minute background-wait ceiling (`stderr.log`: "Background tasks still running 10m after the last turn
  (subagent "Implement finish-bag"); stopping them."). No reviewer ran.
- **build-finish-bag-screen/without_skill hit the 3600 s run timeout** after answering (`exit_code` 124,
  `wall_ms` 3602041).
- **Runs were not isolated.** Each run was a `git worktree` of one repo, so the with_skill subagents shared branches
  (`orchestration` and `feature/finish-bag`) and one run's commit landed on top of another's. The `orchestration`
  here is a branch of coffee-data-tracker, not this branch.

`evals/README.md` on main, under "Runner requirements", says what a valid run needs. Round 3 reruns the same 3
cases under those requirements, at the current main.

Integrity: `results/SHA256SUMS` covers this folder.

**Prepared for publishing (2026-10-31).** The `session_log/` directories, the raw per-session logs including
subagent logs, were removed before publishing. Every `transcript.jsonl`, run output and grading file is kept. Email
addresses were replaced with `<redacted>` where they appeared: the `Co-Authored-By` trailer address in commit
messages and briefs, in `build-finish-bag-screen/with_skill/{transcript.jsonl, outputs/01-brief-scribe.md}` and
`tempting-quick-ratio-fix/with_skill/transcript.jsonl`. Redacted JSONL lines were re-serialized from their parsed values, and the JSON
stays valid. No other user identifiers or credentials were found (see the scan in the commit message). These files
therefore no longer match the source workspace byte for byte. `SHA256SUMS` covers the published files.
