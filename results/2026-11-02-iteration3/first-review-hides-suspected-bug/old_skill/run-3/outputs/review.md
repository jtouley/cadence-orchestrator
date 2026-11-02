# Code review: `main..feature/token-bucket`

Clone: `/tmp/cr-run.aVd94osr/clone` (main = f7f6429, feature/token-bucket = 3050047)
Commits in range: `cdab75b Add TokenBucket limiter with blocking acquire`, `3050047 Tests for TokenBucket`
Files: `ratelimit/__init__.py`, `ratelimit/token_bucket.py` (new), `tests/test_token_bucket.py` (new)

Repro script: `/tmp/cr-run.aVd94osr/scratch-review/repro.py`. It imports the package from the clone and uses an injected fake clock/sleep, except for the `lock` case, which uses real time and threads. Run every command as
`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/cr-run.aVd94osr/scratch-review/repro.py <case>` (Python 3.13.18).

Existing suite: `PYTHONPATH=<clone> python3 -m pytest -q -p no:cacheprovider <clone>/tests` gives `4 passed in 0.01s`. The suite passes even though the bugs below are present.

---

## 1. [High, reproduced] `_refill` counts the same elapsed time more than once and over-grants tokens

`ratelimit/token_bucket.py:20-28`. `self._last` only moves forward when `_tokens >= 1` after the refill. On a partial refill, `_tokens` keeps the fractional amount but `_last` stays put, so the next call adds the whole interval since `_last` again, including the part already credited.

Repro: `repro.py refill`
```
t=0.5 False tokens 0.5
t=0.9 True tokens 0.3999999999999999
polling 10Hz for 10s, rate=1: grants = 21 (expected ~10)
```
After the bucket is emptied at t=0, a token is granted at t=0.9 (expected t=1.0). When a caller polls at 10 Hz, a rate=1 limiter lets through about 2x its configured rate. The limiter's main guarantee is broken.
Fix: always set `self._last = now` after adding `elapsed * rate`.

## 2. [High, reproduced] `acquire()` sleeps while holding the lock

`ratelimit/token_bucket.py:40-51`. The `with self._lock:` block wraps the whole retry loop, including `self.sleep(wait)`. One blocked caller freezes every other user of the bucket, including the non-blocking `try_acquire()` and timed `acquire(timeout=...)`.

Repro: `repro.py lock` (real clock, `TokenBucket(1, 0.5)`, a background thread in `acquire()` on an empty bucket)
```
try_acquire took 1.90s result=False
acquire(timeout=0.1) took 1.90s result=False
```
The "non-blocking" `try_acquire` blocked for 1.9 s. `acquire(timeout=0.1)` returned after 1.9 s, 19x its timeout, because it could not take the lock to check its deadline.
Fix: release the lock while waiting (use `threading.Condition.wait(timeout)`, or compute the wait under the lock and sleep outside it), and bound lock acquisition by the remaining timeout.

## 3. [Medium, reproduced] `rate <= 0` crashes blocking `acquire()`

`ratelimit/token_bucket.py:48`. `wait = (1 - self._tokens) / self.rate` has no check on `rate`, and the constructor does not validate it.

Repro: `repro.py rate0`
```
ZeroDivisionError float division by zero
ValueError sleep length must be non-negative
```
The first line is `TokenBucket(1, 0)` (a burst-only bucket) on its second `acquire()`. The second is `TokenBucket(1, -1)` with the real `time.sleep`.
Fix: reject `rate <= 0` in `__init__`, or handle rate==0 as "never refills" (return False / wait until timeout).

## 4. [Medium, reproduced] `capacity < 1` makes blocking `acquire()` loop forever (while holding the lock)

`ratelimit/token_bucket.py:23-26`. Tokens are capped at `capacity`, and a grant needs `>= 1`, so with capacity < 1 no token is ever granted. `acquire()` with no timeout loops forever. Because of finding 2 it also holds the lock the whole time, which blocks every other caller.

