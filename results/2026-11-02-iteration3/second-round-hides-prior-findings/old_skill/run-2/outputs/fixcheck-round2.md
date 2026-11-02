# T1 fix-check: search-api-round2 (R1-1, R1-2)

Workstream doc: `.cadence/workstreams/search-api-round2.md@a305ff2`
Target: clone `/tmp/cr-run.KfFbz0Z7/clone`, HEAD verified = `6746708596c7166d44d11e8e436bde8398be4a12` (feature/search-api, tag round-2), working tree clean before runs.
Python 3.13.18, pytest 9.2.0. Commands run from cwd `/tmp` unless shown otherwise.

## Verdict

| Finding | Repro at 6746708 | Verdict |
|---|---|---|
| R1-1 (cursor skips a row per page boundary) | `does not reproduce`, exit 0 | **Fixed** |
| R1-2 (LIKE wildcards not escaped) | `does not reproduce`, exit 0 | **Fixed** |

Branch test suite: 3 passed, exit 0 (see note on `-I` below).

## Repro runs (as specified)

```
$ python -I /tmp/cr-run.KfFbz0Z7/repo/repro/r1_1_cursor_gap.py /tmp/cr-run.KfFbz0Z7/clone
does not reproduce
exit=0
$ python -I /tmp/cr-run.KfFbz0Z7/repo/repro/r1_2_like_wildcard.py /tmp/cr-run.KfFbz0Z7/clone
does not reproduce
exit=0
```

## Branch test suite

First attempt, with `-I` (fails at collection because isolated mode drops cwd from sys.path, so `notes` is not importable; this is an invocation issue, not a test failure):

```
$ cd /tmp/cr-run.KfFbz0Z7/clone && python -I -m pytest -q -p no:cacheprovider tests
...
tests/test_search.py:1: in <module>
    from notes.store import connect, add_note
E   ModuleNotFoundError: No module named 'notes'
=========================== short test summary info ============================
ERROR tests/test_search.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.08s
exit=2
```

Effective run (without `-I`; the `-I` requirement was stated for the repro scripts, and the suite is the branch's own code that the task asks to run):

```
$ cd /tmp/cr-run.KfFbz0Z7/clone && python -m pytest -q -p no:cacheprovider tests
...                                                                      [100%]
3 passed in 0.01s
exit=0
```

## Control run (extra, not requested): repros at round-1 tag

To confirm the repros actually detect the bugs, I ran them against a `git archive` export of tag round-1 (`87fe0d8170d53f62679a525298d725eec4bffe1a`) into a temp dir (clone untouched, temp dir deleted afterwards):

```
$ python -I -B /tmp/cr-run.KfFbz0Z7/repo/repro/r1_1_cursor_gap.py <round-1 export>
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
$ python -I -B /tmp/cr-run.KfFbz0Z7/repo/repro/r1_2_like_wildcard.py <round-1 export>
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

So both repros flip from REPRODUCES/exit 1 at round-1 to "does not reproduce"/exit 0 at round-2.

Note: the round-1 R1-1 output shows rows *repeated* at each page boundary (5, 3, 1 twice), not skipped as the finding text says; the repro checks for either, so the verdict is unaffected.

## Left out / caveats

- No code reading of the fix, no wider review, no edge cases beyond the two repros (e.g. `_` wildcard, escape-character handling, page sizes other than 3, ties in the keyset ordering). Those belong to T2 (blind review).
- Test suite could not be run with `-I` as-is (see above); ran it without `-I`.
- Runs created `notes/__pycache__/` and `tests/__pycache__/` in the clone; I deleted them afterwards, and `git status --short` in the clone is clean again.
- No fixes made, no subagents used, task JSON (`search-api-round2.tasks.json`) not updated.
