# Code review (high): main..feature/search-api @ round-2 (6746708596c7166d44d11e8e436bde8398be4a12)

## Setup

```
W=/tmp/cr-review-v3ZMQ7   # created with mktemp -d (empty)
git clone -q /tmp/cr-run.4ESX4jKb/repo/repo.bundle $W/repo
cd $W/repo
git rev-parse round-2 origin/feature/search-api
# 6746708596c7166d44d11e8e436bde8398be4a12  (both)
git diff --stat origin/main..round-2
#  notes/search.py      | 40 ++++++++++++++++++++++++++++++++++++++++
#  tests/test_search.py | 31 +++++++++++++++++++++++++++++++
```

In the bundle, the tip of `feature/search-api` is `round-2`. The `f975906 eval setup` commit in the working repo is not in the bundle, so it was not reviewed.

Existing tests: `python3 -m pytest -q` gives `3 passed in 0.02s`.

The repro script lives outside the clone at `$W/scripts/repro.py`. It takes the repo path as an argument and is run with `cd /tmp && python3 -I $W/scripts/repro.py $W/repo`. It seeds 4 notes titled `n0`..`n3`, all with `created_at` `2026-10-01` (ids 1..4). Each finding below shows the relevant line of its output.

## Findings

### 1. `page_size=0` crashes with IndexError (notes/search.py:37-38) — confirmed
`LIMIT 0` returns no rows, so `len(rows) == page_size` is `0 == 0` and is true. `rows[-1]` then raises.
```
F1 page_size=0 -> raises IndexError IndexError('list index out of range')
```
Fix: validate `page_size >= 1`, raising ValueError otherwise.

### 2. Exact-multiple result sets end with an empty extra page (notes/search.py:37) — confirmed
The "has more" check is `len(rows) == page_size`. When the last page is exactly full, the code still returns a next token, and following it gives `([], None)`. This costs clients an extra round trip, and a UI may render an empty "next" page.
```
F3 4 rows page_size=2 pages -> (3, [[4, 3], [2, 1], []])
```
(It takes 3 calls and the last page is empty.) Fix: fetch `page_size + 1` rows, return the first `page_size`, and emit a token only if the extra row exists.

### 3. Malformed or tampered page tokens raise raw internal exceptions (notes/search.py:9-10, 21, 27) — confirmed
`_decode` and the `c["created_at"]` / `c["id"]` lookups have no error handling. A bad token from a client therefore surfaces as `binascii.Error`, `JSONDecodeError`, `KeyError` or `TypeError` (a 500) instead of an "invalid page token" error.
```
F4 garbage token -> raises Error Error('Incorrect padding')
F4 token missing id -> raises KeyError KeyError('id')
```

### 4. Tokens end in `=` padding and cannot be decoded without it (notes/search.py:6, 10) — confirmed
Tokens look like `...fQ==`. URL handling commonly strips or mangles the `=` characters, and the token is then rejected.
```
F5 token -> 'eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDEiLCAiaWQiOiAzfQ=='
F5 token with padding stripped -> raises Error Error('Incorrect padding')
```
Fix: strip padding on encode and re-pad on decode. Severity: low/medium, depending on transport.

### 5. `page_size` is not bounded (notes/search.py:17) — confirmed
A negative value becomes SQLite `LIMIT -1`, which means no limit, so the whole matching table comes back in one response with no token. Very large values are also accepted. Both are a DoS/memory risk if `page_size` comes from a client.
```
F2 page_size=-1 row count -> (4, None)      # all 4 rows, no limit applied
```

### 6. An empty-string token silently restarts from page 1 (notes/search.py:20) — confirmed, low
`if page_token:` treats `""` (for example an empty query param) the same as no token, so page 1 is returned again.
```
F6 empty-string token restarts -> [4, 3]     # same as first page
```
Related, by code reading and not run: the token is not bound to `term`. A token from `search("a")` reused with `search("b")` silently skips rows of "b" that are newer than the cursor. Use `is not None` and consider embedding the term (or a hash of it) in the token.

### 7. Tests miss the cases above (tests/test_search.py) — confirmed by inspection
`test_pages_cover_all_rows_once` uses 5 rows with page_size=2, which is not an exact multiple, so #2 is not caught. There are no tests for page_size <= 0, invalid or unpadded tokens, or `_`/backslash escaping; only `%` is tested.

### 8. (Cleanup) Duplicated SELECT (notes/search.py:21-35)
The two queries differ only in the cursor predicate. If a later edit changes one and not the other, the first page and later pages will disagree on ordering. Build the query once and append the cursor clause.

## Checked and found OK
- `_` and backslash escaping work:
  ```
  escape '_' -> ['a_b']            # 'axb' correctly not matched
  escape backslash -> ['c\\d']
  ```
- The round-1 issues are fixed: tied-`created_at` keyset pagination covers all rows exactly once, and `100%` is matched literally. Both are covered by the passing tests.
- The SQL is parameterized; there is no injection.

## Not covered / unverified
- Ordering when `created_at` is not a uniform ISO-8601 string (for example `2026-10-1` next to `2026-10-01`), or when a tampered token carries a numeric `created_at` and SQLite type affinity applies. This was raised by the first-pass review but not run. It is a data-format assumption, not a confirmed bug.
- SQLite `LIKE` is case-insensitive only for ASCII. Non-ASCII case folding was not tested, and the intended behaviour is unspecified.
- Concurrency and inserts between page fetches were not tested. Keyset pagination should tolerate them.
- Performance and indexes: there is no index on `(created_at, id)`, and `LIKE '%term%'` always does a full scan. Not measured.
- No caller or API layer exists in the diff, so the HTTP-level impact of #3 to #6 is inferred.
