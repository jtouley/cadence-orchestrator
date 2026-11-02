You are a setup/scribe agent. Do exactly these steps, nothing else, and do not spawn agents:
1. Save this entire prompt, verbatim, to /tmp/cr-run.BZmrs5aO/repo/outputs/subagent-prompt-01.md (create outputs/ if needed).
2. Clone /tmp/cr-run.BZmrs5aO/repo/repo.bundle into the new empty directory /tmp/cr-run.BZmrs5aO/review-clone (git clone the bundle; make local branches main and feature/token-bucket track it). Do not run any code from the clone.
3. In the clone, write (do not push; there is no remote — local mode) .cadence/workstreams/token-bucket-review.md with:
   - Ask (verbatim): "Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds. [hunch held back]"
   - Scope: in = commits main..feature/token-bucket of the bundle; out = any fixes or edits to code, merging. Done = a review report with findings, each backed by a repro command and its output where possible. Stop at: review reported, not merged, nothing fixed. Deployed when: n/a (review only; user merges).
   - Decisions: 2026-11-02, user: "Have a separate reviewer agent do the actual review and bring me back what it finds."
   - Status and evidence: (empty for now)
   and .cadence/workstreams/token-bucket-review.tasks.json with one task {"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}. Commit both on a local branch named orchestration (created from main), not on feature/token-bucket. If pre-commit is unavailable, skip it and say so.
4. Report back: the full SHAs of main and feature/token-bucket in the clone, the orchestration commit SHA, `git log --oneline main..feature/token-bucket` output, and anything you skipped or couldn't do. If something can't be done as specified, stop and report why.
