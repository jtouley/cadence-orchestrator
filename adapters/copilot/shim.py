#!/usr/bin/env python3
"""tpm guard shim for GitHub Copilot (CLI and cloud agent; enforcing).

Configured with the PascalCase (VS Code compatible) event names, so input uses
snake_case and Claude tool names, and hooks inside a subagent carry agent_id
(root-agent input has none). camelCase input (toolName/toolArgs/agentId) is also
accepted. Deny = JSON permissionDecision on stdout, exit 0: a command preToolUse
hook that crashes or exits non-zero denies the call on Copilot, so this never does,
and the hook command in hooks.json exits 0 even when python3 or this file is missing.
"""

FALLBACK_STDOUT = ""
import json
import os
import sys

# Hooks run inside the user's repo; don't leave __pycache__ next to the vendored scripts.
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
# Vendored: runtime.py sits beside this file. Repo or plugin layout: core/scripts.
for _d in (HERE, os.path.join(HERE, "..", "..", "core", "scripts")):
    if os.path.exists(os.path.join(_d, "runtime.py")):
        sys.path.insert(0, os.path.abspath(_d))
        break
try:
    import runtime
    from runtime import Event, Outcome, Platform
except ImportError as exc:  # fail open, in this platform's "allow" shape
    print(FALLBACK_STDOUT) if FALLBACK_STDOUT else None
    print(f"tpm guard: cannot load runtime ({exc}); allowing.", file=sys.stderr)
    sys.exit(0)


def _args(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


# str_replace_editor's effect depends on its `command` argument.
EDITOR_COMMANDS = {"create": "Write", "str_replace": "Edit", "insert": "Edit", "view": "Read"}


def tool_name(name: str, args: dict) -> str:
    if name == "str_replace_editor":
        return EDITOR_COMMANDS.get(str(args.get("command", "")), "Edit")
    return TOOL_MAP.get(name, name)


# camelCase payloads carry Copilot's runtime tool names; PascalCase ones already use Claude's.
# From the hooks reference's "Tool names for hook matching" table.
TOOL_MAP = {
    "bash": "Bash",
    "powershell": "PowerShell",
    "view": "Read",
    "create": "Write",
    "edit": "Edit",
    "apply_patch": "Edit",
    "grep": "Grep",
    "rg": "Grep",
    "glob": "Glob",
    "web_fetch": "WebFetch",
    "web_search": "WebSearch",
    "ask_user": "AskUserQuestion",
    "update_todo": "TodoWrite",
    "task": "Agent",
}


def parse(p: dict) -> Event:
    session = str(p.get("session_id") or p.get("sessionId") or "")
    project = p.get("cwd") or ""
    if "prompt" in p and "tool_name" not in p and "toolName" not in p:
        return Event(
            "prompt", session, project, starts_tpm=bool(runtime.TPM_PROMPT.match(str(p.get("prompt", ""))))
        )
    if "tool_name" in p or "toolName" in p:
        name = str(p.get("tool_name") or p.get("toolName") or "")
        args = runtime.canonical_args(_args(p.get("tool_input", p.get("toolArgs"))))
        return Event(
            "tool",
            session,
            project,
            tool=tool_name(name, args),
            args=args,
            is_subagent=bool(p.get("agent_id") or p.get("agentId")),
        )
    return Event("other", session, project)


PLATFORM = Platform(
    name="copilot",
    enforcing=True,
    parse=parse,
    render_tool=lambda ok, reason: (
        Outcome()
        if ok
        else Outcome(stdout=json.dumps({"permissionDecision": "deny", "permissionDecisionReason": reason}))
    ),
    render_advisory=lambda msg: Outcome(),
    # Copilot drops userPromptSubmitted output, so the model can't be told; `status` shows it.
    render_prompt=lambda message: Outcome(stderr=message),
)

if __name__ == "__main__":
    sys.exit(runtime.main(PLATFORM))
