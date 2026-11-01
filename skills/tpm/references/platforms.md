# Platform notes

The skill is written for any Agent Skills client. This is what differs between the clients the guard supports.
"Unverified" means it comes from the platform's docs or our reading of them, not from a live test.

| Platform | Start TPM with | Subagent tool | Guard |
| --- | --- | --- | --- |
| Claude Code | `/tpm` (`/cadence-orchestrator:tpm` as a plugin) | `Agent` (formerly `Task`) | Enforces |
| GitHub Copilot (CLI, cloud agent) | `/tpm` or `$tpm` | `task` | Enforces |
| Codex (CLI) | `$tpm`, or pick it in `/skills` | Codex subagents (tool name unverified) | Advisory; live hooks unverified |
| Codex (cloud) | `$tpm` | Codex subagents (seen working on 2026-10-31) | None: project hooks didn't run (observed) |
| Cursor | `/tpm` or `$tpm` | `Task` | Advisory |
| Gemini CLI | `/tpm` or `$tpm` | unverified | Advisory |
| Any other Agent Skills client | as the client invokes skills | whatever the client offers | None: instructions only |

Where the guard is advisory or absent, follow the skill as if it enforced: a "tpm advisory" warning is a denial,
and without the `TPM guard armed` line you're in instructions-only mode.
