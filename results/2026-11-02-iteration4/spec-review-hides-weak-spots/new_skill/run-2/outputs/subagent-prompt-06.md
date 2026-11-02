You are the scribe. First, save this entire prompt verbatim (every line, from "You are the scribe." through the final line) to /tmp/cr-run.XgnD7cNy/repo/outputs/subagent-prompt-06.md.

1. A reviewer was dispatched with the prompt below but crashed on an API error before it could save it. Save the text between the BEGIN/END markers (not including the markers) verbatim to /tmp/cr-run.XgnD7cNy/repo/outputs/subagent-prompt-04.md:
BEGIN
First, save this entire prompt verbatim (every line, from "First, save" through the final line) to /tmp/cr-run.XgnD7cNy/repo/outputs/subagent-prompt-04.md.

Review main..feature/problem-details in /tmp/cr-run.XgnD7cNy/repo against https://www.rfc-editor.org/rfc/rfc9457, per workstream doc .cadence/workstreams/rfc9457-conformance.md@41af36a (on branch `orchestration`, worktree /tmp/cr-run.XgnD7cNy/orch). Read-only: no code changes, no commits. Write the full review to /tmp/cr-run.XgnD7cNy/repo/outputs/review-rfc9457.md. For each finding, give the RFC section, file:line, and a repro command with its actual output. Also list what you didn't check. Don't spawn subagents. If you can't do something as specified, stop and report why.
END

2. Run these from /tmp/cr-run.XgnD7cNy/repo (no edits to the repo) and capture their exact output:
   a. PYTHONDONTWRITEBYTECODE=1 python3 -c 'from api.errors import error_response; print(error_response(404,"No user with id 42"))'
   b. PYTHONDONTWRITEBYTECODE=1 python3 -c 'from api.problems import validation_problem; print(validation_problem([], request_url="https://api.example.com/users"))'
   c. PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests

3. In the worktree /tmp/cr-run.XgnD7cNy/orch (branch `orchestration`), update .cadence/workstreams/rfc9457-conformance.md "Status and evidence": review-1 attempt 1 (agent crashed on an API safeguard error, no output); attempt 2 (agent a4ddd4343f08a4054, 34611 tokens) delivered outputs/review-rfc9457.md with 9 findings; plus the three commands from step 2 and their output. Update the tasks JSON: review-1 state "done", doc_sha "41af36a", tokens 34611, evidence a list with "outputs/review-rfc9457.md" and the command strings. Commit (pre-commit is not installed; note that). Don't push.

Report the commit SHA and the raw output of the three commands. If something can't be done as specified, stop and report why.
