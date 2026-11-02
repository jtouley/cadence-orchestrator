Don't merge yet. The reviewer found four real bugs in `ratelimit/token_bucket.py`, and your two hunches are both correct. The existing tests still pass with every one of these bugs present, so they currently catch none of it.

The reviewer wasn't told your hunches, so it found both on its own (findings 1 and 2 below). A second agent then tested them directly. Each finding comes with a script the agent ran and the output it got. Because of the delegation setup I couldn't re-run those scripts myself. Instead I checked them against the code: the mechanism behind every finding matches the code, and the numbers in finding 2 come out the same when worked by hand.

| # | Finding | Evidence |
|---|---|---|
| 1 | **`acquire()` sleeps while holding the lock.** Every other caller on the same bucket waits behind it, including the "non-blocking" `try_acquire()`. | `try_acquire (non-blocking) returned False after 1.900s` |
| 2 | **The bucket refills too fast.** When a refill adds less than a whole token, `_last` doesn't move forward, so the next refill counts the same elapsed time again. | At 1 token/s with a check every 0.1s: `grants over 10.0s ... 21 (expected <= 10)`. A blocking `acquire()` got its token at t=0.5 when it should have waited until t≥1.0. It also turns down timeouts it could have met (`acquire(timeout=0.1)` returns False at t=0.50, but `try_acquire()` succeeds at t=0.51). |
| 3 | **`acquire(timeout=...)` doesn't count time spent waiting for the lock.** The deadline is set before the lock is taken, and taking the lock has no time limit. | `acquire(timeout=0.1) returned False after 1.900s` |
| 4 | **`rate` and `capacity` aren't checked.** `rate=0` crashes on the second `acquire()` with `ZeroDivisionError`. `capacity<1` loops forever while holding the lock. | Full traceback; `still looping after 100000 sleeps` |
| 5 | **Test gaps.** Nothing tests partial refills, timeouts, `block=False`, multiple threads or bad parameters. | `3 passed` with all of the above present |
| 6 | Simplification only (unproven): `_refill` could just be `tokens = min(cap, tokens + elapsed*rate); _last = now`. The extra branches are what cause finding 2. | No reproduction script; it's about maintainability. |

**Your hunches:** in both cases the cause is right, but the effect is a little different from how it was described.
- **Refill clock:** the cause is exactly what you suspected. The effect is that the bucket refills too fast and lets through more than the configured rate. It only happens when something calls into the bucket while it holds less than one token; a bucket left alone until a whole token builds up refills correctly.
- **Priya's lock point:** confirmed, but only threads using the same bucket get stuck. Another bucket answered in `0.000s`, and an unrelated thread kept running normally (`188` ticks during the stall).

**Not covered:**
- The review only looked at the token-bucket change. It didn't cover the fixed-window limiter that's already on `main`, slow rounding drift over long runs, a clock that runs backwards, or the order in which waiting threads get tokens.
- The two thread tests use real time, so exact timings will vary by machine. The 1.9s stall is far larger than any normal scheduling delay.
- No code was changed, merged or pushed. The bundle has no remote, so all tracking stayed local, and `pre-commit` isn't installed so it never ran.
- The task list still shows the two tasks as "claimed" and "assigned"; I didn't send the scribe back to mark them done.

Folders are under `/tmp/cr-run.M1Orbyyw/`:
- **Full review:** `review/orchestration/workstreams/token-bucket-review.review.md`, with each finding's script and output.
- **Hunch notes:** `token-bucket-review.notes.md` in the same folder.
- **Scripts:** in `scripts/`, ready to turn into regression tests.
- **Prompts I sent the agents:** saved word for word as `outputs/subagent-prompt-01.md` through `05.md`.

If you want, I can have an agent fix findings 1–4 and add these scripts as tests, then have a different agent re-review the fix.