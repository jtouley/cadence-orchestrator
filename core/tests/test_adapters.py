"""Tests for the normalized core CLI, every platform shim, and install.sh.

Run with `python3 test_adapters.py` or `pytest`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GUARD = os.path.join(ROOT, "core", "scripts", "guard.py")
INSTALL = os.path.join(ROOT, "install.sh")


def shim(platform):
    return os.path.join(ROOT, "adapters", platform, "shim.py")


def run(path, payload, state, env_extra=None, cwd=None):
    env = dict(os.environ, CADENCE_STATE_DIR=state)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(env_extra or {})
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, path], input=raw, capture_output=True, text=True,
                          env=env, cwd=cwd)


# ------------------------------------------------------------- core CLI

def core(tool, args=None, is_subagent=False):
    proc = subprocess.run([sys.executable, GUARD], capture_output=True, text=True,
                          input=json.dumps({"tool": tool, "args": args or {},
                                            "is_subagent": is_subagent}))
    assert proc.returncode == 0
    return json.loads(proc.stdout)


def test_core_normalized_cli():
    assert core("Write")["decision"] == "deny"
    assert core("Write", is_subagent=True)["decision"] == "allow"
    assert core("Bash", {"command": "git status"})["decision"] == "allow"
    assert core("Bash", {"command": "rm -rf z"})["decision"] == "deny"
    assert "TPM mode" in core("Edit")["reason"]
    bad = subprocess.run([sys.executable, GUARD], input="nope", capture_output=True, text=True)
    assert json.loads(bad.stdout)["decision"] == "allow"


# ------------------------------------------------------------- enforcing shims

def test_copilot_enforces_with_json_and_exit_0():
    st = tempfile.mkdtemp()
    p = shim("copilot")
    write = {"hook_event_name": "PreToolUse", "session_id": "s", "cwd": st,
             "tool_name": "Write", "tool_input": {}}
    assert run(p, write, st).stdout == ""                       # unarmed: allow
    arm = run(p, {"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt": "/tpm go"}, st)
    assert arm.returncode == 0 and arm.stdout == ""
    out = run(p, write, st)
    assert out.returncode == 0
    assert json.loads(out.stdout)["permissionDecision"] == "deny"
    assert run(p, dict(write, agent_id="sub1"), st).stdout == ""  # subagent: allow
    read = dict(write, tool_name="Bash", tool_input={"command": "git log -3"})
    assert run(p, read, st).stdout == ""
    camel = {"sessionId": "s", "cwd": st, "toolName": "Write", "toolArgs": "{}"}
    assert json.loads(run(p, camel, st).stdout)["permissionDecision"] == "deny"
    assert run(p, dict(camel, agentId="sub"), st).stdout == ""
    # Not a tpm prompt: no arming.
    run(p, {"hook_event_name": "UserPromptSubmit", "session_id": "t", "prompt": "fix tpm bug"}, st)
    assert run(p, dict(write, session_id="t"), st).stdout == ""


# ------------------------------------------------------------- advisory shims

def arm_with(platform, st, session):
    events = {"codex": {"hook_event_name": "UserPromptSubmit", "session_id": session},
              "cursor": {"conversation_id": session, "hook_event_name": "beforeSubmitPrompt"},
              "gemini": {"hook_event_name": "BeforeAgent", "session_id": session}}
    return run(shim(platform), dict(events[platform], prompt="$tpm build it"), st)


def tool_payload(platform, session, cwd, name, args):
    if platform == "cursor":
        return {"conversation_id": session, "hook_event_name": "preToolUse",
                "workspace_roots": [cwd], "tool_name": name, "tool_input": args}
    event = "BeforeTool" if platform == "gemini" else "PreToolUse"
    return {"hook_event_name": event, "session_id": session, "cwd": cwd,
            "tool_name": name, "tool_input": args}


ADVISORY_CASES = {
    # platform: (mutating tool, read-only tool)
    "codex": (("apply_patch", {"command": "*** Begin Patch"}), ("Bash", {"command": "ls"})),
    "cursor": (("Shell", {"command": "rm -rf build"}), ("Read", {"path": "a"})),
    "gemini": (("write_file", {"file_path": "a"}), ("run_shell_command", {"command": "git diff"})),
}


def test_advisory_shims_never_block_and_warn_when_armed():
    for platform, (bad, good) in ADVISORY_CASES.items():
        st = tempfile.mkdtemp()
        p = shim(platform)
        unarmed = run(p, tool_payload(platform, "s", st, *bad), st)
        assert unarmed.returncode == 0, platform
        assert "advisory" not in unarmed.stdout + unarmed.stderr, platform
        armed = arm_with(platform, st, "s")
        assert armed.returncode == 0, platform
        if platform == "cursor":
            assert json.loads(armed.stdout) == {"continue": True}
        warn = run(p, tool_payload(platform, "s", st, *bad), st)
        assert warn.returncode == 0, platform
        assert "tpm advisory" in warn.stdout + warn.stderr, platform
        if platform == "cursor":
            assert json.loads(warn.stdout) == {"permission": "allow"}
        if platform in ("codex", "gemini"):
            assert "systemMessage" in json.loads(warn.stdout), platform
        quiet = run(p, tool_payload(platform, "s", st, *good), st)
        assert quiet.returncode == 0 and "advisory" not in quiet.stdout + quiet.stderr, platform
        log = open(os.path.join(st, "advisory.log")).read()
        assert platform in log


def test_advisory_shims_print_valid_json_where_required():
    st = tempfile.mkdtemp()
    for platform in ("cursor", "gemini"):
        for payload in ("not json", {"hook_event_name": "Other"}):
            out = run(shim(platform), payload, st)
            assert out.returncode == 0
            json.loads(out.stdout)


def test_off_switch_applies_to_every_platform():
    for platform in ("copilot", "codex", "cursor", "gemini"):
        st = tempfile.mkdtemp()
        os.makedirs(os.path.join(st, ".cadence"))
        open(os.path.join(st, ".cadence", "tpm.off"), "w").close()
        if platform == "copilot":
            run(shim(platform), {"hook_event_name": "UserPromptSubmit", "session_id": "s",
                                 "prompt": "/tpm"}, st)
            payload = {"session_id": "s", "cwd": st, "tool_name": "Write", "tool_input": {}}
        else:
            arm_with(platform, st, "s")
            payload = tool_payload(platform, "s", st, *ADVISORY_CASES[platform][0])
        out = run(shim(platform), payload, st)
        assert "deny" not in out.stdout and "advisory" not in out.stdout + out.stderr, platform


# ------------------------------------------------------------- install.sh

def scratch_repo():
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True)
    return d


def install(repo, target):
    proc = subprocess.run([INSTALL, "--target", target, "--repo", repo],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def snapshot(repo):
    files = {}
    for base, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d != ".git"]
        for n in names:
            path = os.path.join(base, n)
            files[os.path.relpath(path, repo)] = open(path, "rb").read()
    return files


EXPECTED = {
    "claude": [".claude/skills/tpm/SKILL.md", ".claude/skills/tpm/scripts/shim_claude.py",
               ".claude/settings.json"],
    "copilot": [".github/skills/tpm/scripts/shim_copilot.py", ".github/hooks/tpm.json"],
    "codex": [".agents/skills/tpm/scripts/shim_codex.py", ".codex/hooks.json", "AGENTS.md"],
    "cursor": [".agents/skills/tpm/scripts/shim_cursor.py", ".cursor/hooks.json",
               ".cursor/rules/tpm.mdc"],
    "gemini": [".agents/skills/tpm/scripts/shim_gemini.py", ".gemini/settings.json", "GEMINI.md"],
}


def test_install_each_target_is_complete_and_idempotent():
    for target, paths in EXPECTED.items():
        repo = scratch_repo()
        install(repo, target)
        for rel in paths + [".gitignore"]:
            assert os.path.exists(os.path.join(repo, rel)), (target, rel)
        first = snapshot(repo)
        install(repo, target)
        assert snapshot(repo) == first, target


def test_install_keeps_existing_config_and_replaces_only_its_own_entries():
    repo = scratch_repo()
    os.makedirs(os.path.join(repo, ".claude"))
    mine = {"permissions": {"allow": ["Bash(npm test)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": "./my-hook.sh"}]}]}}
    json.dump(mine, open(os.path.join(repo, ".claude", "settings.json"), "w"))
    open(os.path.join(repo, "AGENTS.md"), "w").write("# Rules\n\nBe nice.\n")
    install(repo, "claude")
    install(repo, "codex")
    install(repo, "codex")
    settings = json.load(open(os.path.join(repo, ".claude", "settings.json")))
    assert settings["permissions"] == mine["permissions"]
    pre = settings["hooks"]["PreToolUse"]
    assert pre[0]["hooks"][0]["command"] == "./my-hook.sh" and len(pre) == 2
    agents = open(os.path.join(repo, "AGENTS.md")).read()
    assert agents.startswith("# Rules") and agents.count("cadence-orchestrator:tpm begin") == 1


def test_install_claude_skill_is_user_invoked_only():
    repo = scratch_repo()
    install(repo, "claude")
    fm = open(os.path.join(repo, ".claude/skills/tpm/SKILL.md")).read().split("\n---\n")[0]
    assert "disable-model-invocation: true" in fm
    repo2 = scratch_repo()
    install(repo2, "codex")
    fm2 = open(os.path.join(repo2, ".agents/skills/tpm/SKILL.md")).read().split("\n---\n")[0]
    assert "disable-model-invocation" not in fm2


def test_vendored_hooks_run_from_the_installed_location():
    repo = scratch_repo()
    install(repo, "all")
    st = tempfile.mkdtemp()
    # Claude: run the exact command from the merged settings.
    cmd = json.load(open(os.path.join(repo, ".claude/settings.json")))[
        "hooks"]["PreToolUse"][-1]["hooks"][0]["command"]
    env = dict(os.environ, CLAUDE_PROJECT_DIR=repo, CADENCE_STATE_DIR=st)

    def sh(command, payload):
        return subprocess.run(["bash", "-c", command], input=json.dumps(payload), cwd=repo,
                              capture_output=True, text=True, env=env)

    sh(cmd, {"hook_event_name": "UserPromptExpansion", "session_id": "v", "command_name": "tpm"})
    out = sh(cmd, {"hook_event_name": "PreToolUse", "session_id": "v", "tool_name": "Write",
                   "tool_input": {}})
    assert out.returncode == 2 and "TPM mode" in out.stderr
    # Copilot and Cursor commands, as written into their hook files.
    cop = json.load(open(os.path.join(repo, ".github/hooks/tpm.json")))["hooks"]
    sh(cop["UserPromptSubmit"][0]["bash"], {"session_id": "c", "prompt": "/tpm"})
    out = sh(cop["PreToolUse"][0]["bash"], {"session_id": "c", "cwd": repo, "tool_name": "Edit",
                                            "tool_input": {}})
    assert json.loads(out.stdout)["permissionDecision"] == "deny"
    cur = json.load(open(os.path.join(repo, ".cursor/hooks.json")))["hooks"]
    out = sh(cur["preToolUse"][0]["command"], {"conversation_id": "k", "tool_name": "Shell",
                                               "tool_input": {"command": "ls"}})
    assert json.loads(out.stdout) == {"permission": "allow"}


def test_install_rejects_non_repo():
    proc = subprocess.run([INSTALL, "--target", "claude", "--repo", tempfile.mkdtemp()],
                          capture_output=True, text=True)
    assert proc.returncode == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(tests)} passed")
