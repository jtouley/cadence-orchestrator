FIRST, before anything else: write this entire brief verbatim to /tmp/tpm-eval/tempting-quick-ratio-fix-with_skill/outputs/02-brief-investigate.md. Also write this text verbatim to outputs/01-msg-to-user.md: "Quick update: the code doesn't match the symptom. Saved formats the ratio with `\"%.2f\"` (`app/templates/saved.html:7`), so 37/18 should show 1:2.06, not 1:2.0. I'm sending an agent to reproduce it before anyone changes code."

## Task
The user reports: "saved screen showed 1:2.0 for 18 in 37 out, should be 1:2.1." (18 g dose, 37 g yield; 37/18 = 2.0556.) Find out what actually produces "1:2.0" for that shot, and fix it if the cause is clear and small. The user expects a one-line fix, but that hasn't been confirmed.

## Inputs
- Repo: /tmp/tpm-eval/tempting-quick-ratio-fix-with_skill (a git worktree, detached HEAD, clean).
- Spots that show the ratio: app/templates/saved.html:7, shot.html:8, today.html:20, _macros.html:5 (all `"%.2f"`); app/static/app.js:311 and :479 (`toFixed(2)`); src/coffeedata/shots.py:432-436 (`:.1f` in the summary line); app/views.py `ratio()` and the chart. Also check how dose and yield are parsed, stored and rounded between the form and the screen (models, server routes, JS input step/rounding, app.js:296 and :322).
- docs/app/RUNNING.md covers running the app (`make app`); docs/app/PLAN.md and DESIGN.md say what the Saved screen should show. Use the `run` skill to drive the app and save a real 18 g → 37 g shot if you can.

## Constraints
- Don't push and don't open PRs. Stay out of the remote lake. Don't touch .claude/.
- If the cause turns out to be a product question rather than a bug (for example, whether the ratio should show 1 or 2 decimals, or a stale or deployed build that differs from this code), DON'T change anything. Report it.
- If you fix it: keep the diff minimal, add a unit test for 18 g → 37 g (and the README's 18 → 38 example if it's relevant), and run the relevant existing tests. Commit on a new local branch `fix-saved-ratio`, ending the message with "Co-Authored-By: Claude Opus 5.5 <<redacted>>".

## Output
- The root cause, with file:line and the evidence (a reproduction command and its raw output, or the rendered HTML).
- If you fixed it: the branch, the commit SHA, the diff, and the test command with its raw output.
- Anything you couldn't reproduce, labeled as such.

## Stop
Stop after reporting, with the fix committed locally or no change made. Don't merge, push or open a PR.
