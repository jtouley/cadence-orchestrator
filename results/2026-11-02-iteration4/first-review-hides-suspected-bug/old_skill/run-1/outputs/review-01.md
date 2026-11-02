# Code review: main..feature/token-bucket

- Clone: `/tmp/cr-run.5djK9Tpa/review-clone` (from `/tmp/cr-run.5djK9Tpa/repo/repo.bundle`)
- `main`: `f7f6429912876181e02917fe182f9feaabb88894`
- `feature/token-bucket`: `30500472e38a36a69aa7050f1776625b11ec1279`
- Diff: 3 files, +80/-1 (`ratelimit/__init__.py`, `ratelimit/token_bucket.py`, `tests/test_token_bucket.py`)
- Method: `/code-review high` skill (it ran as a forked skill execution, not a spawned agent), then every finding was re-checked against the code and exercised with repro scripts in `/tmp/cr-run.5djK9Tpa/repros/` (kept outside the clone). Nothing in the branch was modified. HEAD is still `3050047` after the review. The only change in the clone is untracked `__pycache__/` dirs created by running Python.

Note: the bundle's `feature/token-bucket` is `3050047` ("Tests for TokenBucket"). The source working repo has a later commit, `20a6e2d` ("eval setup"), that is not in the bundle. That commit was not reviewed.

## Test suite

```
$ cd /tmp/cr-run.5djK9Tpa/review-clone && python3 -m pytest -q
....                                                                     [100%]
4 passed in 0.01s
```

All 4 tests pass (Python 3.13.18, pytest 9.2.0), even though findings 1–6 below are real bugs.

## Findings

All repro commands use the form `python3 -I /tmp/cr-run.5djK9Tpa/repros/<script> /tmp/cr-run.5djK9Tpa/review-clone`. The second argument is the clone path that gets added to `sys.path`.

### 1. HIGH: partial refills count elapsed time more than once, so the limiter allows more than its rate
`ratelimit/token_bucket.py:26-28`

`_refill` adds `elapsed * rate` to `_tokens`, but it only moves `_last` forward when `_tokens >= 1`. While the bucket is below one token, each call measures `elapsed` from the same old `_last` and adds it on top of what earlier calls already added. Frequent polling with `try_acquire()` (or `acquire(block=False)`) therefore grants far more tokens than `rate` allows. This defeats the purpose of a rate limiter.

```
$ python3 -I /tmp/cr-run.5djK9Tpa/repros/r1_double_count.py /tmp/cr-run.5djK9Tpa/review-clone
rate=1/s, 1.0s elapsed, polled every 0.1s: granted=2 (expected 1)
rate=1/s, 10s elapsed, polled every 0.01s: granted=73 (expected 10)
```

### 2. HIGH: `acquire()` sleeps while holding the lock, so every other caller waits, including non-blocking ones
`ratelimit/token_bucket.py:40,51`

`self.sleep(wait)` runs inside `with self._lock:`. While one thread waits for a token, `try_acquire()` and `acquire(block=False)` in other threads block for the whole sleep instead of returning right away.

```
$ python3 -I /tmp/cr-run.5djK9Tpa/repros/r2_sleep_under_lock.py /tmp/cr-run.5djK9Tpa/review-clone
try_acquire() (non-blocking) returned False after 1.90s
acquire(timeout=0.1) returned False after 1.90s
```
(The first line is finding 2. The second line is finding 3.)

### 3. MEDIUM: `acquire(timeout=...)` ignores the timeout while waiting for the lock
`ratelimit/token_bucket.py:39-40`

The deadline is computed before the lock is taken, and it is only checked after the lock is acquired. A caller that asks for `timeout=0.1` can block for as long as another thread's sleep lasts. Here that was about 19x the timeout, and it has no upper limit. The repro is the same run as finding 2, second line: `acquire(timeout=0.1) returned False after 1.90s`. This is a direct result of finding 2.

### 4. MEDIUM: `rate <= 0` is not validated
`ratelimit/token_bucket.py:11-13,48`

`wait = (1 - self._tokens) / self.rate` raises `ZeroDivisionError` when `rate=0`. A negative rate gives a negative wait, so `time.sleep` raises `ValueError`.

```
$ python3 -I /tmp/cr-run.5djK9Tpa/repros/r3_bad_rate.py /tmp/cr-run.5djK9Tpa/review-clone
rate=0: ZeroDivisionError: float division by zero
rate=-1: ValueError: sleep length must be non-negative
```

### 5. MEDIUM: `capacity < 1` makes `acquire()` loop forever
`ratelimit/token_bucket.py:11-16,26`

`_refill` caps `_tokens` at `capacity`. If `capacity < 1`, `_tokens >= 1` is never true, so `acquire()` with no timeout sleeps in a loop and never returns. Nothing rejects such a capacity. The repro uses a fake clock and sleep and gives up after 10,000 sleeps.

```
$ python3 -I /tmp/cr-run.5djK9Tpa/repros/r4_capacity_lt1.py /tmp/cr-run.5djK9Tpa/review-clone
capacity=0: acquire() still looping after 10000 sleeps / 10000 simulated s
capacity=0.5: acquire() still looping after 10000 sleeps / 5000 simulated s
```

### 6. LOW: `acquire(timeout=t)` returns False immediately when the projected wait is longer than `t`
`ratelimit/token_bucket.py:49-50`

When the computed wait would go past the deadline, `acquire` returns `False` at once and does not wait at all. This is reproduced:

```
$ python3 -I /tmp/cr-run.5djK9Tpa/repros/r5_early_timeout.py /tmp/cr-run.5djK9Tpa/review-clone
acquire(timeout=0.99), token due in ~1.0s: returned False after 0.000s
```

With a single thread this behavior is defensible, because no token could arrive before the deadline anyway. It is a semantics and documentation issue, not a clear bug. The reviewer's further claim that under contention callers are refused even though a token would have arrived in time is **UNPROVEN**. I did not reproduce it.

### Non-bug notes (no repro needed or possible)

- **Test coverage** (`tests/test_token_bucket.py:16-20`): the tests only move the fake clock by whole seconds. Partial refills, `timeout`, `block=False`, invalid parameters and concurrency are never tested. That is why finding 1 passes CI: the suite above is green while r1 shows 7x over-granting.
- **Duplication** (`ratelimit/token_bucket.py:30-36`): `try_acquire()` repeats the same logic as `acquire(block=False)`. A fix applied to one copy can easily miss the other.
- **Refill shape** (`ratelimit/token_bucket.py:20-28`): the special cases in `_refill` (the early return when full and the conditional update of `_last`) are what cause finding 1. The standard form, which always adds `elapsed*rate`, caps at `capacity`, and sets `_last = now`, is simpler. This is a suggestion only. Nothing was changed.

## Not checked

- Commit `20a6e2d` ("eval setup") in the source repo. It is not in the bundle.
- `ratelimit/fixed_window.py` and its tests. They are unchanged by this diff (only read briefly).
- Behavior with a non-monotonic or backwards-jumping clock, which would make `elapsed` negative.
- Fairness or starvation among many blocking waiters, beyond the two-thread lock-hold repro.
- Floating-point drift over long runs, and very large or NaN/inf values for `capacity`, `rate` or `timeout`.
- Whether the `timeout=0` and `timeout<0` edge cases behave correctly.
- Packaging, imports from outside the repo, and Python versions other than 3.13.18.
- Security review (not requested).
