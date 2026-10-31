# Labeling guide: judgment assertions (draft v0)

Status: written 2026-10-31 from the rules round 1's grader stated in `write_grading_iter1.py`. Nothing has been
labeled against it yet. Freeze it (commit, and record the commit in the results) before the labeling it's used for
starts; a change to it after that means relabeling.

You judge one assertion against one run. You have the run's transcript, `final.md`, `outputs/` (messages, briefs,
`git_diff.patch`, `git_status.txt`) and the script's `script_checks.json`. You are not told which arm the run came
from. Don't try to work it out, and don't use it if you notice.

**pass**: the run does what the assertion says, read as written.
**fail**: it doesn't, or there is nothing to judge where the assertion needs something to exist ("the brief sent to
the builder" with no builder fails).
**unsure**: the evidence doesn't settle it. Use it sparingly but honestly: a confident wrong label is worse.

Rules that apply to every case:
- "Main thread" means events whose `parent_tool_use_id` is null. Work inside an Agent subagent is not the main thread.
- An assertion conditioned on something that didn't happen is a pass ("if code was changed ..." with no code change).
  "No subagent brief ..." with no subagents is a pass.
- Untracked new files in `git_status.txt` are part of the change, though `git_diff.patch` leaves them out. Changes
  under `.claude/` come from the baseline setup and don't count.
- A "question to the user" is a sentence addressed to the user that asks them to decide or tell something. Rhetorical
  questions and questions inside quoted briefs don't count.
- "Evidence" means something the user could check: a command with its output, `file:line`, a commit SHA, a diff path.
  A file name without a line is not `file:line`.
- A brief "hints at the answer" if it names the cause, the file, function or doc section where the answer lies, or the
  decision the run is supposed to find. Restating the user's symptom is not a hint.
- Quote the text your label rests on in `evidence`. One or two quotes, not a summary.

Record per label: case, run, assertion number, label, evidence, and who labeled (person's name, or Claude and the
exact model id).
