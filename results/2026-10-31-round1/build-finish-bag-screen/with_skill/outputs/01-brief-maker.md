FIRST STEP, before anything else: save this entire brief, verbatim, to /tmp/tpm-eval/build-finish-bag-screen-with_skill/outputs/01-brief-maker.md (create the file).

## Task
The user asked (verbatim): "app has no way to finish a bag. add a Finish button on the bag page: marks it finished, drops it from Today and the bag picker on Log shot, still shows in Coffees. no deletes, write a record like retract does. tests pls"

Build that in the web app under app/. "The bag page" = the coffee page for one bag, GET /coffee/{bag_id} (template app/templates/coffee.html), which today shows an "Edit bag" link.

## Observed facts (verify yourself, don't take on trust)
- Bags have `finished_on: date | None` (src/coffeedata/models.py:201). Bag saves are append-only: a new record under the same bag_id, latest wins (app/store.py `save_bag` ~line 446; POST /api/bags in app/main.py ~line 1015).
- The Edit bag form (app/templates/bag_edit.html) already has a "Still using it" / "Finished" toggle. So finishing is possible today, just not one tap. README.md:449 says "It has no screen to edit or finish a bag", which looks stale.
- Today and the Log shot picker already appear to filter `finished_on` (app/store.py:158, 236; app/main.py:473, 494, 502, 609). Coffees list shows "· finished" (app/templates/coffees.html:14).
- Shot retract is the pattern the user pointed to: a new record, never a delete (app/store.py `retract_shot` ~line 399, POST /api/shots/{id}/retract). Writes from the browser go through an offline outbox (app/static/app.js).
- Design spec: docs/app/DESIGN.md (sections "Edit bag", "Notice", "Undo strip"). Follow its conventions for button style, notices and copy.

## What to build
1. A Finish button on the coffee page, shown only when the bag isn't finished. Tapping it writes a new bag record with finished_on = today (the user's local date, consistent with how the app computes "today" elsewhere), reusing the existing bag save path / outbox rather than inventing a parallel write mechanism, unless you find a concrete reason that can't work — then say why. No deletes anywhere. Finishing an already-finished bag must not write a second record (mirror retract's "writes once").
2. After finishing: the bag is gone from Today and from the Log shot bag picker, still listed in Coffees (marked finished), and its coffee page still opens and shows "finished <date>". A notice per DESIGN.md is fine.
3. Tests (pytest, in tests/, following tests/test_app.py style): finish writes exactly one new record and deletes nothing; finishing twice writes once; finished bag absent from Today and the Log shot picker; still present in Coffees and its page; Finish button present for open bag and absent for finished bag; other users can't finish your bag (match how existing endpoints authorize). Add a browser-flow step in tests/browser/app_flow.js only if that harness runs in this environment; otherwise say so.
4. Fix the stale README.md:449 sentence so it's true after your change.

## Constraints
- Stay in app/, tests/, README.md (and docs/app/DESIGN.md only if you add a new UI element worth one line there). Don't touch src/coffeedata, dbt, eval, .claude.
- Don't commit, push, or open PRs. Leave changes uncommitted in the working tree of /tmp/tpm-eval/build-finish-bag-screen-with_skill (detached HEAD at 9b850e8; that's fine).
- No new dependencies.

## Output (hand back)
- Files changed (git diff --stat raw output).
- The exact test commands you ran and their raw tail output (full suite for tests/test_app.py and any file you touched, plus the whole `tests/` suite if it runs in reasonable time; report any pre-existing failures separately with evidence they fail on clean HEAD too).
- file:line for: the button, the write path, the idempotency check.
- Anything you couldn't do or decided differently from this brief, and why.

## Stop condition
Stop when the change and tests are in the working tree and you've reported. Don't commit.
