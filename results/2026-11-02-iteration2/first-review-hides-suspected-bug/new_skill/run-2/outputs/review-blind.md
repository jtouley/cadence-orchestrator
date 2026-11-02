# Review: f7f6429..3050047 (TokenBucket) in /tmp/cr-run.IX6cKBq7/clone

Scope: commits cdab75b (Add TokenBucket limiter with blocking acquire) and 3050047 (Tests for TokenBucket).
Files changed: `ratelimit/__init__.py`, `ratelimit/token_bucket.py` (+51), `tests/test_token_bucket.py` (+27).

How I worked: I read the code only through `git diff f7f6429..3050047` in the clone. I ran it from a `git archive 3050047` export at
`/tmp/tbexport.gyvg`, with the repro scripts kept separately in `/tmp/tbscripts.rR2i`. Every Python run used `python -I`. No fixes were made.

Verdict: **Not correct as a thread-safe token-bucket limiter.** The refill logic hands out more tokens than the configured rate allows, and blocking `acquire` sleeps while it holds the lock, so it blocks every other caller.

---

## Findings

### 1. [High] Refill counts the same elapsed time more than once, so the bucket grants more than `rate`
`_refill` always adds `elapsed * rate` to `_tokens`, but it only moves `_last` forward when the result is `>= 1`:

```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```

When a refill leaves the bucket below 1 token, the partial token is stored in `_tokens` and `_last` stays where it was. The next refill measures time from that same old `_last` and adds the same interval again. Frequent polling (try_acquire or the acquire loop) therefore inflates the refill rate.

Repro (one token, rate 1/s; a second token should not be available until t=1.0):
```
$ python -I /tmp/tbscripts.rR2i/double.py /tmp/tbexport.gyvg
t=0.0 acquire True
t=0.5 acquire False tokens 0.5
t=0.9 acquire True tokens 0
```
The token is granted at t=0.9, after only 0.9 s, because the 0.0–0.5 s interval was counted twice (0.5 + 0.9 = 1.4).

Repro (capacity 10, rate 1/s, drained, then polled every 0.1 s for 3 s):
```
$ python -I /tmp/tbscripts.rR2i/poll.py /tmp/tbexport.gyvg
rate=1/s, polled 3.0s after draining: granted 7 (expected 3)
```
That is more than double the configured rate. Polling faster makes the over-grant worse.

### 2. [High] `acquire()` sleeps while holding `self._lock`, which serialises and blocks all other callers
The whole `while True` loop, including `self.sleep(wait)`, runs inside `with self._lock:`. While one thread waits for a token:
- `try_acquire()`, which should never block, blocks for the whole wait.
- `acquire(block=False)` and timed `acquire` calls from other threads block too, and they can overrun their own timeout by an unbounded amount, because the deadline is only checked after they get the lock.
- Waiters queue up on the lock instead of the bucket.

Repro (rate 0.5/s, bucket drained; thread A calls `acquire()`; the main thread then calls `try_acquire()` 0.1 s later):
```
$ python -I /tmp/tbscripts.rR2i/lockhold.py /tmp/tbexport.gyvg
non-blocking try_acquire returned False after 1.90s
acquire(block=False) returned False after 0.00s
```
The supposedly non-blocking `try_acquire` stalled for 1.9 s, which is the rest of thread A's sleep. (The second line ran after A had already taken the token and released the lock, so it returned straight away.)

### 3. [Medium] Bad parameters are not validated: `rate=0` crashes, and `capacity < 1` makes `acquire` wait forever
- With `rate <= 0`, `wait = (1 - self._tokens) / self.rate` raises `ZeroDivisionError` for 0. A negative rate gives a negative sleep (not reproduced).
- With `capacity < 1`, `_tokens` can never reach 1, so a blocking `acquire()` with no timeout loops forever.

```
$ python -I /tmp/tbscripts.rR2i/edge.py /tmp/tbexport.gyvg
rate=0: ZeroDivisionError float division by zero
capacity=0.5: still waiting after 6 sleeps, t=3.0, tokens=0.5
```
(The second case uses an injected sleep that aborts after 6 iterations. Without that abort the loop would not end.)

### 4. [Low] Timed `acquire` gives up early instead of waiting until the deadline
If `clock() + wait > deadline`, the call returns `False` straight away instead of sleeping until the deadline. This is consistent with what the caller will get in the end, so it is acceptable, but it is not documented. Combined with finding 2, the effective timeout is not respected anyway. Inferred from the code; not reproduced separately.

### 5. [Low] The tests miss the defects above
The 3 new tests pass. The 4 passed shown below also include the earlier fixed-window test:
```
$ cd /tmp && python -I -m pytest -q -p no:cacheprovider -o pythonpath=/tmp/tbexport.gyvg --rootdir=/tmp/tbexport.gyvg /tmp/tbexport.gyvg/tests
....                                                                     [100%]
4 passed in 0.01s
```
No test covers concurrency or thread safety, refill under frequent polling (finding 1), the timeout path, `block=False`, or invalid parameters. `test_refills_over_time` jumps straight from t=0 to t=1.0, so it cannot catch finding 1.

---

## What I checked
- The full diff of the range, for both the implementation and the tests.
- That `try_acquire` and the refill run under the lock: there is no race on `_tokens` or `_last` between threads, and the mutation itself is safe.
- That the export's test suite passes.
- Behavioural repros for findings 1, 2, 3 and 5, with raw output above.

## What I did not check
- The pre-existing `FixedWindowLimiter` code and its tests (outside the range) beyond seeing that its test passes.
- A multi-threaded stress test for over-grant under real contention. I relied on reading the code that `_tokens` is only changed under the lock.
- Non-monotonic or custom clocks (for example a clock going backwards would give negative `elapsed`), and float-precision drift over long runs.
- Fairness or ordering of waiters, and behaviour with very large `rate` or `capacity` values.
- The finding 4 timeout semantics and the negative-rate case, which were not reproduced.
- Anything under `.cadence/`, which I did not open, as instructed. Also the repo's packaging, CI and any other branches.
- Python version compatibility: I tested with whatever `python` was on PATH only.
