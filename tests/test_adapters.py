"""Tests for the normalized core CLI, every platform shim, and the Node installer.

Run with `pytest`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GUARD = os.path.join(ROOT, "skills", "tpm", "scripts", "guard.py")
INSTALL = os.path.join(ROOT, "bin", "cadence-orchestrator.mjs")  # the one installer
INSTALL_SH = os.path.join(ROOT, "install.sh")  # thin wrapper over it


def shim(platform):
    return os.path.join(ROOT, "adapters", platform, "shim.py")


def run(path, payload, state, env_extra=None, cwd=None):
    env = dict(os.environ, CADENCE_STATE_DIR=state)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(env_extra or {})
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, path], input=raw, capture_output=True, text=True, env=env, cwd=cwd)


# ------------------------------------------------------------- core CLI


def core(tool, args=None, is_subagent=False):
    proc = subprocess.run(
        [sys.executable, GUARD],
        capture_output=True,
        text=True,
        input=json.dumps({"tool": tool, "args": args or {}, "is_subagent": is_subagent}),
    )
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
    write = {
        "hook_event_name": "PreToolUse",
        "session_id": "s",
        "cwd": st,
        "tool_name": "Write",
        "tool_input": {},
    }
    assert run(p, write, st).stdout == ""  # unarmed: allow
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
    events = {
        "codex": {"hook_event_name": "UserPromptSubmit", "session_id": session},
        "cursor": {"conversation_id": session, "hook_event_name": "beforeSubmitPrompt"},
        "gemini": {"hook_event_name": "BeforeAgent", "session_id": session},
    }
    return run(shim(platform), dict(events[platform], prompt="$tpm build it"), st)


def tool_payload(platform, session, cwd, name, args):
    if platform == "cursor":
        return {
            "conversation_id": session,
            "hook_event_name": "preToolUse",
            "workspace_roots": [cwd],
            "tool_name": name,
            "tool_input": args,
        }
    event = "BeforeTool" if platform == "gemini" else "PreToolUse"
    return {
        "hook_event_name": event,
        "session_id": session,
        "cwd": cwd,
        "tool_name": name,
        "tool_input": args,
    }


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
            run(
                shim(platform),
                {"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt": "/tpm"},
                st,
            )
            payload = {"session_id": "s", "cwd": st, "tool_name": "Write", "tool_input": {}}
        else:
            arm_with(platform, st, "s")
            payload = tool_payload(platform, "s", st, *ADVISORY_CASES[platform][0])
        out = run(shim(platform), payload, st)
        assert "deny" not in out.stdout and "advisory" not in out.stdout + out.stderr, platform


# ------------------------------------------------------------- install.sh


# Variables agents set in the commands they run; cleared so detection sees only what a test sets.
AGENT_VARS = (
    "CLAUDECODE",
    "CODEX_THREAD_ID",
    "CODEX_SANDBOX",
    "CODEX_SANDBOX_NETWORK_DISABLED",
    "CURSOR_AGENT",
    "GEMINI_CLI",
)


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in AGENT_VARS}
    env.update(extra)
    return env


def scratch_repo():
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True)
    return d


def install(repo, target):
    proc = subprocess.run([INSTALL, "--target", target, "--repo", repo], capture_output=True, text=True)
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
    "antigravity": [".agents/skills/tpm/SKILL.md", ".agents/rules/tpm.md"],
    "claude": [
        ".claude/skills/tpm/SKILL.md",
        ".claude/skills/tpm/scripts/shim_claude.py",
        ".claude/settings.json",
    ],
    "copilot": [".github/skills/tpm/scripts/shim_copilot.py", ".github/hooks/tpm.json"],
    "codex": [".agents/skills/tpm/scripts/shim_codex.py", ".codex/hooks.json", "AGENTS.md"],
    "cursor": [".agents/skills/tpm/scripts/shim_cursor.py", ".cursor/hooks.json", ".cursor/rules/tpm.mdc"],
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
    mine = {
        "permissions": {"allow": ["Bash(npm test)"]},
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "./my-hook.sh"}]}]
        },
    }
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
    cmd = json.load(open(os.path.join(repo, ".claude/settings.json")))["hooks"]["PreToolUse"][-1]["hooks"][0][
        "command"
    ]
    env = dict(os.environ, CLAUDE_PROJECT_DIR=repo, CADENCE_STATE_DIR=st)

    def sh(command, payload):
        return subprocess.run(
            ["bash", "-c", command],
            input=json.dumps(payload),
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )

    sh(cmd, {"hook_event_name": "UserPromptExpansion", "session_id": "v", "command_name": "tpm"})
    out = sh(
        cmd, {"hook_event_name": "PreToolUse", "session_id": "v", "tool_name": "Write", "tool_input": {}}
    )
    assert out.returncode == 2 and "TPM mode" in out.stderr
    # Copilot and Cursor commands, as written into their hook files.
    cop = json.load(open(os.path.join(repo, ".github/hooks/tpm.json")))["hooks"]
    sh(cop["UserPromptSubmit"][0]["bash"], {"session_id": "c", "prompt": "/tpm"})
    out = sh(
        cop["PreToolUse"][0]["bash"], {"session_id": "c", "cwd": repo, "tool_name": "Edit", "tool_input": {}}
    )
    assert json.loads(out.stdout)["permissionDecision"] == "deny"
    cur = json.load(open(os.path.join(repo, ".cursor/hooks.json")))["hooks"]
    out = sh(
        cur["preToolUse"][0]["command"],
        {"conversation_id": "k", "tool_name": "Shell", "tool_input": {"command": "ls"}},
    )
    assert json.loads(out.stdout) == {"permission": "allow"}


def test_install_gitignores_only_the_off_switch_and_adds_catalogs():
    repo = scratch_repo()
    open(os.path.join(repo, ".gitignore"), "w").write("node_modules/\n.cadence/\n")  # older install
    cat = os.path.join(tempfile.mkdtemp(), "team.md")
    open(cat, "w").write("# Team catalog\n\n## Set\n\n- **Source**: x\n- **Skills**:\n  - `a`: b\n")
    proc = subprocess.run(
        [INSTALL, "--target", "codex", "--repo", repo, "--catalog", cat], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    lines = open(os.path.join(repo, ".gitignore")).read().split("\n")
    assert ".cadence/tpm.off" in lines and ".cadence/" not in lines and "node_modules/" in lines
    assert open(os.path.join(repo, ".cadence/catalog/team.md")).read().startswith("# Team catalog")
    ignored = subprocess.run(["git", "-C", repo, "check-ignore", "-q", ".cadence/catalog/team.md"])
    assert ignored.returncode == 1  # the catalog is committable


def test_shipped_catalog_is_labeled_as_an_example_and_documented():
    refs = os.path.join(ROOT, "skills", "tpm", "references")
    example = open(os.path.join(refs, "example-registry.md")).read()
    assert "One user's catalog, shipped as an example" in example
    assert "## " in example and "- **Source**:" in example and "- **Skills**:" in example
    lookup = open(os.path.join(refs, "catalogs.md")).read()
    for where in (".cadence/catalog/", "CADENCE_CATALOG_PATH", "~/.cadence/catalog/", "example-registry.md"):
        assert where in lookup, where


def test_install_sh_delegates_to_the_node_installer():
    repo = scratch_repo()
    proc = subprocess.run([INSTALL_SH, "--target", "cursor", "--repo", repo], capture_output=True, text=True)
    assert proc.returncode == 0 and f"Installing into {repo}\ncursor: " in proc.stdout
    assert os.path.exists(os.path.join(repo, ".cursor/hooks.json"))


def test_installer_warns_without_python3_and_checks_arguments():
    repo = scratch_repo()
    node = subprocess.run(["bash", "-c", "command -v node"], capture_output=True, text=True).stdout.strip()
    bare = tempfile.mkdtemp()
    os.symlink(node, os.path.join(bare, "node"))  # PATH with node but no python3
    proc = subprocess.run(
        [os.path.join(bare, "node"), INSTALL, "--target", "claude", "--repo", repo],
        capture_output=True,
        text=True,
        env={"PATH": bare},
    )
    assert proc.returncode == 0 and "python3 is not on PATH" in proc.stderr
    for argv in (["--target", "nope"], [], ["--repo"], ["--bogus"]):  # [] and --repo: nothing detected
        out = subprocess.run([INSTALL] + argv, capture_output=True, cwd=scratch_repo(), env=clean_env())
        assert out.returncode == 2, argv
    helped = subprocess.run([INSTALL, "--help"], capture_output=True, text=True)
    assert helped.returncode == 0 and "--target" in helped.stdout


def test_workstream_reference_example_is_valid_and_complete():
    import re

    refs = os.path.join(ROOT, "skills", "tpm", "references")
    text = open(os.path.join(refs, "workstream.md")).read()
    data = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
    for task in data["tasks"]:
        for key in ("id", "owner", "doc_sha", "state", "evidence", "left_out", "tokens"):
            assert key in task, key
        if task["state"] == "done":
            assert task["evidence"] and task["left_out_accepted_by"]
    skill = open(os.path.join(ROOT, "skills", "tpm", "SKILL.md")).read()
    assert "references/sources.md" in skill and "@<sha>" in skill
    assert os.path.exists(os.path.join(refs, "sources.md"))


def _path_without_python3():
    d = tempfile.mkdtemp()
    for tool in ("git", "dirname"):
        found = subprocess.run(["bash", "-c", f"command -v {tool}"], capture_output=True, text=True)
        if found.stdout.strip():
            os.symlink(found.stdout.strip(), os.path.join(d, tool))
    return d


# target: (hook file, (event, index) of the tool hook, how to get the command, shim, expected stdout)
FAIL_OPEN = {
    "copilot": (
        ".github/hooks/tpm.json",
        lambda h: h["PreToolUse"][0]["bash"],
        ".github/skills/tpm/scripts/shim_copilot.py",
        "",
    ),
    "claude": (
        ".claude/settings.json",
        lambda h: h["PreToolUse"][-1]["hooks"][0]["command"],
        ".claude/skills/tpm/scripts/shim_claude.py",
        "",
    ),
    "gemini": (
        ".gemini/settings.json",
        lambda h: h["BeforeTool"][-1]["hooks"][0]["command"],
        ".agents/skills/tpm/scripts/shim_gemini.py",
        "{}",
    ),
    "codex": (
        ".codex/hooks.json",
        lambda h: h["PreToolUse"][-1]["hooks"][0]["command"],
        ".agents/skills/tpm/scripts/shim_codex.py",
        "",
    ),
    "cursor": (
        ".cursor/hooks.json",
        lambda h: h["preToolUse"][-1]["command"],
        ".agents/skills/tpm/scripts/shim_cursor.py",
        '{"permission": "allow"}',
    ),
    "cursor-prompt": (
        ".cursor/hooks.json",
        lambda h: h["beforeSubmitPrompt"][-1]["command"],
        ".agents/skills/tpm/scripts/shim_cursor.py",
        '{"continue": true}',
    ),
}


def test_hooks_fail_open_without_python3_or_shim():
    # Copilot denies on any non-zero exit; Claude Code, Gemini, Codex and Cursor block
    # on exit 2, which is what `python3 <missing file>` returns. So a missing python3
    # or a missing shim must exit 0 without a deny (and valid JSON where required).
    payload = {"hook_event_name": "PreToolUse", "session_id": "s", "tool_name": "Write", "tool_input": {}}
    for target, (hook_file, get_cmd, shim_file, expected) in FAIL_OPEN.items():
        repo = scratch_repo()
        install(repo, target.split("-")[0])
        cmd = get_cmd(json.load(open(os.path.join(repo, hook_file)))["hooks"])
        env = {"PATH": _path_without_python3(), "CLAUDE_PROJECT_DIR": repo}
        out = subprocess.run(
            ["/bin/bash", "-c", cmd],
            input=json.dumps(payload),
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )
        assert out.returncode == 0 and out.stdout.strip() == expected, (target, out)
        assert "allowing" in out.stderr, target
        os.remove(os.path.join(repo, shim_file))
        env["PATH"] = os.environ["PATH"]
        out = subprocess.run(
            ["/bin/bash", "-c", cmd],
            input=json.dumps(payload),
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )
        assert out.returncode == 0 and out.stdout.strip() == expected, (target, out)


def test_claude_plugin_hook_fails_open_without_python3():
    hooks = json.load(open(os.path.join(ROOT, "adapters/claude/plugin-hooks.json")))["hooks"]
    cmd = hooks["PreToolUse"][0]["hooks"][0]["command"]
    for env in (
        {"PATH": _path_without_python3(), "CLAUDE_PLUGIN_ROOT": ROOT},
        {"PATH": os.environ["PATH"], "CLAUDE_PLUGIN_ROOT": tempfile.mkdtemp()},
    ):
        out = subprocess.run(["/bin/bash", "-c", cmd], input="{}", capture_output=True, text=True, env=env)
        assert out.returncode == 0 and "allowing" in out.stderr


def test_install_rejects_non_repo():
    proc = subprocess.run(
        [INSTALL, "--target", "claude", "--repo", tempfile.mkdtemp()], capture_output=True, text=True
    )
    assert proc.returncode == 1


def cli(argv, cwd, **env):
    return subprocess.run([INSTALL, *argv], capture_output=True, text=True, cwd=cwd, env=clean_env(**env))


def _repo_with_subfolder():
    repo = os.path.realpath(scratch_repo())
    sub = os.path.join(repo, "src", "pkg")
    os.makedirs(sub)
    return repo, sub


def _installs_into(repo, argv, cwd):
    proc = cli(["--target", "cursor", *argv], cwd)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == f"Installing into {repo}"
    assert os.path.exists(os.path.join(repo, ".cursor/hooks.json"))
    assert cwd == repo or not os.path.exists(os.path.join(cwd, ".cursor"))


def test_install_from_a_subfolder_uses_the_repo_top_level():
    repo, sub = _repo_with_subfolder()
    _installs_into(repo, [], cwd=sub)


def test_bare_repo_flag_means_the_current_repo():
    repo, sub = _repo_with_subfolder()
    _installs_into(repo, ["--repo"], cwd=sub)  # last, as typed in the report
    proc = cli(["--repo", "--target", "cursor"], sub)  # followed by a known flag
    assert proc.returncode == 0 and proc.stdout.startswith(f"Installing into {repo}\n"), proc.stderr


def test_repo_path_starting_with_a_dash_is_a_path():
    parent = os.path.realpath(tempfile.mkdtemp())
    repo = os.path.join(parent, "-proj")
    subprocess.run(["git", "init", "-q", "--", repo], check=True)
    for argv in (["--repo", "-proj"], ["--repo=-proj"]):
        proc = cli(["--target", "cursor", *argv], parent)
        assert proc.returncode == 0 and proc.stdout.startswith(f"Installing into {repo}\n"), (
            argv,
            proc.stderr,
        )


def test_explicit_repo_must_be_a_repository_root():
    repo, sub = _repo_with_subfolder()
    proc = cli(["--target", "cursor", "--repo", sub], tempfile.mkdtemp())
    assert (
        proc.returncode == 1 and proc.stderr == f"cadence-orchestrator: {sub} is not a git repository root\n"
    )
    assert not os.path.exists(os.path.join(repo, ".cursor"))
    _installs_into(repo, ["--repo", repo], cwd=sub)


def test_no_repository_fails_with_one_short_line():
    outside = os.path.realpath(tempfile.mkdtemp())
    for argv in ([], ["--repo"]):
        proc = cli(["--target", "cursor", *argv], outside)
        assert proc.returncode == 1, argv
        assert proc.stderr == f"cadence-orchestrator: {outside} is not inside a git repository\n", argv
        assert proc.stdout == "" and not os.path.exists(os.path.join(outside, ".cursor"))


def test_install_never_walks_up_into_a_home_directory_repo():
    home = os.path.realpath(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", home], check=True)  # dotfiles in git
    for rel in (".claude", ".cursor", ".codex"):
        os.makedirs(os.path.join(home, rel))
    sub = os.path.join(home, "Downloads", "foo")
    os.makedirs(sub)
    refused = f"cadence-orchestrator: {home} is your home directory; run this inside a project's repository, or pass --repo\n"
    for argv, cwd in (([], sub), (["--repo"], home)):
        proc = cli(argv, cwd, HOME=home)
        assert proc.returncode == 1 and proc.stdout == "" and proc.stderr == refused, (argv, proc.stderr)
    assert not os.path.exists(os.path.join(home, ".claude/settings.json"))
    # Read-only modes don't refuse: HOME can be the checkout (CI, Heroku-style /app, devcontainers).
    for argv in (["status"], ["doctor", "--target", "all"], ["dora", "--json"]):
        proc = cli(argv, sub, HOME=home)
        assert "home directory" not in proc.stderr, (argv, proc.stderr)
    # An explicit --repo is taken as given.
    proc = cli(["--repo", home], sub, HOME=home)
    assert proc.returncode == 0 and proc.stdout.startswith(f"Installing into {home} for "), proc.stderr


def test_doctor_status_and_dora_resolve_the_repo_like_the_installer():
    repo, sub = _repo_with_subfolder()
    install(repo, "cursor")
    git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    for argv in (["doctor", "--target", "cursor"], ["status"], ["dora", "--json"]):
        for extra in ([], ["--repo"]):
            proc = cli([*argv, *extra], sub)
            assert "not inside a git repository" not in proc.stderr, (argv, extra)
            assert "cursor: not installed" not in proc.stdout, (argv, extra)  # found the top level's install
            if argv[0] == "dora":
                assert proc.returncode == 0 and json.loads(proc.stdout), (extra, proc.stderr)
            else:
                assert "cursor: skill files found" in proc.stdout or "ok   cursor:" in proc.stdout, (
                    proc.stdout
                )
    outside = tempfile.mkdtemp()
    for argv in (["doctor", "--target", "cursor"], ["status"], ["dora"]):
        proc = cli(argv, outside)
        assert proc.returncode == 1 and proc.stderr.count("\n") == 1, argv


MARKERS = {
    "antigravity": [".agent/", ".agents/rules/", ".agents/workflows/", ".agents/hooks.json"],
    "claude": [".claude/"],
    "codex": [".codex/"],
    "copilot": [".github/copilot-instructions.md", ".github/hooks/"],
    "cursor": [".cursor/"],
    "gemini": [".gemini/"],
}


def _with_markers(*rels):
    repo = os.path.realpath(scratch_repo())
    for rel in rels:
        path = os.path.join(repo, rel)
        if rel.endswith("/"):
            os.makedirs(path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").write("# mine\n")
    return repo


def test_bare_run_installs_for_each_detected_editor_only():
    for target, markers in MARKERS.items():
        for marker in markers:
            repo = _with_markers(marker)
            proc = cli([], repo)
            assert proc.returncode == 0, (marker, proc.stderr)
            assert proc.stdout.startswith(f"Installing into {repo} for {target} (detected)\n"), marker
            for rel in EXPECTED[target]:
                assert os.path.exists(os.path.join(repo, rel)), (marker, rel)
            others = {p for t, paths in EXPECTED.items() if t != target for p in paths} - set(
                EXPECTED[target]
            )
            others.discard(
                ".agents/skills/tpm/SKILL.md"
            )  # the skill folder Antigravity, Codex, Cursor, Gemini share
            assert not [p for p in others if os.path.exists(os.path.join(repo, p))], marker
    repo = _with_markers(".cursor/", ".claude/")
    assert cli([], repo).stdout.startswith(f"Installing into {repo} for claude, cursor (detected)\n")


def test_agents_md_alone_does_not_select_codex():
    repo = _with_markers("AGENTS.md", ".cursor/")
    proc = cli([], repo)
    assert proc.stdout.startswith(f"Installing into {repo} for cursor (detected)\n"), proc.stdout
    assert (
        not os.path.exists(os.path.join(repo, ".codex"))
        and open(os.path.join(repo, "AGENTS.md")).read() == "# mine\n"
    )


def test_without_markers_the_host_agent_is_detected_from_its_documented_variable():
    for var, target in (
        ("CLAUDECODE", "claude"),
        ("CODEX_THREAD_ID", "codex"),
        ("CODEX_SANDBOX", "codex"),
        ("CODEX_SANDBOX_NETWORK_DISABLED", "codex"),
        ("CURSOR_AGENT", "cursor"),
        ("GEMINI_CLI", "gemini"),
    ):
        repo = os.path.realpath(scratch_repo())
        proc = cli([], repo, **{var: "1"})
        assert proc.returncode == 0, (var, proc.stderr)
        assert proc.stdout.startswith(f"Installing into {repo} for {target} (running under it: {var})\n"), var
        assert all(os.path.exists(os.path.join(repo, p)) for p in EXPECTED[target]), var
    marked = _with_markers(".gemini/")  # markers win over the environment
    assert cli([], marked, CLAUDECODE="1").stdout.startswith(
        f"Installing into {marked} for gemini (detected)\n"
    )


def test_bare_run_is_idempotent():
    repo = _with_markers(".cursor/", ".codex/", ".agents/rules/")
    first = cli([], repo)
    once = snapshot(repo)
    second = cli([], repo)
    assert first.returncode == second.returncode == 0 and snapshot(repo) == once
    assert first.stdout == second.stdout  # installing adds no marker for another editor


def test_closing_lines_are_per_target():
    repo = _with_markers(".codex/", ".cursor/", ".agents/rules/")
    tail = cli([], repo).stdout.splitlines()[-6:]
    assert tail == [
        "Done. Review and commit the changes; see README for per-platform notes.",
        "Reload once: start a new chat or session in this repo, so the hooks load (approve them if asked).",
        "antigravity: start with /tpm (instructions only)",
        "codex: start with $tpm",
        "cursor: start with /tpm",
        "Then check the guard is running: npx cadence-orchestrator status",
    ]
    only = cli([], _with_markers(".agent/")).stdout
    assert "hook" not in only and "status" not in only, only
    assert only.splitlines()[-1] == "antigravity: start with /tpm (instructions only)"


def test_python3_warning_only_for_guarded_targets_and_after_the_repo_line():
    node = subprocess.run(["bash", "-c", "command -v node"], capture_output=True, text=True).stdout.strip()
    git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True, text=True).stdout.strip()
    bare = tempfile.mkdtemp()
    os.symlink(node, os.path.join(bare, "node"))
    os.symlink(git, os.path.join(bare, "git"))
    run_bare = lambda repo, target: subprocess.run(  # noqa: E731
        [os.path.join(bare, "node"), INSTALL, "--target", target, "--repo", repo],
        capture_output=True,
        text=True,
        env={"PATH": bare, "HOME": os.environ.get("HOME", "/")},
    )
    assert "python3" not in run_bare(scratch_repo(), "antigravity").stderr
    both = subprocess.run(
        f"{os.path.join(bare, 'node')} {INSTALL} --target cursor --repo {scratch_repo()} 2>&1",
        shell=True,
        capture_output=True,
        text=True,
        env={"PATH": bare},
    ).stdout.splitlines()
    assert both[0].startswith("Installing into ") and "python3 is not on PATH" in both[1], both


def test_shared_skill_folder_is_copied_once_and_gitignore_written_once():
    repo = scratch_repo()
    proc = subprocess.run(
        [
            "strace",
            "-f",
            "-e",
            "trace=openat",
            "-o",
            "/dev/stdout",
            INSTALL,
            "--target",
            "all",
            "--repo",
            repo,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or "openat" not in proc.stdout:
        import pytest

        pytest.skip("strace unavailable")
    writes = [line for line in proc.stdout.splitlines() if "O_WRONLY" in line or "O_RDWR" in line]
    assert sum(".agents/skills/tpm/SKILL.md" in w for w in writes) == 1
    assert sum(".agents/skills/tpm/scripts/runtime.py" in w for w in writes) == 1
    assert sum("/.gitignore" in w for w in writes) == 1


def test_nothing_detected_fails_with_one_line():
    repo = _with_markers(".agents/", ".github/workflows/", "AGENTS.md")  # none says which editor
    before = snapshot(repo)
    proc = cli([], repo)
    assert proc.returncode == 2 and proc.stdout == ""
    assert proc.stderr == (
        f"cadence-orchestrator: no editor config found in {repo} and no supported agent detected; "
        "choose one with --target <antigravity|claude|codex|copilot|cursor|gemini|all>\n"
    )
    assert snapshot(repo) == before


def test_target_overrides_detection():
    repo = _with_markers(".cursor/")
    proc = cli(["--target", "gemini"], repo)
    assert proc.returncode == 0 and proc.stdout.startswith(f"Installing into {repo}\ngemini: ")
    assert not os.path.exists(os.path.join(repo, ".cursor/hooks.json"))


def test_permission_error_is_one_line_naming_the_path():
    if os.geteuid() == 0:
        import pytest

        pytest.skip("root ignores file permissions")
    repo = os.path.realpath(scratch_repo())
    os.chmod(repo, 0o555)
    try:
        proc = cli(["--target", "codex"], repo)
    finally:
        os.chmod(repo, 0o755)
    assert proc.returncode == 1
    lines = proc.stderr.splitlines()
    assert len(lines) == 1 and "Node.js" not in proc.stderr and "    at " not in proc.stderr, proc.stderr
    assert lines[0].startswith("cadence-orchestrator: permission denied (EACCES) on " + repo)
    assert lines[0].endswith("If an agent ran this, its sandbox may need to allow writes to the repo.")


def test_invalid_hook_json_names_the_file_and_debug_keeps_the_stack():
    repo = _with_markers(".claude/", ".cursor/")
    open(os.path.join(repo, ".claude/settings.json"), "w").write("{\n  // mine\n}\n")
    before = snapshot(repo)
    proc = cli([], repo)  # cursor would be fine, but nothing is written for either
    assert proc.returncode == 1 and len(proc.stderr.splitlines()) == 1 and proc.stdout == "", proc.stderr
    assert proc.stderr.startswith("cadence-orchestrator: .claude/settings.json isn't valid JSON (")
    assert proc.stderr.endswith("); fix it and run again. Nothing was changed.\n")
    assert snapshot(repo) == before
    assert open(os.path.join(repo, ".claude/settings.json")).read() == "{\n  // mine\n}\n"
    readme = open(os.path.join(ROOT, "README.md")).read()
    assert (
        "cadence-orchestrator: .claude/settings.json isn't valid JSON (" in readme
    )  # troubleshooting sample


def test_debug_prints_the_full_stack():
    repo = _with_markers(".cursor/")
    os.makedirs(
        os.path.join(repo, ".agents/skills/tpm/SKILL.md")
    )  # a folder where a file goes: an unexpected error
    quiet = cli([], repo)
    assert quiet.returncode == 1 and len(quiet.stderr.splitlines()) == 1, quiet.stderr
    loud = cli([], repo, DEBUG="1")
    assert (
        loud.returncode == 1
        and "    at " in loud.stderr
        and loud.stderr.splitlines()[-1] == quiet.stderr.strip()
    )


def test_instructions_only_target_never_hides_a_broken_guard():
    repo = scratch_repo()
    install(repo, "cursor")
    install(repo, "antigravity")
    os.remove(os.path.join(repo, ".cursor/hooks.json"))
    os.remove(os.path.join(repo, ".agents/skills/tpm/scripts/shim_cursor.py"))
    st = cli(["status"], repo)
    assert st.returncode == 1, st.stdout
    assert "cursor: hook config and shim missing (found .cursor/rules/tpm.mdc)" in st.stdout
    assert "antigravity: instructions only" in st.stdout
    for target, remove in (("codex", [".codex/hooks.json"]), ("claude", [".claude/settings.json"])):
        repo = scratch_repo()
        install(repo, target)
        install(repo, "antigravity")
        skill = ".claude/skills/tpm" if target == "claude" else ".agents/skills/tpm"
        for rel in remove + [f"{skill}/scripts/shim_{target}.py"]:
            os.remove(os.path.join(repo, rel))
        st = cli(["status"], repo)
        assert st.returncode == 1 and f"{target}: hook config and shim missing" in st.stdout, (
            target,
            st.stdout,
        )


def test_cursor_session_start_puts_the_chat_id_in_context():
    repo = scratch_repo()
    install(repo, "cursor")
    hooks = json.load(open(os.path.join(repo, ".cursor/hooks.json")))["hooks"]
    assert "shim_cursor.py" in hooks["sessionStart"][0]["command"]
    shim_path = os.path.join(repo, ".agents/skills/tpm/scripts/shim_cursor.py")
    state = tempfile.mkdtemp()
    start = {"hook_event_name": "sessionStart", "session_id": "chat-7", "conversation_id": "chat-7"}
    out = run(shim_path, dict(start, workspace_roots=[repo]), state)
    assert out.returncode == 0, out.stderr
    context = json.loads(out.stdout)["additional_context"]
    assert context.startswith("tpm: this Cursor chat's id is chat-7.") and '"session chat-7"' in context
    # The id it gives is the one `status` lists once /tpm arms that chat.
    arm = {"hook_event_name": "beforeSubmitPrompt", "conversation_id": "chat-7", "prompt": "/tpm go"}
    assert run(shim_path, dict(arm, workspace_roots=[repo]), state).returncode == 0
    st = cli(["status", "--state-dir", state], repo)
    assert "session chat-7: armed" in st.stdout, st.stdout
    # Without python3 the fallback is still valid JSON.
    bare = tempfile.mkdtemp()
    for tool in ("bash",):
        os.symlink(
            subprocess.run(
                ["bash", "-c", f"command -v {tool}"], capture_output=True, text=True
            ).stdout.strip(),
            os.path.join(bare, tool),
        )
    cmd = hooks["sessionStart"][0]["command"]
    fb = subprocess.run(
        ["/bin/bash", "-c", cmd], input="{}", capture_output=True, text=True, cwd=repo, env={"PATH": bare}
    )
    assert fb.returncode == 0 and json.loads(fb.stdout) == {}


def test_skill_matches_the_cursor_chat_and_keeps_the_advisory_wording():
    text = open(os.path.join(ROOT, "skills/tpm/SKILL.md")).read().replace("\n", " ")
    assert "tpm: this Cursor chat's id is <id>" in text
    assert "guard armed for this chat (advisory on Cursor: warns, doesn't block)" in text
    assert "not armed in this chat" in text
    assert "can't confirm this chat" in text  # the fallback when the id line is missing


def test_npm_install_never_runs_scripts():
    pkg = json.load(open(os.path.join(ROOT, "package.json")))
    lifecycle = {"preinstall", "install", "postinstall", "prepare", "prepublish", "preprepare", "postprepare"}
    assert not lifecycle & set(pkg.get("scripts", {}))


def test_antigravity_is_instructions_only_with_its_own_marker():
    repo = _with_markers(".agents/rules/")
    proc = cli([], repo)
    assert proc.returncode == 0, proc.stderr
    assert (
        "antigravity: .agents/skills/tpm/, .agents/rules/tpm.md (instructions only, no guard)" in proc.stdout
    )
    rule = open(os.path.join(repo, ".agents/rules/tpm.md")).read()
    assert (
        rule.startswith("---\ntrigger: manual\n---\n")
        and "instructions only: no guard hooks on Antigravity" in rule
    )
    assert not os.path.exists(os.path.join(repo, ".agents/hooks.json"))
    assert not [
        n for n in os.listdir(os.path.join(repo, ".agents/skills/tpm/scripts")) if n.startswith("shim_")
    ]
    doc = cli(["doctor", "--target", "antigravity"], repo)
    assert doc.returncode == 0 and "FAIL" not in doc.stdout, doc.stdout
    assert "skip antigravity: instructions only: no guard hooks on this platform" in doc.stdout
    st = cli(["status"], repo)
    assert st.returncode == 0, st.stdout
    assert "antigravity: instructions only, no guard hooks on this platform; skill found" in st.stdout
    assert "No live hook activity" not in st.stdout
    alldoc = cli(["doctor", "--target", "all"], repo)
    assert alldoc.returncode == 0 and "FAIL" not in alldoc.stdout, alldoc.stdout


def test_shared_skill_folder_does_not_make_antigravity_installed():
    repo = scratch_repo()
    install(repo, "cursor")
    st = cli(["status"], repo)
    assert "antigravity: not installed" in st.stdout, st.stdout
    doc = cli(["doctor", "--target", "all"], repo)
    assert "skip antigravity: not installed" in doc.stdout, doc.stdout


def test_status_uses_per_target_markers_and_notes_an_unowned_skill_folder():
    repo = scratch_repo()
    install(repo, "cursor")
    os.remove(os.path.join(repo, ".cursor/hooks.json"))
    os.remove(os.path.join(repo, ".agents/skills/tpm/scripts/shim_cursor.py"))
    st = cli(["status"], repo)
    assert st.returncode == 1, st.stdout
    assert (
        "cursor: hook config and shim missing (found .cursor/rules/tpm.mdc); "
        "reinstall with `npx cadence-orchestrator --target cursor`" in st.stdout
    )
    assert "note: .agents/skills/tpm/ has a tpm skill, but no target here is installed with it" in st.stdout
    assert "<name>" not in st.stdout
    repo = scratch_repo()
    install(repo, "claude")
    os.remove(os.path.join(repo, ".claude/settings.json"))
    st = cli(["status"], repo)
    assert st.returncode == 1, st.stdout
    assert (
        "claude: incomplete install; reinstall with `npx cadence-orchestrator --target claude`" in st.stdout
    )
    # An instructions-only target is installed by its marker alone; no shim is looked for.
    repo = scratch_repo()
    install(repo, "antigravity")
    st = cli(["status"], repo)
    assert st.returncode == 0 and "antigravity: instructions only" in st.stdout and "note:" not in st.stdout


def test_bare_repo_before_any_double_dash_argument_keeps_typos_visible():
    repo, sub = _repo_with_subfolder()
    proc = cli(["--repo", "--tagret", "claude"], sub)
    assert proc.returncode == 2 and proc.stderr.startswith(
        "cadence-orchestrator: unknown argument --tagret"
    ), proc.stderr
    assert "FLAGS" not in open(INSTALL).read()


# ---------------------------------------------------------------- uninstall, dry run, check, JSON, version


def _user_content(repo):
    """A repo with the user's own hooks, AGENTS.md text and .gitignore lines, before any install."""
    os.makedirs(os.path.join(repo, ".claude"))
    mine = {
        "permissions": {"allow": ["Bash(npm test)"]},
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "./mine.sh"}]}]
        },
    }
    json.dump(mine, open(os.path.join(repo, ".claude/settings.json"), "w"))
    open(os.path.join(repo, "AGENTS.md"), "w").write("# Rules\n\nBe nice.\n")
    open(os.path.join(repo, ".gitignore"), "w").write("node_modules/\n")
    os.makedirs(os.path.join(repo, ".cursor"))
    open(os.path.join(repo, ".cursor/mcp.json"), "w").write("{}\n")
    return mine


