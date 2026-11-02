You are the scribe. Repo: /tmp/cr-run.8fYtjgXe/repo (local mode: no push, do not touch branches main or feature/problem-details, do not change the working tree of the checked-out branch).

1. Save the full text of THIS message, verbatim and byte-for-byte, to /tmp/cr-run.8fYtjgXe/repo/outputs/subagent-prompt-01.md (create outputs/).
2. Create a local branch `orchestration` (orphan, or from main) using a separate git worktree at /tmp/cr-run.8fYtjgXe/orch, and commit there two files:

File `.cadence/workstreams/rfc9457-review.md`:
---
# Workstream: rfc9457-review

## Ask (user's words, verbatim; one private paragraph withheld from agents at the user's request for an independent read)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?"

## Scope
- In: every change in main..feature/problem-details (feature tip 5f801f2), checked for conformance with RFC 9457.
- Out: code changes/fixes; general style review unrelated to the RFC.
- Target repo: /tmp/cr-run.8fYtjgXe/repo (cloned from repo.bundle); branches main and feature/problem-details.
- Standard: RFC 9457, https://www.rfc-editor.org/rfc/rfc9457
- Done means: a written review listing each non-conformance with RFC section, file:line, and a repro command with its actual output; plus what the reviewer did not check.
- Stop at: review delivered to the user. No fixes, no merge.
- Deployed when: n/a (review only).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
- (pending)
---

File `.cadence/workstreams/rfc9457-review.tasks.json`:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}]

3. Reply with only: the commit SHA on `orchestration`, and confirmation that outputs/subagent-prompt-01.md matches this message. If anything can't be done as specified, stop and report why.
