First, save this entire prompt verbatim to /tmp/cr-run.VICTq7he/repo/outputs/subagent-prompt-07.md.

Wait (poll every 20s, up to 10 minutes) until `git -C /tmp/cr-run.VICTq7he/orchestration rev-parse HEAD` is no longer dfac40b6de4e13b59031c6af1042fcbee09f9da1; then reply with the new SHA and the output of `python3 -I /tmp/cr-run.VICTq7he/repo/.claude/skills/tpm/scripts/tasks_check.py /tmp/cr-run.VICTq7he/orchestration/workstreams/search-api-round-2.tasks.json; echo exit=$?`. Change nothing. Reply "timed out" otherwise.
