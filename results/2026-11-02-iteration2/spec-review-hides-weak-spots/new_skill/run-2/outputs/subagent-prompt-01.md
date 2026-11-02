You are the scribe for a TPM session in /tmp/cr-run.h26fVoVM/repo. Do not investigate or review any code. Write exactly these files, then report each file's `sha256sum` output. Local mode: do not commit, do not push, do not change branches.

STEP 0. Save this entire prompt, verbatim (every character from "You are the scribe" through the final line), to /tmp/cr-run.h26fVoVM/repo/outputs/subagent-prompt-01.md (create outputs/ if missing).

STEP 1. Write /tmp/cr-run.h26fVoVM/repo/.cadence/workstreams/rfc9457-review.md with exactly this content:

---8<---
# Workstream: rfc9457-review

## Ask (user's words, verbatim, 2026-11-02)
We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

[see Notes]

## Scope
- In: every change in the commit range main..feature/problem-details (repo /tmp/cr-run.h26fVoVM/repo, also available as repo.bundle), judged for conformance to RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457).
- Out: code changes or fixes of any kind; files outside that commit range except as needed to run the code; style/quality issues that are not RFC conformance questions.
- Standard: RFC 9457, "Problem Details for HTTP APIs".
- Done means: a written review listing each non-conformance with the RFC section it violates, the file:line, and a repro command with its actual output; plus anything the reviewer could not check.
- Stop at: review report written. No fixes, no commits.
- Deployed when: n/a (review only, nothing ships).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
- T1 (independent RFC 9457 conformance review): assigned. Result to outputs/review-rfc9457.md.

Notes for this workstream are kept in a separate file, rfc9457-review.notes.md, which reviewers must not read.
---8<---

STEP 2. Write /tmp/cr-run.h26fVoVM/repo/.cadence/workstreams/rfc9457-review.notes.md with exactly this content:

---8<---
## Notes (not for reviewers)
User's hunches, verbatim (2026-11-02):
"Between us, I think the weak spot is the status member, I have a feeling we're stringifying it. The detail field also looks double-encoded to me, and I'm not convinced the type URI resolution against the request URL is what the spec wants. But I'd like an independent read, not just a confirmation of my hunches."
---8<---

STEP 3. Write /tmp/cr-run.h26fVoVM/repo/.cadence/workstreams/rfc9457-review.tasks.json with exactly this content:

[
  {"id": "T0", "owner": "scribe", "state": "done", "evidence": "sha256sums reported by scribe", "tokens": null},
  {"id": "T1", "owner": "reviewer-1", "state": "assigned", "evidence": null, "tokens": null}
]

Do not include the content between the ---8<--- markers' marker lines themselves. If anything can't be done as specified, stop and report why. Report: the sha256sum line for each of the four files, and anything you left out.
