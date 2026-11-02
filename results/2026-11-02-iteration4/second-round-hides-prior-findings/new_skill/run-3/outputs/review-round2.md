# Code review (high): main..feature/search-api

Review only. No fixes, no commits.

## Setup and scope

- Fresh clone of `/tmp/cr-run.IUIMLbzs/repo/repo.bundle` into the new empty directory `/tmp/cr-clone.s9LjZ7/repo`. All verification ran against that clone.
- In the clone, `main` exists only as the remote-tracking branch `origin/main`, so the literal `git log main..feature/search-api` fails. The range was resolved as `origin/main..feature/search-api`, which is the same base. It has 3 commits: 87fe0d8, 6a9d4f0, 6746708.
- The bundle does not contain the `a1551f2 eval setup` commit from the source repo, so it is not reviewed.
- Files changed: `notes/search.py` (+40) and `tests/test_search.py` (+31).
- Note: the initial `/code-review` skill pass ran in a forked context that did not report its working directory. It said it excluded `.claude/` and `repo.bundle`, which suggests it may have read the original repo instead of the clone. To keep this review to the fresh clone, every confirmed finding below was re-run against the clone. Findings marked "by inspection" were checked by reading the clone's code.

## Commands and raw output

```
$ D=$(mktemp -d /tmp/cr-clone.XXXXXX); ls -A "$D"; git clone /tmp/cr-run.IUIMLbzs/repo/repo.bundle "$D/repo"
CLONE_DIR=/tmp/cr-clone.s9LjZ7
Cloning into '/tmp/cr-clone.s9LjZ7/repo'...

$ git branch -a
* feature/search-api
  remotes/origin/HEAD -> origin/feature/search-api
  remotes/origin/feature/search-api
  remotes/origin/main

$ git log --oneline --all
6746708 Tests for pagination and LIKE escaping
6a9d4f0 Search: keyset pagination, escape LIKE input
87fe0d8 Add paginated title search
6a70bbd Notes store

$ git log --oneline main..feature/search-api
fatal: ambiguous argument 'main..feature/search-api': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'

$ git log --oneline origin/main..origin/feature/search-api
6746708 Tests for pagination and LIKE escaping
6a9d4f0 Search: keyset pagination, escape LIKE input
87fe0d8 Add paginated title search

$ git diff --stat origin/main..feature/search-api
 notes/search.py      | 40 ++++++++++++++++++++++++++++++++++++++++
 tests/test_search.py | 31 +++++++++++++++++++++++++++++++
 2 files changed, 71 insertions(+)

$ python3 -m pytest -q        (in clone)
...                                                                      [100%]
3 passed in 0.01s

$ python3 -I /tmp/cr-scripts/repro.py /tmp/cr-clone.s9LjZ7/repo   (script kept outside the clone)
page_size=0 -> EXC IndexError list index out of range
page_token='abc' -> EXC Error Incorrect padding
page_size=-1 count -> 4
p2 ids [2, 1] token True
p3 -> ([], None)
term='' -> 4
term=None -> EXC AttributeError 'NoneType' object has no attribute 'replace'
mixed-format order -> ['2026-10-9', '2026-10-10']

$ grep -n "INDEX\|CREATE" notes/store.py
5:CREATE TABLE IF NOT EXISTS notes (
```

The repro script inserts 4 notes `a0..a3` with created_at `2026-10-01..04`. It calls `search()` with the edge inputs shown. For the ordering check, a second DB holds `2026-10-9` and `2026-10-10`.

## What is correct

- With consistently formatted timestamps, the keyset predicate `(created_at < ? OR (created_at = ? AND id < ?))` matches `ORDER BY created_at DESC, id DESC`. Ties on created_at page correctly, which `test_pages_cover_all_rows_once` exercises.
- `escape_like` escapes the backslash first, then `%` and `_`, and the queries use `ESCAPE '\'`. Values are bound as parameters, so there is no SQL injection.

## Findings

1. **notes/search.py:37: `page_size=0` raises IndexError.** `LIMIT 0` returns no rows, so `len(rows) == page_size` is `0 == 0`, which is true, and the code then reads `rows[-1]`. Confirmed: `IndexError list index out of range`.
2. **notes/search.py:21 (`_decode`, line 10): a malformed or truncated page_token raises an unhandled exception.** Confirmed: `'abc'` raises `binascii.Error: Incorrect padding`. Crafted tokens such as base64 of `{}` or `[]` would raise KeyError or TypeError (by inspection). An API layer would probably return these as a 500 instead of a 400.
3. **notes/search.py:36: a next token is issued when the last page is exactly full.** Confirmed: with 4 rows and page_size=2, page 2 returns `[2, 1]` plus a token, and page 3 returns `([], None)`. That costs an extra round trip and leaves an empty last page. The usual fix is to fetch `page_size + 1` rows.
4. **notes/search.py:27/34: a negative `page_size` turns off the limit.** SQLite treats `LIMIT -1` as no limit. Confirmed: `page_size=-1` returned all 4 rows. If the value comes from the user, it gets around any page-size cap.
5. **notes/search.py:25: ordering and the cursor compare created_at as TEXT.** Confirmed: with `2026-10-9` and `2026-10-10`, "newest first" returns `['2026-10-9', '2026-10-10']`, which is the wrong order. Any timestamps that are not zero-padded, or that use mixed timezones or offsets, will misorder and can skip or repeat rows across pages. This is only a problem if the store accepts timestamps in more than one format. `add_note` takes a raw string.
6. **notes/search.py:21: the page token is not tied to the query.** By inspection: a token from `search('tax')` is silently accepted by `search('groc')` and starts mid-stream, so newer matches go missing with no error.
7. **notes/search.py:19: an empty term matches everything, and `None` crashes.** Confirmed: `term=''` returned all 4 rows, and `term=None` raised `AttributeError: 'NoneType' object has no attribute 'replace'`. Whether an empty term should match everything is a product decision. The crash on None is a bug if the caller can pass a missing query parameter.
8. **notes/store.py: no index on `(created_at, id)`.** Confirmed: `store.py` has only `CREATE TABLE` and no index. Every page does a full scan and sort, which removes most of the benefit of keyset pagination on large tables. (Performance.)
9. **tests/test_search.py:16: test coverage gaps.** The pagination test uses a single created_at value and 5 rows with page_size=2, which is not an exact multiple. Findings 1–5 and 7 all pass CI. (Tests.)
10. **notes/search.py:20–35: the two SQL strings are duplicated.** They differ only in the cursor predicate, so later edits could make them drift apart. Build one query and append the cursor clause conditionally. (Cleanup, not a bug.)

## Not covered

- The `a1551f2 eval setup` commit and the `.cadence/` and `outputs/` paths in the source repo are not in the bundle or the range, so they were not reviewed.
- `notes/store.py` (pre-existing, outside the range) was read only for the index check. Its schema, connection settings and `row_factory` were not reviewed.
- No calling or API layer exists in the repo, so how exceptions surface (500 vs 400), auth, and page-size caps could not be checked.
- Concurrency (inserts or deletes between page fetches), performance at scale (no benchmark ran), and behaviour on databases other than SQLite were not tested.
- Findings 2 (KeyError/TypeError variants), 6 and 10 are by inspection only.
- No CLAUDE.md or project conventions apply, so there was no conventions check.
