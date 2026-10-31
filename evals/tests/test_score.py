"""Tests for evals/scripts/score.py: run layouts, per-arm totals across runs, the kit-install exclusion, Wilson.

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


def make_run(run: Path, edit: str | None = None, diff: str = "", status: str = "", files: dict | None = None):
    (run / "outputs").mkdir(parents=True)
    (run / "transcript.jsonl").write_text(_transcript(str(run), edit and str(run / edit)))
    (run / "final.md").write_text("done")
    (run / "outputs" / "git_diff.patch").write_text(diff)
    (run / "outputs" / "git_status.txt").write_text(status)
    for name, text in (files or {}).items():
        (run / name).write_text(text)


def make_case(root: Path, case: str = CASE) -> Path:
    d = root / case
    d.mkdir(parents=True)
    (d / "eval_metadata.json").write_text(json.dumps({"eval_name": case, "assertions": _assertions(case)}))
    return d


def run_score(root: Path, reg: dict | None = None, **kw) -> str:
    args = argparse.Namespace(**{"dir": str(root), "set": "all", "exclude_outputs": False, **kw})
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        score.cmd_score(args, reg or score.registry())
    return out.getvalue()


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
        labels = [score.run_label(c, a, r) for c, a, r, _ in score.runs(root, "all", score.registry())]
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


def test_both_layouts_in_one_arm_is_an_error():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        (case / "with_skill" / "transcript.jsonl").write_text(_transcript(str(case)))
        try:
            run_score(root)
        except SystemExit as e:
            assert "both run-<n>/" in str(e), e
        else:
            raise AssertionError("expected SystemExit")


# ------------------------------------------------------------------ runs that can't be scored (findings 5, 7)


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
        with_part, without_part = out.split("without_skill:")
        assert "not scored                       2 under _invalid/" in with_part, out
        assert "not scored                       1 under _invalid/" in without_part, out
        assert "with_skill: 1 cases, 1 runs scored" in out and "1/1 = 100%" in with_part, out


def test_arm_with_only_invalid_runs_is_still_reported():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "without_skill" / "run-1")
        (case / "with_skill").mkdir()
        make_run(root / "_invalid" / CASE / "with_skill" / "run-1-attempt-1")
        out = run_score(root)
        assert "with_skill: 0 cases, 0 runs scored" in out, out
        assert "1 under _invalid/" in out, out


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


def test_run_dir_without_transcript_is_counted_not_dropped():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        (case / "with_skill" / "run-2" / "outputs").mkdir(parents=True)  # crashed before the transcript
        out = run_score(root)
        assert "with_skill: 1 cases, 1 runs scored (1 per case)" in out, out
        assert "not scored                       1 missing transcript" in out, out


def test_underscore_dir_inside_a_case_is_counted():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        make_run(case / "_scratch" / "run-1", edit="app/views.py")
        out = run_score(root)
        assert "?: 0 cases, 0 runs scored" in out and f"1 under {CASE}/_scratch/" in out, out
        assert "1/1 = 100%" in out, out


# ------------------------------------------------------------------ what the run changed (findings 1-4, 6, 8)

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
SHA = "0123456789abcdef0123456789abcdef01234567"


def _post_setup(run: Path, base: str | None = SHA) -> None:
    (run / "post_setup_commit").write_text(SHA + "\n")
    if base:
        (run / "outputs" / "git_diff_base").write_text(base + "\n")


def _changes(run: Path) -> dict:
    return score.check_run(run, CASE)


def test_post_setup_commit_diff_is_the_runs_own_work():
    """With the install committed, every file in the diff and every untracked file is the run's,
    .claude/ and .cadence/ included: there is no special case left to hide an edit."""
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        make_run(
            run,
            diff=APP_DIFF + CLAUDE_DIFF + GITIGNORE_DIFF,
            status=" M .gitignore\n?? .cadence/tpm.off\n?? outputs/01-message.md\n?? tests/test_new.py\n",
        )
        _post_setup(run)
        f = _changes(run)
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


def test_post_setup_commit_with_no_run_changes():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        make_run(run, status="?? outputs/01-message.md\n")
        _post_setup(run)
        assert _changes(run)["code_or_test_files_changed"] == []


def test_diff_not_against_post_setup_commit_is_not_scored():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        for n, base in ((1, SHA), (2, None), (3, "f" * 40)):
            run = case / "with_skill" / f"run-{n}"
            make_run(run)
            _post_setup(run, base)
        out = run_score(root)
        assert "with_skill: 1 cases, 1 runs scored" in out, out
        assert "2 diff not taken against the post-setup commit" in out, out


def test_legacy_rounds_read_as_before():
    """Rounds 1-3 have no post_setup_commit: diff files under .claude/ are set aside (round 1), and so are
    untracked files listed in git_status_post_setup.txt (round 3's uncommitted install), by exact path only."""
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        make_run(
            run,
            diff=CLAUDE_DIFF + GITIGNORE_DIFF,
            status="?? .claude/settings.json\n?? .claude/skills/tpm/extra.md\n?? outputs/m.md\n",
            files={"git_status_post_setup.txt": " M .gitignore\n?? .claude/settings.json\n"},
        )
        f = _changes(run)
        assert f["diff_base"] == "legacy"
        assert f["code_or_test_files_changed"] == [".gitignore", ".claude/skills/tpm/extra.md"], f
        assert f["diff_deleted_lines"] == 1, f


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
