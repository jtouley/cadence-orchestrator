# Claims check: TokenBucket (main..feature/token-bucket)

Clone: `/tmp/cr-run.aVd94osr/clone` (HEAD 3050047). Code under test: `ratelimit/token_bucket.py`.
Scratch scripts: `/tmp/cr-run.aVd94osr/scratch-claims/`. The clone was not modified. My runs created `ratelimit/__pycache__/`, and I deleted it afterwards. `git status` is clean.

## Claim 1: "the refill clock drifts when the bucket is empty, the way `_last` only gets bumped once there's a whole token looks wrong"

**Verdict: CONFIRMED.** The direction needs one correction. The clock does not fall behind. The bucket double-counts elapsed time and refills too fast.

Code (`_refill`, lines 26-28):
```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```
When the result is below 1, `_tokens` keeps the fractional credit but `_last` stays where it was. The next call measures `elapsed` from that same old `_last` and adds the same time span again. Every call made while the bucket is under 1 token re-credits all the time since the last whole token. The more often callers poll, the faster tokens come back.

Repro: `python3 /tmp/cr-run.aVd94osr/scratch-claims/claim1_refill.py` (capacity=1, rate=1/s, fake clock)
```
t=0.0 try_acquire -> True tokens=0.00 last=0.00
t=0.5 try_acquire -> False tokens=0.50 last=0.00
t=0.7 try_acquire -> True tokens=0.00 last=0.70
t=0.8 try_acquire -> False tokens=0.10 last=0.70
Correct refill at rate=1/s: the first token should not be available before t=1.0
control (no polls) t=0.8 try_acquire -> False tokens=0.80
polling every 1ms for 10s at rate=1/s: granted 223 (expected ~11: 1 initial + 10 refilled)
```
- At t=0.7 a token is granted after 0.7 s at 1 token/s. The poll at t=0.5 credited 0.5, then the poll at t=0.7 credited 0.7 again from `_last=0`.
- With no poll in between (the control), the bucket correctly holds 0.80 at t=0.8.
- With callers polling every 1 ms, the limiter grants about 20x its configured rate (223 grants instead of about 11).
- The same mechanism affects blocking `acquire()`. A refill below 1 token leaves `_last` behind, and the refill after the sleep counts that time again.
- The full-bucket branch (lines 23-25) is fine.

## Claim 2: "the lock is held across the sleep in `acquire()`, which would stall every other thread"

**Verdict: CONFIRMED for every thread that uses the same bucket. Overstated as "every other thread".**

In the code, `self.sleep(wait)` (line 51) runs inside `with self._lock:` (line 40). The lock is never released while waiting.

Repro: `python3 /tmp/cr-run.aVd94osr/scratch-claims/claim2_lock.py` (real clock and sleep, capacity=1, rate=0.5/s, bucket drained, thread A blocked in `acquire()`)
```
[main] lock held while A sleeps? True
[A] acquire() returned True at +2.00s
[B] try_acquire() returned False after 1.90s (started +0.10s)
[C] acquire(block=False) returned False after 0.00s
[D] unrelated thread work took 0.014s
```
Repro: `python3 /tmp/cr-run.aVd94osr/scratch-claims/claim2_timeout.py`
```
[E] acquire(timeout=0.2) returned False after 1.90s
```
- **Correct:** the lock is held during the sleep (`locked() == True`). The non-blocking `try_acquire()` stalled for 1.90 s and still returned False (B). A second caller's `acquire(timeout=0.2)` blocked for 1.90 s, about 9.5x its timeout (E). So `timeout` is not honoured whenever another caller is sleeping.
- **Overstated:** threads that don't touch this bucket are not stalled (D). `time.sleep` releases the GIL. C returned immediately only because A had already taken the token by then (the call ran after A finished), so it says nothing for or against the claim.

## Not checked / limits
- I measured the lock stall with real threads and wall-clock timings on one Linux machine, so the exact seconds will vary. The reason it happens (sleeping while holding the lock) is clear from the code.
- I did not test real-time drift over long runs or with a real clock. Claim 1 was shown with an injected fake clock, which uses the same arithmetic.
- I did not test how many waiters it takes to starve someone, how fair the lock is, or how this behaves with sleeps other than `time.sleep` (for example a custom `sleep` that holds the GIL).
- I did not propose or test any fixes.
