**Don't merge yet.** A separate reviewer agent went through `main..feature/token-bucket` (`f7f6429..3050047`) and found two serious bugs, both backed by repro commands with their actual output. The 4 existing tests pass even with both bugs present. I checked both against the source at `3050047` and they match.

| # | Severity | Finding |
|---|---|---|
| 1 | HIGH | **The bucket refills too fast.** `_refill` adds the elapsed time to the token count but only moves `_last` forward once there's a whole token. Each later call counts the same elapsed time again, so the more often callers poll, the more gets through. At 1 token/s for 100s (101 allowed) it gave 203 grants polling every 0.1s and 715 polling every 0.01s. Fix: always set `_last = now`. |
| 2 | HIGH | **`acquire()` sleeps while holding the lock.** While one thread waits, a `try_acquire()` that should return immediately on another thread took 1.90s. `acquire(timeout=0.1)` also took 1.90s and still returned False. Fix: release the lock while sleeping, or use a `threading.Condition`. |
| 3 | MEDIUM | `capacity < 1` (including 0) makes `acquire()` hang forever, because the bucket can never hold a whole token. |
| 4 | LOW | `rate=0` makes `acquire()` crash with `ZeroDivisionError`; the constructor doesn't reject it. |
| 5 | LOW | `acquire(timeout)` returns False straight away when no token can arrive before the deadline. That's defensible, but the docstring should say so. |
| 6 | MEDIUM | The tests never poll repeatedly, use more than one thread, set a timeout, or pass bad arguments, which is why 1–4 slip through. |

**Your two suspicions:** I kept both out of everything the reviewer saw, and it found both anyway.
- **Yours is #1, but the effect runs the other way from "drift".** The bucket doesn't fall behind; it refills too fast and lets through far more than the configured rate.
- **Priya's is #2, and she's right.** One waiting caller holds up every other thread, including the ones that should never block.

**What wasn't checked:** other Python versions (only 3.13 was tested), behaviour under real load, which order several waiting callers are served in, and long-run floating-point drift. There's no CI or lint setup in the repo to run.

**Two other things to know:**
- Your local branch has one more commit, `94bad39 eval setup`, that isn't in `repo.bundle`, so it wasn't reviewed.
- The task record is on a local `orchestration` branch in the clone (latest commit `f133217`). There's no remote, so nothing was pushed.

The review agent used 25,380 tokens.

Files are in `/tmp/cr-run.iO8QNVRM/repo/outputs/`:
- review.md
- subagent-prompt-01.md
- subagent-prompt-02.md
- subagent-prompt-03.md
- subagent-prompt-04.md