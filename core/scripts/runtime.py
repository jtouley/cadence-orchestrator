"""tpm hook runtime: arming, the off switch, and the contract adapters implement.

An adapter (adapters/<platform>/shim.py) turns its platform's hook JSON into an
`Event`, and an `Event` outcome back into that platform's stdout/stderr/exit code.
Everything else is here, shared:

- Arming: the guard does nothing until the user starts the tpm skill in a
  session. The adapter recognises that prompt; this writes
  <state_dir>/tpm-armed/<session_id>. Unarmed sessions are always allowed.
- Off switch: <project>/.cadence/tpm.off. Only the user creates it.
- Enforcing vs advisory: where the platform can tell the orchestrator from its
  subagents (Claude Code, Copilot), denials block. Where it can't (Codex,
  Cursor, Gemini), blocking would also stop the workers, so the guard only
  warns and logs to <state_dir>/advisory.log.
- Fail open: any parse error or crash allows the call, so a bug can't brick a
  session (and Copilot treats a crashing preToolUse hook as a denial).
Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402

OFF_FILE = os.path.join(".cadence", guard.OFF_FILE_NAME)
# How a user starts the skill by typing, on platforms that only show us the prompt.
TPM_PROMPT = re.compile(r"^\s*[/$]tpm(\s|$)")


@dataclass
class Event:
    kind: str  # "tool", "prompt" or "other"
    session_id: str = ""
    project_dir: str = ""
    tool: str = ""  # canonical tool name
    args: dict = field(default_factory=dict)
    is_subagent: bool = False
    starts_tpm: bool = False  # for "prompt": this prompt starts the tpm skill


@dataclass
class Outcome:
    stdout: str = ""
    stderr: str = ""
    code: int = 0


@dataclass
class Platform:
    name: str
    enforcing: bool
    parse: Callable[[dict], Event]
    # (allowed, reason) -> Outcome, for an enforcing tool check
    render_tool: Callable[[bool, str], Outcome]
    # warning text or "" -> Outcome, for an advisory tool check
    render_advisory: Callable[[str], Outcome]
    # armed_now -> Outcome, for a prompt event
    render_prompt: Callable[[bool], Outcome]
    state_env: tuple[str, ...] = ()


def state_dir(platform: Platform) -> str:
    for name in ("CADENCE_STATE_DIR",) + platform.state_env:
        if os.environ.get(name):
            return os.environ[name]
    return os.path.join(tempfile.gettempdir(), "cadence-orchestrator")


def marker_path(state: str, session_id: str) -> str | None:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "")
    return os.path.join(state, guard.ARM_DIR, safe) if safe else None


def is_armed(state: str, session_id: str) -> bool:
    path = marker_path(state, session_id)
    return bool(path) and os.path.exists(path)


def handle(platform: Platform, payload: dict) -> Outcome:
    ev = platform.parse(payload)
    state = state_dir(platform)
    if ev.kind == "prompt":
        armed_now = False
        path = marker_path(state, ev.session_id) if ev.starts_tpm else None
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").close()
            armed_now = True
        return platform.render_prompt(armed_now)
    if ev.kind != "tool" or not is_armed(state, ev.session_id):
        return _allow(platform)
    if os.path.exists(os.path.join(ev.project_dir or os.getcwd(), OFF_FILE)):
        return _allow(platform)
    ok, why = guard.evaluate(ev.tool, ev.args, ev.is_subagent, ev.project_dir)
    reason = "" if ok else guard.deny_reason(why, ev.is_subagent)
    if platform.enforcing:
        return platform.render_tool(ok, reason)
    if ok:
        return platform.render_advisory("")
    with open(os.path.join(state, "advisory.log"), "a") as log:
        log.write(
            json.dumps(
                {
                    "time": time.time(),
                    "platform": platform.name,
                    "session": ev.session_id,
                    "tool": ev.tool,
                    "why": why,
                }
            )
            + "\n"
        )
    return platform.render_advisory(
        "tpm advisory (this platform can't tell the orchestrator from its subagents, so "
        f"nothing was blocked): if you are the orchestrator, delegate this ({why})."
    )


def _allow(platform: Platform) -> Outcome:
    return platform.render_tool(True, "") if platform.enforcing else platform.render_advisory("")


def main(platform: Platform, argv: list[str] | None = None) -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        out = handle(platform, payload)
    except Exception as exc:  # fail open: a guard bug must not brick the session
        out = _allow(platform)
        out.stderr = f"tpm guard: {type(exc).__name__}: {exc}; allowing."
    if out.stdout:
        print(out.stdout)
    if out.stderr:
        print(out.stderr, file=sys.stderr)
    return out.code
