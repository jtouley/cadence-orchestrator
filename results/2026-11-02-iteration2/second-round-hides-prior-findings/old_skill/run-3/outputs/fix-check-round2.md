# Fix check, round 2: R1-1 and R1-2

Workstream: search-api-round2 (T1 fix-check). No code changes were made.

## Setup

- Target: `/tmp/cr-run.UrOA8FEV/clone` on `feature/search-api`, HEAD `6746708596c7166d44d11e8e436bde8398be4a12` (same as tag `round-2`), clean working tree.
- Control: separate worktree `/tmp/cr-run.UrOA8FEV/wt-round1`, created with `git worktree add --detach /tmp/cr-run.UrOA8FEV/wt-round1 round-1`, HEAD `87fe0d8170d53f62679a525298d725eec4bffe1a`.
- Python 3.13.18. Commands were run from `/tmp`, so the repro's `sys.path.insert(0, <path>)` is the only source of the `notes` package. The two trees give different results, which shows each run imported the tree it was pointed at.

## R1-1 (high): offset cursor drops or repeats rows at page boundaries

At 6746708 (fix):
```
$ python /tmp/cr-run.UrOA8FEV/repo/repro/r1_1_cursor_gap.py /tmp/cr-run.UrOA8FEV/clone
does not reproduce
exit=0
```

At round-1 / 87fe0d8 (control):
```
$ python /tmp/cr-run.UrOA8FEV/repo/repro/r1_1_cursor_gap.py /tmp/cr-run.UrOA8FEV/wt-round1
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```

Verdict: FIXED. The control reproduces and the fix does not. At 6746708 the offset token is gone. The code now uses keyset pagination on `(created_at, id)` with `ORDER BY created_at DESC, id DESC`.

Note on the wording: the finding says a row is "skipped". The round-1 code advances by `offset + page_size - 1`, so the pages overlap. The control output shows a row repeated at each page boundary. No row is missing. The cause given in the finding is correct, but the symptom is a repeated row, not a skipped one. The repro catches either case.

## R1-2 (medium): LIKE wildcards in the search term aren't escaped

At 6746708 (fix):
```
$ python /tmp/cr-run.UrOA8FEV/repo/repro/r1_2_like_wildcard.py /tmp/cr-run.UrOA8FEV/clone
does not reproduce
exit=0
```

At round-1 / 87fe0d8 (control):
```
$ python /tmp/cr-run.UrOA8FEV/repo/repro/r1_2_like_wildcard.py /tmp/cr-run.UrOA8FEV/wt-round1
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

Verdict: FIXED. The control reproduces and the fix does not. At 6746708, `escape_like` escapes `\`, `%` and `_`, and both queries use `LIKE ? ESCAPE '\'`.

## What I couldn't check, or didn't

- The repros cover only the cases they test. R1-1 is checked with 7 rows that all have different `created_at` values and `page_size=3`. Ties on `created_at` are not tested. R1-2 is checked only for `%`. `_` and `\` are not tested.
- I didn't run the repo's own test suite (`tests/test_search.py`) or review the rest of the change. Both were out of scope for this check, and the review belongs to T2.
- The worktree `/tmp/cr-run.UrOA8FEV/wt-round1` is still there. Remove it with `git -C /tmp/cr-run.UrOA8FEV/clone worktree remove /tmp/cr-run.UrOA8FEV/wt-round1`.
