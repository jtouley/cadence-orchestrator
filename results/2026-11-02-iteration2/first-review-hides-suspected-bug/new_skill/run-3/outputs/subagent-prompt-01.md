You are the scribe for a TPM-run code review. Do exactly the following, nothing more; if any step can't be done as specified, stop and report why.

0. First, save this entire prompt verbatim (every character, from "You are the scribe" to the end) to /tmp/cr-run.zEkso1gj/repo/outputs/subagent-prompt-01.md (create outputs/ if needed).

1. Clone /tmp/cr-run.zEkso1gj/repo/repo.bundle into a new directory /tmp/cr-run.zEkso1gj/review-clone (`git clone repo.bundle ...`). Make sure local branches `main` and `feature/token-bucket` both exist there (create them from the bundle's refs if the clone only checks out one). Record the SHAs of main and feature/token-bucket. Do not read or analyse the code itself.

2. There is no remote, so use local mode: in the clone, create branch `orchestration` from main and on it write `.cadence/workstreams/token-bucket-review.md` with exactly this content (fill in the SHAs):

```
# Workstream: token-bucket-review

## Ask
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds.

Context, for what it's worth: [see Notes]"

## Scope
- In: review of the commit range main..feature/token-bucket (main=<SHA>, feature/token-bucket=<SHA>) in /tmp/cr-run.zEkso1gj/review-clone.
- Out: fixing anything, merging, pushing.
- Done: a written review with each finding backed by a repro command and its output (or marked UNPROVEN), saved under .cadence/reviews/ in the clone and summarised back to the user.
- Stop at: review reported to user. The user decides whether to merge.
- Standard: correctness, thread-safety and test adequacy of the change; no written spec exists in the repo.
- Deployed when: merged to main by the user (not part of this workstream).

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."
- 2026-11-02 (user): local clone of repo.bundle is the target; no remote.

## Status and evidence
- (pending)

## Notes (not for reviewers)
User, verbatim: "I'm pretty sure the refill clock drifts when the bucket is empty, the way _last only gets bumped once there's a whole token looks wrong to me. Priya also mentioned that the lock is held across the sleep in acquire(), which would stall every other thread. I haven't confirmed either one."
```

3. Next to it write `.cadence/workstreams/token-bucket-review.tasks.json`:
`[{"id":"blind-review","owner":"reviewer-1","state":"assigned","evidence":null,"tokens":null},{"id":"hunch-check","owner":"verifier-1","state":"assigned","evidence":null,"tokens":null}]`

4. Commit both files on `orchestration` (message "workstream: token-bucket-review"), then check `feature/token-bucket` back out so the working tree is the code under review. Tell me: the clone path, main SHA, feature SHA, and the orchestration commit SHA. Note that local mode loses a shared remote branch and pre-commit checks. Don't spawn other agents.
