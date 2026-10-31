The bag page now has a **Finish bag** button. The full test suite passes: 645 passed, 3 skipped. Nothing is committed or pushed.

**One thing first:** the app could already finish a bag. Edit bag has a "Still using it / Finished" toggle, and Today, Switch coffee and Log shot already leave finished bags out. The README's "no screen to edit or finish a bag" line was out of date. What was missing was a one-tap Finish on the bag page, which is what I added.

**What it does**
- **Button:** on an open bag's page (`/coffee/{bag_id}`), under the roast line. It asks for a second tap ("Tap again to finish this bag"), like Retire on the gear screen. The page then reloads showing "Finished Oct 31" with the notice "Bag finished: <name>", and the button is gone.
- **The record:** `POST /api/bags/{id}/finish` writes the bag again with `finished_on` set, as a new record. Nothing is deleted. Finishing an already-finished bag writes nothing and keeps the first date, so a resend from the offline queue is harmless, the same as Retract (`app/store.py`, `finish_bag`).
- **The date:** the phone sends its own date, so a finish that waits offline keeps the day it was tapped. A date more than a day in the future is refused. A date before the bag was opened (a phone clock running behind) is moved up to the day it was opened.
- **Where the bag goes:** it leaves Today, Switch coffee and Log shot, even if this phone had it selected. It stays in Coffees marked "finished", with its shots. Correcting one of its shots still offers it.
- **Offline:** it waits in the queue like any other write. Once it goes through, the phone clears its saved copies of Today and Log shot, and drops the bag as its selection.
- **To undo:** Edit bag → "Still using it" opens it again. There's no 5-second Undo strip like Retract's; I used the second tap instead. Adding one means a reopen endpoint, so say if you want it.

**Tests:** 7 new ones in `tests/test_app.py`, under "finishing a bag":
- the finish adds a file and keeps the old one;
- finishing twice writes once;
- the result survives a restart;
- the bag leaves Today, the bag picker and Log shot even when it was selected, and stays in Coffees;
- finishing the only bag leaves Today on the last coffee;
- correcting one of its shots still offers it;
- reopening and finishing again works;
- refusals: another person's bag, an unknown bag, a future or garbled date, and a request not from the app's own page;
- the opened-date floor.

One timing test, `test_burst.py::test_hashing_runs_a_few_at_a_time`, failed once while two test runs shared the machine. It passed alone and in the full run.

**Not tested here:** the button's JavaScript (`app/static/app.js`). The browser tests skip because Playwright isn't installed in this sandbox, and I didn't add a browser step for Finish. `node --check` passes, but nothing has clicked the button yet.

I also updated the stale README line and added a "Finish bag" section to `docs/app/DESIGN.md`. CLAUDE.md's measurement process doesn't apply here: this is a feature, not a classifier or matching rule.
