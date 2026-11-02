You are the scribe/setup agent. Do exactly these steps; do not review or read the code under review. If any step can't be done as specified, stop and report why.

0. Save this entire prompt, verbatim (byte-for-byte, from "You are the scribe/setup agent." to the final line), to /tmp/cr-run.0lrKXAqS/repo/outputs/subagent-prompt-01.md (create the outputs/ dir).
1. Clone /tmp/cr-run.0lrKXAqS/repo/repo.bundle into /tmp/cr-run.0lrKXAqS/clone (`git clone /tmp/cr-run.0lrKXAqS/repo/repo.bundle /tmp/cr-run.0lrKXAqS/clone`). Make sure local branches `main` and `feature/token-bucket` both exist in the clone (create them from origin/* if needed). Record the SHAs of main and feature/token-bucket and the output of `git log --oneline main..feature/token-bucket`.
2. In the clone, on a new branch `orchestration` created from main, write `.cadence/workstreams/token-bucket-review.md` with exactly this content (fill in the SHAs):

---
# Workstream: token-bucket-review

## Ask (user's words, verbatim; a context paragraph from the user is held by the TPM and intentionally not recorded here to keep review independent)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."

## Scope
- In: code review of the commit range main..feature/token-bucket (main=<SHA>, feature/token-bucket=<SHA>) in /tmp/cr-run.0lrKXAqS/clone.
- Out: fixing anything, merging, pushing.
- Done: a written review with findings, each with a repro command and its raw output (or marked UNPROVEN), plus a list of what the reviewer did not check.
- Stop at: review reported to the user. Do not merge.
- Standard: correctness of the token bucket limiter as a thread-safe rate limiter; the repo's existing tests.
- Deployed when: merged to main by the user (not part of this workstream).

## Decisions
- 2026-11-02 (user): review by a separate reviewer agent; user decides on merge.

## Status and evidence
- (pending)
---

3. Write `.cadence/workstreams/token-bucket-review.tasks.json`:
[{"id":"review","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null,"doc_sha":"<commit SHA from step 4>"},
 {"id":"claim-check","owner":"verifier-agent","state":"assigned","evidence":null,"tokens":null,"doc_sha":"<commit SHA from step 4>"}]
4. Commit both files on `orchestration` (message "Add token-bucket-review workstream"), then amend the tasks.json doc_sha only if you can do so without changing the doc file; otherwise leave doc_sha as the SHA of that first commit and note it. Then `git checkout feature/token-bucket` so the working tree is on the branch under review. Do not push anywhere.

Report back: clone path, the main and feature SHAs, the `git log --oneline main..feature/token-bucket` output, the orchestration commit SHA that contains the doc, and confirmation that outputs/subagent-prompt-01.md was written.
