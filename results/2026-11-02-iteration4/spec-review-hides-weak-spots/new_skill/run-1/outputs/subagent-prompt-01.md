You are the scribe. Step 0: save this entire prompt, verbatim and unmodified, to /tmp/cr-run.HCTyclmI/repo/outputs/subagent-prompt-01.md (create the dir).

Local mode (do not push anywhere). In /tmp/cr-run.HCTyclmI/repo, create a local branch `orchestration` via `git worktree add` at /tmp/cr-run.HCTyclmI/orchestration (orphan branch is fine; do NOT touch the feature/problem-details or main branches). In it, write and commit two files exactly as dictated below, then report the commit SHA. If pre-commit is available run `pre-commit run --all-files` first; if not, say so. If anything blocks you, stop and report why.

File `workstreams/rfc9457-review.md`:
---
# Workstream: rfc9457-review

## Ask (user's words, verbatim; hunches withheld)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

Between us, [hunch held back]. [hunch held back] [hunch held back] But I'd like an independent read, not just a confirmation of my hunches.

Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on.

Input files: repo.bundle"

## Scope
- In: every change in main..feature/problem-details (repo at /tmp/cr-run.HCTyclmI/repo; repo.bundle is the same history). Check conformance against RFC 9457, https://www.rfc-editor.org/rfc/rfc9457 (the standard).
- Out: making fixes; style/quality issues unrelated to RFC conformance.
- Done: a written list of every non-conformance, each citing the RFC section, the code location, and a repro command with its actual output; plus what the reviewer did not check.
- Stop at: findings report. No code changes, no commits to feature/problem-details or main.
- Deployed when: n/a (review only).

## Decisions
- 2026-11-02 (user): "Can you have a reviewer agent check it against the RFC and tell me where we don't conform?" / "I'd like an independent read".

## Status and evidence
- (pending)
---

File `workstreams/rfc9457-review.tasks.json`:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null,"doc_sha":null}]

Report: the commit SHA, file paths, and anything you skipped.
