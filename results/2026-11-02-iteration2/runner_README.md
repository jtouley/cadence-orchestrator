# clean-review eval, iteration 2 (2026-11-02)
Arms: old_skill = skills/tpm at main 13a9a21; new_skill = skills/tpm at review-blind-notes 012d107 (kit installed from that commit with
`node bin/cadence-orchestrator.mjs --target claude --repo <clone>` and committed as the setup commit).
Cases: evals/{first-review-hides-suspected-bug,second-round-hides-prior-findings,spec-review-hides-weak-spots} as of 012d107
(cases.csv status: exploratory; second-round is author_read_skill=yes). No local edits to cases or graders.
Graders: deterministic = evals/scripts/det_grade_clean_review.py @012d107 over outputs/subagent-prompt-*.md (verdict) and the transcript's
Agent prompts (reported); judgment = one fresh `claude -p` grader per run reading skill-creator agents/grader.md and only copies of the
saved prompts in a random-token directory (blind to arm).
Runner: same as iteration-1 (fresh mktemp -d parent + full clone of the case bundle per run, push URL no-push, allowlisted env,
CLAUDE_AUTO_BACKGROUND_TASKS unset, CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0, setup commit, diff against it).
Pilots: ../pilots-iteration-2/limits.txt → first-review 1200 s, second-round 600 s, spec-review 600 s.
Invalid runs: none. Timeouts: none. Isolation: isolation_check.txt, all PASS.
Earlier, stopped iteration-2 attempt (kits 8f95f9a/c7e4ad6): _superseded/ (not graded).
Files: summary_stats.txt (Wilson intervals, per-assertion), leak_prompt_types.txt (which prompt kind each leak came through, heuristic).
