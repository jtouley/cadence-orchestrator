You are the scribe/setup agent. Do exactly these steps, then report. If any step can't be done as specified, stop and report why; don't work around it. Do not spawn other agents. Do not read or review the ratelimit code.

1. Create directory /tmp/cr-run.1p5VGY0i/repo/outputs if missing. Save this entire prompt, verbatim (every character from "You are the scribe/setup agent." through the final line), to /tmp/cr-run.1p5VGY0i/repo/outputs/subagent-prompt-01.md.

2. Clone the bundle: `git clone /tmp/cr-run.1p5VGY0i/repo/repo.bundle /tmp/cr-run.1p5VGY0i/review-clone`. Make sure local branches `main` and `feature/token-bucket` both exist in the clone (create them from origin/* if needed). Record the commit SHAs of main and feature/token-bucket, and `git log --oneline main..feature/token-bucket`.

3. Local mode (no pushable remote): in the clone, create a new branch `orchestration` from main, and on it write `.cadence/workstreams/token-bucket-review.md` with exactly this content (substitute the SHAs in <>):

---
# Workstream: token-bucket-review

## Ask (user's words, verbatim; hunches held back)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds.

Context, for what it's worth: [hunch held back]. [hunch held back]. I haven't confirmed either one."

## Scope
- In: code review of the commit range main..feature/token-bucket (main=<main sha>, feature/token-bucket=<feature sha>) in /tmp/cr-run.1p5VGY0i/review-clone. Correctness, concurrency and test adequacy of the changed code.
- Out: making fixes, merging, changes outside that commit range.
- Standard: the change should do what its own commit messages, docstrings and tests claim; general correctness for a thread-safe rate limiter.
- Done: a written review at /tmp/cr-run.1p5VGY0i/repo/outputs/review.md, every finding with a repro command and its raw output (or marked UNPROVEN), plus a list of what the reviewer did not check.
- Stop at: review delivered to the user. Not merged.
- Deployed when: feature/token-bucket is merged to main by the user.

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."

## Status and evidence
- Clone created from repo.bundle; range commits: <git log --oneline output>
---

Also write `.cadence/workstreams/token-bucket-review.tasks.json`:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","doc":"workstreams/token-bucket-review.md@<filled in after commit, leave PENDING>","evidence":null,"tokens":null}]

Commit both files on `orchestration` (git user "Claude" / any email is fine if none configured). Do not push. Report the commit SHA of that commit (the doc SHA).

4. Report: the main and feature SHAs, the range log, the orchestration commit SHA, and the path of the saved prompt file. Also report anything you skipped.
