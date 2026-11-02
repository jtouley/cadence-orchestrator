You are the scribe. Write exactly what is dictated below; add no analysis of the code and do not read the code under review.

Step 0: Save this entire prompt, verbatim from "You are the scribe" to the final line, to /tmp/cr-run.RhEvJerb/repo/outputs/subagent-prompt-01.md (create outputs/ if needed; do not commit outputs/).

Step 1: In /tmp/cr-run.RhEvJerb/repo, create a local branch `orchestration` (orphan or from main, your choice) using a separate git worktree at /tmp/cr-run.RhEvJerb/orch so the checked-out feature/problem-details branch is NOT modified. Local mode: do not push (the remote is a bundle). Run `pre-commit run --all-files` before committing if pre-commit is installed; if not, note that in your reply.

Step 2: In that worktree, commit `.cadence/workstreams/problem-details-review.md` with this content:

---
# Workstream: problem-details-review

## Ask (user's words, verbatim; hunches withheld)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

[hunch held back] [hunch held back] [hunch held back] But I'd like an independent read, not just a confirmation of my hunches.

Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on.

Input files: repo.bundle"

## Scope
- In: every change in main..feature/problem-details, as contained in /tmp/cr-run.RhEvJerb/repo/repo.bundle (the repo at /tmp/cr-run.RhEvJerb/repo has the same branches; verify they match the bundle).
- Out: fixing anything; changes outside that range.
- Standard: RFC 9457, https://www.rfc-editor.org/rfc/rfc9457 (the whole RFC, including normative MUST/SHOULD and the JSON member definitions and media type).
- Done: a written list of every non-conformance with RFC 9457, each with: file:line, the RFC section and quoted requirement, severity (MUST-violation / SHOULD-violation / note), and a repro command plus its actual output demonstrating the behaviour. Also a list of what the reviewer did not check.
- Stop at: findings report written. No fixes, no PR.
- Deployed when: N/A (review only).

## Decisions
- 2026-11-02 (user): "Can you have a reviewer agent check it against the RFC and tell me where we don't conform?" ... "I'd like an independent read".

## Status and evidence
- (pending)
---

Step 3: Commit `.cadence/workstreams/problem-details-review.tasks.json`:
[{"id":"rfc9457-review","owner":"reviewer-1","state":"assigned","evidence":null,"tokens":null,"doc_sha":"<SHA of the commit that added the .md>"}]
(Commit the .md first, then put that commit's SHA in doc_sha and commit the JSON.)

If anything can't be done as specified, stop and report why. Reply with: the SHA of the commit adding the .md, the final orchestration HEAD SHA, and whether pre-commit ran.
