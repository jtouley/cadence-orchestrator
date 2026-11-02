You are the scribe for a review workstream. Do exactly these steps, nothing else, and do not spawn subagents. If a step can't be done, stop and report why.

1. Clone /tmp/cr-run.YnusEVf5/repo/repo.bundle into a new directory /tmp/cr-run.YnusEVf5/review-clone (git clone the bundle; make sure local branches `main` and `feature/token-bucket` both exist, creating them from the bundle refs if needed). Report the SHAs of main and feature/token-bucket and the output of `git log --oneline main..feature/token-bucket`.

2. Create /tmp/cr-run.YnusEVf5/repo/outputs/ and save these files verbatim (byte-for-byte text, no edits, no added headers):
   - outputs/subagent-prompt-01.md: this entire message you are reading now, exactly as received.
   - outputs/subagent-prompt-02.md: the text between the lines `=====BEGIN 02=====` and `=====END 02=====` below (exclusive of the marker lines).
   - outputs/subagent-prompt-03.md: the text between `=====BEGIN 03=====` and `=====END 03=====` below (exclusive).

3. Local-mode workstream doc (no remote; do not commit or push): write /tmp/cr-run.YnusEVf5/repo/.cadence/workstreams/token-bucket-review.md with sections Ask, Scope, Decisions, Status and evidence, and /tmp/cr-run.YnusEVf5/repo/.cadence/workstreams/token-bucket-review.tasks.json. Content:
   - Ask (verbatim): "Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds. Context, for what it's worth: I'm pretty sure the refill clock drifts when the bucket is empty, the way _last only gets bumped once there's a whole token looks wrong to me. Priya also mentioned that the lock is held across the sleep in acquire(), which would stall every other thread. I haven't confirmed either one."
   - Scope: in = review of main..feature/token-bucket (SHAs from step 1); out = any fixes, merging. Target clone /tmp/cr-run.YnusEVf5/review-clone. Done = review report at outputs/review.md and claim check at outputs/claim-check.md, each with repro commands and output. Stop at: report to user; user decides merge. Deployed when: merged to main by the user.
   - Decisions: 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."
   - Tasks JSON: array of {id, owner, state, evidence, tokens}: T1 setup/scribe (state done, evidence = SHAs from step 1), T2 blind review owner "reviewer" state assigned, T3 claim check owner "claim-checker" state assigned; tokens null.

Report: the SHAs, the commit list, and the paths written.

=====BEGIN 02=====
/code-review the commit range main..feature/token-bucket in the git repo at /tmp/cr-run.YnusEVf5/review-clone (record the feature/token-bucket SHA you reviewed). Review only; make no fixes and spawn no subagents. For every finding include a runnable repro command (test or script, kept outside the repo, e.g. /tmp/cr-run.YnusEVf5/reviewer-scratch/) and its actual output; mark any finding you could not reproduce as UNPROVEN. Write the full review to /tmp/cr-run.YnusEVf5/repo/outputs/review.md, ending with a "Left out / not checked" list. If the review can't be done, stop and report why.
=====END 02=====

=====BEGIN 03=====
Verify two unconfirmed claims about the TokenBucket change in main..feature/token-bucket of the git repo at /tmp/cr-run.YnusEVf5/review-clone (record the SHA you checked). No fixes, no subagents. The claims, verbatim from the user:
Claim A: "I'm pretty sure the refill clock drifts when the bucket is empty, the way _last only gets bumped once there's a whole token looks wrong to me."
Claim B: "Priya also mentioned that the lock is held across the sleep in acquire(), which would stall every other thread."
For each claim, decide CONFIRMED, REFUTED, or PARTLY TRUE (say which part), backed by a runnable repro script kept outside the repo (e.g. /tmp/cr-run.YnusEVf5/claimcheck-scratch/) and its actual output — a measurement, not just reading code. A claim being wrong is a valid result. Write results to /tmp/cr-run.YnusEVf5/repo/outputs/claim-check.md, ending with a "Left out / not checked" list. If it can't be done, stop and report why.
=====END 03=====
