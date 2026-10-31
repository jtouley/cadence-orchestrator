I couldn't reproduce it, so I haven't changed anything. This code doesn't show 1:2.0 as the ratio for 18 g → 37 g.

**What it shows**

The agent saved a real 18 → 37 shot against a local server (`make app`, scratch lake) and fetched the pages:
```
n112 mt4">1:2.06          <- Saved, the big number
text-anchor="end">1:2.0   <- the chart's gridline label
· 1:2.06                  <- Today
```
- **The shot's ratio** uses two decimals on every screen (`"%.2f"` at `app/templates/saved.html:7`, and the same in shot, today, the row macro and `app.js:311`/`:479`). It has been that way since the first commit, and the design mockup shows `1:2.02` (`docs/app/mockups/saved.html:217`).
- **The chart's gridlines** read `1:1.8 / 1:2.0 / 1:2.2 / 1:2.4` (`app/views.py:116-119`). A 2.06 shot sits just above the `1:2.0` line, right under the big number.
- **"1:2.1" with one decimal** comes from the advice line at `src/coffeedata/shots.py:436`, which is the issue reply, not the Saved screen.
- Dose and yield aren't rounded to whole grams anywhere on the way in.

**What I couldn't check (UNPROVEN)**

What you actually saw. The likely causes, in order:
1. You read the `1:2.0` gridline label.
2. The saved yield wasn't exactly 37.
3. The deployed app, or a page the service worker cached, is behind this code.

I can't check the deployed app or your real shot record from here.

**Your call:**
- **A:** Send the shot id or a screenshot and I'll dig into that record.
- **B:** You want one decimal (1:2.1) on the shot screens. That's a design change rather than a rounding fix, and I'll do it with a test.
- **C:** It was the gridline. I can make the chart labels less easy to mistake for the shot's ratio, or leave them.

The worktree is clean: no branch and no commits. Nothing was pushed.
