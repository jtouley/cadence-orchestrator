# cadence-orchestrator

Your coding agent plans and delegates; subagents do the work; nothing counts as done without evidence.

cadence-orchestrator is a skill that makes your coding agent act as a technical program manager. You describe
the work; the orchestrator plans it with you, hands every piece of it to subagents, has separate reviewers check
what comes back, and reports with evidence. A guard stops the orchestrator from doing the work itself.

It works with Claude Code, GitHub Copilot, Codex, Cursor, Gemini CLI and (instructions only) Google Antigravity. It is
an offshoot of [cadence-core](https://github.com/jtouley/cadence-core). The skill in [`skills/tpm/`](skills/tpm/)
follows the [Agent Skills open standard](https://agentskills.io/specification), so any client that reads Agent Skills
can use it as instructions (`npx skills add jtouley/cadence-orchestrator`); the guard needs this repo's installer.

> [!NOTE]
> Experimental (0.1.x). The skill's behaviour has not been evaluated yet (see `evals/`). macOS and Linux
> only.

Issues: [github.com/jtouley/cadence-orchestrator/issues](https://github.com/jtouley/cadence-orchestrator/issues)

## How It Works

- **It scopes with you first.** The orchestrator reads what's already decided (CLAUDE.md, ADRs, earlier
  workstream docs) and asks only about decisions still open, one at a time.
- **Shared state lives on an `orchestration` branch.** Each workstream gets a doc (`workstreams/<slug>.md`: your
  ask verbatim, scope, your decisions, evidence) and a task file (`workstreams/<slug>.tasks.json`: owner, state,
  evidence, tokens, the `doc_sha` the task was given and the worker's `left_out` list). A scribe subagent writes
  both. The skill tells the orchestrator a task is done only with evidence and a left-out list the reviewer
  accepted; the guard and a pre-commit hook on the orchestration branch reject a `done` task without them.
- **Subagents get one-line prompts.** A builder's or investigator's prompt names a skill or verb, a target with
  the doc pinned to a commit (`workstreams/<slug>.md@<sha>`), what's out of scope, and where the result goes; the
  details are in the doc.
- **Reviewers stay independent.** Checks are anchored in tests, CI or a repro command. A separate reviewer runs
  the result itself and judges what the worker left out, spec first (against the pinned doc), then quality. Its
  prompt never carries suspected issues, focus areas or earlier findings, and has no out-of-scope line; parallel
  reviewers may each own a slice, as long as together they cover the whole change ([step 5](skills/tpm/SKILL.md#workflow)
  has the full rule). Any claim not backed by a command and its output, a commit or a PR link is reported as
  unproven.
- **A guard keeps the orchestrator out of the work.** Once armed, it blocks the orchestrator from editing files or
  running commands with side effects. Subagents keep all their tools.

Prompts the orchestrator sends its subagents look like this:

```text
Implement workstreams/finish-bag.md@3f2a1c9, not the bag-list screen. Open a PR citing that doc@sha and what you left out, don't merge; link it in the doc.
/code-review on PR #42 against workstreams/finish-bag.md@3f2a1c9 and comment the full review to GitHub.
/code-review on PR #42 and comment the full review to GitHub.
```

## Use cadence-orchestrator

There are two ways to use it, and only the second enforces anything.

- **Use the instructions.** Any agent that reads [`skills/tpm/SKILL.md`](skills/tpm/SKILL.md) (or the installed skill) can
  follow the playbook. Nothing checks it: no hooks run, and the skill tells you "guard not running in this session —
  instructions only" when it doesn't see the guard.
- **Install and activate the guard**: the five steps in [Install in a Repo](#install-in-a-repo).

> [!IMPORTANT]
> On Codex, Cursor and Gemini the guard is **advisory, not enforcement**: it warns and logs, and never blocks.
> In a **Codex cloud** task the project hooks didn't run at all, so it's **instructions only** there (observed
> 2026-10-31 with kit 0.1.2: no armed line, no advisory, no hook-approval prompt, `status` saw no hooks). OpenAI's
> docs (as read on 2026-10-31) list local command hooks as not supported in cloud; we observed the same (details and
> sources in [`docs/live-testing.md`](docs/live-testing.md); URLs to be added). In the local Codex CLI the guard
> should be advisory once its hooks are trusted in `/hooks`; live hooks there are unverified. Check with `status`.

### Install in a Repo

From anywhere inside the git repository you want to use it in:

1. Run `npx cadence-orchestrator`.
2. Review and commit the result, so everyone working in the repo, including cloud sessions, gets it.
3. Reload once: start a **new** chat or session in the repo; hooks load when a session starts. Approve the hooks
   if asked: on Codex, review and trust them in `/hooks`.
4. Start the skill: `$tpm` on Codex, `/tpm` everywhere else.
5. Check the guard with `npx cadence-orchestrator status`. Claude Code, Codex and Gemini also show the agent
   `TPM guard armed (session <id>, log <path>)`. Copilot can't, so run `status` there. On Cursor, the skill runs
   `status` for you after `/tpm` and says whether this chat is armed.

In a repo that already has `.claude/` and `.cursor/`:

```console
Installing into /home/you/project for claude, cursor (detected)
claude: .claude/skills/tpm/, .claude/settings.json
cursor: .agents/skills/tpm/, .cursor/hooks.json, .cursor/rules/tpm.mdc
Done. Review and commit the changes; see README for per-platform notes.
Reload once: start a new chat or session in this repo, so the hooks load (approve them if asked).
claude: start with /tpm
cursor: start with /tpm
Then check the guard is running: npx cadence-orchestrator status
```

A bare run installs for every editor it detects from the repo's config (`.claude/`, `.codex/`, `.cursor/`, `.gemini/`,
`.github/copilot-instructions.md` or `.github/hooks/`, and for Antigravity `.agent/`, `.agents/rules/`,
`.agents/workflows/` or `.agents/hooks.json`). With none of those, it installs for the agent it's running under (Claude
Code, Codex, Cursor or Gemini CLI, from the variables they set), or else stops and asks for `--target`. Detection can
pick up config you no longer use, so check the `(detected)` line. `--target <name>` installs for that one platform
instead (`all` for every one). `npm i` alone writes nothing into the repo. On Antigravity there's no guard, only the
skill: its hooks can't see that you typed `/tpm`.

You need Node 18 or later to run the installer, and `python3` for the guard hooks it installs; the installer
warns if `python3` is missing. To install from source instead of npm, use
`npx github:jtouley/cadence-orchestrator`.

`--repo <path>` installs into the repository whose root is that path; without it, into the one you're in, at its top
level (but not your home directory, if that's a git repository). Re-running is safe: the installer replaces only its own
entries in the files it touches, and adds `.cadence/tpm.off` to `.gitignore`. From a clone of this repository,
`./install.sh` takes the same options.

| Command | What it does | Exits non-zero when |
| --- | --- | --- |
| `npx cadence-orchestrator [--target <name>\|all] [--repo <path>]` | Installs (detects targets without `--target`) | 2: nothing detected; 1: other errors |
| `… --dry-run` | Lists `would create\|update <file>`; writes nothing | |
| `… --check` | Lists files that differ from what this version would write (for CI) | 1: any differ, or nothing is installed |
| `… uninstall [--target <name>] [--dry-run]` | Removes only what the installer added | 1: on error |
| `… doctor --target all [--json]` | Checks files and hook config, runs the hooks on simulated events; changes nothing | 1: a check fails |
| `… status [--hours <n>] [--state-dir <path>] [--json]` | Installed targets and version, and live hook activity | 1: an install is incomplete, nothing is installed, or a guarded target has no live activity |

A passing `doctor` doesn't show that the hooks fire in a real session; `status` does. Run `status` from inside the
agent's session (ask the agent to run it), so it sees the same `CADENCE_STATE_DIR` and temp dir as the hooks, or pass
`--state-dir <path>`. To test in a real session, follow [`docs/live-testing.md`](docs/live-testing.md).

A reinstall backs up a vendored skill file you edited to `.cadence/backups/<time>/` before replacing it, for installs
made with this version or later (older installs have no record of what they wrote). Uninstall removes the hook
entries, the block in `AGENTS.md` or `GEMINI.md`, the installer's files and the `.gitignore` lines, and only empty
folders the installer created, never a `skills` or `hooks` folder. Your own hooks and text, `--catalog` files and
`.cadence/backups/` stay.

| Platform | `--target` | What it adds | Guard |
| --- | --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/tpm/`, hooks in `.claude/settings.json` | **Blocks** |
| GitHub Copilot (CLI and cloud agent) | `copilot` | `.github/skills/tpm/`, `.github/hooks/tpm.json` | **Blocks** |
| Codex | `codex` | `.agents/skills/tpm/`, `.codex/hooks.json`, a block in `AGENTS.md` | CLI: warns (live hooks unverified). Cloud: **instructions only**; hooks didn't run in the one observed task (2026-10-31, kit 0.1.2) |
| Cursor | `cursor` | `.agents/skills/tpm/`, `.cursor/hooks.json`, `.cursor/rules/tpm.mdc` | Warns |
| Google Antigravity | `antigravity` | `.agents/skills/tpm/`, `.agents/rules/tpm.md` | **Instructions only** |
| Gemini CLI | `gemini` | `.agents/skills/tpm/`, `.gemini/settings.json`, a block in `GEMINI.md` | Warns |

Claude Code and Copilot mark tool calls made by subagents, so the guard can block the orchestrator and let
subagents through. Codex, Cursor and Gemini don't, and blocking there would stop the subagents too. On those
three the guard only shows a "tpm advisory" warning, which the skill tells the orchestrator to treat as a denial,
and logs it to `advisory.log` in `$CADENCE_STATE_DIR` (default: `cadence-orchestrator/` in the system temp
directory), not in the repo or `.cadence/`. `doctor` prints the exact path.

### Or as a Claude Code Plugin

To use it in your own Claude Code without installing it into a repo, run these inside Claude Code.

```text
/plugin marketplace add jtouley/cadence-orchestrator
/plugin install cadence-orchestrator@cadence-orchestrator
```

The plugin's command is `/cadence-orchestrator:tpm`.

### Skill Catalogs

The orchestrator chooses which skills to route work to from catalogs: markdown files in the repo's
`.cadence/catalog/` (commit them, so cloud sessions see them), then `$CADENCE_CATALOG_PATH` or
`~/.cadence/catalog/`. Add one while installing with `--catalog <file.md>`; repeat the flag for more than one.
The shipped [`example-registry.md`](skills/tpm/references/example-registry.md) is one user's catalog; the orchestrator
treats it as a format example unless you confirm it fits.

### Start and Stop

Start the session by typing `/tpm` and the work (`/cadence-orchestrator:tpm` with the plugin). On Codex, begin the
message with `$tpm`: Codex mentions skills with `$` (or the `/skills` picker), and `/tpm` isn't a Codex command. On
Copilot, Cursor and Gemini, begin it with `/tpm` or `$tpm`; on Antigravity, `/tpm` (instructions only). That arms the
guard for this session only; a model loading the skill by itself doesn't arm it. On Claude Code the hook reports it, and
an edit by the orchestrator is then refused (exit code 2, message shortened here):

```text
TPM guard armed (session 4f1c…, log /tmp/cadence-orchestrator/advisory.log)
TPM mode is on: the main thread doesn't do core work (Edit). Delegate it to a subagent: …
```

To switch it off, start a new session, or create the off switch in the repo root (delete it to switch back on):

```sh
mkdir -p .cadence && touch .cadence/tpm.off
```

Switching it off is your call. The skill tells the orchestrator never to create that file, and the guard refuses
subagent tool calls that mention it.

## What the Guard Allows

It allows reading, searching, delegating, task tracking and read-only shell commands, and denies edits, writes,
other commands and any tool it doesn't recognise. Subagents keep every tool, but a file-tool write that would mark
a task `done` without evidence (an invalid `workstreams/*.tasks.json`) is denied on Claude Code and Copilot and
warned about on Codex, Cursor and Gemini; shell writes aren't seen, and the orchestration branch's pre-commit hook
catches those. On Claude Code a Stop hook also blocks the orchestrator once per stop attempt while agents it started
are still running; the next attempt goes through. The exact rules are in
[`skills/tpm/references/guard.md`](skills/tpm/references/guard.md).

## Measuring Delivery (DORA)

`npx cadence-orchestrator dora` reports [DORA's five delivery metrics](https://dora.dev/guides/dora-metrics/) for a
repo, read-only, with each metric's definition, source and sample size:

- **Deploys** are release tags `v*` by default, changes landing on `main` with `--deploys merges`, or versions
  published to npm with `--deploys npm`. Prefer `npm` for a published package (it asks the registry, so it's
  opt-in): tag mode counts a tag even when its release failed, and a lightweight tag only has its commit's date.
  Prereleases and `0.0.0` placeholders aren't production deploys and don't count (`--include-prereleases` counts
  prereleases). In npm mode it warns about `v*` tags that were never published, which aren't counted.
- **Deployment frequency** is the number of deploys and the time they span. A per-week rate appears only when the
  window (from `--since` or the first deploy, to now) is at least 4 weeks. With fewer than 10 deploys it shows
  the real intervals (min, median, max) rather than a median alone.
- **Change lead time** runs from each commit to the first deploy that contains it, counted once. Commits from before
  the window are the baseline and aren't measured. It uses the committer date, which a rebase or squash resets.
- **Change fail rate, rework and recovery time** come only from explicit records: CHANGELOG
  `### Fixed (regression from X.Y.Z)` entries and tasks.json tasks with `kind: "fix"` (matched to the release in
  `fixed_in`, or the latest deploy at or before `deployed_at`, within 48 h). Without them it prints
  "not measurable" rather than guess.

`--since 2026-10-01` limits the window and `--json` gives machine-readable output. Each run ends with DORA's caution:
read the metrics together, as one team's trend over time, not as targets or to compare teams or repos. With fewer
than 10 deploys that caution comes first, since a handful of releases is a snapshot, not a trend.

## Threat Model

The guard is not a sandbox. It keeps a cooperative orchestrator from drifting into doing the work, nothing more.

- Its shell check and its off-switch protection are text filters; a determined model can get around them.
- It fails open: malformed hook input or a crash in the guard allows the call, so a bug can't lock up a session.
- It only warns on Codex, Cursor and Gemini. Subagents are restricted only around the off switch and task files.

Use your platform's permissions or a real sandbox to contain an agent you don't trust.

## Further Reading

- [`skills/tpm/SKILL.md`](skills/tpm/SKILL.md): the full playbook the orchestrator follows
- [`skills/tpm/references/guard.md`](skills/tpm/references/guard.md): what the guard allows and denies
- [`skills/tpm/references/catalogs.md`](skills/tpm/references/catalogs.md): catalog format and lookup order
- [`skills/tpm/references/workstream.md`](skills/tpm/references/workstream.md): the workstream doc and `tasks.json` format
- [`skills/tpm/references/example-registry.md`](skills/tpm/references/example-registry.md): an example catalog

## Troubleshooting

### `npx` fails before the installer runs

If `npx` or `npm view` fails with a cache or permission error (common in cloud sandboxes where the home directory
isn't writable), point npm at a writable cache:

```sh
npm_config_cache=/tmp/npm-cache npx cadence-orchestrator --target codex
```

### The installer stops with "isn't valid JSON"

A hook file it would merge into, such as `.claude/settings.json`, has `//` comments or other non-JSON text:

```console
cadence-orchestrator: .claude/settings.json isn't valid JSON (…parse error…); fix it and run again. Nothing was changed.
```

Every file the run would touch is checked before anything is written, so the repo is unchanged. Remove the
comments and run the installer again. A managed block in `AGENTS.md` or `GEMINI.md` whose begin or end marker
was deleted stops the run the same way. Errors print one line; set `DEBUG=1` to also print the full stack trace.

### "no editor config found … and no supported agent detected" (exit 2)

The repo has none of the editor folders listed under [Install in a Repo](#install-in-a-repo), and the run isn't
inside a supported agent. Choose the platform: `npx cadence-orchestrator --target cursor` (or `all`).

### "… is your home directory"

You ran it outside a project, and your home directory is a git repository (dotfiles), so it refuses to install there.
Run it inside the project's repository, or pass `--repo <path>` if you do mean that repository.

### "permission denied (EACCES) on <path>"

The installer couldn't write to the repo. If an agent ran it, its sandbox may need to allow writes to the repo:
approve the command, or run it yourself in a terminal.

### `warning: python3 is not on PATH`

The install finishes, but the guard can't run until `python3` is installed. Meanwhile the hooks allow every call
(they fail open) instead of blocking; the same applies if the shim script is missing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
