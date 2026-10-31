"""Tests for `cadence-orchestrator doctor`."""

from __future__ import annotations

import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI = os.path.join(ROOT, "bin", "cadence-orchestrator.mjs")
TARGETS = ("claude", "codex", "copilot", "cursor", "gemini")
SHIMS = {
    "claude": ".claude/skills/tpm/scripts/shim_claude.py",
    "codex": ".agents/skills/tpm/scripts/shim_codex.py",
    "copilot": ".github/skills/tpm/scripts/shim_copilot.py",
    "cursor": ".agents/skills/tpm/scripts/shim_cursor.py",
    "gemini": ".agents/skills/tpm/scripts/shim_gemini.py",
}


def repo_with(*targets):
    repo = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", repo], check=True)
    for t in targets:
        subprocess.run([CLI, "--target", t, "--repo", repo], check=True, capture_output=True)
    return repo


def doctor(repo, target, env=None):
    return subprocess.run(
        [CLI, "doctor", "--target", target, "--repo", repo], capture_output=True, text=True, env=env
    )


def snapshot(repo):
    out = {}
    for base, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, repo)] = open(p, "rb").read()
    return out


def test_doctor_passes_for_each_installed_target_and_changes_nothing():
    for target in TARGETS:
        repo = repo_with(target)
        before = snapshot(repo)
        out = doctor(repo, target)
        assert out.returncode == 0, (target, out.stdout)
        assert "FAIL" not in out.stdout and "checks passed" in out.stdout, target
        assert "arms the session" in out.stdout and "Write" in out.stdout, target
        assert snapshot(repo) == before, target
    claude = doctor(repo_with("claude"), "claude").stdout
    assert "orchestrator Write is denied" in claude and "Stop with no running agents is allowed" in claude
    codex = doctor(repo_with("codex"), "codex").stdout
    assert "simulated $tpm arms" in codex and "advisory is logged" in codex and "skip codex" in codex


def test_doctor_all():
    out = doctor(repo_with("all"), "all")
    assert out.returncode == 0 and all(f"ok   {t}:" in out.stdout for t in TARGETS)


def test_doctor_fails_on_a_missing_shim():
    for target in TARGETS:
        repo = repo_with(target)
        os.remove(os.path.join(repo, SHIMS[target]))
        out = doctor(repo, target)
        assert out.returncode == 1, target
        assert f"FAIL {target}: {SHIMS[target]} exists" in out.stdout, target
        assert (
            "arms the session" in out.stdout
            and "FAIL" in out.stdout.split("arms the session")[0].splitlines()[-1]
        )


def test_doctor_fails_without_python3():
    repo = repo_with("copilot")
    node = subprocess.run(["bash", "-c", "command -v node"], capture_output=True, text=True).stdout.strip()
    bare = tempfile.mkdtemp()
    for tool in ("node", "bash", "git", "dirname"):
        found = subprocess.run(
            ["bash", "-c", f"command -v {tool}"], capture_output=True, text=True
        ).stdout.strip()
        if found:
            os.symlink(found, os.path.join(bare, tool))
    out = subprocess.run(
        [os.path.join(bare, "node"), CLI, "doctor", "--target", "copilot", "--repo", repo],
        capture_output=True,
        text=True,
        env={"PATH": bare},
    )
    assert node and out.returncode == 1 and "FAIL copilot: python3 is on PATH" in out.stdout


def test_doctor_fails_when_not_installed_or_hook_removed():
    out = doctor(repo_with(), "claude")
    assert out.returncode == 1 and "FAIL claude: .claude/skills/tpm/SKILL.md exists" in out.stdout
    repo = repo_with("cursor")
    open(os.path.join(repo, ".cursor/hooks.json"), "w").write('{"version": 1, "hooks": {}}\n')
    out = doctor(repo, "cursor")
    assert out.returncode == 1 and "FAIL cursor: preToolUse hook points at" in out.stdout


def test_doctor_reports_the_real_state_dir_and_checks_it_is_writable():
    repo = repo_with("codex")
    state = tempfile.mkdtemp()
    out = doctor(repo, "codex", env=dict(os.environ, CADENCE_STATE_DIR=state))
    assert out.returncode == 0
    assert f"ok   codex: state dir {state} is writable; advisory log: {state}/advisory.log" in out.stdout
    assert os.listdir(state) == []  # the probe file is removed
    not_a_dir = tempfile.mkstemp()[1]
    out = doctor(repo, "codex", env=dict(os.environ, CADENCE_STATE_DIR=os.path.join(not_a_dir, "sub")))
    assert out.returncode == 1 and "FAIL codex: state dir" in out.stdout and "CADENCE_STATE_DIR" in out.stdout


