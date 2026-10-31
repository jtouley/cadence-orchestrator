# Changelog

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
