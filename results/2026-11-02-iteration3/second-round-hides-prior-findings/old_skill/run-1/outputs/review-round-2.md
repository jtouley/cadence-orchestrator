# Code review: round-2 (main..6746708)

## Setup

- Fresh clone: `git clone /tmp/cr-run.NbzCWSvP/repo/repo.bundle` into the new empty directory `/tmp/cr-clone.yQVmBF/r`
- Range: the clone has no local `main`, so `main` resolves to `origin/main` = `6a70bbd` ("Notes store"). Tag `round-2` = `6746708596c7166d44d11e8e436bde8398be4a12`.
- Commits reviewed: `87fe0d8` Add paginated title search, `6a9d4f0` Search: keyset pagination, escape LIKE input, `6746708` Tests for pagination and LIKE escaping.
- Files changed: `notes/search.py` (+40), `tests/test_search.py` (+31).
- Method: ran the `/code-review` skill at `high`, then reproduced each finding by hand. The code was not changed. The only side effect, `__pycache__` directories, was deleted, and `git status` is clean.
- Environment: Python 3.13.18, SQLite 3.53.1.
- Repro script: `/tmp/cr-scripts.xYyLrL/repro.py`, kept outside the clone and run as `python3 -I /tmp/cr-scripts.xYyLrL/repro.py /tmp/cr-clone.yQVmBF/r <case>`. In the commands below, `R=/tmp/cr-clone.yQVmBF/r` and `S=/tmp/cr-scripts.xYyLrL`.

Existing tests pass:
```
$ cd /tmp && python3 -I -c "import sys; sys.path.insert(0,'/tmp/cr-clone.yQVmBF/r'); import pytest; sys.exit(pytest.main(['-q','-p','no:cacheprovider','/tmp/cr-clone.yQVmBF/r/tests']))"
...                                                                      [100%]
3 passed in 5.65s
```

## Findings

### 1. HIGH: `page_size=0` crashes with IndexError, and page_size is never validated
`notes/search.py:37-38`. `LIMIT 0` returns `[]`. Then `len(rows) == page_size` is `0 == 0`, so `rows[-1]` raises. A negative page_size means `LIMIT -1`, which SQLite treats as no limit. Nothing sets an upper bound either.

Repro: `python3 -I $S/repro.py $R pagesize0`. The case runs `search(db,"a",page_size=0)`, then `search(db,"",page_size=-1)`.
```
IndexError: list index out of range
([{'id': 1, 'title': 'a', 'created_at': '2026-10-01'}], None)
```
Line 2 shows that `page_size=-1` returns every row and no token.

### 2. HIGH: A malformed or edited page token raises unhandled exceptions
`notes/search.py:9-10` (`_decode`) and `notes/search.py:21,27`. The token comes from the client. It is not validated or signed. Bad base64, bad JSON, and JSON with the wrong shape each raise a different raw exception, which becomes a 500 rather than a clean "invalid token" error. A client can also forge any cursor value.

Repro: `python3 -I $S/repro.py $R badtoken`
```
!!! -> JSONDecodeError: Expecting value: line 1 column 1 (char 0)
eyJ -> Error: Incorrect padding
W10= -> TypeError: list indices must be integers or slices, not str
e30= -> KeyError: 'created_at'
bm90anNvbg== -> JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```
(`Error` is `binascii.Error`. `W10=` is `[]` and `e30=` is `{}`.)

### 3. MEDIUM: An exactly full last page still returns a token, and that token leads to an empty page
`notes/search.py:37`. When the number of matches is a multiple of page_size, the client gets a next token for a page with no rows. The usual fix is to fetch `LIMIT page_size + 1` and emit a token only if the extra row comes back.

Repro: `python3 -I $S/repro.py $R emptypage` (4 notes, page_size=2)
```
page 1 [4, 3] token
page 2 [2, 1] token
page 3 [] None
```

