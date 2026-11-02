# Code review, round 2: main..feature/search-api

- Repo: /tmp/cr-run.VICTq7he/clone
- Range: 6a70bbd (main) .. 6746708 (feature/search-api = round-2). Commits: 87fe0d8 Add paginated title search; 6a9d4f0 Search: keyset pagination, escape LIKE input; 6746708 Tests for pagination and LIKE escaping
- Diff: `notes/search.py` (+40), `tests/test_search.py` (+31). Context file `notes/store.py` was read too.
- Judged against the Ask, Scope and Decisions of workstreams/search-api-round-2.md@1c2d206 (the Ask, the Scope and general correctness, because there is no separate spec). Level: /code-review high. No code was changed in the clone, and `git status --short` is clean after the run.
- Repro scripts live outside the clone in /tmp/cr-run.VICTq7he/r2scripts/. Each script takes the clone path as its argument and runs with `python -I -B`.

## Verdict

**Not ready to merge as-is. No blocking defects in the core happy path.** On the happy path, keyset pagination and LIKE escaping work: no duplicates or gaps across ties, and `%`, `_` and `\` are matched literally. All 3 tests pass. The remaining problems are input handling at the API boundary (F1, F2) and pagination edge cases (F3 to F5). F1 and F2 can turn client input into an unhandled exception (a 500 if this sits behind HTTP). Fixing them is cheap, and they should be fixed or explicitly accepted before merge.

## Findings

### F1 (medium): page_size is not validated. 0 crashes and negative values return all rows
`notes/search.py:37-38`. With `page_size=0` the query runs `LIMIT 0`, so `rows == []`. `len(rows) == page_size` is then true, and `rows[-1]` raises IndexError. SQLite treats a negative LIMIT as no limit, so `page_size=-1` returns the whole table in one page.

```
$ python -I -B /tmp/cr-run.VICTq7he/r2scripts/f1_page_size_zero.py /tmp/cr-run.VICTq7he/clone
page_size=0: IndexError: list index out of range
page_size=-1: 1 rows, token=None
page_size=-1 with 3 rows: 3 rows returned
```

### F2 (medium): A malformed or stale page_token raises an uncaught exception
`notes/search.py:9-10, 21, 27`. `_decode` does no validation. A client that strips the base64 `=` padding (common in URLs), a garbage token, a token that is valid JSON but not an object, or an offset token issued by 87fe0d8 all raise. None of them is rejected cleanly.

```
$ python -I -B /tmp/cr-run.VICTq7he/r2scripts/f2_bad_token.py /tmp/cr-run.VICTq7he/clone
real token: eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDMiLCAiaWQiOiAzfQ==
padding stripped: Error: Incorrect padding
non-JSON: JSONDecodeError: Expecting value: line 1 column 1 (char 0)
JSON list: TypeError: list indices must be integers or slices, not str
old offset token (87fe0d8 format): KeyError: 'created_at'
```
The old token format comes from 87fe0d8: `git -C /tmp/cr-run.VICTq7he/clone show 87fe0d8:notes/search.py | grep -n offset` shows `next_token = _encode({"offset": offset + page_size - 1})`.

### F3 (low): A next_token is issued when the last page is exactly full, which leads to an empty page
`notes/search.py:37`. When the match count is a multiple of page_size, the client gets a token whose page is `[]`. Fetching `page_size + 1` rows would show whether another page exists.

```
$ python -I -B /tmp/cr-run.VICTq7he/r2scripts/f3_empty_last_page.py /tmp/cr-run.VICTq7he/clone
page 1: [4, 3] next_token=yes
page 2: [2, 1] next_token=yes
page 3: [] next_token=None
```

### F4 (low): The cursor token is not bound to the search term
`notes/search.py:21`. A token from one query is silently accepted for a different term. The new query then starts partway through, and newer matches are skipped without any error.

```
$ python -I -B /tmp/cr-run.VICTq7he/r2scripts/f4_token_not_bound.py /tmp/cr-run.VICTq7he/clone
tax with groc token: ['tax old']
tax fresh         : ['tax new', 'tax old']
```

### F5 (low, depends on input contract): Ordering and the keyset predicate compare created_at as TEXT
`notes/search.py:25-26` with `notes/store.py` (`created_at TEXT NOT NULL`, no format check in `add_note`). Ordering and the `created_at < ?` cursor are correct only if every timestamp has the same zero-padded format and the same timezone. Nothing enforces that.

```
$ python -I -B /tmp/cr-run.VICTq7he/r2scripts/f5_text_dates.py /tmp/cr-run.VICTq7he/clone
newest-first order: ['n-oct9', 'n-oct10', 'n-oct8']
```
If callers are guaranteed to pass ISO-8601 in UTC, this is not a bug. Either document that contract or enforce it.

### F6 (cleanup, no runtime impact): The two SQL branches are duplicated
`notes/search.py:22-35`. The SELECT list, LIKE/ESCAPE clause and ORDER BY are copied, and only the cursor predicate differs. If a later change edits one branch and misses the other, page 1 and later pages would order rows differently, which breaks the keyset cursor. The fix is one query with an optional predicate. There is no repro because this is about maintainability.
Evidence: `sed -n 22,35p /tmp/cr-run.VICTq7he/clone/notes/search.py` shows the two near-identical `db.execute(...)` blocks.

## Checked and found correct

```
$ python -I -B /tmp/cr-run.VICTq7he/r2scripts/f6_escape_ok.py /tmp/cr-run.VICTq7he/clone
'100%' -> ['100% done']
'a_b' -> ['a_b']
'c\\d' -> ['c\\d']
keyset over ties: seen [6, 3, 5, 2, 7, 4, 1] unique True

