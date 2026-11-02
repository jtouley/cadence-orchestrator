You are a scribe. Do not review or read any code. Two steps:

1. Save this entire prompt, verbatim from its first word to its last, to /tmp/cr-run.8o21j3kg/repo/outputs/subagent-prompt-03.md.
2. Save the text between the BEGIN and END markers below (exclusive of the marker lines), verbatim, to /tmp/cr-run.8o21j3kg/repo/outputs/subagent-prompt-02.md.
BEGIN
Review main..feature/token-bucket (f7f6429..3050047) in the clone at /tmp/cr-run.8o21j3kg/tb-review against .cadence/workstreams/token-bucket-review.md@d28b0a9 (on branch `orchestration`); use the /code-review skill if available, otherwise review by hand. No fixes and no commits to the feature branch; do not spawn other agents. Back each finding with a repro command you actually ran and its raw output (mark any finding you couldn't reproduce UNPROVEN), list what you left out, and return the full review as your reply. If it can't be done as specified, stop and report why.
END
3. In /tmp/cr-run.8o21j3kg/tb-review on branch `orchestration`, set the task review-1 in .cadence/workstreams/token-bucket-review.tasks.json to state "claimed" and doc_sha "d28b0a9", and commit (local only).
Reply with the two file paths and the new commit SHA.
