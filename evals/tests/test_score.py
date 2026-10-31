"""Tests for evals/scripts/score.py: run layouts, per-arm totals across runs, runs that can't be scored, what a run
changed (setup commit vs the legacy rule for rounds 1-3), sealed-name safety, Wilson.

Run with `python3 evals/tests/test_score.py` or `pytest`. Standard library only (pytest optional).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent
_spec = importlib.util.spec_from_file_location("score", EVALS / "scripts" / "score.py")
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

CASE = "tempting-quick-ratio-fix"  # a real case: the scorer checks run assertions against its graders
SHA = "0123456789abcdef0123456789abcdef01234567"


def _assertions(case: str) -> list[str]:
    return [g.read_text().split("---", 2)[2].strip() for g in sorted((EVALS / case / "graders").glob("*.md"))]


def _transcript(cwd: str, edit: str | None = None) -> str:
    events = [{"type": "system", "subtype": "init", "cwd": cwd}]
    if edit:
        events.append(
            {
                "type": "assistant",
                "parent_tool_use_id": None,
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Edit", "id": "t1", "input": {"file_path": edit}}
                    ]
                },
            }
        )
    events.append({"type": "result", "result": "done"})
    return "\n".join(json.dumps(e) for e in events) + "\n"


def make_run(
    run: Path,
    edit: str | None = None,
    diff: str = "",
    status: str = "",
    files: dict | None = None,
    setup: str | None = SHA,
    diffed_against: str | None = SHA,
):
    """A run directory. By default in the current layout: setup committed as SHA and the diff taken against it.
    setup=None, diffed_against=None gives a round 1-3 (legacy) run."""
    (run / "outputs").mkdir(parents=True)
    (run / "transcript.jsonl").write_text(_transcript(str(run), edit and str(run / edit)))
    (run / "final.md").write_text("done")
    (run / "outputs" / "git_diff.patch").write_text(diff)
    (run / "outputs" / "git_status.txt").write_text(status)
    if setup:
        (run / "post_setup_commit").write_text(setup + "\n")
    if diffed_against:
        (run / "outputs" / "git_diff_base").write_text(diffed_against + "\n")
    for name, text in (files or {}).items():
        (run / name).write_text(text)


def legacy_run(run: Path, **kw):
    make_run(run, setup=None, diffed_against=None, **kw)


def make_case(root: Path, case: str = CASE) -> Path:
    d = root / case
    d.mkdir(parents=True)
    (d / "eval_metadata.json").write_text(json.dumps({"eval_name": case, "assertions": _assertions(case)}))
    return d


def run_score(root: Path, reg: dict | None = None, **kw) -> str:
    args = argparse.Namespace(
        **{"dir": str(root), "set": "all", "exclude_outputs": False, "legacy": False, **kw}
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        score.cmd_score(args, reg or score.registry())
    return out.getvalue()


def section(out: str, arm: str) -> str:
    """The lines of `score` output that belong to one arm."""
    lines, keep = [], False
    for line in out.splitlines():
        if not line.startswith(" "):
            keep = line.startswith(f"{arm}:")
        if keep:
            lines.append(line)
    return "\n".join(lines)


# ------------------------------------------------------------------ layouts and totals


def test_run_n_layout_totals_across_runs_per_arm():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        make_run(case / "with_skill" / "run-2", edit="app/views.py")  # main-thread edit: #01 fails
        make_run(case / "with_skill" / "run-10")
        make_run(case / "without_skill" / "run-1", edit="app/views.py")
        out = run_score(root)
        assert "with_skill: 1 cases, 3 runs scored (3 per case)" in out, out
        assert "deterministic assertions passed  2/3 = 67%" in out, out
        assert "without_skill: 1 cases, 1 runs scored (1 per case)" in out, out
        assert "deterministic assertions passed  0/1 = 0%" in out, out
        assert "not scored" not in out, out
        labels = [score.run_label(c, a, r) for c, a, r, _, _ in score.runs(root, "all", score.registry())]
        assert labels == [
            f"{CASE}/with_skill/run-1",
            f"{CASE}/with_skill/run-2",
            f"{CASE}/with_skill/run-10",
            f"{CASE}/without_skill/run-1",
        ], labels


def test_single_run_layout_still_read():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill")
        (case / "with_skill" / "session_log").mkdir()  # other subdirectories are not runs
        out = run_score(root)
        assert "with_skill: 1 cases, 1 runs scored (1 per case)" in out, out
        assert score.run_label(CASE, "with_skill", case / "with_skill") == f"{CASE}/with_skill"


def test_both_layouts_in_one_arm_is_counted_not_scored():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        (case / "with_skill" / "transcript.jsonl").write_text(_transcript(str(case)))
        out = run_score(root)
        assert "with_skill: 0 cases, 0 runs scored" in out, out
        assert "2 both run-<n>/ and a top-level transcript in the arm" in out, out


# ------------------------------------------------------------------ runs that can't be scored


def test_invalid_attempts_counted_per_arm():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        make_run(case / "without_skill" / "run-1")
        for attempt in ("run-1-attempt-1", "run-1-attempt-2"):
            make_run(root / "_invalid" / CASE / "with_skill" / attempt, edit="app/views.py")
        make_run(root / "_invalid" / CASE / "without_skill" / "run-2-attempt-1")
        out = run_score(root)
        assert "2 under _invalid/" in section(out, "with_skill"), out
        assert "1/1 = 100%" in section(out, "with_skill"), out
        assert "1 under _invalid/" in section(out, "without_skill"), out


def test_arm_with_only_invalid_runs_is_still_reported():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "without_skill" / "run-1")
        (case / "with_skill").mkdir()  # emptied: every attempt was moved to _invalid/
        make_run(root / "_invalid" / CASE / "with_skill" / "run-1-attempt-1")
        out = run_score(root)
        assert "with_skill: 0 cases, 0 runs scored" in out, out
        assert section(out, "with_skill").count("not scored") == 1 and "1 under _invalid/" in out, out


def test_not_scored_respects_set():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        make_run(root / "_invalid" / CASE / "with_skill" / "run-1-attempt-1")
        reg = score.registry()
        assert reg[CASE]["set"] == "train"
        assert "not scored" not in run_score(root, set="validation")
        assert "1 under _invalid/" in run_score(root, set="train")
        reg[CASE]["set"] = "validation"
        assert "1 under _invalid/" in run_score(root, reg=reg, set="validation")
        assert "not scored" not in run_score(root, reg=reg, set="train")


def test_missing_transcript_counted_in_both_layouts():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        (case / "with_skill" / "run-2" / "outputs").mkdir(parents=True)  # crashed before the transcript
        (case / "without_skill" / "outputs").mkdir(parents=True)  # one-run arm, no transcript
        out = run_score(root)
        assert "with_skill: 1 cases, 1 runs scored (1 per case)" in out, out
        assert "1 missing transcript" in section(out, "with_skill"), out
        assert "without_skill: 0 cases, 0 runs scored" in out, out
        assert "1 missing transcript" in section(out, "without_skill"), out


def test_underscore_dirs_at_any_level_counted_under_the_arm():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        make_run(case / "_invalid" / "with_skill" / "run-1", edit="app/views.py")
        make_run(case / "with_skill" / "_retry" / "run-2", edit="app/views.py")
        make_run(case / "with_skill" / "run-1" / "_old", edit="app/views.py")
        make_run(case / "_scratch" / "run-1")  # no arm in the path
        out = run_score(root)
        w = section(out, "with_skill")
        assert "with_skill: 1 cases, 1 runs scored" in w and "1/1 = 100%" in w, out
        assert "1 under _invalid/" in w and "1 under _old/" in w and "1 under _retry/" in w, out
        assert "1 under _scratch/" in section(out, "?"), out


def test_stray_entries_under_invalid_dont_abort():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        (root / "_invalid").mkdir()
        (root / "_invalid" / "transcript.jsonl").write_text(_transcript(str(root)))
        make_run(root / "_invalid" / "round2" / CASE / "with_skill")  # an older layout
        make_run(root / "_invalid" / "retired-case" / "with_skill" / "run-1")
        out = run_score(root)
        assert "with_skill: 1 cases, 1 runs scored" in out, out
        assert "2 under _invalid/, no known case" in section(out, "?"), out
        # the older layout's case is known: counted under its arm
        assert "1 under _invalid/" in section(out, "with_skill"), out
        assert "no known case" not in run_score(root, set="train"), "unknown cases belong to no set"


# ------------------------------------------------------------------ no sealed case names


def test_set_test_prints_no_case_names():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        (case / "with_skill" / "run-2").mkdir()
        make_run(case / "with_skill" / "run-3", setup=None, diffed_against=None)
        make_run(case / "_scratch" / "with_skill" / "run-1")
        make_run(case / "without_skill" / "run-1")
        (case / "without_skill" / "transcript.jsonl").write_text(_transcript(str(case)))
        make_run(root / "_invalid" / CASE / "with_skill" / "run-1-attempt-1")
        reg = score.registry()
        reg[CASE]["set"] = "test"
        out = run_score(root, reg=reg, set="test")
        assert "with_skill: 1 cases, 1 runs scored" in out, out
        assert "not scored" in out, out
        for name in reg:
            assert name not in out, (name, out)


# ------------------------------------------------------------------ setup commit vs legacy: one decision


def test_diff_base_decides_in_one_place():
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        cases = {
            "ok": (SHA, SHA),
            "no-setup": (None, None),
            "no-diff-base": (SHA, None),
            "other-base": (SHA, "f" * 40),
            "diff-base-only": (None, SHA),
        }
        for name, (setup, against) in cases.items():
            make_run(t / name, setup=setup, diffed_against=against)
        verdict = {n: score.diff_base(t / n, legacy=False) for n in cases}
        assert verdict["ok"] == (SHA, None)
        assert verdict["no-setup"] == (None, "no post_setup_commit (rounds 1-3 need --legacy)")
        assert verdict["diff-base-only"] == verdict["no-setup"]
        assert verdict["no-diff-base"] == (None, "diff not taken against the post-setup commit")
        assert verdict["other-base"] == verdict["no-diff-base"]
        legacy = {n: score.diff_base(t / n, legacy=True) for n in cases}
        assert legacy["no-setup"] == ("legacy", None)
        for n in ("ok", "no-diff-base", "other-base", "diff-base-only"):
            assert legacy[n] == (None, "setup commit recorded in a --legacy round"), n


def test_run_without_setup_commit_refused_unless_legacy():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        legacy_run(case / "with_skill" / "run-1", diff=CLAUDE_DIFF)
        out = run_score(root)
        assert "with_skill: 0 cases, 0 runs scored" in out, out
        assert "1 no post_setup_commit (rounds 1-3 need --legacy)" in out, out
        out = run_score(root, legacy=True)
        assert "with_skill: 1 cases, 1 runs scored" in out and "--legacy" in out, out


# ------------------------------------------------------------------ what the run changed

APP_DIFF = """diff --git a/app/views.py b/app/views.py
index 1111111..2222222 100644
--- a/app/views.py
+++ b/app/views.py
@@ -1,3 +1,3 @@
 a = 1
