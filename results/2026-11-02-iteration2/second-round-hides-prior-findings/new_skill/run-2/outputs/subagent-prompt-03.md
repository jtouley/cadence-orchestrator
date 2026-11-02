Use the schema in .claude/skills/tpm/references/workstream.md ("## tasks.json") for the tasks file.

Step 0: Save this entire message, verbatim from "Use the schema" to the end, to /tmp/cr-run.0xfme1Ia/repo/outputs/subagent-prompt-03.md.
Step 1: Commit workstreams/search-api-round2.md alone on `orchestration` and note its SHA as DOCSHA.
Step 2: Write workstreams/search-api-round2.tasks.json as {"workstream":"search-api-round2","tasks":[...]}. It holds two tasks, "fix-check" (owner "verifier-agent") and "blind-review" (owner "reviewer-agent"). Give each task "doc_sha": DOCSHA, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null and "tokens": null. Validate it with `python3 -m json.tool`, then commit it.
Step 3: Don't push. Report DOCSHA and the second commit's SHA. If you can't do this as specified, stop and report why.
