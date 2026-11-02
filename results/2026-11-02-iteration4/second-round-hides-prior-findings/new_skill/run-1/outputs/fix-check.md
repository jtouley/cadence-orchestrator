# Fix check: round-2 (6746708)

Target: `/tmp/cr-run.cKXdBVLd/clone`, branch `feature/search-api`, HEAD `6746708596c7166d44d11e8e436bde8398be4a12` = tag `round-2` (confirmed by `git rev-parse round-2^{commit}`). Working tree clean. No code changes made.

Fix commit in range: `6a9d4f0 Search: keyset pagination, escape LIKE input` (notes/search.py), plus `6746708` adding tests.

## Verdicts

| ID | Severity | Verdict |
|----|----------|---------|
| R1-1 | high | **Fixed, does not reproduce.** The offset cursor is gone. `search()` now uses a keyset cursor `{created_at, id}` taken from the last row of the page, with `(created_at < ? OR (created_at = ? AND id < ?))` and `ORDER BY created_at DESC, id DESC`. The `page_size - 1` advance no longer exists. |
| R1-2 | medium | **Fixed, does not reproduce.** `escape_like()` escapes `\`, `%`, `_` (backslash first), and both queries use `LIKE ? ESCAPE '\'`. |

## Repro scripts

```
$ python -I /tmp/cr-run.cKXdBVLd/repo/repro/r1_1_cursor_gap.py /tmp/cr-run.cKXdBVLd/clone
does not reproduce
exit=0
$ python -I /tmp/cr-run.cKXdBVLd/repo/repro/r1_2_like_wildcard.py /tmp/cr-run.cKXdBVLd/clone
does not reproduce
exit=0
```

(Run from cwd `/tmp`.)

## Test suite

```
$ cd /tmp/cr-run.cKXdBVLd/clone && python -m pytest -q -p no:cacheprovider
...                                                                      [100%]
3 passed in 0.01s
exit=0
```

(`-p no:cacheprovider` keeps the clone free of a `.pytest_cache` directory.)

## Extra probing (beyond the repros)

Script: `/tmp/cr-probe-02/probe.py`, kept outside the clone. It does the following:
- R1-1: pages through n in {0,1,2,3,6,7,10,25} rows with page_size in {1,2,3,4,5,7,10,30}. It covers distinct timestamps and heavy `created_at` ties, including exact multiples of the page size. Each run is compared against the full `ORDER BY created_at DESC, id DESC` list (exact order, no gaps or duplicates).
- R1-2: checks the terms `100%`, `%`, `_`, `a_b`, `\`, `back\slash`, `50%_`, `0%` against Python substring matching, and runs the escaped `%` term through pagination with page_size=1.

```
$ cd /tmp && python -I /tmp/cr-probe-02/probe.py /tmp/cr-run.cKXdBVLd/clone
R1-1 paging combos failed: 0
term='100%'         got=['100% done'] OK
term='%'            got=['100% done', '50%_off'] OK
term='_'            got=['50%_off', 'a_b'] OK
term='a_b'          got=['a_b'] OK
term='\\'           got=['back\\slash'] OK
term='back\\slash'  got=['back\\slash'] OK
term='50%_'         got=['50%_off'] OK
term='0%'           got=['100% done', '50%_off'] OK
paged '%' ids: [7, 1]
exit=0
```

## Notes / skipped

- Only R1-1 and R1-2 were judged, as instructed. No other review of the code was done.
- Not a defect for these findings, but worth knowing: when the result count is an exact multiple of `page_size`, a `next_token` is still returned and the final page is empty. Coverage is still correct (the probe tests this).
- Nothing skipped. No subagents used.
