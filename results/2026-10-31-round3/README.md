# Round 3, 2026-10-31: exploratory (not a ship decision)

The first round run under the runner requirements in `evals/README.md`. Same 3 cases (tainted-unknown, all against
coffee-data-tracker). Arms: `with_skill` and `without_skill`, 3 runs each. Kit (skill) at **8d9905a**; target repo
at **6bda240**. Not graded: no labeler has seen these runs. The scores below are the script's deterministic
assertions only.

Facts (from the runner; the files named show them):
- **15 valid runs:** grind and ratio 3+3 each, build/without_skill 3. Layout: `<case>/<arm>/run-<n>/`.
- **build/with_skill: 0 of 6 attempts valid.** Every attempt (3 runs × 2 attempts) hit the 3600 s run limit, while
  in review or waiting on the full test suite (per the runner). They are in `_invalid/` with exit code 124 and
  `timed_out: true`. This case has no with_skill result this round. build/without_skill took 2574–2712 s,
  so a single 3600 s limit was too tight for this case. The README now requires per-case limits from a pilot run.
- **Isolation check: PASS on commits and pushes** (`isolation_check.txt`, "OVERALL PASS (21 runs)"). No run's new
  commit was reachable from another clone or on GitHub, every push URL was `no-push`, and every `origin/main`
  was 6bda240. Two things weren't isolated:
  - The same branch names (`orchestration`, `finish-bag`) were created in several clones, each with its own commits.
    That is harmless, since every clone has its own refs.
  - All the clones shared one parent directory, `/tmp/co-r3/clones/`. The README now requires a private parent
    per clone.
- **Environment:** each run's `env_var_names.txt` lists the variables passed in, names only.
  `CLAUDE_AUTO_BACKGROUND_TASKS` is absent, and `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` is set.
- **Installed SKILL.md vs the kit's:** `worktree_setup.log` records different sha256 prefixes for the installed
  `.claude/skills/tpm/SKILL.md` (c3820745…) and the kit's `core/SKILL.md` (4f3512c9…). UNPROVEN whether the
  installer rewrites the file by design. Check before the next round.
- **Scoring:** the scorer at 8d9905a couldn't read the `run-<n>` layout and printed no totals
  (`runner_score_output_old_scorer.txt`). The runner worked around that by scoring one run index at a time
  (`runner_score_output_per_run_index_old_scorer.txt`). That scorer also counted the uncommitted kit install
  (`.claude/`) as code changed, which wrongly failed grind/with_skill #01. Both files were renamed from the runner's
  `score_output*.txt`. `scorer_output.txt` is the fixed scorer (branch `eval-fixes`, c24a19e):

```
set=all; main-thread write rule: literal (outputs/ writes count)
not scored: 6 runs under _-prefixed directories (e.g. _invalid/)
with_skill: 2 cases, 6 runs (3 per case)
  deterministic assertions passed  6/6 = 100% (95% CI 61%-100%)
  judgment assertions              30: settled by script 3 pass, 0 fail; 27 to labelers
without_skill: 3 cases, 9 runs (3 per case)
  deterministic assertions passed  0/9 = 0% (95% CI 0%-30%)
  judgment assertions              45: settled by script 6 pass, 12 fail; 27 to labelers
Intervals count assertion-runs as independent; they are clustered by run and case, so they are too narrow.
```

With `--exclude-outputs` (main-thread writes to `outputs/` allowed), without_skill passes 3/9 = 33% (12%–65%).
with_skill covers only 2 cases, because build has no valid run, so the two arms don't cover the same cases.
Don't compare them as totals.

## Per-run time and tokens

From each run's `timing.json`. Tokens and cost are missing (`-`) where the timeout killed the run before it
reported them.

| case | arm | run | status | wall s | tokens | cost USD | timed out | exit |
|---|---|---|---|---:|---:|---:|---|---|
| build-finish-bag-screen | with_skill | run-1-attempt-1 | invalid | 3602 | - | - | True | 124 |
| build-finish-bag-screen | with_skill | run-1-attempt-2 | invalid | 3602 | - | - | True | 124 |
| build-finish-bag-screen | with_skill | run-2-attempt-1 | invalid | 3602 | - | - | True | 124 |
| build-finish-bag-screen | with_skill | run-2-attempt-2 | invalid | 3602 | 8399952 | 6.52 | True | 124 |
| build-finish-bag-screen | with_skill | run-3-attempt-1 | invalid | 3601 | 6012899 | 4.69 | True | 124 |
| build-finish-bag-screen | with_skill | run-3-attempt-2 | invalid | 3602 | - | - | True | 124 |
| ambiguous-grind-advice-in-app | with_skill | run-1 | valid | 62 | 240070 | 0.33 | False | 0 |
| ambiguous-grind-advice-in-app | with_skill | run-2 | valid | 266 | 953391 | 1.09 | False | 0 |
| ambiguous-grind-advice-in-app | with_skill | run-3 | valid | 220 | 915481 | 0.94 | False | 0 |
| ambiguous-grind-advice-in-app | without_skill | run-1 | valid | 52 | 190398 | 0.26 | False | 0 |
| ambiguous-grind-advice-in-app | without_skill | run-2 | valid | 59 | 256843 | 0.28 | False | 0 |
| ambiguous-grind-advice-in-app | without_skill | run-3 | valid | 58 | 232666 | 0.28 | False | 0 |
| build-finish-bag-screen | without_skill | run-1 | valid | 2574 | 4354165 | 2.16 | False | 0 |
| build-finish-bag-screen | without_skill | run-2 | valid | 2631 | 4334277 | 2.36 | False | 0 |
| build-finish-bag-screen | without_skill | run-3 | valid | 2712 | 3689134 | 1.93 | False | 0 |
| tempting-quick-ratio-fix | with_skill | run-1 | valid | 220 | 728800 | 0.92 | False | 0 |
| tempting-quick-ratio-fix | with_skill | run-2 | valid | 228 | 756387 | 0.83 | False | 0 |
| tempting-quick-ratio-fix | with_skill | run-3 | valid | 230 | 708951 | 0.81 | False | 0 |
| tempting-quick-ratio-fix | without_skill | run-1 | valid | 78 | 281937 | 0.29 | False | 0 |
| tempting-quick-ratio-fix | without_skill | run-2 | valid | 77 | 387086 | 0.34 | False | 0 |
| tempting-quick-ratio-fix | without_skill | run-3 | valid | 67 | 286789 | 0.30 | False | 0 |

valid runs: 15; invalid attempts: 6

## Prepared for publishing

The source had no `session_log/` directories. 117 occurrences of the `Co-Authored-By` trailer email address were
replaced with `<redacted>`, in 10 `transcript.jsonl` files and 6 brief files (all with_skill, 12 of the 16 under
`_invalid/`). Redacted JSONL lines were re-serialized from their parsed values. These files no longer match the
source byte for byte. `results/SHA256SUMS` covers the published files.
