# Claim check: TokenBucket (main..feature/token-bucket)

- Repo: /tmp/cr-run.YnusEVf5/review-clone
- Checked SHA: `30500472e38a36a69aa7050f1776625b11ec1279` (feature/token-bucket; main = `f7f6429`)
- File under test: `ratelimit/token_bucket.py`
- Repro scripts (outside repo): /tmp/cr-run.YnusEVf5/claimcheck-scratch/claim_a.py, claim_b.py
  Run: `python3 <script> /tmp/cr-run.YnusEVf5/review-clone`

## Claim A: refill clock drifts when empty because `_last` only moves once there's a whole token

**Verdict: CONFIRMED.** The mechanism is right. The effect is over-crediting: the bucket hands out tokens faster than `rate`. It does not under-fill.

`_refill` adds `elapsed * rate` to `_tokens` every call, but only advances `_last` when `_tokens >= 1`. While the bucket holds a fractional token, every call counts the same time span again. The more often callers poll an empty bucket, the more tokens it grants.

Output (fake clock, capacity=1, rate=1 tok/s, drained at t=0):
```
trace: rate=1, cap=1, drained at t=0
  t=0.25: try_acquire=False _tokens=0.250 _last=0.0  (correct _tokens=0.250)
  t= 0.5: try_acquire=False _tokens=0.750 _last=0.0  (correct _tokens=0.500)
  t=0.75: try_acquire=True  _tokens=0.000 _last=0.75  (correct _tokens=0.750)

tokens granted over 10 s at rate=1 (expected 10):
  poll every   1.0s -> 10 tokens
  poll every   0.5s -> 10 tokens
  poll every  0.25s -> 13 tokens
  poll every   0.1s -> 21 tokens
  poll every  0.01s -> 71 tokens

blocking acquire() x10 after drain: fake time elapsed = 10.000s (expected 10.0)
```
Notes:
- If callers poll `try_acquire()` every 10 ms, the bucket admits 7.1x its configured rate.
- A single caller using blocking `acquire()` gives the correct timing, because it sleeps through the whole deficit before it checks again. The bug shows when callers check an empty bucket often: `try_acquire()` polling, several threads, or `acquire(block=False)`.
- The existing tests miss this. They advance the clock in whole-token steps or use `acquire()` alone.

## Claim B: lock is held across the sleep in `acquire()`, stalling every other thread

**Verdict: PARTLY TRUE.**
- True: `self.sleep(wait)` runs inside `with self._lock:`. While one thread waits, every other thread that uses **the same bucket** is blocked. That includes non-blocking `try_acquire()` and `acquire(timeout=...)`, which then ignore their own non-blocking or timeout behaviour.
- Not true: threads that don't touch the bucket keep running. `time.sleep` releases the GIL, and the lock belongs to this one bucket only.

Output (real clock, capacity=1, rate=0.5 tok/s, so the drained bucket needs a ~2 s wait; thread W calls `acquire()`, main thread calls in 0.2 s later):
```
lock held while W is in acquire()/sleep: True
try_acquire() (non-blocking) returned False after 1.799s
unrelated thread ticks during that call: 178 (~180 expected if not stalled)
W acquire() finished at t=2.000s
acquire(timeout=0.1) on contended bucket returned False after 1.800s
```
- A call that should be non-blocking took 1.8 s and then returned False.
- `acquire(timeout=0.1)` took 1.8 s, 18x its timeout.
- The unrelated thread kept ticking normally: 178 of about 180 expected ticks.

## Left out / not checked
- No fixes were made or proposed beyond describing each mechanism.
- Claim A was measured only with a fake clock and capacity=1, rate=1. Other capacities and rates, and the real clock, were not swept.
- Claim A was not measured under real multi-thread contention, where several waiters would each poll and over-credit.
- Claim B timing was measured on one machine, once. There are no repeated runs or statistics.
- The `deadline` arithmetic in `acquire(timeout=...)` was not checked beyond the observed contention overrun.
- `ratelimit/fixed_window.py` and the rest of the package were not reviewed. The existing test suite was not run.
- No other issues in the diff were looked for. Only the two claims were checked.
