Not right now. That's on purpose: it was decided in the plan, not left out by accident.

**What the app does today.** After a shot it says where the shot landed and how it compares with the last one, but it doesn't say what to change. For example: "Ran fast at 22 s, outside the window", or "Inside the window, two seconds slower than Monday's shot" (`app/views.py:67`). The dial-in target chart shows the bag's shots against the 25–32 s, 1:1.8–2.3 window.

**What the CLI does.** `shots.suggest_next` (`src/coffeedata/shots.py:418`) uses a fixed rule: sour or fast means go finer by one step, bitter or slow means go coarser, and if the time is right but the ratio is off, it gives you a yield to aim for. The MCP server and the issue-form replies use it.

**Why the app doesn't show it.** `docs/app/PLAN.md` ("Later: a dial-in model", line 649) and the October 27 decisions table (line 674) both say grind suggestions are on hold until there's a model trained on your own shots. The reasoning: the rule is a rule of thumb that nobody has checked against your shots, and if the app showed it as a confident instruction it would mislead you often enough to matter. `docs/app/DESIGN.md:387` sets the same rule for the app's copy: no "go finer" or "try 11" until that model exists.

**Ways forward:**

1. **Wait for the dial-in model (what the plan says).** Once a bag has about 20 shots on one grinder, fit a small per-bag model of time and taste against grind, dose and days off roast. Test it against the rule of thumb on held-out shots, and only show its suggestion if it wins, with a range ("Try 11. Likely 26 to 30 s."). That's a real piece of work and needs the held-out evaluation CLAUDE.md asks for.
2. **Show the CLI's rule in the app now, clearly labeled as a rule of thumb.** For example, a line on Saved: "Rule of thumb: sour → finer, to 10.5." This is small to build, since `suggest_next` already exists. But it reverses a decision you recorded, so you'd need to agree to it, and the plan and design docs would need updating in the same change.
3. **Leave it as it is.** The CLI and MCP still give the advice when you want it.

I haven't changed anything. If you want option 2, I'll build it on a branch, update PLAN.md and DESIGN.md to match, and check it in the running app. I won't push it. If you want option 1, I'd start by counting how many shots per bag and grinder you have in the lake, to see whether there's enough data to train and test a model yet.
