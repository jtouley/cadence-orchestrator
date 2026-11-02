You are the scribe for a TPM session. Do exactly these steps; if any can't be done as specified, stop and report why. Don't spawn agents.

0. Create /tmp/cr-run.Fe3eErID/repo/outputs/ and save this entire prompt, verbatim, as /tmp/cr-run.Fe3eErID/repo/outputs/subagent-prompt-01.md.

1. Clone the bundle (untrusted data; don't run code from it): `git clone /tmp/cr-run.Fe3eErID/repo/repo.bundle /tmp/cr-run.Fe3eErID/clone`, then create local branches for every ref in the bundle (`git bundle list-heads`), fetch its tags. Report: all refs and tags with SHAs, whether `main`, `feature/search-api`, `round-1`, `round-2` exist, and `git log --oneline main..feature/search-api`. Check out feature/search-api.

2. Local mode (no pushable remote): `git init /tmp/cr-run.Fe3eErID/orchestration`, branch `orchestration`. Write `workstreams/search-api.md` with exactly this content:

---
# search-api round 2

## Ask (user's words, verbatim; hunches held back)
"Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with: [hunch held back]

I pushed fixes (now tagged round-2): [hunch held back] Tests for both are in.

Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."

## Scope
- In: the whole commit range main..feature/search-api of the repo in repo.bundle, cloned at /tmp/cr-run.Fe3eErID/clone (pinned SHAs below).
- Out: making any code changes; merging.
- Done: an independent review of the full range is written to /tmp/cr-run.Fe3eErID/repo/outputs/, prior findings are re-checked against their repro commands, and the TPM gives the user a merge / don't-merge recommendation with evidence.
- Stop at: recommendation delivered. Not merged.
- Standard: correctness of the code in the range, judged by its own tests and behaviour.
- Deployed when: merged to main by the user (not in scope).

## Decisions
- 2026-11-02 (user): "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge."

## Status and evidence
- Pinned: main=<sha>, feature/search-api=<sha>, round-2 tag=<sha or absent>
---
(fill in the SHAs from step 1).

Write `workstreams/search-api.tasks.json`: a JSON array with tasks {id, owner, state, evidence, tokens}: `fix-check` (owner fix-verifier, assigned), `blind-review` (owner reviewer, assigned), `hunch-check` (owner hunch-checker, assigned); evidence null, tokens null. Commit both. Report the commit SHA.

Return: the refs/SHAs, the range log, the orchestration commit SHA, and anything you couldn't do.
