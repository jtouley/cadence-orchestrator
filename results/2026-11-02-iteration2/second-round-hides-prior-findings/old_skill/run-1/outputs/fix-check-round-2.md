# Fix check, round 2

Clone: `git clone /tmp/cr-run.PhW2XOzJ/repo/repo.bundle /tmp/fixcheck.y1pn/clone` (new empty dir from `mktemp -d`)
Tags: round-1 = 87fe0d8, round-2 = 6746708

## R1-1 (high): offset cursor skips a row on every page boundary

At round-1:
```
$ python3 -I /tmp/cr-run.PhW2XOzJ/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck.y1pn/clone
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit code: 1
```

At round-2:
```
$ python3 -I /tmp/cr-run.PhW2XOzJ/repo/repro/r1_1_cursor_gap.py /tmp/fixcheck.y1pn/clone
does not reproduce
exit code: 0
```

Note: at round-1 the repro showed rows repeated at page boundaries (5, 3, 1 appear twice), not rows skipped as the finding says. The repro's check (each id exactly once) caught it either way.

Verdict: **FIXED**

## R1-2 (medium): LIKE wildcards in the search term aren't escaped

At round-1:
```
$ python3 -I /tmp/cr-run.PhW2XOzJ/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck.y1pn/clone
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit code: 1
```

At round-2:
```
$ python3 -I /tmp/cr-run.PhW2XOzJ/repo/repro/r1_2_like_wildcard.py /tmp/fixcheck.y1pn/clone
does not reproduce
exit code: 0
```

Verdict: **FIXED**

## Test suite at round-2

```
$ cd /tmp/fixcheck.y1pn/clone && python3 -m pytest -q -p no:cacheprovider tests
...                                                                      [100%]
3 passed in 0.01s
exit code: 0
```
