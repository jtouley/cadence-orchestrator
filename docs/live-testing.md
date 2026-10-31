# Live testing checklist

`doctor` simulates hook events; it can't show that a real session loads and runs the hooks. Run this checklist in
a real, signed-in session, **separately for the local CLI and the cloud agent** of each platform, since hook
support and approval can differ between them. Record the platform, surface (CLI or cloud), version and date.

Setup: install the target into a test repo (`npx cadence-orchestrator --target <t>`), commit, and push if the
cloud agent works from the remote.

1. **Skill discovery.** In a new session, ask the agent to list its skills, or open the skill picker (`/skills` on
   Codex). `tpm` is there.
2. **Hook trust and approval.** Note whether the platform asks you to review or trust the project hooks (Codex:
   `/hooks`; Claude Code: workspace trust) and approve them. Note if it never asks.
3. **Hook execution.** Run any small task, then `npx cadence-orchestrator status` from inside the session (ask the
   agent to run it, so it sees the agent's environment), or from a terminal with `--state-dir <path>`. The session is
   listed under "hooks seen firing". If it isn't, the hooks didn't run; stop here and record that.
4. **Arming marker.** Start a message with `$tpm` (Codex) or `/tpm` (elsewhere). Where the platform can show it
   (Claude Code, Codex, Gemini), the agent reports `TPM guard armed (session …, log …)`; `status` shows the session
   as armed on every platform.
5. **Guard behaviour.** Ask the orchestrator to edit a file itself. Claude Code and Copilot refuse it; on Codex,
   Cursor and Gemini a "tpm advisory" warning appears and a line is added to the advisory log `status` prints.
6. **Delegation.** Give it a small real task. It writes the workstream doc (or uses local mode and says so),
   dispatches a subagent with a one-line prompt, and reports with evidence. If the session can't start subagents,
   it says so and works as one agent.
7. **Instructions only.** In a repo without the hooks, start TPM: the agent says "guard not running in this
   session — instructions only". With `.cadence/tpm.off`, the marker reads "TPM guard switched off by
   .cadence/tpm.off …: instructions only" where the platform shows it.

## Recorded results

### Codex cloud, 2026-10-31, kit 0.1.2

Repo `jtouley/sandbox`, branch `tpm-live-test`, installed with `--target codex` and pushed; one Codex cloud task.

| Step | Outcome |
| --- | --- |
| 1. Skill discovery | Passed: the `tpm` skill loaded and `$tpm` instructions were followed. |
| 2. Hook trust and approval | No hook-approval prompt appeared. |
| 3. Hook execution | Failed: `status` saw no hooks (output below). |
| 4. Arming marker | Failed: no `TPM guard armed` line. |
| 5. Guard behaviour | Not observed: no advisory, nothing logged. |
| 6. Delegation | Passed: a subagent was started and created `CONTRIBUTORS.md`. |
| 7. Instructions only | Not run separately; in effect the whole task ran instructions only. |

`status` in the task, verbatim (exit code 1; a trailing npm upgrade notice is left out):

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

Conclusion: in this one Codex cloud task on 2026-10-31, the project hooks didn't run, so the skill worked as
instructions only. Our guess, not confirmed, is that project hooks need a one-time approval (`/hooks`) that the
cloud task never prompted for. The local Codex CLI hasn't been tested live yet.
