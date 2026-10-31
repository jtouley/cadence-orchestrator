# Code review (medium): finish-bag, main@6bda240..5eb5cb9

- Worktree: /tmp/co-r3/clones/build-finish-bag-screen-with_skill-2-finish-bag (HEAD = 5eb5cb9, clean)
- Context: workstreams/finish-bag.md@52599f1 (orch2 worktree). The Ask: a Finish button on the bag page that writes a
  new record (no deletes), drops the bag from Today and the Log shot picker, keeps it in Coffees, with tests.
- Changed files reviewed: app/main.py, app/store.py, app/static/app.js, app/templates/coffee.html,
  docs/app/DESIGN.md, tests/test_finish_bag.py
- Read-only. No fixes, no push, no PR, no subagents. The /code-review skill ran as a forked execution of this same
  session, not a separate reviewer agent. Repro tests are in /tmp/co-r3/review-scratch/test_review_repro.py,
  outside the worktree.

## Verdict

**No blockers.** The change does what the Ask says. It appends one record with `finished_on`, writes no deletes and
leaves existing files untouched. A second finish writes nothing. The button goes away once the bag is finished. The
new tests (7) pass. The findings below are should-fix items and nits.

### Test suite

```
$ cd <worktree> && .venv/bin/python -m pytest -q -p no:cacheprovider
FAILED tests/test_verdict.py::test_the_build_takes_claudes_verdict_over_the_rules
1 failed, 564 passed, 83 skipped, 1 warning in 112.96s
$ .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_verdict.py::test_the_build_takes_claudes_verdict_over_the_rules | grep '^E '
E   FileNotFoundError: [Errno 2] No such file or directory: 'dbt'
$ .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_finish_bag.py
7 passed in 2.21s
```
The one failure is the environment: `dbt` isn't on PATH, and the test imports none of the changed files. I didn't
run it on `main`, because that would mean creating a worktree, and this review is read-only.

How the repros below were run:
```
cd /tmp/co-r3/clones/build-finish-bag-screen-with_skill-2-finish-bag
PYTHONPATH=. .venv/bin/python -m pytest /tmp/co-r3/review-scratch/test_review_repro.py -s -q \
  -p no:cacheprovider -p tests.conftest --rootdir=.
```

---

## Should-fix (minor)

### 1. A finish date before the roast date is accepted, and the page then shows a negative day count. app/store.py:481
`finish_bag` only rejects dates in the future. A phone whose clock reads the past, or any API client, can store a
`finished_on` before `roast_date` or `opened_on`.
```
BEFORE_ROAST: 200 {'bag_id': 'bag1', 'written': True}        # POST {"finished_on": "2025-10-30"}, roast 2026-10-18
PAGE: ['Roasted Oct 18 · day -353 · finished Oct 30']
```
CONFIRMED. The existing Edit bag path doesn't check `finished_on` at all, so this isn't a regression in kind. But the
new code already has a date check, and adding a lower bound there is cheap.

### 2. With no `finished_on` in the body, the server's local date is used, not the user's zone. app/main.py:1030
`date.today()` is the process's local date. The rest of main.py uses `tz(request)` for the viewer's day. The phone
always sends a date, so only API clients are affected.
```
# server TZ=Pacific/Kiritimati, cookie tz=America/Los_Angeles, POST {} on 2026-10-31
NO_DATE: 200 {'bag_id': 'bag1', 'written': True} server date.today()= 2026-11-01
PAGE: ['Roasted Oct 18 · day 14 · finished Nov 1']
```
CONFIRMED. The fix: use `datetime.now(tz(request)).date()`, or require the field.

### 3. Offline, the finished bag stays on the phone's kept Today and Log shot until the write syncs. app/static/app.js:1150 and :107
`clearBagPages()` and clearing `selected-bag` run only inside `deliverOnce` after `r.ok`. Offline, `go(here, ...)`
reloads `/coffee/{id}`, which is in the service worker's KEEP list (app/sw.js:15). That serves the cached copy,
which still has the Finish button and no "finished" date, while the notice says "Bag finished on this phone". The kept
`/` and `/log` still show the bag as current, so shots logged offline get that `bag_id`.
UNPROVEN. This needs a browser with the service worker and a simulated offline state, which I didn't run. The path
is clear from reading the code: app.js:99-115 runs only on `r.ok`, and sw.js:66-68 is the cache fallback. Edit bag's
"Finished" has the same behavior already. DESIGN.md says "Offline it waits in the outbox like any other write", so this
is consistent with the documentation. It is still a gap against "drops it from Today and the bag picker" while offline.

### 4. Read-then-write race with concurrent bag writes. app/store.py:476-483
`prev` is read outside `self.lock`, and `_commit` writes `prev.item.model_copy(...)`. If a concurrent `save_bag` on the
same bag (for example `apply_read` after a photo upload) read the bag before the finish committed, it can write a
later record with `finished_on=None`, and the bag silently reopens. In the other order, the finish copy loses the
photo's `coffee_id`/`match_score`.
UNPROVEN. It's timing-dependent and I wrote no deterministic repro. `save_bag` has the same read-outside-lock
pattern, so this is an existing design limit that the new code inherits, not something it introduced.

## Nits

### 5. A non-string `finished_on` is accepted. app/main.py:1030
`str(body["finished_on"])` makes a JSON number parse as a basic-format ISO date on Python 3.11+.
```
NUMERIC: 200 {'bag_id': 'bag1', 'written': True}             # POST {"finished_on": 20261030}
```
CONFIRMED. A typed Pydantic body model (`finished_on: date | None`) would reject this and match the other endpoints.
A non-dict body is already rejected by FastAPI (`LIST_BODY: 422 {"detail":["Input should be a valid dictionary"]}`),
so that part isn't an issue.

### 6. Duplicated "bag finished" cleanup in `deliverOnce`. app/static/app.js:99-114
The new `finish:` branch sits next to the existing `/api/bags && finished_on` branch and behaves differently. The new
one always clears the kept pages; the existing one clears them only when the finished bag was the selected one. Both
entry bodies carry `bag_id` and `finished_on`, so a single condition would cover both writes.
Proven by reading the diff (shown above in the review session). No runtime repro is needed.

### 7. Duplicated local-date formatter. app/static/app.js:1145
The `YYYY-MM-DD` string built from `getFullYear/getMonth/getDate` copies the Edit bag handler (around :698).
Extract a `localToday()` helper. Proven by reading the code: `grep -n 'padStart(2, "0")' app/static/app.js`.

### 8. Duplicated future-date grace rule. app/store.py:481
`datetime.now(UTC).date() + timedelta(days=1)` is copied from `save_bag` (:454), and a comment says it mirrors the
phone's check. Changing one copy and not the other would make the two writes disagree. Proven by reading the code:
`grep -n 'timedelta(days=1)' app/store.py`.

### 9. The test fetches the page twice. tests/test_finish_bag.py:37-38
`page = client.get(...).text` is followed by `assert client.get(...).status_code == 200`, so the status checked isn't
the status of the response whose body is checked. Use `r = client.get(...)` once. Proven by reading the code.

## Scope check against the workstream
- No deletes, and no edits of existing files: covered by `test_finishing_appends_one_record_and_deletes_nothing`.
- Leaves Today and the Log shot picker, stays in Coffees: covered by tests in tests/test_finish_bag.py, all passing.
- No un-finish control and no dbt/model changes. DESIGN.md gains a "Finish bag" section that matches the behavior.
  Nothing is out of scope.
