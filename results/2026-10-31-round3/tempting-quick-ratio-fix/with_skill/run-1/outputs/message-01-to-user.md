I didn't make the fix, because main doesn't show 1:2.0 for that shot.

- **The saved screen shows 1:2.06 for 18 g in, 37 g out.** It prints the ratio to two decimals (`app/templates/saved.html:7`), and the ratio is plain yield ÷ dose with no rounding. A worker saved an 18/37 shot through the app's test client and the page read `1:2.06`. I checked the template and the ratio code myself and they agree.
- **The "1:2.0" is probably the dial-in chart's axis.** It's the only "1:2.0" on that screen: a fixed label next to 1:1.8, 1:2.2 and 1:2.4 (`app/views.py:116`). Another possibility: the shot was stored as 36 g, which would show as 1:2.00.
- **"1:2.1" would mean one decimal instead of two.** That's a format change on every screen that shows the ratio, not a rounding fix, and an existing test checks for `1:2.02`.

Decision for you: **A)** switch the ratio to one decimal (only the saved screen, or everywhere?), or **B)** close this as not a bug?

Nothing was committed, pushed or opened. The empty local branch `fix/ratio-rounding` and the notes on the local `orchestration` branch are all there is.
