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
    f = m["deployment_frequency"]
    assert f["count"] == 3 and f["median_seconds_between"] == 2 * DAY
    # n deploys over [first deploy, now], not n over the n-1 gaps between them.
    weeks = (f["window"]["end"] - f["window"]["start"]) / (7 * DAY)
    assert f["window"]["start"] == T0 + DAY and abs(f["per_week"] - 3 / weeks) < 1e-9
    # Commit a predates the first deploy: baseline, not measured. b, changelog and c each took a day.
    assert m["change_lead_time"]["sample"] == 3 and m["change_lead_time"]["baseline_commits"] == 1
    assert m["change_lead_time"]["median_seconds"] == DAY
    assert "committer date" in m["change_lead_time"]["source"]
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
    # The fix shipped in v0.1.2 (tagged T0 + 5 days); deployed_at is the npm publish, 2 h after the tag.
    deployed = T0 + 5 * DAY + 2 * 3600
    task = {"id": "hotfix", "state": "done", "kind": "fix", "fixes": "0.1.1", "deployed_at": iso(deployed)}
    json.dump({"tasks": [task]}, open(os.path.join(repo, "workstreams", "w.tasks.json"), "w"))
    m = dora(repo)["metrics"]
    assert m["change_fail_rate"]["failed"] == ["0.1.1"]
    # Matched to the latest deploy at or before deployed_at, which shipped it; recovery runs to deployed_at.
    assert m["deployment_rework_rate"]["rework"] == ["0.1.2"]
    assert m["deployment_rework_rate"]["value"].startswith("1/3 deploys (33%)")
    assert m["failed_deployment_recovery_time"]["median_seconds"] == deployed - (T0 + 3 * DAY)
    since = dora(repo, "--since", iso(T0 + 4 * DAY))  # only v0.1.2 (T0 + 5 days) is after this
    assert since["metrics"]["deployment_frequency"]["count"] == 1
    assert since["metrics"]["change_fail_rate"]["failed"] == []  # v0.1.1 is outside the window


def task_repo(task):
    repo = synthetic(changelog="")
    os.makedirs(os.path.join(repo, "workstreams"))
    json.dump(
        {"tasks": [dict({"id": "hotfix", "state": "done", "kind": "fix", "fixes": "0.1.1"}, **task)]},
        open(os.path.join(repo, "workstreams", "w.tasks.json"), "w"),
    )
    return dora(repo)["metrics"]


def test_task_fix_matching_rules():
    # fixed_in names the release outright.
    m = task_repo({"fixed_in": "0.1.2"})
    assert m["deployment_rework_rate"]["rework"] == ["0.1.2"]
    assert m["failed_deployment_recovery_time"]["median_seconds"] == 2 * DAY
    # deployed_at right after the failed release itself: that deploy is the failure, not its fix -> unmatched.
    m = task_repo({"deployed_at": iso(T0 + 3 * DAY + 6 * 3600)})
    assert m["deployment_rework_rate"]["rework"] == []
    assert (
        "%" not in m["deployment_rework_rate"]["value"]
        and "1 unmatched (fix of 0.1.1)" in m["deployment_rework_rate"]["value"]
    )
    # More than 48 h after the latest tag: too far to credit that tag -> unmatched.
    m = task_repo({"deployed_at": iso(T0 + 8 * DAY)})
    assert m["deployment_rework_rate"]["rework"] == [] and "unmatched" in m["deployment_rework_rate"]["value"]
    # fixed_in naming a version with no deploy -> unmatched, no bare percentage.
    m = task_repo({"fixed_in": "0.9.0"})
    assert "%" not in m["deployment_rework_rate"]["value"]


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


# ------------------------------------------------------------- PR #8 review fixes


