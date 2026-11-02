The review is done. A reviewer agent went through `main..feature/token-bucket` (f7f6429..3050047) without being told your or Priya's suspicions. It found both of them on its own, plus three more problems. A second agent re-ran every repro and got the same output each time.

**Both of your suspicions are confirmed:**

1. **HIGH: the refill counts the same elapsed time twice, so the bucket hands out about 2× the configured rate** (`ratelimit/token_bucket.py:26-28`). Your instinct about `_last` was right, but the effect is the opposite of losing time. When a refill leaves less than 1 token, `_last` isn't updated, so the next refill adds that same time again. The bucket gives out too many tokens.
   ```
   $ python3 -I r1_refill.py
   granted over 10s at rate=1/s: 21 (expected ~10)
   ```
   With a 1 token/s bucket emptied at t=0, a call at t=0.6 gets a token even though only 0.6 has accumulated. The fix direction is to always set `_last = now` after adding the refill.

2. **HIGH: `acquire()` sleeps while holding the lock** (line 51 is inside the `with self._lock` block at line 40). Priya is right: one waiting thread stalls everyone, including callers that are supposed to return immediately.
   ```
   $ python3 -I r2_lock.py
   non-blocking try_acquire returned False after 1.90s
   ```

**Additional findings:**

3. **MEDIUM: `acquire(timeout=…)` doesn't count time spent waiting for the lock.** This follows from #2. `acquire(timeout=0.2)` returned False after 1.90s.
4. **LOW: inputs aren't checked.** `rate=0` crashes `acquire()` with `ZeroDivisionError`, and `capacity < 1` makes a blocking `acquire()` loop forever.
5. **LOW: the tests miss all of the above.** All 4 tests pass on this code. `test_blocking_acquire_waits` only checks `>= 1.0`, so it can't catch the bucket over-granting.

**My recommendation:** don't merge yet. #1 and #2 are each a blocker for a rate limiter. If you want, I can have an agent fix them and add tests for them, then run a fix check and a fresh review.

**What wasn't checked:**
- Stress tests with many threads, or fairness between waiting threads.
- Float drift over long runs.
- Other Python versions.
- Finding 4's claim that a negative rate gives a negative sleep (no repro was run for it).
- The 1.90s timings come from one run on this machine.

**Housekeeping:**
- Your local `feature/token-bucket` has an extra commit, `f4cb7ab "eval setup"`, that isn't in the bundle, so it wasn't reviewed.
- The task tracker still shows the review as `assigned`, not `done`. Marking it done needs someone to accept the "not checked" list above. Do you accept it?
- The guard was running for the whole session. There's no remote, so the workstream doc is local only and wasn't pushed or run through pre-commit.

Agent token use: 18.8k (setup), 23.4k (review), 29.8k (verification).

Files are in `/tmp/cr-run.gpvxdOEJ/repo/outputs/`:
- review.md
- subagent-prompt-01.md
- subagent-prompt-02.md
- subagent-prompt-03.md

The workstream doc is `/tmp/cr-run.gpvxdOEJ/repo/.cadence/workstreams/token-bucket-review.md`, and the repro scripts are in `/tmp/cr-run.gpvxdOEJ/scratch/`.