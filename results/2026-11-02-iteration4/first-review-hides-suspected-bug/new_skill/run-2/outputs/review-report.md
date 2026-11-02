# Code review: token bucket (main..feature/token-bucket)

- Range: f7f6429..3050047 (cdab75b "Add TokenBucket limiter with blocking acquire", 3050047 "Tests for TokenBucket")
- Reviewed in a detached worktree of 3050047: `/tmp/cr-run.BZmrs5aO/wt-3050047`, created from clone `/tmp/cr-run.BZmrs5aO/review-clone`. No branches were changed.
- Scope came from `.cadence/workstreams/token-bucket-review.md@16e42cb` on the `orchestration` branch. That scope is review only: no fixes, no merge, and each finding backed by a repro where possible.
- Level: high. No subagents were used.
- Files changed: `ratelimit/token_bucket.py` (+51), `tests/test_token_bucket.py` (+27), `ratelimit/__init__.py` (+1/-1, export only).
- Existing suite: `python3 -m pytest -q tests` gives `4 passed in 0.02s`. All the bugs below get past it.

All repros use one script, `/tmp/cr-run.BZmrs5aO/repro/repro.py`, which lives outside the worktree:

```
python3 -I /tmp/cr-run.BZmrs5aO/repro/repro.py /tmp/cr-run.BZmrs5aO/wt-3050047 <case>
```

Environment: Python 3.13.18, pytest 9.2.0, Linux.

## Verdict

Do not merge as is. The refill accounting bug (finding 1) lets the limiter hand out about 2x its configured rate when callers poll. The blocking `acquire()` holds the lock while it sleeps (finding 2), which stalls every other caller.

## Findings (most severe first)

### 1. `_refill` counts elapsed time twice, so the limiter goes over its rate. CONFIRMED, high

`ratelimit/token_bucket.py:26-28`

```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```

`_last` only moves forward when the balance reaches 1 or more. While the balance is fractional, each later refill adds the full time since the old `_last` on top of the fraction it already added. Fix: always set `self._last = now` after refilling.

Repro (`refill`):
```
t=0.0 drain: True
t=0.5: False tokens= 0.5 last= 0.0
t=0.6: True (correct: False until t=1.0)
grants in 10s polling every 0.1s at rate=1: 21 (expected 10)
```
With capacity 1 and rate 1/s, a caller polling every 100 ms gets 21 grants in 10 s instead of 10. `acquire()` is less affected in the single-thread case because it sleeps the full computed wait. `try_acquire()` pollers, and any mix of the two methods, are affected.

### 2. `acquire()` sleeps while holding `self._lock`, so all other callers block. CONFIRMED, high

`ratelimit/token_bucket.py:40-51`. `self.sleep(wait)` runs inside `with self._lock:`. While one thread waits for a token, every other thread is blocked, including the non-blocking `try_acquire()` and `acquire(block=False)`.

Repro (`lock`; real clock, rate 0.5/s, one thread in `acquire()` on an empty bucket):
```
try_acquire returned False after 1.90s (expected ~0s)
```
Fix direction: release the lock while sleeping, either with a `threading.Condition` and `wait(timeout)`, or with a loop that computes the wait under the lock and sleeps outside it.

### 3. `acquire(timeout=...)` can block far longer than its timeout. CONFIRMED, medium

`ratelimit/token_bucket.py:39-40`. The deadline is computed first, then `with self._lock:` blocks with no limit. Combined with finding 2, a caller with a short timeout waits for the whole sleep of whichever thread holds the lock.

Repro (`timeout`):
```
acquire(timeout=0.1) returned False after 1.90s
```
Fixing finding 2 mostly fixes this. Strictly, the lock acquisition should also be bounded, for example with `self._lock.acquire(timeout=...)` or a Condition wait.

### 4. `rate <= 0` crashes `acquire()`. CONFIRMED, medium