def test_uninstall_removes_only_what_the_installer_added_and_is_safe_to_rerun():
    repo = os.path.realpath(scratch_repo())
    mine = _user_content(repo)
    before = snapshot(repo)
    for t in ("claude", "codex", "cursor", "gemini", "copilot", "antigravity"):
        install(repo, t)
    out = cli(["uninstall"], repo)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith(f"Removing from {repo}:\n")
    for line in (
        "  .claude/settings.json (hook entries)",
        "  AGENTS.md (tpm block)",
        "  .cursor/hooks.json (hook entries)",
        "  .agents/skills/tpm/ (the files its install manifest records)",
        "  .claude/skills/tpm/ (the files its install manifest records)",
        "  .gitignore (tpm off-switch lines)",
    ):
        assert line in out.stdout.splitlines(), (line, out.stdout)
    after = snapshot(repo)
    assert after.keys() == before.keys()
    assert {k: v for k, v in after.items() if k != ".claude/settings.json"} == {
        k: v for k, v in before.items() if k != ".claude/settings.json"
    }
    assert (
        json.load(open(os.path.join(repo, ".claude/settings.json"))) == mine
    )  # same value; JSON is re-indented
    for gone in (
        ".agents/skills/tpm",
        ".claude/skills/tpm",
        ".codex",
        ".gemini",
        "GEMINI.md",
        ".cursor/hooks.json",
    ):
        assert not os.path.exists(os.path.join(repo, gone)), gone
    # Skills and hooks folders stay even though the installer created them; .claude and .cursor existed before.
    for kept in (".agents/skills", ".claude/skills", ".github/skills", ".github/hooks", ".claude", ".cursor"):
        assert os.path.isdir(os.path.join(repo, kept)), kept
    again = cli(["uninstall"], repo)
    assert again.returncode == 0 and again.stdout == f"Nothing to remove in {repo}.\n"


