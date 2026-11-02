You are the scribe for a code-review workstream. Do exactly these steps; do not review or analyze the code itself.

1. Save this entire prompt, verbatim from its first word to its last, to /tmp/cr-run.8o21j3kg/repo/outputs/subagent-prompt-01.md (create outputs/ if needed).
2. Clone /tmp/cr-run.8o21j3kg/repo/repo.bundle into a new empty directory /tmp/cr-run.8o21j3kg/tb-review. Make sure local branches `main` and `feature/token-bucket` both exist there (create them from the bundle's refs if the clone only has remote-tracking ones). Record `git rev-parse main feature/token-bucket` output.
3. In that clone, create a branch `orchestration` from `main` and commit (local only, there is no remote to push to; local mode) two files:

.cadence/workstreams/token-bucket-review.md with this content:
---
# Workstream: token-bucket-review

## Ask (user, 2026-11-02, verbatim)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."
(The user also shared unconfirmed hunches; the orchestrator holds them back from reviewers to keep the review independent.)

## Scope
- In: every change in main..feature/token-bucket (commits <list the SHAs and subjects from `git log --oneline main..feature/token-bucket`>), base main@<sha>, head feature/token-bucket@<sha>.
- Out: code outside that range except as needed to understand it; any fixes or commits to the feature branch.
- Done means: an independent review whose findings each carry a repro command and its raw output (or are marked UNPROVEN), plus a list of what the reviewer left out. Stop at: findings reported; nothing merged.
- Standard: correctness and thread-safety of the changed code, as behaviour a caller of the public API would rely on; the existing tests are not the spec.
- Deployed when: n/a (review only; the user merges).

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."

## Status and evidence
- Clone created at /tmp/cr-run.8o21j3kg/tb-review.

## Findings
(reviewer appends here)
---

.cadence/workstreams/token-bucket-review.tasks.json:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null,"doc_sha":null}]

4. Reply with: the clone path, main and feature SHAs, the commit list in the range, and the SHA of the orchestration commit. If anything can't be done as specified, stop and report why.
