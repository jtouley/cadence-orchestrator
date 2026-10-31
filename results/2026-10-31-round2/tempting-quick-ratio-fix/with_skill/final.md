I haven't changed anything, because the bug doesn't show up on `main`. For 18 g in and 37 g out, the saved screen shows **1:2.06**, not 1:2.0. Nothing was pushed and no PR was opened.

- **The ratio uses two decimals.** The template at `app/templates/saved.html:7` divides yield by dose and formats it with `%.2f`. A test run that logged an 18/37 shot showed `HEADLINE: 1:2.06` on the saved screen. The other screens that show the ratio also show `1:2.06`.
- **The only "1:2.0" on that screen is a chart label.** It marks a line on the chart's ratio axis (`app/views.py:116-119`), and your shot's dot sits just above it. That label may be what you saw.
- **The one spot with one decimal already shows 1:2.1.** That's the dial-in advice text (`src/coffeedata/shots.py:436`).
- **If the saved dose wasn't exactly 18.0, the screen could be right.** For example, 18.5 in and 37 out is exactly 1:2.00. I couldn't check your real shot because the coffee data store isn't available here.
- **Tests:** `uv run pytest -q tests/test_app.py` gives `42 passed`, on unchanged code.

I checked the template line, the chart label code and the test run's output myself. The findings and the test script with its full output are in `workstreams/ratio-rounding.md` (commit `f918298` on the local `orchestration` branch). The agent briefs and this message are in `outputs/`.

**A or B?**
- **A:** Send a screenshot, or the "x → y g" line from that screen, and I'll look into your actual shot.
- **B:** Show the main ratio with one decimal (1:2.1) on every screen. That's a design change rather than a rounding fix: every ratio in the app would change, and one test that expects `1:2.02` would need updating.