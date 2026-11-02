# Code review (round 2): main..feature/search-api

- Source: fresh clone of `/tmp/cr-run.PhW2XOzJ/repo/repo.bundle` into the new empty directory `/tmp/crclone.YWMVid/c`
- The bundle has no local `main` branch, only `origin/main`, so `main..feature/search-api` was resolved as `origin/main..feature/search-api` (6a70bbd..6746708: commits 87fe0d8, 6a9d4f0, 6746708).
- Diff: `notes/search.py` (+40, new), `tests/test_search.py` (+31, new). `notes/store.py` is unchanged and was read for context only.
- Environment: Python 3.13.18, pytest. No fixes were made.

## Test suite

```
$ cd /tmp/crclone.YWMVid/c && python3 -m pytest -q
...                                                                      [100%]
3 passed in 0.01s
```

## Repro harness

Every repro runs `python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c <case>`. The script lives outside the clone, and its full text is at the end of this file. The base fixture holds notes a1..a4 with created_at 2026-10-01..04 (ids 1..4).

## Findings

### 1. [High] page_size=0 crashes with IndexError: notes/search.py:37-38
`len(rows) == page_size` is true for an empty result (0 == 0), so `rows[-1]` is read from an empty list. Nothing checks that page_size >= 1.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c pz0
page_size=0 -> IndexError: list index out of range
```

### 2. [Medium] A negative page_size returns the whole result set: notes/search.py:17,37
In SQLite, `LIMIT -1` means no limit, so a negative page_size skips paging and returns every match. If page_size comes from a client, this bypasses the page cap.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c pzneg
page_size=-1 -> ([{'id': 4, 'title': 'a4', 'created_at': '2026-10-04'}, {'id': 3, 'title': 'a3', 'created_at': '2026-10-03'}, {'id': 2, 'title': 'a2', 'created_at': '2026-10-02'}, {'id': 1, 'title': 'a1', 'created_at': '2026-10-01'}], None)
```

### 3. [Medium] A malformed page_token raises an unhandled exception (likely a 500): notes/search.py:10,21,28
`_decode` and the `c["created_at"]` / `c["id"]` lookups have no error handling. Garbage input, a token whose `=` padding was stripped (common when tokens pass through URLs), and valid JSON with the wrong shape each raise a different exception type. None of them raises a clear "invalid token" error. (`Error` below is `binascii.Error`.)
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c badtok
token='abc' -> Error: Incorrect padding
token=stripped padding -> Error: Incorrect padding
token=b64('{}') -> KeyError: 'created_at'
token=b64('[]') -> TypeError: list indices must be integers or slices, not str
```

### 4. [Medium] Cursor values from the client are not type-checked, so forged tokens silently return wrong pages: notes/search.py:21-28
The token is unsigned client JSON, and its values go straight into the comparison. Because SQLite orders values across types, a string `id` makes `id < 'x'` true for every integer id, which re-includes rows from the cursor's date. An integer `created_at` makes `created_at < 0` false for all TEXT values, so the result is an empty page with no next token. Neither case raises an error.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c forged
cursor id='x' (str) -> ([{'id': 4, 'title': 'a4', 'created_at': '2026-10-04'}, {'id': 3, 'title': 'a3', 'created_at': '2026-10-03'}, {'id': 2, 'title': 'a2', 'created_at': '2026-10-02'}, {'id': 1, 'title': 'a1', 'created_at': '2026-10-01'}], None)
cursor created_at=0 (int) -> ([], None)
```
(The cursor in the first case had created_at=2026-10-04. A correct cursor would have excluded a4 or returned nothing.)