def test_failures_from_both_sources_are_deduplicated_and_unmatched_records_reported():
    repo = synthetic()  # CHANGELOG: 0.1.1 fixes 0.1.0
    os.makedirs(os.path.join(repo, "workstreams"))
    tasks = {
        "tasks": [
            {
                "id": "same",
                "state": "done",
                "kind": "fix",
                "fixes": "0.1.0",
                "deployed_at": iso(T0 + 4 * DAY + 3600),
            },
            {
                "id": "ghost",
                "state": "done",
                "kind": "fix",
                "fixes": "0.0.9",
                "deployed_at": iso(T0 + 4 * DAY),
            },
        ]
    }
    json.dump(tasks, open(os.path.join(repo, "workstreams", "w.tasks.json"), "w"))
    m = dora(repo)["metrics"]
    assert m["change_fail_rate"]["failed"] == ["0.1.0"]  # one failure, recorded twice
    assert (
        m["change_fail_rate"]["value"].startswith("1/3 deploys") and "0.0.9" in m["change_fail_rate"]["value"]
    )
    assert m["deployment_rework_rate"]["rework"] == ["0.1.1"]  # the earlier of the two fixes
    assert m["failed_deployment_recovery_time"]["median_seconds"] == 2 * DAY
    only_ghost = synthetic(changelog="")
    os.makedirs(os.path.join(only_ghost, "workstreams"))
    json.dump(
        {"tasks": [tasks["tasks"][1]]}, open(os.path.join(only_ghost, "workstreams", "w.tasks.json"), "w")
    )
    m = dora(only_ghost)["metrics"]
    assert m["change_fail_rate"]["value"].startswith("not measurable: failure records don't match any deploy")
    assert "%" not in m["change_fail_rate"]["value"]


def test_lead_time_counts_each_commit_once_with_out_of_order_tags():
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q", "-b", "main")
    commit(repo, "base", T0)
    tag(repo, "0.1.0", T0 + DAY)
    commit(repo, "feature", T0 + 2 * DAY)
    tag(repo, "0.2.0", T0 + 3 * DAY)
    git(repo, "switch", "-q", "-c", "maint", "v0.1.0")
    commit(repo, "backport", T0 + 4 * DAY)
    tag(repo, "0.1.5", T0 + 5 * DAY)  # maintenance release, tagged after 0.2.0
    git(repo, "switch", "-q", "main")
    commit(repo, "next", T0 + 6 * DAY)
    tag(repo, "0.2.1", T0 + 7 * DAY)
    lt = dora(repo, "--since", iso(T0 - DAY))["metrics"]["change_lead_time"]
    # base, feature, backport, next: four commits, each counted once (the old prev..cur range counted
    # "feature" again under 0.2.1).
    assert lt["sample"] == 4 and lt["baseline_commits"] == 0
    assert lt["median_seconds"] == DAY


def test_annotated_tags_use_the_tagger_date_and_lightweight_tags_warn():
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q", "-b", "main")
    commit(repo, "a", T0)
    tag(repo, "0.1.0", T0 + 5 * DAY)  # annotated, tagged five days after the commit
    commit(repo, "b", T0 + 6 * DAY)
    git(repo, "tag", "v0.1.1", at=T0 + 9 * DAY)  # lightweight: carries the commit's date
    report = dora(repo, "--since", iso(T0 - DAY))
    lt = report["metrics"]["change_lead_time"]
    assert lt["sample"] == 2
    assert any("lightweight tag" in w for w in report["warnings"])
    assert any("even one whose release failed" in w for w in report["warnings"])
    assert lt["p90_seconds"] == 5 * DAY  # a -> v0.1.0's tagger date; b -> v0.1.1 at b's own commit date (0)


