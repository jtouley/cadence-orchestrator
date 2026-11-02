# Review: main..feature/token-bucket (f7f6429..3050047)

- Clone: /tmp/cr-run.gpvxdOEJ/review-clone (HEAD 30500472e38a36a69aa7050f1776625b11ec1279, main f7f6429912876181e02917fe182f9feaabb88894, clean tree)
- Workstream doc: /tmp/cr-run.gpvxdOEJ/repo/.cadence/workstreams/token-bucket-review.md, sha256 e6b041251c759d343bd9f5dedd5ecd3b3f06a79b03854706d5abbbf874c8fb7b (matches the e6b04125 prefix I was given)
- Standard: correctness and thread-safety, judged against the code's own docstrings and tests
- Commits: cdab75b (TokenBucket), 3050047 (tests). Files: ratelimit/__init__.py, ratelimit/token_bucket.py, tests/test_token_bucket.py
- Repro scripts are in /tmp/cr-run.gpvxdOEJ/scratch/ (outside the clone). Each imports the clone through sys.path and runs with `python3 -I`. I made no changes to the clone.
- Existing tests: `python3 -m pytest -q` in the clone printed `4 passed in 0.01s`. The new tests pass but miss every bug below.

## Findings

### 1. HIGH: `_refill` counts the same elapsed time more than once, so it hands out up to about 2x the configured rate
ratelimit/token_bucket.py:26-28

When a refill leaves `_tokens < 1`, the code adds `elapsed * rate` to `_tokens` but leaves `_last` unchanged. The next refill measures elapsed time from the same old `_last` and adds that whole period again. Any caller that polls more often than once per token period gets extra tokens. That breaks the docstring's promise of a refill "at `rate` tokens per second".

Repro (fake clock, capacity=1, rate=1/s, one token taken at t=0):
```
$ python3 -I r1b_trace.py
t=0.5: try_acquire=False tokens_after=0.50 _last=0.0
t=0.6: try_acquire=True tokens_after=0.00 _last=0.6
```
At t=0.6 only 0.6 tokens should exist. The 0.5 from the first refill was added again (0.5 + 0.6, capped at 1), so the call succeeded.

```
$ python3 -I r1_refill.py
granted over 10s at rate=1/s: 21 (expected ~10)
```
Suggested direction (not applied): always set `self._last = now` after adding the refill.

### 2. HIGH: `acquire()` sleeps while holding the lock, so it blocks every other caller, including non-blocking ones
ratelimit/token_bucket.py:40-51 (`self.sleep(wait)` at line 51 runs inside `with self._lock`)

While one thread waits in `acquire()`, every other thread stalls for the whole wait: `try_acquire()`, `acquire(block=False)` and `acquire(timeout=...)` all block on the lock. This breaks the non-blocking contract of `try_acquire` and `block=False`, and it puts all waiters in a single queue behind the lock.

Repro (real clock, capacity=1, rate=0.5/s, bucket emptied; a background thread calls `acquire()` and the main thread then calls `try_acquire()`):
```
$ python3 -I r2_lock.py
non-blocking try_acquire returned False after 1.90s
acquire(block=False) returned False after 0.00s
```
The "non-blocking" `try_acquire` took 1.90 s. (The second line ran after the background thread had already finished, so it shows nothing.)

### 3. MEDIUM: `acquire(timeout=...)` ignores its timeout while waiting for the lock
ratelimit/token_bucket.py:39-41

This is a consequence of finding 2. The deadline is computed before `with self._lock`, and lock acquisition has no time limit, so a caller can overrun its timeout by an arbitrary amount.
```
$ python3 -I r3_timeout.py
acquire(timeout=0.2) returned False after 1.90s
```

### 4. LOW: parameters are not validated. `rate=0` crashes, and `capacity < 1` makes `acquire()` loop forever
ratelimit/token_bucket.py:11-17, 48

`rate <= 0` raises ZeroDivisionError at line 48 (a negative rate gives a negative sleep). With `capacity < 1`, `_tokens` can never reach 1, so a blocking `acquire()` with no timeout never returns.
```
$ python3 -I r4_edge.py
rate=0 acquire(): ZeroDivisionError float division by zero
capacity=0.5 acquire(): still looping after 1000 sleeps, t=500.5
exit=1
```
(The exit=1 comes from the script's own SystemExit guard, which stopped the loop.)

### 5. LOW: the tests cover none of the above
tests/test_token_bucket.py

The tests have no fine-grained polling (which would catch 1), no concurrency or lock-contention check (2, 3), no `timeout`/`block=False` coverage, and no invalid parameters (4). `test_blocking_acquire_waits` only checks `t[0] >= 1.0`, which still passes when the bucket over-grants. Evidence: `4 passed in 0.01s` on code that has findings 1-4.

## Observations (not counted as defects, UNPROVEN as bugs)
- acquire(timeout) at line 49 returns False as soon as the projected wait exceeds the deadline, without waiting until the deadline. That is a reasonable choice, but the docstring does not document it. I wrote no repro because this is behavior, not a failure.
- `_refill` at lines 23-25 resets `_last` when the bucket is full. That is correct, and I saw no issue there.

## What I did not check
- I ran no stress test with many threads beyond the single-contender repros, and did not check fairness or starvation between waiters.
- Real-clock behavior was checked with one timing run per script. Timings (1.90 s) are from this machine and are not statistically validated.
- Float-precision drift over long runs.
- ratelimit/fixed_window.py and its tests, which are outside the range (I only ran them as part of the full pytest run).
- Python versions other than the local `python3`, and packaging or import side effects beyond `__init__.py`.
- Whether `clock`/`sleep` injection is meant to be part of the public API.
