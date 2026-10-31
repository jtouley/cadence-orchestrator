You are the scribe. First save this brief verbatim (from "You are the scribe." to the end) to /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3/outputs/004-brief-scribe-2.md (don't git add). Never push; don't spawn agents; don't touch app code.

In the orchestration worktree /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-orch, rewrite workstreams/finish-bag.tasks.json (validate with python -m json.tool) and append to the "Status and evidence" section of workstreams/finish-bag.md, then commit locally:
- task `build`: state "claimed" (not done: reviews pending), tokens 113741, evidence ["f191398 on local branch finish-bag (worktree /tmp/co-r3/clones/build-finish-bag-screen-with_skill-3-finish)", "make test → 643 passed, 2 skipped, 1 warning; EXIT=0 (builder-reported, log /tmp/finish-make-test.log)"], left_out:
  1. "No un-finishing/reopening, no Edit bag form change, no dbt/mart change, no other screens, no new styling. Edit bag's existing 'Still using it' can still bring a finished bag back."
  2. "One tap finishes; no confirmation, no Undo."
  3. "On Today, a finished bag that was the only open one is no longer 'On the grinder', but its name still shows under 'Last coffee' (from its last shot); unchanged."
  4. "Correcting a shot that belongs to a finished bag still lists that bag in the Log shot bag picker; existing rule kept."
  5. "Interpreted 'the bag page' as /coffee/{bag_id} (coffee.html), since bag.html is the New bag screen."
  6. "Didn't identify which 2 tests were skipped."
- tasks `spec-review` and `quality-review`: unchanged (assigned).
- scribe's own task tokens: add a task `scribe` owner scribe, state done, evidence the orchestration commits, tokens 22838 for the first scribe run (note this run's tokens as null).
- in finish-bag.md Status: "2026-10-31 build: f191398 on finish-bag; make test 643 passed/2 skipped (builder-reported). Awaiting spec review."
Reply with the new orchestration HEAD SHA.
