I didn't change anything. I couldn't find a rounding bug that would print 1:2.0 for 18 g in and 37 g out.

I saved an 18 g → 37 g shot through the app's test client and opened its saved screen. The big ratio reads **1:2.06**. That's correct: 37 / 18 = 2.056, and every screen shows the ratio to two decimals (`app/templates/saved.html:7`, and the offline saved screen at `app/static/app.js:479`). The dial-in advice is the only place with one decimal, and it says 1:2.1 (`src/coffeedata/shots.py:436`).

The "1:2.0" on that screen is a label on the chart's vertical axis. The chart always marks 1:1.8, 2.0, 2.2 and 2.4 (`app/views.py:116-119`), whatever the shot was. My guess is that's what you saw.

If what you saw was the big number reading 1:2.0, it came from something other than the current `main`: maybe an older deployed build or a cached service worker. Tell me where it was and I'll look. Or, if you want the headline at one decimal (1:2.1), that's a one-line change in three templates and two places in `app.js`, and some tests would need updating. Say if you want it.
