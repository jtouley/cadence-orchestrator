Approved: use the object format for the tasks.json file. First, save this entire message verbatim to /tmp/cr-run.HCTyclmI/repo/outputs/subagent-prompt-02.md.

Write `workstreams/rfc9457-review.tasks.json` as:
{"workstream":"rfc9457-review","tasks":[{"id":"review-1","owner":"reviewer-agent","doc_sha":null,"state":"assigned","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null}]}

Commit both files on `orchestration` (local only, no push; pre-commit unavailable is fine, note it in the commit message). Report the commit SHA.
