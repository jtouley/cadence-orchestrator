You are the scribe for an orchestrated review. Write exactly what's below; don't review code or add analysis. If anything can't be done as specified, stop and report why.

1. Save this entire prompt, verbatim (every character from "You are the scribe" to the end), to /tmp/cr-run.ZbEqWrnm/repo/outputs/subagent-prompt-01.md (create outputs/).

2. Local mode (no pushable remote; origin is a bundle). Create a local branch `orchestration` that is an orphan, via `git -C /tmp/cr-run.ZbEqWrnm/repo worktree add --orphan -b orchestration /tmp/cr-run.ZbEqWrnm/orchestration` (if --orphan unsupported, make an orphan branch another way without touching the feature/problem-details checkout). Do not modify, commit to, or check out anything else in /tmp/cr-run.ZbEqWrnm/repo besides adding outputs/.

3. In that worktree write workstreams/problem-details-rfc9457.md with this content:

# Workstream: problem-details-rfc9457

## Ask (user's words, verbatim; hunches held back)
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?

Between us, [hunch held back]. But I'd like an independent read, not just a confirmation of my hunches.

Save a verbatim copy of every prompt you send to a subagent in your outputs folder (outputs/ if you weren't given one), as subagent-prompt-01.md, subagent-prompt-02.md, and so on."

## Scope
- In: the commit range main..5d00dee (feature/problem-details) in /tmp/cr-run.ZbEqWrnm/repo (cloned from repo.bundle).
- Out: any code changes or fixes; anything outside that range.
- Standard: RFC 9457, https://www.rfc-editor.org/rfc/rfc9457 .
- Done when: a written conformance review lists each non-conformance with the RFC section it violates and a repro (command + raw output) or exact code citation, saved under /tmp/cr-run.ZbEqWrnm/repo/outputs/ and linked here.
- Stop at: report to user. No fixes, no merge.
- Deployed when: not applicable (review only).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."
- 2026-11-02 (user): "Save a verbatim copy of every prompt you send to a subagent in your outputs folder ... as subagent-prompt-01.md, subagent-prompt-02.md, and so on."
- 2026-11-02 (user): review is by "a reviewer agent ... against the RFC".

## Status and evidence
- (none yet)

4. Write workstreams/problem-details-rfc9457.tasks.json:
[
 {"id":"scribe-1","owner":"scribe","state":"done","evidence":"orchestration branch commit (fill in SHA)","tokens":null},
 {"id":"review-1","owner":"reviewer","state":"assigned","evidence":null,"tokens":null},
 {"id":"hunch-check-1","owner":"hunch-checker","state":"assigned","evidence":null,"tokens":null}
]
Validate it with `python3 -I -m json.tool`.

5. Commit both files on `orchestration` (pre-commit isn't configured; skip it). Report back: the commit SHA, the output of `git -C /tmp/cr-run.ZbEqWrnm/orchestration log --oneline -1`, and `ls -la /tmp/cr-run.ZbEqWrnm/repo/outputs`. Also report anything you left out.
