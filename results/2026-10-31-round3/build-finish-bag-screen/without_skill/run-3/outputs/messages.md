# Messages to the user

## 1 (progress)

Still reading the code. The app already has a `finished_on` field on bags, and Edit bag has a "Finished" toggle.
Today, Switch bag and Log shot already leave out finished bags. What's missing is a direct Finish button on the bag
page. Next I'm reading the bag page and the bag-save path, then I'll add the button, the endpoint and the tests.

## 2 (progress)

I've read the code. Edit bag already has a Finished toggle, so the app can finish a bag, but only through that
form. I found one real gap: after you finish the last open bag, Today and Log shot still fall back to that bag's
coffee through its last shot. My plan:
- add `POST /api/bags/{id}/finish`, which writes a new bag record with `finished_on` set (finishing twice writes
  once);
- add a Finish button on the coffee page that needs a second tap to confirm;
- stop falling back to a finished bag's coffee on Today and Log shot.

Then the tests.

## 3 (progress)

The code is written: the endpoint, the Store method, the button and its JS, the Today and Log shot fallback fix,
and the docs. Next I'm writing tests and running the suite.

## 4 (progress)

The 8 new tests pass. One of them fails without the Today/Log shot fix, so it does catch that case. Lint is clean.
The full suite is still running and takes a while; I'm waiting for it to finish.

## 5 (progress)

The full suite ran past the 10-minute limit and was stopped before printing a result, so I don't know yet whether
it passed. I'm rerunning the app tests on their own, which is where this change lives, and then the rest of the
suite.

## 6 (progress)

The app tests pass: 230 passed and 1 skipped (the browser test, because Playwright isn't installed here). That
includes the 8 new ones. The rest of the suite (the dbt builds and the non-app tests) is running in the background,
and I'll report when it's done.

## 7 (final)

The Finish button is on the bag page (`/coffee/<bag>`). The first tap changes it to "Tap again to finish it", and
the second tap saves. Then the page reloads with "Bag finished: <name>" and the button is gone. I haven't checked it
in a real browser.

**About "no way to finish a bag":** the app already had one. Edit bag has a "Still using it" / "Finished" toggle,
and Today, Switch coffee and Log shot already left finished bags out. So the new part is the one-step button. While
testing it I found and fixed a real gap: finishing your last open bag didn't take it off Today. Today kept showing
it as "Last coffee", and Pull again would have logged the next shot to that coffee with no bag. Now Today says
"Nothing on the grinder" and Log shot sends you to New bag. Shots from before bags were recorded (with no bag) still
show the old way.

**How it works:**
- The button calls `POST /api/bags/{id}/finish` (in `app/main.py`), which hands off to `Store.finish_bag` (in
  `app/store.py`).
- That writes a new bag record: the stored bag with `finished_on` set. Nothing is deleted or rewritten, the same way
  retract works.
- Finishing a bag that's already finished writes nothing and keeps the first date, so a resend from the phone's
  outbox is harmless.
- The date is the phone's, so a bag finished offline keeps the day you tapped it. A future date, or someone else's
  bag, is refused.
- It goes through the outbox, so it works offline. If that phone had the bag selected, it forgets it, and the
  saved Today and Log shot pages are cleared.
- To undo it, choose "Still using it" on Edit bag.
- Coffees still lists the bag, marked "finished", and its page and shots stay.

**Tests:** `tests/test_finish_bag.py` has 8 tests:
- it writes a new record and leaves every earlier file in place;
- finishing twice writes once;
- the bag leaves Today, Switch coffee and Log shot, and stays in Coffees and History;
- finishing the last open bag leaves nothing on the grinder, and that bag's shots can still be corrected;
- it rejects someone else's bag, a future date and a bad date;
- reopening the bag through Edit bag works.

The "last open bag" test fails without the fix, so it catches that case.

**Results:**
- The full suite passes: 646 passed and 3 skipped, run in two parts (230 + 1 skipped, then 416 + 2 skipped).
- The browser flow test (`tests/test_app_browser.py`) was one of the skips, because Playwright isn't installed here.
  So the button's JavaScript hasn't run in a browser and has no automated test; in CI it runs only if you add a
  step to `tests/browser/app_flow.js`.
- `ruff check` and `ruff format` are clean.
- README and `docs/app/DESIGN.md` describe the button.

**One gap I didn't fix:** if an Edit bag form is already open when you finish the bag, saving that form afterwards
sets the bag back to "Still using it". Edit bag has always saved this way.

Nothing is committed. The changes are in the working tree on `main`, and this log is in `outputs/messages.md`.