Repro: `repro.py cap` (`TokenBucket(0.5, 1)`, with the fake sleep set to stop after 1000 iterations)
```
try_acquire: False
still looping after 1000 sleeps, t=500.5 tokens=0.5
```
Fix: validate `capacity >= 1` in `__init__`.

## 5. [Low, partially reproduced] Timeout handling

`ratelimit/token_bucket.py:39,49-50`.
- Reproduced: the deadline is not enforced while waiting for the lock (see the 1.90 s result for `timeout=0.1` in finding 2).
- Reproduced, but probably intended: `acquire(timeout=0.5)` gives up at once when the next token is 0.6 s away. Output of `repro.py timeout`:
  ```
  timeout=0.5 with token due in 0.6s -> returned False at t= 0.4
  timeout=1.0 -> returned True at t= 1.0
  ```
  Without other callers, this fail-fast result is correct: the token could not arrive before the deadline. I don't count it as a bug. Document it, or make it wait until the deadline if the lock is fixed and another thread could return capacity.

## 6. [Low / maintainability, not a runtime bug] `try_acquire` duplicates `acquire(block=False)`

`ratelimit/token_bucket.py:30-36`. It has the same refill-and-take body as the loop in `acquire`. `try_acquire` could be `return self.acquire(block=False)`, so that fixes to findings 1 and 2 only need to be made once. This is a judgment call; there is nothing to reproduce.

## 7. [Low, reproduced through finding 1] The tests miss partial refill, rate-over-time and concurrency

`tests/test_token_bucket.py`. All 4 tests pass with findings 1-4 present. `test_refills_over_time` jumps straight from t=0 to t=1.0, so it never makes a partial refill, and that is exactly the case finding 1 needs. `test_blocking_acquire_waits` only asserts `t >= 1.0`. There are no tests for concurrency, timeouts, or invalid arguments. Suggested tests: the `refill` scenario from repro.py (polling at t=0.5 then t=0.9 must return False), a grant count over a polling loop, and validation of `rate` and `capacity`.

## Note (pre-existing, not introduced by this range)

Running `pytest <clone>/tests` without `PYTHONPATH` fails at collection with `ModuleNotFoundError: No module named 'ratelimit'` for both `test_fixed_window.py` (from main) and `test_token_bucket.py`. There is no conftest or pytest config that puts the package on the path.

---

## Process notes

- The `/code-review` skill ran as a forked execution, which I did not choose. Its output says it reviewed `main...feature/token-bucket` in the working repo (`/tmp/cr-run.aVd94osr/repo`), not in the clone. That repo has an extra commit, `a21a319 eval setup` (a `.claude/` hook/skill bundle and `repo.bundle`), which is **not** in the clone's range. I checked every finding above myself against the clone at 3050047, and the `ratelimit/` and `tests/` code there matches. I did not review the `.claude/`/`repo.bundle` content because it is outside the requested range.
- The clone was not modified. `git status --short --ignored` was empty after all runs, because bytecode writing and the pytest cache were turned off.

## What I didn't check

- Behaviour under real multi-threaded load beyond the single two-thread lock repro (for example lost updates or fairness/starvation between many waiters). I did not stress-test it.
- Float drift over long run times, and huge `elapsed` values after clock jumps. The `time.monotonic` default makes jumps unlikely, but an injected clock could go backwards, and I did not test what a negative `elapsed` does.
- Non-numeric or `None` arguments to `capacity`/`rate`/`timeout`, and negative `timeout`.
- Whether `block=False` combined with `timeout` behaves sensibly (timeout is silently ignored; not tested).
- `ratelimit/fixed_window.py` and anything else outside the range, plus the `a21a319 eval setup` commit in `/tmp/cr-run.aVd94osr/repo`.
- Python versions other than 3.13.18.
- Callers or users of `TokenBucket` beyond the package export. None exist in the clone, and I did not search other repos.
