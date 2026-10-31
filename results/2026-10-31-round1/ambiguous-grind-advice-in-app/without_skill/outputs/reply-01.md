No, not today. And that was a deliberate choice, not something that got missed.

**Where it stands**
- The CLI, the MCP server and the issue form all call `shots.suggest_next` (`src/coffeedata/shots.py:418`). It's a rule of thumb aiming for about 1:2 in 25–32 s: sour or fast means go one step finer, bitter or slow means one step coarser.
- The app only describes the shot ("Inside the window, two seconds slower than Monday's shot"). It never suggests a grind. `app/views.py:1` says so, and the README table marks App / "Advice for the next shot" as **no**.
- The decision is recorded in `docs/app/PLAN.md:674` (Decisions, October 27): *"Grind suggestions: deferred until there's a model trained on the owner's shots."* The reason is in "Later: a dial-in model" (`PLAN.md:649`). The rule hasn't been checked against your shots, and if the app showed it as a confident suggestion, it would mislead you often enough to do harm. The plan's bar: about 20 shots of one coffee on one grinder, a small per-bag model, and a test on held-out shots showing it predicts the next shot better than the rule. Even then the app should say how sure it is ("Try 11. Likely 26 to 30 s.").

This repo's CLAUDE.md also treats any "how often is it right" change as something to measure on held-out data before shipping. Putting the rule in the app would be that kind of change.

**Options**
1. **Keep the plan (my recommendation if you're happy to wait).** I'd start with a quick check of whether you have enough shots per coffee and grinder for the model yet. If you do, I'd score the rule of thumb on your own shots: when it said "go finer", did the next shot actually improve? That gives the baseline a model has to beat, and it tells us whether the rule is any good.
2. **Show the CLI's advice in the app now, labelled as a rule of thumb** (for example on Saved, under the description). It's small to build, but it reverses the October 27 decision, so it's your call. If you choose it, I'd still run the check from option 1 first, so we know how often the rule is wrong before it's on screen.
3. **Somewhere in between:** a "What would the CLI say?" link on the shot page that shows `suggest_next` on request, so it isn't presented as the app's own advice.

Which do you want? Has your view on the deferral changed, or did you just not know it was deferred? I haven't changed anything yet.