def test_npm_mode_uses_publish_times_and_maps_versions_to_commits():
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q", "-b", "main")
    for version, at in (("0.1.0", T0), ("0.1.1", T0 + 2 * DAY)):
        open(os.path.join(repo, "package.json"), "w").write(
            json.dumps({"name": "demo", "version": version}, indent=2)
        )
        git(repo, "add", "package.json")
        git(repo, "commit", "-q", "-m", version, at=at)
        if version == "0.1.0":
            tag(repo, "0.1.0", T0 + 3600)
    git(repo, "tag", "-a", "v0.9.9", "-m", "never published", at=T0 + 3 * DAY)  # a tag npm doesn't have
    times = {
        "created": iso(T0),
        "modified": iso(T0 + 3 * DAY),
        "0.1.0": iso(T0 + 2 * 3600),
        "0.1.1": iso(T0 + 2 * DAY + 3600),
        "0.1.2": iso(T0 + 4 * DAY),
    }
    path = os.path.join(tempfile.mkdtemp(), "times.json")
    json.dump(times, open(path, "w"))
    env = dict(os.environ, CADENCE_DORA_NPM_TIMES=path)
    out = subprocess.run(
        [CLI, "dora", "--repo", repo, "--json", "--deploys", "npm", "--since", iso(T0 - DAY)],
        capture_output=True,
        text=True,
        env=env,
    )
    report = json.loads(out.stdout)
    m = report["metrics"]
    assert m["deployment_frequency"]["count"] == 3  # published versions only; v0.9.9 isn't one
    assert any("0.1.2" in w and "no matching commit" in w for w in report["warnings"])
    # 0.1.0 via its tag (published 2 h after its commit), 0.1.1 via package.json history (1 h).
    assert m["change_lead_time"]["sample"] == 2 and m["change_lead_time"]["p90_seconds"] == 2 * 3600


def test_bad_task_files_and_times_warn_and_changelog_resets_on_other_headings():
    repo = synthetic(
        changelog="# Changelog\n\n## 0.1.1\n\n- planned\n\n## Notes\n\n### Fixed (regression from 0.1.0)\n"
    )
    os.makedirs(os.path.join(repo, "workstreams"))
    open(os.path.join(repo, "workstreams", "broken.tasks.json"), "w").write("{not json")
    json.dump(
        {
            "tasks": [
                {"id": "x", "state": "done", "kind": "fix", "fixes": "0.1.0", "deployed_at": "2026-06-01"}
            ]
        },
        open(os.path.join(repo, "workstreams", "w.tasks.json"), "w"),
    )
    report = dora(repo)
    assert any("broken.tasks.json isn't valid JSON" in w for w in report["warnings"])
    assert any("isn't ISO 8601" in w for w in report["warnings"])
    m = report["metrics"]
    assert m["deployment_rework_rate"]["rework"] == []  # "## Notes" isn't a release
    assert "no matched fix" in m["failed_deployment_recovery_time"]["value"]
    assert "%" not in m["deployment_rework_rate"]["value"]


ISO_CASES = {
    "2026-11-02T09:30:00Z": True,
    "2026-11-02T09:30Z": True,
    "2026-11-02T09:30:00.123+02:00": True,
    "2026-11-02T09:30:00.123456-05:00": True,
    "2026-11-02T09:30:00": False,  # no timezone
    "2026-11-02": False,
    "20261102T093000Z": False,  # basic format
    "2026-11-02 09:30:00Z": False,
    "2026-11-02T09:30:00.1Z": False,
    "2026-02-30T00:00Z": False,  # no such day
    "2026-11-02T24:00Z": False,  # no such hour
    "2026-11-02T09:60Z": False,
    "2028-02-29T12:00Z": True,  # leap day
    "yesterday": False,
}


def test_dora_and_tasks_check_share_one_iso8601_rule():
    import re
    import sys

    sys.path.insert(0, os.path.join(ROOT, "skills", "tpm", "scripts"))
    import tasks_check

    js = open(os.path.join(ROOT, "bin", "dora.mjs")).read()
    assert re.search(r"const ISO8601 = /(.+)/;", js).group(1) == tasks_check.ISO8601
    assert re.search(r"const SEMVER = /(.+)/;", js).group(1) == tasks_check.SEMVER
    script = (
        f"import {{ parseTime }} from {json.dumps(os.path.join(ROOT, 'bin', 'dora.mjs'))};"
        f"console.log(JSON.stringify({json.dumps(list(ISO_CASES))}.map((v) => parseTime(v) !== null)));"
    )
    node = json.loads(
        subprocess.run(
            ["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True
        ).stdout
    )
    python = [tasks_check.parse_time(v) is not None for v in ISO_CASES]
    assert node == python == list(ISO_CASES.values())
