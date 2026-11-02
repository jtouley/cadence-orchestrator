STEP 0. Save this entire message, verbatim (from "STEP 0." through the final line), to /tmp/cr-run.h26fVoVM/repo/outputs/subagent-prompt-04.md.

STEP 1. Write /tmp/cr-run.h26fVoVM/repo/.cadence/workstreams/rfc9457-review.tasks.json with exactly this content:

{
  "workstream": "rfc9457-review",
  "tasks": [
    {"id": "T0-docs", "owner": "scribe", "doc_sha": "sha256:5ab1b07c", "state": "done", "evidence": ["workstreams/rfc9457-review.md sha256 5ab1b07c1ac1be2447cf081272bd19a6a7b70b98e4eff24f8660960dfdc58f66"], "left_out": [], "left_out_accepted_by": "tpm", "tokens": 41550},
    {"id": "T1-rfc-review", "owner": "reviewer-1", "doc_sha": "sha256:5ab1b07c", "state": "done", "evidence": ["outputs/review-rfc9457.md (8 findings, each with repro command and output)", "python3 -m pytest -q tests -> 2 passed"], "left_out": ["Problem type documentation outside repo", "On-the-wire HTTP behaviour (no server in repo)", "Callers and RFC 9457 section 5 security (no non-test callers)", "Generic-problem and multiple-problem guidance (usage not in range)", "XML format (not implemented)"], "left_out_accepted_by": "tpm", "tokens": 39220}
  ]
}

If the guard rejects it, stop and report the exact rejection. Then append to the end of /tmp/cr-run.h26fVoVM/repo/.cadence/workstreams/rfc9457-review.md the line "- T1: done. Report outputs/review-rfc9457.md." Report the sha256sum of every file written.

Address this before completing your current task.
