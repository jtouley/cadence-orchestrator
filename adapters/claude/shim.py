#!/usr/bin/env python3
"""tpm guard shim for Claude Code (enforcing).

Claude Code sets agent_id on hook input only inside a subagent, so the guard can
tell the orchestrator from its workers. Deny = exit 2 with the reason on stderr.
Arms on UserPromptExpansion for the tpm skill (typed /tpm or /<plugin>:tpm).
On Stop, blocks once (decision "block") while agent tasks the orchestrator
started are still in Stop's background_tasks; stop_hook_active means it already
did, so it lets the stop through.
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


def parse(p: dict) -> Event:
    event = p.get("hook_event_name", "")
    session = str(p.get("session_id", ""))
    project = os.environ.get("CLAUDE_PROJECT_DIR") or p.get("cwd") or ""
    if event == "UserPromptExpansion":
        name = str(p.get("command_name", "")).split(":")[-1]
        return Event("prompt", session, project, starts_tpm=name == "tpm")
    if event == "UserPromptSubmit":
        return Event(
            "prompt", session, project, starts_tpm=bool(runtime.TPM_PROMPT.match(str(p.get("prompt", ""))))
        )
    if event == "Stop":
        return Event(
            "stop",
            session,
            project,
            stop_hook_active=bool(p.get("stop_hook_active")),
            background_tasks=p.get("background_tasks") or [],
        )
    if event == "PreToolUse" or "tool_name" in p:
        args = p.get("tool_input")
        return Event(
            "tool",
            session,
            project,
            tool=str(p.get("tool_name", "")),
            args=args if isinstance(args, dict) else {},
            is_subagent=bool(p.get("agent_id")),
        )
    return Event("other", session, project)


PLATFORM = Platform(
    name="claude",
    enforcing=True,
    parse=parse,
    render_tool=lambda ok, reason: Outcome() if ok else Outcome(stderr=reason, code=2),
    render_advisory=lambda msg: Outcome(),
    render_prompt=lambda armed: Outcome(
        stdout="TPM guard armed for this session: the main thread delegates core work." if armed else ""
    ),
    state_env=("CLAUDE_PLUGIN_DATA",),
    render_stop=lambda reason: Outcome(
        stdout=json.dumps({"decision": "block", "reason": reason}) if reason else ""
    ),
)

if __name__ == "__main__":
    sys.exit(runtime.main(PLATFORM))
