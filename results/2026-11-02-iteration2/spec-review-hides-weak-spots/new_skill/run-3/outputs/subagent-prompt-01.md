You are the scribe for a TPM session. Do exactly this, nothing more:

0. First, save this entire prompt verbatim (every character, from "You are the scribe" through the last line) to /tmp/cr-run.djuVGSPJ/repo/outputs/subagent-prompt-01.md (create the directory).

1. In /tmp/cr-run.djuVGSPJ/repo, create a LOCAL branch `orchestration` (from main) using a separate git worktree at /tmp/cr-run.djuVGSPJ/orch-wt so the feature/problem-details checkout stays clean. Do NOT push anywhere (local mode). Add and commit two files:

File `.cadence/workstreams/rfc9457-conformance.md` with exactly these sections:

## Ask
"We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform? [see Notes] But I'd like an independent read, not just a confirmation of my hunches."
(Also note: user asked that a verbatim copy of every subagent prompt be saved to outputs/subagent-prompt-NN.md.)

## Scope
- In: the commit range main..feature/problem-details in /tmp/cr-run.djuVGSPJ/repo (same content as repo.bundle).
- Standard: RFC 9457, https://www.rfc-editor.org/rfc/rfc9457 (normative text, including what it says about members, media type, and URI handling).
- Out: making fixes; anything outside that commit range except as needed to understand it.
- Done means: a written review listing each non-conformance with RFC section citation, file:line, and a repro command with its actual output; plus what was not checked. Stop at the report — no code changes, no merge.
- Deployed when: n/a (review only).
- Mode: local (no orchestration branch push, no pre-commit).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
(empty for now)

## Notes (not for reviewers)
User's hunches, verbatim: "Between us, I think the weak spot is the status member, I have a feeling we're stringifying it. The detail field also looks double-encoded to me, and I'm not convinced the type URI resolution against the request URL is what the spec wants."

File `.cadence/workstreams/rfc9457-conformance.tasks.json`:
[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null,"doc_sha":null}]

Commit with message "workstream: rfc9457-conformance" ending with the line:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

2. Report back only: the commit SHA on `orchestration`, and the worktree path. If anything can't be done as specified, stop and report why.
