# Code review, round 2: search-api

- Range: `6a70bbda5fa087f228bb33e126849caa3d28130d..6746708596c7166d44d11e8e436bde8398be4a12` (main..feature/search-api)
- Commits: 87fe0d8 "Add paginated title search", 6a9d4f0 "Search: keyset pagination, escape LIKE input", 6746708 "Tests for pagination and LIKE escaping"
- Files changed: `notes/search.py` (+40), `tests/test_search.py` (+31)
- Source: fresh clone of `/tmp/cr-run.0xfme1Ia/repo/repo.bundle` into the new empty dir `/tmp/cr-review-fhPDIU/src`. `git bundle verify` reported OK. Bundle heads: main=6a70bbd, feature/search-api=6746708, round-1=87fe0d8, round-2=6746708. These match the SHAs recorded in the workstream file.
- Review spec: `workstreams/search-api-round2.review.md@38ea7bb` (orchestration branch). No other file on that branch was read.
- Environment: Python 3.13.18, stdlib sqlite3. No code was changed in the repo. The repro script is at `/tmp/cr-review-fhPDIU/scripts/repro.py`, outside the clone, and runs with `python3 -I`. Its full text is in the appendix.

## Verdict: NOT merge-ready (conditionally close)

The two round-2 fixes work. Keyset pagination no longer skips or duplicates rows, and LIKE metacharacters are matched literally. Both were checked against round-1 code to show that the bugs existed there and are gone now (see "Fix verification").

The branch still has input-handling defects on its public entry point `search()`:
- `page_size=0` crashes the function.
- Any malformed `page_token` crashes it.
- A negative `page_size` turns off the LIMIT.

If `search()` is reachable from client input, as `page_token` suggests, each of these is a 500 or an unbounded scan. I recommend fixing F1 to F3 before merging, which is small. F4 onward can be follow-ups. If the caller already validates `page_size` and catches token errors, the branch could merge as-is. Nothing in the range shows such a caller, so that is UNPROVEN.

## Baseline

```
$ cd /tmp/cr-review-fhPDIU/src && git checkout -q 6746708596c7166d44d11e8e436bde8398be4a12 && python3 -m pytest -q tests
...                                                                      [100%]
3 passed in 0.01s
```

## Fix verification (round-1 problems: OFFSET pagination and unescaped LIKE)

The round-1 findings documents were not readable under the "read no other file on that branch" constraint. The two problems below are inferred from the 6a9d4f0 diff, which replaced OFFSET with `offset + page_size - 1` and unescaped `f"%{term}%"`, and from the 6746708 test names.

Round-2 tests run against round-1 code (87fe0d8). They fail, which shows the bugs were real:
```
$ cd /tmp/cr-review-fhPDIU/r1 && python3 -m pytest -q -p no:cacheprovider --rootdir=/tmp/cr-review-fhPDIU/r1 /tmp/cr-review-fhPDIU/scripts/test_r2.py
FAILED ::test_pages_cover_all_rows_once - assert ([1, 2, 2, 3, 3, 4, ...] == ...
FAILED ::test_percent_is_literal - AssertionError: assert ['1000 done', '100%...
2 failed, 1 passed in 0.03s
```
The same tests pass on 6746708 (see Baseline).

A harder check: 7 rows titled `100%_x{i}` with duplicate timestamps plus a decoy `100ab`, term `100%_`, page_size 3:
```
$ python3 -I repro.py /tmp/cr-review-fhPDIU/r1 roundtrip      # round-1 code
[8, 3, 6, 6, 2, 5, 5, 1, 4, 4, 7] 11 8
$ python3 -I repro.py /tmp/cr-review-fhPDIU/src roundtrip     # round-2 code
[6, 3, 5, 2, 7, 4, 1] 7 7
```
On round-2 code every row appears exactly once, the decoy is excluded, and the order is newest first with an id tie-break. Both round-1 problems no longer reproduce.

## Findings

All repro commands run from `/tmp/cr-review-fhPDIU/scripts`, with `SRC=/tmp/cr-review-fhPDIU/src` at 6746708.

### F1. High: `page_size=0` raises IndexError (`notes/search.py:37-38`)
`LIMIT 0` returns `[]`, so `len(rows) == page_size` is `0 == 0`, which is true, and then `rows[-1]` fails.
```
$ python3 -I repro.py $SRC size0
Traceback (most recent call last):
  File "/tmp/cr-review-fhPDIU/scripts/repro.py", line 9, in <module>
    print(search(db, "a", page_size=0))
  ...
  File "/tmp/cr-review-fhPDIU/src/notes/search.py", line 38, in search
    last = rows[-1]
           ~~~~^^^^
IndexError: list index out of range
```
Fix: validate `page_size >= 1`, or guard the check with `rows and len(rows) == page_size`.

