Not today. The app doesn't suggest a change, and that's on purpose. In your decisions of October 27 you wrote: "Grind suggestions: Deferred until there's a model trained on the owner's shots" (docs/app/PLAN.md, Decisions table, and "Later: a dial-in model"). The Saved and Today screens only describe the shot ("Inside the window, two seconds slower than Wednesday's shot."). A test fails the build if they say "finer", "coarser" or "Try N" (tests/test_app.py::test_save_shows_saved_and_today_without_grind_advice). I checked both of those myself.

The CLI's advice comes from `shots.suggest_next`. It's a fixed rule of thumb, not Claude: sour or fast means one step finer, bitter or slow means one step coarser, against 1:1.8 to 1:2.3 in 25 to 32 s. It also points you to your best-rated shot of that coffee. An agent ran it on a throwaway lake and got "It ran fast (21 s): go finer to 14…".

Bringing it to the app isn't just a copy:
- `suggest_next` reads every user's shots and doesn't separate grinders, so it would need a per-user, per-grinder version.
- The no-advice test and the PLAN decision would have to be reversed.
- Under CLAUDE.md, a rule whose advice reaches you counts as "how often is it right". So it needs a held-out eval before it ships, and no eval for shot advice exists yet.

Which one?
A. Leave it as decided: no advice in the app.
B. Show the CLI's rule of thumb in the app, after an eval on your shots shows how often it's right.
C. Start the dial-in model from PLAN.md, scored against the rule of thumb on held-out shots.

I haven't started anything beyond the read-only check, and nothing was changed or pushed.
