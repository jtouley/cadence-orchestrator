# cadence-orchestrator

Your coding agent plans and delegates; subagents do the work; nothing counts as done without evidence.

cadence-orchestrator is a skill that makes your coding agent act as a technical program manager. You describe
the work; the orchestrator plans it with you, hands every piece of it to subagents, has separate reviewers check
what comes back, and reports with evidence. A guard stops the orchestrator from doing the work itself.

It works with Claude Code, GitHub Copilot, Codex, Cursor and Gemini CLI. It is an offshoot of
[cadence-core](https://github.com/jtouley/cadence-core).

> [!NOTE]
> Version 0.1.0, experimental. The skill's behaviour has not been evaluated yet (see `evals/`). macOS and Linux
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
- **Subagents get one-line prompts, and reviewers stay independent.** The prompt names a skill or verb, a target
  with the doc pinned to a commit (`workstreams/<slug>.md@<sha>`), what's out of scope, and where the result goes;
  the details are in the doc. Checks are anchored in tests, CI or a repro command. A separate reviewer runs the
  result itself and judges what the worker left out, spec first, then quality. Any claim not backed by a command
  and its output, a commit or a PR link is reported as unproven.
- **A guard keeps the orchestrator out of the work.** Once armed, it blocks the orchestrator from editing files or
  running commands with side effects. Subagents keep all their tools.

Prompts the orchestrator sends its subagents look like this:

```text
/code-review on PR #42 and push the full review to the PR as a comment.
Implement workstreams/finish-bag.md@3f2a1c9, not the bag-list screen. Open a PR, don't merge; link it in the doc.
```

## Use cadence-orchestrator

There are two ways to use it, and only the second enforces anything.

- **Use the instructions.** Any agent that reads [`core/SKILL.md`](core/SKILL.md) (or the installed skill) can
  follow the playbook. Nothing checks it: no hooks run, and the skill tells you "guard not running in this session —
  instructions only" when it doesn't see the guard.
- **Install and activate the guard.**
  1. Install it into the repo (below) and commit the result.
  2. Start a **new** session in that repo; hooks load when a session starts.
  3. Approve the hooks if the agent asks (Codex, for example, asks you to review and trust project hooks in `/hooks`).
  4. Begin your message with `$tpm` on Codex, `/tpm` everywhere else.
  5. Confirm it's armed: the agent sees `TPM guard armed (session <id>, log <path>)` on Claude Code, Codex and
     Gemini. Copilot and Cursor can't show that line, so run `npx cadence-orchestrator status` in the repo.

> [!IMPORTANT]
> On Codex, Cursor and Gemini the guard is **advisory, not enforcement**: it warns and logs, and never blocks.
> In a **Codex cloud** task the project hooks didn't run at all, so it's **instructions only** there (observed
> 2026-10-31 with kit 0.1.2: no armed line, no advisory, no hook-approval prompt, `status` saw no hooks). Our guess,
> not confirmed, is that project hooks need a one-time approval that cloud tasks never prompt for. In the local
> Codex CLI the guard should be advisory; live hooks there are unverified. Check with `status` in each.

### Install in a Repo

From the root of the git repository you want to use it in:

```sh
npx cadence-orchestrator --target claude
```

```console
claude: .claude/skills/tpm/, .claude/settings.json
Done. Review and commit the changes; see README for per-platform notes.
```

You need Node 18 or later to run the installer, and `python3` for the guard hooks it installs; the installer
warns if `python3` is missing. To install from source instead of npm, use
`npx github:jtouley/cadence-orchestrator --target claude`.

`--repo <path>` installs into another repository; it defaults to the current directory. `--target all` installs
for every platform. Re-running is safe: the installer replaces only its own entries in the files it touches. It
also adds `.cadence/tpm.off` to `.gitignore`. Commit the result so everyone working in the repo, including cloud
sessions, gets it. From a clone of this repository, run `./install.sh --repo <path>` with the same options.

To check an install, run `npx cadence-orchestrator doctor --target claude` (`all` checks every target that's
installed). It checks that the files and hook config are in place and point at existing scripts, that `python3`
is on `PATH`, and runs the installed hooks on simulated events: arming, an orchestrator write (denied, or an
advisory on Codex, Cursor and Gemini), a subagent write (allowed) and, on Claude Code, a stop. It prints one line
per check, exits 1 if any fail, and changes nothing in the repo. A passing `doctor` doesn't show that the hooks
fire in a real session; `npx cadence-orchestrator status` does. It lists, separately, the skill files, the hook
config, the sessions whose hooks have fired in the last 24 hours (`--hours <n>`) and whether each is armed, and the
advisory log path. It exits 1 when no live hook activity has been seen. Run it from inside the agent's session (ask the
agent to run it), so it sees the same `CADENCE_STATE_DIR` and temp dir as the hooks, or pass `--state-dir <path>`;
it prints where the state dir came from. To test in a real session, follow
[`docs/live-testing.md`](docs/live-testing.md).

