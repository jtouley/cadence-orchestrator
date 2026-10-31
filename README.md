# cadence-orchestrator

A skill that turns a frontier-model coding session into a technical program manager for its own agents.

You type `/tpm` and describe the work. The session scopes it with you, splits it into workstreams, hands every
piece of investigation, coding, testing and review to subagents, checks what comes back with independent
reviewers, and reports with evidence. A guard keeps the orchestrating thread from doing the work itself, so its
context stays on the plan and on whether the results are right.

It runs on Claude Code, GitHub Copilot, Codex, Cursor and Gemini CLI. It is an offshoot of
[cadence-core](https://github.com/jtouley/cadence-core).

## How it works

- **Scopes with you first.** It reads what's already decided (CLAUDE.md, ADRs, earlier workstream docs) and asks
  only the real forks, one choice at a time.
- **Shared state lives on an `orchestration` branch.** One doc per workstream (`workstreams/<slug>.md`) holds your
  ask verbatim, the scope, your decisions, one owner per task, and links to evidence. A scribe agent writes it.
- **Dispatch prompts are one line.** A verb or skill, a target, and where the result goes. The details are in the
  doc, so agents investigate instead of confirming the orchestrator's guess.
- **Verification is independent.** A separate reviewer gets the artifact and the doc, never the maker's
  conclusion. A claim without a command and its output, a commit or a PR link is reported as unproven.
- **A guard keeps the orchestrator out of the work.** Once armed, it blocks the main thread from editing files or
  running commands with side effects. Subagents keep all their tools.

What the orchestrator sends its agents looks like this:

```text
/code-review on PR #42 and push the full review to the PR as a comment.
Implement workstreams/finish-bag.md (branch orchestration on origin). Open a PR, don't merge; link it in the doc.
```

The full playbook is [`core/SKILL.md`](core/SKILL.md).

## Install

Requires `git` and `python3` (standard library only). The installer copies the skill and its hooks into a
repository; `--repo` must be the root of a git checkout. Commit the result so everyone working in that repo gets it.

```sh
git clone https://github.com/jtouley/cadence-orchestrator
cd cadence-orchestrator
./install.sh --target claude --repo ~/code/my-app
```

```console
claude: .claude/skills/tpm/, .claude/settings.json
Done. Review and commit the changes; see README for per-platform notes.
```

Use `--target all` for every platform at once. Re-running is safe: it replaces only its own hook entries and
keeps everything else in those files. It also adds `.cadence/` to the repo's `.gitignore`.

| Platform | `--target` | What it adds | Guard |
| --- | --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/tpm/`, hooks in `.claude/settings.json` | **Enforces** |
| GitHub Copilot (CLI and cloud agent) | `copilot` | `.github/skills/tpm/`, `.github/hooks/tpm.json` | **Enforces** |
| Codex | `codex` | `.agents/skills/tpm/`, `.codex/hooks.json`, a block in `AGENTS.md` | Warns only |
| Cursor | `cursor` | `.agents/skills/tpm/`, `.cursor/hooks.json`, `.cursor/rules/tpm.mdc` | Warns only |
| Gemini CLI | `gemini` | `.agents/skills/tpm/`, `.gemini/settings.json`, a block in `GEMINI.md` | Warns only |

Claude Code and Copilot mark tool calls made inside a subagent, so the guard can block the orchestrator and let
its workers through. Codex, Cursor and Gemini don't, so blocking there would stop the workers too. On those three
the guard never blocks: it shows a "tpm advisory" warning, which the skill tells the model to treat as a denial,
and logs it to `advisory.log` in the state directory (`$CADENCE_STATE_DIR`, or `cadence-orchestrator/` in the
system temp directory).

### Claude Code plugin

To use it in your own Claude Code without vendoring it into a repo, install the plugin from inside Claude Code:

```text
/plugin marketplace add jtouley/cadence-orchestrator
/plugin install cadence-orchestrator@cadence-orchestrator
```

Then start it with `/cadence-orchestrator:tpm`.

## Usage

Open a session in the repo and begin your message with `/tpm`:

```text
/tpm add a finish screen for the bag flow, then review it
```

That arms the guard for this session only. It arms when you type the command, not when a model loads the skill
on its own. On Copilot, Codex, Cursor and Gemini the message has to start with `/tpm` (or `$tpm`).

**To switch it off**, start a new session, or create the off switch in the repo root:

```sh
mkdir -p .cadence && touch .cadence/tpm.off
```

Delete the file to turn the guard back on in sessions that were armed. Turning it off is your call: the skill
tells the model never to create the file, an enforced main thread can't write it, and the guard refuses subagent
tool calls that mention it.

## What the guard allows

On an armed main thread the guard allows reading, searching, delegation (subagents, child sessions, skills), task
tracking and conversation, plus MCP tools whose names say they only read (`get_*`, `list_*`, `search_*` and
similar). A shell command passes only if every part of it is on a short read-only list (`ls`, `cat`, `grep`,
`find`, `git status`, `git log`, `git diff`, ...) with allowlisted options. Edits, writes, other shell commands
and any tool it doesn't recognise are denied, with a message telling the model to delegate.

The exact lists are in [`core/references/guard.md`](core/references/guard.md); the policy is
[`core/scripts/guard.py`](core/scripts/guard.py).

## Threat model

The guard is **not a sandbox**. It stops a cooperative orchestrator from drifting into doing the work itself; it
is not a security boundary.

- The shell check is a text filter. A determined model can get around it.
- The off-switch protection is a text match on tool arguments: a backstop, not a lock.
- It fails open. Malformed hook input or a crash in the guard allows the call, so a bug can't lock up a session.
- On Codex, Cursor and Gemini it only warns.
- Subagents are unrestricted apart from the off switch and the arming state.

Don't rely on it to contain an agent you don't trust; use your platform's permissions or a real sandbox for that.

## Repository layout

```text
core/            the skill: SKILL.md, references/, scripts/ (guard.py policy, runtime.py), tests/
adapters/        one folder per platform: a shim that maps its hook input onto the guard, plus hook templates
install.sh       vendors the skill into a repo (runs tools/install.py)
.claude-plugin/  Claude Code plugin and marketplace manifests
evals/           behaviour cases: a prompt, the expected outcome and LLM graders
```

The cases in `evals/` use the layout `claude plugin eval` reads. They were written against one app repository
(coffee-data-tracker), so they don't run on their own.

## Development

The tests need only the standard library:

```sh
python3 core/tests/test_guard.py
python3 core/tests/test_adapters.py
```

If you change what the guard allows, update `core/references/guard.md` in the same change; a test checks its tool
list against `guard.py`.

## License

[MIT](LICENSE)
