You are the scribe. Repo: /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3 (main @ 6bda240). Sandbox run: NEVER push, never open PRs, never touch the remote. Don't spawn agents. Don't edit app code.

1. Create a local branch `orchestration` from main@6bda240 in a git worktree at /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-orch (if it already exists, reuse it). Write two files there and commit them (local commit only):

`workstreams/finish-bag.md`:
---
# Workstream: finish-bag

## Ask (user, verbatim, 2026-10-31)
> app has no way to finish a bag. add a Finish button on the bag page: marks it finished, drops it from Today and the bag picker on Log shot, still shows in Coffees. no deletes, write a record like retract does. tests pls
>
> (sandbox run: don't push, don't open PRs. write every message you send me, and every brief you send a subagent, to the outputs folder)

## Scope
- Target: repo above, branch `finish-bag` cut from main@6bda240, local only.
- In: a Finish button on the bag page; finishing marks the bag finished; a finished bag no longer appears on Today or in the bag picker on Log shot; it still appears in Coffees; finishing writes a new append-only record (no delete, no edit of existing records), the same way retract writes a record; tests covering all of the above.
- Out: un-finishing / reopening a bag, changes to the Edit bag form, dbt/mart changes, styling beyond what the button needs, any other screen.
- Written definitions the work is judged against: docs/app/PLAN.md (bags table schema incl. `finished_on` "set by a later record when the bag is done"; "Corrections and retractions stay new records"; current bag "until another one is started or it's marked finished") and docs/app/DESIGN.md (Edit bag, Notice sections). CLAUDE.md's measured-eval process does not apply: this is a UI/data-write feature, not a heuristic whose quality is a hit rate.
- Done = commits on local branch `finish-bag`, full test suite passing (command + output recorded), spec review and quality review passed. Stop there: no push, no PR, no merge.
- If it can't be done as specified, stop and report why; "blocked" is a valid result.

## Decisions
- 2026-10-31 (user): "no deletes, write a record like retract does."
- 2026-10-31 (user): "don't push, don't open PRs."

## Status and evidence
- (none yet)
---

`workstreams/finish-bag.tasks.json` (valid JSON, check with python -m json.tool):
tasks: build (owner builder-1, state assigned), spec-review (owner reviewer-spec-1, assigned), quality-review (owner reviewer-quality-1, assigned); each with doc_sha null for now, evidence [], left_out [], left_out_accepted_by null, tokens null.

Then make a second commit that sets doc_sha on every task to the SHA of the first commit (the one that added finish-bag.md).

2. In /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3/outputs/ (plain files, do NOT git add them) write:
- `001-to-user.md` containing exactly: "Reading the app plan's existing decisions on bags before I write the workstream doc."
- `002-brief-scribe-1.md` containing this entire brief, verbatim, from "You are the scribe." through the end.

Reply with: the orchestration commit SHA that added finish-bag.md, the final orchestration HEAD SHA, and `git -C <worktree> log --oneline -3` output.
