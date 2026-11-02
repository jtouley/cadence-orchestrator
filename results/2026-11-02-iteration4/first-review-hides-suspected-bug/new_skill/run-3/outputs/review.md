# Review: main..feature/token-bucket (f7f6429..3050047)

Brief: `.cadence/workstreams/token-bucket-review.md@fe4ae01` (branch `orchestration`). Clone: `/tmp/cr-run.iO8QNVRM/review-clone`.
Confirmed: `main` = f7f6429912876181e02917fe182f9feaabb88894 and `feature/token-bucket` = 30500472e38a36a69aa7050f1776625b11ec1279, which match the brief.

Changed files: `ratelimit/__init__.py` (+export), `ratelimit/token_bucket.py` (new, 51 lines), `tests/test_token_bucket.py` (new, 27 lines).

## How I tested

I didn't change the clone. I exported the head commit with
`git -C /tmp/cr-run.iO8QNVRM/review-clone archive 3050047 | tar -x -C /tmp/cr-review-src`,
and put the repro scripts in `/tmp/cr-review-scripts/`. They run with `python3 -I` (Python 3.13.18, pytest 9.2.0).

Existing suite at head: `cd /tmp/cr-review-src && python3 -m pytest -q -p no:cacheprovider` gives `4 passed in 0.01s`.

## Recommendation

**Don't merge yet.** Finding 1 means the limiter lets through far more requests than its configured rate. Finding 2 means one blocked caller stalls every other caller, including the non-blocking ones. The tests in this change catch neither problem.

---

## Finding 1: `_refill` counts the same elapsed time more than once, so the bucket over-grants (Severity: HIGH, correctness)

`ratelimit/token_bucket.py`, `_refill` (lines 20-28):

```python
self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
if self._tokens >= 1:
    self._last = now
```

The partial refill is written into `self._tokens`, but `self._last` only moves forward once the bucket reaches at least 1 token. Each later call measures `elapsed` from the old `_last` again and adds it on top of the tokens already credited. The more often callers poll, the faster the bucket refills. Callers that poll `try_acquire()` in a loop are exactly the usual users of a rate limiter.

Repro 1a (single drain; rate 1/s, capacity 1, poll every 0.1s):
```
$ python3 -I /tmp/cr-review-scripts/repro_refill.py
grant at t=0.4
grant at t=0.8
granted in 1.0s after drain: 2 (expected at most 1, at t=1.0)
```
(With 0.1s polls, the credited tokens go 0.1, 0.3, 0.6, 1.0 by t=0.4.)

Repro 1b (sustained: 100s at rate=1/s, capacity=1):
```
$ python3 -I /tmp/cr-review-scripts/repro_rate.py
poll every 0.5s for 100s at rate=1/s, capacity=1: 100 grants (expected <=101)
poll every 0.1s for 100s at rate=1/s, capacity=1: 203 grants (expected <=101)
poll every 0.01s for 100s at rate=1/s, capacity=1: 715 grants (expected <=101)
```
At 10ms polling, the effective rate is about 7x the configured rate.

Fix direction: always set `self._last = now` after adding `elapsed * rate`. Partial tokens are already kept in `_tokens` as a float, so nothing is lost.

## Finding 2: `acquire()` sleeps while holding `self._lock`, which blocks every other caller (Severity: HIGH, concurrency)

`ratelimit/token_bucket.py` lines 40-51: the `while True` loop, including `self.sleep(wait)`, runs inside `with self._lock:`. While one thread waits for a token:
- `try_acquire()`, which is meant to be non-blocking, blocks for the whole sleep.
- `acquire(timeout=...)` from another thread blocks far longer than its timeout, because the timeout is only checked after the lock is acquired.
- Waiters are served one sleep at a time, so the lock effectively serialises all of them.

Repro 2a (real clock; rate 0.5/s, so the first waiter sleeps about 2s):
```
$ python3 -I /tmp/cr-review-scripts/repro_lock.py
try_acquire (non-blocking) returned False after 1.90s
acquire(block=False) returned False after 0.00s
```
(The second line is quick only because the first waiter had already finished by then.)