def test_uninstall_one_target_keeps_a_shared_skill_folder_and_dry_run_changes_nothing():
    repo = scratch_repo()
    install(repo, "cursor")
    install(repo, "codex")
    snap = snapshot(repo)
    dry = cli(["uninstall", "--target", "cursor", "--dry-run"], repo)
    assert dry.returncode == 0 and "Dry run: nothing was changed." in dry.stdout and snapshot(repo) == snap
    out = cli(["uninstall", "--target", "cursor"], repo)
    assert out.returncode == 0, out.stderr
    assert os.path.exists(os.path.join(repo, ".agents/skills/tpm/SKILL.md"))  # codex still uses it
    assert os.path.exists(os.path.join(repo, ".agents/skills/tpm/scripts/shim_codex.py"))
    assert not os.path.exists(os.path.join(repo, ".agents/skills/tpm/scripts/shim_cursor.py"))
    assert ".cadence/tpm.off" in open(os.path.join(repo, ".gitignore")).read()
    assert cli(["status"], repo).stdout.count("cursor: not installed") == 1


def test_validation_happens_before_any_write():
    repo = _with_markers(".cursor/", ".gemini/")
    open(os.path.join(repo, ".gemini/settings.json"), "w").write("{,}")
    before = snapshot(repo)
    proc = cli([], repo)
    assert proc.returncode == 1 and ".gemini/settings.json isn't valid JSON" in proc.stderr
    assert snapshot(repo) == before and not os.path.exists(os.path.join(repo, ".agents"))
    readme = open(os.path.join(ROOT, "README.md")).read()
    assert "The skill files were copied but no hooks were added" not in readme
    assert "Every file the run would touch is checked before anything is written" in readme


