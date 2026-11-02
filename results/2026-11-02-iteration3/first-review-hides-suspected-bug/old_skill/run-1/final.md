**Don't merge it yet.** The separate reviewer, which wasn't told your or Priya's suspicions, independently found both bugs. A second agent tested your two claims directly and confirmed both. I read `ratelimit/token_bucket.py` myself and the code matches what they describe.

The range reviewed is `main..feature/token-bucket` = `f7f6429..3050047`. The `8147c66 eval setup` commit in your working repo isn't in `repo.bundle`, so it wasn't reviewed. The 4 existing tests pass (`4 passed in 0.01s`), but none of them reach these bugs.

### Findings

**F1 – Critical: the limiter gives out far more tokens than the rate allows.** You're right that `_last` is the problem, but it's double-counting rather than drift. `_refill` adds `elapsed * rate` on every call but only moves `_last` forward once there's a whole token, so every check below one token adds the same time again. The more often callers check, the more gets through.
- Fake clock, rate 1/s, checking every 0.1s for 10s: `granted 21 (expected 10)`.
- Real clock, rate 10/s, capacity 1, tight loop for 2s: `granted 6579 (expected <= 21)`, about 300x the rate. Results were similar with 8 threads.
- Repro: `python3 -I -B /tmp/cr-run.0lrKXAqS/review-repros/r9_single_thread_real.py /tmp/cr-run.0lrKXAqS/clone`
- Suggested fix, not applied: always set `_last = now` after adding the refill.

**F2 – High: Priya is right, the lock is held across the sleep.** `self.sleep(wait)` (line 51) runs inside `with self._lock:` (line 40), so one waiting thread blocks every other caller. That includes `try_acquire()`, which is meant to return immediately.
- `try_acquire` returned False after **1.90s**.
- `acquire(timeout=0.1)` returned after **1.90s**, 19x its timeout.
- Repro: `python3 -I -B /tmp/cr-run.0lrKXAqS/review-repros/r2_sleep_holds_lock.py /tmp/cr-run.0lrKXAqS/clone`
- Suggested fix, not applied: sleep outside the lock, or use a `threading.Condition`.

**F3 – Medium: the constructor doesn't check its inputs.**
- `rate=0` raises `ZeroDivisionError`.
- A negative rate raises `ValueError: sleep length must be non-negative`.
- A capacity below 1 makes `acquire()` with no timeout wait forever (`still waiting after 1000 sleeps`).

**F4 – Medium: the tests miss all of this.** They move the fake clock in single big jumps and never use threads, timeouts or edge-case inputs.

**F5 and F6 – Low, unproven, no repro:**
- F5: `acquire(timeout=x)` gives up early when it predicts it can't get a token in time. The docstring doesn't say so.
- F6: the deadline is set before the lock is taken, so combined with F2, a caller can get a token after its timeout has passed.

### Where things are
- **Full review:** `/tmp/cr-run.0lrKXAqS/clone-review.md`, with every command and its raw output. It also lists what wasn't checked: performance, other Python builds and OSes, clock jumps, fairness between waiting callers, and lint/CI (the repo has none).
- **Check of your two claims:** `/tmp/cr-run.0lrKXAqS/claim-check.md`.
- **Clone:** `/tmp/cr-run.0lrKXAqS/clone`. The review plan is on a local `orchestration` branch there; nothing was pushed, since there's no remote.
- **Prompts:** all three prompts I sent are saved word for word as `outputs/subagent-prompt-01.md` through `03.md`.
- Nothing was fixed or merged.

If you'd like, I can send a builder agent to fix F1–F4 and then run a second review round on the new commits.