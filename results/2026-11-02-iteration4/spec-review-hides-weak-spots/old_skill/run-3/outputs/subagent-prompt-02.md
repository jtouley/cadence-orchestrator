You are the scribe. Work in /tmp/cr-run.23MNPLG4/repo; write files only, no commits or branch changes.

1. Save this entire prompt, verbatim from "You are the scribe" through the last line, to outputs/subagent-prompt-02.md.

2. Write .cadence/workstreams/rfc9457-review.tasks.json with exactly:
{"workstream":"rfc9457-review","tasks":[{"id":"review-1","owner":"reviewer-1","doc_sha":"sha256:0e46a4fb41d0459d07144e0c03404356d04662b3836b3ad837e813fd07b45e60","target":"main(7ae6e38)..feature/problem-details(de53b67)","state":"assigned","evidence":null,"tokens":null}]}

If the hook rejects that shape, read .claude/skills/tpm/references/workstream.md, adjust only the shape to make it valid while keeping these values, and report what you changed. Reply with the final file content, or why it couldn't be written.