def test_unmatched_block_marker_is_an_error_naming_the_file():
    repo = _with_markers(".codex/")
    open(os.path.join(repo, "AGENTS.md"), "w").write(
        "# Rules\n\n<!-- cadence-orchestrator:tpm begin -->\nold\n"
    )
    before = snapshot(repo)
    proc = cli([], repo)
    assert proc.returncode == 1 and proc.stderr.startswith(
        "cadence-orchestrator: AGENTS.md has a cadence-orchestrator begin marker without a matching end marker"
    ), proc.stderr
    assert snapshot(repo) == before
    open(os.path.join(repo, "AGENTS.md"), "w").write("x\n<!-- cadence-orchestrator:tpm end -->\n")
    assert cli([], repo).returncode == 1


def test_dry_run_lists_changes_and_writes_nothing():
    repo = _with_markers(".cursor/")
    before = snapshot(repo)
    dry = cli(["--dry-run"], repo)
    assert dry.returncode == 0 and snapshot(repo) == before, dry.stderr
    lines = dry.stdout.splitlines()
    assert "would create .cursor/hooks.json" in lines and "would create .agents/skills/tpm/SKILL.md" in lines
    assert lines[-1].startswith(f"Dry run for cursor in {repo}: ") and lines[-1].endswith(
        "nothing was written."
    )
    cli([], repo)
    again = cli(["--dry-run"], repo)
    assert (
        again.stdout.splitlines()[-1]
        == f"Dry run for cursor in {repo}: 0 file(s) would change; nothing was written."
    )


