Fix check, no code changes, don't spawn agents. Clone /tmp/cr-run.t8cHjpMu/repo/repo.bundle into a fresh empty directory. For each finding below, run its repro (the scripts are in /tmp/cr-run.t8cHjpMu/repo/repro/; run them with `python -I`) against the clone checked out at tag round-1, at tag round-2, and at the tip of feature/search-api, and run the project's test suite at round-2 and at the tip. Judge only these findings: for each, give FIXED or NOT FIXED with the exact commands and raw output. Also report whether round-2 and the feature/search-api tip differ (and the diff if so), and anything you skipped or couldn't run. If it can't be done as specified, stop and report why.

Findings, verbatim from the round-1 review:
- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)
