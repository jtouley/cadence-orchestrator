The app can't do that yet, and that's on purpose. I haven't changed anything.

**Where the CLI's advice comes from:** `coffeedata shot` prints its reply, and the reply ends with the output of `shots.suggest_next` (`src/coffeedata/shots.py:418`). That's a fixed rule of thumb applied to your last shot:
- sour, or faster than 25 s: one grind step finer;
- bitter, or slower than 32 s: one step coarser;
- ratio off: a yield to aim for.

It also names your best-rated shot of that coffee. The MCP server uses the same function.

**Why the app doesn't show it:** in the October 27 decisions in `docs/app/PLAN.md`, you put grind suggestions in the app on hold until there's a model trained on your own shots. The reason given under "Later: a dial-in model" is that the rule of thumb isn't learned from your shots, so a confident-looking suggestion from it would often be wrong. `app/views.py` and `docs/app/DESIGN.md` follow that: the app describes each shot and suggests nothing.

**Which way do you want to go?**

1. **Show the rule of thumb in the app, labeled as one.** For example, on the Saved screen: "Rule of thumb: sour and fast, so try 14 (one step finer)." This is a small change because the logic already exists. It needs a view, tests, and edits to PLAN and DESIGN. It does reverse your October 27 decision. I'd word it as a rough guide and wouldn't pre-fill the grind field with it.
2. **Build the dial-in model the plan describes.** It would predict time and taste for each bag from grind, dose and days since roast. The app would show it only if it beats the rule of thumb on shots held back for testing, and with a range ("Try 11. Likely 26 to 30 s."). This is the real fix, but it needs about 20 shots of one coffee on one grinder, and the full held-out testing that CLAUDE.md requires. I'd start by checking whether your shot log has enough data yet.
3. **Leave the app as it is** and use the CLI or MCP when you want advice.

If you want advice on your phone soon, I'd do option 1 now and replace it with option 2 once there's enough data.

This reply is saved in `outputs/message-1.md`.