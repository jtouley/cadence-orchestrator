#!/usr/bin/env python3
"""tpm guard shim for GitHub Copilot (CLI and cloud agent; enforcing).

Configured with the PascalCase (VS Code compatible) event names, so input uses
snake_case and Claude tool names, and hooks inside a subagent carry agent_id
(root-agent input has none). camelCase input (toolName/toolArgs/agentId) is also
accepted. Deny = JSON permissionDecision on stdout, exit 0: a command preToolUse
hook that crashes or exits non-zero denies the call on Copilot, so this never does.
"""
FALLBACK_STDOUT = ""
import json
import os
import sys

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


def parse(p: dict) -> Event:
    event = p.get("hook_event_name", "")
    session = str(p.get("session_id") or p.get("sessionId") or "")
    project = p.get("cwd") or ""
    if "prompt" in p and "tool_name" not in p and "toolName" not in p:
        return Event("prompt", session, project,
                     starts_tpm=bool(runtime.TPM_PROMPT.match(str(p.get("prompt", "")))))
    if "tool_name" in p or "toolName" in p:
        return Event("tool", session, project,
                     tool=str(p.get("tool_name") or p.get("toolName") or ""),
                     args=_args(p.get("tool_input", p.get("toolArgs"))),
                     is_subagent=bool(p.get("agent_id") or p.get("agentId")))
    return Event("other", session, project)


PLATFORM = Platform(
    name="copilot",
    enforcing=True,
    parse=parse,
    render_tool=lambda ok, reason: Outcome() if ok else Outcome(stdout=json.dumps(
        {"permissionDecision": "deny", "permissionDecisionReason": reason})),
    render_advisory=lambda msg: Outcome(),
    render_prompt=lambda armed: Outcome(),  # Copilot drops userPromptSubmitted output
)

if __name__ == "__main__":
    sys.exit(runtime.main(PLATFORM))
