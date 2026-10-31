# Saved screen ratio, 18 g in and 37 g out: I couldn't reproduce it, so I didn't change any code

I rendered the Saved page for an 18 g → 37 g shot using the app's test client and current code (`9b850e8`).

- **The big ratio number reads `1:2.06`.** It comes from `app/templates/saved.html:7`, which formats with `"%.2f"`. The math is right: 37 / 18 = 2.0556, which rounds to 2.06. Git history shows `saved.html` has used `%.2f` since the first commit. It never rounded to one decimal.
- **The `1:2.0` on that page is the chart's axis label.** The target chart's y-axis is labelled `1:1.8 / 1:2.0 / 1:2.2 / 1:2.4` (`app/views.py:116-119`, kept at one decimal on purpose, as `test_default_chart_keeps_one_decimal_on_ratio_ticks` checks). A 2.06 shot's dot sits almost on the `1:2.0` line, so it's easy to read that label as the shot's value.
- Every other place in the app that shows a ratio uses two decimals: Today, the shot list and shot detail, and the Log screen's live and offline-saved readouts. Only the issue-reply text uses one decimal (`src/coffeedata/shots.py:436`), and for this shot it gives `1:2.1`, which is correct.

**So there's no rounding bug to fix.** Changing the headline to one decimal would just be a design change, and `tests/test_app.py:129` checks for two decimals (`1:2.02`).

If the screen you saw showed something other than the chart label, send me any one of these and I'll dig in:
- a screenshot;
- the shot id;
- whether you were on a build older than the current one, or whether the shot was saved offline.

Nothing was committed or pushed.
