Not right now, and that's by your own call: PLAN.md, Decisions (Oct 27): "Grind suggestions: Deferred until there's a model trained on the owner's shots." The Saved screen describes the shot ("Ran fast at 22 s, outside the window") but says nothing about what to change. The CLI/MCP advice comes from `shots.suggest_next`, a rule of thumb ("sour or fast, go finer"). The plan judged it wrong too often to show with confidence.

Three options:
- **A. Keep it.** The app stays descriptive.
- **B. Reverse the decision now.** Show `suggest_next`'s line on Saved, marked as a rule of thumb, not a prediction. A small change: an agent builds it on a local branch (no push or PR, per the sandbox) and a separate reviewer checks it.
- **C. Build the dial-in model** ("Later" in PLAN.md). It gets measured against the rule of thumb on held-out shots, per CLAUDE.md. It needs about 20 shots per coffee on one grinder, so step one is checking whether your shots have that.

B gets you what you asked for today. C is the real fix. B now and C later also works. A, B, or C?
