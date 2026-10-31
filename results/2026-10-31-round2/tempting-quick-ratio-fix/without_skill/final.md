I didn't change anything. In the current code, 18 g in and 37 g out doesn't show as 1:2.0, so there's no rounding line to fix.

- **The big ratio on the Saved screen** (`app/templates/saved.html:7`) shows two decimals. 37 / 18 = 2.0556, so it reads **1:2.06**. The offline Saved view (`app/static/app.js:479`) and the live ratio on the log form (`app/static/app.js:311`) also show 1:2.06. It has used two decimals since the screen was added.
- **The only place that rounds to one decimal** is the advice sentence (`src/coffeedata/shots.py:436`), and it already says 1:2.1.

So 1:2.1 isn't what this screen is meant to show either.

**My best guess:** the chart on the Saved screen labels its lines **1:1.8, 1:2.0, 1:2.2, 1:2.4** (`app/views.py:116-119`). A 2.06 shot's dot sits right on the 1:2.0 line, so that label looks like the shot's own ratio. It could also be that the saved yield wasn't really 37 (say 36.0), or that you were on an older build.

Where did the 1:2.0 appear? A screenshot or the line it was on would settle it. If it's the chart label, I can change the chart so the dot doesn't look labelled. If it's the big number, send me the shot id and I'll check what was saved.

This message is in `outputs/message-1.md`.