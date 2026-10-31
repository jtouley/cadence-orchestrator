"""Tests for live-session evidence: heartbeats, the armed marker line, and `status`."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI = os.path.join(ROOT, "bin", "cadence-orchestrator.mjs")


def shim(platform):
    return os.path.join(ROOT, "adapters", platform, "shim.py")


def hook(platform, payload, state, project=None):
    env = dict(os.environ, CADENCE_STATE_DIR=state)
    if project:
        env["CLAUDE_PROJECT_DIR"] = project
    return subprocess.run(
        [sys.executable, shim(platform)], input=json.dumps(payload), capture_output=True, text=True, env=env
    )


def beat(state, session):
    return json.load(open(os.path.join(state, "sessions", f"{session}.json")))


ARM = {
    "claude": {"hook_event_name": "UserPromptExpansion", "session_id": "s1", "command_name": "tpm"},
    "codex": {"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "$tpm go"},
    "copilot": {"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "/tpm go"},
    "cursor": {"hook_event_name": "beforeSubmitPrompt", "conversation_id": "s1", "prompt": "/tpm go"},
    "gemini": {"hook_event_name": "BeforeAgent", "session_id": "s1", "prompt": "/tpm go"},
}


def test_every_hook_event_writes_a_heartbeat():
    state, project = tempfile.mkdtemp(), tempfile.mkdtemp()
    hook(
        "claude",
        {"hook_event_name": "PreToolUse", "session_id": "s1", "tool_name": "Read", "tool_input": {}},
        state,
        project,
    )
    b = beat(state, "s1")
    assert b["platform"] == "claude" and b["last_event"] == "PreToolUse" and b["armed"] is False
    assert b["project"] == os.path.realpath(project) and time.time() - b["time"] < 30
    hook("claude", ARM["claude"], state, project)
    assert beat(state, "s1")["armed"] is True and beat(state, "s1")["last_event"] == "UserPromptExpansion"


def test_armed_marker_line_reaches_the_model_where_the_platform_allows():
    for platform, payload in ARM.items():
        state = tempfile.mkdtemp()
        out = hook(platform, payload, state, tempfile.mkdtemp())
        line = f"TPM guard armed (session s1, log {os.path.join(state, 'advisory.log')})"
        assert out.returncode == 0, platform
        if platform in ("claude", "codex"):
            assert out.stdout.strip() == line, platform  # plain stdout becomes model context
        elif platform == "gemini":
            data = json.loads(out.stdout)
            assert data["hookSpecificOutput"]["additionalContext"] == line and data["systemMessage"] == line
        elif platform == "cursor":
            assert json.loads(out.stdout) == {"continue": True} and line in out.stderr
        else:  # copilot drops prompt-hook output; status is the only evidence
            assert out.stdout == "" and line in out.stderr
        assert beat(state, "s1")["armed"] is True, platform
    not_tpm = hook("codex", dict(ARM["codex"], prompt="fix the bug"), tempfile.mkdtemp())
    assert "TPM guard armed" not in not_tpm.stdout


def test_a_broken_heartbeat_never_changes_the_decision():
    state = tempfile.mkdtemp()
    hook("claude", ARM["claude"], state)
    sessions = os.path.join(state, "sessions")
    for name in os.listdir(sessions):
        os.remove(os.path.join(sessions, name))
    os.rmdir(sessions)
    open(sessions, "w").close()  # a file where the sessions directory should be
    out = hook(
        "claude",
        {"hook_event_name": "PreToolUse", "session_id": "s1", "tool_name": "Write", "tool_input": {}},
        state,
    )
    assert out.returncode == 2 and "TPM mode" in out.stderr


def test_skill_says_instructions_only_when_the_marker_is_missing():
    skill = open(os.path.join(ROOT, "core", "SKILL.md")).read()
    assert "TPM guard armed" in skill and "guard not running in this session" in skill
    assert "instructions only" in skill.lower()


# ------------------------------------------------------------- status


def repo_with(*targets):
    repo = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", repo], check=True)
    for t in targets:
        subprocess.run([CLI, "--target", t, "--repo", repo], check=True, capture_output=True)
    return repo


def status(repo, state, *extra):
    return subprocess.run(
        [CLI, "status", "--repo", repo, *extra],
        capture_output=True,
        text=True,
        env=dict(os.environ, CADENCE_STATE_DIR=state),
    )


def test_status_separates_installed_from_seen_firing():
    repo, state = repo_with("claude", "codex"), tempfile.mkdtemp()
    out = status(repo, state)
    assert out.returncode == 1
    assert "claude: skill files found" in out.stdout and "claude: hook config installed" in out.stdout
    assert "claude: hooks seen firing: none" in out.stdout and "No live hook activity" in out.stdout
    assert "cursor: not installed" in out.stdout and f"advisory log: {state}/advisory.log" in out.stdout
    # A live session: run the installed Claude hook command from inside the repo.
    cmd = json.load(open(os.path.join(repo, ".claude/settings.json")))["hooks"]["PreToolUse"][-1]["hooks"][0][
        "command"
    ]
    env = dict(os.environ, CADENCE_STATE_DIR=state, CLAUDE_PROJECT_DIR=repo)
    for payload in (
        ARM["claude"],
        {"hook_event_name": "PreToolUse", "session_id": "s1", "tool_name": "Read"},
    ):
        subprocess.run(
            ["bash", "-c", cmd], input=json.dumps(payload), cwd=repo, env=env, capture_output=True, text=True
        )
    out = status(repo, state)
    assert out.returncode == 0
    assert "claude: hooks seen firing: 1 session(s) in the last 24 h, 1 armed" in out.stdout
    assert "session s1: armed, last PreToolUse" in out.stdout
    assert "codex: hooks seen firing: none" in out.stdout


def test_status_ignores_old_and_other_repo_sessions():
    repo, state = repo_with("codex"), tempfile.mkdtemp()
    os.makedirs(os.path.join(state, "sessions"))
    old = {
        "session": "old",
        "platform": "codex",
        "last_event": "PreToolUse",
        "time": time.time() - 48 * 3600,
        "armed": True,
        "project": os.path.realpath(repo),
    }
    other = dict(old, session="other", time=time.time(), project=os.path.realpath(tempfile.mkdtemp()))
    for rec in (old, other):
        json.dump(rec, open(os.path.join(state, "sessions", f"{rec['session']}.json"), "w"))
    assert status(repo, state).returncode == 1
    out = status(repo, state, "--hours", "72")
    assert out.returncode == 0 and "session old: armed" in out.stdout and "other" not in out.stdout


def test_status_arguments_and_empty_repo():
    state = tempfile.mkdtemp()
    out = status(repo_with(), state)
    assert out.returncode == 1 and "No target is installed" in out.stdout
    bad = subprocess.run(
        [CLI, "status", "--target", "claude", "--repo", repo_with()], capture_output=True, text=True
    )
    assert bad.returncode == 2 and "status doesn't take --target" in bad.stderr
    bad = subprocess.run(
        [CLI, "status", "--hours", "0", "--repo", repo_with()], capture_output=True, text=True
    )
    assert bad.returncode == 2


def test_doctor_says_the_simulation_is_not_a_live_check():
    repo = repo_with("codex")
    out = subprocess.run([CLI, "doctor", "--target", "codex", "--repo", repo], capture_output=True, text=True)
    assert out.returncode == 0
    assert (
        out.stdout.strip()
        .splitlines()[-1]
        .startswith("Simulation passed; this does not confirm the hooks fire")
    )
    assert "status" in out.stdout.strip().splitlines()[-1]


def test_off_switch_changes_the_marker_line():
    state, project = tempfile.mkdtemp(), tempfile.mkdtemp()
    os.makedirs(os.path.join(project, ".cadence"))
    open(os.path.join(project, ".cadence", "tpm.off"), "w").close()
    out = hook("claude", ARM["claude"], state, project)
    assert "switched off by .cadence/tpm.off" in out.stdout and "instructions only" in out.stdout
    assert "TPM guard armed (" not in out.stdout


# ------------------------------------------------------------- PR #5 review fixes


def run_installed(repo, state, payloads, cwd=None, platform="codex"):
    hooks = json.load(open(os.path.join(repo, ".codex/hooks.json")))["hooks"]
    cmd = hooks["PreToolUse"][-1]["hooks"][0]["command"]
    env = dict(os.environ, CADENCE_STATE_DIR=state)
    for p in payloads:
        subprocess.run(
            ["bash", "-c", cmd], input=json.dumps(p), cwd=cwd or repo, env=env, capture_output=True, text=True
        )


def test_sessions_started_in_a_subdirectory_count_for_the_repo():
    repo, state = repo_with("codex"), tempfile.mkdtemp()
    sub = os.path.join(repo, "app", "src")
    os.makedirs(sub)
    run_installed(repo, state, [dict(ARM["codex"], cwd=sub)], cwd=sub)
    b = beat(state, "s1")
    assert b["project"] == os.path.realpath(repo) and b["cwd"] == os.path.realpath(sub)
    out = status(repo, state)
    assert out.returncode == 0 and "session s1: armed" in out.stdout


def test_switched_off_sessions_are_not_reported_as_armed():
    repo, state = repo_with("codex"), tempfile.mkdtemp()
    os.makedirs(os.path.join(repo, ".cadence"))
    open(os.path.join(repo, ".cadence", "tpm.off"), "w").close()
    run_installed(repo, state, [dict(ARM["codex"], cwd=repo)])
    b = beat(state, "s1")
    assert b["armed"] is False and b["switched_off"] is True
    out = status(repo, state)
    assert "0 armed, 1 switched off" in out.stdout
    assert (
        "session s1: switched off (.cadence/tpm.off)" in out.stdout and "session s1: armed" not in out.stdout
    )


def test_status_state_dir_flag_and_source():
    repo, state = repo_with("codex"), tempfile.mkdtemp()
    run_installed(repo, state, [dict(ARM["codex"], cwd=repo)])
    # The terminal doesn't have the agent's CADENCE_STATE_DIR: nothing found...
    env = {k: v for k, v in os.environ.items() if k != "CADENCE_STATE_DIR"}
    env["TMPDIR"] = tempfile.mkdtemp()
    out = subprocess.run([CLI, "status", "--repo", repo], capture_output=True, text=True, env=env)
    assert out.returncode == 1 and "(from temp dir)" in out.stdout
    # ...until it's pointed at the agent's state dir.
    out = subprocess.run(
        [CLI, "status", "--repo", repo, "--state-dir", state], capture_output=True, text=True, env=env
    )
    assert out.returncode == 0 and f"state dir: {state} (from --state-dir)" in out.stdout
    assert "session s1: armed" in out.stdout
    out = status(repo, state)
    assert f"state dir: {state} (from CADENCE_STATE_DIR)" in out.stdout
    bad = subprocess.run(
        [CLI, "doctor", "--target", "codex", "--repo", repo, "--state-dir", state],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 2 and "doesn't take --state-dir" in bad.stderr
