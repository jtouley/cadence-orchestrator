# Verification of outputs/review.md

## Setup

- Fresh export: `cd /tmp/cr-run.IX6cKBq7/clone && git archive 3050047 | tar -x -C /tmp/cr-run.IX6cKBq7/verify-src.YhM1` (new dir from `mktemp -d`, not the reviewer's `review-src`).
- `cmp <(git show 3050047:ratelimit/token_bucket.py) verify-src.YhM1/ratelimit/token_bucket.py` -> `export matches 3050047`.
- Export contents: `ratelimit/{__init__,fixed_window,token_bucket}.py`, `tests/{test_fixed_window,test_token_bucket}.py`.
- Python 3.13.18. All scripts run with `python3 -I` from cwd `/tmp`, with the export path as argv[1].
- Import check (same `sys.path.insert(0, argv[1])` the scripts use):
  ```
  $ python3 -I -c "import sys; sys.path.insert(0, sys.argv[1]); import ratelimit, ratelimit.token_bucket as m; print(ratelimit.__file__); print(m.__file__)" /tmp/cr-run.IX6cKBq7/verify-src.YhM1
  /tmp/cr-run.IX6cKBq7/verify-src.YhM1/ratelimit/__init__.py
  /tmp/cr-run.IX6cKBq7/verify-src.YhM1/ratelimit/token_bucket.py
  ```
- Existing suite in the export: `python3 -m pytest -q -p no:cacheprovider` -> `4 passed in 0.01s` (matches review).

Script audit, all three: each does `from ratelimit import TokenBucket` from the exported tree. None of them defines, subclasses or monkeypatches TokenBucket. The only injected pieces are `clock` and `sleep`, which are constructor parameters of the real class.

## Finding 1: refill double-counts elapsed time while tokens < 1 -> REPRODUCES

```
$ python3 -I /tmp/cr-run.IX6cKBq7/review-scripts/repro_refill.py /tmp/cr-run.IX6cKBq7/verify-src.YhM1
granted at t=0.4  (expected first grant at t=1.0)
granted at t=0.9  (expected first grant at t=1.0)
tokens granted in 1.0s: 2 (expected 1)
exit=0
```

Script audit: it uses the real class with a fake clock and a no-op sleep (`acquire` is never called). It drains at t=0, then polls `try_acquire` at t=0.1..1.0, with `round()` applied to the times. The expectation is honest: with capacity=1 and rate=1/s, a correct bucket earns at most 1 token by t=1.0. It got 2, the first at t=0.4. Float noise is not the cause. Under float arithmetic the first-cycle sum reaches 1.0000000000000002 at t=0.4, but the over-grant comes from `_last` not advancing (token_bucket.py:26-28). A boundary rounding error could not produce a grant 2.5x too early. The cause matches the code as read.

## Finding 2: acquire() sleeps while holding the lock and blocks try_acquire() -> REPRODUCES

```
$ python3 -I /tmp/cr-run.IX6cKBq7/review-scripts/repro_lock_sleep.py /tmp/cr-run.IX6cKBq7/verify-src.YhM1
try_acquire returned False after 1.90s (expected ~0.00s)
real	0m2.019s
exit=0
```

Script audit: it uses the real class with the default `time.monotonic` / `time.sleep` and a real thread. The background thread drains, then `acquire()` computes a wait of about 2 s and sleeps inside `with self._lock` (lines 40-51). The main thread's `try_acquire()` blocked for 1.90 s. The test is timing-dependent, but the only race (the thread not entering `acquire` within 0.1 s) would produce a false negative, not a false positive. Limit: the script exercises only `try_acquire()`. The review's added claims that `acquire(block=False)` and another thread's `timeout` are also stalled are consistent with the code (same lock) but were not run separately.

## Finding 3: acquire() never returns when capacity < 1 -> REPRODUCES

```
$ python3 -I /tmp/cr-run.IX6cKBq7/review-scripts/repro_edge.py /tmp/cr-run.IX6cKBq7/verify-src.YhM1
rate=0: ZeroDivisionError float division by zero
capacity=0.5: RuntimeError still looping after 1000 sleeps, t=500.5
exit=0
```

Script audit: it uses the real class with `TokenBucket(0.5, 1.0)`, a fake clock and a fake sleep that raises after 1000 calls. The cap stands in for "infinite", which is reasonable. The code confirms it: `_tokens` starts at 0.5, `_refill` returns early when `_tokens >= capacity` (line 23), so `_tokens >= 1` can never hold, and the loop sleeps 0.5 s forever. t=500.5 = 1001 x 0.5. The RuntimeError is the script's own guard, as the review says.

## Finding 4: rate=0 raises ZeroDivisionError from acquire() -> REPRODUCES

Same command and output as Finding 3 (first line: `rate=0: ZeroDivisionError float division by zero`). Script audit: it uses the real `TokenBucket(1, 0)`, drains with `try_acquire()`, then calls `acquire(block=True, timeout=1)`. The exception is raised at `wait = (1 - self._tokens) / self.rate` (line 48) before the deadline check, so the `timeout` does not prevent it. The sub-claim that negative rate/capacity are accepted has no repro (the review says "Not run"). Reading the source confirms `__init__` does no validation.

## Finding 5: tests do not cover risky paths -> no repro script (not applicable). Claim confirmed by reading the tests

There is no script for this finding, so none of the three verdicts strictly applies. I read `tests/test_token_bucket.py` in the export. It has 3 tests (`test_burst_then_empty`, `test_refills_over_time`, `test_blocking_acquire_waits`), all single-threaded with an injected fake clock and sleep. None covers polling while tokens < 1, concurrency or real sleep, `timeout`, `block=False`, or invalid parameters. `test_blocking_acquire_waits` asserts only `t[0] >= 1.0`. The claim is accurate.

## Summary

| # | Finding | Verdict |
|---|---------|---------|
| 1 | Refill over-grants when polled below 1 token | REPRODUCES |
| 2 | Lock held during sleep blocks try_acquire | REPRODUCES (only the try_acquire path was exercised) |
| 3 | capacity < 1 -> acquire loops forever | REPRODUCES |
| 4 | rate=0 -> ZeroDivisionError | REPRODUCES |
| 5 | Test coverage gaps | No repro script. Confirmed by reading the tests |

No repro is flawed and no output differs from what review.md reports. No fixes were made and nothing in the clone was modified. The only new artifact besides this file is the export dir `/tmp/cr-run.IX6cKBq7/verify-src.YhM1`.