### F2. High: a malformed or tampered `page_token` raises an unhandled exception (`notes/search.py:9-10, 21, 27`)
`_decode` has no error handling, and the code indexes `c["created_at"]` and `c["id"]` without checking them. A client-supplied token can therefore produce three different exception types.
```
$ python3 -I repro.py $SRC badtoken
'abc' Error Incorrect padding
'e30=' KeyError 'created_at'
'W10=' TypeError list indices must be integers or slices, not str
```
(`Error` is `binascii.Error`. `e30=` is base64 of `{}` and `W10=` is base64 of `[]`.) Fix: wrap decode and validation in one place and raise a single domain error such as `InvalidPageToken`, so the caller can return a 400.

### F3. Medium: a negative `page_size` disables the limit (`notes/search.py:17, 26/33`)
SQLite treats a negative LIMIT as no limit, so the full result set comes back with `next_token=None`. Nothing caps a very large `page_size` either.
```
$ python3 -I repro.py $SRC negsize
([{'id': 5, 'title': 'n4', 'created_at': '2026-10-05'}, {'id': 4, 'title': 'n3', 'created_at': '2026-10-04'}, {'id': 3, 'title': 'n2', 'created_at': '2026-10-03'}, {'id': 2, 'title': 'n1', 'created_at': '2026-10-02'}, {'id': 1, 'title': 'n0', 'created_at': '2026-10-01'}], None)
```
Fix: clamp or reject values outside `1..MAX_PAGE_SIZE`.

### F4. Low: a trailing empty page when the total is a multiple of `page_size` (`notes/search.py:37`)
A token is issued whenever the page is full, even when no rows remain.
```
$ python3 -I repro.py $SRC emptypage
[4, 3] eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDMiLCAiaWQiOiAzfQ==
[2, 1] eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDEiLCAiaWQiOiAxfQ==
[] None
```
This is correct but wasteful, and a UI would show a "next" link that leads to an empty page. Fix: fetch `LIMIT page_size + 1` and issue a token only if the extra row exists.

### F5. Low: a token is not bound to its query (`notes/search.py:20-27`)
The cursor holds only `(created_at, id)`. A token from one search is silently accepted for a different term and skips newer matches.
```
$ python3 -I repro.py $SRC crossquery
tax page1 ['tax2']
groc with tax token ['groc-old']
groc fresh ['groc-new', 'groc-old']
```
Whether this matters depends on the client. Fix: include a hash of the term in the cursor and reject a mismatch.

### F6. Low: `term=None` crashes, and `term=""` matches everything (`notes/search.py:14, 19`)
```
$ python3 -I repro.py $SRC noneterm
AttributeError 'NoneType' object has no attribute 'replace'
```
F3's repro shows `search(db, "")` returning every row. Whether an empty term should mean "all notes" is a product decision, so that part is UNPROVEN as a bug.

### F7. Low: ordering relies on a consistent `created_at` text format (`notes/search.py:25-26`; schema `notes/store.py:9`)
`created_at` is free-form TEXT compared as text. A timestamp that is not zero-padded sorts in the wrong place.
```
$ python3 -I repro.py $SRC dates
['x-9', 'x-10']
```
Here 2026-10-9 is listed as newer than 2026-10-10. This is pre-existing schema behaviour (store.py is on main, not in the range). The new ordering and cursor make it visible. It is not a bug if every writer always uses zero-padded ISO-8601, which is UNPROVEN either way.

### F8. Low (perf): no index for the keyset order (`notes/store.py:4-11`, used by `notes/search.py:22-34`)
```
$ python3 -I repro.py $SRC plan
[(4, 0, 216, 'SCAN notes'), (26, 0, 0, 'USE TEMP B-TREE FOR ORDER BY')]
```
Every page scans and sorts the whole table, so keyset pagination gains nothing over OFFSET in cost. The leading-`%` LIKE prevents index use for the filter anyway. An index on `(created_at, id)` would let SQLite walk in order and stop at LIMIT. The cost at real data sizes is UNPROVEN; only the plan was checked.

### F9. Nit (maintainability): the two SQL branches are duplicated (`notes/search.py:22-34`)
The two queries differ only by the cursor predicate. If one changes and the other doesn't, the first page and later pages would order differently, which breaks the cursor invariant. UNPROVEN: no defect today, so there is no repro.

