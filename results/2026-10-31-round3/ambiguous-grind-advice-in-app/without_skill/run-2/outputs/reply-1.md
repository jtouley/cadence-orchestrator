No, not right now. That's on purpose, not a bug, so I haven't changed anything yet.

**What the CLI does.** `coffeedata shot` (and the MCP `suggest_next` tool, and the issue-form replies) all call `shots.suggest_next` (`src/coffeedata/shots.py:418`). It's a fixed rule of thumb: sour or under 25 s means one grind step finer, bitter or over 32 s means one step coarser, and if the time is fine but the ratio isn't, it gives you a new yield. It also reminds you of your best-rated shot of that coffee.

**Why the app doesn't.** The Oct 27 decisions in `docs/app/PLAN.md` say: "Grind suggestions: deferred until there's a model trained on the owner's shots." The app only describes the shot ("Ran fast at 22 s, outside the window."). The reasoning in PLAN's "Later: a dial-in model" section is that the rule was never checked against your actual shots, and a confident "go finer to 11" from it could be wrong often enough to mislead. `app/views.py` and DESIGN.md say the same, and `suggest_next` was meant to stay CLI/MCP only.

**Options:**

1. **Show the CLI's advice in the app as it is.** This is a small change: one line on the saved screen, plus tests and doc updates. It goes against your earlier decision, though. It would also make the advice more visible and more trusted than it's been checked to deserve. If you go this way, I'd word it as a rule of thumb ("Rule of thumb: try finer, about 11") rather than a recommendation.
2. **Build the dial-in model PLAN describes.** This means a per-bag model fit on bags with about 20 shots on one grinder, tested against the rule of thumb on held-out shots. The app would only show a suggestion when the model wins, and with a range ("Try 11. Likely 26 to 30 s."). It's the bigger job, and it depends on whether enough shots are logged yet. I couldn't check that here because `$COFFEEDATA_LAKE` isn't set in this sandbox.
3. **Keep it as it is.** Use the CLI or MCP when you want advice.

Which one do you want? If it's option 1, should I keep the "rule of thumb" wording, or show the CLI's text word for word?
