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

## Failure modes

Malformed hook input, or any crash in the guard, is allowed with a note on stderr, so a bug can't lock up
the session. Subagents may not touch `.cadence/tpm.off` or the arming markers (a text match after stripping
quotes and backslashes; a backstop, not a boundary).
