No, not yet, and that was a deliberate choice, not something that got missed. I haven't changed anything.

**Where it stands**
- The CLI, the MCP server and the issue form all use `shots.suggest_next` (`src/coffeedata/shots.py:418`). It's a rule of thumb aiming for about 1:2 in 25–32 s: a sour or fast shot means one step finer, a bitter or slow one means one step coarser.
- The app only describes the shot ("Inside the window, two seconds slower than Monday's shot") and never suggests a grind. The README's comparison table also marks "Advice for the next shot" as **no** for the app.
- You decided this on October 27 (`docs/app/PLAN.md:674`): *"Grind suggestions: deferred until there's a model trained on the owner's shots."* The reason, in `PLAN.md:649`: the rule has never been checked against your shots, and showing it in the app as a confident suggestion would mislead you too often.
- The plan's bar for turning it on:
  - about 20 shots of one coffee on one grinder;
  - a small model per bag that predicts the next shot better than the rule on shots it wasn't fitted to;
  - advice that says how sure it is ("Try 11. Likely 26 to 30 s.").

The repo's CLAUDE.md also says any change judged by "how often is it right" gets measured on held-out data before it ships. Putting the rule in the app would be that kind of change.

**Options**
1. **Stick with the plan (my recommendation if you're happy to wait).** I'd first check whether you have enough shots per coffee and grinder yet. Then I'd score the rule on your own shots: when it said "go finer", did the next shot actually improve? That tells us whether the rule is any good, and gives a model a score to beat.
2. **Show the CLI's advice in the app now, labelled as a rule of thumb**, for example on the Saved screen under the description. It's quick to build, but it reverses the October 27 decision, so it's your call. I'd still run the check from option 1 first, so we know how often the rule is wrong before it's on screen.
3. **In between:** a "What would the CLI say?" link on the shot page that shows the rule's advice only when you tap it, so it doesn't look like the app's own advice.

Which would you like? And has your view on waiting changed, or did you just not know it was deferred?

I saved this message to `outputs/reply-01.md`.