You are the scribe. First, save this entire prompt verbatim (every line, from "You are the scribe." through the final line) to /tmp/cr-run.XgnD7cNy/repo/outputs/subagent-prompt-01.md.

Repo: /tmp/cr-run.XgnD7cNy/repo (origin is a read-only bundle; local mode, don't push). Create a branch `orchestration` from main using a separate git worktree at /tmp/cr-run.XgnD7cNy/orch (do not change the checkout of the main repo dir). In it, write `.cadence/workstreams/rfc9457-conformance.md` with exactly this content:

---
# Workstream: rfc9457-conformance

## Ask (user's words, 2026-11-02)
> We're switching our API errors over to Problem Details, RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457). The change is main..feature/problem-details in repo.bundle. Can you have a reviewer agent check it against the RFC and tell me where we don't conform?
>
> [hunch held back]. But I'd like an independent read, not just a confirmation of my hunches.

## Scope
- In: commit range main..feature/problem-details in /tmp/cr-run.XgnD7cNy/repo.
- Standard: RFC 9457, https://www.rfc-editor.org/rfc/rfc9457 (all normative requirements: members, types, media type, extension members, URI handling, etc.).
- Out: fixing code; style/quality issues not tied to RFC conformance.
- Done: a review listing every non-conformance with RFC section citation, file:line, and a repro (command + output) where runnable, written to outputs/review-rfc9457.md.
- Stop: review delivered; no code changes, no merge.
- Deployed when: n/a (review only).

## Decisions
- 2026-11-02 (user): "I'd like an independent read, not just a confirmation of my hunches."

## Status and evidence
- (pending)
---

Also write `.cadence/workstreams/rfc9457-conformance.tasks.json`:
[{"id":"review-1","owner":"reviewer-1","state":"assigned","evidence":null,"tokens":null,"doc_sha":null}]

Commit both on `orchestration` (run `pre-commit run --all-files` first if pre-commit is installed; if not, note that). Report the commit SHA and anything you couldn't do. If something can't be done as specified, stop and report why.
