No, the app doesn't tell you what to change after a shot, and that's on purpose. You decided to hold off on grind suggestions until there's a model trained on your own shots. That decision is written down in `docs/app/PLAN.md` ("Grind suggestions: Deferred…" and "Later: a dial-in model") and in `DESIGN.md`. A test also checks that the app never says "finer", "coarser" or "Try N" (`tests/test_app.py::test_save_shows_saved_and_today_without_grind_advice`). The app only describes each shot: how it compares with the last one, the time and ratio window, and your best recipe.

The CLI's advice comes from `shots.suggest_next`. It looks only at your last shot of that coffee: if it was sour or fast, go finer; if bitter or slow, go coarser; if the ratio is off, change the yield. It can't simply be wired into the app as it is:

- **It reads every account's shots of a coffee.** In a test run with your shot at grind 11 and another account's at 40, it said "go finer to -18". It also showed the other person's shot as "your best-rated shot".
- **It mixes grinders.** The CLI will hit the same bug with only your data once you log one coffee on two grinders.
- **It guesses the grind step.** It uses the gap between any two logged settings, not your grinder's actual step.

**One decision from you:** (A) undo the hold and add rule-of-thumb advice to the app now, limited to your shots on that grinder and bag; or (B) keep the hold and build toward the dial-in model?

If A, I'll come back with a couple of smaller choices: a direct "go finer to 10" versus a hint you tap to see, and whether to fix the CLI's rule as well.

Nothing in the code has changed. The findings and test output are on the local `orchestration` branch (commit `0804382`, `workstreams/grind-advice.md`). Nothing was pushed. Every brief and this message are saved in `outputs/` (01–03).