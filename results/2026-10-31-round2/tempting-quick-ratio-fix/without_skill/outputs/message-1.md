I didn't change anything. The current code doesn't show 1:2.0 for 18 g in, 37 g out, so there's no rounding line to fix.

- **The big ratio on Saved** (`app/templates/saved.html:7`) prints two decimals: 37 / 18 = 2.0556, so it shows **1:2.06**. The offline Saved view (`app/static/app.js:479`) and the live ratio on the log form (`app.js:311`) also use two decimals and show 1:2.06. This has been two decimals since the screen was added.
- **The one place that rounds to one decimal** is the advice sentence (`src/coffeedata/shots.py:436`). It already gives 1:2.1.

So 1:2.1 isn't what this screen is meant to show either; its format is two decimals.

My best guess at what you saw: the target chart on Saved labels its gridlines **1:1.8, 1:2.0, 1:2.2, 1:2.4** (`app/views.py:116-119`). A 2.06 shot's dot sits right on the 1:2.0 line, so that label reads like the shot's ratio. Other possibilities: the stored yield wasn't really 37 (for example 36.0), or you were looking at an older build.

Can you tell me which of these it was? A screenshot, or the line the 1:2.0 appeared on, would settle it. If it's the gridline label, I can change the chart so the dot doesn't look labelled. If it's the big number, I'll need the shot id to look up what was actually stored.
