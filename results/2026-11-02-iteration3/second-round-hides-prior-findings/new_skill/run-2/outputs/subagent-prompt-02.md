Approved: use the object format the guard requires for the tasks file. First save this message, verbatim, to /tmp/cr-run.xLyRCDK9/repo/outputs/subagent-prompt-02.md. Then write /tmp/cr-run.xLyRCDK9/repo/.cadence/workstreams/search-api-round2.tasks.json as:
{"workstream":"search-api-round2","tasks":[
 {"id":"T1-fix-check","owner":"fix-verifier","state":"assigned","evidence":null,"tokens":null},
 {"id":"T2-blind-review","owner":"reviewer","state":"assigned","evidence":null,"tokens":null}
]}
If the guard rejects this too, report the exact message and stop. Validate with `python3 -I -m json.tool` and reply with the output.