----- a markdown rule or a SQL comment, deleted
+b = 2
"""
CLAUDE_DIFF = """diff --git a/.claude/skills/tpm/SKILL.md b/.claude/skills/tpm/SKILL.md
--- a/.claude/skills/tpm/SKILL.md
+++ b/.claude/skills/tpm/SKILL.md
@@ -1 +1 @@
-old rule
+new rule
"""
GITIGNORE_DIFF = """diff --git a/.gitignore b/.gitignore
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,2 @@
 .venv/
-.cadence/tpm.off
"""


def test_setup_commit_diff_is_the_runs_own_work():
    """With the setup committed, every file in the diff and every untracked file is the run's,
    .claude/ and .cadence/ included."""
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        make_run(
            run,
            diff=APP_DIFF + CLAUDE_DIFF + GITIGNORE_DIFF,
            status=" M .gitignore\n?? .cadence/tpm.off\n?? outputs/01-message.md\n?? tests/test_new.py\n",
        )
        f = score.check_run(run, CASE, SHA)
        assert f["diff_base"] == SHA
        assert f["code_or_test_files_changed"] == [
            "app/views.py",
            ".claude/skills/tpm/SKILL.md",
            ".gitignore",
            ".cadence/tpm.off",
            "tests/test_new.py",
        ], f["code_or_test_files_changed"]
        # 1 + 1 + 1: the content line starting with "----" counts, the "--- a/..." headers don't
        assert f["diff_deleted_lines"] == 3, f["diff_deleted_lines"]


def test_setup_commit_with_no_run_changes():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        make_run(run, status="?? outputs/01-message.md\n")
        assert score.check_run(run, CASE, SHA)["code_or_test_files_changed"] == []


def test_legacy_rule_sets_aside_claude_diffs_and_listed_untracked_only():
    """The legacy rule, exactly: diff files under .claude/ and untracked files listed in
    git_status_post_setup.txt (by exact path) are set aside. Everything else counts: an untracked .claude/ file
    the setup didn't list, untracked .cadence/ files, and a tracked file such as .gitignore that is in the diff,
    whoever edited it. (On the stored rounds 1-3 this gives c24a19e's facts: none of them has the last three.)"""
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        legacy_run(
            run,
            diff=CLAUDE_DIFF + GITIGNORE_DIFF,
            status=(
                "?? .claude/settings.json\n?? .claude/skills/tpm/extra.md\n?? .cadence/tpm.off\n"
                "?? outputs/m.md\n"
            ),
            files={"git_status_post_setup.txt": " M .gitignore\n?? .claude/settings.json\n"},
        )
        f = score.check_run(run, CASE, "legacy")
        assert f["diff_base"] == "legacy"
        assert f["diff_files"] == [".gitignore"], f
        assert f["untracked_non_outputs"] == [".claude/skills/tpm/extra.md", ".cadence/tpm.off"], f
        assert f["diff_deleted_lines"] == 1, f


def test_legacy_round_3_shape_reads_clean():
    """Round 3's real shape: the uncommitted install listed in git_status_post_setup.txt, and .gitignore left out
    of git_diff.patch by its runner. Nothing counts as changed."""
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        install = "?? .claude/settings.json\n?? .claude/skills/tpm/SKILL.md\n"
        legacy_run(
            run,
            status=install + "?? outputs/02-message-to-user.md\n",
            files={"git_status_post_setup.txt": " M .gitignore\n" + install},
        )
        assert score.check_run(run, CASE, "legacy")["code_or_test_files_changed"] == []


def test_parse_diff_skips_only_headers():
    files = score.parse_diff(APP_DIFF + GITIGNORE_DIFF)
    assert files == [("app/views.py", 1), (".gitignore", 1)], files


# ------------------------------------------------------------------ statistics


def test_wilson():
    p, lo, hi = score.wilson(10, 18)
    assert (round(p, 4), round(lo, 4), round(hi, 4)) == (0.5556, 0.3372, 0.7544)
    p, lo, hi = score.wilson(0, 3)
    assert (p, lo, round(hi, 4)) == (0.0, 0.0, 0.5615)
    assert score.wilson(0, 0)[1:] == (0.0, 1.0)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
