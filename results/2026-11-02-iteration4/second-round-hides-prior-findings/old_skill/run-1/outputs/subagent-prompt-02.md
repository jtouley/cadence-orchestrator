First, save this entire prompt verbatim, from its first line to its last, as /tmp/cr-run.OAMYHrAZ/repo/outputs/subagent-prompt-02.md.

Fix check for task `fix-check` in /tmp/cr-run.OAMYHrAZ/orchestration/workstreams/search-api-round2.md@11ead17. Target: /tmp/cr-run.OAMYHrAZ/clone at 6746708596c7166d44d11e8e436bde8398be4a12 (don't modify the clone; copy it if you need to experiment). Judge only these two first-round findings, quoted verbatim:

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

The repro scripts are in /tmp/cr-run.OAMYHrAZ/repo/repro/. Run each against the clone and record the exact command, raw output and exit code. Then decide whether each finding is actually fixed, not just whether its one repro passes: you may write extra checks of the same defect (other inputs, page sizes, data shapes), and record each with command and output. Out of scope: anything unrelated to R1-1 and R1-2, and making fixes.

Write the result to /tmp/cr-run.OAMYHrAZ/repo/outputs/fix-check-r2.md: per finding, FIXED / NOT FIXED / PARTIAL with the evidence. If something can't be done, stop and report why; don't fake a result. Report what you left out. Don't spawn other agents.
