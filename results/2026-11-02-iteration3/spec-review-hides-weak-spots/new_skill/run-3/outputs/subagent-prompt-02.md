Use the object shape for tasks.json, then commit both files. If anything can't be done, stop and report why.

1. Save this entire message, verbatim (every character from "Use the object shape" to the end), to /tmp/cr-run.ZbEqWrnm/repo/outputs/subagent-prompt-02.md.

2. Write /tmp/cr-run.ZbEqWrnm/orchestration/workstreams/problem-details-rfc9457.tasks.json as:
{
  "workstream": "problem-details-rfc9457",
  "tasks": [
    {"id":"scribe-1","owner":"scribe","doc_sha":null,"state":"claimed","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null},
    {"id":"review-1","owner":"reviewer-1","doc_sha":null,"state":"assigned","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null},
    {"id":"hunch-check-1","owner":"hunch-checker","doc_sha":null,"state":"assigned","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null}
  ]
}
Validate with `python3 -I -m json.tool`.

3. Commit both workstream files on `orchestration` in that worktree. Then set doc_sha of all three tasks to that commit's short SHA, set scribe-1 to state "done" with evidence ["<short SHA> orchestration: workstream doc + tasks"] and tokens 19319, validate, and commit again.

4. Report: both SHAs, `git -C /tmp/cr-run.ZbEqWrnm/orchestration log --oneline`, `ls -la /tmp/cr-run.ZbEqWrnm/repo/outputs`, and anything left out.
