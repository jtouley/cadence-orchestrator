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


def run_score(root: Path, **kw) -> str:
    args = argparse.Namespace(dir=str(root), set="all", exclude_outputs=False, **kw)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        score.cmd_score(args, score.registry())
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
        assert "with_skill: 1 cases, 3 runs (3 per case)" in out, out
        assert "deterministic assertions passed  2/3 = 67%" in out, out
        assert "without_skill: 1 cases, 1 runs (1 per case)" in out, out
        assert "deterministic assertions passed  0/1 = 0%" in out, out
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
        assert "with_skill: 1 cases, 1 runs (1 per case)" in out, out
        assert score.run_label(CASE, "with_skill", case / "with_skill") == f"{CASE}/with_skill"


def test_underscore_dirs_counted_not_scored():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        case = make_case(root)
        make_run(case / "with_skill" / "run-1")
        make_run(root / "_invalid" / CASE / "with_skill" / "run-1-attempt-1", edit="app/views.py")
        make_run(case / "_scratch" / "run-1", edit="app/views.py")
        out = run_score(root)
        assert "not scored: 2 runs" in out, out
        assert "with_skill: 1 cases, 1 runs" in out and "1/1 = 100%" in out, out
        assert "_scratch" not in out and "_invalid:" not in out, out


# ------------------------------------------------------------------ kit install is not a code change

GITIGNORE_DIFF = """diff --git a/.gitignore b/.gitignore
--- a/.gitignore
+++ b/.gitignore
@@ -1,2 +1,4 @@
 .venv/
+# tpm off switch (user-local)
+.cadence/tpm.off
"""
KIT_STATUS = """ M .gitignore
?? .claude/settings.json
?? .claude/skills/tpm/SKILL.md
?? .cadence/tpm.off
?? outputs/01-message.md
"""
POST_SETUP = {
    "git_status_post_setup.txt": " M .gitignore\n?? .claude/settings.json\n?? .claude/skills/tpm/SKILL.md\n",
    ".gitignore.post_setup": ".venv/\n# tpm off switch (user-local)\n.cadence/tpm.off\n",
}


def _changed(run: Path) -> list[str]:
    return score.check_run(run, CASE)["code_or_test_files_changed"]


def test_kit_install_not_counted_as_code_changed():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        make_run(run, diff=GITIGNORE_DIFF, status=KIT_STATUS, files=POST_SETUP)
        assert _changed(run) == []


def test_real_changes_still_counted_next_to_the_install():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "r"
        app = "diff --git a/app/views.py b/app/views.py\n--- a/app/views.py\n+++ b/app/views.py\n+x = 1\n"
        make_run(
            run, diff=GITIGNORE_DIFF + app, status=KIT_STATUS + "?? tests/test_new.py\n", files=POST_SETUP
        )
        assert _changed(run) == ["app/views.py", "tests/test_new.py"]


def test_gitignore_counts_when_the_run_changed_it_beyond_the_install():
    extra = GITIGNORE_DIFF + "+build/\n"
    removed = GITIGNORE_DIFF.replace(" .venv/", "-.venv/")
    with tempfile.TemporaryDirectory() as tmp:
        for i, diff in enumerate((extra, removed)):
            run = Path(tmp) / f"r{i}"
            make_run(run, diff=diff, status=KIT_STATUS, files=POST_SETUP)
            assert _changed(run) == [".gitignore"], diff
        run = Path(tmp) / "no-snapshot"  # without the post-setup record nothing is excused
        make_run(run, diff=GITIGNORE_DIFF, status=KIT_STATUS)
        assert _changed(run) == [".gitignore"]


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
