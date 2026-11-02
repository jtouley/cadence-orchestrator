Thanks, my spec was wrong. Write workstreams/problem-details-review.tasks.json in this shape instead, validate it, then commit both files on `orchestration` in /tmp/cr-run.gq3t7ez8/orch (no push). Reply with the commit SHA.

{
  "workstream": "problem-details-review",
  "tasks": [
    {"id": "scribe-01", "owner": "scribe", "doc_sha": null, "state": "done", "evidence": ["outputs/subagent-prompt-01.md", "workstream doc committed on orchestration branch (SHA reported separately)"], "left_out": [], "left_out_accepted_by": "tpm", "tokens": 18745},
    {"id": "review-rfc9457", "owner": "reviewer-1", "doc_sha": null, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null, "tokens": null}
  ]
}
