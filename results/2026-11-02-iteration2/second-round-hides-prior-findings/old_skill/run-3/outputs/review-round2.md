# Code review, round 2: 6a70bbd..6746708 (feature/search-api)

- Scope: `notes/search.py` (+40) and `tests/test_search.py` (+31), reviewed in `/tmp/cr-run.UrOA8FEV/clone` at 6746708.
- Method: `/code-review high`. No code changes were made and no other agents were used. Every finding below was re-checked by hand against the clone.
- Tests: `python -m pytest -q` gave **3 passed** (test_finds_by_title, test_pages_cover_all_rows_once, test_percent_is_literal).
- Round-1 fixes: `python -I repro/r1_1_cursor_gap.py <clone>` and `python -I repro/r1_2_like_wildcard.py <clone>` both printed "does not reproduce" and exited with 0.
  - R1-1 (cursor gap) is fixed by the `(created_at, id)` keyset cursor.
  - R1-2 (LIKE wildcard) is fixed by `escape_like` with `ESCAPE '\'`.
- No high-severity correctness bug was found.

## Findings

### 1. Medium: `page_size=0` crashes with IndexError, and a negative page_size returns all rows
- Location: `notes/search.py:37-38`
- `LIMIT 0` returns `[]`. Since `0 == 0` is true, line 38 then evaluates `rows[-1]` and raises IndexError.
- `page_size=-1` becomes `LIMIT -1` in SQLite, which returns every row with no token.
- page_size is never validated or clamped.
- How I confirmed it: in a Python session against the clone, `search(db, "n", page_size=0)` raised `IndexError: list index out of range`. `page_size=-1` returned all 4 rows and `None`.

### 2. Medium: an invalid page_token raises uncaught exceptions
- Location: `notes/search.py:21` (through `_decode` at line 10)
- The token comes from the client but is decoded without any validation.
- Malformed base64 raises `binascii.Error`. Base64 that isn't JSON raises `JSONDecodeError`. JSON without the `created_at` or `id` keys raises `KeyError`, and so does an old offset-format token from 87fe0d8. Behind an API, each of these becomes a 500 instead of an "invalid token" error.
- How I confirmed it: `search(db, "n", page_token="garbage!")` raised `binascii.Error: Incorrect padding`. I verified the KeyError and JSON cases by reading the code.

### 3. Low: a page-aligned result set ends with an extra, empty page
- Location: `notes/search.py:37`
- A token is issued whenever a page is full. When the match count is an exact multiple of page_size, the client makes one more request and gets `([], None)`.
- Fix: fetch `LIMIT page_size + 1` and trim the extra row.
- How I confirmed it: with 4 notes and page_size=2, page 2 returned ids [2, 1] with a non-null token, and page 3 returned `([], None)`.

### 4. Low: the cursor isn't bound to the search term
- Location: `notes/search.py:21`
- A token from `search('tax')` is silently accepted by `search('groc')`. The second query then starts after the last 'tax' row, so newer 'groc' notes are skipped without any error.
- How I confirmed it: by reading the code. The token holds only `{created_at, id}`.

### 5. Low: ordering depends on TEXT timestamps all having the same fixed-width format
- Location: `notes/search.py:25-26` and `notes/store.py` (`created_at TEXT`)
- created_at is compared as text. The store accepts any string, so mixed formats such as `'2026-9-30'` vs `'2026-10-01'`, or a date-only value next to a full datetime, sort wrongly. The cursor would then skip or repeat rows.
- How I confirmed it: by reading the code and the schema. This is latent, since all current callers and tests use `YYYY-MM-DD`.

### 6. Low: an empty or None term isn't handled
- Location: `notes/search.py:19` (`escape_like` at line 14)
- `search(db, None)` raises AttributeError. `search(db, '')` builds the pattern `%%` and matches every note, which may or may not be intended.
- How I confirmed it: running `search(db, None)` raised `AttributeError`. I checked the `''` case by reading the code.

### 7. Low (test gap): the pagination test never exercises the `created_at < ?` branch
- Location: `tests/test_search.py:16`
- All 5 notes share `created_at="2026-10-01"`, so every page goes through the `created_at = ? AND id < ?` tie-breaker. Dropping or inverting `created_at < ?`, or sorting ASC, would still pass.
- There are also no tests for:
  - a page-aligned count (finding 3)
  - page_size <= 0 (finding 1)
  - an invalid token (finding 2)
  - `_` or `\` escaping (only `%` is tested)
- How I confirmed it: by reading the test. The r1_1 repro, which uses distinct dates, covers the `created_at < ?` path outside the suite.

### 8. Nit (maintainability): duplicated SQL in the two branches
- Location: `notes/search.py:20-35`
- The two branches differ only in the keyset predicate, so a future change to columns, filters or ordering has to be made in both places. Build the query once and add the clause conditionally.
- How I confirmed it: by reading the code.

## Left out / not covered
- The review skill reported `rows[-1]` at line 39. The actual line is 38, and I corrected it above. All other locations were re-checked.
- Security: all values are bound parameters, so there is no SQL injection. A forged token can only move the cursor within the same user-visible query, and no tenant or ownership model exists to bypass. Nothing to report.
- LIKE in SQLite is case-insensitive for ASCII only. Non-ASCII titles match case-sensitively. This is pre-existing behaviour and isn't part of this diff's intent, so I didn't count it as a finding.
- Performance: there is no index on `(created_at, id)`, and `%term%` can't use an index anyway. This is fine at the current scale, so it isn't listed.
- I ran pytest and the repro scripts in the clone, then removed the `__pycache__` and `.pytest_cache` directories. `git status` in the clone is clean.