### 5. [Low] An empty extra page when the match count is an exact multiple of page_size: notes/search.py:37
A token is emitted whenever a page is full, so with 4 matches and page_size=2, page 2 returns a token and page 3 is an empty query. A client that shows a "next" link when a token is present will show one that leads to an empty page. Fetching `LIMIT page_size+1` would fix this.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c exact
p1 ([{'id': 4, 'title': 'a4', 'created_at': '2026-10-04'}, {'id': 3, 'title': 'a3', 'created_at': '2026-10-03'}], 'eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDMiLCAiaWQiOiAzfQ==')
p2 ([{'id': 2, 'title': 'a2', 'created_at': '2026-10-02'}, {'id': 1, 'title': 'a1', 'created_at': '2026-10-01'}], 'eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDEiLCAiaWQiOiAxfQ==')
p3 ([], None)
```

### 6. [Low] The page token is not tied to the search term: notes/search.py:21
A token from a search for term "a" is accepted for term "b" and silently skips the newer "b" matches. A fresh search for "b" returns two rows. The same search with the reused token returns none.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c crossterm
token from term a page1: eyJjcmVhdGVkX2F0IjogIjIwMjYtMTAtMDIiLCAiaWQiOiAzfQ==
reuse with term b -> []
term b fresh -> ['b newest', 'b new']
```

### 7. [Low] term=None crashes, and term='' matches every note: notes/search.py:14,19
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c term
term=None -> AttributeError: 'NoneType' object has no attribute 'replace'
term='' -> ['a4', 'a3', 'a2', 'a1']
```
Returning everything for '' may be intended. The crash on None is not.

### 8. [Low, partly pre-existing] Ordering and the cursor compare created_at as plain text: notes/search.py:25-26 (root cause: notes/store.py:21, which is not in the diff)
`add_note` accepts any string for created_at, and search orders and pages on lexical TEXT comparison. Dates that are not zero-padded, or ISO strings that mix the `T` and space separators, sort in the wrong order. "Newest first" is wrong in both cases below.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c dates
newest-first order -> [('n old', '2026-10-9'), ('n new', '2026-10-10')]
ISO T vs space -> [('n z', '2026-10-01T12:00:00Z'), ('n plain', '2026-10-01 13:00:00')]
```

### 9. [Low] Test coverage gaps: tests/test_search.py
There are no tests for page_size <= 0, malformed or forged tokens, an exact-multiple last page, or `_` and `\` escaping. Escaping currently works, as shown below, but no test would catch a regression. Findings 1-7 all pass the current suite (3 passed above).
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c escape
term='a_b' -> ['a_b']
term='c\\d' -> ['c\\d']
```

### 10. [Info, UNPROVEN as a defect] Notes inserted behind the cursor between page fetches are skipped
This is how keyset pagination normally behaves and is noted only so the behavior is known. A note inserted with a timestamp at or before the cursor's position but a higher id is never shown. In the run below, `n_late` (created_at 2026-10-02, the cursor's date, id 4) appears on neither page.
```
$ python3 -I /tmp/crscripts/r.py /tmp/crclone.YWMVid/c concurrent
p1 ['n2', 'n1']
p2 ['n0']
```

### 11. [Nit, UNPROVEN, no repro applicable] notes/search.py:20-35
The two SELECT statements are copies that differ only in the cursor predicate, so a later edit to one could be missed in the other. Building the WHERE clause and params once would avoid this.

## Things that checked out
- The keyset predicate `(created_at < ? OR (created_at = ? AND id < ?))` matches `ORDER BY created_at DESC, id DESC`. Rows with equal timestamps are paged without duplicates or gaps (test_pages_cover_all_rows_once passes).
- LIKE escaping for `%`, `_` and `\` works with `ESCAPE '\'` (test_percent_is_literal plus the escape repro above).
- All queries are parameterized, and the SQL is not built from user input.

## Verdict
**Not ready to merge.** The happy path works and the core keyset logic is correct. Two fixes are needed first. Finding 1 is a crash on a trivial input. Findings 2-4 mean anything sent by a client (page_size, page_token) can crash the call or return unbounded or wrong results, because nothing validates it. This needs input validation (page_size in [1, max], decoding the token with try/except into a clear "invalid token" error, and type checks on the cursor fields) plus tests for those cases. Findings 5-8 can be follow-ups.