### 4. MEDIUM: Ordering and the cursor depend on comparing `created_at` as TEXT, so mixed timestamp formats sort wrong
`notes/search.py:25-26`, with `notes/store.py` (`created_at TEXT`, and `add_note` accepts any string). "Newest first" and the `created_at < ?` cursor are only correct if every timestamp has the same fixed width and format.

Repro: `python3 -I $S/repro.py $R tsformat`
```
['x new@2026-10-10T00:00:00Z', 'x mid@2026-10-1', 'x old@2026-10-09']
```
`2026-10-1` (Oct 1) sorts ahead of `2026-10-09`. The same comparison drives the cursor predicate, so rows could be skipped or repeated across pages. The ordering error is proven. Skips or repeats across pages are inferred and UNPROVEN.

Note: this is a design risk. It only applies if callers write timestamps in more than one format. The current tests use a single date format.

### 5. LOW: An empty search term matches every note, and `None` crashes
`notes/search.py:14,19`.

Repro: `python3 -I $S/repro.py $R emptyterm`. The case runs `search(db,"")`, then `search(db,None)`.
```
([{'id': 2, 'title': 'b', 'created_at': '2026-10-02'}, {'id': 1, 'title': 'a', 'created_at': '2026-10-01'}], None)
AttributeError: 'NoneType' object has no attribute 'replace'
```
Whether an empty term should mean "list all" is a product decision. The `None` crash is a real bug only if callers can pass `None`.

### 6. LOW: Case-insensitive matching works only for ASCII
`notes/search.py:24`. SQLite's built-in `LIKE` folds case for ASCII letters only.

Repro: `python3 -I $S/repro.py $R unicode`. The case searches `"groc"` against "Groceries", then `"über"` against "Über Notes".
```
['Groceries']
[]
```

### 7. LOW (cleanup): The two query branches are duplicates, and no index supports the keyset query
`notes/search.py:20-35`. The two SQL strings are the same except for the cursor predicate. The predicate could be built conditionally as `(created_at, id) < (?, ?)`. The schema has no index on `(created_at, id)`, so every page scans the whole table and sorts it in a temporary B-tree, which defeats the point of keyset pagination.

Repro: `python3 -I $S/repro.py $R plan`, which runs EXPLAIN QUERY PLAN on the cursor query.
```
[(4, 0, 216, 'SCAN notes'), (25, 0, 0, 'USE TEMP B-TREE FOR ORDER BY')]
```
The full scan and sort are proven. The claim that the row-value form would use an index once one exists is UNPROVEN, because it was not tested.

### 8. LOW (tests): Escaping and pagination edge cases have no tests
`tests/test_search.py:26-31`. The tests cover only `%`. There are no tests for `_`, backslash, page_size=0, an exactly full last page, or bad tokens. The escaping itself is correct today. This finding is about coverage, not a bug.

Repro (escaping works now): `python3 -I $S/repro.py $R escape`, with notes `a_b`, `axb`, `a\b`, `a\\b`.
```
'a_b' -> ['a_b']
'a\\b' -> ['a\\b']
```
The claim that a regression would pass CI is UNPROVEN. It follows from reading the test file and was not demonstrated with a mutation.

## Merge-ready: NO

Findings 1 and 2 are reachable crashes from client-controlled input (`page_size` and `page_token`), assuming these values come from API clients, as the branch name `feature/search-api` suggests. Finding 3 is a visible pagination bug. Fix 1-3 and add tests for them before merging. Findings 4-8 can be follow-ups.

## Not checked
- How `search` is exposed, since this range contains no API or HTTP layer. I assumed `page_size`, `page_token`, and `term` come from clients.
- Concurrency: inserts or deletes between page fetches, and SQLite thread-safety of the shared connection.
- Performance at realistic data sizes. Only the query plan was inspected, with no benchmarks.
- Python and SQLite versions other than 3.13.18 and 3.53.1. Behaviour of `LIMIT -1` and Unicode `LIKE` depends on the SQLite build, for example ICU.
- Security beyond token forgery and parsing. SQL injection looks safe because every value is bound as a parameter, but no dedicated security review was done.
- Commits outside `main..6746708`, including `def5e03` "eval setup".
