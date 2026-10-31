The bag page (`/coffee/<bag>`) now has a Finish button, and the full test suite passes. I haven't seen the button work in a real browser.

**The app could already finish a bag:** Edit bag has a "Still using it" / "Finished" toggle, and finished bags were already left out of Today, Switch coffee and Log shot. What's new is the one-step button.

**A bug I fixed along the way:** finishing your last open bag didn't take it off Today. Today showed it as "Last coffee", and Pull again would have logged the next shot to that coffee with no bag. Now Today says "Nothing on the grinder" and Log shot sends you to New bag. Shots from before bags were recorded still show the old way.

**How it works:**
- **Button:** the first tap changes it to "Tap again to finish it" and the second saves. The page then reloads with "Bag finished: <name>" and the button is gone.
- **Record:** a new endpoint, `POST /api/bags/{id}/finish`, writes a new bag record with `finished_on` set. Nothing is deleted or rewritten, the same way retract works.
- **Finishing twice:** a bag that's already finished gets no new record and keeps its first date, so a resend from the phone is harmless.
- **Date:** the phone sends its own date, so a bag finished offline keeps the day you tapped it. A future date, a bad date, or someone else's bag is refused.
- **Offline:** it waits in the phone's outbox like any other save. If that phone had the bag selected, it forgets it.
- **Coffees:** the bag is still listed there, marked "finished", and its page and shots stay.
- **Undo:** choose "Still using it" on Edit bag.

**Tests:** `tests/test_finish_bag.py` has 8 tests covering:
- the record: a new file is written and every earlier file stays;
- finishing twice writes only once;
- where the bag shows: gone from Today, Switch coffee and Log shot, still in Coffees and History;
- finishing the last open bag: nothing on the grinder, and its shots can still be corrected;
- refusals: someone else's bag, a future date, a bad date;
- reopening through Edit bag.

The "last open bag" test fails without the fix, so it does catch that bug.

**Results:**
- All tests pass: 646 passed, 3 skipped (run in two batches because a single run hit the 10-minute limit). Lint is clean.
- One skip is the browser test, because Playwright isn't installed here. So the button's JavaScript has never run and no test covers it. Even in CI it won't be tested until a step for it is added to `tests/browser/app_flow.js`.
- The README and `docs/app/DESIGN.md` now describe the button.

**Not fixed:** if an Edit bag form is already open when you finish the bag, saving that form afterwards sets the bag back to "Still using it". Edit bag has always worked that way.

Nothing is committed; the changes are uncommitted on `main`. Every message I sent you is also in `outputs/messages.md` in the repo; I didn't start any subagents.