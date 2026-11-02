# Search API round 2: both round-1 bugs are fixed, but I'd fix two new medium findings before merging

Nothing high-severity came back. The two medium findings are cheap to fix, and with a public API a client can trigger either one.

## Fix check: both round-1 bugs are fixed
Each repro still triggers the bug at round-1 and no longer does at round-2. Full output is in `outputs/fix-check-round2.md`.

| | round-1 (87fe0d8) | round-2 (6746708) |
|---|---|---|
| R1-1 `r1_1_cursor_gap.py` | `REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1]…`, exit 1 | `does not reproduce`, exit 0 |
| R1-2 `r1_2_like_wildcard.py` | `REPRODUCES: search('100%') returned ['1000 done', '100% done']`, exit 1 | `does not reproduce`, exit 0 |

One small correction to the R1-1 write-up: at round-1 a row was **repeated** at each page boundary, not skipped. The cause you gave was right.

## Fresh review of main..feature/search-api
This reviewer wasn't told about round 1. `pytest` gave 3 passed. Full report is in `outputs/review-round2.md`. I read `notes/search.py` at 6746708 myself, and the code matches each finding.

**Medium:**
1. **Page size isn't validated** (`notes/search.py:37-38`). `page_size=0` raises `IndexError`, and `page_size=-1` returns every row. The reviewer ran both.
2. **A bad `page_token` crashes instead of being rejected** (`notes/search.py:21`, via `_decode` at line 10). It surfaces as a 500 rather than an "invalid token" error. `"garbage!"` raised `binascii.Error` when run. By reading the code, a token missing keys or an old offset-format token would raise `KeyError`.

**Low:**
- When the result count is an exact multiple of the page size, the last full page still carries a token, so the client makes one extra request and gets an empty page.
- The token isn't tied to the search term, so reusing it with a different term silently skips newer rows.
- `created_at` is compared as text, so ordering is only right if every timestamp uses the same fixed-width format.
- `term=None` crashes, and `''` matches every note.
- **Test gap:** every note in the paging test has the same `created_at`, so the `created_at < ?` part of the query is never exercised. Only `%` escaping is tested, not `_` or `\`.

**Nit:** the SQL query is written out twice, once per branch.

## Recommendation
Fix the two medium findings and give the paging test notes with different dates, then merge. If `page_size` and `page_token` never come straight from clients, it's mergeable as is. That's your call. I can send one agent to make those fixes, with the findings word for word, and run a round-3 check.

## Housekeeping
- **Commit not in the bundle:** your local branch has a commit that isn't in `repo.bundle`: 1ab3d94 "eval setup". The review covered the bundle tip, 6746708.
- **Prompt copies:** `outputs/subagent-prompt-01.md` through `05.md`.
- **Tracking (local mode, no remote):** the task tracker is `.cadence/workstreams/search-api-round2.tasks.json`. Both tasks are done, with evidence and token counts.
- **Leftover worktree:** the fix check left one at `/tmp/cr-run.UrOA8FEV/wt-round1`.
- **Not merged or deployed.**