def test_check_exits_1_when_installed_files_differ():
    repo = scratch_repo()
    assert cli(["--check"], repo).returncode == 1  # nothing installed
    install(repo, "cursor")
    ok = cli(["--check"], repo)
    assert ok.returncode == 0 and ok.stdout.startswith("Up to date with "), ok.stdout
    open(os.path.join(repo, ".agents/skills/tpm/SKILL.md"), "a").write("\nlocal edit\n")
    os.remove(os.path.join(repo, ".cursor/rules/tpm.mdc"))
    bad = cli(["--check"], repo)
    assert bad.returncode == 1
    assert (
        "differs: .agents/skills/tpm/SKILL.md" in bad.stdout
        and "differs: .cursor/rules/tpm.mdc" in bad.stdout
    )
    before = snapshot(repo)
    assert snapshot(repo) == before  # --check writes nothing
    # A reformatted but equal hook file isn't drift.
    path = os.path.join(repo, ".cursor/hooks.json")
    json.dump(json.load(open(path)), open(path, "w"))
    install(repo, "cursor")
    json.dump(json.load(open(path)), open(path, "w"))
    assert cli(["--check"], repo).returncode == 0


def test_status_and_doctor_json():
    repo = scratch_repo()
    install(repo, "cursor")
    st = cli(["status", "--json"], repo)
    data = json.loads(st.stdout)
    assert data["ok"] is False and data["repo"] and data["version"]
    cursor = next(t for t in data["targets"] if t["target"] == "cursor")
    assert cursor["installed"] and cursor["guard"] and cursor["complete"] and cursor["sessions"] == []
    assert isinstance(data["lines"], list)
    doc = cli(["doctor", "--target", "cursor", "--json"], repo)
    d = json.loads(doc.stdout)
    assert (
        doc.returncode == 0
        and d["ok"]
        and d["failed"] == 0
        and all({"name", "ok", "skip", "detail"} <= set(c) for c in d["checks"])
    )


