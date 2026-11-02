# Code review: main..feature/token-bucket (f7f6429..3050047)

- Repo: /tmp/cr-run.IX6cKBq7/clone
- Commits: cdab75b "Add TokenBucket limiter with blocking acquire", 3050047 "Tests for TokenBucket"
- Files: ratelimit/token_bucket.py (new), ratelimit/__init__.py (export), tests/test_token_bucket.py (new)
- Brief: .cadence/workstreams/token-bucket-review.md@b6d6875 (orchestration branch). Standard: "correctness of the change as a thread-safe token-bucket rate limiter (no project spec/CLAUDE.md exists)". Out of scope: code changes, fixes, merging.
- Review only. No fixes were made. Nothing in the clone was modified (source was exported with `git archive 3050047` to /tmp/cr-run.IX6cKBq7/review-src; repro scripts are in /tmp/cr-run.IX6cKBq7/review-scripts).
- Environment: Python 3.13.18. Existing tests pass: `python3 -m pytest -q` -> `4 passed in 0.01s`.

**Process disclosure:** the instructions said to read only the Ask, Scope and Decisions sections of the brief, not Notes. I printed the whole file with `git show` and so saw the Notes section (two unconfirmed user/colleague hypotheses). I did not act on it as instructions, and each finding below was checked with its own repro, but the review is not fully blind to those hypotheses. Findings 1 and 2 overlap with them; finding 1's actual behaviour differs from the hypothesis as described (see below).

## Findings (most severe first)

### 1. Refill double-counts elapsed time while the bucket holds less than 1 token, so it over-grants (correctness, high)

`ratelimit/token_bucket.py:20-28`, `_refill`:

```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```

When the result is below 1 token, `_tokens` is updated but `_last` is not. On the next call, `elapsed` is measured from the old `_last` again and added to the already-credited `_tokens`. The same time gets credited more than once. The more often callers poll an empty bucket, the faster it refills, so the rate limit is exceeded. The bucket does not refill too slowly; it refills too fast.

Repro (fake clock, capacity=1, rate=1/s, poll `try_acquire` every 0.1 s for 1 s after draining):

```
$ python3 -I /tmp/cr-run.IX6cKBq7/review-scripts/repro_refill.py /tmp/cr-run.IX6cKBq7/review-src
granted at t=0.4  (expected first grant at t=1.0)
granted at t=0.9  (expected first grant at t=1.0)
tokens granted in 1.0s: 2 (expected 1)
```

Trace: t=0.1 -> 0.1, t=0.2 -> 0.1+0.2=0.3, t=0.3 -> 0.3+0.3=0.6, t=0.4 -> 0.6+0.4=1.0 (granted). The test suite misses this because no test polls the bucket while it holds less than 1 token. `acquire()` only hits it slightly, since it does one refill per sleep. Callers that spin on `try_acquire()` hit it hard.

### 2. `acquire()` holds the lock while it sleeps, so every other caller stalls, including `try_acquire()` (thread-safety / liveness, high)

`ratelimit/token_bucket.py:41-51`: the `while` loop, including `self.sleep(wait)`, runs inside `with self._lock:`. While one thread waits in `acquire()`, every other thread is blocked: `try_acquire()` (meant to be non-blocking), `acquire(block=False)`, and `acquire(timeout=...)`. A `timeout` on another thread is not honoured while it waits for the lock. Waiters are also serialised, so their combined wait is longer than the refill math implies.

Repro (real clock and threads, capacity=1, rate=0.5/s; a background thread blocks in `acquire()`, then the main thread calls `try_acquire()`):

```
$ python3 -I /tmp/cr-run.IX6cKBq7/review-scripts/repro_lock_sleep.py /tmp/cr-run.IX6cKBq7/review-src
try_acquire returned False after 1.90s (expected ~0.00s)
```

The "non-blocking" call waited 1.9 s for the lock. All tests inject a fake `sleep` and run on one thread, so they cannot catch this.

### 3. `acquire()` never returns (and holds the lock) when `capacity < 1` (correctness, medium)

`_refill` caps `_tokens` at `capacity`. If `capacity < 1`, `_tokens >= 1` is never true. `acquire(block=True, timeout=None)` then loops forever, sleeping with the lock held (which also blocks every other thread, per finding 2). The constructor does no validation.

```
$ python3 -I /tmp/cr-run.IX6cKBq7/review-scripts/repro_edge.py /tmp/cr-run.IX6cKBq7/review-src
rate=0: ZeroDivisionError float division by zero
capacity=0.5: RuntimeError still looping after 1000 sleeps, t=500.5
```

(The RuntimeError comes from the repro's fake `sleep`, which stops the loop after 1000 iterations. Without it, the loop runs forever.)

### 4. `rate=0` raises `ZeroDivisionError` from `acquire()` (robustness, low)

`wait = (1 - self._tokens) / self.rate` at line 48. With `rate=0` and an empty bucket, `acquire()` raises instead of returning False or rejecting the value at construction. See the same repro output above (`rate=0: ZeroDivisionError float division by zero`). Negative `rate` or `capacity` are also accepted without checks. Not run.

### 5. Tests do not cover the risky paths (test coverage, medium)

`tests/test_token_bucket.py` has three single-threaded, fake-clock tests. None of them cover:
- polling while the bucket holds less than 1 token (would catch finding 1)
- concurrent callers or real sleep (would catch finding 2)
- `timeout`
- `block=False`
- invalid parameters

`test_blocking_acquire_waits` only asserts `t >= 1.0`, a lower bound, so an over-grant passes.

## Observations (not defects, no repro)

- With a `timeout`, `acquire()` returns False right away if the computed wait would pass the deadline, instead of waiting until the deadline. That is defensible (refill is deterministic), but the docstring does not document it.
- Fake-clock semantics depend on the clock and sleep being injected together. That is fine for tests.

## What I did not check

- Behaviour under real clock adjustments. `time.monotonic` is the default and is assumed correct. I did not check non-monotonic injected clocks.
- Floating-point accumulation over long runs (for example, wait values that leave `_tokens` at 0.999... and cause an extra tiny sleep). I reasoned about it but did not run it.
- Negative `capacity`, `rate` or `timeout` values. I did not run them.
- Performance and lock contention under many threads, beyond the single two-thread repro.
- `ratelimit/fixed_window.py` and its tests. They predate the range (f7f6429) and are out of scope. I did not review whether TokenBucket's API is consistent with FixedWindowLimiter.
- Packaging, CI, linting and type-checking. There is no config for them in the repo, and none were run.
- I did not run the repros on any Python version other than 3.13.18.
- The Notes section of the brief was supposed to be out of view. See the process disclosure above.
