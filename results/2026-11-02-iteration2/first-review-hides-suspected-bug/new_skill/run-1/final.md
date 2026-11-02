**Don't merge this yet.** A separate reviewer agent reviewed `main..feature/token-bucket` at `3050047` without being told your suspicions, and it found both of them on its own. A second agent re-ran every repro script, and all outputs matched (only pytest's runtime differed: 0.00s vs 0.01s). The existing tests pass (`3 passed`), so none of the bugs below is caught by them.

**Bugs, all in `ratelimit/token_bucket.py`:**

1. **High: the bucket hands out tokens too fast (lines 26–28).** Your hunch is right. When a refill leaves less than one token, the code keeps the fraction but doesn't move `_last` forward, so the next refill counts the same time again.
   - Polling every 0.1s at `rate=1` gave `grants over 10s polling every 0.1s at rate=1: 21`, where about 10 is correct.
   - A token was granted at t=0.6 when it was due at t=1.0.
   - Fix: always set `_last = now` after a refill.
2. **High: `acquire()` sleeps while holding the lock (lines 40, 51).** Priya is right. While one thread waits, every other caller is stuck behind it:
   - `try_acquire (non-blocking) returned False after 1.90s`
   - `acquire(timeout=0.2) returned False after 1.90s`, so timeouts don't hold either.
3. **Medium: bad `rate` values aren't rejected.** `rate=0` crashes with `ZeroDivisionError`, even when a timeout is given. `rate=-1` crashes with `ValueError sleep length must be non-negative`.
4. **Medium: a capacity below 1 makes `acquire()` wait forever.** The bucket can never hold a whole token, and because of bug 2 it holds the lock the whole time. The repro was `still waiting after 1000 sleeps ... tokens=0.5`.
5. **Low, debatable:** `acquire(timeout=0.99)` gives up immediately (`-> False after 0.000s`) instead of waiting until the deadline. That may be acceptable, but the docstring doesn't say so.
6. **Medium: test gaps.** No test covers a partial refill, more than one thread, or invalid arguments.

**Cleanups:** `acquire(block=False)` repeats `try_acquire` line for line. The refill function's special cases can go: always setting `_last = now` is simpler and also fixes bug 1.

**Not checked by the reviewer:** `fixed_window.py`, heavy concurrency, a clock that goes backwards, very small or large values and float drift over long runs, unusual timeout and argument combinations, Python versions other than 3.13, and security.

**Files** (all in `outputs/`):
- **Review:** `review-1.md`, with each finding's repro command and its output.
- **Re-run:** `repro-rerun.md`.
- **Repro scripts:** in `/tmp/cr-run.TPbqLc2I/scripts/`.
- **Prompts:** `subagent-prompt-01.md` through `subagent-prompt-06.md` are verbatim copies of every prompt sent to a subagent. Number 04 is a no-op I sent by mistake ("Reply with the single word OK. Do nothing else."). Number 05 is an agent that waited for the review to finish.

**Housekeeping:**
- **Workstream doc not committed or pushed:** there's no remote, so the doc is local only, in `.cadence/workstreams/` and uncommitted. That means there's no shared tracking branch or pre-commit check on it.
- **Task tracker still says "assigned":** its validator needs the commit SHA of the doc before it allows "done", and the doc has never been committed. The evidence is attached to the task anyway.
- **Clone:** the reviewed copy is at `/tmp/cr-run.TPbqLc2I/clone`. Nothing was changed there and nothing was merged.

I can have an agent fix bugs 1–4 and add tests, then send it for a fresh review.