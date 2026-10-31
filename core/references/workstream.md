# Workstream files

Each workstream has two files on the `orchestration` branch, written by the scribe agent:

- `workstreams/<slug>.md`: the ask (verbatim), scope, the user's decisions (verbatim, dated), status and links
  to evidence. Prose, for people.
- `workstreams/<slug>.tasks.json`: task status, for agents and for checking mechanically.

## tasks.json

```json
{
  "workstream": "finish-bag",
  "tasks": [
    {
      "id": "build-finish-screen",
      "owner": "builder-1",
      "state": "done",
      "evidence": ["https://github.com/<owner>/<repo>/pull/57", "a1b2c3d"],
      "tokens": 182400
    },
    {
      "id": "spec-review",
      "owner": "reviewer-1",
      "state": "claimed",
      "evidence": [],
      "tokens": null
    }
  ]
}
```

- `id`: short and stable. `owner`: exactly one agent, or `null` while unassigned.
- `state`: `assigned`, `claimed`, `blocked` or `done`. A `blocked` task carries the reason in `evidence`
  (what was tried, the command and its output).
- `evidence`: SHAs, PR or comment links, `command → output` excerpts. **A `done` task must have at least one.**
- `tokens`: total tokens the delegated agent reported spending, or `null` if the platform doesn't report it.

The scribe rewrites the whole file on each update (no hand-merged fragments) and validates it as JSON before
pushing.

## Enforcing "no done without evidence" (not built)

On platforms where the guard enforces (Claude Code, Copilot), it could check this cheaply. A subagent's
`Write` to a `*.tasks.json` path carries the new content in the tool input, so the guard can parse it and deny
any task with `"state": "done"` and empty `evidence`. An `Edit` would need the guard to apply the edit to the
file on disk first, and a shell-built file can't be seen at all. So the robust place is a check on the
`orchestration` branch itself: a pre-push hook or a CI job that validates every `*.tasks.json` against these
rules. On advisory platforms only that branch check can enforce it.