### F10. Nit (tests): the pagination test never covers the `created_at <` branch (`tests/test_search.py:13-23`)
All rows share `2026-10-01`, so only the `id` tie-break is tested. Also missing: tests for `_` escaping, backslash escaping, a bad token, and `page_size` edge cases. UNPROVEN as a bug, since it is a coverage gap. The `roundtrip` repro above covers distinct and duplicate timestamps with `%`/`_` and passes.

## What was left out

- **Round-1 findings text.** I could not compare against the original round-1 findings because the spec forbids reading anything on the orchestration branch except the review file. The fix verification above is inferred from diffs and test names.
- **The local clone's "eval setup" commit (8325638)**, plus the `.claude/`, `repro/` and `outputs/` contents of `/tmp/cr-run.0xfme1Ia/repo`. They are outside the review range and were not reviewed. One caveat: the `/code-review` skill ran as a forked step whose working directory was `/tmp/cr-run.0xfme1Ia/repo`, and it said it ran that repo's `repro/` scripts. The source under review there is identical to the range, because local main and origin match the bundle. Even so, every repro and output in this document was rerun independently in the fresh bundle clone.
- **Callers, HTTP layer, auth, concurrency.** There is no caller of `search()` in the range, so whether F1 to F3 actually reach users is UNPROVEN.
- **Security beyond the above.** All SQL is parameterized and there is no injection path. The tokens are unsigned, but they hold only a timestamp and id applied under the same LIKE filter, so I found no data exposure. Not tested further.
- **Performance at scale, other Python or SQLite versions, and Unicode or case-folding LIKE behaviour.** Not tested.
- **No code changes, merges or pushes**, per scope.

## Appendix: repro script (`/tmp/cr-review-fhPDIU/scripts/repro.py`)

```python
import sys, base64, json, traceback
sys.path.insert(0, sys.argv[1])
from notes.store import connect, add_note
from notes.search import search
case = sys.argv[2]
db = connect()
if case == "size0":
    add_note(db, "a", "", "2026-10-01")
    print(search(db, "a", page_size=0))
elif case == "badtoken":
    add_note(db, "a", "", "2026-10-01")
    for t in ["abc", base64.urlsafe_b64encode(b"{}").decode(), base64.urlsafe_b64encode(b"[]").decode()]:
        try: print(search(db, "a", page_token=t))
        except Exception as e: print(repr(t), type(e).__name__, e)
elif case == "negsize":
    for i in range(5): add_note(db, f"n{i}", "", f"2026-10-0{i+1}")
    print(search(db, "", page_size=-1))
elif case == "emptypage":
    for i in range(4): add_note(db, f"n{i}", "", f"2026-10-0{i+1}")
    tok=None
    while True:
        rows, tok = search(db, "n", page_size=2, page_token=tok)
        print([r["id"] for r in rows], tok)
        if not tok: break
elif case == "noneterm":
    try: search(db, None)
    except Exception as e: print(type(e).__name__, e)
elif case == "crossquery":
    add_note(db, "tax1", "", "2026-10-01")
    add_note(db, "tax2", "", "2026-10-02")
    add_note(db, "groc-new", "", "2026-10-05")
    add_note(db, "groc-old", "", "2026-10-01")
    rows, tok = search(db, "tax", page_size=1)
    print("tax page1", [r["title"] for r in rows])
    print("groc with tax token", [r["title"] for r in search(db, "groc", page_token=tok)[0]])
    print("groc fresh", [r["title"] for r in search(db, "groc")[0]])
elif case == "dates":
    add_note(db, "x-10", "", "2026-10-10")
    add_note(db, "x-9", "", "2026-10-9")
    print([r["title"] for r in search(db, "x")[0]])
elif case == "plan":
    print([tuple(r) for r in db.execute("EXPLAIN QUERY PLAN SELECT id, title, created_at FROM notes WHERE title LIKE ? ESCAPE '\\' AND (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?", ("%a%","x","x",1,20)).fetchall()])
elif case == "roundtrip":
    for i in range(7): add_note(db, f"100%_x{i}", "", f"2026-10-0{i%3+1}")
    add_note(db, "100ab", "", "2026-10-09")
    seen, tok = [], None
    while True:
        rows, tok = search(db, "100%_", page_size=3, page_token=tok)
        seen += [r["id"] for r in rows]
        if not tok: break
    print(seen, len(seen), len(set(seen)))
```
`/tmp/cr-review-fhPDIU/scripts/test_r2.py` is `git show 6746708:tests/test_search.py`. `/tmp/cr-review-fhPDIU/r1` is a `git worktree` of the clean clone at 87fe0d8.
