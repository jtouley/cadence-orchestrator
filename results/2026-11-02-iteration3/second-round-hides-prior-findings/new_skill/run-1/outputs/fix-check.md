# Fix check: search-api round 1 findings

- Clone: /tmp/cr-run.Fe3eErID/clone, branch feature/search-api, HEAD 6746708596c7166d44d11e8e436bde8398be4a12 (checked with `git rev-parse HEAD`)
- Workstream: workstreams/search-api.md@4dfac79 in /tmp/cr-run.Fe3eErID/orchestration (4dfac79 is the latest commit to touch that file)
- Environment: Python 3.13.18, pytest 9.2.0
- I made no code changes. I deleted the `__pycache__`/`.pytest_cache` files my runs created, so the clone's working tree is clean again.

## R1-1 (high): offset cursor skips a row on every page boundary (page_size - 1)

Command (cwd /tmp/cr-run.Fe3eErID/repo):

    $ python3 -I repro/r1_1_cursor_gap.py /tmp/cr-run.Fe3eErID/clone
    does not reproduce
    exit=0

Verdict: **FIXED.** The offset cursor is gone. `notes/search.py` now uses a keyset cursor: the token holds the last row's `(created_at, id)`, and the next page is fetched with `created_at < ? OR (created_at = ? AND id < ?)`, ordered by `created_at DESC, id DESC`. Paging 7 rows 3 at a time returns ids 1..7, each exactly once.

## R1-2 (medium): LIKE wildcards in the search term aren't escaped

Command (cwd /tmp/cr-run.Fe3eErID/repo):

    $ python3 -I repro/r1_2_like_wildcard.py /tmp/cr-run.Fe3eErID/clone
    does not reproduce
    exit=0

Verdict: **FIXED.** `escape_like()` escapes `\`, `%` and `_`, and both queries use `LIKE ? ESCAPE '\'`. Searching "100%" returns only "100% done".

## Test suite

First attempt, run in the same isolated mode as the repros:

    $ cd /tmp/cr-run.Fe3eErID/clone && python3 -I -m pytest -q
    ERROR collecting tests/test_search.py
    E   ModuleNotFoundError: No module named 'notes'
    1 error in 0.07s
    exit=2

This error comes from the command, not the code. `-I` stops Python from adding the current directory to the import path, so the tests couldn't import the `notes` package. The normal way to run the suite, from the clone root:

    $ cd /tmp/cr-run.Fe3eErID/clone && python3 -m pytest -q
    ...                                                                      [100%]
    3 passed in 0.01s
    exit=0

The tests are test_finds_by_title, test_pages_cover_all_rows_once and test_percent_is_literal.

## Not checked / caveats

- I judged each fix only against its finding, as asked. I did not review the rest of the code.
- Neither repro covers rows with equal `created_at` at a page boundary. `test_pages_cover_all_rows_once` does (5 rows with the same timestamp, 2 per page), and it passes.
- I didn't check what happens when a client sends an old offset-style or malformed page token. That is outside both findings.
- When the last page is exactly full, the search returns a next token and the following page comes back empty. This doesn't skip or repeat rows, so it is outside R1-1.
