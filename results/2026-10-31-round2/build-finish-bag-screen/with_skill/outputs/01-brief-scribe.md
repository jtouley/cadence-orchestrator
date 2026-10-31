You are a scribe. Repo: /tmp/tpm-eval/iteration-2-build-finish-bag-screen-with_skill. SANDBOX: never push, never open PRs, never touch the remote.

Task A — outputs folder (in the repo's working tree, don't commit it). Write these files verbatim:
1. outputs/01-brief-scribe.md containing this entire brief, verbatim.
2. outputs/00-message-to-user.md containing exactly:
"Setting up: a scribe agent will record the plan locally (no push), then an implementer and a separate reviewer take it."

Task B — orchestration branch, local only. Create a local branch `orchestration` from `main` (if it doesn't exist) using a separate git worktree at /tmp/tpm-eval/orch-wt-finish-bag so the main worktree is untouched. Write workstreams/finish-bag.md with the content below, commit it (message "workstreams: finish-bag", ending with the line "Co-Authored-By: Claude Opus 5.5 <<redacted>>"). Do not push. Report the commit SHA and the worktree path.

--- workstreams/finish-bag.md ---
# Finish a bag

## Ask (user, verbatim, 2026-10-31)
> app has no way to finish a bag. add a Finish button on the bag page: marks it finished, drops it from Today and the bag picker on Log shot, still shows in Coffees. no deletes, write a record like retract does. tests pls
>
> (sandbox run: don't push, don't open PRs. write every message you send me, and every brief you send a subagent, to the outputs folder)

## Scope
- Target: this repo, the app under `app/`. Work on a local branch `feature/finish-bag` off `main`. Commit locally. Do NOT push, do NOT open a PR.
- In: a Finish button on the bag page; finishing writes a new record (append-only, the same way retract/corrections do — no edits or deletes of existing lake files); a finished bag no longer appears on Today or in the bag picker on Log shot; it still appears in Coffees (and the coffee/bag page itself). Tests for all of it.
- Out: un-finishing a bag; any change to shots; deleting anything; push/PR.
- Written definitions to judge against: `docs/app/PLAN.md` (the `bags` record schema already defines `finished_on`, "set by a later record when the bag is done"; "Corrections and retractions stay new records"; per-user isolation — one user must not be able to finish another user's bag; offline outbox / `rev` rules for writes); `docs/app/DESIGN.md` for UI; repo `CLAUDE.md`. The CLAUDE.md "measured, not argued" process does not apply: this is a feature, not a heuristic.
- Done means: commits on local `feature/finish-bag`; full test suite run with the command and its raw output recorded below; an independent code review recorded below with any blockers fixed.
- Stop at: local commits reviewed. User says "merge it".

## Decisions
- User (2026-10-31): "no deletes, write a record like retract does." "tests pls." Sandbox: no push, no PRs.
- Orchestrator default, not the user's (2026-10-31), open for the user to override: after the current bag is finished, Today behaves as if that bag never were current (it falls back to whatever Today shows for the next most recent unfinished bag, or the no-bag state). Finishing is idempotent: finishing an already-finished bag does not write a second record or error.

## Status and evidence
- 2026-10-31: workstream opened.
--- end ---
