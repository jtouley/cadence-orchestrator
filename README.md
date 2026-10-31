# cadence-orchestrator

cadence-orchestrator is a skill that makes your coding agent act as a technical program manager. You describe
the work; the orchestrator plans it with you, hands every piece of it to subagents, has separate reviewers check
what comes back, and reports with evidence. A guard stops the orchestrator from doing the work itself.

It works with Claude Code, GitHub Copilot, Codex, Cursor and Gemini CLI. It is an offshoot of
[cadence-core](https://github.com/jtouley/cadence-core).

> [!NOTE]
> Version 0.1.0. The repository is private and the npm package is not published yet. macOS and Linux only.

## How It Works

- **It scopes with you first.** The orchestrator reads what's already decided (CLAUDE.md, ADRs, earlier
  workstream docs) and asks only about decisions still open, one at a time.
- **Shared state lives on an `orchestration` branch.** Each workstream gets a doc (`workstreams/<slug>.md`: your
  ask verbatim, scope, your decisions, evidence) and a task file (`workstreams/<slug>.tasks.json`: owner, state,
  evidence, tokens, the `doc_sha` the task was given and the worker's `left_out` list). A scribe subagent writes
  both. The skill tells the orchestrator a task is done only with evidence and a left-out list the reviewer
  accepted; nothing checks this automatically yet.
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

### Install in a Repo

From the root of the git repository you want to use it in:

```sh
npx github:jtouley/cadence-orchestrator --target claude
```

```console
claude: .claude/skills/tpm/, .claude/settings.json
Done. Review and commit the changes; see README for per-platform notes.
```

You need Node 18 or later to run the installer, and `python3` for the guard hooks it installs; the installer
warns if `python3` is missing. Because the repository is private, `npx github:` needs GitHub access: an SSH key
or a token that git can use. (The npm package won't need this.) Once it's published, the command will be
`npx cadence-orchestrator --target claude`.

`--repo <path>` installs into another repository; it defaults to the current directory. `--target all` installs
for every platform. Re-running is safe: the installer replaces only its own entries in the files it touches. It
also adds `.cadence/tpm.off` to `.gitignore`. Commit the result so everyone working in the repo, including cloud
sessions, gets it. From a clone of this repository, run `./install.sh --repo <path>` with the same options.

| Platform | `--target` | What it adds | Guard |
| --- | --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/tpm/`, hooks in `.claude/settings.json` | **Blocks** |
| GitHub Copilot (CLI and cloud agent) | `copilot` | `.github/skills/tpm/`, `.github/hooks/tpm.json` | **Blocks** |
| Codex | `codex` | `.agents/skills/tpm/`, `.codex/hooks.json`, a block in `AGENTS.md` | Warns |
| Cursor | `cursor` | `.agents/skills/tpm/`, `.cursor/hooks.json`, `.cursor/rules/tpm.mdc` | Warns |
| Gemini CLI | `gemini` | `.agents/skills/tpm/`, `.gemini/settings.json`, a block in `GEMINI.md` | Warns |

Claude Code and Copilot mark tool calls made by subagents, so the guard can block the orchestrator and let
subagents through. Codex, Cursor and Gemini don't, and blocking there would stop the subagents too. On those
three the guard only shows a "tpm advisory" warning, which the skill tells the orchestrator to treat as a denial,
and logs it to `advisory.log` in `$CADENCE_STATE_DIR` (default: `cadence-orchestrator/` in the system temp
directory).

### Or as a Claude Code Plugin

To use it in your own Claude Code without installing it into a repo, run these inside Claude Code. While the
repository is private, this also needs GitHub access.

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

Start the session by typing `/tpm` and the work (`/cadence-orchestrator:tpm` with the plugin). On Copilot,
Codex, Cursor and Gemini the message must begin with `/tpm` or `$tpm`. That arms the guard for this session
only; a model loading the skill by itself doesn't arm it. On Claude Code the hook reports it, and an edit by the
orchestrator is then refused (exit code 2, message shortened here):

```text
TPM guard armed for this session: the main thread delegates core work.
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
other commands and any tool it doesn't recognise; the exact lists are in
[`core/references/guard.md`](core/references/guard.md).

## Threat Model

The guard is not a sandbox. It keeps a cooperative orchestrator from drifting into doing the work, nothing more.

- Its shell check and its off-switch protection are text filters; a determined model can get around them.
- It fails open: malformed hook input or a crash in the guard allows the call, so a bug can't lock up a session.
- It only warns on Codex, Cursor and Gemini, and it doesn't restrict subagents beyond the off switch.

Use your platform's permissions or a real sandbox to contain an agent you don't trust.

## Further Reading

- [`core/SKILL.md`](core/SKILL.md): the full playbook the orchestrator follows
- [`core/references/guard.md`](core/references/guard.md): what the guard allows and denies
- [`core/references/catalogs.md`](core/references/catalogs.md): catalog format and lookup order
- [`core/references/workstream.md`](core/references/workstream.md): the workstream doc and `tasks.json` format
- [`core/references/example-registry.md`](core/references/example-registry.md): an example catalog

## Troubleshooting

### `npx github:` fails to fetch the package

The repository is private. Give git access to GitHub (an SSH key, or a token through a credential helper), or
clone it with credentials you already have and run `./install.sh --repo <path>` from the clone.

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

The install finishes, but the guard can't run until `python3` is installed. Meanwhile, on Claude Code, Copilot and
Gemini the hooks allow every call (they fail open) instead of blocking; the same applies if the shim script is
missing.

## Development

```sh
python3 core/tests/test_guard.py
python3 core/tests/test_adapters.py
```

The tests use only the Python standard library (test_adapters.py also needs Node). If you change what the guard
allows, update `core/references/guard.md` in the same change; a test checks its tool list against `guard.py`. `evals/` holds
behaviour cases written against one app repository (coffee-data-tracker), so they don't run on their own.

## License

[MIT](LICENSE)
