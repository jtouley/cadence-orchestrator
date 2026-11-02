You are the scribe for a review workstream. Do exactly these steps, nothing else, no code review. If any step can't be done as specified, stop and report why.

0. Save this entire prompt, verbatim (byte-for-byte, from "You are the scribe" through the last line), to /tmp/cr-run.M1Orbyyw/repo/outputs/subagent-prompt-01.md (create the outputs dir).
1. Clone /tmp/cr-run.M1Orbyyw/repo/repo.bundle into a new empty dir /tmp/cr-run.M1Orbyyw/review/repo (git clone the bundle; make sure local branches `main` and `feature/token-bucket` exist, tracking the bundle's refs). Report `git log --oneline main..feature/token-bucket` and the SHAs of main and feature/token-bucket.
2. Local mode (no remote): create an orphan branch `orchestration` in that clone, checked out as a git worktree at /tmp/cr-run.M1Orbyyw/review/orchestration. In it write `workstreams/token-bucket-review.md` with this content, filling the <...> SHAs from step 1:

# Workstream: token-bucket-review

## Ask (verbatim, hunches held back)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds.

Context, for what it's worth: [hunch held back] [hunch held back] I haven't confirmed either one."

## Scope
- In: code review of the commit range main..feature/token-bucket (main=<main sha>, feature/token-bucket=<feature sha>) in the clone at /tmp/cr-run.M1Orbyyw/review/repo.
- Out: fixing code, merging, pushing anywhere.
- Done: a review report with findings, each with a repro command and its output (or marked UNPROVEN), recorded under Status and evidence.
- Stop at: review report delivered to the user. Not merged.
- Standard: correctness of the change as a thread-safe rate limiter, per its own docstrings/tests; no separate spec exists.
- Deployed when: user merges feature/token-bucket into main (not done by agents).

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."

## Status and evidence
- (none yet)

Also write `workstreams/token-bucket-review.tasks.json`:
[{"id":"T1-clone-and-doc","owner":"scribe","state":"done","evidence":"<clone path + feature sha>","tokens":null},
 {"id":"T2-blind-review","owner":"reviewer","state":"assigned","evidence":null,"tokens":null}]
Validate the JSON with `python3 -I -m json.tool`. Run `pre-commit run --all-files` if pre-commit is installed; if not, say so. Commit on `orchestration` and report the commit SHA.

Report back: main SHA, feature SHA, commit list, orchestration commit SHA, whether pre-commit ran, and anything you left out.