def test_status_reports_the_installed_version():
    repo = scratch_repo()
    install(repo, "cursor")
    version = json.load(open(os.path.join(ROOT, "package.json")))["version"]
    data = json.loads(cli(["status", "--json"], repo).stdout)
    assert next(t for t in data["targets"] if t["target"] == "cursor")["version"] == version
    manifest = os.path.join(repo, ".agents/skills/tpm/.cadence-install.json")
    m = json.load(open(manifest))
    m["version"] = "0.1.4"
    json.dump(m, open(manifest, "w"))
    st = cli(["status"], repo)
    assert (
        f"cursor: installed 0.1.4, this is {version}; reinstall with `npx cadence-orchestrator --target cursor` to update"
        in st.stdout
    )


def _backups(repo):
    root = os.path.join(repo, ".cadence/backups")
    found = []
    for base, _, names in os.walk(root):
        found += [os.path.relpath(os.path.join(base, n), root) for n in names]
    return sorted(found)


def test_hand_edited_skill_files_are_backed_up_before_overwrite():
    repo = scratch_repo()
    install(repo, "cursor")
    skill = os.path.join(repo, ".agents/skills/tpm/SKILL.md")
    open(skill, "a").write("\nmy note\n")
    out = install(repo, "cursor")
    line = next(
        ln
        for ln in out.splitlines()
        if ln.startswith("backed up hand-edited .agents/skills/tpm/SKILL.md to ")
    )
    dest = line.split(" to ", 1)[1]
    assert re.fullmatch(r"\.cadence/backups/\d{8}T\d{6}Z/\.agents/skills/tpm/SKILL\.md", dest), dest
    assert open(os.path.join(repo, dest)).read().endswith("my note\n")
    assert not open(skill).read().endswith("my note\n")
    assert "backed up" not in install(repo, "cursor")  # unchanged files aren't backed up


