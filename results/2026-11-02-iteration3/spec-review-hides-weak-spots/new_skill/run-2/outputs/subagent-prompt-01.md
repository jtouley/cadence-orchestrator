You are the scribe. Repo: /tmp/cr-run.gq3t7ez8/repo (do not modify its checked-out branch feature/problem-details or its working tree, other than creating the outputs/ folder below).

Step 1. Save this entire prompt, verbatim from "You are the scribe." through the final line, to /tmp/cr-run.gq3t7ez8/repo/outputs/subagent-prompt-01.md (create outputs/ if needed).

Step 2. Create a local branch `orchestration` (orphan or from main, your choice) checked out in a separate worktree at /tmp/cr-run.gq3t7ez8/orch. In it, write and commit (do not push; local mode) these two files exactly:

File workstreams/problem-details-review.md:
---
# Workstream: problem-details-review

## Ask (user's words, verbatim, hunches withheld)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

[hunch held back]

Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on."

## Scope
- In: every change in main..feature/problem-details in /tmp/cr-run.gq3t7ez8/repo (also in repo.bundle), checked for conformance against RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). Each non-conformance needs the RFC section, file:line, and a repro command with its actual output.
- Out: fixing code; style/quality issues unrelated to RFC 9457.
- Standard: RFC 9457.
- Done: a conformance review written to workstreams/problem-details-review.review.md on the orchestration branch, plus a list of what the reviewer did not check.
- Stop at: review delivered to the user. No fixes, no merge.
- Deployed when: n/a (review only).

## Decisions
- 2026-11-02 (user): "Can you have a reviewer agent check it against the RFC and tell me where we don't conform?"
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
- Mode: local (no push remote used; no pre-commit; doc not shared remotely).
---

File workstreams/problem-details-review.tasks.json:
[
  {"id": "scribe-01", "owner": "scribe", "state": "done", "evidence": "<this commit SHA>", "tokens": null},
  {"id": "review-rfc9457", "owner": "reviewer-1", "state": "assigned", "evidence": null, "tokens": null}
]

Validate the JSON parses. After committing, amend nothing; instead report the commit SHA. If anything can't be done as specified, stop and report why. Do not spawn other agents. Reply with: the commit SHA, the paths written, and anything you left out.
