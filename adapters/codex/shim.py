#!/usr/bin/env python3
"""tpm guard shim for OpenAI Codex (ADVISORY: never blocks).

Codex's PreToolUse input has no subagent marker, so the guard can't tell the
orchestrator from its workers; blocking would stop the workers too. It warns
via systemMessage and logs instead. apply_patch maps to Edit.
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

TOOL_MAP = {"apply_patch": "Edit"}


def parse(p: dict) -> Event:
    event = p.get("hook_event_name", "")
    session = str(p.get("session_id", ""))
    project = p.get("cwd") or ""
    if event == "UserPromptSubmit":
        return Event(
            "prompt", session, project, starts_tpm=bool(runtime.TPM_PROMPT.match(str(p.get("prompt", ""))))
        )
    if event == "PreToolUse" or "tool_name" in p:
        name = str(p.get("tool_name", ""))
        args = p.get("tool_input")
        return Event(
            "tool",
            session,
            project,
            tool=TOOL_MAP.get(name, name),
            args=runtime.canonical_args(args),
        )
    return Event("other", session, project)


PLATFORM = Platform(
    name="codex",
    enforcing=False,
    parse=parse,
    render_tool=lambda ok, reason: Outcome(),
    render_advisory=lambda msg: Outcome(stdout=json.dumps({"systemMessage": msg}) if msg else ""),
    # UserPromptSubmit: plain stdout is added as extra developer context (Codex hooks docs).
    render_prompt=lambda message: Outcome(stdout=message),
)

if __name__ == "__main__":
    sys.exit(runtime.main(PLATFORM))
