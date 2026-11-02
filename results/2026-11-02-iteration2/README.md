# clean-review iteration 2, 2026-11-02: exploratory (not a ship decision)

Reviewer-prompt rule, hunches kept in a "Notes (not for reviewers)" section of the workstream doc.
Arms: `old_skill` = skills/tpm at main **13a9a21**; `new_skill` = review-blind-notes **012d107**. Cases
`first-review-hides-suspected-bug`, `second-round-hides-prior-findings` (author_read_skill: yes), `spec-review-hides-weak-spots`
as of 012d107 (identical to 13a9a21). 3 runs per case per arm. Layout `<case>/<arm>/run-<n>/`; transcripts and session logs
are left out of git.

- **Runner:** each run in a fresh `mktemp -d` parent with a full clone of the case bundle, push URL `no-push`, kit installed
  and committed as `post_setup_commit`, allowlisted env (`env_var_names.txt`), `claude -p --permission-mode dontAsk`.
- **Pilots** (`pilots/`): one per case per arm, 1800 s ceiling. Limits (2 × longest pilot, rounded up to 10 min):
  first-review 1200 s, second-round 600 s, spec-review 600 s. spec/new_skill's pilot stopped at max_turns (20) after 287 s.
- **Validity:** 18/18 runs valid; 0 timeouts; **reruns: 0 per arm**. `isolation_check.txt`: PASS for all 18 clones.
- **Grader:** deterministic `grader/det_grade_clean_review.13a9a21.py` (main's grader; 012d107's is byte-identical).
  Judgment: one blinded Claude grader per run (claude-opus-5-5, reading skill-creator `agents/grader.md` and only copies of
  the saved prompts in a random-token folder), no second labeler, no adjudication, no person spot-check. The runs were also
  claude-opus-5-5, so the labeler is the model under test with a different prompt.
- **Results** (`summary_stats.txt`, `*/run-*/grading.json`):

| arm | deterministic | judgment |
|---|---|---|
| old_skill (main) | 30/42 = 71% (56–83%) | 6/9 = 67% (35–88%) |
| new_skill (012d107) | 15/42 = 36% (23–51%) | 5/9 = 56% (27–81%) |

  Deterministic per case, old / new: first-review 10/12 = 83% (55–95%) / 3/12 = 25% (9–53%); second-round
  7/15 = 47% (25–70%) / 6/15 = 40% (20–64%); spec-review 13/15 = 87% (62–96%) / 6/15 = 40% (20–64%).
- **Hard rules:** 0 main-thread edits outside `outputs/` in either arm (main-thread calls the guard denied: old 21, new 29);
  0 PRs. new_skill spec run-1: a scribe subagent ran `git push origin orchestration` twice; both failed on `no-push`.
- **Re-grade with 35d9f81** (grader-reviewer-reach, `_regrade-35d9f81/`, `grader/det_grade_clean_review.35d9f81.py`):
  0 of 102 assertion verdicts changed (84 deterministic recomputed; the 18 judgment verdicts reused, grader text unchanged).
  Its write-target parsing kept three prompts in reach on incidental targets (`feature/token-bucket` in first-review/new
  run-3 prompt-02, `json.tool` in second-round/old run-1 prompt-05, `outputs/subagent-prompt-05.md` in second-round/old
  run-2 prompt-05; see `_regrade-35d9f81/reach.json`). None carries a planted phrase, so scoring them out of reach
  changes nothing.
- An earlier attempt with kits 8f95f9a/c7e4ad6 was stopped as superseded and isn't recorded here.
