# Fix-check, round 2

Target: clone `/tmp/cr-run.VICTq7he/clone`, branch `feature/search-api` = `6746708596c7166d44d11e8e436bde8398be4a12` (clean tree, verified with `git rev-parse HEAD` and `git status`). Python 3.13.18. No code was changed.

| Finding | Verdict |
|---|---|
| R1-1 (high) offset cursor skips/repeats a row at page boundaries | FIXED |
| R1-2 (medium) LIKE wildcards not escaped | FIXED |

## R1-1: FIXED

Repro at round-2 (run from `/tmp/cr-run.VICTq7he/repo`):

```
$ python -I repro/r1_1_cursor_gap.py /tmp/cr-run.VICTq7he/clone; echo "exit=$?"
does not reproduce
exit=0
```

Control: the same repro against a `git archive` export of round-1 (`87fe0d8`) at `/tmp/cr-run.VICTq7he/round1-export`:

```
$ python -I repro/r1_1_cursor_gap.py /tmp/cr-run.VICTq7he/round1-export; echo "exit=$?"
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```

(Note: at round-1 the defect showed up as repeated rows, not skipped ones. Advancing by `page_size - 1` repeats the last row of each page. The finding's wording says "skips", but the repro checks for both.)

Why it's fixed: `notes/search.py` no longer uses an offset. It uses keyset pagination on `(created_at DESC, id DESC)` with the predicate `created_at < ? OR (created_at = ? AND id < ?)`, and the cursor is the last row's `(created_at, id)`.

Variants the repro misses: the repro uses only distinct timestamps and one page size. `/tmp/cr-run.VICTq7he/fixcheck-scripts/variants.py` covers ties on `created_at` (all equal, groups of 3, random), n = 0..12 matching rows plus one interleaved non-matching row, every page size from 1 to n+1 (including exact multiples), and compares the paged order with the full ordered query. Result: `R1-1 variants: 364 cases checked`, no failures (full output below).

## R1-2: FIXED

```
$ python -I repro/r1_2_like_wildcard.py /tmp/cr-run.VICTq7he/clone; echo "exit=$?"
does not reproduce
exit=0
```

Control against round-1:

```
$ python -I repro/r1_2_like_wildcard.py /tmp/cr-run.VICTq7he/round1-export; echo "exit=$?"
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

Why it's fixed: `escape_like()` escapes `\`, then `%`, then `_`. Both queries (the first page and the cursor page) use `LIKE ? ESCAPE '\'`. The Python literal `'\\'` becomes a single backslash in SQL.

Variants the repro misses: `_`, backslash, `\%`, `%%`, `__`, and mixed terms such as `50%_`, each compared with Python's `term in title` substring semantics. All matched (output below).

## Variant script output

```
$ cd /tmp && python -I /tmp/cr-run.VICTq7he/fixcheck-scripts/variants.py /tmp/cr-run.VICTq7he/clone; echo "exit=$?"
R1-1 variants: 364 cases checked
R1-2 term='100%': ok got=['100% done'] expected=['100% done']
R1-2 term='%': ok got=['100% done', '50%_off', '50%xoff', '\\%', 'x%'] expected=['100% done', '50%_off', '50%xoff', '\\%', 'x%']
R1-2 term='_': ok got=['50%_off', 'a_b'] expected=['50%_off', 'a_b']
R1-2 term='a_b': ok got=['a_b'] expected=['a_b']
R1-2 term='\\': ok got=['\\%', 'c\\\\d', 'c\\d'] expected=['\\%', 'c\\\\d', 'c\\d']
R1-2 term='c\\d': ok got=['c\\d'] expected=['c\\d']
R1-2 term='50%_': ok got=['50%_off'] expected=['50%_off']
R1-2 term='\\%': ok got=['\\%'] expected=['\\%']
R1-2 term='%%': ok got=[] expected=[]
R1-2 term='__': ok got=[] expected=[]
R1-2 term='x%': ok got=['x%'] expected=['x%']
FAILS: 0
exit=0
```

## Left out / caveats

- This was a fix-check only, not a review of the rest of the branch. These were not assessed: case-insensitivity of SQLite `LIKE` (a different behavior, not this defect); handling of malformed or tampered page tokens (`_decode` with bad input, or a token missing keys); the extra empty page when the result count is an exact multiple of `page_size` (the rows are still correct; this is a design point); consistency when rows are inserted or deleted between page requests; non-ISO or mixed-format `created_at` strings (ordering is lexicographic on TEXT); performance and indexes.
- I did not run the repo's own `tests/test_search.py` (pytest). It was out of scope for the repro check.
- Running the repros wrote `notes/__pycache__/` into the clone. I deleted it afterwards, and the clone tree is clean again.