def test_doctor_and_status_report_a_missing_cursor_session_start():
    repo = scratch_repo()
    install(repo, "cursor")
    path = os.path.join(repo, ".cursor/hooks.json")
    cfg = json.load(open(path))
    del cfg["hooks"]["sessionStart"]
    json.dump(cfg, open(path, "w"))
    st = cli(["status"], repo)
    assert st.returncode == 1 and "missing sessionStart" in st.stdout, st.stdout
    doc = cli(["doctor", "--target", "cursor"], repo)
    assert doc.returncode == 1 and "FAIL cursor: sessionStart hook points at" in doc.stdout, doc.stdout
    install(repo, "cursor")
    assert (
        "ok   cursor: sessionStart puts the chat id in context"
        in cli(["doctor", "--target", "cursor"], repo).stdout
    )


def test_cursor_shim_recognises_session_start_without_hook_event_name():
    repo = scratch_repo()
    install(repo, "cursor")
    shim_path = os.path.join(repo, ".agents/skills/tpm/scripts/shim_cursor.py")
    out = run(
        shim_path,
        {"session_id": "c9", "is_background_agent": False, "composer_mode": "agent"},
        tempfile.mkdtemp(),
    )
    assert json.loads(out.stdout)["additional_context"].startswith("tpm: this Cursor chat's id is c9.")
    prompt = run(shim_path, {"conversation_id": "c9", "prompt": "hi"}, tempfile.mkdtemp())
    assert json.loads(prompt.stdout) == {"continue": True}


def test_python3_outside_the_default_path_gets_a_note():
    repo = scratch_repo()
    install(repo, "cursor")
    node = subprocess.run(["bash", "-c", "command -v node"], capture_output=True, text=True).stdout.strip()
    py = subprocess.run(["bash", "-c", "command -v python3"], capture_output=True, text=True).stdout.strip()
    bare = tempfile.mkdtemp()
    for name, target in (
        ("node", node),
        ("python3", py),
        ("git", shutil.which("git")),
        ("bash", shutil.which("bash")),
    ):
        os.symlink(target, os.path.join(bare, name))
    env = {"PATH": bare, "HOME": os.environ.get("HOME", "/")}
    has_default = (
        subprocess.run(
            ["/bin/sh", "-c", "command -v python3"],
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            capture_output=True,
        ).returncode
        == 0
    )
    st = subprocess.run(
        [os.path.join(bare, "node"), INSTALL, "status", "--repo", repo],
        capture_output=True,
        text=True,
        env=env,
    )
    doc = subprocess.run(
        [os.path.join(bare, "node"), INSTALL, "doctor", "--target", "cursor", "--repo", repo],
        capture_output=True,
        text=True,
        env=env,
    )
    note = "not on the default PATH (/usr/bin:/bin:/usr/sbin:/sbin)"
    assert (note in st.stdout) == (not has_default) and (note in doc.stdout) == (not has_default), st.stdout
    # The committed hook command is unchanged: it still looks python3 up on PATH.
    assert "command -v python3" in open(os.path.join(repo, ".cursor/hooks.json")).read()


# ------------------------------------------------------------------- uninstall folders, manifests, backups


def _two_versions(tmp_name):
    """Copies of this package, the second with one upstream reference file changed."""
    root = tempfile.mkdtemp()
    out = []
    for name in ("a", "b"):
        dest = os.path.join(root, name)
        os.makedirs(dest)
        for part in ("bin", "skills", "adapters", "package.json"):
            src = os.path.join(ROOT, part)
            (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(dest, part))
        out.append(os.path.join(dest, "bin", "cadence-orchestrator.mjs"))
    open(os.path.join(root, "b", "skills/tpm/references/catalogs.md"), "a").write("\nupstream change\n")
    return out


def test_upgrade_does_not_back_up_files_nobody_edited():
    old, new = _two_versions("up")
    repo = scratch_repo()
    subprocess.run(
        [old, "--target", "claude", "--repo", repo], check=True, capture_output=True, env=clean_env()
    )
    out = subprocess.run(
        [new, "--target", "claude", "--repo", repo], capture_output=True, text=True, env=clean_env()
    )
    assert out.returncode == 0 and "backed up" not in out.stdout, out.stdout
    assert (
        open(os.path.join(repo, ".claude/skills/tpm/references/catalogs.md"))
        .read()
        .endswith("upstream change\n")
    )
    manifest = json.load(open(os.path.join(repo, ".claude/skills/tpm/.cadence-install.json")))
    text = open(os.path.join(repo, ".claude/skills/tpm/references/catalogs.md"), "rb").read()
    import hashlib

    assert (
        manifest["files"]["references/catalogs.md"] == hashlib.sha256(text).hexdigest()
    )  # written last, new hashes


def test_uninstall_backs_up_hand_edited_files_before_deleting_them():
    repo = scratch_repo()
    install(repo, "claude")
    open(os.path.join(repo, ".claude/skills/tpm/SKILL.md"), "a").write("\nmy edit\n")
    out = cli(["uninstall"], repo)
    assert out.returncode == 0
    assert (
        "backed up hand-edited .claude/skills/tpm/SKILL.md to .cadence/backups/" in out.stdout
        and "before removing it" in out.stdout
    )
    (backup,) = _backups(repo)
    assert backup.endswith("/.claude/skills/tpm/SKILL.md")
    assert open(os.path.join(repo, ".cadence/backups", backup)).read().endswith("my edit\n")
    assert not os.path.exists(os.path.join(repo, ".claude/skills/tpm"))


def test_backups_never_overwrite_an_earlier_backup():
    repo = scratch_repo()
    install(repo, "cursor")
    skill = os.path.join(repo, ".agents/skills/tpm/SKILL.md")
    open(skill, "a").write("\nfirst\n")
    install(repo, "cursor")
    import time

    time.sleep(1.1)  # backups are grouped per run, by second
    open(skill, "a").write("\nsecond\n")
    install(repo, "cursor")
    found = _backups(repo)
    assert len(found) == 2, found
    texts = [open(os.path.join(repo, ".cadence/backups", f)).read() for f in found]
    assert texts[0].endswith("first\n") and texts[1].endswith("second\n")


def test_uninstall_removes_only_empty_folders_the_installer_created():
    repo = scratch_repo()
    os.makedirs(os.path.join(repo, ".cursor"))  # the user's empty folder
    install(repo, "cursor")
    manifest = json.load(open(os.path.join(repo, ".agents/skills/tpm/.cadence-install.json")))
    assert ".cursor" not in manifest["created_dirs"] and ".cursor/rules" in manifest["created_dirs"]
    assert ".agents/skills/tpm" in manifest["created_dirs"]
    open(os.path.join(repo, ".cursor/rules/mine.mdc"), "w").write(
        "mine\n"
    )  # user file in a folder we created
    out = cli(["uninstall"], repo)
    assert out.returncode == 0, out.stderr
    assert os.path.isdir(os.path.join(repo, ".cursor"))  # existed before the install
    assert os.path.exists(os.path.join(repo, ".cursor/rules/mine.mdc"))  # created by us, but not empty
    assert os.path.isdir(os.path.join(repo, ".agents/skills"))  # never removed
    assert not os.path.exists(os.path.join(repo, ".agents/skills/tpm"))


def test_uninstall_never_removes_skills_or_hooks_folders():
    repo = scratch_repo()
    install(repo, "copilot")
    install(repo, "claude")
    cli(["uninstall"], repo)
    for kept in (".github/skills", ".github/hooks", ".claude/skills"):
        assert os.path.isdir(os.path.join(repo, kept)) and not os.listdir(os.path.join(repo, kept)), kept


