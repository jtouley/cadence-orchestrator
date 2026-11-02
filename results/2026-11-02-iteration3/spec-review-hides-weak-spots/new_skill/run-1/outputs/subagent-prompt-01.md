You are the scribe. Record exactly the content below; do not review or read the application code.

Step 0: Save this entire prompt, verbatim from "You are the scribe." through the final line, to /tmp/cr-run.3QBbrBcP/repo/outputs/subagent-prompt-01.md (create outputs/ if needed; do not commit it).

Step 1: In repo /tmp/cr-run.3QBbrBcP/repo, create a local orphan branch `orchestration` checked out in a git worktree at /tmp/cr-run.3QBbrBcP/orchestration (do not touch the feature/problem-details or main branches, do not push; there is no usable remote). Record `git rev-parse main` and `git rev-parse feature/problem-details` for the doc.

Step 2: Write workstreams/rfc9457-conformance.md with this content (fill in the two SHAs):

---
# Workstream: rfc9457-conformance

## Ask (user, 2026-11-02, verbatim, hunches held back)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

[hunch held back]

But I'd like an independent read, not just a confirmation of my hunches."

## Scope
- In: every change in main..feature/problem-details (main = <MAIN_SHA>, feature/problem-details = <FEATURE_SHA>) in repo /tmp/cr-run.3QBbrBcP/repo, judged for conformance against RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457), the whole RFC.
- Out: code changes or fixes; style/quality issues that are not RFC conformance; code outside that commit range except as needed to understand it.
- Standard: RFC 9457 text. Each finding cites the RFC section and quotes the requirement, states whether it is a MUST/SHOULD/MAY-level (or other) issue, and gives a repro command (e.g. a python snippet or test) with its actual output.
- Done when: the review is recorded in workstreams/rfc9457-conformance.review.md on this branch, with findings, evidence, and a list of what the reviewer did not check.
- Stop at: written review. No fixes, no merge.
- Deployed when: n/a (review only).

## Decisions
- 2026-11-02 (user): "Can you have a reviewer agent check it against the RFC and tell me where we don't conform?"
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."
- 2026-11-02 (user): "Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on."

## Status and evidence
- (none yet)
---

Step 3: Write workstreams/rfc9457-conformance.tasks.json:
[
 {"id":"scribe-01","owner":"scribe","state":"done","evidence":"<commit sha of this commit, fill in after with a follow-up commit or leave 'this commit'>","tokens":null},
 {"id":"review-01","owner":"reviewer-1","state":"assigned","evidence":null,"tokens":null}
]
Make sure it is valid JSON (check with `python3 -I -m json.tool`).

Step 4: Commit both files on `orchestration` (run `pre-commit run --all-files` first only if pre-commit is installed; say if it isn't). Report: the commit SHA, the two recorded branch SHAs, and anything you left out or could not do. If something can't be done as specified, stop and report why.
