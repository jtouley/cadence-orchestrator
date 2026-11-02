I wouldn't merge this yet. A reviewer agent found two serious bugs and three smaller problems, and the existing tests catch none of them. Both of your suspicions turned out to be real.

I cloned the bundle to `/tmp/cr-run.zEkso1gj/review-clone` and reviewed `main..feature/token-bucket` (f7f6429..3050047). The reviewer agent was never told your suspicions or Priya's. A second agent then checked those two claims separately, writing its own test scripts. Each finding below was reproduced by running code. I read the diff and both agents' result files to confirm the outputs they quoted; I didn't rerun their scripts myself.

**Findings** (all in `ratelimit/token_bucket.py`):

| # | Severity | Finding | What the test showed |
|---|---|---|---|
| F1 | High | **Your refill-clock suspicion is right, but the effect is the opposite of drift: the bucket refills too fast.** `_refill` adds `elapsed * rate` on every call but only moves `_last` forward once there's a whole token. So while the bucket holds less than one token, the same elapsed time is counted again on each call. | Bucket set to 1 token/s: polling 10×/s gave 20 tokens in 10s instead of 10. Polling every 1ms gave **223 grants instead of 11**. The more often callers poll, the more extra tokens they get. |
| F2 | High | **Priya is right: `acquire()` sleeps while holding the lock.** Every other caller is stuck until the sleeper wakes, including the non-blocking `try_acquire()`. | A `try_acquire()` call blocked for 0.95–1.90s and then returned False. `acquire(timeout=0.2)` took 1.90s, so its timeout was ignored. |
| F3 | Medium | `capacity` and `rate` are never checked. | `rate=0` raises `ZeroDivisionError` and `rate=-1` raises `ValueError`. A capacity of 0 or 0.5 makes `acquire()` wait forever, and because of F2 it holds the lock the whole time. |
| F4 | Low | `acquire(timeout=0.9)` on an empty bucket returns False immediately if the wait would exceed the timeout. | Returned after 0.000s. It may be intended, but it isn't documented or tested. |
| F5 | Medium | The tests don't cover locking or refill. | All 4 tests pass. With the lock removed the token-bucket tests still pass, and the same happens with F1 fixed. Timeouts, `block=False`, multiple threads and bad inputs are never tested. |

What checked out: 8 threads making 500 `try_acquire` calls each got exactly 1000 tokens from a capacity-1000 bucket, and the `__init__.py` export is correct.

**Not checked:** fairness among several waiting callers, clocks going backwards, floating-point drift over long runs, performance, and whether F1 changes how long real-clock `acquire()` waits.

**Where things are** (everything is local only, since the bundle has no remote, so nothing was pushed and no pre-commit checks ran):
- **Full reviews:** `.cadence/reviews/token-bucket-review-1.md` and `.cadence/reviews/hunch-check.md` in the clone. The status record is on the clone's local `orchestration` branch at `128ab14`.
- **Test scripts:** `/tmp/cr-run.zEkso1gj/repro/` and `/tmp/cr-run.zEkso1gj/verify/`.
- **Subagent prompts:** all six are saved verbatim as `outputs/subagent-prompt-01.md` through `06.md`. Four went to a helper agent that cloned the repo and kept the records; three of those were short follow-ups after its task file was rejected twice for format.
- **Your local branch has one more commit than the bundle:** `0140adb "eval setup"`, which wasn't part of this review.

Nothing was fixed or merged. If you want, I can have an agent fix F1–F3 and add tests, then run a fresh review on the result.