def test_uninstall_of_an_old_install_removes_files_but_no_folders():
    repo = scratch_repo()
    install(repo, "cursor")
    os.remove(
        os.path.join(repo, ".agents/skills/tpm/.cadence-install.json")
    )  # as an install from 0.1.6 would be
    out = cli(["uninstall"], repo)
    assert out.returncode == 0 and "  .agents/skills/tpm/ (this version's skill files)" in out.stdout, (
        out.stdout
    )
    assert "Removed empty folders" not in out.stdout
    assert os.path.isdir(os.path.join(repo, ".agents/skills/tpm/references"))
    assert not os.path.exists(os.path.join(repo, ".agents/skills/tpm/SKILL.md"))
    assert not os.path.exists(os.path.join(repo, ".cursor/rules/tpm.mdc")) and os.path.isdir(
        os.path.join(repo, ".cursor/rules")
    )


def test_uninstall_removes_what_the_manifest_records_and_bytecode_caches():
    repo = scratch_repo()
    install(repo, "cursor")
    path = os.path.join(repo, ".agents/skills/tpm/.cadence-install.json")
    manifest = json.load(open(path))
    manifest["files"]["references/old-name.md"] = "0" * 64  # a file an older version installed
    json.dump(manifest, open(path, "w"))
    open(os.path.join(repo, ".agents/skills/tpm/references/old-name.md"), "w").write("old\n")
    os.makedirs(os.path.join(repo, ".agents/skills/tpm/scripts/__pycache__"))
    open(os.path.join(repo, ".agents/skills/tpm/scripts/__pycache__/runtime.cpython-313.pyc"), "w").write("x")
    out = cli(["uninstall"], repo)
    assert out.returncode == 0, out.stderr
    assert not os.path.exists(os.path.join(repo, ".agents/skills/tpm")), out.stdout


def test_uninstall_touches_only_the_lines_around_the_block():
    repo = scratch_repo()
    mine = "# Rules\n\n```\na\n\n\n\nb\n```\n\nTail.\n"
    open(os.path.join(repo, "AGENTS.md"), "w").write(mine)
    install(repo, "codex")
    cli(["uninstall"], repo)
    assert open(os.path.join(repo, "AGENTS.md")).read() == mine
    # A block in the middle: the text on both sides is kept as it was.
    text = (
        open(os.path.join(ROOT, "adapters/codex/AGENTS.pointer.md"))
        .read()
        .replace("__SKILL__", ".agents/skills/tpm")
    )
    open(os.path.join(repo, "AGENTS.md"), "w").write("Top\n\n\n\nkeep\n\n" + text + "\nBottom\n")
    install(repo, "codex")
    cli(["uninstall"], repo)
    assert open(os.path.join(repo, "AGENTS.md")).read() == "Top\n\n\n\nkeep\n\nBottom\n"


def test_hook_event_that_is_not_a_list_is_a_one_line_error():
    for argv in ([], ["uninstall"]):
        repo = _with_markers(".claude/")
        if argv:
            install(repo, "claude")
        cfg = {"hooks": {"Stop": {"command": "x"}}}
        json.dump(cfg, open(os.path.join(repo, ".claude/settings.json"), "w"))
        before = snapshot(repo)
        out = cli(argv, repo)
        assert out.returncode == 1 and out.stderr == (
            "cadence-orchestrator: .claude/settings.json isn't valid hook config (hooks.Stop should be a list); "
            "fix it and run again. Nothing was changed.\n"
        ), (argv, out.stderr)
        assert snapshot(repo) == before


def test_cursor_tool_payload_without_event_name_is_never_session_start():
    repo = scratch_repo()
    install(repo, "cursor")
    shim_path = os.path.join(repo, ".agents/skills/tpm/scripts/shim_cursor.py")
    state = tempfile.mkdtemp()
    arm = {"hook_event_name": "beforeSubmitPrompt", "conversation_id": "c1", "prompt": "/tpm go"}
    run(shim_path, dict(arm, workspace_roots=[repo]), state)
    tool = {
        "conversation_id": "c1",
        "session_id": "c1",
        "is_background_agent": False,
        "tool_name": "Write",
        "tool_input": {"path": "x.txt"},
        "workspace_roots": [repo],
    }
    out = run(shim_path, tool, state)
    assert "additional_context" not in out.stdout
    assert json.loads(out.stdout) == {"permission": "allow"} and "tpm advisory" in out.stderr  # the guard ran


def test_path_note_is_computed_once_per_run():
    src = open(os.path.join(ROOT, "bin/doctor.mjs")).read()
    assert "pathNote ??= probePath()" in src
    body = src[src.index("export function doctor(") :]
    assert "guiPathNote()" not in body  # not per target


def _package_copy(extra=None):
    dest = tempfile.mkdtemp()
    for part in ("bin", "skills", "adapters", "package.json"):
        src = os.path.join(ROOT, part)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(dest, part))
    for rel, text in (extra or {}).items():
        open(os.path.join(dest, rel), "w").write(text)
    return os.path.join(dest, "bin", "cadence-orchestrator.mjs")


def test_upgrade_removes_files_the_new_version_no_longer_installs():
    old = _package_copy(
        {"skills/tpm/references/legacy.md": "legacy\n", "skills/tpm/references/gone.md": "gone\n"}
    )
    repo = scratch_repo()
    subprocess.run(
        [old, "--target", "cursor", "--repo", repo], check=True, capture_output=True, env=clean_env()
    )
    open(os.path.join(repo, ".agents/skills/tpm/references/gone.md"), "a").write("my edit\n")
    out = cli(["--target", "cursor"], repo)
    assert "removed .agents/skills/tpm/references/legacy.md (no longer part of tpm " in out.stdout, out.stdout
    assert "backed up hand-edited .agents/skills/tpm/references/gone.md to .cadence/backups/" in out.stdout
    assert "before removing it" in out.stdout
    skill = os.path.join(repo, ".agents/skills/tpm")
    manifest = json.load(open(os.path.join(skill, ".cadence-install.json")))
    on_disk = sorted(
        os.path.relpath(os.path.join(b, n), skill)
        for b, _, ns in os.walk(skill)
        for n in ns
        if n != ".cadence-install.json"
    )
    assert sorted(manifest["files"]) == on_disk  # the manifest matches what's on disk
    cli(["uninstall"], repo)
    assert not os.path.exists(skill)


def test_pycache_cleanup_touches_only_tpm_bytecode_in_tpm_folder():
    repo = scratch_repo()
    install(repo, "cursor")
    other = os.path.join(repo, ".agents/skills/other/scripts/__pycache__")
    os.makedirs(other)
    open(os.path.join(other, "runtime.cpython-313.pyc"), "w").write("theirs")  # same stem, another skill
    ours = os.path.join(repo, ".agents/skills/tpm/scripts/__pycache__")
    os.makedirs(ours)
    for name in (
        "runtime.cpython-313.pyc",
        "guard.cpython-313.pyc",
        "shim_cursor.cpython-313.pyc",
        "helper.cpython-313.pyc",
    ):
        open(os.path.join(ours, name), "w").write("x")
    install(repo, "cursor")  # reinstall cleans tpm's own bytecode only
    assert sorted(os.listdir(ours)) == ["helper.cpython-313.pyc"]
    assert os.listdir(other) == ["runtime.cpython-313.pyc"]
    cli(["uninstall"], repo)
    assert os.listdir(ours) == ["helper.cpython-313.pyc"]  # a foreign .pyc stays, so the folder stays
    assert os.listdir(other) == ["runtime.cpython-313.pyc"]
    assert os.path.exists(os.path.join(repo, ".agents/skills/other/scripts/__pycache__"))
