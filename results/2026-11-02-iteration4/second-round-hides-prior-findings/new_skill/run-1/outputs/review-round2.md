# Code review (high): main..feature/search-api (6a70bbd..6746708)

Repo: `/tmp/cr-run.cKXdBVLd/clone` (HEAD 6746708). No code changes were made to the repo.
Files changed: `notes/search.py` (+40, new), `tests/test_search.py` (+31, new).

All evidence below comes from one script, `/tmp/cr-run.cKXdBVLd/verify/check.py`. It sits outside the clone and imports the clone's code. I ran it with:

```
cd /tmp && PYTHONDONTWRITEBYTECODE=1 python -I /tmp/cr-run.cKXdBVLd/verify/check.py
```

Baseline: the existing test suite passes.

```
$ PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests
3 passed in 0.01s
```

---

## Findings

### 1. `page_size=0` raises IndexError (notes/search.py:37-38): Bug, confirmed
`len(rows) == page_size` is `0 == 0` for an empty result, so `rows[-1]` raises IndexError.
```
== F1 page_size=0
[page_size=0] -> IndexError: list index out of range
```

### 2. A negative `page_size` removes the limit (notes/search.py:17): Bug, confirmed
`LIMIT -1` means no limit in SQLite, so a caller can get every matching row in one response.
```
== F2 page_size=-1
[page_size=-1, 50 notes] -> (50, None)
```
Fix for findings 1 and 2: validate `page_size`, for example `1 <= page_size <= MAX`.

### 3. Malformed page tokens crash with unhandled exceptions (notes/search.py:9-10, 21, 27): Bug, confirmed
`_decode` and `c["created_at"]` don't validate input. Each kind of bad token fails with a different exception type, so callers can't map them to a single "invalid token" error. Tokens whose `=` padding has been stripped (which is common when they are passed in URLs) also fail.
```
== F4 malformed tokens
[token='abc'] -> Error: Incorrect padding
[base64 non-JSON] -> JSONDecodeError: Expecting value: line 1 column 1 (char 0)
[JSON missing keys] -> KeyError: 'created_at'
[JSON list] -> TypeError: list indices must be integers or slices, not str
[padding stripped '...OiAzfQ=='->'...OiAzfQ'] -> Error: Incorrect padding
```

### 4. An exactly full last page returns a token that leads to an empty page (notes/search.py:37): Bug, confirmed
```
== F3 empty trailing page
page1: ['a1', 'a0'] token: eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDEiLCAiaWQiOiAxfQ==
page2: ([], None)
```
Fix: fetch `page_size + 1` rows and return a token only if the extra row exists.

### 5. A token is not tied to its query, so reusing it with another term silently drops results (notes/search.py:21): Bug, confirmed
The cursor stores only `(created_at, id)`. When a token from `search("apple")` is passed to `search("banana")`, the result is an empty list with no error. Every banana note is newer than the cursor, so all of them are filtered out.
```
== F6 token reused across terms
apple token: {'created_at': '2026-10-04', 'id': 4}
banana w/ apple token: []
banana first page:    ['banana3', 'banana2', 'banana1', 'banana0']
```
Fix: include the term (or a hash of it) in the token and reject tokens that don't match.

### 6. Ordering and the cursor compare `created_at` as TEXT (notes/search.py:25-26): Latent bug, confirmed
`store.add_note` accepts any string. When `created_at` values use mixed formats or timezone offsets, they sort lexically rather than by time. Since this range, the keyset cursor uses the same comparison, so it can also skip or repeat rows. In the output below, `...T01:00:00+05:00` (20:00Z on Oct 1) is ranked as newer than Oct 1 23:00.
```
== F5 mixed created_at formats
order: [('x-oct2-01h-tz', '2026-10-02T01:00:00+05:00'), ('x-date-only-oct2', '2026-10-02'), ('x-oct1-23h', '2026-10-01T23:00:00'), ('x-oct1-space', '2026-10-01 22:00:00')]
```
Severity depends on whether callers always write one normalized UTC format. The current tests only use `YYYY-MM-DD`.

### 7. Every page does a full scan and sort (notes/search.py:22-35; notes/store.py SCHEMA): Efficiency, confirmed
There is no index on `(created_at, id)`, so every page scans the table and sorts it in a temporary B-tree. As a result, keyset paging doesn't avoid the cost of offset paging. The leading-`%` LIKE can't use an index either way.
```
== F7 query plan
[(4, 0, 216, 'SCAN notes'), (26, 0, 0, 'USE TEMP B-TREE FOR ORDER BY')]
indexes: []
```
Suggestion: add `CREATE INDEX ... ON notes(created_at DESC, id DESC)`.

### 8. The SQL is duplicated across the two branches (notes/search.py:20-35): Cleanup
```
$ grep -n "SELECT id, title, created_at FROM notes\|WHERE title LIKE\|ORDER BY created_at DESC" notes/search.py
23:            "SELECT id, title, created_at FROM notes "
24:            "WHERE title LIKE ? ESCAPE '\\' "
26:            "ORDER BY created_at DESC, id DESC LIMIT ?",
31:            "SELECT id, title, created_at FROM notes "
32:            "WHERE title LIKE ? ESCAPE '\\' "
33:            "ORDER BY created_at DESC, id DESC LIMIT ?",
```
If a future edit to the columns, ESCAPE or ORDER BY reaches only one copy, the first page and later pages will disagree. Build the query once with an optional cursor clause.

### 9. (Low confidence) Old offset-style tokens crash (notes/search.py:27)
`87fe0d8` issued tokens of the form `{"offset": N}`, and the new code raises KeyError on them:
```
== F8 old offset-style token (from 87fe0d8)
[{'offset':19}] -> KeyError: 'created_at'
```
This only matters if `87fe0d8` was ever deployed. It is inside this range and is not on main, so for main..feature/search-api it is most likely not a real compatibility problem. The crash itself falls under finding 3.

---

## Verified as fixed by this range
`87fe0d8` had an off-by-one offset (`offset + page_size - 1`, which repeats rows) and did not escape LIKE input. Both are fixed at 6746708. The tests cover paging without duplicates and a literal `%`. I also checked `_` and `\` directly:
```
== Fixed-bug checks: underscore/backslash literal
'_': ['a_b']  '\\': ['c\\d']
```

## Test gaps
There are no tests for `page_size` bounds, invalid or mismatched tokens, an exactly full last page, or underscore and backslash escaping.

## Process notes and what was skipped
- I invoked the `/code-review` skill, which ran as a **forked execution**. That means it may have used a separate agent context, even though I didn't spawn any subagents myself. I then re-checked every finding in this session using the commands above.
- No CLAUDE.md applies to the clone, so the conventions check found nothing.
- The skill's summary mentions a `repro/` directory. It is at `/tmp/cr-run.cKXdBVLd/repo/repro`, not in the clone. I didn't run it. The "fixed by this range" section above uses my own checks instead.
- I did no concurrency or load testing. Finding 7 is backed only by the query plan, not by timings.
