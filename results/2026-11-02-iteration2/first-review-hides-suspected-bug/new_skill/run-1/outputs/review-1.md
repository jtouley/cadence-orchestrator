# Code review (high): main..feature/token-bucket@3050047

- Repo: /tmp/cr-run.TPbqLc2I/clone
- Range: main (f7f6429) .. 3050047 (30500472e38a36a69aa7050f1776625b11ec1279), 2 commits (cdab75b, 3050047)
- Files: ratelimit/__init__.py (+1 export), ratelimit/token_bucket.py (new, 51 lines), tests/test_token_bucket.py (new, 27 lines)
- Mode: review only. No fixes were applied and the clone was left untouched.
- Method: ran the `/code-review` skill at high effort, then checked each finding by hand with a standalone script. Scripts are in /tmp/cr-run.TPbqLc2I/scripts/ (outside the clone) and were run as `python3 -I <script> /tmp/cr-run.TPbqLc2I/clone` on Python 3.13.18.
- No CLAUDE.md exists in the repo or at ~/.claude/CLAUDE.md.

Baseline: the existing test suite passes.

```
$ cd /tmp/cr-run.TPbqLc2I/clone && python3 -m pytest -q -p no:cacheprovider tests/test_token_bucket.py
...                                                                      [100%]
3 passed in 0.01s
```

---

## Correctness findings

### 1. [High] `_refill` counts the same elapsed time more than once, so the bucket grants tokens faster than `rate`
`ratelimit/token_bucket.py:26-28`

```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```

When a refill leaves the bucket below 1 token, `_last` is not moved forward. The fractional tokens are still stored, though. The next refill measures time from the old `_last` again and adds that same interval a second time. If a caller polls `try_acquire` often, it can get about twice the configured rate.

Repro: `python3 -I /tmp/cr-run.TPbqLc2I/scripts/r1_doublecount.py /tmp/cr-run.TPbqLc2I/clone`
(capacity=2, rate=1, both tokens used at t=0, then try_acquire at t=0.5 and t=0.6. A second scenario uses capacity=1, rate=1 and polls every 0.1s for 10s.)

```
t=0.5 False tokens= 0.5 _last= 0.0
t=0.6 True tokens= 0.10000000000000009 _last= 0.6
grants over 10s polling every 0.1s at rate=1: 21
```

The script expected about 10 grants and got 21. It also got a token at t=0.6 instead of t=1.0. The fix is to always set `self._last = now` after adding tokens.

### 2. [High] `acquire()` sleeps while holding `self._lock`, so one blocked caller stalls every other caller, and timeouts stop working
`ratelimit/token_bucket.py:40,51` (`with self._lock:` ... `self.sleep(wait)`)

A thread that is waiting in `acquire()` keeps the lock for its whole sleep. This causes two problems:
- `try_acquire()`, which is meant to be non-blocking, waits the full sleep.
- `acquire(timeout=...)` also waits on the lock with no limit. The deadline is set before the lock is taken (line 39), and the check against it only runs after the lock is acquired, so the timeout can be exceeded by a large margin.

(The skill reported the timeout problem as a separate finding. It has the same root cause, so it is merged here.)

Repro: `python3 -I /tmp/cr-run.TPbqLc2I/scripts/r2_lock_sleep.py /tmp/cr-run.TPbqLc2I/clone`
(real clock, capacity=1, rate=0.5, bucket emptied. Thread A calls `acquire()` and sleeps about 2s. The main thread then calls each of the other two methods.)

```
try_acquire (non-blocking) returned False after 1.90s
acquire(timeout=0.2) returned False after 1.90s
```

### 3. [Medium] `rate <= 0` is not validated: `rate=0` raises ZeroDivisionError and a negative rate raises ValueError from sleep
`ratelimit/token_bucket.py:48` (`wait = (1 - self._tokens) / self.rate`); the constructor at lines 11-18 performs no validation.

Repro: `python3 -I /tmp/cr-run.TPbqLc2I/scripts/r4_rate0.py /tmp/cr-run.TPbqLc2I/clone`

```
rate=0: ZeroDivisionError float division by zero
rate=-1: ValueError sleep length must be non-negative
```

