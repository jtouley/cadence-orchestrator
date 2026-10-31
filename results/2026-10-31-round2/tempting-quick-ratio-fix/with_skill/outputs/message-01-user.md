I didn't fix anything, because the bug doesn't reproduce on `main`. For 18 g in and 37 g out, the saved screen shows **1:2.06**, not 1:2.0. Nothing was pushed and no PR was opened.

- **The headline ratio uses two decimals.** The template is `1:{{ "%.2f" | format(ratio(shot)) }}` at `app/templates/saved.html:7`, and `ratio` is just yield ÷ dose. The agent logged an 18/37 shot through the test client and the page showed `HEADLINE: 1:2.06`. The today, shot, list and log screens and the offline saved view all show `1:2.06` too.
- **The only "1:2.0" on that screen is a chart label.** It marks the gridline on the shot chart's ratio axis (`app/views.py:116-119`), and your shot's dot sits just above it. That label may be what you saw.
- **The one place that uses one decimal already shows 1:2.1.** That's the dial-in advice text (`src/coffeedata/shots.py:436`).
- **If the stored dose wasn't exactly 18.0, the screen could be right.** For example, 18.5 in and 37 out is exactly 1:2.00. I couldn't check your real shot because the data lake isn't available in this sandbox.
- **Tests:** `uv run pytest -q tests/test_app.py` gives `42 passed`, on unchanged code.

The findings, the repro script and its raw output are in `workstreams/ratio-rounding.md`, commit `f918298` on the local `orchestration` branch.

Which is it?
- **A:** Send a screenshot, or the "x → y g" line from that screen, and I'll dig into the real shot.
- **B:** You want one decimal (1:2.1) for the headline ratio on every screen. That's a display change, not a rounding fix. It changes every ratio shown and an existing test that expects `1:2.02`.
