First, save this entire prompt, verbatim from "First, save" to the end, to /tmp/cr-run.hszGdFxu/repo/outputs/subagent-prompt-04.md.

Wait (polling every ~15s, up to 25 minutes) until both /tmp/cr-run.hszGdFxu/repo/outputs/fix-check-round2.md and /tmp/cr-run.hszGdFxu/repo/outputs/review-round2.md exist and have stopped changing for 30s, then reply only "both present" or which one is missing at timeout. Don't open, read or edit either file or anything else in outputs/; don't spawn agents.
