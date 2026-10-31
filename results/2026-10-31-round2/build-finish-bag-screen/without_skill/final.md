Each bag's page now has a "Finish this bag" button. Most of the test suite passes, but two slow test files hit my time limit before finishing, and the button has never been clicked in a real browser. Nothing is committed or pushed.

**How it works**
- **Where:** the button sits at the bottom of the bag's page (`/coffee/<bag_id>`) and asks for a second tap to confirm. The page then reloads with "Bag finished: <name>", the bag's details show "finished <date>", and the button disappears.
- **What gets saved:** nothing is deleted. Finishing writes a new bag record with `finished_on` set to the phone's local date, under the same `bag_id`, just as Retract writes a new shot record. If the phone sends the finish twice, the second one writes nothing. It also works offline and syncs later.
- **Where the bag shows up:** Today, the "Switch coffee" list and the bag picker on Log shot (when correcting a shot) already skip finished bags, so it leaves all three. It stays in Coffees, marked "finished", with all its shots.
- **On the phone:** once the finish syncs, the phone stops treating it as the selected bag and refreshes its saved copies of Today and Log shot.
- **Taking it back:** there's no Undo strip. To reopen a bag, use Edit bag → "Still using it", which also writes a new record.

**What changed**
- `app/store.py`: a new `finish_bag()`.
- `app/main.py`: a new endpoint, `POST /api/bags/{bag_id}/finish`.
- `app/templates/coffee.html`: the button.
- `app/static/app.js`: the button's code and the clean-up on the phone after the finish syncs.
- `tests/test_app.py`: 4 new tests. They cover what gets written; the bag leaving Today and both pickers while staying in Coffees; the record being read back after a restart; a resent finish writing nothing; other people's bags, bad dates and future dates being refused; and reopening with "Still using it".

**Tests**
- `test_app.py` passes, 46 tests including the 4 new ones, and so does every other file except two. Lint is clean.
- `test_dbt.py` and `test_quality.py` had no failures, but hit the 100-second-per-file limit I set before they finished. They test the dbt models, which this change doesn't touch.
- The browser test was skipped because Playwright isn't installed here, so the button's JavaScript has only been syntax-checked.

The `.claude/skills/tpm/` files already showed as deleted in your checkout before I started; I left them alone.

My messages are saved in `outputs/` (`01-progress.md` to `04-final.md`). I didn't use any subagents, so there are no briefs.