#!/usr/bin/env python3
"""Validate workstream task files (workstreams/<slug>.tasks.json).

The rules are the ones in references/workstream.md. The one that matters most:
a task is `done` only with evidence, a reviewed left-out list and the doc SHA it
was dispatched against. Used three ways: as a CLI and pre-commit hook on the
orchestration branch, and by the guard to deny a subagent write that would
produce an invalid task file. Stdlib only.

CLI: tasks_check.py FILE...   exit 0 if every file is valid, 1 otherwise.
"""

from __future__ import annotations

import json
import sys

STATES = {"assigned", "claimed", "blocked", "done"}
SUFFIX = ".tasks.json"


def validate(data) -> list[str]:
    """Return a list of problems; empty means valid."""
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        return ['top level must be an object with a "tasks" list']
    errors = []
    seen = set()
    for i, task in enumerate(data["tasks"]):
        where = f"tasks[{i}]"
        if not isinstance(task, dict):
            errors.append(f"{where}: must be an object")
            continue
        tid = task.get("id")
        if not isinstance(tid, str) or not tid:
            errors.append(f"{where}: id must be a non-empty string, not {tid!r}")
        else:
            where = f"task {tid!r}"
            if tid in seen:
                errors.append(f"{where}: duplicate id")
            seen.add(tid)
        state = task.get("state")
        if not isinstance(state, str) or state not in STATES:
            errors.append(f"{where}: state must be one of {sorted(STATES)}, not {state!r}")
        if "evidence" in task and not isinstance(task["evidence"], list):
            errors.append(f"{where}: evidence must be a list")
        if state == "done":
            if not task.get("evidence"):
                errors.append(f"{where}: done without evidence")
            if not isinstance(task.get("left_out"), list):
                errors.append(f"{where}: done without a left_out list (use [] for nothing)")
            if not task.get("left_out_accepted_by"):
                errors.append(f"{where}: done without left_out_accepted_by (the reviewer)")
            if not task.get("doc_sha"):
                errors.append(f"{where}: done without doc_sha")
    return errors


def validate_text(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [f"not valid JSON ({exc})"]
    return validate(data)


def main(argv: list[str]) -> int:
    bad = 0
    for path in argv:
        with open(path, encoding="utf-8") as f:
            errors = validate_text(f.read())
        for e in errors:
            print(f"{path}: {e}", file=sys.stderr)
        bad += bool(errors)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
