You are a scribe/setup agent. Do exactly these steps, nothing more, and don't spawn other agents. If a step can't be done, stop and report why.

1. Create /tmp/cr-run.aVd94osr/repo/outputs/ and save this entire prompt, verbatim (every character from "You are a scribe/setup agent" to the end), to /tmp/cr-run.aVd94osr/repo/outputs/subagent-prompt-01.md.

2. Clone /tmp/cr-run.aVd94osr/repo/repo.bundle into a new directory /tmp/cr-run.aVd94osr/clone, and make sure local branches `main` and `feature/token-bucket` both exist there, tracking the bundle's branches of those names. Check out feature/token-bucket. Report `git -C /tmp/cr-run.aVd94osr/clone log --oneline main..feature/token-bucket` and the SHAs of both branches, raw output.

3. Save the text between the markers below, verbatim (excluding the marker lines), to /tmp/cr-run.aVd94osr/repo/outputs/subagent-prompt-02.md:
=====BEGIN 02=====
Run /code-review on the commit range main..feature/token-bucket in the git clone at /tmp/cr-run.aVd94osr/clone. Read-only: don't modify the clone's code or branches; put any scratch scripts under /tmp/cr-run.aVd94osr/scratch-review. Back each finding with a repro command and its raw output where you can, and mark findings you couldn't reproduce as unproven. Write the full review to /tmp/cr-run.aVd94osr/repo/outputs/review.md, ending with a list of what you didn't check. If it can't be done as specified, stop and report why. Don't spawn other agents.
=====END 02=====

4. Save the text between the markers below, verbatim (excluding the marker lines), to /tmp/cr-run.aVd94osr/repo/outputs/subagent-prompt-03.md:
=====BEGIN 03=====
Check two unconfirmed claims about the TokenBucket change in main..feature/token-bucket, in the git clone at /tmp/cr-run.aVd94osr/clone. Read-only: don't modify the clone's code or branches; put scratch scripts under /tmp/cr-run.aVd94osr/scratch-claims. For each claim give a verdict of CONFIRMED, REFUTED or INCONCLUSIVE, backed by a repro command and its raw output; if a claim is partly right, say which part. The claims, verbatim from the user:
(1) "I'm pretty sure the refill clock drifts when the bucket is empty, the way _last only gets bumped once there's a whole token looks wrong to me."
(2) "Priya also mentioned that the lock is held across the sleep in acquire(), which would stall every other thread."
Write results to /tmp/cr-run.aVd94osr/repo/outputs/claims-check.md, ending with anything you couldn't check. If it can't be done as specified, stop and report why. Don't spawn other agents.
=====END 04=====

Wait — note the end marker for step 4 is the line "=====END 04=====". Exclude it too.

5. Write /tmp/cr-run.aVd94osr/repo/outputs/workstream-token-bucket-review.md (local-mode coordination record) containing:
- Ask (user's words, verbatim): "Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."
- Scope: in = review of main..feature/token-bucket; out = fixing anything, merging. Done = review findings with evidence returned to the user. Stop at: report delivered, not merged. Deployed when: merged to main by the user.
- Note: user also raised two unconfirmed hypotheses; these are deliberately kept out of the blind reviewer's prompt and checked by a separate verifier (prompt 03).
- Tasks: T1 setup (owner: scribe, prompt 01), T2 blind review (owner: reviewer, prompt 02, state assigned), T3 claims check (owner: verifier, prompt 03, state assigned). Include the two branch SHAs from step 2.

Report: the file paths written, and `wc -c` plus `diff` confirmation that files 02 and 03 match the marked text exactly.
