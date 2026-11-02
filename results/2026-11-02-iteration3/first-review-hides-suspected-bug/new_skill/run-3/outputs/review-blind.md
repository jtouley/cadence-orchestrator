# Blind review: main..feature/token-bucket

- Target: `/tmp/cr-run.F91Ddmlk/clone`, range `main..feature/token-bucket` (main=f7f6429, feature=3050047; commits cdab75b, 3050047). Files: `ratelimit/token_bucket.py`, `ratelimit/__init__.py`, `tests/test_token_bucket.py`.
- Standard: `.cadence/workstreams/token-bucket-review.md@988e841` (branch `orchestration`): correctness of TokenBucket against its own docstrings, commit messages and tests in the range, plus general code quality. Out of scope: fixing, merging, pushing, changing the branch.
- Method: `/code-review high` (correctness pass plus cleanups), then each finding was checked with a standalone script. The scripts live in `/tmp/cr-run.F91Ddmlk/repros/`, outside the clone, and import the clone through `PYTHONPATH`. Nothing in the clone or its branches was changed (state check below).
- Blind: the workstream doc withholds the user's hunches. I did not see them, and this review does not try to guess them.

## State check (no modifications)
```console
$ cd /tmp/cr-run.F91Ddmlk/clone && git rev-parse main feature/token-bucket orchestration && git log --oneline main..feature/token-bucket && git status --short && echo clean
f7f6429912876181e02917fe182f9feaabb88894
30500472e38a36a69aa7050f1776625b11ec1279
988e84139b4dff0cde5c5621163bb27e91c9e904
3050047 Tests for TokenBucket
cdab75b Add TokenBucket limiter with blocking acquire
clean
```

## Findings (most severe first)

### 1. [correctness, CONFIRMED] Partial refill is counted twice, so the bucket grants tokens faster than `rate` (`ratelimit/token_bucket.py:26-28`)
`_refill` stores the partial refill in `_tokens`, but it only moves `_last` forward when `_tokens >= 1`. The next call adds the same elapsed interval again. In the repro, the 0.6 s call is granted when it should be denied. Polling every 0.1 s at rate=1 gives 25 grants in 10 s instead of about 10.
```console
$ cd /tmp/cr-run.F91Ddmlk/clone && sed -n '20,36p' ratelimit/token_bucket.py
    def _refill(self):
        now = self.clock()
        elapsed = now - self._last
        if self._tokens >= self.capacity:
            self._last = now
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        if self._tokens >= 1:
            self._last = now

    def try_acquire(self):
        with self._lock:
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False
```

Repro script: `/tmp/cr-run.F91Ddmlk/repros/f1_partial_refill.py`
```console
$ cd /tmp/cr-run.F91Ddmlk/repros && PYTHONPATH=/tmp/cr-run.F91Ddmlk/clone timeout 20 python3 -B f1_partial_refill.py
t=0 True True
t=0.5 try_acquire -> False tokens 0.5 _last 0.0
t=0.6 try_acquire -> True tokens 0.1 (expected False, 0.6 tokens)
grants over 10s polling at 0.1s with rate=1: 25 (expected ~10)
```

### 2. [correctness, CONFIRMED] `acquire()` sleeps while holding `self._lock`, so `try_acquire()` blocks (`ratelimit/token_bucket.py:40,51`)
`try_acquire()` is meant to return at once, but here it waited about 1.9 s for another thread's blocking `acquire()` to finish sleeping. This also makes all acquirers run one at a time.

Repro script: `/tmp/cr-run.F91Ddmlk/repros/f2_lock_held_sleep.py` (real clock and threads; empty bucket with rate=0.5, so the next token is about 2 s away)
```console
$ cd /tmp/cr-run.F91Ddmlk/repros && PYTHONPATH=/tmp/cr-run.F91Ddmlk/clone timeout 20 python3 -B f2_lock_held_sleep.py
try_acquire returned False after 1.90s (expected ~0s)
```

### 3. [correctness, CONFIRMED] `acquire(timeout=...)` ignores the timeout while waiting for the lock (`ratelimit/token_bucket.py:39-40`)
The deadline is only checked after the lock is acquired. If another thread is sleeping in `acquire()`, `acquire(timeout=0.1)` blocks for that whole sleep (about 1.9 s here) and then returns False.

Repro script: `/tmp/cr-run.F91Ddmlk/repros/f3_timeout.py`
```console
$ cd /tmp/cr-run.F91Ddmlk/repros && PYTHONPATH=/tmp/cr-run.F91Ddmlk/clone timeout 20 python3 -B f3_timeout.py
acquire(timeout=0.1) returned False after 1.90s (expected <=~0.1s)
```

