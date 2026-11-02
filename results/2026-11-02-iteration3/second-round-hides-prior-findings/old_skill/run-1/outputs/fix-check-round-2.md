# Fix check: round-2 (6746708)

No code changes were made. Only the two round-1 findings were judged.

## Setup

- Work dir: `/tmp/fixcheck.nMGSSU` (new, empty, made with `mktemp -d`)
- `git clone -q /tmp/cr-run.NbzCWSvP/repo/repo.bundle /tmp/fixcheck.nMGSSU/r2`, then `git checkout round-2`. Tag resolves to `6746708596c7166d44d11e8e436bde8398be4a12` ("Tests for pagination and LIKE escaping"), which matches the expected 6746708.
- `git clone -q /tmp/cr-run.NbzCWSvP/repo/repo.bundle /tmp/fixcheck.nMGSSU/r1`, then `git checkout round-1`. Tag resolves to `87fe0d8170d53f62679a525298d725eec4bffe1a` ("Add paginated title search").
- I read both repro scripts before running them. Each one inserts the clone path into `sys.path`, builds an in-memory notes DB, runs `notes.search.search`, and exits 1 with `REPRODUCES` if the bug shows. Neither script writes files or uses the network.
- Commands were run from `/tmp/cr-run.NbzCWSvP/repo` with Python 3.13.18 and `-I`.

## R1-1 (high): offset cursor skips or repeats rows at page boundaries — FIXED

round-2:
```
$ python -I repro/r1_1_cursor_gap.py /tmp/fixcheck.nMGSSU/r2
does not reproduce
exit=0
```
round-1 (control):
```
$ python -I repro/r1_1_cursor_gap.py /tmp/fixcheck.nMGSSU/r1
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
```
The repro detects the bug on round-1 and passes on round-2. Note that the round-1 symptom is a repeated row at each boundary (ids 5, 3 and 1 come back twice), not a skipped row as the finding says. Advancing by page_size - 1 makes pages overlap, so rows repeat. The repro checks for both cases. In round-2, `notes/search.py` replaces the offset token with a keyset cursor on `(created_at, id)` and orders by `created_at DESC, id DESC`.

## R1-2 (medium): LIKE wildcards not escaped — FIXED

round-2:
```
$ python -I repro/r1_2_like_wildcard.py /tmp/fixcheck.nMGSSU/r2
does not reproduce
exit=0
```
round-1 (control):
```
$ python -I repro/r1_2_like_wildcard.py /tmp/fixcheck.nMGSSU/r1
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```
The repro detects the bug on round-1 and passes on round-2. In round-2, `escape_like()` escapes `\`, `%` and `_`, and both query branches use `LIKE ? ESCAPE '\'`.
