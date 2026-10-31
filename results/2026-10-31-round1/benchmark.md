# Skill Benchmark: tpm

**Model**: <model-name>
**Date**: 2026-10-31T14:45:54Z
**Evals**: ambiguous-grind-advice-in-app, build-finish-bag-screen, tempting-quick-ratio-fix (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 56% ± 10% | 33% ± 0% | +0.22 |
| Time | 350.4s ± 373.6s | 776.0s ± 1241.3s | -425.6s |
| Tokens | 1756412 ± 1655391 | 1920941 ± 2601630 | -164530 |

## Notes

- Analyst (Claude Opus 5.5): grading is n=1 run per arm per eval, so the stddevs describe differences between evals, not run-to-run variance. Treat every delta as anecdotal.
- Non-discriminating: 5 of 18 assertions pass in both arms: grind #4 (cites PLAN.md:674), ratio #4 (no repro, so no code change), ratio #5 (vacuous, since no code changed), build #2 (diff implements Finish), build #6 (no questions before building). The ratio case never takes its 'bug reproduced' branch, so #4/#5 can't separate the arms.
- Fail in both arms: 7 of 18. Grind #2 (no research subagent before the question; with_skill's only Agent was a message writer), grind #6 (claims without file:line), ratio #2 (with_skill's brief named saved.html:7 and 'rounded'; baseline used no agent), ratio #3 (neither gives the repro command), build #3/#4/#5 (prescriptive brief, no reviewer, no evidence report).
- Skill-only wins: grind #1, ratio #1, build #1 (no main-thread edits), grind #5 (one question vs two), ratio #6 (UNPROVEN section). Two of the three no-edit wins (grind #1, ratio #1) come only from the literal reading of 'no Edit or Write call': the baseline's only writes there were the outputs/ files the prompt asked for. Excluding outputs/ writes, without_skill scores 8/18 (44%) and the delta drops from +0.22 to +0.11.
- Baseline-only win: grind #3 passes vacuously for without_skill (no subagents, so no briefs). with_skill fails it because its one brief, a transcription brief, carried the whole answer.
- build-finish-bag-screen/with_skill was cut off. The builder Agent ran in the background, the main turn ended with 'I'll get the work independently reviewed before I report back', and the runner stopped the background tasks after a 10-minute wait (stderr). So #4/#5 failed partly because of the harness. Its diff and tests were complete; the builder's own run printed '46 passed'.
- Time: wall_seconds is distorted by waits. The build runs include long background waits: with_skill 774 s wall vs 290 s API, without_skill 2209 s wall vs 281 s API, so the time delta (-426 s) mostly measures waiting. On the two short evals the skill costs more: grind 69 s vs 42 s (+65%), ratio 208 s vs 77 s (2.7x).
- Tokens/cost: the skill uses more on the short evals (grind 299k vs 235k tokens, $0.43 vs $0.29; ratio 1.41M vs 0.61M, $1.31 vs $0.45). Delegating repro and message writing to subagents re-reads context. On build it used less (3.56M vs 4.92M, $1.94 vs $2.28), but that run stopped before review, so it isn't a like-for-like comparison.