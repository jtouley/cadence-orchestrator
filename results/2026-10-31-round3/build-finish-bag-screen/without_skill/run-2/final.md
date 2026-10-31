Every open bag's page now has a **Finish this bag** button. Tapping it marks the bag finished. Today, Switch coffee and the bag picker on Log shot drop it, and it stays in Coffees marked "· finished". The full test suite passes (652 passed, 2 skipped), including the browser test.

**Correction to "no way to finish":** the Edit bag form already had a "Still using it" / "Finished" switch, and the screens already hid finished bags. What was missing was a direct button. Nothing about which screens show a finished bag had to change.

**How it works**
- **No deletes:** tapping Finish writes a new record of the same bag with `finished_on` set, the same way Retract writes a new shot record with `deleted = true`. Every other field is kept. Finishing an already-finished bag writes nothing, so a resend or a second phone can't create a second record.
- **Undo:** like Retract, there's no confirmation. A "Bag finished" strip with Undo stays up for 5 seconds, then the page reloads showing "Finished Oct 31". Undo writes one more record with the date cleared.
- **Offline:** the tap waits on the phone like any other save. Undo before it syncs just removes it from the phone. Once a finish or undo syncs, the phone's saved copies of Today and Log shot are cleared so they don't show the old bag.
- **Finish date:** it's the phone's date at the tap, not the day it syncs. A future date is refused. A date before the bag was opened is moved up to the open date.

**Where the code is**
- `app/store.py`: `finish_bag` and `reopen_bag`
- `app/main.py`: `POST /api/bags/{id}/finish` and `/reopen`, which use the same write check and per-person check as retract
- `app/templates/coffee.html`: the button and Undo strip
- `app/static/app.js`: `finishBag` and the offline handling
- `docs/app/DESIGN.md`: a short "Finish this bag" entry

**Tests**
- `tests/test_finish_bag.py` (13 tests) checks:
  - the record is added and nothing is deleted;
  - finishing twice writes once;
  - the bag leaves Today, Switch and the Log shot picker, but a shot already in the bag can still be corrected against it;
  - it stays in Coffees and History;
  - Undo works;
  - it survives a restart;
  - other people get a 404, and a write without the app's headers gets a 403;
  - the date rules above.
- The Playwright flow (`tests/browser/app_flow.js`) now covers Finish then Undo, Finish offline then Undo, and finishing for good. It also runs the accessibility check and takes light and dark screenshots of the Undo strip.

I installed the browser test's npm dependencies locally to run it (`tests/browser/node_modules`, which git ignores). Nothing is committed. The changes are in the working tree on `main`. Each message I sent you is saved in `outputs/` (`01-status.md` through `06-final.md`); I didn't use any subagents.