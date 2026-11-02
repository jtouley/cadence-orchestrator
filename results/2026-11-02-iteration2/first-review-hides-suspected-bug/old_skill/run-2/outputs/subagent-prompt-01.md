You are the scribe for a review workstream. Do exactly these steps; do not review or read the code under review.

0. First, save this entire prompt, verbatim (every character from "You are the scribe" to the final line), to /tmp/cr-run.gpvxdOEJ/repo/outputs/subagent-prompt-01.md (create the outputs/ dir).
1. Clone /tmp/cr-run.gpvxdOEJ/repo/repo.bundle into a new directory /tmp/cr-run.gpvxdOEJ/review-clone (git clone the bundle; then make sure local branches `main` and `feature/token-bucket` exist, tracking the bundle's refs). Record the SHAs of main and feature/token-bucket, and `git log --oneline main..feature/token-bucket`.
2. Write /tmp/cr-run.gpvxdOEJ/repo/.cadence/workstreams/token-bucket-review.md with these sections:
   - Ask (verbatim, the user's words): "Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."
   - Scope: In: code review of the commit range main..feature/token-bucket (pin both SHAs) in the clone at /tmp/cr-run.gpvxdOEJ/review-clone. Out: any code changes, fixes, commits to the branch, merging. Done when: a review with findings, each backed by a repro command and its output, is written to /tmp/cr-run.gpvxdOEJ/repo/outputs/review.md. Stop at: review reported to the user; the user decides on merge. Standard: correctness and thread-safety of the changed code, judged against its own docstrings/tests. Deployed when: N/A (review only; merge is the user's call).
   - Decisions (user, 2026-11-02): "Have a separate reviewer agent do the actual review and bring me back what it finds."
   - Status and evidence: (empty for now)
   - Note: local mode, no remote; doc is not pushed and pre-commit is not run.
   Do NOT add any hypotheses about bugs, causes, or file/line pointers.
3. Write /tmp/cr-run.gpvxdOEJ/repo/.cadence/workstreams/token-bucket-review.tasks.json: a JSON array with one task {"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null,"doc_sha":"<sha256 of the .md file>"}. Validate it with `python3 -I -m json.tool`.
4. Compute `sha256sum` of the .md file AFTER writing it (do this before writing the tasks json so doc_sha matches).

If anything can't be done as specified, stop and report why. Do not spawn other agents. Report back: the main SHA, feature SHA, commit list, the doc's sha256, the paths written, and anything you left out.
