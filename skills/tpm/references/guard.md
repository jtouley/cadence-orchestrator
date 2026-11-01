# What the guard allows on the main thread

Tool names use Claude Code's vocabulary; each platform's shim maps its own tools onto these names (Cursor
`Shell` and Gemini `run_shell_command` become `Bash`, Codex `apply_patch` becomes `Edit`, and so on).
`scripts/guard.py` is the source of truth, and a test checks this list against it.

## Tools

Allowed as-is: `Read`, `Grep`, `Glob`, `LS`, `WebFetch`, `WebSearch`, `Agent`, `Task`, `Workflow`,
`SendMessage`, `TaskOutput`, `TaskStop`, `BashOutput`, `Skill`, `ToolSearch`, `ListSkills`, `SearchSkills`,
`ListPlugins`, `SearchPlugins`, `TodoWrite`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`,
`AskUserQuestion`, `EnterPlanMode`, `ExitPlanMode`, `SubagentHandback`, and for child sessions
`mcp__claude-code-remote__create_session`, `mcp__claude-code-remote__send_message`,
`mcp__claude-code-remote__send_later`, `mcp__claude-code-remote__subscribe_pr_activity` and
`mcp__claude-code-remote__unsubscribe_pr_activity`.

Also any MCP tool whose last name segment starts with `get`, `list`, `read`, `search`, `describe`, `view`,
`whoami` or `guide`. Everything else is denied, including `Edit`, `Write`, `NotebookEdit`, `MultiEdit`,
`PowerShell`, `Monitor` and unknown tools.

## Shell

`Bash` passes only when every segment of a pipe or chain is one of `ls`, `cat`, `head`, `tail`, `wc`, `grep`,
`rg`, `sort`, `uniq` (one input at most, `-` included), `find`, `pwd`, `cd`, `sed -n <address>p <files>`, or
`git status/diff/log/show/grep/rev-parse` and listing-only `git branch`.

Each command has its own option allowlist (`SPECS`, `GIT_LONG`, `FIND_PREDICATES` in `guard.py`). Long options
must match exactly, because GNU tools and git accept abbreviations (`--out` for `--output`). Redirection is
allowed only to `/dev/null`, as `2>&1`, or as `< file` input; quoted text never counts as an operator. Command
substitution, subshells, heredocs, comments and environment assignments are denied.

## Subagents

Subagents keep every tool, with two exceptions:

- They may not touch `.cadence/tpm.off` or the arming markers (a text match after stripping quotes and
  backslashes; a backstop, not a boundary).
- A `Write` to a `*.tasks.json` file whose content, or an `Edit`/`MultiEdit` whose result (applied to the file
  on disk), fails `scripts/tasks_check.py` is denied: for example a `done` task without evidence. Writes made
  through the shell can't be seen; the `cadence-tasks-check` pre-commit hook on the orchestration branch covers
  those. Validation errors deny too, rather than failing open, and so does a task-file change the guard can't model
  (a patch, an insert, an edit to a file it can't read). On advisory platforms, where every call looks
  like the orchestrator's, the same check runs and its findings are part of the warning.

## Ending the turn (Claude Code)

A Stop hook blocks the orchestrator from ending its turn while tasks it started are still running: any
unfinished entry in Stop's `background_tasks` whose type isn't clearly a non-agent (`shell`, `bash`, `monitor`,
`MCP task`). It blocks once per stop attempt; the next attempt carries `stop_hook_active` and is let through, so
it can't loop. The off switch (`.cadence/tpm.off`) disables it like the rest of the guard. Copilot (`agentStop`), Codex (`Stop`),
Cursor (`stop`) and Gemini (`AfterAgent`) have stop hooks that can force another turn, but their documented
input has no list of running subagents, so there's no equivalent there yet.

## Evidence that it runs

Every hook event writes `<state>/sessions/<session>.json` (platform, last event, time, armed, project). Arming
adds `TPM guard armed (session <id>, log <path>)` where the platform passes hook output to the model: plain stdout
on Claude Code's `UserPromptExpansion` and Codex's `UserPromptSubmit`, `additionalContext` on Gemini's
`BeforeAgent`. Copilot drops prompt-hook output and Cursor's `beforeSubmitPrompt` can't add context, so there the
line only goes to stderr. `npx cadence-orchestrator status` reads the heartbeats.

## Failure modes

Malformed hook input, or any crash in the guard, is allowed with a note on stderr, so a bug can't lock up
the session. That includes a missing `python3` or shim: every hook command checks for both and exits 0.
