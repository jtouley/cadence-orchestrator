# Changelog

A fix for something an earlier release broke goes under `### Fixed (regression from X.Y.Z)` in the release that
ships it, naming the release that broke it. `npx cadence-orchestrator dora` reads these to measure change fail
rate, rework and recovery time.

## Unreleased

## 0.1.7

Upgrading from 0.1.6:

- Installs from 0.1.6 or earlier have no install manifest, so reinstall once with `npx cadence-orchestrator`. Until
  then `status` says "installed by 0.1.6 or earlier; run `npx cadence-orchestrator` once to upgrade" for each target.
- Removing files a newer version drops, and backing up hand edits, apply to installs made with 0.1.7 or later; the
  first reinstall over a 0.1.6 install overwrites its files without backups.
- Cursor installs from 0.1.6 have no `sessionStart` entry, so `status` exits 1 for it until you reinstall.

Changes:

- `npx cadence-orchestrator` with no `--target` installs for each editor the repo has config for (`.claude/`,
  `.codex/`, `.cursor/`, `.gemini/`, `.github/copilot-instructions.md` or `.github/hooks/`, Antigravity's
  `.agent/` or `.agents/rules|workflows|hooks.json`). With none, it uses the agent it runs under, from documented
  variables (`CLAUDECODE`, `CODEX_THREAD_ID`/`CODEX_SANDBOX*`, `CURSOR_AGENT`, `GEMINI_CLI`); otherwise it fails
  with one line. It ends with per-target next steps: reload once where hooks were installed, `$tpm` on Codex and
  `/tpm` elsewhere, then `status`.
- `--repo` defaults to the git repository you're in, at its top level, also from a subfolder or as a bare `--repo`
  (last, or followed by a `--` argument). `--repo <path>` must still be a repository root. When installing, the
  walk up from the current folder never lands on the home directory. The installer prints which repository it
  installs into; outside a repository it fails with one line. `doctor`, `status` and `dora` resolve it the same way.
- Errors print one line instead of a stack trace (`DEBUG=1` adds the stack); a permission error names the path and
  says an agent's sandbox may need to allow writes to the repo, and a hook file that isn't valid JSON is named.
- New `antigravity` target (Google Antigravity): the skill in `.agents/skills/tpm/` (run as `/tpm`) and a manual rule
  `.agents/rules/tpm.md` that marks the install. Instructions only: no Antigravity hook input carries the prompt, so
  nothing can arm the guard. `doctor` and `status` report it as instructions only.
- `status` exits 1, naming the reinstall command, when an installed guarded target's skill, shim or hook config is
  missing, and notes a skill folder that no installed target owns.
- Cursor: a `sessionStart` hook puts the chat's id in its context, so after `/tpm` the skill matches it in `status`
  and says "guard armed for this chat (advisory on Cursor: warns, doesn't block)" or "not armed in this chat" with
  the fix command.
- `status` also exits 1 when a guarded target's hook config and shim are gone but its own files remain, even if an
  instructions-only target shares its skill folder.
- Shared skill folders are copied once per run, and `.gitignore` is updated once.
- `npx cadence-orchestrator uninstall [--target …] [--dry-run]` removes only what the installer added (marked hook
  entries, the managed block, its files, the shim, a skill folder no remaining target uses, the `.gitignore` lines)
  and prints what it removed; re-running is safe. It removes the files its install manifest records (plus bytecode
  compiled from tpm's own scripts, `<script>.*.pyc` in tpm's `scripts/__pycache__`; other skills are never
  touched), backs up hand-edited ones first, and removes a folder only if the installer created it (recorded in the
  manifest) and it's empty, never a `skills` or `hooks` folder. Older installs keep their folders.
- Every file a run touches is parsed and checked before anything is written: invalid JSON, or a managed block whose
  begin or end marker is missing, stops the run with the repo unchanged.
- `--dry-run` lists what an install would change and writes nothing; `--check` exits 1 when installed files differ
  from what this version would write.
- `status --json` and `doctor --json` print one JSON object. `status` shows the installed version and says to
  reinstall when it differs. Each skill folder gets a `.cadence-install.json` with the version and file hashes.
- A vendored skill file edited by hand is backed up to `.cadence/backups/<time>/` before a reinstall overwrites it
  (installs made with this version or later). Manifests are read before any write and written last, so an upgrade
  doesn't mistake upstream changes for hand edits. From installs made with 0.1.7 or later, a reinstall removes files
  an older version installed that this one doesn't (backing up edited ones), so the manifest matches what's on disk.
- A managed block is replaced or removed in place, without touching the rest of `AGENTS.md`/`GEMINI.md`. A hook
  event that isn't a list stops the run with a one-line error naming the file.
- `doctor` and `status` report a missing Cursor `sessionStart` entry, and note when python3 isn't on the default
  PATH an editor started from the desktop may get. The Cursor shim recognises `sessionStart` input without
  `hook_event_name`.

## 0.1.6

- Releases publish with npm trusted publishing (OIDC) from `.github/workflows/release.yml`: no npm token, a pinned
  npm 11.21.1 checked against its integrity, and provenance added by npm without `--provenance`.

## 0.1.5

- Also first publishes 0.1.4's changes (below): 0.1.4 was tagged but never reached npm.
- Reviewer prompts stay clean (`skills/tpm/SKILL.md`, step 5): target, skill, standard and destination only,
  never suspected issues, focus areas, fix summaries, earlier findings, the orchestrator's conclusions or an
  out-of-scope line. The two review passes differ only in the standard (spec against the pinned doc, which builders
  cite in the PR description with their left-out list; then quality, which always runs over everything under
  review). Round two is a fix check, given the blockers verbatim, plus a blind review of the new commit range.
  Parallel reviewers may each be given a slice of files or commits that together cover the whole change.
- Evals: record the blind-notes results in `evals/README.md`: two designs for keeping hunches from reviewers,
  neither shipped.
- Evals: three exploratory cases on reviewer-prompt leaks, with a deterministic grader
  (`evals/scripts/det_grade_clean_review.py`); `cases.csv` gains a `status` column, and `exploratory` cases stay
  in train.

## 0.1.4

Tagged `v0.1.4` but not published to npm (the publish job failed); its changes first reach npm in 0.1.5.

- Releases are published by CI from a `vX.Y.Z` tag on `main` (`.github/workflows/release.yml`): a `verify` job
  without publishing rights checks the tag, `main`, that the version isn't on npm yet, and runs the tests; a
  `publish` job in the `npm-release` environment publishes with npm provenance (prereleases to `next`).
- `cadence-orchestrator dora [--since] [--deploys tags|merges|npm] [--json]` reports DORA's five delivery metrics:
  deploys from annotated tags, main, or npm publish times; lead time counted once per commit against the first
  deploy containing it, with older commits as the baseline; failures only from CHANGELOG and tasks.json records,
  de-duplicated per failed version, and "not measurable" (never 0%) when there are none or they don't match;
  unmatched records are counted and listed instead of a bare percentage. Prereleases aren't deploys unless
  `--include-prereleases`; `0.0.0` placeholders never are.
- tasks.json: optional `committed_at`, `merged_at`, `deployed_at` (ISO 8601 with a timezone, ordered; one rule shared
  with `dora`, impossible dates rejected on both sides) and `kind: planned|fix` with `fixes` (a version or another
  task's id) and `fixed_in` (the version that shipped the fix); `tasks_check.py` validates them. Workstream docs
  get a "Deployed when:" line, and the report step gives the merge SHA and deployed version.

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
