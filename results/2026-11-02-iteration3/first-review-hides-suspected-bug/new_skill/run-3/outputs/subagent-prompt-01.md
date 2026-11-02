You are a scribe/setup agent. Step 0: before anything else, save this entire prompt, verbatim and byte-for-byte (from "You are a scribe/setup agent." through the final line), to /tmp/cr-run.F91Ddmlk/repo/outputs/subagent-prompt-01.md (create the outputs/ dir). Do not review or read the source code; you only record.

1. Clone /tmp/cr-run.F91Ddmlk/repo/repo.bundle into a new empty dir /tmp/cr-run.F91Ddmlk/clone (git clone the bundle; create local branches `main` and `feature/token-bucket` tracking the bundle's refs). Report the SHAs of main and feature/token-bucket and `git log --oneline main..feature/token-bucket`.
2. In the clone, create a local branch `orchestration` from main (no remote exists; local mode, nothing is pushed). On it, write `.cadence/workstreams/token-bucket-review.md` with exactly this content:

---
# Workstream: token-bucket-review

## Ask (user, 2026-11-02, verbatim; hunches held back)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds.

Context, for what it's worth: [hunch held back] [hunch held back] I haven't confirmed either one."

## Scope
- In: review of the commit range main..feature/token-bucket (clone at /tmp/cr-run.F91Ddmlk/clone).
- Out: fixing anything, merging, pushing, changing the feature branch.
- Standard: correctness of the TokenBucket limiter as described by its own docstrings/commit messages and tests in the range; general code quality.
- Done when: a blind review with reproducible evidence (commands + output) for each finding is recorded, and returned to the user.
- Stop at: review reported to the user. Not merged.
- Deployed when: user merges feature/token-bucket into main (not in scope here).

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."

## Status and evidence
- (to be filled)
---

Also write `.cadence/workstreams/token-bucket-review.tasks.json` as a JSON array with: {"id":"setup","owner":"scribe-01","state":"done","evidence":"<clone SHAs>","tokens":null}, {"id":"blind-review","owner":"reviewer-02","state":"assigned","evidence":null,"tokens":null}. Commit both on `orchestration` (message "workstream: token-bucket-review") and report the commit SHA. Leave the clone checked out on `orchestration` is NOT required; check out `feature/token-bucket` afterwards.
3. Report: the SHAs, the orchestration commit SHA, and anything you could not do or left out. If something can't be done as specified, stop and report why.
