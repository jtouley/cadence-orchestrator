# Suspicion check: TokenBucket (clone at 3050047)

Clone: /tmp/cr-run.sgCR8FiU/review-clone, HEAD `30500472e38a36a69aa7050f1776625b11ec1279`, `git status --short` output: `?? ratelimit/__pycache__/`.
Code under test: `ratelimit/token_bucket.py` (`_refill` lines 20-28, `acquire` lines 38-51).
Only the two claims below were judged. No fixes made, no subagents used.

## Verdicts

### (1) "the refill clock drifts when the bucket is empty, the way _last only gets bumped once there's a whole token looks wrong" -- CONFIRMED (with a correction on direction)

The mechanism is real. When the bucket is below capacity and the refill leaves it under 1 token, `_refill` adds `elapsed * rate` to `_tokens` but leaves `_last` unchanged (line 27-28). The next call measures `elapsed` from the same old `_last`, so the same time period gets added again.
The result is over-refill, not a lagging clock: tokens build up too fast.
- Drained at t=0 with rate=1/s: t=0.5 gives tokens=0.50 and `_last` stays 0.0. Then t=0.9 gives 0.5+0.9=1.4, so the acquire **succeeds at t=0.9**. It should not succeed before t=1.0.
- Polling every 0.1s for 10s after a drain gave **25 grants where about 10 were expected**, which is 2.5x the configured rate.
The overshoot gets bigger the more often callers poll while the bucket is under 1 token. Callers that rarely poll see little effect.

### (2) "the lock is held across the sleep in acquire(), which would stall every other thread" -- CONFIRMED

`acquire` calls `self.sleep(wait)` inside `with self._lock:` (lines 40-51). The repro injects a sleep that parks thread A. While A is in that sleep, `_lock.locked()` is True. Thread B's non-blocking `try_acquire()` did not return within 1.0s. It returned only after A's sleep was released, after waiting 1.00s.
So any thread calling `try_acquire`/`acquire` is serialized behind a sleeping `acquire`, including callers that pass `block=False`.

## Script

Path: `/tmp/cr-run.sgCR8FiU/scripts/suspicion_repro.py` (outside the clone)

```python
"""Repro for two suspicions about ratelimit.TokenBucket. Usage: python3 -I suspicion_repro.py <clone_path>"""
import sys, threading, time
sys.path.insert(0, sys.argv[1])
from ratelimit import TokenBucket

print("=== Claim 1: _last not bumped while tokens < 1 ===")
t = [0.0]
b = TokenBucket(2, 1.0, clock=lambda: t[0], sleep=lambda s: None)
assert b.try_acquire() and b.try_acquire()
print(f"t=0.0 drained, tokens={b._tokens}, _last={b._last}")
for now in (0.5, 0.9):
    t[0] = now
    ok = b.try_acquire()
    print(f"t={now}: try_acquire -> {ok}; tokens={b._tokens:.2f}, _last={b._last}")
print("Correct behaviour at rate=1/s: at t=0.9 only 0.9 tokens should exist -> try_acquire should be False")

# Count grants over 10 s of polling every 0.1 s after draining
t[0] = 0.0
b = TokenBucket(2, 1.0, clock=lambda: t[0], sleep=lambda s: None)
b.try_acquire(); b.try_acquire()
grants = 0
for i in range(1, 101):
    t[0] = i * 0.1
    grants += b.try_acquire()
print(f"Polling every 0.1s for 10s after drain: {grants} grants (expected ~10 at rate=1/s)")

print()
print("=== Claim 2: lock held across sleep in acquire() ===")
in_sleep = threading.Event()
release = threading.Event()
def fake_sleep(s):
    in_sleep.set()
    release.wait(5)          # hold the "sleep" until main thread lets go
b = TokenBucket(1, 1.0, clock=time.monotonic, sleep=fake_sleep)
b.try_acquire()              # drain
a = threading.Thread(target=b.acquire)
a.start()
in_sleep.wait(5)
print("thread A is inside sleep(); lock.locked() =", b._lock.locked())
res = {}
def other():
    t0 = time.monotonic(); res['r'] = b.try_acquire(); res['dt'] = time.monotonic() - t0
c = threading.Thread(target=other); c.start()
c.join(1.0)
print("thread B try_acquire() finished within 1.0s while A sleeps:", not c.is_alive())
release.set(); a.join(5); c.join(5)
print(f"thread B try_acquire() returned {res.get('r')} after {res.get('dt'):.2f}s (only after A's sleep was released)")
```

## Command

```
cd /tmp && python3 -I /tmp/cr-run.sgCR8FiU/scripts/suspicion_repro.py /tmp/cr-run.sgCR8FiU/review-clone
```

## Raw output

```
=== Claim 1: _last not bumped while tokens < 1 ===
t=0.0 drained, tokens=0.0, _last=0.0
t=0.5: try_acquire -> False; tokens=0.50, _last=0.0
t=0.9: try_acquire -> True; tokens=0.40, _last=0.9
Correct behaviour at rate=1/s: at t=0.9 only 0.9 tokens should exist -> try_acquire should be False
Polling every 0.1s for 10s after drain: 25 grants (expected ~10 at rate=1/s)

=== Claim 2: lock held across sleep in acquire() ===
thread A is inside sleep(); lock.locked() = True
thread B try_acquire() finished within 1.0s while A sleeps: False
thread B try_acquire() returned False after 1.00s (only after A's sleep was released)
```

## Not checked

- No other defects in TokenBucket were looked at. Examples: deadline/timeout handling, `timeout` ignored when `block=False`, rate<=0 or capacity<1 inputs, float precision. This check covered only the two claims.
- Claim 2 was shown with an injected sleep and a 1s observation window, not with the real `time.sleep` under load. It shows the lock is held during sleep. It does not measure throughput impact in production.
- Claim 1 was measured with an injected fake clock only, at one capacity/rate setting (2, 1.0/s) and one polling interval (0.1s).
- `fixed_window.py` and the existing test suite were not run or reviewed.
- Python version: Python 3.13.18.
