"""Tests for the Claude Code Stop hook: no ending a TPM turn while agents it started are running."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHIM = os.path.join(ROOT, "adapters", "claude", "shim.py")
RUNNING_AGENT = {"id": "t1", "type": "subagent", "status": "running", "description": "build finish screen"}


def run(payload, state, raw=None):
    env = dict(os.environ, CADENCE_STATE_DIR=state)
    return subprocess.run(
        [sys.executable, SHIM],
        input=raw if raw is not None else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def armed(session="s"):
    state = tempfile.mkdtemp()
    run({"hook_event_name": "UserPromptExpansion", "session_id": session, "command_name": "tpm"}, state)
    return state


def stop(tasks, active=False, session="s"):
    return {
        "hook_event_name": "Stop",
        "session_id": session,
        "stop_hook_active": active,
        "background_tasks": tasks,
    }


def test_blocks_while_an_agent_it_started_is_running():
    out = run(stop([RUNNING_AGENT]), armed())
    assert out.returncode == 0
    decision = json.loads(out.stdout)
    assert decision["decision"] == "block"
    assert "still running" in decision["reason"] and "build finish screen" in decision["reason"]


def test_allows_stop_when_nothing_outstanding():
    state = armed()
    for tasks in (
        [],
        [dict(RUNNING_AGENT, status="completed")],
        [{"id": "sh", "type": "shell", "status": "running", "command": "tail -f log"}],
        [{"id": "c", "type": "monitor", "status": "running"}],
    ):
        out = run(stop(tasks), state)
        assert out.returncode == 0 and out.stdout == "", tasks
    no_field = {"hook_event_name": "Stop", "session_id": "s", "stop_hook_active": False}
    assert run(no_field, state).stdout == ""


def test_never_loops_and_only_in_tpm_mode():
    assert run(stop([RUNNING_AGENT], active=True), armed()).stdout == ""  # already continued once
    assert run(stop([RUNNING_AGENT]), tempfile.mkdtemp()).stdout == ""  # not armed
    assert run(stop([RUNNING_AGENT], session="other"), armed()).stdout == ""  # another session


def test_fails_open_on_bad_input():
    state = armed()
    for raw in ("not json", json.dumps(stop("not-a-list")), json.dumps(stop([None, 5, "x"]))):
        out = run(None, state, raw=raw)
        assert out.returncode == 0 and '"block"' not in out.stdout, raw


def test_stop_hook_is_configured_for_claude_only():
    for name in ("settings.hooks.json", "plugin-hooks.json"):
        hooks = json.load(open(os.path.join(ROOT, "adapters", "claude", name)))["hooks"]
        cmd = hooks["Stop"][0]["hooks"][0]["command"]
        assert cmd == hooks["PreToolUse"][0]["hooks"][0]["command"]  # same fail-open wrapper
    for platform, name in (
        ("copilot", "hooks.json"),
        ("codex", "hooks.json"),
        ("cursor", "hooks.json"),
        ("gemini", "settings.hooks.json"),
    ):
        hooks = json.load(open(os.path.join(ROOT, "adapters", platform, name)))["hooks"]
        assert not {"Stop", "stop", "agentStop", "AfterAgent"} & set(hooks), platform


def test_installed_stop_hook_blocks_from_the_vendored_location():
    repo = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(
        [os.path.join(ROOT, "bin", "cadence-orchestrator.mjs"), "--target", "claude", "--repo", repo],
        check=True,
        capture_output=True,
    )
    hooks = json.load(open(os.path.join(repo, ".claude", "settings.json")))["hooks"]
    cmd = hooks["Stop"][-1]["hooks"][0]["command"]
    state = armed()
    env = dict(os.environ, CLAUDE_PROJECT_DIR=repo, CADENCE_STATE_DIR=state)
    out = subprocess.run(
        ["bash", "-c", cmd], input=json.dumps(stop([RUNNING_AGENT])), capture_output=True, text=True, env=env
    )
    assert out.returncode == 0 and json.loads(out.stdout)["decision"] == "block"
