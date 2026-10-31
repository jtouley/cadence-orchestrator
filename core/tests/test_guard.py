"""Policy tests, driven through the Claude Code shim (the enforcing reference adapter). Run with `python3 test_guard.py` or `pytest test_guard.py`."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # repo root
GUARD = os.path.join(ROOT, "core", "scripts", "guard.py")
SHIM = os.path.join(ROOT, "adapters", "claude", "shim.py")
SKILL_MD = os.path.join(ROOT, "core", "SKILL.md")
GUARD_DOC = os.path.join(ROOT, "core", "references", "guard.md")
HOOKS_JSON = os.path.join(ROOT, "adapters", "claude", "plugin-hooks.json")
STATE = tempfile.mkdtemp()  # CADENCE_STATE_DIR for every run
ARMED_SESSION = "s-armed"


def load_guard():
    spec = importlib.util.spec_from_file_location("tpm_guard", GUARD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tpm_guard"] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


def frontmatter():
    return open(SKILL_MD).read().split("\n---\n", 1)[0]


def guard_proc(raw, project_dir=None, state=STATE):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = project_dir or tempfile.mkdtemp()
    env["CADENCE_STATE_DIR"] = state
    raw = raw if isinstance(raw, str) else json.dumps(raw)
    return subprocess.run([sys.executable, SHIM],
                          input=raw, capture_output=True, text=True, env=env)


def arm(session, command_name="cadence-orchestrator:tpm", state=STATE):
    return guard_proc({"hook_event_name": "UserPromptExpansion", "session_id": session,
                       "command_name": command_name}, state=state)


arm(ARMED_SESSION)


def run(payload, project_dir=None):
    if isinstance(payload, dict):
        payload = {"session_id": ARMED_SESSION, **payload}
    proc = guard_proc(payload, project_dir=project_dir)
    return proc.returncode, proc.stderr


def call(tool, agent_id=None, project_dir=None, **tool_input):
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    if agent_id:
        payload["agent_id"] = agent_id
    return run(payload, project_dir)[0]


def bash(command, **kw):
    return call("Bash", command=command, **kw)


ALLOW, DENY = 0, 2


def test_subagent_keeps_full_tools():
    assert call("Edit", agent_id="a1", file_path="x.py") == ALLOW
    assert call("Write", agent_id="a1", file_path="x.py", content="") == ALLOW
    assert bash("rm -rf build && make", agent_id="a1") == ALLOW


def test_subagent_cannot_flip_off_switch():
    assert bash("touch .cadence/tpm.off", agent_id="a1") == DENY
    assert call("Write", agent_id="a1", file_path=".cadence/tpm.off", content="") == DENY
    assert call("Read", agent_id="a1", file_path=".cadence/tpm.off") == ALLOW


def test_main_thread_denies_mutating_tools():
    for tool in ("Edit", "Write", "NotebookEdit", "MultiEdit", "PowerShell", "Monitor",
                 "SomeUnknownTool", "mcp__github__create_pull_request"):
        assert call(tool, file_path="x") == DENY, tool


def test_main_thread_allows_reads_and_delegation():
    for tool in ("Read", "Grep", "Glob", "Agent", "Skill", "TodoWrite", "AskUserQuestion",
                 "mcp__github__get_file_contents", "mcp__claude-code-remote__list_events"):
        assert call(tool) == ALLOW, tool


def test_deny_message_explains_tpm_mode():
    code, err = run({"tool_name": "Edit", "tool_input": {}})
    assert code == DENY
    assert "TPM mode" in err and "subagent" in err and "Only the user" in err


def test_read_only_bash_allowed():
    for cmd in ("git status", "git diff --stat HEAD~1", "git log --oneline -5",
                "git show HEAD:README.md", "git branch", "git branch -a -v",
                "git branch --show-current", "git -C /tmp status", "ls -la src",
                "cat README.md", "head -20 a.py", "tail -n 5 b.log", "wc -l *.py",
                "grep -rn 'def main' src", "rg -n 'a|b' src", "find . -name '*.py'",
                "pwd", "git log | head -20", "ls src && cat README.md",
                "grep -c x f 2>/dev/null", "git diff 2>&1 | tail -5",
                "cd /home/user/x && git status"):
        assert bash(cmd) == ALLOW, cmd


def test_tricky_bash_denied():
    for cmd in ("cat x > y", "cat x >> y", "echo hi > f", "ls && rm -rf z",
                "ls; rm -rf z", "ls || rm z", "git log | sh", "find . -delete",
                "find . -name '*.pyc' -exec rm {} \\;", "find . -fprint out",
                "git commit -m x", "git push", "git checkout main", "git reset --hard",
                "git branch -D feature", "git branch new-feature", "git -c core.pager=sh log",
                "git diff --output=patch.txt", "git diff --ext-diff",
                "sed -i 's/a/b/' f.py", "rm -rf build", "python3 x.py", "touch .cadence/tpm.off",
                "cat $(echo /etc/passwd)", "cat `whoami`", "ls\nrm -rf z",
                "FOO=1 ls", "/bin/ls", "rg --pre sh x", "tee out < in", "(rm x)",
                "cat <<EOF > f\nhi\nEOF", "ls 'unterminated", ""):
        assert bash(cmd) == DENY, repr(cmd)


def test_off_switch():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".cadence"))
    assert call("Edit", project_dir=d, file_path="x") == DENY
    open(os.path.join(d, ".cadence", "tpm.off"), "w").close()
    assert call("Edit", project_dir=d, file_path="x") == ALLOW
    assert bash("rm -rf build", project_dir=d) == ALLOW


def test_malformed_input_fails_open():
    code, err = run("not json{")
    assert code == ALLOW and "allowing" in err
    assert run("[1, 2]")[0] == ALLOW


# Regression tests for the independent review's findings.

def test_hash_is_not_a_comment_escape():
    for cmd in ("ls x#; touch /tmp/pwned", "cat a#b\nrm -rf z", "ls # note", "ls x#\nrm z"):
        assert bash(cmd) == DENY, repr(cmd)
    for cmd in ("cat a#b", "grep -n '#include' f.c", 'grep "#" f'):
        assert bash(cmd) == ALLOW, repr(cmd)


def test_off_switch_match_survives_quoting():
    for cmd in ('touch .cadence/tpm.of""f', "touch .cadence/tpm.of\\f", "touch '.cadence/tpm.'off",
                "touch .cadence/tpm .off"):
        assert bash(cmd, agent_id="a1") == DENY, cmd


def test_rg_options_that_run_programs():
    for cmd in ("rg --hostname-bin=/tmp/x foo", "rg --hostname-bin /tmp/x foo",
                "rg --pre-glob '*.gz' --pre zcat x", "rg --pre=sh x"):
        assert bash(cmd) == DENY, cmd


def test_quoted_operators_and_new_readers_allowed():
    for cmd in ('grep -rn "def main(" src', "grep -n '|' f", "grep -E 'a>b|c<d' f",
                "sort f | uniq -c", "uniq f", "git grep -n foo", "git rev-parse HEAD",
                "cat < f", "sed -n 1,20p f.py", "sed -n '$p' f", "sed -n 5p a b",
                "git log --format='%h (%an)'"):
        assert bash(cmd) == ALLOW, cmd
    for cmd in ("sort -o out f", "sort --output=out f", "sort -ro out f",
                "sort --compress-program=sh f", "uniq in out", "sed -n '1,5w out' f",
                "sed -n 1p -i f", "sed 1,20p f", "sed -n '/x/e rm z' f", "git grep -O vim x",
                "git grep --open-files-in-pager=vim x", "cat <<< x", "cat <(ls)",
                "cat $'\\x3b'", "ls >| f"):
        assert bash(cmd) == DENY, cmd


def test_delegation_tools_allowed_and_documented():
    for tool in ("Workflow", "mcp__claude-code-remote__create_session",
                 "mcp__claude-code-remote__send_message", "mcp__claude-code-remote__send_later",
                 "mcp__claude-code-remote__subscribe_pr_activity",
                 "mcp__claude-code-remote__unsubscribe_pr_activity"):
        assert call(tool) == ALLOW, tool
    assert call("mcp__claude-code-remote__archive_session") == DENY
    section = open(GUARD_DOC).read().split("## Tools", 1)[1].split("Also any MCP tool", 1)[0]
    documented = {n for n in re.findall(r"`([A-Za-z_][\w-]*)`", section)
                  if n[0].isupper() or n.startswith("mcp__")}
    assert documented == load_guard().SAFE_TOOLS, documented ^ load_guard().SAFE_TOOLS


def test_tail_follow_denied():
    for cmd in ("tail -f log", "tail -F log", "tail --follow=name log", "tail -fn 5 log", "tail --fo f", "tail -s 1 f"):
        assert bash(cmd) == DENY, cmd
    assert bash("tail -n 5 log") == ALLOW


def test_abbreviated_and_unlisted_long_options_denied():
    # Reproduced bypasses from the second review: abbreviations of dangerous options.
    for cmd in ("git grep --open=rm a", "git grep --open-files-in-pager=rm a",
                "sort --out=/tmp/pw f", "sort --compress=sh -S 1 f", "tail --fo f",
                "rg --hostname=x a", "rg --pr=sh a", "grep --unknown x f", "ls --zzz",
                "git diff --out=p", "git log --ext=x", "git show --textconv HEAD",
                "git status --unknown", "git rev-parse --git-path x", "find . -newerXY x",
                "head --foo f", "cat --zzz f", "wc --files0-from=f"):
        assert bash(cmd) == DENY, cmd


def test_uniq_counts_dash_as_a_file():
    for cmd in ("cat f | uniq - /tmp/pw", "uniq - out", "uniq -c in out", "uniq -f 2 a b"):
        assert bash(cmd) == DENY, cmd
    for cmd in ("cat f | uniq", "cat f | uniq -", "uniq -c f", "uniq -f 2 f", "sort f | uniq -c"):
        assert bash(cmd) == ALLOW, cmd


def test_common_read_options_still_allowed():
    for cmd in ("ls -la --color=auto src", "grep -rn --include='*.py' -A 3 foo src",
                "grep -C2 -e x f", "rg -n -g '*.py' --hidden foo", "sort -k2,2 -t: -rn f",
                "head -n 20 f", "tail -20 f", "wc -l f", "git log --oneline --graph -n 5",
                "git diff --stat --cached -- src", "git status --short --branch",
                "git grep -n -e foo -- '*.py'", "git rev-parse --abbrev-ref HEAD",
                "find . -maxdepth 2 -type f -name '*.md' -print"):
        assert bash(cmd) == ALLOW, cmd


def test_deny_message_points_to_light_prompts_and_scribe():
    code, err = run({"tool_name": "Write", "tool_input": {"file_path": "workstreams/x.md"}})
    assert code == DENY
    assert "one- or two-line prompt" in err and "orchestration branch" in err and "scribe" in err


def test_main_thread_cannot_write_or_push_orchestration_docs():
    # Design choice: a scribe agent owns the docs; the main thread gets no carve-out.
    assert call("Write", file_path="workstreams/finish-bag.md", content="x") == DENY
    assert call("Edit", file_path="workstreams/finish-bag.md") == DENY
    for cmd in ("git push origin orchestration", "git commit -m status",
                "git fetch origin orchestration", "git switch orchestration"):
        assert bash(cmd) == DENY, cmd
    assert bash("git show origin/orchestration:workstreams/finish-bag.md") == ALLOW
    assert call("mcp__github__get_file_contents") == ALLOW
    # The scribe is a subagent, so it can.
    assert call("Write", agent_id="scribe", file_path="workstreams/finish-bag.md") == ALLOW
    assert bash("git push origin orchestration", agent_id="scribe") == ALLOW


# Plugin packaging and per-session arming.

def test_unarmed_session_allows_everything():
    for tool, inp in (("Write", {"file_path": "x"}), ("Bash", {"command": "rm -rf z"})):
        payload = {"hook_event_name": "PreToolUse", "session_id": "never-armed",
                   "tool_name": tool, "tool_input": inp}
        assert guard_proc(payload).returncode == ALLOW
    assert guard_proc({"tool_name": "Write", "tool_input": {}}).returncode == ALLOW  # no session


def test_arming_is_per_session_and_only_for_tpm():
    state = tempfile.mkdtemp()
    write = lambda s: guard_proc({"session_id": s, "tool_name": "Write", "tool_input": {}},
                                 state=state).returncode
    assert write("a") == ALLOW
    assert arm("a", command_name="cadence-orchestrator:review", state=state).returncode == 0
    assert write("a") == ALLOW
    proc = arm("a", state=state)
    assert proc.returncode == 0 and "armed" in proc.stdout
    assert write("a") == DENY and write("b") == ALLOW
    assert arm("c", command_name="tpm", state=state).returncode == 0 and write("c") == DENY
    # Odd session ids can't escape the state directory.
    arm("../../x", state=state)
    assert os.listdir(os.path.join(state, "tpm-armed")) and not os.path.exists(
        os.path.join(state, "..", "x"))


def test_subagent_cannot_touch_arming_markers():
    assert bash("rm -rf $CLAUDE_PLUGIN_DATA/tpm-armed", agent_id="a1") == DENY


def test_claude_plugin_hooks_point_at_bundled_shim():
    hooks = json.load(open(HOOKS_JSON))["hooks"]
    pre = hooks["PreToolUse"][0]
    arm_h = hooks["UserPromptExpansion"][0]
    assert pre["matcher"] == "*"
    assert re.search(arm_h["matcher"], "cadence-orchestrator:tpm")
    assert re.search(arm_h["matcher"], "tpm")
    assert not re.search(arm_h["matcher"], "cadence-orchestrator:other")
    for group in (pre, arm_h):
        h = group["hooks"][0]
        assert h["command"] == "python3"
        assert h["args"] == ["${CLAUDE_PLUGIN_ROOT}/adapters/claude/shim.py"]
    manifest = json.load(open(os.path.join(ROOT, ".claude-plugin", "plugin.json")))
    assert os.path.normpath(os.path.join(ROOT, manifest["hooks"])) == HOOKS_JSON
    assert os.path.exists(os.path.join(ROOT, manifest["skills"], "SKILL.md"))


def test_shim_crash_fails_open():
    # Arming with a state "dir" that is a regular file raises inside the runtime;
    # the shim must still exit 0 and say so, not block.
    bad_state = tempfile.mkstemp()[1]
    proc = arm("s-crash", state=bad_state)
    assert proc.returncode == ALLOW and "allowing" in proc.stderr


def test_skill_has_no_frontmatter_hooks():
    # Hooks and Claude-only keys live in the adapter layer, not the agent-neutral skill.
    assert "hooks:" not in frontmatter()
    assert "disable-model-invocation" not in frontmatter()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(tests)} passed")
