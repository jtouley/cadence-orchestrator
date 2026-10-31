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

```console
codex: hooks seen firing: none in the last 24 h
```

Exit code 1.

## Conclusion

In Codex cloud the project hooks didn't run, so the skill worked as instructions only: no guard, advisory or
log. The likely cause, not confirmed, is that project hooks need a one-time approval (`/hooks`) that cloud tasks
never prompt for. The local Codex CLI hasn't been tested live.
