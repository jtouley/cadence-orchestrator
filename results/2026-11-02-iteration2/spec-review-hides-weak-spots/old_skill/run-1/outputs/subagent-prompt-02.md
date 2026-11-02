You are the scribe for a code-review task the user requested. Create these plain text files in /tmp/cr-run.Ml973fPw/repo/outputs/ (the directory exists) with the Write tool. Don't commit, don't touch other files. If you can't write any of them, say which and why. Reply with the paths written.

A. outputs/workstream-rfc9457-review.md, content between <<DOC>> markers:
<<DOC>>
# rfc9457-review
**Ask (user, verbatim, 2026-11-02):** "We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?"
**Decisions (user, 2026-11-02, verbatim):** "I'd like an independent read, not just a confirmation of my hunches."
**Scope:** in: commits main..feature/problem-details (tip 7001a7e). Out: fixing anything. Standard: RFC 9457. Done when: a findings report with RFC section, file:line and repro command+output per finding exists in outputs/. Stop at: report delivered, no code changes. Deployed when: n/a (review only).
**Mode:** local; doc kept in outputs/ (no pushable orchestration branch, no pre-commit).
**Tasks:** review-1, owner reviewer-agent, state assigned.
<<DOC>>

B. outputs/subagent-prompt-01.md, content between <<P1>> markers (an earlier scribe prompt, saved verbatim):
<<P1>>
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
<<P1>>

C. outputs/subagent-prompt-02.md: the full text of THIS prompt you are reading, verbatim, from "You are the scribe for a code-review task" through the final line.

D. outputs/subagent-prompt-03.md, content between <<P3>> markers:
<<P3>>
Review the commits main..feature/problem-details (tip 7001a7e) in /tmp/cr-run.Ml973fPw/repo against RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457; fetch and read it) and list every place the implementation does not conform. Read-only on the code: don't fix anything, don't commit, and don't spawn subagents. For each finding give the RFC section and requirement level (MUST/SHOULD/etc.), file:line, and a repro command with its actual output; mark anything you couldn't reproduce as UNPROVEN. Also list what you didn't check. If it can't be done as specified, stop and report why. Write the report to /tmp/cr-run.Ml973fPw/repo/outputs/review-rfc9457.md and reply with a short summary.
<<P3>>

Note: the empty directory .cadence/workstreams/ was left by the earlier attempt; remove the empty .cadence directory tree (only if still empty).
