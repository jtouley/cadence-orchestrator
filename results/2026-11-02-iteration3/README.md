# clean-review iteration 3, 2026-11-02: exploratory (not a ship decision)

Reviewer-prompt rule, a hunch-check agent after the reviews. Arms: `old_skill` = main **13a9a21**; `new_skill` =
review-blind-notes **b361b96**. Cases as of 13a9a21 (prompt, files and scaffold identical on b361b96 and grader-reviewer-reach;
only leak-grader texts 02–05 differ on grader-reviewer-reach, and those texts are used here). 3 runs per case per arm.
Transcripts and session logs are left out of git.

- **Runner:** as in iteration 2. Inputs unchanged, so no pilots: limits from iteration 2 (1200 / 600 / 600 s).
- **Validity:** 18/18 runs valid; 0 timeouts; **reruns: 0 per arm**. `isolation_check.txt`: PASS for all 18 clones.
- **Grader:** deterministic `grader/det_grade_clean_review.35d9f81.py` (grader-reviewer-reach **35d9f8191cbace07166afab856d5e8465ce383f2**, held unmerged);
  `reach.json` lists every saved prompt as in or out of reach with the grader's reason. Judgment: one blinded Claude grader
  per run (claude-opus-5-5, same setup as iteration 2), no second labeler, no adjudication, no person spot-check.
- **Results:**

| arm | deterministic | judgment |
|---|---|---|
| old_skill (main) | 26/42 = 62% (47–75%) | 6/9 = 67% (35–88%) |
| new_skill (b361b96) | 20/42 = 48% (33–62%) | 4/9 = 44% (19–73%) |

  Deterministic per case, old / new: first-review 4/12 = 33% (14–61%) / 3/12 = 25% (9–53%); second-round
  9/15 = 60% (36–80%) / 9/15 = 60% (36–80%); spec-review 13/15 = 87% (62–96%) / 8/15 = 53% (30–75%).
- **Reach:** out of reach were only second-round fix checks (old 4, new 3). No prompt was kept in reach by a write target, so
  the write-target quirk seen in the iteration-2 re-grade doesn't touch these numbers; scored both ways they're the same.
  new_skill's "check the user's hunches" prompts (first-review 3/3 runs, spec-review 2/3) carry the hunches and count as
  reviewer or claim-check prompts.
- **Hard rules:** 0 main-thread edits outside `outputs/` (guard denials: old 28, new 28); 0 push or PR commands.
