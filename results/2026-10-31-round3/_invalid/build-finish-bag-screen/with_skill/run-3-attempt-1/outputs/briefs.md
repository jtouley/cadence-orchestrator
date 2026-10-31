## 1. scribe — workstream setup

You are the scribe. Repo: /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3. Sandbox run: never push, never open PRs, never touch any remote. Do not modify the main checkout's working tree except files under its `outputs/` folder.

Task A — orchestration branch (local only):
1. Create a local branch `orchestration` from `main` (if absent) and check it out in a worktree at /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-orch.
2. In that worktree write `workstreams/finish-bag.md` with EXACTLY this content:

---
# Workstream: finish-bag

## Ask (user, verbatim, 2026-10-31)
> app has no way to finish a bag. add a Finish button on the bag page: marks it finished, drops it from Today and the bag picker on Log shot, still shows in Coffees. no deletes, write a record like retract does. tests pls

## Scope
- Target repo: this repo (`app/`). Base: `main` @ 6bda240. Work branch: `finish-bag` (local; sandbox run, no push, no PR).
- In: a Finish button on the bag page; tapping it writes a new append-only `bags` record for that bag with `finished_on` set (same pattern as retract writes a new record — no deletes, no edits to existing records); a finished bag no longer appears on Today or in the Log shot bag picker; it still appears in Coffees; automated tests covering each of those behaviours.
- Out: deleting or editing existing records; un-finishing a bag; changes to dbt, the lake schema, or other screens beyond what the ask requires.
- Definition the work is judged against: the Ask above; `docs/app/PLAN.md` (the `bags` table: "`finished_on` | date | set by a later record when the bag is done"; Non-goals: "Editing or deleting lake files. Corrections and retractions stay new records."; "The bag becomes the 'current bag' until another one is started or it's marked finished."); `CLAUDE.md`.
- Done = commits on `finish-bag`, the full test suite run with output recorded, independent spec + quality review passed. Stop there: not merged, not pushed.

## Decisions
- 2026-10-31 (user): "no deletes, write a record like retract does."
- 2026-10-31 (user): "sandbox run: don't push, don't open PRs."

## Status and evidence
(none yet)
---

3. Write `workstreams/finish-bag.tasks.json` as a JSON array with these tasks, each having fields id, owner, state, evidence (null), tokens (null), doc_sha (null):
   - {"id":"implement","owner":"implementer-1","state":"assigned"}
   - {"id":"verify-tests","owner":"verifier-1","state":"assigned"}
   - {"id":"review-spec","owner":"reviewer-spec-1","state":"assigned"}
   - {"id":"review-quality","owner":"reviewer-quality-1","state":"assigned"}
   Validate it parses (python3 -m json.tool).
4. Commit both files on `orchestration` ("Add finish-bag workstream"). Then set doc_sha on every task to that commit's short SHA, commit again ("Pin finish-bag doc sha").

Task B — outputs log, in /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3/outputs/:
- Create `messages-to-user.md` and append these two messages, each under a heading `## <n>` with the text verbatim:
  1: "Reading the app's plan doc for any decisions already made about finishing bags, then I'll set up the workstream."
  2: "No decisions are missing. PLAN.md already says `finished_on` is \"set by a later record when the bag is done\", so the work isn't blocked on anything from you. Next I'm having a scribe agent set up the workstream doc and the outputs log."
- Create `briefs.md` and append this entire prompt you received, verbatim, under the heading `## 1. scribe — workstream setup`.

Report back: the pinned doc SHA (from step 1.4's first commit), the final orchestration HEAD SHA, and anything you couldn't do. If anything can't be done as specified, stop and report why.

## 2. implementer-1 — implement

First, append this whole prompt verbatim to /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3/outputs/briefs.md under the heading `## 2. implementer-1 — implement`.

Implement `workstreams/finish-bag.md@7bad08a` (branch `orchestration` of /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3; read it with `git show 7bad08a:workstreams/finish-bag.md`) on a new local branch `finish-bag` from `main`, in a worktree at /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-finish. Out of scope: un-finish, dbt, the lake schema, pushing, PRs. Don't spawn agents. Commit your work, then report back: commit SHAs, the exact test command and its raw summary output, and a "left out / not done" list. If it can't be done as specified, stop and report why. Don't weaken or skip existing tests.

## 4. reviewer-spec-1 — spec review

First, append this whole prompt verbatim to /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3/outputs/briefs.md under the heading `## 4. reviewer-spec-1 — spec review`.

Spec-compliance review of `git diff main 58b8bb8` (branch `finish-bag`, worktree /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-finish) against `workstreams/finish-bag.md@7bad08a` (`git show 7bad08a:workstreams/finish-bag.md`). Not code style/quality, no edits or commits, don't spawn agents. Check every part of the Ask is met and nothing beyond it was added, exercising it yourself (run the app or the relevant tests; use a scratch copy, not the worktree). Also judge whether each item on the implementer's left-out list is acceptable: (1) browser test skipped, Playwright not installed; (2) one tap, no confirmation or undo strip — an existing "Still using it" on Edit bag sets it back; (3) offline, the button stays visible until the queued write syncs; (4) un-finish/dbt/schema out of scope. Report PASS/FAIL per requirement with evidence (commands + output), and any blockers.

## 3. verifier-1 — verify tests

First, append this whole prompt verbatim to /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3/outputs/briefs.md under the heading `## 3. verifier-1 — verify tests`.

Verify tests for `workstreams/finish-bag.md@7bad08a` (`git show 7bad08a:workstreams/finish-bag.md` in /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3) against branch `finish-bag`@58b8bb8 in worktree /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-finish. Read-only: no edits, no commits, no review of code quality, don't spawn agents. Run the full suite and lint, confirm the interpreter/venv and imported `app` package are this worktree's, confirm the new tests fail on `main`'s app code (e.g. by checking out only the tests onto a scratch copy of main), and try to get the skipped browser test running (e.g. install Playwright in a scratch location) — if impossible, say why. Report exact commands and raw output summaries, plus anything you couldn't do.
