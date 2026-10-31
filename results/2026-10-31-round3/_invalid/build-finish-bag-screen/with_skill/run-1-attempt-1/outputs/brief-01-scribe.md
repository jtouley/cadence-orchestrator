You are the scribe. Repo: /tmp/co-r3/clones/build-finish-bag-screen-with_skill-1. Sandbox run: never push, never open PRs, don't touch the main checkout's working tree beyond the outputs/ folder.

1. Save this exact brief (everything in this message) to /tmp/co-r3/clones/build-finish-bag-screen-with_skill-1/outputs/brief-01-scribe.md.
2. Create a local branch `orchestration` from main in a git worktree at /tmp/co-r3/clones/build-finish-bag-screen-with_skill-1-orch (git worktree add -b orchestration <path> main). If it exists, reuse it.
3. In it, write `workstreams/finish-bag.md` with these sections, content verbatim where quoted:

## Ask (verbatim, user, 2026-10-31)
"app has no way to finish a bag. add a Finish button on the bag page: marks it finished, drops it from Today and the bag picker on Log shot, still shows in Coffees. no deletes, write a record like retract does. tests pls"
"(sandbox run: don't push, don't open PRs. write every message you send me, and every brief you send a subagent, to the outputs folder)"

## Scope
- In: a Finish button on the bag page (the page a bag opens to). Tapping it marks the bag finished by appending a new bags record (same bag_id, `finished_on` set), the same append-only way retract/corrections write new records; nothing is deleted or rewritten. A finished bag no longer appears on Today or in the bag picker on Log shot. It still appears in Coffees (with its shots). Tests covering each of those behaviours, plus that no delete happens and another user can't finish someone else's bag.
- Out: un-finishing / reopening, an undo strip for finish, changing the Edit bag form, dbt models, lake data, deploy, design changes beyond the button and its notice.
- Target: this repo, local branch `finish-bag` off main @ <main SHA, fill in from `git rev-parse main`>. Done = commits on `finish-bag`, full test suite run with output recorded, reviewed. Stop at: local branch committed. No push, no PR (sandbox).
- Judged against: this Ask; docs/app/PLAN.md (bags schema `finished_on` "set by a later record when the bag is done"; "Corrections and retractions stay new records"; per-user access rules); docs/app/DESIGN.md (Edit bag, Notice sections) for UI conventions.
- If it can't be done as specified, stop and report why; "blocked" is a valid result.

## Decisions
- 2026-10-31, user: "no deletes, write a record like retract does."
- 2026-10-31, user: "sandbox run: don't push, don't open PRs."

## Status and evidence
(empty for now)

4. Write `workstreams/finish-bag.tasks.json`: a JSON array with tasks
   {"id":"impl","owner":"implementer","state":"assigned","doc_sha":null,"evidence":null,"tokens":null},
   {"id":"review-spec","owner":"reviewer-spec","state":"assigned","doc_sha":null,"evidence":null,"tokens":null},
   {"id":"review-quality","owner":"reviewer-quality","state":"assigned","doc_sha":null,"evidence":null,"tokens":null}
5. Commit both on `orchestration` (message "finish-bag: workstream doc and tasks", ending with a blank line then "Co-Authored-By: Claude Opus 5.5 <<redacted>>"). Then set doc_sha on all three tasks to that commit SHA and commit again.
Reply with: the main SHA, the doc commit SHA, and the worktree path. Nothing else.
