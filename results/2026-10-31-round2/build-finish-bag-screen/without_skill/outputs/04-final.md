Done: the bag page now has a Finish button. Nothing is committed or pushed.

**What it does**
- The button is at the bottom of each bag's page (`/coffee/<bag_id>`). It reads "Finish this bag" and needs a second tap to confirm, like the existing "Sign out everywhere" button. Once tapped, the page reloads with "Bag finished: <name>", shows "finished <date>" in the bag's details line, and the button is gone.
- Finishing never deletes anything. It writes a new bag record with `finished_on` set to the phone's local date, under the same `bag_id`, the same way Retract writes a new shot record. A second Finish, such as the phone resending it, writes nothing. The finish goes through the same offline queue as other saves, so it works offline and syncs later.
- Today, the "Switch coffee" bag list and the bag picker when correcting a shot on Log shot already skip finished bags, so a finished bag drops out of all three. It stays in Coffees, marked "finished", with all its shots. Correcting a shot from a finished bag still shows that bag as the shot's own.
- Once the finish reaches the server, the phone forgets the bag if it was the one selected, and clears its saved copies of Today and Log shot so they don't keep showing it.
- There's no Undo strip. To reopen a bag, use Edit bag → "Still using it", which also writes a new record. There's a test for that.

**Changes**
- `app/store.py`: `finish_bag()`. It refuses another person's bag or a missing one (404) and a date more than a day ahead (422).
- `app/main.py`: `POST /api/bags/{bag_id}/finish`, which takes `{"finished_on": "YYYY-MM-DD"}`. With no date it uses today in the phone's time zone.
- `app/templates/coffee.html`: the button.
- `app/static/app.js`: the button's handler, plus clearing the bag on this phone once the finish syncs.
- `tests/test_app.py`: 4 new tests, covering what gets written, Today, both bag lists, Coffees and the bag page, survival across a restart, resends, other people's bags, bad and future dates, the same-origin check, and reopening the bag.

**Test results**
- Every file except two passes, including `test_app.py` (46 passed, 4 of them new). Lint is clean.
- `test_dbt.py` and `test_quality.py` passed everything they reached but hit the 100 s per-file limit I set before finishing. They exercise the dbt models, which this change doesn't touch.
- The browser test (`test_app_browser.py`) was skipped because Playwright isn't installed here. That means the button's script has only been syntax-checked, never clicked in a browser.

**Already in your checkout:** the `.claude/skills/tpm/` files show as deleted in the working tree. That was already the case when I started. I left them alone.
