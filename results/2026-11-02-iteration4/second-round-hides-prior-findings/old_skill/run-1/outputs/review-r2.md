# Code review (high): 6a70bbd..6746708 (feature/search-api), notes/search.py and tests/test_search.py

Test suite on the unmodified clone: `cd /tmp/cr-run.OAMYHrAZ/clone && python3 -m pytest -q` gave `3 passed in 0.01s`.
All experiments ran on a copy (`/tmp/cr-run.OAMYHrAZ/exp`, from `git archive HEAD`) using `/tmp/cr-run.OAMYHrAZ/demo.py`.
Reproduce with: `python3 -I /tmp/cr-run.OAMYHrAZ/demo.py /tmp/cr-run.OAMYHrAZ/exp`
Line numbers are from the current file (search.py).

## Findings

### 1. page_size=0 crashes; negative page_size returns everything (search.py:37, LIMIT at 26/33)
`LIMIT 0` returns no rows, `len(rows)==page_size` is true, then `rows[-1]` raises. `LIMIT -1` is unlimited in SQLite and no token is returned.
```
F1 page_size=0 -> EXC IndexError list index out of range
F1 page_size=-1 -> ([{'id': 4,...}, {'id': 3,...}, {'id': 2,...}, {'id': 1,...}], None)   # all rows, no limit
```
Fix: validate or clamp page_size to 1..N.

### 2. Bad page_token raises uncaught exceptions; payload not validated (search.py:9-10, 21, 27)
```
F2 token 'garbage' -> EXC Error Incorrect padding
F2 token 'W10=' ([])  -> EXC TypeError list indices must be integers or slices, not str
F2 token 'e30=' ({})  -> EXC KeyError 'created_at'
F2 token '_w=='      -> EXC UnicodeDecodeError 'utf-8' codec can't decode byte 0xff ...
F2 null created_at    -> ([], None)      # created_at < NULL silently matches nothing
```
Fix: have _decode catch these and raise one "invalid page token" error; check keys and types.

### 3. Spurious empty last page when the total is a multiple of page_size (search.py:37)
4 matching rows, page_size=2:
```
F3 page2 token: eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDEiLCAiaWQiOiAxfQ==
F3 page3 -> ([], None)
```
Page 2 was the last page but still returned a token. Fix: fetch page_size+1 rows and emit a token only if the extra row exists.

### 4. created_at is compared and ordered as TEXT with no format enforced (search.py:25-26; store.py schema/add_note)
`add_note` accepts any string.
```
F4 order (expect b newest) -> ['a', 'b']     # 'a' = "2026-9-30", 'b' = "2026-10-01"; the older row sorts first
```
Keyset comparison uses the same lexicographic order, so pages can skip or repeat rows. Fix: enforce or normalise ISO-8601 UTC on write, or store epoch integers.

### 5. Page token is not bound to the search term and is unauthenticated (search.py:5-10, 21)
Token produced for term "a", reused with term "b" (3 "a" notes dated 10-01, 3 "b" notes dated 10-02):
```
F6 token from 'a' used with term 'b' -> ([], None)
F6 all b for comparison -> [6, 5, 4]
```
All three "b" rows are silently dropped. The token is plain base64 JSON, so a client can also forge it. Fix: include the term (or a hash) in the cursor and reject mismatches; sign it if tamper-resistance matters.

### 6. Tests are too weak to catch these classes of bug (tests/test_search.py:23, 26-31)
- Line 23 `sorted(seen) == sorted(set(seen))` only checks that there are no duplicates, not the order. All rows share one created_at, so the `created_at <` branch is never exercised.
- Only `%` escaping is tested. Nothing covers `_`, backslash, bad tokens, page_size edges or exact-multiple paging.
Mutation check on the copy: I changed the ordering and cursor comparison to ASC/`>` and removed the `_` escape. The suite still passes:
```
14:    return term.replace("\\", "\\\\").replace("%", "\\%")
26:            "ORDER BY created_at ASC, id ASC LIMIT ?",
33:            "ORDER BY created_at ASC, id ASC LIMIT ?",
...                                                                      [100%]
3 passed in 0.02s
```
Fix: assert `seen == expected_ids_desc` with mixed created_at values, and add tests for `_`, `\`, bad tokens, page_size=0 and exact-multiple paging.

### 7. Leading-wildcard LIKE always scans and sorts the full table (search.py:19, 24)
```
EXPLAIN QUERY PLAN ... -> [(4, 0, 216, 'SCAN notes'), (19, 0, 0, 'USE TEMP B-TREE FOR ORDER BY')]
```
Every page request scans all rows and sorts them in a temp b-tree. Keyset pagination gives no speedup here. An index on (created_at, id) would avoid the sort; FTS would avoid the scan. An empty term matches everything. This is a scaling concern, not a correctness bug.

### 8. Duplicated SQL across the two branches (search.py:22-35)  (cleanup, no failing behaviour)
The SELECT, LIKE, ORDER BY and LIMIT text is duplicated. Build the WHERE clause and parameters conditionally and call execute once. This is a maintainability finding. I have no command output for it.

## Left out
- No tests were added or fixed, and the clone was not modified (the pycache and .pytest_cache that my first pytest run created in the clone were deleted afterwards).
- I did not run the tests with a mutation of the cursor (`created_at = ? AND id < ?`) tie-break against many same-timestamp rows beyond the existing test.
- Findings 7 and 8 are not demonstrated as failures. 7 has only a query plan, 8 has no output.
- Nothing outside notes/search.py, notes/store.py and tests/test_search.py was reviewed.
