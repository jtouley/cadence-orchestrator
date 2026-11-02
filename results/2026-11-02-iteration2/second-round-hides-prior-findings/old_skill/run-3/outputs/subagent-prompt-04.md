Scribe task, write files only. Save these three prompts verbatim (exact text between the ===== markers, nothing added) into /tmp/cr-run.UrOA8FEV/repo/outputs/: PROMPT-02 as subagent-prompt-02.md, PROMPT-03 as subagent-prompt-03.md, and this whole message you are reading as subagent-prompt-04.md. Then in /tmp/cr-run.UrOA8FEV/repo/.cadence/workstreams/search-api-round2.tasks.json set T1 and T2 state to "claimed" and note on T1 prompt=outputs/subagent-prompt-02.md, on T2 prompt=outputs/subagent-prompt-03.md, pinned SHA 6746708. Report the paths written.

===== PROMPT-02 =====
Fix check, per /tmp/cr-run.UrOA8FEV/repo/.cadence/workstreams/search-api-round2.md: confirm whether each finding below still reproduces at 6746708 (feature/search-api) in /tmp/cr-run.UrOA8FEV/clone, and as a control at tag round-1 (87fe0d8) in a separate worktree. Judge only these two findings; no code changes, no other agents. If it can't be done as specified, stop and report why.

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1. Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done". Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

The repro scripts are in /tmp/cr-run.UrOA8FEV/repo/repro/. Write each command, its full output and exit code, and your verdict per finding to /tmp/cr-run.UrOA8FEV/repo/outputs/fix-check-round2.md, plus anything you couldn't check.
===== END PROMPT-02 =====

===== PROMPT-03 =====
/code-review high on main..feature/search-api (6a70bbd..6746708) in /tmp/cr-run.UrOA8FEV/clone; run the tests too. No code changes, no other agents. Write the full review (each finding with severity, file:line and how you confirmed it) and anything you left out to /tmp/cr-run.UrOA8FEV/repo/outputs/review-round2.md.
===== END PROMPT-03 =====