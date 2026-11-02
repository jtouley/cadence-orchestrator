Don't merge yet. The reviewer found two high-severity bugs, and both are the issues you and Priya suspected. A second agent reran every repro and got the same output as the report. The 4 existing tests still pass on the buggy code.

**What the reviewer found** (full report: `outputs/review-report.md`)

1. **High: refill counts the same time twice.** `_last` only moves forward once the balance reaches 1, so time already turned into fractional tokens gets added again on the next refill (`token_bucket.py:26-28`). Your instinct was right, but the effect is that the bucket hands out tokens too fast, not too slowly. With capacity 1 and a rate of 1/s, polling `try_acquire()` every 0.1s gives `21 (expected 10)` grants in 10s. The fix is to always set `_last = now` after refilling.
2. **High: `acquire()` sleeps while holding the lock** (lines 40-51). This confirms Priya's point. While one thread waits, another thread's `try_acquire()` returned `False after 1.90s (expected ~0s)`.
3. **Medium: the timeout isn't enforced while waiting for the lock.** `acquire(timeout=0.1)` returned `False after 1.90s`. Fixing #2 mostly fixes this.
4. **Medium: a rate of 0 or less isn't rejected.** A rate of 0 raises `ZeroDivisionError`; a negative rate raises `ValueError sleep length must be non-negative`.
5. **Medium: a capacity below 1 isn't rejected.** `try_acquire()` always returns False and `acquire()` never returns.
6. **Medium: the tests miss these cases.** None cover partial refills, timeouts, `block=False`, invalid arguments or more than one thread, which is why all of the above gets through.
7. **Low:** two cleanups (simplify `_refill`, share the token-taking code between the two methods). There's also a design note: `TokenBucket` has no `allow()`, so it can't be swapped in for `FixedWindowLimiter`.

The reviewer also checked and rejected one possible issue: `acquire(timeout=0.99)` returning False right away at 1 token/s is correct, because no token can arrive before 1.0s.

**How this was checked**
- I didn't pass your suspicions or Priya's to the reviewer, so it found #1 and #2 without being pointed at them. I also read `token_bucket.py` myself, and the code matches both findings.
- Rerun any case with `python3 -I /tmp/cr-run.BZmrs5aO/repro/repro.py /tmp/cr-run.BZmrs5aO/wt-3050047 <case>`, using refill, lock, timeout, rate0, rateneg, cap, iface or failfast.

**Not covered:** heavy contention and fairness (only two threads were run), a clock that goes backwards, float precision, inputs like 1.5, NaN or infinity, other Python versions, and `fixed_window.py`, which this range doesn't change.

**Housekeeping**
- **Range reviewed:** the bundle's `feature/token-bucket` stops at `3050047`, so the range was `f7f6429..3050047`. Your working repo has one more commit, `af1b279 eval setup`, which wasn't in the bundle or the review.
- **Workstream record:** there's no remote, so it's kept locally on an `orchestration` branch in `/tmp/cr-run.BZmrs5aO/review-clone`, latest commit `0ededfd`, not pushed. That means no shared branch and no pre-commit checks (pre-commit isn't installed).
- **Prompt copies:** `outputs/subagent-prompt-01.md` to `04.md`, one per agent. 01 and 02 set up the clone and the record, 03 is the reviewer and 04 is the rerun.
- **Leftovers:** the review worktree is still at `/tmp/cr-run.BZmrs5aO/wt-3050047` so you can rerun the repros. Remove it with `git -C /tmp/cr-run.BZmrs5aO/review-clone worktree remove /tmp/cr-run.BZmrs5aO/wt-3050047`.

Nothing has been fixed or merged. If you want #1–#5 fixed, I can send a builder the findings word for word and then run a fix check and a fresh review on the new commits.