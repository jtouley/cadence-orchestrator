# Code review (high): main..feature/search-api

- Repo: /tmp/cr-run.Fe3eErID/clone
- Range: 6a70bbda5fa087f228bb33e126849caa3d28130d..6746708596c7166d44d11e8e436bde8398be4a12 (main..feature/search-api; both refs checked and match the pins)
- Workstream: /tmp/cr-run.Fe3eErID/orchestration workstreams/search-api.md@4dfac79. Standard: "correctness of the code in the range, judged by its own tests and behaviour."
- Files changed: notes/search.py (+40), tests/test_search.py (+31). Commits: 87fe0d8, 6a9d4f0, 6746708.
- No code changes were made. Repro script: /tmp/cr-run.Fe3eErID/scratch/r.py (outside the clone). Stray `__pycache__` was deleted afterward, and the clone's `git status` is clean.

## Process note

I first ran the `/code-review` skill. It ran as a forked execution, which may count as a subagent, and it reviewed the wrong checkout: the cwd /tmp/cr-run.Fe3eErID/repo, including commit ba96310 "eval setup" and `repo.bundle`, instead of the pinned clone. I threw out all of its output. The review below was done by hand on the pinned range in the clone, and I re-ran every repro myself.

## Baseline

```
$ cd /tmp/cr-run.Fe3eErID/clone && python -m pytest -q -p no:cacheprovider
...                                                                      [100%]
3 passed in 0.02s
```

The fixes claimed for keyset pagination and LIKE escaping hold up. Pagination covers every row exactly once, including across different `created_at` values. `%`, `_` and `\` all match literally:

```
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py cursor
[('2026-10-03', 5), ('2026-10-03', 1), ('2026-10-02', 3), ('2026-10-01', 4), ('2026-10-01', 2)]
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py escape
'a_b' ['a_b']
'a\\b' ['a\\b']
'a%b' ['a%b']
```

## Findings

### 1. `page_size=0` crashes with IndexError (notes/search.py:37-38), severity: medium
`LIMIT 0` returns `[]`, so `len(rows) == page_size` is `0 == 0`, which is True, and `rows[-1]` raises. There is no check on `page_size`.
```
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py zero
  File "/tmp/cr-run.Fe3eErID/clone/notes/search.py", line 38, in search
    last = rows[-1]
           ~~~~^^^^
IndexError: list index out of range
```

### 2. A negative `page_size` turns off pagination (notes/search.py:27/34), severity: medium
SQLite treats a negative LIMIT as "no limit". `page_size=-1` returns every match and no token, so a caller can get an unbounded result set.
```
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py neg
5 None
```
(5 = all rows; the token is None.)

### 3. A malformed or tampered `page_token` raises a raw exception (notes/search.py:9-10, 21, 27), severity: medium
`_decode` does no validation. An invalid token raises `binascii.Error`, `JSONDecodeError`, `KeyError` or `TypeError` instead of a clear "invalid token" error. Tokens are unsigned and not tied to `term`, so a client can make up a cursor or reuse a token across queries.
```
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py badtok
Error Incorrect padding
KeyError 'created_at'
```
(`Error` is `binascii.Error` for token `"abc"`. `KeyError` is for base64 `{"x":1}`.)

### 4. An exactly full last page still returns a next token (notes/search.py:37), severity: low
When the number of matches is a multiple of `page_size`, the last full page returns a token, and the next request comes back `([], None)`. That is an extra round trip and a "next" link that leads to an empty page. Fetching `page_size + 1` rows would fix it.
```
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py full
request 1 [4, 3] token
request 2 [2, 1] token
request 3 [] None
```

### 5. "Newest first" depends on `created_at` text format (notes/search.py:25-26, 33), severity: low, outside the diff's direct control
The ordering and cursor compare `created_at` as TEXT, and `add_note` accepts any string. With mixed ISO formats, the order comes out wrong (`'T'` sorts after `' '`):
```
$ python -I /tmp/cr-run.Fe3eErID/scratch/r.py fmt
['early', 'late']
```
(`early` = `2026-10-01T09:00` sorts ahead of `late` = `2026-10-01 10:00`, which is not newest first.) This only matters if callers mix formats. The existing tests use `YYYY-MM-DD` only.

### 6. Test gaps (tests/test_search.py), severity: low
The tests don't cover `page_size <= 0`, invalid tokens, an exactly full last page, `_` or `\` escaping, or a cursor across different `created_at` values. Because `test_pages_cover_all_rows_once` uses a single date, the `created_at < ?` branch is never tested on its own. The repros for findings 1-4 above all pass CI unnoticed:
```
$ python -m pytest -q -p no:cacheprovider
3 passed in 0.02s
```

### Minor (no behavioural impact)
The two SQL branches in `search` duplicate SELECT/WHERE/ORDER BY and differ only in the cursor predicate. If they drift apart, page 1 and later pages could sort differently.

## Verdict

The core pagination and escaping behaviour is correct, and the branch's own tests pass. Findings 1-3 are input-validation bugs that will surface as 500s or unbounded queries once `search` is exposed to request parameters. I would fix 1-3 (and ideally 4) before merging. As a library function with trusted callers, it is otherwise sound.