# ------------------------------------------------------------- PR #4 review fixes

RUNTIMES = {t: s.replace(f"shim_{t}.py", "runtime.py") for t, s in SHIMS.items()}


def test_missing_runtime_fails_the_state_check_and_changes_nothing():
    for target in TARGETS:
        repo = repo_with(target)
        os.remove(os.path.join(repo, RUNTIMES[target]))
        before = snapshot(repo)
        out = doctor(repo, target)
        assert out.returncode == 1, target
        assert (
            f"FAIL {target}: state dir (unresolved)" in out.stdout and "runtime.py is missing" in out.stdout
        ), target
        assert snapshot(repo) == before, target  # e.g. no `{}` directory from Gemini's fallback output


def test_reinstall_removes_old_pycache_only_inside_the_skill_dir():
    repo = repo_with("codex")
    stale = os.path.join(repo, ".agents/skills/tpm/scripts/__pycache__")
    mine = os.path.join(repo, "src/__pycache__")
    for d in (stale, mine):
        os.makedirs(d)
        open(os.path.join(d, "x.cpython-313.pyc"), "wb").write(b"\0")
    subprocess.run([CLI, "--target", "codex", "--repo", repo], check=True, capture_output=True)
    assert not os.path.exists(stale) and os.path.exists(os.path.join(mine, "x.cpython-313.pyc"))


def test_doctor_all_checks_only_installed_targets():
    out = doctor(repo_with("claude", "cursor"), "all")
    assert out.returncode == 0
    for t in ("codex", "copilot", "gemini"):
        assert f"skip {t}: not installed" in out.stdout and f"FAIL {t}" not in out.stdout
    assert "ok   claude:" in out.stdout and "ok   cursor:" in out.stdout
    none = doctor(repo_with(), "all")
    assert none.returncode == 1 and "FAIL no target is installed" in none.stdout


def test_doctor_rejects_catalog():
    repo = repo_with("claude")
    out = subprocess.run(
        [CLI, "doctor", "--target", "claude", "--repo", repo, "--catalog", "x.md"],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 2 and "doctor doesn't take --catalog" in out.stderr


# ------------------------------------------------------------- PR #4 round 2


def _bare_path(tools=("node", "bash", "git", "dirname")):
    bare = tempfile.mkdtemp()
    for tool in tools:
        found = subprocess.run(
            ["bash", "-c", f"command -v {tool}"], capture_output=True, text=True
        ).stdout.strip()
        if found:
            os.symlink(found, os.path.join(bare, tool))
    return bare


def test_resolver_ignores_modules_planted_in_the_temp_dir():
    repo = repo_with("gemini")
    shared = tempfile.mkdtemp()  # stands in for a world-writable /tmp
    marker = os.path.join(tempfile.mkdtemp(), "planted-ran")
    for name in ("json", "tempfile", "types", "dataclasses"):
        open(os.path.join(shared, f"{name}.py"), "w").write(f"open({marker!r}, 'w').close()\n")
    # Sanity: the old invocation (cwd = temp dir, no -I) does pick the planted module up.
    subprocess.run(["python3", "-B", "-c", "import json"], cwd=shared, capture_output=True)
    assert os.path.exists(marker)
    os.remove(marker)
    out = doctor(repo, "gemini", env=dict(os.environ, TMPDIR=shared, TMP=shared, TEMP=shared))
    assert out.returncode == 0, out.stdout
    assert not os.path.exists(marker)


def test_relative_state_dir_resolves_against_the_repo_without_creating_it():
    repo = repo_with("codex")
    before = snapshot(repo)
    out = doctor(repo, "codex", env=dict(os.environ, CADENCE_STATE_DIR=".cadence/state"))
    assert out.returncode == 0, out.stdout
    assert f"state dir {os.path.join(repo, '.cadence/state')} is writable" in out.stdout
    assert snapshot(repo) == before and not os.path.exists(os.path.join(repo, ".cadence"))


def test_unreadable_hook_file_is_a_fail_line_not_a_crash():
    repo = repo_with()
    os.makedirs(os.path.join(repo, ".codex", "hooks.json"))  # a directory where the file should be
    out = doctor(repo, "all")
    assert out.returncode == 1 and "Error" not in out.stderr
    assert "FAIL codex: can't read .codex/hooks.json (EISDIR)" in out.stdout


def test_missing_python3_is_reported_as_python3():
    repo = repo_with("claude")
    bare = _bare_path()
    out = subprocess.run(
        [os.path.join(bare, "node"), CLI, "doctor", "--target", "claude", "--repo", repo],
        capture_output=True,
        text=True,
        env={"PATH": bare},
    )
    assert out.returncode == 1 and "python3 not found" in out.stdout and "couldn't load" not in out.stdout
