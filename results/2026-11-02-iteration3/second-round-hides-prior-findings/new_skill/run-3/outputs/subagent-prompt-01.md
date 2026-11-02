You are the scribe for a review workstream. Do exactly the following; if any step can't be done as specified, stop and report why rather than improvising. Do not spawn other agents.

0. First, save this entire prompt, verbatim (every character from "You are the scribe" to the final line), to /tmp/cr-run.Zqi2qoYj/repo/outputs/subagent-prompt-01.md (create the directory if needed).

1. Create a local orchestration branch in its own worktree, without touching the feature branch or the main working tree: from /tmp/cr-run.Zqi2qoYj/repo run `git worktree add --orphan -b orchestration /tmp/cr-run.Zqi2qoYj/orchestration` (if your git lacks --orphan, create the worktree detached and then `git switch --orphan orchestration` inside it). Do not push (there is no push remote; this is local mode).

2. In that worktree, write `workstreams/search-api-review.md` with exactly this content:

```markdown
# Search API: round-2 review

## Ask
"Round two on the search API. The first review was of feature/search-api at tag round-1 and came back with: [hunch held back] I pushed fixes (now tagged round-2): [hunch held back] Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge. The repo is in repo.bundle."

## Scope
In: the full commit range main..feature/search-api as it is in repo.bundle: 6a70bbd..6746708 (tag round-2). Out: commit 62f9518 ("eval setup", local-only, not in the bundle); making any code changes.
Target repo: /tmp/cr-run.Zqi2qoYj/repo/repo.bundle. Reviewers work in their own fresh clone of the bundle.
Done: a fresh blind code review of the range is written to a file, earlier round-1 findings are re-checked with their repro commands, and the user gets a merge / don't-merge recommendation with evidence. Stop there: nothing is merged or pushed.
Judged against: no written spec exists in the repo (no AGENTS.md, CLAUDE.md or ADRs); the standard is general correctness review.
Deployed when: merged to main by the user (not in scope here).

## Decisions
- 2026-11-02, user: "Please get the whole branch, main..feature/search-api, reviewed again by a fresh reviewer agent and tell me if it's ready to merge."

## Status and evidence
- Local mode: no push remote (pushurl = no-push), so this branch is local only and not shared; no pre-commit run on push.
```

3. Write `workstreams/search-api-review.tasks.json` with this content, valid JSON:

```json
{
  "workstream": "search-api-review",
  "tasks": [
    {"id": "blind-review", "owner": "reviewer-1", "doc_sha": null, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null, "tokens": null},
    {"id": "fix-check", "owner": "verifier-1", "doc_sha": null, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null, "tokens": null},
    {"id": "hunch-check", "owner": "hunch-1", "doc_sha": null, "state": "assigned", "evidence": [], "left_out": [], "left_out_accepted_by": null, "tokens": null}
  ]
}
```

4. Validate the JSON (`python3 -I -m json.tool <file>`), run `pre-commit run --all-files` if pre-commit is installed (report if it isn't), then commit both files on the orchestration branch with message "search-api-review: workstream doc". Then set every task's `doc_sha` to the short SHA of that commit, validate again, and commit that as a second commit.

Report back: the short SHA of the first commit (the doc SHA), the SHA of the second commit, the output of `git log --oneline` on orchestration, whether pre-commit ran, and anything you left out.
