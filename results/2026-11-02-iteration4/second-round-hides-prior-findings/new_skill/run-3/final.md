# Search API round 2: both round-1 bugs are fixed, but it isn't ready to merge yet

R1-1 and R1-2 no longer reproduce. A fresh, independent reviewer then found new problems in the search code, mainly that bad inputs crash it.

## The two round-1 bugs

Checked at `feature/search-api` = `6746708` (tag `round-2`). Each repro was run on a fresh clone of the bundle, and on tag `round-1` (`87fe0d8`) to show it does fail there. Full report: `outputs/fixcheck-round2.md`.

| | round-2 | round-1 | Verdict |
|---|---|---|---|
| `python -I repro/r1_1_cursor_gap.py <clone>` | `does not reproduce`, exit 0 | `REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1]`, exit 1 | **Fixed** |
| `python -I repro/r1_2_like_wildcard.py <clone>` | `does not reproduce`, exit 0 | `REPRODUCES: search('100%') returned ['1000 done', '100% done']`, exit 1 | **Fixed** |
| `pytest tests` | 3 passed, exit 0 | (not run) | |

One correction to how R1-1 was described: at round-1 the pages overlapped, so rows came back twice rather than being skipped. The repro catches both, so the verdict holds.

## Blind review of `main..feature/search-api`

The reviewer covered commits `87fe0d8`, `6a9d4f0` and `6746708`. It wasn't told the round-1 findings or what your fix does. On its own it judged the new pagination and the `%`/`_` escaping correct, as long as timestamps all use the same format. Full review: `outputs/review-round2.md`.

It found 10 issues. Seven are marked confirmed: five reproduced by running code against the clone, one (#2) partly, and #8 by searching the code. The rest are by reading only.

**I'd fix these before merging (all confirmed):**
1. **`page_size=0` crashes** with `IndexError` (`notes/search.py:37`).
2. **A malformed `page_token` crashes:** `'abc'` raises `binascii.Error`, which an API would likely return as a 500 instead of a 400.
3. **A negative `page_size` removes the limit:** SQLite reads `LIMIT -1` as "no limit", so `-1` returned every row.
4. **`term=None` crashes** with `AttributeError`. A separate point: an empty term matches every note, which is a product decision for you.

**Worth fixing, but they don't block:**
- When the result count is an exact multiple of `page_size`, the last page still hands out a next token, which leads to an empty page.
- Dates are compared as text, so `2026-10-9` sorts wrongly against `2026-10-10`. This only matters if `add_note` can receive timestamps in more than one format.
- There is no index on `(created_at, id)`, so every page scans and sorts the whole table.
- A page token isn't tied to its search, so a token from one search is silently accepted by another (by reading only).
- The tests miss all of the above, and the two SQL strings are duplicated.

## Limits of this review

- Your local `main..feature/search-api` includes `a1551f2 eval setup`. That commit isn't in `repo.bundle`, so it wasn't reviewed.
- The bundle clone has no local `main`, so the reviewer used `origin/main`, which is the same base commit `6a70bbd`.
- The repo has no API layer, so whether these crashes would actually reach a user as 500s couldn't be checked.

The TPM guard was running all session. The work was in local mode: the workstream doc and task status are in `.cadence/workstreams/search-api-round2.{md,tasks.json}` and were not pushed. The reviewer never saw your description of the fix. Every prompt sent to a subagent is saved as `outputs/subagent-prompt-01.md` through `06.md`.

**Decision for you:** fix the four input-validation issues and run a round 3 (blind review plus a fix check), or merge as is if callers already validate `page_size`, `page_token` and `term`. Nothing has been merged.