# Search API code review, round 2: main..6746708 (tag round-2)

- **Target:** a fresh clone of `/tmp/cr-run.hszGdFxu/repo/repo.bundle` at `/tmp/cr-clone.8rNDZJ/clone`, made in a new empty directory. Range `origin/main` (6a70bbd)..`6746708` (= tag `round-2`), with 3 commits: 87fe0d8, 6a9d4f0 and 6746708. Files: `notes/search.py` (+40) and `tests/test_search.py` (+31).
- **Judged against:** the Ask, Scope and Decisions sections of `workstreams/search-api-round2.md@449655c`, which ask for correctness of the search API as built. No spec document exists. Out of scope: commit 5ec1bcf and making fixes.
- **Effort:** high. No subagents were used because the diff is 71 lines.
- **Probe scripts:** kept outside the clone at `/tmp/cr-probes.8rNDZJ/probe.py`. I ran them with `cd /tmp; python3 -I /tmp/cr-probes.8rNDZJ/probe.py /tmp/cr-clone.8rNDZJ/clone`.

## Verdict: merge-ready: YES, with two non-blocking findings

The two main correctness problems of the round-1 code are fixed and the new tests check for them:
- Pagination returned duplicate rows.
- LIKE wildcards in the search term were not escaped.

The remaining findings only trigger on invalid input (`page_size` of 0, or a malformed or tampered `page_token`). The repo has no HTTP or API layer, so it is unclear whether these values can reach `search()` from untrusted callers without validation. If they can, findings 1 and 2 should be fixed before the branch is exposed. They do not need to block a library-level merge.

## Tests

```
$ cd /tmp/cr-clone.8rNDZJ/clone && git checkout -q 6746708 && python3 -m pytest -q
...                                                                      [100%]
3 passed in 0.02s
```

The new tests fail on the round-1 code, so they do detect the regressions. I swapped in round-1's `notes/search.py` with the round-2 tests, then restored it:

```
$ git checkout -q round-1 -- notes/search.py && python3 -m pytest -q
FAILED tests/test_search.py::test_pages_cover_all_rows_once - assert ([1, 2, ...
FAILED tests/test_search.py::test_percent_is_literal - AssertionError: assert...
2 failed, 1 passed in 0.02s
$ git checkout -q 6746708 -- notes/search.py
```

## (a) Fix check of round-1 issues

**Caveat:** I did not have the round-1 findings list or its repro commands. They are not in the Ask, Scope or Decisions sections, and I was told not to read Notes or anything else in `outputs/`. So I worked out the round-1 defects myself by diffing tag `round-1` (87fe0d8) against `round-2`, and ran the same probe script against both versions. Each fix check below is against my own repro, not the original round-1 one.

| Round-1 defect (my reconstruction) | Probe input | round-1 output | round-2 output | Status |
|---|---|---|---|---|
| Off-by-one cursor: `offset + page_size - 1` at round-1 `search.py:23` re-emits the last row of each page | 5 rows, same `created_at`, walk all pages with `page_size=2` | `([1, 2, 2, 3, 3, 4, 4, 5, 5], 5)`: duplicates | `([5, 4, 3, 2, 1], 3)` | Fixed |
| Same defect with an exact-multiple page | 5 rows, `page_size=5` | `([1, 2, 3, 4, 5, 5], 2)` | `([5, 4, 3, 2, 1], 2)` | Fixed |
| Non-deterministic order on tied `created_at` (`ORDER BY created_at DESC` only) | same data | ascending ids returned for a "newest first" API; tie order not defined | `ORDER BY created_at DESC, id DESC` with keyset `(created_at, id)` gives a stable order | Fixed |
| `%` in the term not escaped | `search(db, "100%")` with titles `100% done` and `1000 done` | covered by `test_percent_is_literal`, which fails on round-1 (see above) | passes | Fixed |
| `_` in the term not escaped | `search(db, "a_b")` with titles `a_b` and `axb` | `['axb', 'a_b']` | `['a_b']` | Fixed (no test; see finding 4) |
| Backslash handling | `search(db, "c\\d")` with titles `c\d` and `cd` | `['c\\d']` | `['c\\d']` | OK in both |

## (b) Findings

### 1. `page_size=0` crashes with IndexError, a regression from round-1 (medium)

**Where:** `notes/search.py:37-38`

`LIMIT 0` returns `[]`. Then `len(rows) == page_size` is `0 == 0`, which is true, so `rows[-1]` raises. Round-1 returned `([], <token>)` for the same call.

