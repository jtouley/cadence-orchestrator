**No, not yet. You decided that.** On Oct 27 you put grind suggestions in the app on hold until there's a dial-in model trained on your own shots (`docs/app/PLAN.md:674`, and "Later: a dial-in model" at `docs/app/PLAN.md:649`). The plan gives the reason: the CLI's rule ("sour or fast, go finer") is a rule of thumb, not something learned from your shots. A confident-looking suggestion from it would be wrong often enough to mislead you.

For now, the app describes each shot ("Inside the window, two seconds slower than Monday's shot") and suggests nothing. `shots.suggest_next` still gives suggestions through the MCP server and the issue-form replies.

Which one do you want?
- **A.** Keep it on hold.
- **B.** Reverse the Oct 27 decision and show the CLI's rule in the app now, clearly labeled as a rule of thumb.
- **C.** Start building the dial-in model. The plan says it needs about 20 shots per bag on one grinder. It also has to predict held-out shots better than the rule of thumb before the app shows anything from it.

I've only read the plan, not the code. If you pick B or C, the first agent will start by checking where the app actually stands.