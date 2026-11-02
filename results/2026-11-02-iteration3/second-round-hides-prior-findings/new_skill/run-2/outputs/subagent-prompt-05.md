Retry the tasks file using the full schema from .claude/skills/tpm/references/workstream.md. First save this message, verbatim, to /tmp/cr-run.xLyRCDK9/repo/outputs/subagent-prompt-05.md (prompts 03 and 04 went to other agents). Then write /tmp/cr-run.xLyRCDK9/repo/.cadence/workstreams/search-api-round2.tasks.json as:
{"workstream":"search-api-round2","tasks":[
 {"id":"T1-fix-check","owner":"fix-verifier","doc_sha":"sha256:d886be68ba7c","state":"claimed","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null},
 {"id":"T2-blind-review","owner":"reviewer","doc_sha":"sha256:d886be68ba7c","state":"claimed","evidence":[],"left_out":[],"left_out_accepted_by":null,"tokens":null}
]}
Validate it with `python3 -I -m json.tool` and reply with the output. If the guard rejects it, report the exact message and stop.
