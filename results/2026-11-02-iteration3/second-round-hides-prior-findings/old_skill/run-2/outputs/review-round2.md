# Code review (high): main..feature/search-api (6a70bbd..6746708)

Repo: /tmp/cr-run.KfFbz0Z7/clone
Commits in range: 87fe0d8 Add paginated title search, 6a9d4f0 Search: keyset pagination, escape LIKE input, 6746708 Tests for pagination and LIKE escaping.
Files: notes/search.py (+40), tests/test_search.py (+31).

Status: completed (not blocked). Python 3 / SQLite 3.53.1. Existing suite: 3 passed.
I ran every runtime claim below with my own probe script (/tmp/cr-scripts-04/probe.py) against the clone, plus an EXPLAIN QUERY PLAN. I made no fixes.

Process note: I invoked `/code-review high` through the Skill tool. The harness ran that skill as a forked execution, so its first pass was not done in this agent's own thread. I did not start any agents myself. After the skill returned, I re-ran every finding it based on running code. "Confirmed" below means I reproduced it myself. "Read-only" means it comes from reading the code only.

## Findings (most severe first)

1. **Empty trailing page when the result count is an exact multiple of page_size** (notes/search.py:37-38, correctness). Confirmed.
   `if len(rows) == page_size` returns a token even when no more rows exist. With 4 matches and page_size=2, page 2 returns a token, and following it returns `([], None)`. Clients get an empty page and run an extra query, and a "Next" link leads to nothing. Fix: fetch `LIMIT page_size + 1` and only return a token if the extra row exists.

2. **page_size is not validated** (notes/search.py:17/37-39, correctness). Confirmed.
   `page_size=0` raises `IndexError` because `len([]) == 0` leads to `rows[-1]`. `page_size=-1` turns off the LIMIT in SQLite and returned all 4 rows, unpaginated. If page_size comes from the client, a negative value gets around paging.

3. **Malformed page_token raises uncaught exceptions** (notes/search.py:9-10, 21, robustness/API). Confirmed.
   `"garbage!"` raises `binascii.Error: Incorrect padding`, and a token encoding `{}` raises `KeyError: 'created_at'`. A wrapping API would return a 500 instead of a 400 "invalid page token". Wrong types (for example `{"created_at": 1, "id": "x"}`) would also pass through without an error.

4. **Cursor is not tied to the query** (notes/search.py:20-28, correctness). Confirmed.
   Reusing a token from a search for "tax" in a search for "groc" returned `([], None)`, even though "groc" is the newest note. Results are skipped with no error. Fix: include the term (and ideally page_size) in the token and reject a mismatch.

5. **Token depends on '=' padding** (notes/search.py:5-10, robustness). Confirmed.
   A sample token is `eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDEiLCAiaWQiOiAzfQ==`. With the padding stripped, decoding raises `Incorrect padding`. '=' is also a reserved character in query strings. Fix: strip the padding when encoding and add it back when decoding.

6. **No index supports the keyset order** (notes/search.py:24-26 vs notes/store.py schema, performance). Confirmed by query plan.
   EXPLAIN QUERY PLAN shows `SCAN notes` + `USE TEMP B-TREE FOR ORDER BY`. Every page scans and sorts the whole table, so keyset pagination gains nothing over OFFSET. Adding an index on `(created_at, id)` would let SQLite read rows in index order and stop at LIMIT. The `%term%` LIKE still can't use an index, but stopping early still helps.

7. **The two SQL branches duplicate the same query** (notes/search.py:22-35, maintainability). Read-only.
   The two branches repeat the SELECT/WHERE/ORDER BY text and differ only in the keyset clause. If a later edit changes one branch and not the other, the first page and later pages would sort or filter differently, which breaks keyset correctness. Build the query once with an optional clause.

8. **Test gaps** (tests/test_search.py, test coverage). Read-only, but checked by the probes above.
   The tests use 5 rows with page_size=2, so they never hit the exact-multiple case. They don't cover page_size<=0, bad or stale tokens, or ties across different created_at values, and they test only '%' escaping, not '_' or '\'. Findings 1-5 all pass CI today.

## Verified working (no finding)
- Paging returns every row exactly once when the count isn't a multiple of page_size, including when all rows tie on created_at (the id tiebreak works).
- LIKE escaping: `a_b` does not match `axb`, `a\b` matches only itself, and `50%` does not match `500`. The `ESCAPE '\'` clause matches `escape_like`.
- All queries are parameterized, so there is no SQL injection.

## Left out / not reported as findings
- SQLite LIKE ignores case only for ASCII: "groc" matches "Groceries", but "ébène" does not match "Ébène". This is SQLite's built-in behavior and was not introduced by this diff. Worth noting if the product expects Unicode case folding.
- An empty term matches every note. This is probably intended (list all), and the docstring doesn't say otherwise.
- created_at is compared as TEXT. Ordering and the cursor comparison both use lexicographic order, so they stay consistent with each other. Mixed formats (date vs datetime with or without a timezone) would sort oddly, but store.py has the same problem, so I left it out.
- Deep security review, load testing, and concurrency (rows inserted between pages) were not examined beyond noting that keyset pagination is stable under inserts of newer rows.
- No CLAUDE.md or project conventions apply.

## Merge verdict
**Do not merge yet (request changes).** Findings 1-3 are correctness and robustness bugs you can easily hit in a public paginated API: an empty trailing page, a crash or lost limit from page_size, and 500s on bad tokens. Finding 4 silently skips results. All are small fixes. Fix 1-5, add an index for 6, and add tests for 8, then merge. Finding 7 is optional cleanup.
