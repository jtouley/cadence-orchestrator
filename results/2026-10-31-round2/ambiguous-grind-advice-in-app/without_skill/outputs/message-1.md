Not right now, and that was a deliberate choice, not a gap. I haven't changed anything.

**Where the CLI advice comes from:** `coffeedata shot` prints `shots.issue_reply`, which ends with
`shots.suggest_next` (`src/coffeedata/shots.py:418`). That function is a fixed rule of thumb applied to the last
shot: sour or faster than 25 s means one grind step finer, bitter or slower than 32 s means one step coarser, and if
the ratio is off it tells you a yield to aim for. It also names your best-rated shot of that coffee. The MCP server
uses the same function.

**Why the app doesn't show it:** in the October 27 decisions (`docs/app/PLAN.md`, "Grind suggestions") you put grind
suggestions in the app on hold until a model trained on your own shots exists. The reasoning in "Later: a dial-in
model" is that the rule of thumb isn't learned from your shots, and a confident-looking suggestion from it would
mislead you often enough to do harm. `app/views.py` and `docs/app/DESIGN.md` say the same: the app describes each
shot ("Inside the window, two seconds slower than Monday's shot") and suggests nothing.

**Three ways to go. Which do you want?**

1. **Show the rule of thumb in the app, clearly labeled as one.** For example, on the Saved screen: "Rule of thumb:
   sour and fast, so try 14 (one step finer)." This is small: the logic already exists, and it needs a view, tests
   and edits to PLAN and DESIGN. It goes back on the October 27 decision, so it's your call. I'd word it as a
   heuristic and never pre-fill the grind field with it.
2. **Build the dial-in model the plan describes.** This means a per-bag regression of time and taste on grind, dose
   and days off roast. It's shown only when it beats the rule of thumb on held-out shots, and with a range ("Try 11.
   Likely 26 to 30 s."). It's the real fix, but it needs about 20 shots of one coffee on one grinder, and it needs
   the full measured process from CLAUDE.md (split, held-out comparison, intervals). I'd start by checking whether
   your shot log has enough data yet.
3. **Leave the app as it is.** Use the CLI or MCP `suggest_next` when you want advice.

If you just want the CLI's advice on your phone now, option 1 is the quick route, and option 2 can replace it later.
