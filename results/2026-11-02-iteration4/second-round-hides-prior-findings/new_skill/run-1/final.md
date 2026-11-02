## Verdict: not ready to merge yet

Both round-1 fixes work. But the fresh review of main..feature/search-api found new bugs in `notes/search.py`, and a couple of them are input-validation bugs that I'd fix before merging.

### Round-1 findings: both fixed, checked against the repro scripts
I checked the clone of `repo.bundle` at `6746708`, which is where tag round-2 and feature/search-api both point.
```
$ python -I repro/r1_1_cursor_gap.py /tmp/cr-run.cKXdBVLd/clone
does not reproduce
exit=0
$ python -I repro/r1_2_like_wildcard.py /tmp/cr-run.cKXdBVLd/clone
does not reproduce
exit=0
$ python -m pytest -q -p no:cacheprovider
3 passed in 0.01s
```
The checker also tried page sizes from 1 to 30 on 0 to 25 rows, including many rows with the same `created_at`. Every row came back exactly once, in order. It also searched for `%`, `_` and `\`, and each matched only those literal characters. Full output is in `outputs/fix-check.md`.

### New findings from the fresh review
The reviewer was told nothing about round 1. Every item below comes with a command and its output in `outputs/review-round2.md`:

1. **`page_size=0` crashes** with `IndexError: list index out of range`.
2. **A negative `page_size` removes the limit.** `page_size=-1` returned all 50 rows, because SQLite treats `LIMIT -1` as no limit. If a client can set the page size, this is the one that matters most.
3. **Bad page tokens raise a different exception each time:** `Error`, `JSONDecodeError`, `KeyError` or `TypeError`. That includes tokens whose trailing `=` was stripped, which often happens in URLs.
4. **A token isn't tied to its search term.** Using a token from a search for "apple" in a search for "banana" silently returned `[]`.
5. **When the last page is exactly full, the API still returns a token, and that token leads to an empty page.** The fix checker saw the same thing on its own. No rows are lost.
6. **`created_at` is compared as text.** Dates written in different formats or timezones sort in the wrong order, and the cursor can then skip or repeat rows. This only matters if writes don't all use one format.
7. **No index on `(created_at, id)`**, so every page scans and sorts the whole table.
8. **The search SQL is written out twice,** once for the first page and once for later pages.

The tests don't cover page size limits, bad or mismatched tokens, or an exactly full last page.

### Things to know
- **Your local repo has a commit the bundle doesn't.** Here, feature/search-api is at `4932aa7` ("eval setup"), one commit ahead of the bundle. I reviewed the bundle as you asked.
- **The reviewer describes the round-1 cursor bug as repeating rows; your R1-1 says it skipped them.** Either way, it no longer happens.
- **Your request didn't contain any unconfirmed guesses about causes,** so there was nothing I had to keep out of the review.

### Records and cost
- **Workstream doc and tasks:** I couldn't push, so these are on a local `orchestration` branch in the worktree at `/tmp/cr-run.cKXdBVLd/orchestration`. The latest commit is `9e55b28`, and the doc was first committed at `9046dd0`. Without a pushed branch there's no shared copy, and the pre-commit checks weren't run.
- **Prompts:** every prompt sent to an agent is saved word for word as `outputs/subagent-prompt-01.md` through `-06.md`. Number 04 went to a helper that only waited for the results.
- **Tokens:** about 144k across 5 agents.

**Decision for you:** fix items 1–3 (and probably 4–5) and run a round 3, or merge as is and track them separately.