# Fix check: search-api round 2

Workstream: `.cadence/workstreams/search-api-round2.md`, sha256 `626254b4c1f7f6b8eff29f65d3523e5186c2d578d7d89f91d5f0e23cda09188d` (prefix 626254b4c1 matches).

## Verdicts

| Finding | feature/search-api (6746708) | Control: round-1 (87fe0d8) | Verdict |
|---|---|---|---|
| R1-1 (high) cursor gap | "does not reproduce", exit 0 | REPRODUCES, exit 1 | **FIXED** |
| R1-2 (medium) LIKE wildcards | "does not reproduce", exit 0 | REPRODUCES, exit 1 | **FIXED** |

Test suite at feature/search-api: 3 passed, exit 0.

Note on R1-1 wording: the finding says the cursor "skips a row". At round-1 the next token is `offset + page_size - 1`, which makes pages **overlap**, so rows get **repeated** rather than skipped. The control output shows this: ids 5, 3 and 1 each come back twice, and none are missing. The repro checks for skipped or repeated rows, so it still catches the defect. At round-2 the offset cursor has been replaced by a keyset cursor on (created_at, id), so the cause of the bug no longer exists.

## Setup

Fresh directory: `/tmp/fixcheck.Hu4RBi`. The clone of feature/search-api is at `clone/`. A separate second clone checked out at tag round-1 is at `clone-r1/`, so the main clone was never moved off the branch. The repros were run with `python -I` from a neutral cwd (`/tmp/fixcheck.Hu4RBi/run`).

```
$ git bundle list-heads /tmp/cr-run.IUIMLbzs/repo/repo.bundle
6746708596c7166d44d11e8e436bde8398be4a12 refs/heads/feature/search-api
6a70bbda5fa087f228bb33e126849caa3d28130d refs/heads/main
87fe0d8170d53f62679a525298d725eec4bffe1a refs/tags/round-1
6746708596c7166d44d11e8e436bde8398be4a12 refs/tags/round-2
6746708596c7166d44d11e8e436bde8398be4a12 HEAD

$ git clone -q /tmp/cr-run.IUIMLbzs/repo/repo.bundle /tmp/fixcheck.Hu4RBi/clone
exit=0
$ git -C /tmp/fixcheck.Hu4RBi/clone checkout -q feature/search-api
exit=0
$ git -C /tmp/fixcheck.Hu4RBi/clone rev-parse HEAD
6746708596c7166d44d11e8e436bde8398be4a12
$ git -C /tmp/fixcheck.Hu4RBi/clone rev-parse 'round-2^{commit}' 'round-1^{commit}'
6746708596c7166d44d11e8e436bde8398be4a12
87fe0d8170d53f62679a525298d725eec4bffe1a
$ git -C /tmp/fixcheck.Hu4RBi/clone log --oneline --all --decorate
6746708 (HEAD -> feature/search-api, tag: round-2, origin/feature/search-api, origin/HEAD) Tests for pagination and LIKE escaping
6a9d4f0 Search: keyset pagination, escape LIKE input
87fe0d8 (tag: round-1) Add paginated title search
6a70bbd (origin/main) Notes store

$ git clone -q /tmp/cr-run.IUIMLbzs/repo/repo.bundle /tmp/fixcheck.Hu4RBi/clone-r1 && git -C /tmp/fixcheck.Hu4RBi/clone-r1 checkout -q round-1 && git -C /tmp/fixcheck.Hu4RBi/clone-r1 rev-parse HEAD
87fe0d8170d53f62679a525298d725eec4bffe1a
```

feature/search-api is at 6746708596c7166d44d11e8e436bde8398be4a12. Tag round-2 points to that same commit.

## R1-1 repro runs

```
$ python -I /tmp/cr-run.IUIMLbzs/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck.Hu4RBi/clone
does not reproduce
exit=0

$ python -I /tmp/cr-run.IUIMLbzs/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck.Hu4RBi/clone-r1
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```

## R1-2 repro runs

```
$ python -I /tmp/cr-run.IUIMLbzs/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck.Hu4RBi/clone
does not reproduce
exit=0

$ python -I /tmp/cr-run.IUIMLbzs/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck.Hu4RBi/clone-r1
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

## Test suite at feature/search-api

```
$ cd /tmp/fixcheck.Hu4RBi/clone && python -m pytest -p no:cacheprovider -v tests
============================= test session starts ==============================
platform linux -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0 -- /usr/local/bin/python
rootdir: /tmp/fixcheck.Hu4RBi/clone
plugins: anyio-4.15.1
collecting ... collected 3 items

tests/test_search.py::test_finds_by_title PASSED                         [ 33%]
tests/test_search.py::test_pages_cover_all_rows_once PASSED              [ 66%]
tests/test_search.py::test_percent_is_literal PASSED                     [100%]

============================== 3 passed in 0.02s ===============================
exit=0
```

Afterwards, `git status --porcelain --ignored` in the clone showed only untracked `notes/__pycache__/` and `tests/__pycache__/`. History and tracked files were not changed.

## Left out

- No review of the code beyond these two findings. That includes the new keyset and escaping code itself, edge cases such as rows with the same timestamp beyond what the repro and tests cover, and `_`/`\` escaping. The blind full-branch review is a separate task.
- No fixes, and no edits to the repros, tests, or clone history.
- The test suite was not run at round-1. Only the repros were used as controls.
