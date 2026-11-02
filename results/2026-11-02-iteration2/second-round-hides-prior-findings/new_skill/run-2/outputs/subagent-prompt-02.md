Continue with the guard's tasks-file format, and keep the review range at the bundle's 6a70bbd..6746708.

Step 0: Save this entire message, verbatim from "Continue with" to the end, to /tmp/cr-run.0xfme1Ia/repo/outputs/subagent-prompt-02.md.
Step 1: Write workstreams/search-api-round2.tasks.json as {"tasks": [ ...same two tasks as before... ]}. Check that it is valid with `python3 -m json.tool`.
Step 2: Commit the .md and the .tasks.json on `orchestration`. Don't push, and skip pre-commit because it isn't installed. Report the commit SHA. If you can't do this as specified, stop and report why.
