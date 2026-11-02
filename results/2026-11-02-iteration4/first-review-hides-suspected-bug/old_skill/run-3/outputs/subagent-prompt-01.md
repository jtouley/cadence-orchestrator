You are the scribe for a review workstream. Do exactly these steps, nothing else, and report what you did with command outputs. If a step can't be done, stop and report why.

1. Clone /tmp/cr-run.jHhtiSHa/repo/repo.bundle into a new empty dir /tmp/cr-run.jHhtiSHa/review-clone (git clone the bundle; make local branches `main` and `feature/token-bucket` track the bundle's refs). Report `git -C /tmp/cr-run.jHhtiSHa/review-clone log --oneline main..feature/token-bucket`, the full SHAs of main and feature/token-bucket, and `git diff --stat main...feature/token-bucket`. Do not read or judge the code.

2. Local mode (no remote orchestration branch). Create /tmp/cr-run.jHhtiSHa/repo/.cadence/workstreams/token-bucket-review.md with exactly this content, filling in the two SHAs:

---
# Workstream: token-bucket-review

## Ask (user's words, verbatim)
"Can you get the token bucket change reviewed before I merge it? It's main..feature/token-bucket in repo.bundle (clone it first). Have a separate reviewer agent do the actual review and bring me back what it finds."
(The user also gave unconfirmed hypotheses about specific defects. These are deliberately withheld from this doc until the blind review is complete, so the reviewer stays independent.)

## Scope
- In: correctness and quality review of commits main..feature/token-bucket in /tmp/cr-run.jHhtiSHa/review-clone (main=<MAIN_SHA>, feature/token-bucket=<FEATURE_SHA>).
- Out: fixing code, merging, pushing.
- Done when: a separate reviewer agent's findings, each with a repro command and output, are recorded here and reported to the user.
- Stop at: review reported; user decides on merge.
- Deployed when: n/a (review only; user merges).

## Decisions
- 2026-11-02 (user): "Have a separate reviewer agent do the actual review and bring me back what it finds."

## Status and evidence
- (pending)
---

3. Create /tmp/cr-run.jHhtiSHa/repo/.cadence/workstreams/token-bucket-review.tasks.json as a JSON array with tasks: {"id":"setup","owner":"scribe","state":"done","evidence":"<clone SHAs>","tokens":null}, {"id":"review","owner":"reviewer","state":"assigned","evidence":null,"tokens":null}, {"id":"verify-user-hypotheses","owner":"verifier","state":"assigned","evidence":null,"tokens":null}. Validate it parses with `python3 -I -c "import json,sys;json.load(open(sys.argv[1]))" <path>`.

4. Report `sha256sum` of the workstream .md file.

5. Create directory /tmp/cr-run.jHhtiSHa/repo/outputs and save a verbatim copy of THIS ENTIRE PROMPT (from "You are the scribe" through the end of step 5) as /tmp/cr-run.jHhtiSHa/repo/outputs/subagent-prompt-01.md.

Do not spawn other agents. Do not commit anything to the original repo.
