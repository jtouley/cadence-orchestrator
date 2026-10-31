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
