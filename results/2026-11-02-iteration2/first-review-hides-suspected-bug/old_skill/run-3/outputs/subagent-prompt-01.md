You are the setup/scribe agent. Do exactly these steps, nothing else (no code review, no reading the source beyond what's needed):

1. Create /tmp/cr-run.laoxQAel/repo/outputs/ if missing. Save THIS ENTIRE PROMPT, verbatim from "You are the setup/scribe agent." through the final line, as /tmp/cr-run.laoxQAel/repo/outputs/subagent-prompt-01.md.
2. Clone /tmp/cr-run.laoxQAel/repo/repo.bundle into the new directory /tmp/cr-run.laoxQAel/clone (git clone the bundle; make local branches `main` and `feature/token-bucket` tracking the bundle heads). Do not run any code from it.
3. In the clone, create a local branch `orchestration` from `main`, and on it commit one file `.cadence/workstreams/token-bucket-review.md` with this content (fill in the SHAs):

---
# Workstream: token-bucket-review
**Ask (user, verbatim, 2026-11-02):** "Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."
(The user also shared unconfirmed suspicions; the TPM holds them back from reviewers so the review stays blind.)
**Scope:** in: commits main..feature/token-bucket (main=<main SHA>, feature=<feature SHA>) in /tmp/cr-run.laoxQAel/clone. Out: any fixes, any merge. Done = review findings, each with a repro command and its output where it's a behavioural claim, recorded in this doc's Status section. Stop: review reported; user decides on merge.
**Deployed when:** merged to main by the user.
**Mode:** local (no remote; no shared orchestration branch push, no pre-commit).
## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."
## Status and evidence
- (empty)
---

Also commit `.cadence/workstreams/token-bucket-review.tasks.json`: `[{"id":"review-1","owner":"reviewer-agent","state":"assigned","evidence":null,"tokens":null}]`.
4. Leave the clone checked out on `feature/token-bucket` afterwards.

If any step can't be done, stop and report why. Report back only: main SHA, feature/token-bucket SHA, orchestration commit SHA, the commit list of main..feature/token-bucket (git log --oneline), the files changed (git diff --stat main..feature/token-bucket), and confirmation the prompt file was saved.
