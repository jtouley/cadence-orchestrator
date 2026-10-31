"""Tests for tasks_check.py and its use by the guard (no `done` without evidence)."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(ROOT, "core", "scripts")
CHECK = os.path.join(SCRIPTS, "tasks_check.py")
sys.path.insert(0, SCRIPTS)
import tasks_check  # noqa: E402

DONE = {
    "id": "build",
    "owner": "builder-1",
    "doc_sha": "3f2a1c9",
    "state": "done",
    "evidence": ["https://github.com/o/r/pull/57"],
    "left_out": [],
    "left_out_accepted_by": "reviewer-1",
    "tokens": 1200,
}
CLAIMED = {"id": "review", "owner": "reviewer-1", "state": "claimed", "evidence": []}


def doc(*tasks):
    return {"workstream": "w", "tasks": [copy.deepcopy(t) for t in tasks]}


def test_reference_example_is_valid():
    text = open(os.path.join(ROOT, "core", "references", "workstream.md")).read()
    example = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
    assert tasks_check.validate(example) == []


def test_done_needs_evidence_left_out_reviewer_and_doc_sha():
    assert tasks_check.validate(doc(DONE, CLAIMED)) == []
    for key, value, message in (
        ("evidence", [], "done without evidence"),
        ("left_out", None, "left_out list"),
        ("left_out_accepted_by", None, "left_out_accepted_by"),
        ("doc_sha", "", "doc_sha"),
    ):
        task = dict(DONE, **{key: value})
        errors = tasks_check.validate(doc(task))
        assert any(message in e for e in errors), (key, errors)
    missing = {k: v for k, v in DONE.items() if k != "left_out"}
    assert tasks_check.validate(doc(missing))


def test_schema_errors():
    assert tasks_check.validate([])
    assert tasks_check.validate(doc(dict(CLAIMED, state="finished")))
    assert tasks_check.validate(doc(CLAIMED, CLAIMED))  # duplicate id
    assert tasks_check.validate(doc(dict(CLAIMED, id="")))
    assert tasks_check.validate_text("{not json")


def test_cli_exit_codes():
    d = tempfile.mkdtemp()
    good, bad = os.path.join(d, "a.tasks.json"), os.path.join(d, "b.tasks.json")
    json.dump(doc(DONE), open(good, "w"))
    json.dump(doc(dict(DONE, evidence=[])), open(bad, "w"))
    assert subprocess.run([sys.executable, CHECK, good]).returncode == 0
    out = subprocess.run([sys.executable, CHECK, good, bad], capture_output=True, text=True)
    assert out.returncode == 1 and "done without evidence" in out.stderr and "b.tasks.json" in out.stderr


# ------------------------------------------------------------- through the guard


def shim(platform):
    return os.path.join(ROOT, "adapters", platform, "shim.py")


def hook(platform, payload, state, project):
    env = dict(os.environ, CADENCE_STATE_DIR=state, CLAUDE_PROJECT_DIR=project)
    return subprocess.run(
        [sys.executable, shim(platform)], input=json.dumps(payload), capture_output=True, text=True, env=env
    )


def armed_claude():
    state, project = tempfile.mkdtemp(), tempfile.mkdtemp()
    hook(
        "claude",
        {"hook_event_name": "UserPromptExpansion", "session_id": "s", "command_name": "tpm"},
        state,
        project,
    )
    return state, project


def tool(name, args, agent_id="sub-1"):
    return {
        "hook_event_name": "PreToolUse",
        "session_id": "s",
        "agent_id": agent_id,
        "tool_name": name,
        "tool_input": args,
    }


def test_subagent_write_of_invalid_done_task_is_denied():
    state, project = armed_claude()
    path = os.path.join(project, "workstreams", "w.tasks.json")
    bad = hook(
        "claude",
        tool("Write", {"file_path": path, "content": json.dumps(doc(dict(DONE, evidence=[])))}),
        state,
        project,
    )
    assert bad.returncode == 2 and "done without evidence" in bad.stderr and "subagent" in bad.stderr
    good = hook(
        "claude", tool("Write", {"file_path": path, "content": json.dumps(doc(DONE))}), state, project
    )
    assert good.returncode == 0
    other = hook(
        "claude",
        tool("Write", {"file_path": os.path.join(project, "x.json"), "content": "{}"}),
        state,
        project,
    )
    assert other.returncode == 0


def test_subagent_edit_is_validated_after_applying_it():
    state, project = armed_claude()
    os.makedirs(os.path.join(project, "workstreams"))
    path = os.path.join(project, "workstreams", "w.tasks.json")
    open(path, "w").write(json.dumps(doc(dict(CLAIMED, doc_sha="3f2a1c9")), indent=2))
    to_done = {"file_path": path, "old_string": '"state": "claimed"', "new_string": '"state": "done"'}
    out = hook("claude", tool("Edit", to_done), state, project)
    assert out.returncode == 2 and "done without evidence" in out.stderr
    rename = {"file_path": path, "old_string": '"owner": "reviewer-1"', "new_string": '"owner": "reviewer-2"'}
    assert hook("claude", tool("Edit", rename), state, project).returncode == 0
    multi = {
        "file_path": path,
        "edits": [
            {"old_string": '"state": "claimed"', "new_string": '"state": "done"'},
            {"old_string": '"evidence": []', "new_string": '"evidence": ["abc1234"]'},
        ],
    }
    out = hook("claude", tool("MultiEdit", multi), state, project)
    assert out.returncode == 2 and "left_out" in out.stderr
    relative = dict(to_done, file_path="workstreams/w.tasks.json")
    assert hook("claude", tool("Edit", relative), state, project).returncode == 2


def test_copilot_denies_and_advisory_platforms_only_warn():
    state, project = tempfile.mkdtemp(), tempfile.mkdtemp()
    content = json.dumps(doc(dict(DONE, doc_sha="")))
    hook(
        "copilot",
        {"hook_event_name": "UserPromptSubmit", "session_id": "c", "prompt": "/tpm"},
        state,
        project,
    )
    out = hook(
        "copilot",
        {
            "session_id": "c",
            "cwd": project,
            "agent_id": "sub",
            "tool_name": "Write",
            "tool_input": {"file_path": "w.tasks.json", "content": content},
        },
        state,
        project,
    )
    assert json.loads(out.stdout)["permissionDecision"] == "deny"
    hook(
        "codex", {"hook_event_name": "UserPromptSubmit", "session_id": "x", "prompt": "/tpm"}, state, project
    )
    out = hook(
        "codex",
        {
            "hook_event_name": "PreToolUse",
            "session_id": "x",
            "cwd": project,
            "tool_name": "Write",
            "tool_input": {"file_path": "w.tasks.json", "content": content},
        },
        state,
        project,
    )
    assert out.returncode == 0 and "tpm advisory" in out.stdout
