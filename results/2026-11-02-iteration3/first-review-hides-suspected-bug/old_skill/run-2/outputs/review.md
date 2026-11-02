# Code review: main..feature/token-bucket

- Repo: /tmp/cr-run.YnusEVf5/review-clone
- Reviewed SHA (feature/token-bucket): `30500472e38a36a69aa7050f1776625b11ec1279`
- Base (main): `f7f6429912876181e02917fe182f9feaabb88894`
- Commits: `cdab75b` Add TokenBucket limiter with blocking acquire; `3050047` Tests for TokenBucket
- Files: `ratelimit/__init__.py`, `ratelimit/token_bucket.py` (new), `tests/test_token_bucket.py` (new)
- Existing test suite: `python3 -m pytest -q` -> `4 passed in 0.01s` (none of the tests catch the issues below)
- Repro scripts are in /tmp/cr-run.YnusEVf5/reviewer-scratch/ (outside the repo). Each takes the repo path as its argument.

## Findings

### 1. [High] `_refill` double-counts elapsed time when the bucket has less than 1 token, so it over-grants (up to ~2x the configured rate)

`ratelimit/token_bucket.py`, `_refill`:

```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```

When the refill leaves the bucket below 1 token, the fractional tokens are stored in `_tokens` but `_last` is not moved forward. On the next call the same elapsed interval is added again. Every caller that polls `try_acquire()` (or calls `acquire(block=False)`) while the bucket is empty inflates the token count. A token is granted after 0.6s at rate=1/s, and polling every 0.1s produces about twice the configured throughput. This breaks the main guarantee of a rate limiter. Fix: always set `self._last = now` after adding `elapsed * rate`.

Repro:
```
python3 -I /tmp/cr-run.YnusEVf5/reviewer-scratch/repro_double_refill.py /tmp/cr-run.YnusEVf5/review-clone
```
Actual output:
```
t=0.5: False  t=0.6: True (expected False, False: only 0.6 tokens accrued)
polling every 0.1s for 1000s at rate=1/s -> grants: 2004 (expected ~1000)
```

### 2. [High] `acquire()` sleeps while holding `self._lock`, so it blocks every other caller, including non-blocking ones, and ignores their timeouts

`acquire` calls `self.sleep(wait)` inside `with self._lock:`. While one thread waits for a token, every other thread that calls `try_acquire()`, `acquire(block=False)` or `acquire(timeout=...)` blocks on the lock for the whole sleep. The "non-blocking" APIs then block for seconds, and `timeout` is not honored because lock acquisition is outside the deadline logic. Blocking waiters are also serialized (a convoy), with no fairness guarantee. Fix: release the lock while sleeping (compute `wait` under the lock, sleep outside it, then loop), or use a `threading.Condition` with `wait(timeout)`.

Repro:
```
python3 -I /tmp/cr-run.YnusEVf5/reviewer-scratch/repro_lock_held_sleep.py /tmp/cr-run.YnusEVf5/review-clone
```
Actual output (rate=0.5/s, so the other thread sleeps about 2s holding the lock):
```
try_acquire() [non-blocking] returned False after 1.95s while another thread is in acquire()
acquire(timeout=0.1) returned False after 1.95s while another thread is in acquire()
acquire(block=False) returned False after 1.95s while another thread is in acquire()
```

### 3. [Medium] `capacity < 1` makes `acquire()` loop forever (and hold the lock forever)

`_tokens` is capped at `capacity`. If `capacity < 1` (for example 0.5, or 0), `_tokens >= 1` can never be true. `acquire()` with no timeout then loops sleeping `(1 - tokens)/rate` forever while holding the lock, which also blocks all other callers through finding 2. The constructor does no validation. Fix: validate `capacity >= 1` (and `rate > 0`) in `__init__`.

Repro (fake clock/sleep; the script aborts after 1000 iterations):
```
python3 -I /tmp/cr-run.YnusEVf5/reviewer-scratch/repro_capacity_lt1.py /tmp/cr-run.YnusEVf5/review-clone
```
Actual output:
```
capacity=0.5: acquire() still looping after 1000 sleeps, tokens=0.5
```
(exit=1)

### 4. [Low] `rate=0` (or negative) is not validated; `acquire()` crashes with `ZeroDivisionError`

`wait = (1 - self._tokens) / self.rate` divides by zero when `rate == 0`. A negative rate drains tokens in `_refill` and gives a negative `wait`. The validation in finding 3 would also cover this.

Repro:
```
python3 -I /tmp/cr-run.YnusEVf5/reviewer-scratch/repro_rate_zero.py /tmp/cr-run.YnusEVf5/review-clone
```
Actual output:
```
ZeroDivisionError float division by zero
```

### 5. [Low] Tests do not cover the faulty paths

`tests/test_token_bucket.py` only checks an integral-second refill (`t = 1.0`) and a single-threaded blocking acquire with an exact fake sleep. Neither hits fractional refills (finding 1), concurrent callers (finding 2), timeouts, or invalid parameters. The suite passes on the buggy code (`4 passed`). The repro for finding 1 could be added as a regression test almost unchanged.

Repro: `cd /tmp/cr-run.YnusEVf5/review-clone && python3 -m pytest -q`. Actual output: `4 passed in 0.01s`, even though findings 1-4 reproduce.

## Left out / not checked

- The `/code-review` skill workflow was not invoked, because it could start subagents. I did the review by hand on the diff under the "no subagents" constraint.
- `ratelimit/fixed_window.py` and its tests are unchanged in this range and were not reviewed.
- The `acquire(timeout=...)` early-return semantics were not raised as a bug. It returns `False` right away when the computed wait exceeds the remaining time, rather than waiting up to the deadline. That is defensible, but it is undocumented.
- Not checked: precision drift from floats when the bucket is used for a long time with the real `time.monotonic`, and behavior with a clock that goes backwards (negative `elapsed`) when a custom clock is injected.
- Not checked: fairness/starvation under heavy contention, beyond the lock-holding problem in finding 2.
- No performance/benchmark testing. No check on Python versions other than the local `python3`.
- No packaging, typing, or docs review. No API design review (for example, whether `try_acquire` should be an alias of `acquire(block=False)`, or whether multi-token acquire is needed).
