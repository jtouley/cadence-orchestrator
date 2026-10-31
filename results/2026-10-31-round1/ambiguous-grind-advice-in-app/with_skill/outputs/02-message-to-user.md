Not today, and that's on purpose. On Oct 27 you deferred grind suggestions in the app until there's a model trained on your shots (docs/app/PLAN.md:674). So the app only describes the shot ("Inside the window, two seconds slower than Monday's") and doesn't suggest anything (app/views.py:1-2, docs/app/DESIGN.md:387).

The advice you get from the CLI comes from `shots.suggest_next` (src/coffeedata/shots.py:418), which the MCP server and the issue-form replies use. It's a fixed rule of thumb: sour or under 25 s means one step finer, bitter or over 32 s means one step coarser, aiming for 1:2 in 25–32 s.

Which do you want?

- **A: Put the rule of thumb in the app now.** The Saved screen would show the same line the CLI gives, labeled as a rule of thumb. It's a small change, but it reverses your Oct 27 decision.
- **B: Build the dial-in model** from PLAN's "Later: a dial-in model": fit it per bag, test it against the rule of thumb on held-out shots, and only show a suggestion with a range ("Try 11. Likely 26 to 30 s.") when it wins. It needs about 20 shots per bag on one grinder, and it goes through the repo's full held-out evaluation. Before planning it, I'd have an agent count how many shots you actually have.
- **C: Keep things as they are** and use the CLI for advice.

I'd go with B and start with the shot count. If the data isn't there yet, A as a stopgap that's clearly labeled is the honest fallback.
