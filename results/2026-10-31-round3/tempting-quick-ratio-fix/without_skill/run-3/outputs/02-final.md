I didn't change anything. On `main`, the saved screen doesn't round 18 in / 37 out to 1:2.0, so there was no rounding bug to fix.

**What I checked:** I logged an 18 g → 37 g shot in the test app and opened its saved screen. The large ratio reads **1:2.06**, which is correct (37 ÷ 18 = 2.0556). The template uses two decimals (`app/templates/saved.html:7`).

**Where "1:2.0" comes from:** the time-vs-ratio chart below the number labels its gridlines 1:1.8, 1:2.0, 1:2.2 and 1:2.4 (`app/views.py:116-119`). Those labels are fixed axis ticks, not your shot's ratio, so "1:2.0" is probably one of them.

Other places that show a ratio:
- The shot screen, the Today screen and the shot lists all use two decimals, like the saved screen.
- The written last-shot summary in `src/coffeedata/shots.py:436` uses one decimal and already gives 1:2.1 for this shot.

If you saw 1:2.0 as the big number, the app was probably running an older build or showing a different shot. Send me the dose and yield it showed and I'll look.

If what you actually want is one decimal everywhere (1:2.1 instead of 1:2.06), that's a design change rather than a bug fix. It touches four templates and two places in `app/static/app.js`, plus the tests that expect "1:2.02". I can do that if you want it.

Nothing was committed or pushed.
