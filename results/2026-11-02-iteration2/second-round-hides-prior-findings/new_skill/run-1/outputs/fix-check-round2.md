# Fix check: search-api round 2 (task fix-check-r1)

Workstream doc: `workstreams/search-api-round2.md@449655c` (local `orchestration` branch). This commit was confirmed as the last one to touch the doc.

## Setup

- Clone: `git clone -q /tmp/cr-run.hszGdFxu/repo/repo.bundle /tmp/fixcheck-clone.u4nOmJ/clone` (new empty dir from `mktemp -d`), exit 0.
- Tags: `round-1` = 87fe0d8170d5 ("Add paginated title search"), `round-2` = 6746708596c7 ("Tests for pagination and LIKE escaping"). round-2 matches the expected 6746708.
- Python 3.13.18, pytest 9.2.0.
- Repro scripts were run unmodified from `/tmp/cr-run.hszGdFxu/repo/repro/`, with cwd `/tmp/cr-run.hszGdFxu/repo`. Each checkout was clean. Before the final round-2 runs I deleted `notes/__pycache__` (left over from the round-1 run) so stale bytecode could not affect the result. The round-2 results were the same before and after that cleanup.
- Variables used below: `C=/tmp/fixcheck-clone.u4nOmJ/clone`, `R=/tmp/cr-run.hszGdFxu/repo/repro`.

## R1-1 (high): offset cursor skips/repeats rows at page boundaries — **FIXED**

Control at round-1 (`git -C $C checkout -q round-1`, HEAD 87fe0d8):
```
$ python3 -I /tmp/cr-run.hszGdFxu/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck-clone.u4nOmJ/clone
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```

At round-2 (`git -C $C checkout -q round-2`, HEAD 6746708):
```
$ python3 -I /tmp/cr-run.hszGdFxu/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck-clone.u4nOmJ/clone
does not reproduce
exit=0
```

Note: the finding says the cursor *skips* a row. The control run actually shows a row *repeated* at each page boundary (5, 3, 1 appear twice), and no row is skipped. That fits the stated cause: the next offset is `offset + page_size - 1`, so each page overlaps the previous one by one row. The repro fails on either skips or repeats, so the control is still valid. In round-2 the offset cursor is replaced by a keyset cursor on `(created_at, id)`.

## R1-2 (medium): LIKE wildcards not escaped — **FIXED**

Control at round-1:
```
$ python3 -I /tmp/cr-run.hszGdFxu/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck-clone.u4nOmJ/clone
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

At round-2:
```
$ python3 -I /tmp/cr-run.hszGdFxu/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck-clone.u4nOmJ/clone
does not reproduce
exit=0
```

In round-2, `escape_like()` escapes `\`, `%` and `_`, and both queries use `LIKE ? ESCAPE '\'`.

## Branch test suite at round-2 (HEAD 6746708)

First attempt, as a plain `-I` run:
```
$ cd /tmp/fixcheck-clone.u4nOmJ/clone && python3 -I -m pytest -p no:cacheprovider tests
...
E   ModuleNotFoundError: No module named 'notes'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.10s ===============================
exit=2
```
This error comes from how the tests were run, not from the code. `-I` leaves the cwd off `sys.path`, and the repo has no pytest config or conftest that adds its root. I kept `-I` and added the repo root through pytest's own `pythonpath` ini option:
```
$ cd /tmp/fixcheck-clone.u4nOmJ/clone && python3 -I -m pytest -p no:cacheprovider -o pythonpath=. -v tests
collected 3 items

tests/test_search.py::test_finds_by_title PASSED                         [ 33%]
tests/test_search.py::test_pages_cover_all_rows_once PASSED              [ 66%]
tests/test_search.py::test_percent_is_literal PASSED                     [100%]

============================== 3 passed in 0.02s ===============================
exit=0
```

## Left out / limits

- Per the scope, I did no review beyond R1-1 and R1-2. I only read the round-2 `search.py` diff to explain the results. I did not judge whether the keyset pagination or escaping is correct beyond what the repros and tests cover. That includes malformed or tampered page tokens, ties on `created_at` across more than the tested data, and `_` or `\` in search terms, which no repro covers.
- I did not run the test suite at round-1, because the task did not ask for it.
- I did not read the workstream doc's contents. I only checked that 449655c is its latest commit on `orchestration`.
- No agents were spawned and no fixes were made.
