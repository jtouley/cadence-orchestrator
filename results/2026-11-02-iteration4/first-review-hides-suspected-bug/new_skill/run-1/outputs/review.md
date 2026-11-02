# Code review: token-bucket (main..feature/token-bucket)

- Range: f7f6429 (main) .. 3050047 (feature/token-bucket). Commits: cdab75b "Add TokenBucket limiter with blocking acquire", 3050047 "Tests for TokenBucket"
- Clone: /tmp/cr-run.1p5VGY0i/review-clone (refs checked: main=f7f6429912876181e02917fe182f9feaabb88894, feature/token-bucket=30500472e38a36a69aa7050f1776625b11ec1279)
- Spec: .cadence/workstreams/token-bucket-review.md @ 04d57ca (orchestration branch)
- Files changed: ratelimit/__init__.py, ratelimit/token_bucket.py (new, 51 lines), tests/test_token_bucket.py (new, 27 lines)
- Method: I did the review by hand in a single agent with no subagents and made no fixes. I exported the tip commit with `git archive 3050047 | tar -x -C /tmp/cr-tip.3sJj`. The repro scripts are in /tmp/cr-scripts/ and run with `python3 -I` (Python 3.13.18). Each one takes the exported tree as its argument.

Baseline: the branch's own test suite passes.
```
$ cd /tmp/cr-tip.3sJj && python3 -m pytest -q
....                                                                     [100%]
4 passed in 0.01s
```

## Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | High | `_refill` counts the same elapsed time more than once, so the bucket grants tokens faster than `rate` | CONFIRMED |
| 2 | High | `acquire()` sleeps while holding the lock, which blocks `try_acquire()`, `acquire(block=False)` and `acquire(timeout=...)` in other threads | CONFIRMED |
| 3 | Medium | `rate=0` raises ZeroDivisionError. `capacity < 1` makes `acquire()` wait forever. There is no input validation | CONFIRMED |
| 4 | Medium | Tests miss partial refill, threads, timeout and `block=False`, so findings 1 and 2 pass the suite | CONFIRMED |

---

## 1. `_refill` counts elapsed time twice when the token count stays below 1 (over-grants)

ratelimit/token_bucket.py, `_refill`:
```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```
When the refill leaves `_tokens` below 1, the new fractional amount is saved in `_tokens` but `_last` stays where it was. The next call measures `elapsed` from that same old `_last` and adds the whole interval again. Callers who poll often (the normal `try_acquire` pattern) therefore get tokens early. This breaks the docstring's promise of a refill at `rate` tokens per second.

Repro (fake clock, capacity=1, rate=1/s, polling every 0.4s after the bucket is drained at t=0):
```
$ python3 -I /tmp/cr-scripts/r1_double_count.py /tmp/cr-tip.3sJj
grants at: [0.8, 1.6, 2.4, 3.2]
count in (0, 3.6]: 4 | correct rate allows at most 3 (at t=1.2, 2.4, 3.6)
exit=0
```
The first grant comes at t=0.8, when only 0.8 tokens should have built up: 0.4 at t=0.4, then 0.4 + 0.8 = 1.2 at t=0.8. That is 4 grants where the limit is 3.

## 2. `acquire()` holds the lock while it sleeps

ratelimit/token_bucket.py, `acquire`: the whole `while True` loop, including `self.sleep(wait)`, runs inside `with self._lock:`. While one thread waits for a token:
- `try_acquire()` in any other thread blocks for the full sleep, even though it is meant to be non-blocking.
- `acquire(block=False)` also blocks.
- `acquire(timeout=t)` ignores its timeout while it waits for the lock. The timeout only applies after the lock is acquired.
- Blocked waiters are served in whatever order they get the lock, not in arrival order (not separately proven).

Repro (real clock, capacity=1, rate=0.5/s. A background thread calls `acquire()` on a drained bucket, then the main thread makes the call shown):
```
$ python3 -I /tmp/cr-scripts/r2_lock_held.py /tmp/cr-tip.3sJj
try_acquire() [non-blocking; expected ~0s] returned False after 1.90s
acquire(timeout=0.1) [expected <=~0.1s] returned False after 1.90s
acquire(block=False) [expected ~0s] returned False after 1.90s
exit=0
```

## 3. No validation of `rate` / `capacity`

- With `rate=0`, `acquire()` divides by zero in `wait = (1 - self._tokens) / self.rate`. A negative rate is untested (UNPROVEN, but the same expression gives a negative sleep, which `time.sleep` rejects).
- With `capacity < 1`, `_tokens` is capped below 1 forever. `acquire()` with no timeout then loops and sleeps endlessly instead of failing.

Repro:
```
$ python3 -I /tmp/cr-scripts/r3_edge.py /tmp/cr-tip.3sJj
rate=0 acquire(): ZeroDivisionError float division by zero
capacity=0.5 acquire(): still sleeping after 1000 iterations | t = 500.5
exit=0
```
(The script's fake `sleep` raises after 1000 calls. Without that limit the call would never return.)

## 4. Test coverage is too thin to catch the bugs above

tests/test_token_bucket.py has 3 tests. All of them advance the clock in whole-token steps and run on one thread. Nothing covers:
- partial or fractional refill across several calls (finding 1)
- concurrent callers or lock behaviour (finding 2)
- `acquire(timeout=...)` and `acquire(block=False)`, which have no tests at all
- invalid constructor arguments (finding 3)
- capping at `capacity` after a long idle period

Evidence: the suite passes against code that fails repros 1 to 3 (see the baseline output above: `4 passed`).

---

## Smaller observations (not proven as defects)

- UNPROVEN / design: `acquire(timeout=t)` returns False at once if the first computed `wait` would pass the deadline. It never uses part of the timeout budget. That is fine as fail-fast behaviour, but it is not documented.
- UNPROVEN: the `deadline` is computed with `self.clock()` before the lock is taken (consistent with finding 2, but worth noting once that is fixed).
- The `__init__.py` export change is correct.

## What I did not check

- Code outside the range: `ratelimit/fixed_window.py` and its tests were not reviewed.
- Python versions other than 3.13.18, and free-threaded (no-GIL) builds.
- Long-running behaviour: float drift over many refills, or a clock that is not monotonic (for example an injected clock that goes backwards).
- Fairness and starvation between many waiting threads. This was reasoned about, not measured.
- Performance under heavy contention.
- Real-time sleep accuracy: only fake clocks were used, except in repro 2.
- Security, packaging and the CI configuration (none appeared to be in the range).
- I did not use the /code-review skill tooling itself. The instruction ruled out subagents, so I did the review manually in one agent.
