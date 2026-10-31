No, the app can't do that yet, and that was your decision. In `docs/app/PLAN.md`, under Decisions (Oct 27), you wrote: *"Grind suggestions: Deferred until there's a model trained on the owner's shots."* After you save a shot, the app describes it ("Ran fast at 22 s, outside the window") but doesn't say what to change.

The CLI's advice comes from `shots.suggest_next`, which is a rule of thumb: "sour or fast, go finer." The plan decided it's wrong too often to show as if it were reliable.

You have three options:

- **A. Keep it as is.** The app keeps describing shots without advice.
- **B. Reverse the decision now.** The screen after saving shows the CLI's line, labelled as a rule of thumb rather than a prediction. It's a small change. An agent would build it on a local branch (no push or PR, since this is a sandbox) and a separate reviewer would check it.
- **C. Build the dial-in model** described under "Later" in PLAN.md. It would be tested against the rule of thumb on shots it hasn't seen, as CLAUDE.md requires. It needs about 20 shots of one coffee on one grinder, so the first step is checking whether you have that many.

B gives you what you asked for today, and C is the real fix. You could also do B now and C later.

**A, B or C?**

Nothing has been built or changed yet. This message is saved in `outputs/01-message-to-user.md`, and the brief I gave the agent that wrote it is in `outputs/01-brief-writer.md`.