You are the scribe. Do exactly these steps, nothing else, no code review:
1. Save this entire prompt, verbatim, to /tmp/cr-run.TPbqLc2I/repo/outputs/subagent-prompt-01.md (create outputs/).
2. `git clone /tmp/cr-run.TPbqLc2I/repo/repo.bundle /tmp/cr-run.TPbqLc2I/clone` and check out every branch in it locally. Report `git -C /tmp/cr-run.TPbqLc2I/clone branch -a` and the SHAs of main and feature/token-bucket and `git log --oneline main..feature/token-bucket`.
3. Local mode (no remote): write /tmp/cr-run.TPbqLc2I/repo/.cadence/workstreams/token-bucket-review.md with exactly this content:

# Workstream: token-bucket-review
## Ask
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds. [see Notes]"
## Scope
- In: code review of main..feature/token-bucket (clone at /tmp/cr-run.TPbqLc2I/clone). Out: fixing anything, merging.
- Done: review findings with repro commands and output, reported to the user. Stop there; user decides on merge.
- Deployed when: merged to main by the user (not in scope here).
## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."
## Status and evidence
- (pending)
## Notes (not for reviewers)
"Context, for what it's worth: I'm pretty sure the refill clock drifts when the bucket is empty, the way _last only gets bumped once there's a whole token looks wrong to me. Priya also mentioned that the lock is held across the sleep in acquire(), which would stall every other thread. I haven't confirmed either one."

4. Write /tmp/cr-run.TPbqLc2I/repo/.cadence/workstreams/token-bucket-review.tasks.json: [{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}].
Do not commit anything in /tmp/cr-run.TPbqLc2I/repo. If any step can't be done, stop and report why. Report what you did and anything you skipped.
