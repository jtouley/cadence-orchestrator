You are the scribe for a TPM session in /tmp/cr-run.gJziX0MU/repo. Do only the following; do not review or read the application code.

1. Save this entire message, verbatim from "You are the scribe" to the final line, to /tmp/cr-run.gJziX0MU/repo/outputs/subagent-prompt-01.md (create outputs/; do not commit outputs/).

2. Create a workstream doc. Try the shared mode first: create an orphan-or-new branch `orchestration` in a separate git worktree (e.g. /tmp/cr-run.gJziX0MU/orch), add `workstreams/rfc9457-review.md` and `workstreams/rfc9457-review.tasks.json`, commit, and `git push origin orchestration` (if rejected, rebase and retry; run `pre-commit run --all-files` first if pre-commit is available). If pushing is impossible, keep the commit local on the `orchestration` branch and say so. Do not modify feature/problem-details or main.

Doc content (copy the quoted text exactly):

# rfc9457-review

## Ask
(user's words, verbatim, 2026-11-02)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

[see Notes] But I'd like an independent read, not just a confirmation of my hunches."

## Scope
- In: every change in the commit range main..feature/problem-details (repo at /tmp/cr-run.gJziX0MU/repo, cloned from repo.bundle), checked for conformance with RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457) — the standard the work is judged against.
- Out: fixing code; anything outside that commit range; style/quality review not tied to RFC conformance.
- Done means: a list of non-conformances, each citing the RFC section, the file:line, and a repro command with its actual output demonstrating the behaviour; plus a list of what the reviewer did not check.
- Stop at: findings recorded in this doc. No code changes, no PR.
- Deployed when: n/a (review only, nothing ships).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
(empty)

## Notes (not for reviewers)
User's hunches, verbatim: "Between us, I think the weak spot is the status member, I have a feeling we're stringifying it. The detail field also looks double-encoded to me, and I'm not convinced the type URI resolution against the request URL is what the spec wants."

Tasks JSON: [{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}]

3. Reply with: the commit SHA of the doc on `orchestration`, whether the push succeeded (with the command output), and the path of the saved prompt file. If any step can't be done, stop and report why.
