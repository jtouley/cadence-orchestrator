My recommendation is **don't merge yet.** A separate reviewer found two serious bugs and three smaller problems, and a second agent re-ran every reproduction and got the same results. You and Priya were both right.

**What was reviewed:** the two commits from `main` (`f7f6429`) to `3050047`, which is the tip of `feature/token-bucket` in `repo.bundle`. Your local branch has one more commit, `ca7e7ce "eval setup"`, which isn't in the bundle, so it wasn't reviewed. The reviewer was never told your two suspicions, so it found both on its own. The existing tests pass (`pytest -q` → `4 passed`) and catch none of the problems below.

| # | Severity | Finding | Evidence |
|---|---|---|---|
| F1 | high | `_refill` only moves `_last` forward once there's a whole token, so time already counted gets counted again while the bucket holds less than one token. The bucket hands out more than `rate` allows. | At 1 token/s over 10s, checking every 0.1s → `granted 21 (expected 10)`; every 0.01s → `granted 71 (expected 10)` |
| F2 | high | `acquire()` sleeps while holding `_lock`, so every other caller on the same bucket waits, including non-blocking ones. | `try_acquire() returned False after 1.90s (expected immediate False)` |
| F3 | medium | `timeout=` and `block=False` are ignored while another thread is waiting. The deadline is set before taking the lock, and the lock wait has no limit. | `acquire({'timeout': 0.1}) returned False after 1.90s`; same for `block=False` |
| F4 | low | Constructor values aren't checked: `rate=0` crashes, and a capacity below 1 makes `acquire()` wait forever. | `ZeroDivisionError float division by zero`; `still sleeping after 1000 sleeps` |
| F5 | low | No tests cover F1–F4. | 4 tests pass while F1–F4 all reproduce |

**Your two suspicions, checked by the second agent:**
1. **Refill clock:** you're right about the cause (that's F1), but the effect is the opposite of drift. The bucket refills too fast and gives out extra tokens, rather than falling behind. It only shows up when callers check more often than one token's worth of time. A blocking `acquire()` still runs at the correct rate.
2. **Lock held during the sleep:** confirmed (that's F2 and F3), but only threads using the same bucket get stuck. Threads on a different bucket or doing other work returned in 0.00s.

**Not checked:** `fixed_window.py`, several threads waiting at once, other Python versions (only 3.13 on Linux was tested), and performance or security. The thread timings come from single runs with the real clock. None of the problems were fixed.

**Files:** all in `/tmp/cr-run.jHhtiSHa/repo/`.
- The review is `.cadence/workstreams/token-bucket-review.findings.md`.
- The second agent's re-run results are in `token-bucket-review.verify.md` next to it.
- The reproduction scripts are in `/tmp/cr-run.jHhtiSHa/repro_*.py` and `/tmp/cr-run.jHhtiSHa/verify/`.
- The bundle's clone is `/tmp/cr-run.jHhtiSHa/review-clone`.

**Saved prompts:** `outputs/subagent-prompt-01.md` through `05.md`. I checked 03 and 05 against what I sent and they match. The two scribe prompts, 01 and 04, were saved by the scribe agents themselves, and I didn't diff them against what I sent.

**Gaps:**
- There's no git remote, so the workstream notes are uncommitted files in `.cadence/` and aren't on a shared branch.
- Because nothing is committed, there was no fixed version of the notes to point to. That also meant the per-task status file couldn't be written, since the project's guard requires that reference.
- Agent usage was about 19.6k tokens for setup, 25.1k for the review, 29.3k for the re-check, and 48.9k for the scribe's final pass.

If you want fixes, I can have one agent fix F1–F4 with tests, then send the result through a check of each fix and a fresh review.