## Not covered
- How search is exposed through HTTP or an API. No caller exists in the repo, so whether these exceptions become 500s is inferred, not observed.
- Performance and query plans on large tables. There is no index on (created_at, id), and `LIKE '%x%'` cannot use an index. This was not benchmarked.
- Concurrency or multi-connection behavior beyond the single-connection repro in finding 10, and SQLite builds or versions other than the one bundled with Python 3.13.18.
- Case-sensitivity and Unicode behavior of LIKE (SQLite's LIKE ignores case for ASCII only).
- Whether tokens need to be signed or encrypted, which depends on product security requirements.
- `notes/store.py` beyond its interaction with search (it is outside the diff).
- Note on process: the `/code-review` skill was invoked first, but its forked run reviewed the outer working directory instead of the clone. It reported `repo.bundle` and `.claude/skills/tpm` files that are not in the bundle's range. Those findings were discarded, and every finding above was re-derived and reproduced against the clone.

## Appendix: /tmp/crscripts/r.py
```python
import sys, traceback, base64, json
sys.path.insert(0, sys.argv[1])
from notes.store import connect, add_note
from notes.search import search, _encode
def run(label, f):
    try: print(label, "->", f())
    except Exception as e: print(label, "->", type(e).__name__ + ":", e)
db = connect()
for i,(t,d) in enumerate([("a1","2026-10-01"),("a2","2026-10-02"),("a3","2026-10-03"),("a4","2026-10-04")]): add_note(db,t,"",d)
which = sys.argv[2]
if which=="pz0": run("page_size=0", lambda: search(db,"a",page_size=0))
if which=="pzneg": run("page_size=-1", lambda: search(db,"a",page_size=-1))
if which=="badtok":
    run("token='abc'", lambda: search(db,"a",page_token="abc"))
    run("token=stripped padding", lambda: search(db,"a",page_token=_encode({"created_at":"2026-10-03","id":3}).rstrip("=")))
    run("token=b64('{}')", lambda: search(db,"a",page_token=base64.urlsafe_b64encode(b"{}").decode()))
    run("token=b64('[]')", lambda: search(db,"a",page_token=base64.urlsafe_b64encode(b"[]").decode()))
if which=="forged":
    run("cursor id='x' (str)", lambda: search(db,"a",page_token=_encode({"created_at":"2026-10-04","id":"x"})))
    run("cursor created_at=0 (int)", lambda: search(db,"a",page_token=_encode({"created_at":0,"id":99})))
if which=="exact":
    p1=search(db,"a",page_size=2); print("p1",p1)
    p2=search(db,"a",page_size=2,page_token=p1[1]); print("p2",p2)
    p3=search(db,"a",page_size=2,page_token=p2[1]); print("p3",p3)
if which=="term":
    run("term=None", lambda: search(db,None))
    run("term=''", lambda: [r["title"] for r in search(db,"")[0]])
if which=="escape":
    d=connect(); add_note(d,"a_b","","2026-10-01"); add_note(d,"axb","","2026-10-02"); add_note(d,"c\\d","","2026-10-03"); add_note(d,"cd","","2026-10-04")
    run("term='a_b'", lambda: [r["title"] for r in search(d,"a_b")[0]])
    run("term='c\\\\d'", lambda: [r["title"] for r in search(d,"c\\d")[0]])
if which=="dates":
    d=connect(); add_note(d,"n old","","2026-10-9"); add_note(d,"n new","","2026-10-10")
    run("newest-first order", lambda: [(r["title"],r["created_at"]) for r in search(d,"n")[0]])
    d=connect(); add_note(d,"n z","","2026-10-01T12:00:00Z"); add_note(d,"n plain","","2026-10-01 13:00:00")
    run("ISO T vs space", lambda: [(r["title"],r["created_at"]) for r in search(d,"n")[0]])
if which=="crossterm":
    d=connect(); add_note(d,"b new","","2026-10-05"); add_note(d,"a1","","2026-10-01"); add_note(d,"a2","","2026-10-02"); add_note(d,"b newest","","2026-10-06")
    t=search(d,"a",page_size=1)[1]; print("token from term a page1:", t)
    run("reuse with term b", lambda: [r["title"] for r in search(d,"b",page_token=t)[0]])
    run("term b fresh", lambda: [r["title"] for r in search(d,"b")[0]])
if which=="concurrent":
    d=connect(); 
    for i in range(3): add_note(d,f"n{i}","","2026-10-0%d"%(i+1))
    r1,t=search(d,"n",page_size=2); print("p1",[x["title"] for x in r1])
    add_note(d,"n_late","","2026-10-02")  # inserted with same date as cursor, higher id
    r2,_=search(d,"n",page_size=2,page_token=t); print("p2",[x["title"] for x in r2])
```