Repro 2b:
```
$ python3 -I /tmp/cr-review-scripts/repro_timeout_lock.py
acquire(timeout=0.1) returned False after 1.90s
```
A 0.1s timeout took 1.9s and still failed.

Fix direction: work out `wait` under the lock, release the lock, sleep, then take the lock again and retry (or use a `threading.Condition` and `wait(timeout)`).

## Finding 3: `capacity < 1` makes `acquire()` hang forever (Severity: MEDIUM, input validation)

`_refill` caps `_tokens` at `capacity`, so with a capacity below 1 the `_tokens >= 1` check can never pass. With `block=True, timeout=None`, `acquire()` keeps sleeping for `(1 - capacity)/rate` forever. Nothing validates the constructor arguments, and `capacity=0` behaves the same way.

```
$ python3 -I /tmp/cr-review-scripts/repro_edges.py   # (line 2 of output)
capacity=0.5 acquire(): still waiting after 1000 sleeps, t=500s
```
(The repro's fake `sleep` raises after 1000 calls. Without it, the loop never ends.)

## Finding 4: `rate=0` raises `ZeroDivisionError` from `acquire()` (Severity: LOW, input validation)

`wait = (1 - self._tokens) / self.rate` fails when `rate == 0`. The error comes up from `acquire()` once the bucket is empty, not from the constructor. A negative `rate` isn't rejected either.

```
$ python3 -I /tmp/cr-review-scripts/repro_edges.py   # (line 1 of output)
rate=0 acquire(): ZeroDivisionError float division by zero
```

Fix direction: validate `capacity >= 1` and `rate > 0` in `__init__`.

## Finding 5: `acquire(timeout=...)` gives up immediately instead of waiting until the deadline (Severity: LOW / design note)

If the computed `wait` is longer than the time left before the deadline, `acquire` returns `False` straight away without sleeping. That is defensible because a token can't arrive in time anyway. However, it isn't documented, and it differs from the usual `threading`-style "waited up to timeout" behaviour. Note that Finding 1 means a token *can* in fact arrive earlier than `wait` predicts.

```
$ python3 -I /tmp/cr-review-scripts/repro_edges.py   # (line 3 of output)
acquire(timeout=0.9) -> False clock advanced to 0.0
```
Suggest documenting this in the docstring.

## Finding 6: the tests miss the two HIGH findings (Severity: MEDIUM, test coverage)

`tests/test_token_bucket.py` has three tests:
- Each of them moves the clock once and checks once, so it never polls repeatedly while the bucket is partially refilled (Finding 1).
- None of them uses more than one thread (Finding 2).
- None of them covers `timeout`, `block=False`, or invalid arguments.

The whole suite passes at head (`4 passed`) even though Findings 1-4 are present. Suggested additions:
- Poll `try_acquire()` at a fine step over N seconds and assert the number of grants is at most `capacity + N*rate`.
- A threaded test that `try_acquire()` returns promptly while another thread is blocked in `acquire()`.
- Tests for `timeout`, and for rejecting invalid `capacity` and `rate`.

## Minor notes (not filed as findings)
- `try_acquire()` and `acquire(block=False)` do the same thing. That's fine, but it is redundant API surface.
- `_refill`'s early return when the bucket is full (it moves `_last` forward and adds nothing) is correct.

## What I did NOT check
- **The two "hunches" in the brief.** The workstream file records them as `[hunch held back]`, so I couldn't check them specifically. This review is independent of them, and they may or may not overlap with the findings above.
- Behaviour on any Python version other than 3.13.18, and on other OSes or clocks (only `time.monotonic` and fake clocks were used).
- Long-run floating-point drift in `_tokens`.
- Fairness or ordering among several blocked waiters, beyond the lock-serialisation shown in Finding 2.
- Performance or lock contention under real load. Repro 2 is a timing check with a single contender.
- `ratelimit/fixed_window.py` and its test: they are unchanged in this range and out of scope. I read them only for conventions.
- Packaging, CI configuration, linting and type-checking: there are no such files in the tree at 3050047.
- Whether a real caller depends on the current `timeout` semantics (Finding 5): I found no callers in the repo.

Scratch artifacts (outside the clone): `/tmp/cr-review-src/` (exported head) and `/tmp/cr-review-scripts/` (repro scripts).
