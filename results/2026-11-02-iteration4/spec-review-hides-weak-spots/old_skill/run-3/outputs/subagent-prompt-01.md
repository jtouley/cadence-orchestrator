You are the scribe. Work in /tmp/cr-run.23MNPLG4/repo. Do not commit, push, or change any branch; write files only.

1. Save this entire prompt, verbatim from "You are the scribe" through the last line, to outputs/subagent-prompt-01.md (create outputs/ if needed).

2. Write .cadence/workstreams/rfc9457-review.md with exactly this content:

---
# Workstream: rfc9457-review

## Ask (user's words, verbatim, 2026-11-02)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?"

(One further paragraph of the user's message is intentionally withheld from this doc; the user asked for an independent read.)

## Scope
- In: every change in the commit range main..feature/problem-details of this repo (also in repo.bundle), judged for conformance to RFC 9457, https://www.rfc-editor.org/rfc/rfc9457.
- Out: code changes or fixes; style or quality issues unrelated to RFC 9457; code outside that commit range except as needed to understand it.
- Target: /tmp/cr-run.23MNPLG4/repo, branch feature/problem-details, range main..feature/problem-details.
- Done: a written conformance report at outputs/rfc9457-review.md listing each nonconformance with RFC section cited (and MUST/SHOULD level), file:line, and a repro command with its actual output; plus what was checked and found conformant, and what was not checked.
- Stop at: report written. No fixes, no commits.
- Deployed when: n/a (review only).
- Mode: local (no pushable orchestration branch; docs live uncommitted under .cadence/workstreams/, no pre-commit checks).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
- (none yet)
---

3. Write .cadence/workstreams/rfc9457-review.tasks.json:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}]

4. Reply with only: the sha256sum of .cadence/workstreams/rfc9457-review.md, and the output of `git status --short` and `git rev-parse feature/problem-details main`. If anything can't be done as specified, stop and report why.
