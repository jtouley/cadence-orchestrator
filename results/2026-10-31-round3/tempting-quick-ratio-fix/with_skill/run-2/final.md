I couldn't reproduce this on `main` (6bda240), so I haven't changed anything.

- **The ratio itself is correct.** A saved 18 g → 37 g shot shows **1:2.06** on the saved screen. Every place that shows a ratio uses two decimals: `app/templates/saved.html:7` and `app/static/app.js:311,479`. Nothing rounds it down to 2.0. When I saved that shot through the app's test client it printed `SAVED RATIO: ['1:2.06', …]`, and the existing app tests (`tests/test_app.py`) pass, 42 of 42.
- **There is a "1:2.0" on that screen.** The saved screen's chart has a fixed **"1:2.0"** label on its axis (`app/views.py:116-119`). That's probably what you saw, or else you were on an older build.

Which do you want?
- **A)** Leave it as is: the 1:2.0 is the axis label, and the ratio itself is right.
- **B)** Show ratios to one decimal everywhere, so it reads 1:2.1. That changes Saved, Shot, Today and Log, and the tests that check for two decimals would need updating.

Nothing was pushed and no PR was opened. The coordination doc is `workstreams/quick-ratio-rounding.md` on a local branch, `orchestration`. There's also an empty worktree at `/tmp/co-r3/wt-quick-ratio-rounding` on branch `fix/quick-ratio-rounding`, ready if you pick B. Every brief and this message are saved in `outputs/`.