# Workstream files

Each workstream has two files on the `orchestration` branch, written by the scribe agent:

- `workstreams/<slug>.md`: the ask (verbatim), scope, the user's decisions (verbatim, dated), status and links
  to evidence, then the user's hunches under `## Notes (not for reviewers)`. Prose, for people.
- `workstreams/<slug>.tasks.json`: task status, for agents and for checking mechanically.

## The doc

```markdown
# Finish a bag
## Ask
"Let me mark a bag finished from its detail screen. [see Notes]"
## Scope
In: the detail screen. Out: the bag list. Done: PR opened, not merged. Judged against DESIGN.md#bags.
Deployed when: merged to main.
## Decisions
- 2026-11-02, user: "No undo for now."
## Status and evidence
## Notes (not for reviewers)
- From the ask, user: "I think the finish button is hidden behind the keyboard on small phones."
```

Notes hold the user's suspected causes, weak spots and earlier findings, verbatim, so nothing they said is lost.
Reviewers are told to read Ask, Scope and Decisions only, and nobody copies Notes into an agent's prompt: a
reviewer who knows the user's suspicion checks that and misses the rest.

## tasks.json

```json
{
  "workstream": "finish-bag",
  "tasks": [
    {
      "id": "build-finish-screen",
      "owner": "builder-1",
      "doc_sha": "3f2a1c9",
      "state": "done",
      "evidence": ["https://github.com/<owner>/<repo>/pull/57", "a1b2c3d"],
      "left_out": ["No animation on the finish button (doc says optional)"],
      "left_out_accepted_by": "reviewer-1",
      "tokens": 182400
    },
    {
      "id": "spec-review",
      "owner": "reviewer-1",
      "doc_sha": "3f2a1c9",
      "state": "claimed",
      "evidence": [],
      "left_out": [],
      "left_out_accepted_by": null,
      "tokens": null
    }
  ]
}
```

- `id`: short and stable. `owner`: exactly one agent, or `null` while unassigned.
- `doc_sha`: the commit of `workstreams/<slug>.md` the dispatch prompt cited (`<slug>.md@<sha>`), so what the
  agent was asked to do can be read back exactly.
- `state`: `assigned`, `claimed`, `blocked` or `done`. A `blocked` task carries the reason in `evidence`
  (what was tried, the command and its output).
- `evidence`: SHAs, PR or comment links, `command → output` excerpts. **A `done` task must have at least one.**
- `left_out`: what the worker says it skipped or didn't finish (an empty list means "nothing"). The reviewer
  judges it; `left_out_accepted_by` names that reviewer. **`done` needs evidence and an accepted `left_out`.**
- `tokens`: total tokens the delegated agent reported spending, or `null` if the platform doesn't report it.
- Optional, for measuring delivery (`npx cadence-orchestrator dora`): `committed_at`, `merged_at`, `deployed_at`
  (ISO 8601 with a timezone, e.g. `2026-11-02T09:30:00Z`, in that order; "deployed" as the doc's **Deployed
  when:** line defines it), and `kind`: `planned` or `fix`. A `fix` names what it fixes in `fixes`: the version
  it repairs (`"0.1.0"`) or a task id, and optionally `fixed_in`: the version that shipped the fix.

The scribe rewrites the whole file on each update (no hand-merged fragments) and validates it as JSON before
pushing.

## Enforcing it

- **The guard** (Claude Code and Copilot): a subagent `Write`, `Edit` or `MultiEdit` that would leave an invalid
  `*.tasks.json` is denied; see `guard.md`. Shell-built files aren't covered.
- **pre-commit on the orchestration branch**: the scribe runs `pre-commit run --all-files` before every push,
  with this `.pre-commit-config.yaml` committed on that branch:

  ```yaml
  repos:
    - repo: https://github.com/gitleaks/gitleaks
      rev: v8.30.1
      hooks: [{id: gitleaks}]
    - repo: https://github.com/jtouley/cadence-orchestrator
      rev: <release tag or commit SHA>
      hooks: [{id: cadence-leak-check}, {id: cadence-tasks-check}]
  ```

  `cadence-tasks-check` runs `scripts/tasks_check.py` on `workstreams/*.tasks.json`; `cadence-leak-check` blocks
  email addresses, account UUIDs and session log paths. Both need pre-commit 4.4.0 or later.