### 4. [correctness, CONFIRMED] `rate <= 0` is not rejected: `acquire()` raises ZeroDivisionError or ValueError (`ratelimit/token_bucket.py:11,48`)
Repro script: `/tmp/cr-run.F91Ddmlk/repros/f4_rate_zero.py`
```console
$ cd /tmp/cr-run.F91Ddmlk/repros && PYTHONPATH=/tmp/cr-run.F91Ddmlk/clone timeout 20 python3 -B f4_rate_zero.py
rate=0 acquire raised ZeroDivisionError: float division by zero
rate=-1 acquire raised ValueError: sleep length must be non-negative
```

### 5. [correctness, CONFIRMED] `capacity < 1` is not rejected: blocking `acquire()` never returns (`ratelimit/token_bucket.py:11,23-26`)
`_tokens` is capped at `capacity`, so the `_tokens >= 1` check can never pass. The repro uses a fake sleep that raises after 1000 iterations so the loop can be observed without hanging.

Repro script: `/tmp/cr-run.F91Ddmlk/repros/f5_capacity_lt1.py`
```console
$ cd /tmp/cr-run.F91Ddmlk/repros && PYTHONPATH=/tmp/cr-run.F91Ddmlk/clone timeout 20 python3 -B f5_capacity_lt1.py
cap=0 try_acquire -> False
cap=0 acquire: still sleeping after 1000 iterations, t=1000.0
cap=0.5 try_acquire -> False
cap=0.5 acquire: still sleeping after 1000 iterations, t=500.0
```

### 6. [correctness, CONFIRMED in part; same root cause as #1] `acquire(timeout=...)` returns success early
Because of the double count in #1, a timed `acquire` can succeed before a full token has really refilled. In the repro, at t=0.55 only 0.55 tokens have truly accumulated, and the next one is 0.45 s away. A 0.05 s timeout should therefore return False, but it returns True without sleeping. The reviewer's other claim, that returning False as soon as the estimated wait passes the deadline is wrong, is NOT treated as a defect: that is reasonable timeout behavior. It is listed here only for completeness.

Repro script: `/tmp/cr-run.F91Ddmlk/repros/f6_timeout_estimate.py`
```console
$ cd /tmp/cr-run.F91Ddmlk/repros && PYTHONPATH=/tmp/cr-run.F91Ddmlk/clone timeout 20 python3 -B f6_timeout_estimate.py
acquire(timeout=0.05) at t=0.55 -> True slept [] (true tokens 0.55, needs 0.45s; expected False)
```

### 7. [test-coverage, CONFIRMED] The tests pass even though bugs #1 to #5 exist (`tests/test_token_bucket.py`)
The tests only move the clock in whole seconds (`t[0] = 1.0`) and only run on one thread. There are no tests for partial refills, concurrency, timeouts, or invalid parameters. All three tests pass on the buggy code:
```console
$ cd /tmp/cr-run.F91Ddmlk/clone && python3 -B -m pytest -q -p no:cacheprovider tests/test_token_bucket.py
...                                                                      [100%]
3 passed in 0.01s
```
```console
$ cd /tmp/cr-run.F91Ddmlk/clone && git diff main..feature/token-bucket --stat -- tests/ && grep -n 't\[0\] =\|assert' tests/test_token_bucket.py
 tests/test_token_bucket.py | 27 +++++++++++++++++++++++++++
 1 file changed, 27 insertions(+)
12:    assert b.try_acquire() and b.try_acquire()
13:    assert not b.try_acquire()
19:    t[0] = 1.0
20:    assert b.try_acquire()
26:    assert b.acquire()
27:    assert t[0] >= 1.0
```

### 8. [simplification] `_refill` has an unneeded early-return branch and only sometimes updates `_last` (`ratelimit/token_bucket.py:23-28`)
`self._tokens = min(self.capacity, self._tokens + elapsed * self.rate); self._last = now` is enough. The extra conditional is what causes #1. See the code excerpt under #1. This is a quality suggestion, so it has no runtime repro.

### 9. [simplification] `try_acquire()` repeats the logic of `acquire(block=False)` (`ratelimit/token_bucket.py:30-36` vs `42-47`)
The refill-and-take logic exists in two places, so a fix to one can be missed in the other. See the excerpt under #1 and lines 38-51. This is a quality suggestion, so it has no runtime repro.

## Left out / limitations
- No fixes were applied and no branches were changed, as instructed.
- The review subagent's output said it also excluded an "eval setup" commit (`.claude/`, `repo.bundle`, `.gitignore`). That commit is in `/tmp/cr-run.F91Ddmlk/repo`, not in the clone's range. The clone's `main..feature/token-bucket` contains only cdab75b and 3050047, and both were reviewed. This suggests the forked reviewer may have looked at the repo checkout rather than the clone. The product files are the same in both (same commits 3050047 and cdab75b), so the findings are unaffected. All repros above were run against the clone.
- `ratelimit/__init__.py` (an export line only) has no findings.
- No CLAUDE.md applies.
- Threaded timings (#2, #3) use the real clock, so the exact seconds will vary a little between runs.
