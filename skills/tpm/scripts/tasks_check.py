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
import re
import sys
from datetime import datetime

STATES = {"assigned", "claimed", "blocked", "done"}
KINDS = {"planned", "fix"}
TIMES = ("committed_at", "merged_at", "deployed_at")  # optional, in this order


# The one ISO 8601 rule for task times, shared with bin/dora.mjs (a test keeps the two patterns identical):
# extended format, seconds optional, fraction of 3 or 6 digits, and a timezone (Z or +hh:mm).
ISO8601 = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{3}|\.\d{6})?)?(Z|[+-]\d{2}:\d{2})$"
# A version as `fixes` names it, shared with bin/dora.mjs too.
SEMVER = r"^v?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$"


def parse_time(value):
    """An ISO 8601 timestamp matching ISO8601, as an aware datetime, or None."""
    if not isinstance(value, str) or not re.match(ISO8601, value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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
        times = []
        for key in TIMES:
            if key in task and task[key] is not None:
                parsed = parse_time(task[key])
                if parsed is None:
                    errors.append(
                        f"{where}: {key} must be an ISO 8601 time with a timezone, not {task[key]!r}"
                    )
                else:
                    times.append((key, parsed))
        for (a, ta), (b, tb) in zip(times, times[1:], strict=False):
            if tb < ta:
                errors.append(f"{where}: {b} is before {a}")
        if "kind" in task and task["kind"] not in KINDS:
            errors.append(f"{where}: kind must be one of {sorted(KINDS)}, not {task['kind']!r}")
        if "fixed_in" in task and not (
            isinstance(task["fixed_in"], str) and re.match(SEMVER, task["fixed_in"])
        ):
            errors.append(
                f"{where}: fixed_in must be the version that shipped the fix, like 0.1.1, not {task['fixed_in']!r}"
            )
        if "fixed_in" in task and not (
            isinstance(task["fixed_in"], str) and re.match(SEMVER, task["fixed_in"])
        ):
            errors.append(
                f"{where}: fixed_in must be the version that shipped the fix, like 0.1.1, not {task['fixed_in']!r}"
            )
        if task.get("kind") == "fix":
            fixes = task.get("fixes")
            ids = {t.get("id") for t in data["tasks"] if isinstance(t, dict)}
            if not (isinstance(fixes, str) and (re.match(SEMVER, fixes) or (fixes in ids and fixes != tid))):
                errors.append(
                    f"{where}: a fix must say what it fixes: a version like 0.1.0 or another task's id, not {fixes!r}"
                )
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