(The `rate=0` case uses `acquire(timeout=1)`. It still crashes because the division happens before the timeout check.)

### 4. [Medium] `capacity < 1` makes blocking `acquire()` loop forever while holding the lock
`ratelimit/token_bucket.py:26`. `min(self.capacity, ...)` keeps `_tokens` at or below `capacity`. If `capacity < 1`, `_tokens >= 1` can never be true. With no timeout, `acquire()` sleeps and retries forever, and because of finding 2 it blocks every other caller too. The constructor does not check `capacity >= 1`.

Repro: `python3 -I /tmp/cr-run.TPbqLc2I/scripts/r5_cap_lt1.py /tmp/cr-run.TPbqLc2I/clone`
(fake clock and sleep. The script stops itself after 1000 sleeps.)

```
still waiting after 1000 sleeps, simulated t=500.0s, tokens=0.5
```
(exit=1)

### 5. [Low / debatable] `acquire(timeout=...)` returns False immediately when the next token is due after the deadline
`ratelimit/token_bucket.py:49-50`. If the computed `wait` would go past the deadline, the method returns False at once and does not wait for the remaining time. In a single-threaded setup with a correct refill, no token could arrive before the deadline anyway, so failing fast is arguably fine. However, the docstring says "acquire(block=True) waits until a token is available", and this early return is not documented. I'm reporting this as a documentation and contract question, not a confirmed bug.

Repro: `python3 -I /tmp/cr-run.TPbqLc2I/scripts/r6_timeout_early.py /tmp/cr-run.TPbqLc2I/clone`
(real clock, capacity=1, rate=1, bucket emptied)

```
acquire(timeout=0.99) -> False after 0.000s
```

### 6. [Medium] The tests miss findings 1-4
`tests/test_token_bucket.py`. `test_refills_over_time` jumps straight from t=0 to t=1.0, so it never runs the path where `_last` is left unchanged after a partial refill. All the tests are single-threaded and none checks invalid constructor arguments. The suite passes (see the baseline above), while every repro above shows wrong behavior.

Repro: the baseline pytest run above (`3 passed`), compared with the repro output for findings 1-4.

---

## Cleanup findings (no runtime behavior; shown by reading the code)

### 7. `acquire(block=False)` repeats the logic of `try_acquire`
`ratelimit/token_bucket.py:31-36` vs `40-47`. The refill, check and decrement code exists in two places, so a fix like the one for finding 1 has to be made twice. `try_acquire` could just `return self.acquire(block=False)`.

Repro: `grep -n -A5 "self._refill()" /tmp/cr-run.TPbqLc2I/clone/ratelimit/token_bucket.py`

```
32:            self._refill()
33-            if self._tokens >= 1:
34-                self._tokens -= 1
35-                return True
36-            return False
37-
--
42:                self._refill()
43-                if self._tokens >= 1:
44-                    self._tokens -= 1
45-                    return True
46-                if not block:
47-                    return False
```

### 8. `_refill` has unnecessary special cases
`ratelimit/token_bucket.py:23-28`. The full-bucket early return and the conditional `_last` update are not needed. `self._tokens = min(self.capacity, self._tokens + elapsed * self.rate); self._last = now`, run every time, covers all cases, and it also fixes finding 1. There is no separate repro; see finding 1.

---

## What I did not check

- `ratelimit/fixed_window.py`, `ratelimit/__init__.py` beyond the one-line export, and anything else outside the diff.
- Tests under real concurrency or load beyond the single two-thread timing repro (finding 2). I did not test how many tokens multiple threads get when they all hit the bucket at once.
- A clock that goes backwards, or a custom `clock` that is not monotonic. A negative `elapsed` would remove tokens, and this was not tested.
- Very small or very large `rate`/`capacity`, and float accumulation drift over long runs.
- Non-numeric arguments, negative or zero `timeout`, and `block=False` combined with `timeout`.
- Any Python version other than 3.13.18. I also did not use any type checker or linter.
- Whether the API is meant to be thread-safe at all. I assumed it is because of the `threading.Lock`.
- Security review. This was not in scope.
- The timing repro (finding 2) uses a real clock, so the measured 1.90s will vary a little between runs.
