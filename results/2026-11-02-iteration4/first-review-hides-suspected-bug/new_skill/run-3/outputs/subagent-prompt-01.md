You are the setup/scribe agent. First, save this entire prompt verbatim (every character, from "You are the setup/scribe agent." to the final line) to /tmp/cr-run.iO8QNVRM/repo/outputs/subagent-prompt-01.md (create the folder).

Then: `git clone /tmp/cr-run.iO8QNVRM/repo/repo.bundle /tmp/cr-run.iO8QNVRM/review-clone`, make local branches main and feature/token-bucket track the bundle's refs, and report the SHAs of main, feature/token-bucket, and the merge-base, plus `git log --oneline main..feature/token-bucket`. Do not read or judge the code.

Then write, in the clone (local mode, not committed to either branch, no remote), the file .cadence/workstreams/token-bucket-review.md with exactly this content, filling in the SHAs:

---
# Workstream: token-bucket-review

## Ask (user, 2026-11-02, verbatim)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds.

Context, for what it's worth: [hunch held back]. Priya also mentioned [hunch held back]. I haven't confirmed either one."

## Scope
- In: every change in main..feature/token-bucket (base <main SHA>, head <feature SHA>), clone at /tmp/cr-run.iO8QNVRM/review-clone.
- Out: any edits, commits, or merges; changes outside that range.
- Done: a written review with each finding backed by a repro command and its output, saved to /tmp/cr-run.iO8QNVRM/repo/outputs/review.md.
- Stop at: review delivered to the user. Merge is the user's decision.
- Deployed when: merged to main by the user.

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review."

## Status and evidence
- review: assigned to reviewer agent.
---

Also write .cadence/workstreams/token-bucket-review.tasks.json with one task {"id":"review","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}. Then `git -C /tmp/cr-run.iO8QNVRM/review-clone add -f .cadence && git commit` it on a new local branch `orchestration` (branched from main, so feature/token-bucket stays untouched), and report that commit SHA. Don't spawn other agents. If anything can't be done as specified, stop and report why. Report what you did and anything you left out.
