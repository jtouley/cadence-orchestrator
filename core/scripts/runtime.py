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
    kind: str  # "tool", "prompt", "stop" or "other"
    session_id: str = ""
    project_dir: str = ""
    tool: str = ""  # canonical tool name
    args: dict = field(default_factory=dict)
    is_subagent: bool = False
    starts_tpm: bool = False  # for "prompt": this prompt starts the tpm skill
    stop_hook_active: bool = False  # for "stop": already continuing because of a stop hook
    background_tasks: list = field(default_factory=list)  # for "stop": in-flight tasks


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
    # armed message ("TPM guard armed (...)") or "" -> Outcome, for a prompt event
    render_prompt: Callable[[str], Outcome]
    state_env: tuple[str, ...] = ()
    # block reason or "" -> Outcome, for a stop event (platforms with a Stop hook)
    render_stop: Callable[[str], Outcome] = lambda reason: Outcome()


# Background task types that are clearly not agents. Anything else unfinished blocks the stop:
# the type labels aren't a closed, verified set, so an unknown one counts as an agent.
NON_AGENT_TASK_TYPES = {"shell", "bash", "monitor", "mcp task"}
FINISHED = {"completed", "complete", "done", "failed", "error", "killed", "cancelled", "canceled", "stopped"}


def outstanding_agents(tasks) -> list[dict]:
    if not isinstance(tasks, list):
        return []
    return [
        t
        for t in tasks
        if isinstance(t, dict)
        and str(t.get("type", "")).lower() not in NON_AGENT_TASK_TYPES
        and str(t.get("status", "")).lower() not in FINISHED
    ]


def stop_reason(tasks: list[dict]) -> str:
    names = "; ".join(
        f"{t.get('type')} {t.get('id', '?')}: {str(t.get('description') or t.get('agent_type') or '')[:80]}"
        for t in tasks
    )
    return (
        f"TPM mode: {len(tasks)} agent task(s) you started are still running ({names}). Don't end the turn "
        "with work outstanding: wait for them and check their results, or tell the user exactly what is "
        "still running and what hasn't started."
    )


# Argument names the guard reads, and the spellings platforms use for them. Shims call
# canonical_args() so the core only ever sees file_path, content, old_string, new_string.
ARG_ALIASES = {
    "path": "file_path",
    "absolute_path": "file_path",
    "file_text": "content",
    "contents": "content",
    "old_str": "old_string",
    "new_str": "new_string",
}


def canonical_args(args, aliases: dict | None = None) -> dict:
    if not isinstance(args, dict):
        return {}
    aliases = ARG_ALIASES if aliases is None else aliases
    out = dict(args)
    for alias, name in aliases.items():
        if alias in out and name not in out:
            out[name] = out.pop(alias)
    if isinstance(out.get("edits"), list):
        out["edits"] = [canonical_args(e, aliases) if isinstance(e, dict) else e for e in out["edits"]]
    return out


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


SESSIONS_DIR = "sessions"


def armed_message(state: str, session_id: str) -> str:
    """The line the model sees when arming works; the skill looks for it."""
    return f"TPM guard armed (session {session_id}, log {os.path.join(state, 'advisory.log')})"


def repo_root(start: str) -> str:
    """The git top level containing `start` (a .git dir or file), or `start` itself."""
    here = os.path.realpath(start)
    probe = here
    while True:
        if os.path.exists(os.path.join(probe, ".git")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return here
        probe = parent


def switched_off(project_dir: str) -> bool:
    """The one test for the off switch: .cadence/tpm.off in the hook's cwd or its git top level."""
    cwd = os.path.realpath(project_dir or os.getcwd())
    return any(os.path.exists(os.path.join(d, OFF_FILE)) for d in {cwd, repo_root(cwd)})


def heartbeat(platform: Platform, state: str, ev: Event, payload: dict) -> None:
    """Record that a hook fired in this session: proof the guard runs live, for `status`."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", ev.session_id or "")
    if not safe:
        return
    path = os.path.join(state, SESSIONS_DIR, safe)
    cwd = os.path.realpath(ev.project_dir or os.getcwd())
    root = repo_root(cwd)
    off = switched_off(cwd)
    record = {
        "session": ev.session_id,
        "platform": platform.name,
        "last_event": str(payload.get("hook_event_name") or ev.kind),
        "time": time.time(),
        # Effective state: armed only if the marker exists and the off switch doesn't.
        "armed": is_armed(state, ev.session_id) and not off,
        "switched_off": off,
        "project": root,
        "cwd": cwd,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.json.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(record, f)
    os.replace(tmp, path + ".json")


def handle(platform: Platform, payload: dict) -> Outcome:
    ev = platform.parse(payload)
    state = state_dir(platform)
    try:
        return _handle(platform, payload, ev, state)
    finally:
        try:
            heartbeat(platform, state, ev, payload)
        except Exception:
            pass  # a heartbeat must never affect the decision


def _handle(platform: Platform, payload: dict, ev: Event, state: str) -> Outcome:
    if ev.kind == "prompt":
        path = marker_path(state, ev.session_id) if ev.starts_tpm else None
        if not path:
            return platform.render_prompt("")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
        if switched_off(ev.project_dir):
            return platform.render_prompt(
                f"TPM guard switched off by .cadence/tpm.off (session {ev.session_id}): instructions only"
            )
        return platform.render_prompt(armed_message(state, ev.session_id))
    if ev.kind == "stop":
        # The off switch wins. Block once per stop: stop_hook_active means we already did, so never loop.
        off = switched_off(ev.project_dir)
        if off or ev.stop_hook_active or not is_armed(state, ev.session_id):
            return platform.render_stop("")
        running = outstanding_agents(ev.background_tasks)
        return platform.render_stop(stop_reason(running) if running else "")
    if ev.kind != "tool" or not is_armed(state, ev.session_id):
        return _allow(platform)
    if switched_off(ev.project_dir):
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
