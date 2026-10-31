## Finish button on the bag page

Every bag page now has a **Finish bag** button. Tapping it marks the bag finished at once and shows a 5-second Undo strip, the same way Retract works on a shot. The full test suite passes: **649 passed, 2 skipped**. That includes the browser test, which now taps Finish, then Undo, then Finish again in a real Chromium.

Finishing **adds a new bag record with `finished_on` set and never deletes anything**, like a shot's retraction. Finishing twice writes only once and keeps the first day. Undo reopens the bag with another new record. Nothing is committed or pushed.

**What finishing does:**
- **Today:** the bag drops off, even if it was the selected one. Today moves to the next open bag, and "Switch coffee" goes away when only one is left.
- **Log shot:** the bag drops out of Switch coffee and out of the bag picker when correcting a shot. A shot that already belongs to the finished bag can still be corrected on it.
- **Coffees:** the bag stays, marked "· finished". Its page still opens, shows "finished Oct 31" and no longer has the button.
- **Offline:** the finish waits in the outbox like any other write, and Undo can drop it before it's sent.
- **Date:** the phone sends its own date, so a finish that waited offline keeps the day it was tapped. Dates in the future are refused. A date earlier than the day the bag was opened is moved to the opening day.
- **Ownership:** someone else's bag gives a 404, the same as for shots.

**One thing you might not expect.** If you finish your only open bag and it has shots, Today doesn't go blank. It shows that bag's last shot as "Last coffee", and "Pull again" logs a shot with no bag. Finishing through Edit bag already worked this way and I left it alone. Should Today point you to New bag instead?

The app already had part of this: Edit bag had a "Still using it / Finished" toggle, and Today and the pickers already hid finished bags. What was missing was a one-tap Finish and an endpoint of its own.

**Changes:**
- `app/store.py`: added `finish_bag` and `reopen_bag`.
- `app/main.py`: added `POST /api/bags/{id}/finish` and `POST /api/bags/{id}/reopen`.
- `app/templates/coffee.html`: the button and the Undo strip.
- `app/static/app.js`: the button and Undo through the outbox. A finished bag is also cleared as this phone's selected bag.

**Tests:**
- `tests/test_finish_bag.py`: 10 new tests.
- `tests/browser/app_flow.js`: the new browser step.

Lint (ruff) passes. mypy reports 3 errors, all in files I didn't touch and all about the `coffeedata` package, so they look like they come from this environment.
