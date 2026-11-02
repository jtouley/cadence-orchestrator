You are a scribe. Write three files byte-for-byte as dictated, with no edits, and do nothing else.

1. Save this entire prompt, verbatim from "You are a scribe" to the end, to /tmp/cr-run.0xfme1Ia/repo/outputs/subagent-prompt-06.md.

2. /tmp/cr-run.0xfme1Ia/repo/outputs/subagent-prompt-04.md gets exactly the text between the BEGIN-04/END-04 marker lines (markers excluded):
BEGIN-04
Fix check for workstreams/search-api-round2.md@ff7e1e168902469290c11a45de971fef5db2d5a0 (task "fix-check"). It's on the local `orchestration` branch, worktree /tmp/cr-run.0xfme1Ia/orch. Clone /tmp/cr-run.0xfme1Ia/repo/repo.bundle into a new empty directory at 6746708596c7166d44d11e8e436bde8398be4a12 (tag round-2), and a second clone at 87fe0d8170d53f62679a525298d725eec4bffe1a (tag round-1) as a control. Then confirm each of these round-1 blockers no longer reproduces at round-2:

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

The repro scripts are in /tmp/cr-run.0xfme1Ia/repo/repro/. Run each one against both clones, so the round-1 run proves the script detects the bug. Also run the repo's test suite at round-2. Judge only these two findings, and make no code changes. If a repro can't run as given, report it as blocked with the reason instead of adapting it. Write the result to /tmp/cr-run.0xfme1Ia/repo/outputs/fix-check.md: for each finding, the verdict (FIXED / STILL REPRODUCES / BLOCKED) with the exact commands, exit codes and raw output. Include what you left out.
END-04

3. /tmp/cr-run.0xfme1Ia/repo/outputs/subagent-prompt-05.md gets exactly the text between the BEGIN-05/END-05 marker lines (markers excluded):
BEGIN-05
/code-review on the commit range 6a70bbda5fa087f228bb33e126849caa3d28130d..6746708596c7166d44d11e8e436bde8398be4a12 (main..feature/search-api), cloned from /tmp/cr-run.0xfme1Ia/repo/repo.bundle into a new empty directory. Review it against workstreams/search-api-round2.md@ff7e1e168902469290c11a45de971fef5db2d5a0 (local `orchestration` branch, worktree /tmp/cr-run.0xfme1Ia/orch), and read only its Ask, Scope and Decisions sections, not Notes. Make no code changes. Write the full review to /tmp/cr-run.0xfme1Ia/repo/outputs/review-round2.md. For each finding, give its severity, file:line, and a repro command with raw output, or mark it UNPROVEN. Give a merge-ready verdict and list what you left out. If the review can't be done as specified, stop and report why.
END-05

Report the three paths written.
