# Changelog

## Unreleased

- Docs: in one Codex cloud task on 2026-10-31 (kit 0.1.2), project hooks didn't run and the skill worked as
  instructions only; recorded in `docs/live-testing.md`.

## 0.1.2

- Using the instructions and running the guard are now separate, visible states:
  - every hook event writes a heartbeat to `<state>/sessions/<session>.json` (platform, last event, time, armed);
  - arming adds `TPM guard armed (session <id>, log <path>)` to the model's context on Claude Code and Codex
    (plain stdout), and on Gemini (additionalContext, also shown to the user); Copilot and Cursor can't show it;
  - the skill tells the user "guard not running in this session — instructions only" when it doesn't see that
    line, and never claims the guard is active from installed files or `doctor` alone.
- `cadence-orchestrator status [--repo] [--hours] [--state-dir]` reports skill files, hook config, sessions seen
  firing (armed, not armed or switched off) and the advisory log path, and where the state dir came from; exit 1
  when no live activity has been seen. Sessions started in a subdirectory count for the repo. `doctor` says its
  simulation isn't a live check.
- SKILL.md: a local mode when there's no remote, push or pre-commit (`.cadence/workstreams/`), and working as one
  agent when the session can't delegate.
- README: "use the instructions" vs "install and activate the guard"; `docs/live-testing.md`.

## 0.1.1

- `cadence-orchestrator doctor --target <platform>` checks an install: files, hook config, `python3`, and the
  installed hooks on simulated events. It also prints where `advisory.log` is written and checks that the state
  directory is writable. It changes nothing in the repo.
- Hooks no longer leave `__pycache__` folders next to the vendored scripts. Re-installing a target removes the
  ones 0.1.0 left in that target's skill folder; targets you don't reinstall keep theirs.
- README: arm Codex with `$tpm` (Codex mentions skills with `$`), and a Troubleshooting entry for `npx` cache
  errors (`npm_config_cache=/tmp/npm-cache`).

## 0.1.0

First release: the `tpm` skill and its guard for Claude Code and Copilot (enforcing) and Codex, Cursor and
Gemini (advisory); the installer (`npx cadence-orchestrator`); task-file validation, leak and branch checks in
pre-commit and CI; and the Claude Code Stop hook.
