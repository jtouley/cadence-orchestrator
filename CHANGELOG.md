# Changelog

A fix for something an earlier release broke goes under `### Fixed (regression from X.Y.Z)` in the release that
ships it, naming the release that broke it. `npx cadence-orchestrator dora` reads these to measure change fail
rate, rework and recovery time.

## Unreleased

- Releases are published by CI from a `vX.Y.Z` tag on `main` (`.github/workflows/release.yml`), with npm
  provenance, so each npm version links back to its commit and tag.
- `cadence-orchestrator dora [--since] [--deploys tags|merges] [--json]` reports DORA's five delivery metrics from
  git, and from explicit failure records only; without them it says "not measurable".
- tasks.json: optional `committed_at`, `merged_at`, `deployed_at` (ISO 8601, ordered) and `kind: planned|fix` with
  `fixes`; `tasks_check.py` validates them. Workstream docs get a "Deployed when:" line, and the report step gives
  the merge SHA and deployed version.

## 0.1.3

- The skill follows the [Agent Skills open standard](https://agentskills.io/specification): it moves from `core/` to
  `skills/tpm/` (directory named after the skill), its frontmatter uses only spec fields (`license`,
  `compatibility` and `metadata` added; `skills-ref validate` passes), and its body names no client-specific
  tools, with per-platform notes in `references/platforms.md`. Tests move to `tests/`. The installer and adapters
  use the new path; the Claude-only `disable-model-invocation` is still added to the vendored Claude copy only.
- Docs (#6): in one Codex cloud task on 2026-10-31 (kit 0.1.2), project hooks didn't run and the skill worked as
  instructions only; OpenAI's docs (as read on 2026-10-31) list local command hooks as not supported in cloud.
  A second, instructions-only TPM run in Codex cloud delegated the work and had it reviewed independently. Both are
  recorded in `docs/live-testing.md`.

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
- README: arm Codex with `$tpm` (Codex mentions skills with `$`), and a Troubleshooting entry for `npx` cache
  errors (`npm_config_cache=/tmp/npm-cache`).

### Fixed (regression from 0.1.0)

- Hooks no longer leave `__pycache__` folders next to the vendored scripts. Re-installing a target removes the
  ones 0.1.0 left in that target's skill folder; targets you don't reinstall keep theirs.

## 0.1.0

First release: the `tpm` skill and its guard for Claude Code and Copilot (enforcing) and Codex, Cursor and
Gemini (advisory); the installer (`npx cadence-orchestrator`); task-file validation, leak and branch checks in
pre-commit and CI; and the Claude Code Stop hook.
