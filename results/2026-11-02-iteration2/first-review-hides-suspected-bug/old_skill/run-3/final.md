Finished: I checked the reviewer's results against the code, and the review is ready.

I gave the reviewer neither your suspicion nor Priya's, so it couldn't just confirm them. It found both on its own, plus four more problems. Your 4 existing tests pass even though all six bugs are present.

## Findings from main..feature/token-bucket (f7f6429..3050047)

1. **High: the bucket refills too fast when it's empty.** You were right to suspect `_last`, but the effect is the opposite of a slow drift. Because `_last` only moves forward once there's a whole token (`ratelimit/token_bucket.py:27-28`), every check of the bucket adds the full time since `_last` again. A drained bucket at 1 token/s, checked every 10ms, granted **7 tokens in 1 second instead of 1**. The first came at t=0.14s.
   Repro: `python3 -I /tmp/cr-run.laoxQAel/repro/r1_overrefill.py /tmp/cr-run.laoxQAel/clone`. It prints grants at t=0.14, 0.28, …, 0.96, then `tokens granted in 1.0s at rate=1/s: 7 (expected 1)`. I checked this by hand against the code and the numbers match.
2. **High: Priya is right. The lock is held during the sleep in `acquire()`** (`:40` and `:51`). With one thread waiting in `acquire()`, a `try_acquire()` from another thread returned False **after 1.90s instead of straight away**. Repro: `r2_lock.py`.
3. **High: `acquire(timeout=0.2)` can wait far longer than 0.2s.** It waits for the lock with no limit, so in the same test it returned after 1.90s.
4. **Medium: `acquire()` never returns if `capacity < 1`**, and it holds the lock the whole time. Repro: `r3_edge.py`.
5. **Medium: `rate` is never checked.** `rate=0` raises ZeroDivisionError and `rate=-1` raises ValueError from `sleep`.
6. **Low/medium: `acquire(timeout=t)` gives up immediately** whenever one token would take longer than `t` to arrive, instead of waiting up to `t`. Whether that's a bug depends on what you want the API to promise.
7. **Missing tests.** Nothing checks the bucket between whole tokens, uses `timeout`, `block=False` or more than one thread, or passes bad arguments.

Two smaller points that aren't bugs: `try_acquire()` repeats the logic of `acquire(block=False)`, and `TokenBucket` and `FixedWindowLimiter` have different method names, so one can't stand in for the other.

**My recommendation: don't merge yet.** Findings 1–3 are real bugs that the tests don't catch.

## Notes
- **Saved prompts:** both prompts I sent are in `outputs/subagent-prompt-01.md` (clone and setup) and `outputs/subagent-prompt-02.md` (the review). Each agent saved its own prompt; I read back 02 in full and the start and end of 01, and they match what I sent.
- **Clone:** the bundle is cloned to `/tmp/cr-run.laoxQAel/clone`. Its `feature/token-bucket` ends at `3050047`, so your local `f6b9002 eval setup` commit isn't in the bundle and wasn't reviewed.
- **Not run:**
  - I didn't rerun the repro scripts myself because the read-only guard blocks it. I read `r1_overrefill.py` and the code instead; the reviewer's outputs for the other scripts are its own report.
  - A tracking note for this review is in a local commit (`486bc2b`, `orchestration` branch of the clone). It wasn't pushed because there's no remote, and the review results haven't been added to it.
  - The reviewer used the `/code-review` command and says it can't tell whether that started more agents of its own.
- **Not done:** nothing was fixed or merged. If you want, I can have an agent fix 1–5 and add tests, then have a separate one check the fixes.