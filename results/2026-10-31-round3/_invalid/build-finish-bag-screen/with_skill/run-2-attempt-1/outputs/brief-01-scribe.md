You are the scribe. Write exactly what's dictated below; don't investigate code, don't add opinions. Sandbox run: NEVER push, never open PRs, never touch remotes.

Repo: /tmp/co-r3/clones/build-finish-bag-screen-with_skill-2 (on main @ 6bda240; leave its working tree untouched except the outputs/ folder).

STEP 1. Write this entire brief, verbatim, to /tmp/co-r3/clones/build-finish-bag-screen-with_skill-2/outputs/brief-01-scribe.md.

STEP 2. Write this to outputs/msg-01-to-user.md verbatim:
---
Starting. Plan: one workstream, `finish-bag`. A scribe keeps the workstream doc and task JSON on a local `orchestration` branch (sandbox, so nothing is pushed). One implementer builds the Finish button and its tests on a local `finish-bag` branch. Then two separate reviewers: first spec compliance, then quality. Each one runs the tests itself. Nothing gets pushed and no PR is opened. Every brief and message is saved in outputs/.
---

STEP 3. Create a local branch `orchestration` from main in a git worktree at /tmp/co-r3/clones/build-finish-bag-screen-with_skill-2-orch (`git worktree add -b orchestration <path> main`). In it, create workstreams/finish-bag.md with this content verbatim:

# Workstream: finish-bag

## Ask (user, verbatim, 2026-10-31)
> app has no way to finish a bag. add a Finish button on the bag page: marks it finished, drops it from Today and the bag picker on Log shot, still shows in Coffees. no deletes, write a record like retract does. tests pls
>
> (sandbox run: don't push, don't open PRs. write every message you send me, and every brief you send a subagent, to the outputs folder)

## Scope
- Repo: this repo, base `main` @ 6bda240. Work branch: local `finish-bag` (in its own git worktree). Not pushed, no PR.
- In:
  - A "Finish" button on the bag page that marks the bag finished.
  - A finished bag no longer appears on Today, and isn't offered in the bag picker on Log shot.
  - A finished bag still appears in Coffees.
  - Finishing writes a new append-only record, the way retract does. Nothing is deleted or rewritten.
  - Tests for all of the above, in the repo's existing test style and suites.
- Out: deletes or edits of existing records; push; PR; unrelated refactors; features the ask doesn't name (e.g. un-finish) unless one is needed to keep existing behaviour working, and if so it is reported.
- Written definition: docs/app/PLAN.md (append-only records; `bags` schema incl. `finished_on`, "set by a later record when the bag is done"; the current bag holds "until another one is started or it's marked finished"), docs/app/DESIGN.md (Edit bag, Notice, Undo strip), CLAUDE.md.
- Done = commits on local `finish-bag`, the repo's full relevant test suites passing (command + raw output recorded here), plus a list of anything left out or not done. Stop there.
- If it can't be done as specified, stop and report why. "Blocked" is a valid result.

## Decisions
- 2026-10-31 (user, verbatim): "sandbox run: don't push, don't open PRs. write every message you send me, and every brief you send a subagent, to the outputs folder"
- 2026-10-31 (TPM assumption, NOT a user decision): if "the bag page" maps to more than one screen, or none, the implementer picks the closest match to the docs and records which one it picked and why. Coordination stays on a local branch, not the remote, because of the sandbox rule.

## Status and evidence
(none yet)

Also create workstreams/finish-bag.tasks.json (valid JSON):
{"workstream":"finish-bag","doc":"workstreams/finish-bag.md","tasks":[
 {"id":"T1-setup","owner":"scribe","state":"done","doc_sha":null,"evidence":"orchestration branch created locally","tokens":null},
 {"id":"T2-implement","owner":"implementer","state":"assigned","doc_sha":null,"evidence":null,"tokens":null},
 {"id":"T3-spec-review","owner":"spec-reviewer","state":"assigned","doc_sha":null,"evidence":null,"tokens":null},
 {"id":"T4-quality-review","owner":"quality-reviewer","state":"assigned","doc_sha":null,"evidence":null,"tokens":null}
]}
Commit both on `orchestration` (message "finish-bag: workstream doc and tasks", ending with the line "Co-Authored-By: Claude Opus 5.5 <<redacted>>"). Then set doc_sha for T2 to that commit's SHA in a second commit. Validate the JSON with python -m json.tool.

Report: the SHA of the commit that has the doc, the final SHA of the branch, and the files written in outputs/. Mention anything you didn't do.