There is also no lower bound on `page_size`: `page_size=-1` becomes `LIMIT -1`, which means unlimited in SQLite, so every matching row comes back in one page.

- **Failing input:** `search(db, "n", page_size=0)`
- **Command:** `cd /tmp; python3 -I /tmp/cr-probes.8rNDZJ/probe.py /tmp/cr-clone.8rNDZJ/clone`
- **Output:**
  ```
  ps=0 -> EXC IndexError list index out of range
  ps=-1 -> ([{'id': 5, ...}, {'id': 4, ...}, {'id': 3, ...}, {'id': 2, ...}, {'id': 1, ...}], None)
  ```
  (round-1 printed `ps=0 -> ([], 'eyJvZmZzZXQiOiAtMX0=')`)

### 2. A malformed or tampered `page_token` raises unhandled exceptions of mixed types (medium, if tokens come from clients)

**Where:** `notes/search.py:9-10` and `notes/search.py:21` (then `c["created_at"]` and `c["id"]` at line 28)

`_decode` does no validation. Depending on the bad input, `search()` raises `binascii.Error`, `json.JSONDecodeError` or `KeyError`. A caller cannot catch one "invalid token" error and turn it into a 400 response. The token is also not tied to the search term. That does not leak rows, because the LIKE filter still applies and the query is parameterized, so there is no injection.

- **Failing inputs:** `page_token="garbage"`, `"!!!!"`, `"e30="` (`{}`), `"eyJjcmVhdGVkX2F0IjogMX0="` (`{"created_at": 1}`)
- **Command:** the probe script above, plus an inline `python3 -I -c` loop over the extra tokens.
- **Output:**
  ```
  token='garbage' -> EXC Error Incorrect padding                       # binascii.Error
  token='e30='({}) -> EXC KeyError 'created_at'
  '!!!!' EXC json.decoder.JSONDecodeError Expecting value: line 1 column 1 (char 0)
  'eyJjcmVhdGVkX2F0IjogMX0=' EXC builtins.KeyError 'id'
  ```

### 3. Exact-multiple result sets return a token that leads to an empty page (low)

**Where:** `notes/search.py:37`

A full page is taken to mean "more rows exist". When the match count is an exact multiple of `page_size`, the caller gets a `next_page_token` and then a page with no rows. Every row is still returned exactly once, so this is not a correctness bug. It costs one extra round trip and can show an empty "next page" in a UI. Fetching `page_size + 1` rows would avoid it.

- **Failing input:** 5 matching rows, `page_size=5`
- **Output:**
  ```
  ps=5 first page token -> True
  ps=5 second page -> ([], None)
  ```

### 4. Gaps in test coverage (low, no runtime bug)

**Where:** `tests/test_search.py`

- No test for `_` or `\` being literal. The `_` fix is only checked by my probe (`['a_b']`).
- `test_pages_cover_all_rows_once` (`tests/test_search.py:14-23`) checks for uniqueness and the count. It does not check the order ("newest first", tie broken by id).
- No test where pages span different `created_at` values.
- No tests for findings 1-3.

### Checked, no finding

- `ESCAPE '\'`: the Python literal `'\\'` gives a valid SQLite escape clause. A term ending in a backslash is handled.
- Case-insensitive match (`GROC` finds `Groceries`): this is SQLite's ASCII LIKE behaviour.
- The keyset predicate `(created_at < ? OR (created_at = ? AND id < ?))` matches `ORDER BY created_at DESC, id DESC`. Rows inserted between page requests do not cause duplicates or skips among rows that already existed.
- SQL injection: everything is parameterized.
- `term=None` raises AttributeError in round-2, where round-1 returned `([], None)`. This is a caller type error, so I am not reporting it as a finding.

## What I left out

- **Round-1 findings and repro commands:** I did not read them (see the caveat in section (a)). Section (a) is a reconstruction.
- **Files I did not open:** the Notes and "Status and evidence" sections of the workstream file, and every other file in `outputs/`.
- **Outside the diff:** `notes/store.py` (base commit). For example, `created_at` is ordered as text, so mixed timestamp formats or timezones would sort wrongly. That comes from the store, not this branch.
- **Not tested:** performance, since `LIKE '%term%'` always does a full scan and there is no index; non-ASCII case folding; and concurrency beyond reasoning about the keyset predicate.
- **No fixes made.** The clone was returned to 6746708 with a clean tree, apart from `__pycache__`.
