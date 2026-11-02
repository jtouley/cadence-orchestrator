You are the scribe. Record only what I tell you; don't review code.

1. Save this entire prompt verbatim, from its first line to its last, as /tmp/cr-run.OAMYHrAZ/repo/outputs/subagent-prompt-05.md.
2. Save the text between the lines `=====BEGIN 03=====` and `=====END 03=====` below (exclusive of those marker lines, byte-for-byte, keeping its blank line) as /tmp/cr-run.OAMYHrAZ/repo/outputs/subagent-prompt-03.md. It was sent unchanged to two agents that both died on an API error before saving it.
=====BEGIN 03=====
First, save this entire prompt verbatim, from its first line to its last, as /tmp/cr-run.OAMYHrAZ/repo/outputs/subagent-prompt-03.md.

/code-review high on main..feature/search-api (6a70bbda5fa087f228bb33e126849caa3d28130d..6746708596c7166d44d11e8e436bde8398be4a12) in /tmp/cr-run.OAMYHrAZ/clone, and run the test suite; for each finding include a command and its output that demonstrates it. If the code-review skill isn't available to you, do a thorough correctness review yourself. Don't modify the clone (copy it to experiment). Write the full review to /tmp/cr-run.OAMYHrAZ/repo/outputs/review-r2.md. If it can't be done, stop and report why. Report what you left out. Don't spawn other agents.
=====END 03=====
3. In /tmp/cr-run.OAMYHrAZ/orchestration, rewrite workstreams/search-api-round2.tasks.json (whole file) so that:
   - `fix-check`: owner verifier-1, state done, evidence ["outputs/fix-check-r2.md", "python repro/r1_1_cursor_gap.py /tmp/cr-run.OAMYHrAZ/clone -> does not reproduce, exit 0 (round-1 control: REPRODUCES, exit 1)", "python repro/r1_2_like_wildcard.py /tmp/cr-run.OAMYHrAZ/clone -> does not reproduce, exit 0 (round-1 control: REPRODUCES, exit 1)"], left_out ["extra checks not run against round-1 baseline", "branch tests not run by verifier", "out-of-scope areas not assessed"], left_out_accepted_by "tpm", tokens 31573.
   - `blind-review`: owner reviewer-1, state done, evidence ["outputs/review-r2.md", "python3 -m pytest -q -> 3 passed", "demo: python3 -I /tmp/cr-run.OAMYHrAZ/demo.py /tmp/cr-run.OAMYHrAZ/exp"], left_out ["findings 7 and 8 not demonstrated as failures", "no tests added"], left_out_accepted_by "tpm", tokens 23634, plus a field "note": "two earlier Opus attempts failed on an API error before producing output; the completed run used Sonnet".
   Keep doc_sha "11ead17" on both. Validate with `python3 -I /tmp/cr-run.OAMYHrAZ/repo/.claude/skills/tpm/scripts/tasks_check.py <file>`.
   Append to the **Status and evidence** section of workstreams/search-api-round2.md: "2026-11-02: fix check — R1-1 FIXED, R1-2 FIXED (outputs/fix-check-r2.md). Blind review — 8 findings, tests 3 passed (outputs/review-r2.md). Recommendation to user: not ready to merge pending user decision on new findings 1, 2, 5, 6." Commit both files (local only, no push).

Don't modify anything else. If a step can't be done, stop and report why. Report the commit SHA, the files written, and anything you left out.
