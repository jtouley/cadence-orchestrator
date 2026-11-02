You are a scribe/verifier agent; don't spawn agents, don't edit any code. Steps:
1) Save this entire prompt verbatim to /tmp/cr-run.BZmrs5aO/repo/outputs/subagent-prompt-04.md.
2) Save the text between the BEGIN/END markers below, verbatim (excluding the marker lines), to /tmp/cr-run.BZmrs5aO/repo/outputs/subagent-prompt-03.md:
BEGIN
/code-review high on commits f7f6429..3050047 (main..feature/token-bucket) in the clone /tmp/cr-run.BZmrs5aO/review-clone (use a git worktree of 3050047; don't modify branches), against .cadence/workstreams/token-bucket-review.md@16e42cb on its orchestration branch. Review only, no fixes, no subagents; back each finding with a repro command and its raw output where possible, and list what you didn't check. Write the full review to /tmp/cr-run.BZmrs5aO/repo/outputs/review-report.md and return it.
END
3) Rerun each repro listed in /tmp/cr-run.BZmrs5aO/repo/outputs/review-report.md (cases refill, lock, timeout, rate0, rateneg, cap, iface, failfast) with `python3 -I /tmp/cr-run.BZmrs5aO/repro/repro.py /tmp/cr-run.BZmrs5aO/wt-3050047 <case>`, plus `python3 -m pytest -q tests` in /tmp/cr-run.BZmrs5aO/wt-3050047. Capture raw output and note whether each matches the report.
4) In /tmp/cr-run.BZmrs5aO/review-clone on branch orchestration, append to .cadence/workstreams/token-bucket-review.md under "Status and evidence": the report path, the commands and raw outputs from step 3. Update the tasks JSON task review-1 to state "done", evidence a list of those artifacts (report path, repro commands), tokens 26589. Keep the existing JSON schema. Commit (no push).
Report the commit SHA, per-case match/mismatch with raw output, and anything you couldn't do; if something can't be done as specified, stop and say why.
