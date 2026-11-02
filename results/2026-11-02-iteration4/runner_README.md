# clean-review eval, iteration 4 (2026-11-02)
Arms: old_skill = skills/tpm at main 13a9a21; new_skill = skills/tpm at hunch-hold 134a88f (kit installed from that commit, committed as setup).
Cases and grader: evals/ at main 13a9a21 (grader evals/scripts/det_grade_clean_review.py @13a9a21, identical to 012d107's).
evals/ is identical on hunch-hold 134a88f (git diff 13a9a21 134a88f -- evals/ is empty). Inputs unchanged, so no pilots: limits from
../pilots-iteration-2/limits.json (first 1200 s, second 600 s, spec 600 s). Judgment: one blinded claude -p grader per run.
Runner unchanged. Invalid runs: none. Isolation: isolation_check.txt, all PASS.
leak_prompt_types.txt: which saved prompt carried each planted phrase, with a heuristic type (fix-check uses the grader's own rule).
