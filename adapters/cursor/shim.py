#!/usr/bin/env python3
"""tpm guard shim for Cursor (ADVISORY: never blocks).

Cursor's preToolUse input has no subagent marker, so the guard can't tell the
orchestrator from its workers; it always answers allow and logs what it would
have denied. Cursor blocks on invalid JSON from permission hooks, so every path
prints valid JSON. Session = conversation_id.
"""

FALLBACK_STDOUT = '{"permission": "allow"}'
import io
import json
import os
import sys

# Hooks run inside the user's repo; don't leave __pycache__ next to the vendored scripts.
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
# Vendored: runtime.py sits beside this file. Repo or plugin layout: skills/tpm/scripts.
for _d in (HERE, os.path.join(HERE, "..", "..", "skills", "tpm", "scripts")):
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

TOOL_MAP = {"Shell": "Bash", "Task": "Agent"}


def parse(p: dict) -> Event:
    session = str(p.get("conversation_id") or p.get("session_id") or "")
    roots = p.get("workspace_roots") or []
    project = (roots[0] if roots else "") or p.get("cwd") or ""
    if "prompt" in p and "tool_name" not in p:
        return Event(
            "prompt", session, project, starts_tpm=bool(runtime.TPM_PROMPT.match(str(p.get("prompt", ""))))
        )
    if "tool_name" in p:
        name = str(p.get("tool_name", ""))
        if name.startswith("MCP:"):
            name = "mcp__cursor__" + name[4:]
        args = p.get("tool_input")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        return Event(
            "tool",
            session,
            project,
            tool=TOOL_MAP.get(name, name),
            args=runtime.canonical_args(args),
        )
    return Event("other", session, project)


PLATFORM = Platform(
    name="cursor",
    enforcing=False,
    parse=parse,
    render_tool=lambda ok, reason: Outcome(stdout=FALLBACK_STDOUT),
    render_advisory=lambda msg: Outcome(stdout=FALLBACK_STDOUT, stderr=msg),
    # beforeSubmitPrompt output can't add context; stderr goes to Cursor's hook log (unconfirmed).
    render_prompt=lambda message: Outcome(stdout='{"continue": true}', stderr=message),
)


def session_context(session: str) -> str:
    """The line sessionStart puts in the chat's context, so /tpm can find this chat in `status`."""
    return (
        f"tpm: this Cursor chat's id is {session}. To check the guard for this chat, look for "
        f'"session {session}" in `npx cadence-orchestrator status`.'
    )


def is_session_start(p: dict) -> bool:
    # hook_event_name is a documented base field. Without it, go only by sessionStart's documented input
    # (session_id, is_background_agent): sessionEnd adds reason, and a tool or prompt event is never a sessionStart,
    # so a payload with tool_name, tool_input or prompt goes to the guard (https://cursor.com/docs/hooks).
    if "hook_event_name" in p:
        return p.get("hook_event_name") == "sessionStart"
    if any(k in p for k in ("tool_name", "tool_input", "prompt", "reason")):
        return False
    return "session_id" in p and "is_background_agent" in p


def main() -> int:
    # sessionStart's session_id equals conversation_id, and its additional_context is added to the chat's
    # context (https://cursor.com/docs/agent/hooks). Every other event goes to the shared runtime.
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if isinstance(payload, dict) and is_session_start(payload):
        session = str(payload.get("session_id") or payload.get("conversation_id") or "")
        print(json.dumps({"additional_context": session_context(session)} if session else {}))
        try:
            runtime.handle(PLATFORM, payload)  # records the heartbeat; the decision doesn't apply here
        except Exception:
            pass
        return 0
    sys.stdin = io.StringIO(raw)
    return runtime.main(PLATFORM)


if __name__ == "__main__":
    sys.exit(main())
