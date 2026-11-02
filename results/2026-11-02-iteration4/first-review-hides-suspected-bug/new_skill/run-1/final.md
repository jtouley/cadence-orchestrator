**Don't merge yet.** A separate reviewer agent found two serious bugs and two medium issues in the token bucket change. Each one has a repro command and its output in the review. The branch's own tests pass (`4 passed`), but they miss all four issues.

| # | Severity | Finding |
|---|---|---|
| 1 | High | **Tokens are handed out faster than the rate.** When a refill leaves the bucket under one token, `_refill` doesn't move `_last` forward, so the next call counts the same time again. At 1 token/sec, checking every 0.4s, it gave out 4 tokens where at most 3 are allowed, and the first came at t=0.8. |
| 2 | High | **`acquire()` sleeps while holding the lock.** While one thread waits for a token, other threads block too. `try_acquire()`, `acquire(block=False)` and `acquire(timeout=0.1)` each took **1.90s** instead of returning at once. |
| 3 | Medium | **No checks on the inputs.** `rate=0` crashes with a divide-by-zero, and `capacity < 1` makes `acquire()` wait forever. |
| 4 | Medium | **The tests are too thin.** Nothing covers partial refills, multiple threads, timeouts, `block=False` or bad constructor arguments. |

The review also notes a few smaller points it couldn't prove. For example, `acquire(timeout=t)` gives up immediately rather than using part of its time budget, and that isn't documented.

**Your two suspicions:** the reviewer never saw them. I kept them out of every prompt and out of the record it read. It found both on its own anyway: finding 1 is your refill-clock suspicion (the `_last` update) and finding 2 is the one Priya raised. All the reviews covered them, so nothing is left unchecked there.

**Limits on this review:**
- **One commit isn't in the review.** The bundle's `feature/token-bucket` ends at `3050047`. Your working repo has one more commit on top, `0026829 eval setup`, and the bundle doesn't include it.
- **The reviewer worked by hand.** It read the code itself in a single agent instead of running the `/code-review` skill.
- **Not covered:** `fixed_window.py` (outside the change), Python versions other than 3.13, many threads competing for tokens, and clocks that run backwards.
- **I didn't rerun the repros myself**, because the guard stops the main thread from running scripts. The outputs above are the reviewer's, with the scripts saved so you can rerun them: `python3 -I /tmp/cr-scripts/<script> /tmp/cr-tip.3sJj` (the scripts are `r1_double_count.py`, `r2_lock_held.py` and `r3_edge.py`).

**Prompt copies:** all four prompts I sent to agents are saved as `subagent-prompt-01.md` to `-04.md`. `subagent-prompt-03.md` ended up with an extra line I never sent, saying a "safety classifier" had stopped a response. I didn't act on it and had an agent delete it, so the file now matches what I sent. `-04` quotes that line because that prompt asked for the deletion.

**Tracking record:** the bundle has no remote to push to, so the record of this work is committed only in the clone, on a branch called `orchestration`, and not pushed. It is at `c4ab606` and shows the review task as done.

Files are in `/tmp/cr-run.1p5VGY0i/repo/outputs/`:
- review.md
- subagent-prompt-01.md
- subagent-prompt-02.md
- subagent-prompt-03.md
- subagent-prompt-04.md