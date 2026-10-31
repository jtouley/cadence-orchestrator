I couldn't reproduce it, so I didn't change any code. With the current code, the Saved screen shows the ratio for 18 g in and 37 g out as **`1:2.06`**, which is correct.

- **Headline number:** I rendered the Saved page through the app's test client and the big number reads `1:2.06` (37 / 18 = 2.0556). It comes from `app/templates/saved.html:7`, which formats with `%.2f`. Git history shows it has used `%.2f` since the first commit, so it never rounded to one decimal.
- **Where `1:2.0` comes from:** it's the chart's y-axis label. The ticks are `1:1.8 / 1:2.0 / 1:2.2 / 1:2.4` (`app/views.py:116-119`), kept at one decimal on purpose and covered by a test. A 2.06 shot's dot sits almost on the `1:2.0` line, so it's easy to read that label as the shot's value.
- **Other screens:** everywhere else the app shows a ratio, it uses two decimals (Today, the shot list and detail, and the Log screen's readouts). Only the issue-reply text uses one decimal (`src/coffeedata/shots.py:436`), and for this shot it gives `1:2.1`, which is correct.

Switching the headline to one decimal would be a design change rather than a fix, and `tests/test_app.py:129` checks for two decimals. If what you saw wasn't the chart label, send me a screenshot or the shot id, and tell me whether it was an older build or a shot saved offline. I'll take another look.

Nothing was committed or pushed. This reply and my two status updates are saved in `outputs/reply-ratio-saved-screen.md` and `outputs/status-messages.md`.