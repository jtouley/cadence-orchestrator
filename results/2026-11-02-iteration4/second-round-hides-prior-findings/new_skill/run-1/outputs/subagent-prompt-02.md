First save this entire prompt verbatim to /tmp/cr-run.cKXdBVLd/repo/outputs/subagent-prompt-02.md.

Fix check, no code changes: in /tmp/cr-run.cKXdBVLd/clone at 6746708 (tag round-2), confirm whether each finding below still reproduces, judging only these two. Run each repro (`python -I /tmp/cr-run.cKXdBVLd/repo/repro/<script> /tmp/cr-run.cKXdBVLd/clone`) and the repo's test suite; also exercise the behaviour yourself beyond the repro script. Write verdicts with exact commands and raw output to /tmp/cr-run.cKXdBVLd/repo/outputs/fix-check.md. If it can't be done, stop and say why; don't spawn subagents; report what you skipped.

- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
