I couldn't reproduce this on `main` (6bda240), so I haven't changed anything.

- A saved 18 g → 37 g shot shows **1:2.06** on the saved screen. Every place that shows a ratio uses two decimals: `app/templates/saved.html:7` and `app/static/app.js:311,479`. Nothing rounds it down to 2.0. Repro output: `SAVED RATIO: ['1:2.06', …]`, and `tests/test_app.py` gives 42 passed.
- The saved screen's chart does have a fixed **"1:2.0"** label on its axis (`app/views.py:116-119`). That's probably what you saw, or else you were on an older build.

Which do you want?
A) Leave it as is: it's the axis label, and the ratio itself is right.
B) Show ratios to one decimal everywhere (1:2.1). This changes Saved, Shot, Today and Log, and the two-decimal tests would need updating.

Coordination doc: local branch `orchestration`, `workstreams/quick-ratio-rounding.md` (not pushed). There's an empty worktree at `/tmp/co-r3/wt-quick-ratio-rounding` on branch `fix/quick-ratio-rounding`.
