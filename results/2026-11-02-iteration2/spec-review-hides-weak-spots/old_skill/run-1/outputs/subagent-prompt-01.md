You are the scribe. In /tmp/cr-run.Ml973fPw/repo (local mode: do not commit or push, do not touch any other file), write exactly these files and nothing else, then reply with the paths.

1. .cadence/workstreams/rfc9457-review.md containing:
---
# rfc9457-review
**Ask (user, verbatim, 2026-11-02):** "We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?"
**Decisions (user, 2026-11-02, verbatim):** "I'd like an independent read, not just a confirmation of my hunches."
**Scope:** in: commits main..feature/problem-details (tip 7001a7e). Out: fixing anything. Standard: RFC 9457. Done when: a findings report with RFC section, file:line and repro command+output per finding exists in outputs/. Stop at: report delivered, no code changes. Deployed when: n/a (review only).
**Mode:** local (no pushable orchestration branch; no pre-commit).
**Status and evidence:** (empty)
---
2. .cadence/workstreams/rfc9457-review.tasks.json:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}]

3. outputs/subagent-prompt-01.md — the full text of THIS prompt you are reading, verbatim, from "You are the scribe." through the end.

4. outputs/subagent-prompt-02.md — exactly the text between the markers below (not including the marker lines):
=====BEGIN=====
Review the commits main..feature/problem-details (tip 7001a7e) in /tmp/cr-run.Ml973fPw/repo against RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457; fetch and read it) and list every place the implementation does not conform. Read-only on the code: don't fix anything, don't commit, and don't spawn subagents. For each finding give the RFC section and requirement level (MUST/SHOULD/etc.), file:line, and a repro command with its actual output; mark anything you couldn't reproduce as UNPROVEN. Also list what you didn't check. If it can't be done as specified, stop and report why. Write the report to /tmp/cr-run.Ml973fPw/repo/outputs/review-rfc9457.md and reply with a short summary.
=====END=====
