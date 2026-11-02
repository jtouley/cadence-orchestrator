You are the scribe. Local mode: write files only, no commits or pushes. Do exactly these steps, then report the paths and anything you couldn't do.

1. Save this entire prompt, verbatim from "You are the scribe." through the final line, to /tmp/cr-run.IUIMLbzs/repo/outputs/subagent-prompt-02.md.
2. Save the text between the <<<P03 and P03>>> lines, verbatim (markers excluded), to /tmp/cr-run.IUIMLbzs/repo/outputs/subagent-prompt-03.md.
3. Save the text between the <<<P04 and P04>>> lines, verbatim (markers excluded), to /tmp/cr-run.IUIMLbzs/repo/outputs/subagent-prompt-04.md.
4. Run `sha256sum /tmp/cr-run.IUIMLbzs/repo/.cadence/workstreams/search-api-round2.md` and report its output.
5. In /tmp/cr-run.IUIMLbzs/repo/.cadence/workstreams/search-api-round2.tasks.json set both tasks' state to "claimed" (rewrite the whole file, validate it as JSON).

<<<P03
Fix check for .cadence/workstreams/search-api-round2.md@626254b4c1 (sha256 prefix of /tmp/cr-run.IUIMLbzs/repo/.cadence/workstreams/search-api-round2.md; confirm it matches). Clone /tmp/cr-run.IUIMLbzs/repo/repo.bundle into a new empty directory and check out feature/search-api (report its SHA and whether tag round-2 points to it). For each round-1 finding below, run its repro against that checkout and judge only whether it still reproduces; as a control, also run each repro against tag round-1 (if the tag exists) to show it does reproduce there. Also run the repo's test suite at feature/search-api. The repro scripts are /tmp/cr-run.IUIMLbzs/repo/repro/r1_1_cursor_gap.py and /tmp/cr-run.IUIMLbzs/repo/repro/r1_2_like_wildcard.py; run them with `python -I`.

Round-1 findings, verbatim:
- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by page_size - 1.
  Repro: `python repro/r1_1_cursor_gap.py <path to the repo clone>` (prints REPRODUCES and exits 1 while the bug is there)
- R1-2 (medium): LIKE wildcards in the search term aren't escaped, so searching "100%" also matches "1000 done".
  Repro: `python repro/r1_2_like_wildcard.py <path to the repo clone>` (same convention)

Out of scope: fixing anything, editing the repro scripts or tests, changing the clone's history, reviewing anything beyond these two findings. Don't spawn other agents. Write a verdict per finding (FIXED / STILL REPRODUCES / CAN'T TELL) with every command, its raw output and exit code, plus the test-suite command and raw output, to /tmp/cr-run.IUIMLbzs/repo/outputs/fixcheck-round2.md. End your report with what you left out. If it can't be done as specified, stop and report why.
P03>>>

<<<P04
/code-review high on the commit range main..feature/search-api in a fresh clone of /tmp/cr-run.IUIMLbzs/repo/repo.bundle (clone it into a new empty directory and work only in that clone). Review only: no fixes, no commits. Write the full review, including any commands you ran with their raw output, to /tmp/cr-run.IUIMLbzs/repo/outputs/review-round2.md. End with what you didn't cover. If it can't be done as specified, stop and report why.
P04>>>
