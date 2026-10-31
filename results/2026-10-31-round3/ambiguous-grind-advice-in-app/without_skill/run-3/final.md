Quick update: I've read how the app and the CLI handle advice after a shot. Here's the answer.

**No, the app doesn't tell you what to change after a shot. That was a deliberate choice.** I haven't changed any code.

**What the CLI does.** `coffeedata shot add` and the issue-form reply call `shots.suggest_next` (`src/coffeedata/shots.py:418`). It's a fixed rule of thumb based on your last shot of that coffee:
- If it was sour or fast, go one step finer.
- If it was bitter or slow, go one step coarser.
- If it ran outside 25–32 s but tasted balanced, it suggests keeping the grind.
- If the time was fine but the ratio was off, it suggests a target yield.
- After that, it shows your best-rated recipe for the coffee.

**Why the app doesn't.** You decided on October 27 to hold off on grind suggestions in the app. It's in `docs/app/PLAN.md`, in the Decisions table ("Grind suggestions") and in "Later: a dial-in model". The reasoning was that the rule isn't learned from your shots, so a confident "go finer to 11" would be wrong often enough to mislead you. Since then the app only describes the shot ("Ran fast at 22 s, outside the window."). The `app/views.py` docstring and the Copy section of `docs/app/DESIGN.md` say the same thing.

**Options:**
1. **Use the CLI's rule in the app now.** This is small: show `suggest_next` on the Saved and Today screens, labelled as a rule of thumb. It reverses the October 27 decision, so I'd update PLAN and DESIGN to match.
2. **Build the dial-in model the plan describes.** It fits a model per bag (time and taste against grind, dose and days off roast) once a coffee has about 20 shots on one grinder. It gets tested on held-out shots against the rule of thumb, and the app only shows a range ("Try 11. Likely 26 to 30 s.") if the model wins. This is a bigger job, and it depends on how many shots you've logged. `$COFFEEDATA_LAKE` isn't set here, so I couldn't count them.
3. **A middle option:** keep showing no suggestion, but add "your best recipe for this bag" to the Saved screen. It's a fact rather than advice, so it fits the current design.

My recommendation: if you've changed your mind and want a nudge now, go with 1, clearly labelled. Otherwise go with 3 until you have enough shots for 2. Which one do you want?

(This message is saved in `outputs/message-1.md`.)