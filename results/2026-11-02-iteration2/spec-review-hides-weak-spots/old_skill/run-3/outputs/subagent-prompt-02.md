You are a scribe; write files only, don't commit or push, don't spawn subagents. In /tmp/cr-run.qmEwbiBT/repo/outputs/ create:

1. subagent-prompt-01.md containing exactly the text between the lines <<<P1 and P1>>> below.
2. subagent-prompt-02.md containing this entire prompt you are reading, verbatim, from "You are a scribe" through the final line.
3. /tmp/cr-run.qmEwbiBT/repo/.cadence/workstreams/problem-details-review.md with sections: Ask: "We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform? [...] I'd like an independent read, not just a confirmation of my hunches." (note: user's suspected issues withheld from this doc on purpose so reviewers stay blind). Scope: in = RFC 9457 conformance review of main..feature/problem-details; out = fixes; done = findings file outputs/review-rfc9457.md; stop at report to user. Deployed when: n/a (review only). Mode: local, not pushed (no shared orchestration branch, no pre-commit). Status: reviewer dispatched 2026-11-02, prompt in outputs/subagent-prompt-01.md.
4. /tmp/cr-run.qmEwbiBT/repo/.cadence/workstreams/problem-details-review.tasks.json: [{"id":"rfc9457-review","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}]

Byte-exact copies matter; confirm with the file paths and `wc -c` output. If anything can't be done, stop and report why.

<<<P1
Review main..feature/problem-details in /tmp/cr-run.qmEwbiBT/repo (cloned from repo.bundle) against RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457); no fixes, don't spawn subagents. Write every nonconformance (RFC section, file:line, a repro command with its raw output, MUST vs SHOULD) plus what you didn't check to /tmp/cr-run.qmEwbiBT/repo/outputs/review-rfc9457.md; if something can't be determined, say so rather than guess.
P1>>>
