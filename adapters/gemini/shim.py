#!/usr/bin/env python3
"""tpm guard shim for Gemini CLI (ADVISORY: never blocks).

Gemini's BeforeTool input has no subagent marker, so the guard can't tell the
orchestrator from its workers; it warns via systemMessage and logs instead.
Gemini requires stdout to be exactly one JSON object.
"""

FALLBACK_STDOUT = "{}"
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

TOOL_MAP = {
    "run_shell_command": "Bash",
    "read_file": "Read",
    "read_many_files": "Read",
    "write_file": "Write",
    "replace": "Edit",
    "glob": "Glob",
    "search_file_content": "Grep",
    "grep_search": "Grep",
    "list_directory": "LS",
    "web_fetch": "WebFetch",
    "google_web_search": "WebSearch",
}


def parse(p: dict) -> Event:
    event = p.get("hook_event_name", "")
    session = str(p.get("session_id", ""))
    project = os.environ.get("GEMINI_PROJECT_DIR") or p.get("cwd") or ""
    if event == "BeforeAgent":
        return Event(
            "prompt", session, project, starts_tpm=bool(runtime.TPM_PROMPT.match(str(p.get("prompt", ""))))
        )
    if event == "BeforeTool" or "tool_name" in p:
        name = str(p.get("tool_name", ""))
        if name.startswith("mcp_") and not name.startswith("mcp__"):
            server, _, tool = name[4:].partition("_")
            name = f"mcp__{server}__{tool}"
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
    name="gemini",
    enforcing=False,
    parse=parse,
    render_tool=lambda ok, reason: Outcome(stdout="{}"),
    render_advisory=lambda msg: Outcome(stdout=json.dumps({"systemMessage": msg}) if msg else "{}"),
    render_prompt=lambda armed: Outcome(stdout="{}"),
)

if __name__ == "__main__":
    sys.exit(runtime.main(PLATFORM))
