"""Tests for `cadence-orchestrator dora` on synthetic repos with controlled commit and tag times."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "bin", "cadence-orchestrator.mjs")
DAY = 86400
T0 = 1_780_000_000  # a fixed epoch second


def git(repo, *args, at=None):
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.com",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.com",
    )
    if at is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"@{at} +0000"
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True, env=env
    ).stdout


def commit(repo, name, at):
    open(os.path.join(repo, name), "w").write(name)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name, at=at)


def tag(repo, version, at):
    git(repo, "tag", "-a", f"v{version}", "-m", version, at=at)


CHANGELOG = """# Changelog

## 0.1.2

- something planned

## 0.1.1

### Fixed (regression from 0.1.0)

- the thing 0.1.0 broke

## 0.1.0

- first
"""


def synthetic(changelog=CHANGELOG):
    """Three releases: commits 1 day before each tag; 0.1.1 fixes 0.1.0, two days after it."""
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q", "-b", "main")
    commit(repo, "a", T0)
    tag(repo, "0.1.0", T0 + DAY)
    commit(repo, "b", T0 + 2 * DAY)
    if changelog:
        open(os.path.join(repo, "CHANGELOG.md"), "w").write(changelog)
        git(repo, "add", "CHANGELOG.md")
    git(repo, "commit", "-q", "--allow-empty", "-m", "changelog", at=T0 + 2 * DAY)
    tag(repo, "0.1.1", T0 + 3 * DAY)
    commit(repo, "c", T0 + 4 * DAY)
    tag(repo, "0.1.2", T0 + 5 * DAY)
    return repo


def dora(repo, *args):
    out = subprocess.run([CLI, "dora", "--repo", repo, "--json", *args], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_throughput_from_tags():
    report = dora(synthetic())
    m = report["metrics"]
    assert m["deployment_frequency"]["count"] == 3
    assert m["deployment_frequency"]["median_seconds_between"] == 2 * DAY
    assert m["change_lead_time"]["sample"] == 4  # a, b, changelog, c
    assert m["change_lead_time"]["median_seconds"] == DAY
    assert "committed to version control to deployed" in m["change_lead_time"]["definition"]
    assert any("too few" in w for w in report["warnings"])


def test_instability_from_changelog_records():
    m = dora(synthetic())["metrics"]
    assert m["change_fail_rate"]["failed"] == ["0.1.0"] and m["change_fail_rate"]["sample"] == 3
    assert m["change_fail_rate"]["value"].startswith("1/3 deploys")
    assert m["deployment_rework_rate"]["rework"] == ["0.1.1"]
    assert m["failed_deployment_recovery_time"]["median_seconds"] == 2 * DAY  # v0.1.0 -> v0.1.1


def test_no_failure_records_means_not_measurable():
    m = dora(synthetic(changelog=""))["metrics"]
    for k in ("change_fail_rate", "deployment_rework_rate", "failed_deployment_recovery_time"):
        assert m[k]["value"] == "not measurable: no failure records", k
        assert m[k]["sample"] == 0


def iso(ts):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


def test_task_records_and_since():
    repo = synthetic(changelog="")
    os.makedirs(os.path.join(repo, "workstreams"))
    fixed_at = T0 + 3 * DAY + 6 * 3600  # six hours after v0.1.1 shipped
    tasks = {
        "tasks": [
            {"id": "hotfix", "state": "done", "kind": "fix", "fixes": "0.1.1", "deployed_at": iso(fixed_at)}
        ]
    }
    json.dump(tasks, open(os.path.join(repo, "workstreams", "w.tasks.json"), "w"))
    m = dora(repo)["metrics"]
    assert m["change_fail_rate"]["failed"] == ["0.1.1"]
    assert m["deployment_rework_rate"]["rework"] == []  # task records name the failure, not a fixing release
    assert m["failed_deployment_recovery_time"]["median_seconds"] == 6 * 3600
    since = dora(repo, "--since", iso(T0 + 4 * DAY))  # only v0.1.2 (T0 + 5 days) is after this
    assert since["metrics"]["deployment_frequency"]["count"] == 1
    assert since["metrics"]["change_fail_rate"]["failed"] == []  # v0.1.1 is outside the window


def test_merges_mode_and_no_tags():
    repo = synthetic()
    m = dora(repo, "--deploys", "merges")["metrics"]
    assert m["deployment_frequency"]["count"] == 4  # four commits on main's first-parent history
    assert "can't match" in m["change_fail_rate"]["value"]
    empty = tempfile.mkdtemp()
    git(empty, "init", "-q", "-b", "main")
    commit(empty, "x", T0)
    report = dora(empty)
    assert report["metrics"]["deployment_frequency"]["value"] == "not measurable: no deploys"
    assert any("No release tags" in w for w in report["warnings"])


def test_text_output_and_arguments():
    repo = synthetic()
    text = subprocess.run([CLI, "dora", "--repo", repo], capture_output=True, text=True).stdout
    assert (
        "Change fail rate: 1/3 deploys" in text
        and "definition:" in text
        and "source:" in text
        and "(n=3)" in text
    )
    for bad in (
        ["--deploys", "weekly"],
        ["--since", "not a date"],
        ["--target", "claude"],
        ["--catalog", "x.md"],
    ):
        out = subprocess.run([CLI, "dora", "--repo", repo, *bad], capture_output=True, text=True)
        assert out.returncode == 2, bad
    out = subprocess.run([CLI, "status", "--repo", repo, "--json"], capture_output=True, text=True)
    assert out.returncode == 2  # --json belongs to dora


def test_this_repos_changelog_records_the_0_1_0_regression():
    text = open(os.path.join(ROOT, "CHANGELOG.md")).read()
    section = text.split("## 0.1.1", 1)[1].split("\n## ", 1)[0]
    assert "### Fixed (regression from 0.1.0)" in section and "__pycache__" in section
