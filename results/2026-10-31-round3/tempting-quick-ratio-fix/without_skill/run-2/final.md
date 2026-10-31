I didn't change any code. On `main` the saved screen doesn't round the ratio the way you described.

I rendered the saved screen for an 18 g → 37 g shot. It shows **1:2.06**, the big number formatted with `"%.2f"` at `app/templates/saved.html:7`. The shot row, the shot page and Today use two decimals as well.

The "1:2.0" on that screen is most likely a label on the y-axis of the dial-in chart under the number. The axis is labelled 1:1.8, 1:2.0, 1:2.2 and 1:2.4 (`app/views.py:116-119`). The 18 → 37 dot sits just above the 1:2.0 line, so it's easy to read the label as the shot's value. That one-decimal label is intended: `test_default_chart_keeps_one_decimal_on_ratio_ticks` checks for it.

Strings from the rendered page:
- `1:2.06`: the shot's ratio
- `1:1.8`, `1:2.3`: the window
- `1:1.8`, `1:2.0`, `1:2.2`, `1:2.4`: axis labels

If you saw 1:2.0 as the big number, it might have come from an older deploy or cached JS. A screenshot would tell us which. If you'd rather the ratio show one decimal (1:2.1) everywhere, that's a quick change to the four templates and two lines in `app.js`. The tests that check for "1:2.02" would change with it. I didn't make that change because the current display isn't wrong; it's just more precise.

My messages to you are in `outputs/01-status.md` and `outputs/02-final.md`. I didn't use any subagents.