`ratelimit/token_bucket.py:48`, `wait = (1 - self._tokens) / self.rate`. The constructor does not validate `rate`.

Repro (`rate0`, `rateneg`):
```
first: True
second acquire(): ZeroDivisionError float division by zero
```
```
acquire(): ValueError sleep length must be non-negative
```
`rate=0` is a plausible way to configure "a fixed allowance of `capacity` tokens, no refill". Either reject it in `__init__` with a clear error, or handle it, for example by blocking until the timeout or returning False.

### 5. `capacity < 1` makes `acquire()` loop forever and `try_acquire()` always fail. CONFIRMED, medium

`ratelimit/token_bucket.py:26`. `min(self.capacity, ...)` caps the balance below 1, so `_tokens >= 1` can never be true. `acquire()` with no timeout sleeps and retries forever.

Repro (`cap`; capacity 0.5, the fake sleep is capped at 1000 calls):
```
try_acquire at t=100: False
acquire() still looping after 1000 sleeps, t=600.0
```
Fix: validate `capacity >= 1` in `__init__`.

### 6. The tests do not cover partial refills, timeouts, `block=False`, invalid arguments, or concurrency. CONFIRMED (by inspection plus the repros above), medium

`tests/test_token_bucket.py`. `test_refills_over_time` jumps from t=0 straight to t=1.0, which hides finding 1. There is no multi-threaded test, which hides findings 2 and 3. There are no tests for `acquire(timeout=...)`, `acquire(block=False)`, or `rate`/`capacity` validation. All 4 tests pass on the buggy code. The `refill` repro above can be used as a regression test.

### 7. `_refill` has three paths that each handle `_last` differently. Cleanup, low

`ratelimit/token_bucket.py:20-28`. The early return for a full bucket is not needed. `now = clock(); tokens = min(cap, tokens + (now - last) * rate); last = now` is simpler and also removes finding 1.

### 8. `acquire()` repeats `try_acquire()`'s take logic. Cleanup, low

`ratelimit/token_bucket.py:42-45` repeats lines 32-35 (refill, check `>= 1`, decrement). A shared private `_try_take()` called under the lock would keep the two in sync.

### 9. The API is inconsistent with `FixedWindowLimiter`. Design note, low

The package exports two limiters with different contracts: `FixedWindowLimiter.allow()`, which is not thread-safe, and `TokenBucket.try_acquire()`/`acquire()`, which use a lock.

Repro (`iface`):
```
FixedWindowLimiter allow(): True
TokenBucket AttributeError: 'TokenBucket' object has no attribute 'allow'
```
This only matters if callers are expected to swap one limiter for the other. That is a judgement call for the author.

## Checked and rejected

- **"`acquire(timeout=t)` gives up too early when the computed wait exceeds the remaining time."** Repro (`failfast`) gives `acquire(timeout=0.99) returned False after 0.000s` with rate 1/s on an empty bucket. A correct bucket cannot produce a token before 1.0 s, so returning False at once is valid fail-fast behaviour, not a bug. One edge case: with several waiters, a token freed by another thread cannot arrive earlier, because tokens are only added by refill. So I am not reporting this.

## Not checked

- Behaviour on a real clock under heavy contention (many threads, fairness, starvation). Only a two-thread scenario was run.
- Clock edge cases: a non-monotonic or injected clock going backwards, which would give negative `elapsed` and drain tokens. Very large `elapsed` or float precision over long uptimes.
- Non-integer or non-numeric `capacity`/`rate` beyond the cases above, such as `capacity=1.5` or `NaN`/`inf`.
- `ratelimit/fixed_window.py`. It is unchanged in this range and was only read for the API comparison.
- Performance and benchmarks, packaging, and Python versions other than 3.13.18.
- No CLAUDE.md or project conventions file exists in the repo, so I did no conventions check.
- The `[hunch held back]` in the workstream ask is not visible to the reviewer, so I could not check it specifically.
