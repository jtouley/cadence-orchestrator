# cadence-orchestrator

_Stub: the full README is being written separately._

The `tpm` skill turns an agent session into a technical program manager. It scopes the work with you, delegates all
execution to subagents, verifies the results and reports with evidence. A per-session guard stops the orchestrating
agent from doing the work itself. The guard is not a sandbox.

- Install into a repo: `./install.sh --target <claude|codex|cursor|copilot|gemini|all> --repo <path>`, then commit.
- On Claude Code and Copilot the guard enforces. On Codex, Cursor and Gemini it is advisory: those platforms
  can't tell the orchestrator from its subagents, so it only warns and logs.
- Off switch: create `.cadence/tpm.off` in the target repo, or start a new session.
- Claude Code plugin (optional, for the local CLI): `/plugin marketplace add jtouley/cadence-orchestrator`, then
  `/plugin install cadence-orchestrator@cadence-orchestrator`, and start it with `/cadence-orchestrator:tpm`.
- `evals/` cases target the coffee-data-tracker repo and are kept as-is.
- Tests: `python3 core/tests/test_guard.py && python3 core/tests/test_adapters.py`.
