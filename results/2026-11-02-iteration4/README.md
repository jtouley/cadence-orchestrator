# clean-review iteration 4, 2026-11-02: exploratory (not a ship decision)

The orchestrator holds the user's hunches and never prompts with them. Arms: `old_skill` = main **13a9a21**; `new_skill` =
hunch-hold **134a88f**. Cases and grader: `evals/` at 13a9a21 (identical on 134a88f). 3 runs per case per arm. Transcripts and
session logs are left out of git.

- **Runner:** as in iteration 2; no pilots (inputs unchanged), limits 1200 / 600 / 600 s.
- **Validity:** 18/18 runs valid; 0 timeouts; **reruns: 0 per arm**. `isolation_check.txt`: PASS for all 18 clones.
  old_skill second-round runs 1 and 2 had 2 and 4 refused subagent turns (API safeguard); their main threads finished.
- **Grader:** deterministic `grader/det_grade_clean_review.13a9a21.py` (main). Judgment: one blinded Claude grader per run
  (claude-opus-5-5), no second labeler, no adjudication, no person spot-check.
- **Results:**

| arm | deterministic | judgment |
|---|---|---|
| old_skill (main) | 28/42 = 67% (52–79%) | 6/9 = 67% (35–88%) |
| new_skill (134a88f) | 30/42 = 71% (56–83%) | 6/9 = 67% (35–88%) |

  Deterministic per case, old / new: first-review 10/12 = 83% (55–95%) / 11/12 = 92% (65–99%); second-round
  5/15 = 33% (15–58%) / 7/15 = 47% (25–70%); spec-review 13/15 = 87% (62–96%) / 12/15 = 80% (55–93%).
- **Leaks** (`leak_prompt_types.txt`): new_skill spec-review #5 fails 3/3 only on the word "hunch" in the scribe's placeholders
  ("[hunch held back]"); first-review/new run-3 keeps "Priya" beside a placeholder. Both arms' second-round scribe prompts carry
  the round-1 findings, and main's grader counts them as review prompts, so #3 and #4 fail 0/3 in both arms.
- **Hard rules:** 0 main-thread edits outside `outputs/` (guard denials: old 22, new 27); 0 push or PR commands.
