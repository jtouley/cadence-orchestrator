# Codex cloud live test, 2026-10-31

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
only: no guard, advisory or log. The likely cause, not confirmed, is that project hooks need a one-time approval
(`/hooks`) that the cloud task never prompted for. The local Codex CLI hasn't been tested live.
