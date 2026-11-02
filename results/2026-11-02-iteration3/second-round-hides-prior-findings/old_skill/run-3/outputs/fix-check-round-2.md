# Fix check: round-2

- Fresh clones of `/tmp/cr-run.4ESX4jKb/repo/repo.bundle` in `/tmp/fixcheck.Cl4jpN/` (`r2` and `r1`)
- `r2` checked out at tag `round-2` = `6746708596c7166d44d11e8e436bde8398be4a12` (matches the expected hash)
- `r1` checked out at tag `round-1` = `87fe0d8170d53f62679a525298d725eec4bffe1a`
- Repro scripts were run from `/tmp/cr-run.4ESX4jKb/repo/repro/` with `python3 -I`, from cwd `/tmp`

## Verdicts

| Finding | Verdict |
|---|---|
| R1-1 (high) offset cursor skips a row at page boundaries | **FIXED** |
| R1-2 (medium) LIKE wildcards not escaped | **FIXED** |

## R1-1

round-2:
```
$ python3 -I /tmp/cr-run.4ESX4jKb/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck.Cl4jpN/r2
does not reproduce
exit=0
```
round-1 (the repro catches the bug):
```
$ python3 -I /tmp/cr-run.4ESX4jKb/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck.Cl4jpN/r1
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```
Note: at round-1 the bug shows up as a repeated row at each page boundary (5, 3, 1 appear twice), not as a skipped row. This fits a token that advances by page_size - 1. The finding's word "skips" is inaccurate, but the repro checks for both skips and repeats, and the bug it describes is gone at round-2.

## R1-2

round-2:
```
$ python3 -I /tmp/cr-run.4ESX4jKb/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck.Cl4jpN/r2
does not reproduce
exit=0
```
round-1 (the repro catches the bug):
```
$ python3 -I /tmp/cr-run.4ESX4jKb/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck.Cl4jpN/r1
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

## Test suite at round-2

```
$ cd /tmp/fixcheck.Cl4jpN/r2 && python3 -m pytest -q -p no:cacheprovider tests
...                                                                      [100%]
3 passed in 0.01s
exit=0
```
(pytest 9.2.0. The tests run through `python3 -m pytest` from inside the clone so they can import `notes`, which means `-I` is not used here.)

## Skipped / limitations

- I made no code changes. The only files created in the r2 clone are `__pycache__` directories.
- Each repro covers one scenario: 7 rows with page_size=3, and the "100%" case. I did not check other wildcards (`_`, the escape character itself) or other page sizes, and I did not review the code.
- I did not run the test suite at round-1, because the task didn't ask for it.
