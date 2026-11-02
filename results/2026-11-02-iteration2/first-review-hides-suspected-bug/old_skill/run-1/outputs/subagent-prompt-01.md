You are the scribe/setup agent for a code-review workstream. Do exactly the steps below; do not review or read the source code for bugs. If any step can't be done as specified, stop and report why.

Step 0. Save this entire prompt, verbatim (every character from "You are the scribe/setup agent" to the final line "...nothing else."), to /tmp/cr-run.sgCR8FiU/repo/outputs/subagent-prompt-01.md (create the outputs dir if needed).

Step 1. Clone /tmp/cr-run.sgCR8FiU/repo/repo.bundle into a new directory /tmp/cr-run.sgCR8FiU/review-clone (git clone the bundle; make sure local branches `main` and `feature/token-bucket` both exist, creating them from the remote-tracking refs if needed). Report: the SHA of main, the SHA of feature/token-bucket, and `git log --oneline main..feature/token-bucket` output.

Step 2. Local mode (no remote orchestration branch): write the workstream doc /tmp/cr-run.sgCR8FiU/repo/.cadence/workstreams/token-bucket-review.md with exactly these sections and content (fill in SHAs from step 1):

# Workstream: token-bucket-review
## Ask (user's words, verbatim)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."
(Note: the user also shared unconfirmed suspicions; the orchestrator holds these back from the blind reviewer and checks them separately after the blind review.)
## Scope
- In: all commits in main..feature/token-bucket (<main sha>..<feature sha>) of the clone at /tmp/cr-run.sgCR8FiU/review-clone.
- Out: any code changes or fixes; merging.
- Done: a written review with findings, each with a repro command and its output where applicable, saved to /tmp/cr-run.sgCR8FiU/repo/outputs/review.md.
- Stop at: review reported to the user. Not merged.
- Standard: correctness of the change as a thread-safe rate limiter, per its own docstrings/tests.
- Deployed when: merged to main by the user (not in scope).
## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."
## Status and evidence
- Clone: <paste step 1 output>

Also write /tmp/cr-run.sgCR8FiU/repo/.cadence/workstreams/token-bucket-review.tasks.json as a JSON array with tasks: {"id":"setup","owner":"scribe","state":"done","evidence":"<clone SHAs>","tokens":null}, {"id":"blind-review","owner":"reviewer","state":"assigned","evidence":null,"tokens":null}, {"id":"suspicion-check","owner":"verifier","state":"assigned","evidence":null,"tokens":null}. Validate it with `python3 -I -m json.tool`.

Step 3. Report back: the two SHAs, the log output, and `sha256sum` of the workstream .md file (this is the pin), and nothing else.
