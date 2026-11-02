# Repro re-run: review-1 scripts against 3050047

- Clone: /tmp/cr-run.TPbqLc2I/clone at 30500472e38a36a69aa7050f1776625b11ec1279. Tracked files are clean (`git status --porcelain --untracked-files=no` prints nothing). The only untracked entries are `ratelimit/__pycache__/` and `tests/__pycache__/`, which were there before this re-run and are still there after it.
- Python 3.13.18.
- I read the scripts in /tmp/cr-run.TPbqLc2I/scripts/ (r1_doublecount.py, r2_lock_sleep.py, r4_rate0.py, r5_cap_lt1.py, r6_timeout_early.py) before running them. Each one only adds the clone to `sys.path`, imports `ratelimit`, and calls `TokenBucket` methods. None of them open, write or delete files, or run git or subprocesses. The scripts and the code were not edited.

```
$ python3 -I /tmp/cr-run.TPbqLc2I/scripts/r1_doublecount.py /tmp/cr-run.TPbqLc2I/clone
t=0.5 False tokens= 0.5 _last= 0.0
t=0.6 True tokens= 0.10000000000000009 _last= 0.6
grants over 10s polling every 0.1s at rate=1: 21
(exit=0)

$ python3 -I /tmp/cr-run.TPbqLc2I/scripts/r2_lock_sleep.py /tmp/cr-run.TPbqLc2I/clone
try_acquire (non-blocking) returned False after 1.90s
acquire(timeout=0.2) returned False after 1.90s
(exit=0)

$ python3 -I /tmp/cr-run.TPbqLc2I/scripts/r4_rate0.py /tmp/cr-run.TPbqLc2I/clone
rate=0: ZeroDivisionError float division by zero
rate=-1: ValueError sleep length must be non-negative
(exit=0)

$ python3 -I /tmp/cr-run.TPbqLc2I/scripts/r5_cap_lt1.py /tmp/cr-run.TPbqLc2I/clone
still waiting after 1000 sleeps, simulated t=500.0s, tokens=0.5
(exit=1)

$ python3 -I /tmp/cr-run.TPbqLc2I/scripts/r6_timeout_early.py /tmp/cr-run.TPbqLc2I/clone
acquire(timeout=0.99) -> False after 0.000s
(exit=0)

$ cd /tmp/cr-run.TPbqLc2I/clone && python3 -m pytest -q -p no:cacheprovider tests/test_token_bucket.py
...                                                                      [100%]
3 passed in 0.00s
(exit=0)
```

## Differences from outputs/review-1.md

- pytest timing: `3 passed in 0.00s` now, `3 passed in 0.01s` in review-1.md. This is run-to-run timing noise.
- All other output matches review-1.md exactly, including the real-clock values in r2 (1.90s) and r6 (0.000s), and r5's exit code 1.