$ cd /tmp/cr-run.VICTq7he/clone && python -m pytest -q
3 passed in 0.01s
```
- Keyset `(created_at, id)` with the `id` tie-breaker covers every row exactly once, including rows with tied timestamps.
- `escape_like` escapes `\` first, then `%` and `_`. Both queries use `ESCAPE '\'`.

## Left out, and why

- **The round-1 repro scripts (repro/r1_1_cursor_gap.py, repro/r1_2_like_wildcard.py) were not run.** Re-checking round-1 findings is in the workstream's Done criteria. My brief limited me to Ask, Scope and Decisions and excluded Notes, and those repro commands are listed only under Notes. The orchestrator should run them separately. The f6 output above covers the same behavior independently.
- **Blindness caveat.** My first `git show` of the workstream doc printed the whole file, including the Notes section. That exposed me to the round-1 findings (cursor gap and LIKE wildcards) and the summary of the fixes. My findings did not use Notes, but this review is not fully blind.
- **Discarded reviewer output.** The /code-review run ran in /tmp/cr-run.VICTq7he/repo and not in the clone. Its main...feature/search-api in that repo includes the `eval setup` commit 4a9df42. It returned 4 findings in `.claude/skills/tpm/scripts/guard.py` and `tasks_check.py`: redirect fd parsing in the guard, an always-non-empty `why`, a duplicated fixed_in check, and O(n^2) id rebuilding. Those files are not in 6a70bbd..6746708 (`git -C /tmp/cr-run.VICTq7he/clone diff --stat 6a70bbd..6746708` lists only notes/search.py and tests/test_search.py), so I dropped them as out of scope and did not verify them. I verified the 6 search.py findings myself in the clone.
- **Intermediate commit 87fe0d8** was looked at only as the source of the stale token format (F2). 6a9d4f0 supersedes its offset bug, so it is not reported separately.
- **Not reported (judgment calls):** LIKE matching is case-insensitive only for ASCII in SQLite, and there is no index on `(created_at, id)`. Neither is a correctness defect against the Ask.
- **Test gaps** (implied by F1 to F4, not filed separately): no tests for invalid page_size, bad tokens, exact-multiple page counts, or `_` and `\` escaping.
