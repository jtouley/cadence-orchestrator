You are the scribe agent. Do exactly these steps and report; if one can't be done, stop and say why. No subagents, and don't read the ratelimit code or outputs/review.md.

1. Save this entire prompt verbatim (from "You are the scribe agent." through the last line) to /tmp/cr-run.1p5VGY0i/repo/outputs/subagent-prompt-03.md.

2. Save the text between the markers BEGIN-02 and END-02 below (excluding the marker lines), verbatim, to /tmp/cr-run.1p5VGY0i/repo/outputs/subagent-prompt-02.md:
BEGIN-02
/code-review main..feature/token-bucket (f7f6429..3050047) in /tmp/cr-run.1p5VGY0i/review-clone against .cadence/workstreams/token-bucket-review.md@04d57ca (orchestration branch); no fixes, no subagents. Write the full review to /tmp/cr-run.1p5VGY0i/repo/outputs/review.md, every finding with its repro command and raw output, and list what you didn't check; if it can't be done as specified, stop and report why.
END-02

3. In /tmp/cr-run.1p5VGY0i/review-clone on branch `orchestration`, edit .cadence/workstreams/token-bucket-review.tasks.json: set task review-1 "doc" to "workstreams/token-bucket-review.md@04d57ca" and "state" to "claimed". Use `git stash`/checkout care: another agent may be reading other branches in that clone, so use `git -C ... worktree add /tmp/cr-run.1p5VGY0i/orch-wt orchestration` and edit/commit there instead of switching branches in the main clone. Commit locally, don't push. Report the new commit SHA.
