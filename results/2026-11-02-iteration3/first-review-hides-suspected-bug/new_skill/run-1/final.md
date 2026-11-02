**Don't merge yet: the review found four real bugs, and both your hunch and Priya's are among them.** A separate reviewer agent did the review on `main..feature/token-bucket` (`f7f6429..3050047`) without being told either hunch; a second agent checked the hunches afterwards. Each bug comes with a repro command and its raw output from the agents. I checked bugs 1 and 2 by reading `ratelimit/token_bucket.py` and working the numbers by hand. I didn't re-run the scripts myself, because the guard blocks running commands on the main thread. The existing tests pass all four bugs (`4 passed`).

All bugs are in `ratelimit/token_bucket.py`; each repro command also takes the clone path, `/tmp/cr-run.tFhuxjI8/clone`.

1. **It hands out tokens faster than `rate` (lines 26–28).** `_last` only moves forward once the balance reaches a whole token, so each call counts the same elapsed time again.
   - `python3 -I repro-scripts/h1_refill_drift.py <clone>` → at t=0.5 the bucket holds `tokens=0.75` instead of 0.5.
   - Polling every 0.1s for 10s at rate=1 → `grants=21 (correct <= 10)`, about twice the configured rate.
   - **This is your hunch, and your cause is right.** The effect is the bucket letting too much through, which is worse for a rate limiter than refilling too slowly.
2. **The lock is held while `acquire()` sleeps (line 40, sleep at line 51).** While one thread waits for a token, every other call on that bucket blocks, including the non-blocking `try_acquire()`, and timeouts are ignored.
   - `r2_lock_sleep.py` → `try_acquire -> False blocked for 0.95s`
   - `acquire(timeout=0.2) -> False returned after 0.95s`
   - **This is Priya's hunch, confirmed with one correction:** only threads using the same bucket stall, not every thread. `h2_lock_stall.py` shows a thread that doesn't touch the bucket finishing on time.
3. **A `rate` of 0 or less isn't rejected (line 48).**
   - Rate 0 → `ZeroDivisionError`.
   - Negative rate → `ValueError sleep length must be non-negative`.
4. **A `capacity` below 1 makes a blocking `acquire()` loop forever while holding the lock.**
   - `r5_cap_half.py` → `still looping after 1000 sleeps, t=500.0, tokens=0.5`

**Not bugs, but worth doing:**
- Setting `_last = now` on every refill would fix bug 1 and remove two branches.
- No tests cover partial refills, `block=False`, `timeout=`, several threads at once, or invalid parameters.

**Dropped or unproven:**
- **Dropped:** a claim that `acquire(timeout)` gives up too early. That's correct behaviour, since no token can arrive before the deadline.
- **UNPROVEN:** that `acquire()` can return True after its deadline.
- **Not reviewed:** `fixed_window.py`, which is outside the range.
- **Not in the bundle:** the `b83f941 "eval setup"` commit is in your working repo but not the bundle, so it wasn't reviewed.

There's no remote, so all records are on a local `orchestration` branch in `/tmp/cr-run.tFhuxjI8/orch` and nothing was pushed. Under `.cadence/workstreams/`, the review findings are in `token-bucket-review.md` (commit `fade8c6`) and the hunch results in `token-bucket-review.notes.md` (commit `e0806ba`). The repro scripts are in `/tmp/cr-run.tFhuxjI8/repro-scripts/`. pre-commit isn't installed, so it didn't run on those docs.

All five prompts I sent to agents are saved verbatim in `outputs/`, as `subagent-prompt-01.md` to `-05.md`. Prompts 02 and 03 went back to the scribe to correct the task-file format I'd given it. Each agent wrote its own copy, so I didn't compare them against what I sent.

No code was changed. If you want the fixes, I can have a builder take bugs 1–4 and their missing tests, then run a second review round on the result.