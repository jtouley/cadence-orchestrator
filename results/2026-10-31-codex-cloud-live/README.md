# Codex cloud live tests, 2026-10-31

A live check of the guard in a real, signed-in Codex cloud task, following `docs/live-testing.md`. It isn't a
graded eval round.

- **Date:** 2026-10-31
- **Platform:** Codex cloud task
- **Kit:** cadence-orchestrator 0.1.2, installed with `--target codex`
- **Repo:** `jtouley/sandbox`, branch `tpm-live-test`

## Outcome per checklist step

| Step | Outcome |
| --- | --- |
| 1. Skill discovery | Passed: the `tpm` skill loaded and `$tpm` instructions were followed. |
| 2. Hook trust and approval | No hook-approval prompt appeared. |
| 3. Hook execution | Failed: `status` saw no hooks. |
| 4. Arming marker | Failed: no `TPM guard armed` line. |
| 5. Guard behaviour | Not observed: no advisory, nothing logged. |
| 6. Delegation | Passed: a subagent was started and created `CONTRIBUTORS.md`. |
| 7. Instructions only | Not run separately; in effect the whole task ran instructions only. |

## `status` output

Verbatim from the task; exit code 1. A trailing npm upgrade notice is left out.

```console
claude: not installed
codex: skill files found (.agents/skills/tpm)
codex: hook config installed in .codex/hooks.json (UserPromptSubmit, PreToolUse)
codex: hooks seen firing: none in the last 24 h (not running in a live session here yet)
copilot: not installed
cursor: not installed
gemini: not installed
state dir: /tmp/cadence-orchestrator (from temp dir)
advisory log: /tmp/cadence-orchestrator/advisory.log
No live hook activity: the files are installed, but the guard hasn't been seen running. Start a new session in this repo, approve its hooks if asked, start with /tpm ($tpm on Codex), then run status again from inside that session (so it sees the agent's environment), or pass --state-dir.
```

## Conclusion

In this one Codex cloud task on 2026-10-31, the project hooks didn't run, so the skill worked as instructions
only: no guard, advisory or log. The local Codex CLI hasn't been tested live.

## What OpenAI's docs say

OpenAI's Codex docs, as a second Codex cloud task read them on 2026-10-31 (quoted as it reported them; URLs to
be added), say:

- Hooks guide: "Project-local hooks load only when the project .codex/ layer is trusted", with trust reviewed per
  hook in the CLI's `/hooks`; command handlers and hooks from local configuration or directories are listed as
  "not supported with cloud orchestration".
- Cloud environments guide: documents only an install script and a start skill, and no project-hook trust or
  approval mechanism for cloud.

So OpenAI's docs (as read on 2026-10-31) list local command hooks as not supported in cloud; we observed the same.

## Second task: an instructions-only TPM run

Same repo and branch, a second Codex cloud task on 2026-10-31.

- **Task:** `$tpm` to add a Testing section to the repo's docs.
- **Orchestrator:** edited no files itself.
- **Maker:** subagent `testing_writer` wrote the section.
- **Review:** subagent `testing_reviewer` checked it independently against the Makefile and configs; verdict PASS,
  no edits.
- **Checks run:** whitespace checks and `make -n` dry runs passed. The real checks and tests weren't run.

Delegation and independent review held without the guard. Not shown: that the documented commands actually pass.
