# Fix check: search-api round-1 findings at round-2

Task: "fix-check" for workstreams/search-api-round2.md@ff7e1e168902469290c11a45de971fef5db2d5a0 (orchestration branch).
Date: 2026-11-02. No code changes were made.

## Summary

| Finding | Round-1 control | Round-2 | Verdict |
|---|---|---|---|
| R1-1 (high) offset cursor page-boundary bug | REPRODUCES, exit 1 | does not reproduce, exit 0 | **FIXED** |
| R1-2 (medium) unescaped LIKE wildcards | REPRODUCES, exit 1 | does not reproduce, exit 0 | **FIXED** |

Round-2 test suite: 3 passed, exit 0.

## Setup

Bundle heads (`git bundle list-heads /tmp/cr-run.0xfme1Ia/repo/repo.bundle`):
```
6746708596c7166d44d11e8e436bde8398be4a12 refs/heads/feature/search-api
6a70bbda5fa087f228bb33e126849caa3d28130d refs/heads/main
87fe0d8170d53f62679a525298d725eec4bffe1a refs/tags/round-1
6746708596c7166d44d11e8e436bde8398be4a12 refs/tags/round-2
6746708596c7166d44d11e8e436bde8398be4a12 HEAD
```

Clones, each in a fresh directory created with `mktemp -d /tmp/fixcheck.XXXX` (it was `/tmp/fixcheck.Zlzh`):
```
git clone -q /tmp/cr-run.0xfme1Ia/repo/repo.bundle /tmp/fixcheck.Zlzh/r2 && git -C /tmp/fixcheck.Zlzh/r2 checkout -q 6746708596c7166d44d11e8e436bde8398be4a12
git clone -q /tmp/cr-run.0xfme1Ia/repo/repo.bundle /tmp/fixcheck.Zlzh/r1 && git -C /tmp/fixcheck.Zlzh/r1 checkout -q 87fe0d8170d53f62679a525298d725eec4bffe1a
```
Checked with `git rev-parse HEAD` / `git describe --tags`: r1 = 87fe0d8170d53f62679a525298d725eec4bffe1a (round-1), r2 = 6746708596c7166d44d11e8e436bde8398be4a12 (round-2). Both had a clean `git status --short`.

Environment: Python 3.13.18, pytest 9.2.0. The repros ran as given, from cwd `/tmp/cr-run.0xfme1Ia/repo`.

Import check: that cwd also has its own `notes/` package. To make sure the repros loaded the clone's code and not that package, I ran a separate check (not a change to the repros) with the same `sys.path.insert(0, <clone>)` that the scripts use:
```
python -I -c "import sys; sys.path.insert(0, sys.argv[1]); import notes.search as s; print(s.__file__)" /tmp/fixcheck.Zlzh/r1   -> /tmp/fixcheck.Zlzh/r1/notes/search.py
python -I -c "import sys; sys.path.insert(0, sys.argv[1]); import notes.search as s; print(s.__file__)" /tmp/fixcheck.Zlzh/r2   -> /tmp/fixcheck.Zlzh/r2/notes/search.py
```

## R1-1 (high): offset cursor page-boundary bug. Verdict: FIXED

Round-1 control:
```
$ python repro/r1_1_cursor_gap.py /tmp/fixcheck.Zlzh/r1
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```
Round-2:
```
$ python repro/r1_1_cursor_gap.py /tmp/fixcheck.Zlzh/r2
does not reproduce
exit=0
```
Note: the finding says the cursor *skips* a row. In the round-1 output, rows are *repeated* at each boundary (5, 3, 1 each appear twice), and none are skipped. That fits a token that advances by page_size - 1, which overlaps pages rather than leaving gaps. The script fails on either a skip or a repeat, so the control run still shows that it detects the bug. Only the finding's wording is off.

At round-2, `notes/search.py` uses keyset pagination on `(created_at, id)` with `ORDER BY created_at DESC, id DESC`. The repro gives each note a distinct `created_at`, so it does not test the `id` tie-breaker for rows that share a timestamp.

## R1-2 (medium): unescaped LIKE wildcards. Verdict: FIXED

Round-1 control:
```
$ python repro/r1_2_like_wildcard.py /tmp/fixcheck.Zlzh/r1
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```
Round-2:
```
$ python repro/r1_2_like_wildcard.py /tmp/fixcheck.Zlzh/r2
does not reproduce
exit=0
```
At round-2, `escape_like()` escapes `\`, `%` and `_`, and both queries use `LIKE ? ESCAPE '\'`. The repro tests only `%`. It does not test `_` or a backslash.

## Round-2 test suite

```
$ cd /tmp/fixcheck.Zlzh/r2 && python -m pytest -v
============================= test session starts ==============================
platform linux -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0 -- /usr/local/bin/python
cachedir: .pytest_cache
rootdir: /tmp/fixcheck.Zlzh/r2
plugins: anyio-4.15.1
collecting ... collected 3 items

tests/test_search.py::test_finds_by_title PASSED                         [ 33%]
tests/test_search.py::test_pages_cover_all_rows_once PASSED              [ 66%]
tests/test_search.py::test_percent_is_literal PASSED                     [100%]

============================== 3 passed in 0.02s ===============================
exit=0
```
For context, the round-1 suite has one test, and it passes (`python -m pytest -q`: `1 passed in 0.01s`, exit 0).

## Left out

- Only R1-1 and R1-2 were judged. This is not a review of the full range 6a70bbd..6746708 or of anything else in the round-1 -> round-2 diff (`notes/search.py` +30/-7, `tests/test_search.py` +21).
- No extra cases were run beyond the repros as given: no rows with the same `created_at` (tie-breaker), no `_` or `\` in search terms, no case-sensitivity checks, and no handling of malformed or old offset-style page tokens.
- I did not check whether the round-2 tests fail at round-1.
- No code changes, commits or pushes. Running pytest left a `.pytest_cache` directory in the clone at `/tmp/fixcheck.Zlzh/r2`, which is outside the repo. Both clones are still at `/tmp/fixcheck.Zlzh/{r1,r2}`.
