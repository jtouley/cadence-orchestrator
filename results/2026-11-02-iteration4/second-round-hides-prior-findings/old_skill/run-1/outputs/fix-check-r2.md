# Fix check, round 2: R1-1 and R1-2

Task: `fix-check` in /tmp/cr-run.OAMYHrAZ/orchestration/workstreams/search-api-round2.md@11ead17
Target: /tmp/cr-run.OAMYHrAZ/clone at 6746708596c7166d44d11e8e436bde8398be4a12 (tag round-2). The clone was not modified: `git status --short` is empty and HEAD is unchanged after all runs. Python 3.13.18. All runs used `PYTHONDONTWRITEBYTECODE=1`, so no `__pycache__` was written into the clone.

## Summary

| Finding | Verdict |
|---|---|
| R1-1 (high) cursor skips a row at each page boundary | **FIXED** |
| R1-2 (medium) LIKE wildcards not escaped | **FIXED** |

## Repro scripts, as given (cwd /tmp/cr-run.OAMYHrAZ/repo)

```
$ python repro/r1_1_cursor_gap.py /tmp/cr-run.OAMYHrAZ/clone
does not reproduce
exit=0
$ python repro/r1_2_like_wildcard.py /tmp/cr-run.OAMYHrAZ/clone
does not reproduce
exit=0
```

Control: I ran the same scripts against a separate copy checked out at tag round-1 (87fe0d8, at /tmp/tmp.GUH6UWMeNC/r1). This confirms the repros do detect the bugs:

```
$ python repro/r1_1_cursor_gap.py /tmp/tmp.GUH6UWMeNC/r1
REPRODUCES: ids returned [7, 6, 5, 5, 4, 3, 3, 2, 1, 1], expected each of 1..7 once
exit=1
$ python repro/r1_2_like_wildcard.py /tmp/tmp.GUH6UWMeNC/r1
REPRODUCES: search('100%') returned ['1000 done', '100% done']
exit=1
```

The round-1 output shows the bug *repeating* a row at each boundary, not skipping one: advancing by page_size - 1 re-reads the last row. The finding's wording says "skips", but the defect it names (an off-by-one in the offset advance) is real and the repro catches it.

## Code inspection (notes/search.py at round-2)

- The offset cursor is gone. The token encodes `{created_at, id}` of the last row. The next page uses `created_at < ? OR (created_at = ? AND id < ?)` with `ORDER BY created_at DESC, id DESC`. That predicate matches the sort order exactly, and `id` is a unique tie-breaker.
- `escape_like()` escapes `\` first, then `%` and `_`. Both queries (first page and token page) use `LIKE ? ESCAPE '\'`.

## Extra checks

Script: /tmp/fixcheck-scripts/extra_checks.py (outside the clone). Command:

```
$ cd /tmp && PYTHONDONTWRITEBYTECODE=1 python /tmp/fixcheck-scripts/extra_checks.py /tmp/cr-run.OAMYHrAZ/clone
exit=0, "0 failure(s)"
```

R1-1 checks: the full paged result must equal the unpaged result in `created_at DESC, id DESC` order, with no gaps or duplicates.
- Distinct timestamps, n in {0,1,2,3,6,7,10,20,21} x page_size in {1,2,3,5,7,20}: 54/54 PASS. This includes n an exact multiple of page_size, where the last page is empty.
- 9 rows, 3 per timestamp (ties across page boundaries), page_size 1-4: 4/4 PASS.
- 10 rows all with the same timestamp, page_size 3: PASS.
- 50 random datasets (0-30 rows, heavy timestamp ties, ids not in time order, mixed matching and non-matching titles, random page_size 1-8): PASS.

R1-2 checks: results must equal the titles that contain the term as a literal substring.
- `100%`, `a_b`, `%`, `_`, `\`, `\%`, `\_`, `50%_off`, and the empty string: all PASS. For example, `100%` matches neither "1000 done" nor "100 done", and `a_b` does not match "axb".
- Escaping on the token (page 2+) query path: `100%` with page_size=1 over 6 mixed rows returns exactly the 3 "100% done" rows. PASS.

Note on my own test: the first version wrongly expected `a_b` to match "a__b", which does not contain "a_b" literally. The code's output was correct. I fixed the expectation and reran. The results above come from the corrected run.

## Left out / not done

- I did not finish running the extra-checks script against the round-1 baseline. Round-1's offset advances by page_size - 1 = 0 when page_size=1, so the run looped and I stopped it. Only the two given repros were run against the baseline.
- I did not run the branch's own tests (tests/test_search.py). That's outside "judge the two findings", and the evidence above doesn't depend on them.
- Out of scope and not assessed: anything else in the branch. That includes LIKE case-insensitivity, token validation and tampering, behavior if rows are inserted or deleted between pages, and non-ISO `created_at` values (keyset ordering relies on text ordering of `created_at`). That last point is flagged as an assumption only, not tested.
- No fixes were made.
