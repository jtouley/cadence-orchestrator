I wouldn't merge this yet. Both reviewers found two serious bugs in the token bucket, and a separate verifier reran the repro scripts and got the same results.

**How the review went.** The first reviewer accidentally read the section of the workstream doc where I'd recorded your hunch and Priya's, so its review wasn't independent of them. It said so itself. I then ran a second reviewer that never saw the doc at all, and it found the same top issues on its own. A third agent reran the first reviewer's repro scripts on a fresh export of the branch tip (`3050047`) and checked that they test the real `TokenBucket` class. Findings 1–4 below reproduced; the test-coverage finding was checked by reading the tests, since it has no script. The branch's own tests pass (`4 passed`), but none of them cover these cases.

**Findings, most severe first:**
1. **High: it hands out tokens faster than the configured rate.** Your hunch picked the right line, but the effect is the opposite of what you guessed. Because `_last` isn't updated until there's a whole token, the same stretch of time is counted again on every check while the bucket is low. So the limiter isn't slow; it over-grants, and the more often callers check, the worse it gets.
   - At 1 token/sec, checking every 0.1s: `granted at t=0.4 … tokens granted in 1.0s: 2 (expected 1)`
   - Blind reviewer, 10 tokens at 1/sec over 3s: `granted 7 (expected 3)`
2. **High: `acquire()` holds the lock while it sleeps. Priya is right.** Every other thread stalls while one waits, including `try_acquire()`, which is meant to return immediately. Both reviewers got `try_acquire returned False after 1.90s (expected ~0.00s)`.
3. **Medium: a capacity below 1 makes `acquire()` loop forever,** holding the lock the whole time. Repro: `capacity=0.5: RuntimeError still looping after 1000 sleeps` (the RuntimeError is the test script's own cut-off).
4. **Low: `rate=0` makes `acquire()` crash** with `ZeroDivisionError`. The constructor doesn't check either setting.
5. **Medium: the tests can't catch any of this.** They run on one thread with a fake clock, and never check a bucket holding less than a whole token. They also don't cover `timeout`, `block=False` or bad settings.

**Not checked:** heavy multi-thread load, clocks going backwards, rounding drift over long runs, negative settings, and Python versions other than 3.13. The scripts covered the `try_acquire()` stall only; that `acquire(block=False)` and other threads' timeouts stall too follows from the code but wasn't run.

**Setup notes:**
- **Guard:** it was running for the whole session, so every edit and command went through agents.
- **Clone:** the bundle is cloned to `/tmp/cr-run.IX6cKBq7/clone`, reviewing `main` (`f7f6429`) to `feature/token-bucket` (`3050047`).
- **Workstream records:** there's no remote, so the workstream doc and task list are only local commits on the clone's `orchestration` branch, the latest being `9fca123`. Nothing was pushed, and pre-commit isn't installed, so no checks ran on them.
- **Changes:** no code was changed, and nothing is merged.

Every message I sent to an agent is saved word for word as `subagent-prompt-01.md` to `-07.md`. Prompts 02 and 03 are follow-ups to the agent that set up the doc and task list, which had its task-list file rejected twice by the guard's format check.

Files are in `/tmp/cr-run.IX6cKBq7/repo/outputs/`:
- review.md
- review-blind.md
- verify.md
- subagent-prompt-01.md to subagent-prompt-07.md