| Platform | `--target` | What it adds | Guard |
| --- | --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/tpm/`, hooks in `.claude/settings.json` | **Blocks** |
| GitHub Copilot (CLI and cloud agent) | `copilot` | `.github/skills/tpm/`, `.github/hooks/tpm.json` | **Blocks** |
| Codex | `codex` | `.agents/skills/tpm/`, `.codex/hooks.json`, a block in `AGENTS.md` | CLI: warns (live hooks unverified). Cloud: **instructions only**, hooks don't run (observed 2026-10-31, kit 0.1.2) |
| Cursor | `cursor` | `.agents/skills/tpm/`, `.cursor/hooks.json`, `.cursor/rules/tpm.mdc` | Warns |
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
The shipped [`example-registry.md`](core/references/example-registry.md) is one user's catalog; the orchestrator
treats it as a format example unless you confirm it fits.

### Start and Stop

Start the session by typing `/tpm` and the work (`/cadence-orchestrator:tpm` with the plugin). On Codex, begin
the message with `$tpm`: Codex mentions skills with `$` (or the `/skills` picker), and `/tpm` isn't a Codex
command. On Copilot, Cursor and Gemini, begin it with `/tpm` or `$tpm`. That arms the guard for this session
only; a model loading the skill by itself doesn't arm it. On Claude Code the hook reports it, and an edit by the
orchestrator is then refused (exit code 2, message shortened here):

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
[`core/references/guard.md`](core/references/guard.md).

## Threat Model

The guard is not a sandbox. It keeps a cooperative orchestrator from drifting into doing the work, nothing more.

- Its shell check and its off-switch protection are text filters; a determined model can get around them.
- It fails open: malformed hook input or a crash in the guard allows the call, so a bug can't lock up a session.
- It only warns on Codex, Cursor and Gemini. Subagents are restricted only around the off switch and task files.

Use your platform's permissions or a real sandbox to contain an agent you don't trust.

## Further Reading

- [`core/SKILL.md`](core/SKILL.md): the full playbook the orchestrator follows
- [`core/references/guard.md`](core/references/guard.md): what the guard allows and denies
- [`core/references/catalogs.md`](core/references/catalogs.md): catalog format and lookup order
- [`core/references/workstream.md`](core/references/workstream.md): the workstream doc and `tasks.json` format
- [`core/references/example-registry.md`](core/references/example-registry.md): an example catalog

## Troubleshooting

### `npx` fails before the installer runs

If `npx` or `npm view` fails with a cache or permission error (common in cloud sandboxes where the home directory
isn't writable), point npm at a writable cache:

```sh
npm_config_cache=/tmp/npm-cache npx cadence-orchestrator --target codex
```

### The installer stops with a `SyntaxError` from `JSON.parse`

The hook file it merges into, such as `.claude/settings.json`, has `//` comments or other non-JSON text:

```console
SyntaxError: Expected property name or '}' in JSON at position 4 (line 2 column 3)
    at JSON.parse (<anonymous>)
    at mergeHooks (…/bin/cadence-orchestrator.mjs:76:39)
```

The skill files were copied but no hooks were added, and the file is unchanged. Remove the comments and run the
installer again.

### `warning: python3 is not on PATH`

The install finishes, but the guard can't run until `python3` is installed. Meanwhile the hooks allow every call
(they fail open) instead of blocking; the same applies if the shim script is missing.

## Development

```sh
pip install pre-commit==4.7.0 pytest==9.1.1    # the versions CI uses
pre-commit install    # ruff, gitleaks, leak check, JSON/YAML, `node --check`; refuses commits to main
pytest
```

The pre-commit hooks also block email addresses, account UUIDs and session logs (`checks/leak_check.py`) and
direct commits to `main`. The guard and shims use only the Python standard library; pytest, ruff and pre-commit
are for development, and the installer tests also need Node. CI runs the same checks, gitleaks over the full
history, an installer smoke test and `npm pack --dry-run`.
If you change what the guard allows, update `core/references/guard.md` in the same change; a test checks its tool
list against `guard.py`. `evals/` holds behaviour cases written against one app repository
([coffee-data-tracker](https://github.com/jtouley/coffee-data-tracker)), so they don't run on their own.

## Contributing

Issues and pull requests are welcome; run `pre-commit run --all-files` and `pytest` before you open one. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
