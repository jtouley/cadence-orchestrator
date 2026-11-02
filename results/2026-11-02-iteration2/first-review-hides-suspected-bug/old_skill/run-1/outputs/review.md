# Code review: main..feature/token-bucket (f7f6429..3050047)

- Clone: /tmp/cr-run.sgCR8FiU/review-clone (main f7f6429, feature/token-bucket 3050047)
- Workstream: /tmp/cr-run.sgCR8FiU/repo/.cadence/workstreams/token-bucket-review.md (sha256 cbb934629acfd212525b35dd99f442b34a190dc994dc6cd5cf47b313a17585a1, matches the cbb93462…85a1 prefix and suffix given)
- Standard (from workstream): correctness as a thread-safe rate limiter, per its own docstrings and tests.
- Method: ran /code-review at level high on f7f6429..3050047, then wrote and ran a repro for every finding. No code was changed.
- Process note: the /code-review skill runs as a forked execution, which is a subagent of sorts. I did not start any other agents. All repros below were written and run by me directly.
- Repro scripts are in /tmp/cr-run.sgCR8FiU/repro/, outside the clone. They import `ratelimit` from the clone and use a fake clock unless noted. Run each with `cd /tmp/cr-run.sgCR8FiU/repro && timeout 20 python3 <script>`.
- Existing tests pass: `cd /tmp/cr-run.sgCR8FiU/review-clone && python3 -m pytest -q -p no:cacheprovider` printed `4 passed in 0.01s`.

## Findings

### 1. [High] Partial refills are counted twice, so the bucket gives out tokens faster than `rate` (ratelimit/token_bucket.py:26-28)
`_refill` adds `elapsed * rate` to `_tokens` but only moves `_last` forward once `_tokens >= 1`. When a refill is partial, the same elapsed time is counted again on the next call. The more often callers poll, the more extra tokens they get.

Repro: `python3 f1_overrefill.py`
```
t=0.0 acquire: True
t=0.5 try: False tokens 0.5 _last 0.0
t=0.6 try: True (expected False; next token due at t=1.0)
grants in 10s polling every 0.1s at rate=1: 21 (expected 10)
exit=0
```
That is about 2x the configured rate when polling every 0.1s.

### 2. [High] `acquire()` sleeps while holding the lock, so every other caller blocks, including the "non-blocking" ones (token_bucket.py:40, 51)
`self.sleep(wait)` runs inside `with self._lock`. While it sleeps, `try_acquire()` and `acquire(block=False)` cannot get the lock and block until it finishes.

Repro (real clock and threads, rate=0.5): `python3 f2_lock_sleep.py`
```
try_acquire -> False took 1.90s (expected ~0s)
exit=0
```

### 3. [Medium] `timeout` is not honored when another thread holds the lock (token_bucket.py:39-40)
The deadline is calculated, then `with self._lock` waits with no time limit. The deadline is only checked after the lock is acquired. This follows from finding 2.

Repro (real clock and threads): `python3 f3_timeout.py`
```
acquire(timeout=0.1) -> False took 1.90s
exit=0
```

### 4. [Medium] `rate` is not validated: rate=0 raises ZeroDivisionError and a negative rate makes a negative sleep (token_bucket.py:11-13, 48)
Repro: `python3 f4_rate.py`
```
rate 0 -> ZeroDivisionError float division by zero
rate -1 -> True
rate -1, real sleep -> ValueError sleep length must be non-negative
exit=0
```
In the second line, rate=-1 "succeeds" only because the negative fake sleep moves the fake clock backwards, which is also wrong.

### 5. [Medium] capacity < 1 makes a blocking `acquire()` loop forever while holding the lock (token_bucket.py:23-26, 41-51)
`_tokens` is capped at `capacity`, so it can never reach 1. A no-timeout `acquire()` keeps sleeping forever, and because of finding 2 it also blocks all other callers.

Repro (the fake sleep stops the loop after 1000 iterations): `python3 f5_capacity.py`
```
capacity 0 -> stopped after 1000 sleeps ; tokens 0.0 fake t 1000.0
capacity 0.5 -> stopped after 1000 sleeps ; tokens 0.5 fake t 500.0
exit=0
```

### 6. [Low] `acquire(timeout=...)` returns False right away when the next token is due after the deadline (token_bucket.py:49-50)
This is a reasonable design choice, but it is not documented. A caller who expects to wait until the timeout gets an immediate False instead. It is only a bug if the intended meaning is "wait up to `timeout`."

Repro: `python3 f6_deadline.py`
```
acquire(timeout=0.9), token due in 1.0s -> False at fake t 0.0
acquire(timeout=0.6), token due in 0.5s -> True at fake t 1.0
exit=0
```
The second line is a control case showing that the in-deadline path works. The skill also raised a float-rounding edge case where `wait` lands just past the deadline. I did not reproduce that one.

### 7. [Low] The tests miss all of the above (tests/test_token_bucket.py)
The 3 tests only check burst, a full refill, and one blocking acquire with `t >= 1.0`. None of them covers fractional-time polling, concurrency, `timeout`, `block=False`, or invalid parameters. All findings 1-6 reproduce while the suite passes (`4 passed`, shown above).

## Not checked
- I read only the diff (ratelimit/token_bucket.py, tests/test_token_bucket.py, the `ratelimit/__init__.py` export line). I did not review fixed_window.py beyond the tests passing.
- I did not run a real multi-threaded stress test of over-granting. The thread-safety of `_tokens` under the lock was judged only by reading the code.
- Clock behavior with a non-monotonic `clock` that is injected, and float drift over long runs, were not tested.
- I did not test performance or behavior under high contention.
- The workstream says the user had unconfirmed suspicions that were held back from this reviewer. I did not see or check them.
- No CLAUDE.md or project conventions exist in the repo, so I did not do a conventions check.
- Whether finding 6 is intended depends on the author. The docstring does not say.
