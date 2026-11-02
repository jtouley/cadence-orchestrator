# clean-review eval, iteration 3 (2026-11-02)
Arms: old_skill = skills/tpm at main 13a9a21; new_skill = skills/tpm at review-blind-notes b361b96 (kit installed from that commit, committed as setup).
Cases: evals/ as of main 13a9a21. prompt.md, place-files.sh, case.yaml and files/ are byte-identical on 13a9a21, b361b96 and
grader-reviewer-reach; only grader texts 02-05 (leak checks) differ on grader-reviewer-reach. eval_metadata uses the grader-branch texts.
Runtime inputs unchanged since iteration-2, so no pilots: limits from ../pilots-iteration-2/limits.json (first 1200 s, second 600 s, spec 600 s).
Grader: evals/scripts/det_grade_clean_review.py at grader-reviewer-reach 35d9f8191cbace07166afab856d5e8465ce383f2 (fetched at grading time). Judgment: one blinded claude -p grader per run.
Runner: unchanged (fresh mktemp -d + full bundle clone per run, push no-push, allowlisted env, CLAUDE_AUTO_BACKGROUND_TASKS unset,
CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0, setup commit). Invalid runs: none. Isolation: isolation_check.txt, all PASS.
iteration-2 regrade with the same grader: ../iteration-2/_regrade-35d9f81/ (0 verdicts changed).
reach.json: every saved prompt's in/out-of-reach status and reason as the grader reported it.
