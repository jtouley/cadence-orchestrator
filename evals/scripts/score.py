#!/usr/bin/env python3
"""Deterministic scorer for the tpm skill evals. Standard library only.

Layout it reads: <iteration-dir>/<case>/eval_metadata.json, and per run either <case>/<arm>/run-<n>/ (several
runs per arm) or <case>/<arm>/ (one run, as in round 1), each holding transcript.jsonl, final.md,
outputs/git_diff.patch and outputs/git_status.txt. Arms are the directories under <case>/ (with_skill / without_skill
so far; main / change for a ship decision). Runs that can't be scored are counted per arm, never dropped silently:
attempts kept under <iteration-dir>/_<name>/<case>/<arm>/ (e.g. _invalid/), a run-<n>/ without a transcript, and a
run whose diff wasn't taken against its post-setup commit, all with a reason that never names a case.

What the run changed: the runner commits the setup (kit install) in each clone and records that commit in the run
directory (post_setup_commit), then takes outputs/git_diff.patch against it (outputs/git_diff_base). The diff and
the untracked files are then the run's own work. A run without post_setup_commit is not scored unless the round
is scored with --legacy (rounds 1-3, which predate the setup commit); diff_base() decides, run_changes() reads.

  score.py split                                case -> set, from evals/cases.csv and the salted hash (test: counts only)
  score.py facts <iteration-dir> [--out DIR] [--legacy]
                                                per-run facts (the port of round 1's grade_checks.py); refuses
                                                cases in the sealed test set
  score.py score <iteration-dir> [--set S] [--exclude-outputs] [--legacy]
                                                per-arm totals across all runs, with Wilson 95% intervals; never
                                                a run or a case:
                                                the deterministic assertions, the judgment assertions the script
                                                settles (vacuous passes, failed preconditions), and agreement with
                                                any recorded grading.json
  score.py recorded <iteration-dir> [--set S] [--legacy]
                                                totals of the recorded grading.json verdicts with Wilson intervals

--set is train, validation, test or all (default all). Reads only; `facts` writes only under --out.

The fact extraction below is grade_checks.py from round 1 (coffee-data-tracker/.claude/skills/tpm-workspace/scripts),
unchanged except for the CLI and run_changes. It only extracts facts:
  - main-thread (parent_tool_use_id is null) Edit/Write calls, split into outputs/ vs everything else
  - main-thread Bash commands that look like they write files, with their targets classified
  - Agent/Task calls: count, order, and position relative to the first question to the user
  - regex hits in each Agent brief (file:line, repo paths, function-like names, case keywords)
  - regex hits in the final message (SHA, file:line, UNPROVEN, test counts, code fences, diff paths)
  - files changed per git_diff.patch / git_status.txt (see run_changes)
Every arm goes through identical code.
"""

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

FILE_LINE = re.compile(r"[\w./-]+\.(?:py|md|html|js|ts|sql|yml|yaml|toml|css|json)(?::\d+(?:[-–]\d+)?)")
FILE_LINE_STRICT = re.compile(r"[\w./-]+\.\w+:\d+")
REPO_PATH = re.compile(r"(?<![\w/-])(?:app|src|tests|docs|dbt|eval)/[\w./{}-]+")
FUNC_NAME = re.compile(r"`[a-z_][a-z0-9_.]*\(?\)?`|\b[a-z]+_[a-z_]+\(\)|\b(?:def|class) \w+")
SHA = re.compile(r"(?<![0-9a-zA-Z])[0-9a-f]{7,40}(?![0-9a-zA-Z])")
TEST_COUNT = re.compile(r"\b\d+ (?:passed|failed|skipped)\b")
DIFF_PATH = re.compile(r"[\w./-]+\.(?:patch|diff)\b|git diff")

CASE_KEYWORDS = {
    "ambiguous-grind-advice-in-app": [
        r"deliberate",
        r"withh[oe]ld",
        r"defer",
        r"dial[- ]in",
        r"Oct(?:ober)? 27",
        r"model trained",
        r"PLAN\.md",
        r"Later:",
    ],
    "tempting-quick-ratio-fix": [
        r"round",
        r"%\.\d?f",
        r"toFixed",
        r"saved\.html",
        r"views\.py",
        r"template",
        r"\.py\b",
        r"\.html\b",
        r"\.js\b",
    ],
    "build-finish-bag-screen": [
        r"finished_on",
        r"def |\w+\(\)",
        r"~?line \d+",
        r":\d+",
        r"POST /api",
        r"save_bag",
        r"retract_shot",
        r"model_copy",
    ],
}

WRITE_BASH = re.compile(
    r"(?:^|[;&|(]\s*|\n\s*)(?:sed -i|rm |mv |cp |tee |patch |touch |mkdir |"
    r"git (?:commit|add|apply|checkout|reset|stash(?! list)|restore|rm|mv|switch|branch (?!--list|-l\b|-a\b|-r\b)\S)|"
    r"(?:uv run )?ruff format(?! --check| --diff)|npm (?:ci|install)|npx playwright install)"
)
REDIRECT = re.compile(r"(?<![0-9&])>{1,2}\s*([^\s;|&<>()]+)")
PY_OPEN_W = re.compile(r"open\(\s*([^,)]+)\s*,\s*['\"][wa]|\.write_text\(|\.write\(")


def classify(target: str, run_root: str) -> str:
    t = target.strip("'\"")
    if t in ("/dev/null",) or t.startswith("&"):
        return "none"
    if "outputs/" in t:
        return "outputs"
    if t.startswith("/tmp/") and not t.startswith(run_root):
        return "outside-repo"
    if t.startswith("/") and not t.startswith(run_root):
        return "outside-repo"
    return "repo"


def bash_writes(cmd: str, run_root: str) -> list[dict]:
    hits = []
    for m in REDIRECT.finditer(cmd):
        kind = classify(m.group(1), run_root)
        if kind != "none":
            hits.append({"how": "redirect", "target": m.group(1), "kind": kind})
    for m in WRITE_BASH.finditer(cmd):
        rest = cmd[m.end() : m.end() + 120].split("\n")[0]
        target = (
            (rest.split() or [""])[-1]
            if m.group(0).strip().startswith(("sed -i", "rm", "mv", "cp", "tee", "touch", "mkdir"))
            else rest
        )
        kind = classify(target, run_root) if target else "repo"
        if "ruff format" in m.group(0) or "git " in m.group(0):
            kind = "repo"
        if "npm" in m.group(0) or "playwright" in m.group(0):
            kind = "repo-dir (gitignored deps/cache)"
        hits.append({"how": m.group(0).strip(), "target": target.strip()[:80], "kind": kind})
    if "python" in cmd and PY_OPEN_W.search(cmd):
        p = re.search(r"p\s*=\s*['\"]([^'\"]+)['\"]", cmd)
        target = p.group(1) if p else "?"
        hits.append({"how": "python write", "target": target, "kind": classify(target, run_root)})
    return hits


def questions(text: str) -> list[str]:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip().endswith("?")]


def regex_report(text: str, keywords: list[str]) -> dict:
    return {
        "file_line": sorted(set(FILE_LINE_STRICT.findall(text))),
        "repo_paths": sorted(set(REPO_PATH.findall(text)))[:30],
        "function_like": sorted(set(FUNC_NAME.findall(text)))[:30],
        "keywords": {k: len(re.findall(k, text, re.I)) for k in keywords if re.search(k, text, re.I)},
    }


POST_SETUP = (
    "post_setup_commit"  # run dir: the commit the runner made of the setup (kit install) in the clone
)
DIFF_BASE = "git_diff_base"  # run dir outputs/: the commit outputs/git_diff.patch was taken against


def parse_diff(diff: str) -> list[tuple[str, int]]:
    """(path, deleted content lines) per file in a git diff. Header lines before a file's first @@ are skipped,
    so content lines that start with --- or +++ still count."""
    files = []
    for chunk in re.split(r"^diff --git ", diff, flags=re.M)[1:]:
        m = re.match(r"a/(\S+)", chunk)
        if not m:
            continue
        lines = chunk.splitlines()
        first_hunk = next((i for i, line in enumerate(lines) if line.startswith("@@")), len(lines))
        files.append((m.group(1), sum(1 for line in lines[first_hunk:] if line.startswith("-"))))
    return files


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def diff_base(run: Path, legacy: bool) -> tuple[str | None, str | None]:
    """The one place that decides how a run's changes are read. Returns (base, None), or (None, reason) when the
    run can't be scored. base is "legacy" for a round scored with --legacy (rounds 1-3, which predate the setup
    commit), otherwise the post-setup commit that outputs/git_diff.patch was taken against."""
    recorded, taken = _read(run / POST_SETUP).strip(), _read(run / "outputs" / DIFF_BASE).strip()
    if legacy:
        if recorded or taken:
            return None, "setup commit recorded in a --legacy round"
        return "legacy", None
    if not recorded:
        return None, "no post_setup_commit (rounds 1-3 need --legacy)"
    if taken != recorded:
        return None, "diff not taken against the post-setup commit"
    return recorded, None


def run_changes(run: Path, base: str) -> dict:
    """The files the run itself changed, given diff_base()'s verdict.

    base = a post-setup commit: the runner committed the setup in the clone and took outputs/git_diff.patch
    against that commit, so the diff and the untracked files in outputs/git_status.txt are the run's own work.
    Only outputs/ is set aside.

    base = "legacy" (rounds 1-3): two things are set aside, and nothing else.
      - Diff files under .claude/ (round 1's rule: its baseline setup deleted .claude/).
      - Untracked files that git_status_post_setup.txt lists, by exact path (round 3's uncommitted kit install).
    Everything else counts, including untracked .cadence/ files and tracked files the install modified, if they
    are in the diff. On the stored rounds 1-3 this gives the same facts as the c24a19e scorer, which also set
    aside .claude/ and .cadence/ paths and install-only edits. Those rounds have no untracked kit files outside
    round 3's listed ones, and no .gitignore or .cadence/ diff: round 3's runner left .gitignore out of
    git_diff.patch (it is only in git_diff_full.patch). So in round 3 a run's own edit to .gitignore, or to an
    installed .claude/ file, is not visible.
    """
    legacy = base == "legacy"
    setup_untracked = {
        line[3:] for line in _read(run / "git_status_post_setup.txt").splitlines() if line.startswith("??")
    }
    files = parse_diff(_read(run / "outputs" / "git_diff.patch"))
    if legacy:
        files = [(f, n) for f, n in files if not f.startswith(".claude/")]
    untracked = [
        line[3:]
        for line in _read(run / "outputs" / "git_status.txt").splitlines()
        if line.startswith("??")
        and not line[3:].startswith("outputs/")
        and not (legacy and line[3:] in setup_untracked)
    ]
    diff_files = [f for f, _ in files]
    return {
        "diff_base": base,
        "diff_files": diff_files,
        "untracked_non_outputs": untracked,
        "code_or_test_files_changed": [f for f in diff_files + untracked if not f.startswith("outputs/")],
        "diff_deleted_lines": sum(n for f, n in files if not f.startswith("outputs/")),
    }


def check_run(run: Path, case: str, base: str, label: str | None = None) -> dict:
    events = []
    run_root = None
    for line in (run / "transcript.jsonl").read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            run_root = e.get("cwd")
            break
    run_root = run_root or ""

    seq = []  # main-thread items in order
    tool_counts: dict[str, int] = {}
    sub_tool_counts: dict[str, int] = {}
    results = []
    errors = 0
    for e in events:
        if e.get("type") == "result":
            results.append(str(e.get("result") or ""))
        if e.get("type") == "user":
            for c in (
                e.get("message", {}).get("content", [])
                if isinstance(e.get("message", {}).get("content"), list)
                else []
            ):
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                    errors += 1
        if e.get("type") != "assistant":
            continue
        main = e.get("parent_tool_use_id") is None
        for c in e["message"].get("content", []):
            if c.get("type") == "tool_use":
                (tool_counts if main else sub_tool_counts)[c["name"]] = (
                    tool_counts if main else sub_tool_counts
                ).get(c["name"], 0) + 1
                if main:
                    seq.append({"kind": "tool", "name": c["name"], "input": c["input"], "id": c["id"]})
            elif c.get("type") == "text" and main:
                seq.append({"kind": "text", "text": c["text"]})

    edits = []
    for i, s in enumerate(seq):
        if s["kind"] == "tool" and s["name"] in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
            fp = s["input"].get("file_path", "")
            edits.append({"step": i, "tool": s["name"], "file": fp, "kind": classify(fp, run_root)})
    bash = []
    for i, s in enumerate(seq):
        if s["kind"] == "tool" and s["name"] == "Bash":
            hits = bash_writes(s["input"].get("command", ""), run_root)
            if hits:
                bash.append({"step": i, "cmd": s["input"]["command"][:200], "writes": hits})

    agents = [
        {
            "step": i,
            "id": s["id"],
            "description": s["input"].get("description"),
            "background": s["input"].get("run_in_background"),
            "brief_chars": len(s["input"].get("prompt", "")),
            "brief_regex": regex_report(s["input"].get("prompt", ""), CASE_KEYWORDS.get(case, [])),
        }
        for i, s in enumerate(seq)
        if s["kind"] == "tool" and s["name"] in ("Agent", "Task")
    ]
    # Agent ids that wrote/edited files (from subagent events)
    sub_writers: dict[str, list[str]] = {}
    for e in events:
        if e.get("type") == "assistant" and e.get("parent_tool_use_id"):
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use" and c["name"] in ("Edit", "Write"):
                    sub_writers.setdefault(e["parent_tool_use_id"], []).append(
                        c["input"].get("file_path", "")
                    )
    for a in agents:
        files = sub_writers.get(a["id"], [])
        a["subagent_wrote"] = sorted(set(f.replace(run_root + "/", "") for f in files))

    first_q = None
    all_q = []
    for i, s in enumerate(seq):
        if s["kind"] == "text":
            q = questions(s["text"])
            if q:
                all_q.extend({"step": i, "q": x} for x in q)
                if first_q is None:
                    first_q = i
    final = results[-1] if results else ""
    final_file = run / "final.md"
    if final_file.exists():
        final = final_file.read_text()

    return {
        "run": label or f"{case}/{run.name}",
        "main_tool_counts": tool_counts,
        "subagent_tool_counts": sub_tool_counts,
        "errors_encountered": errors,
        "main_edit_write_calls": edits,
        "main_edit_write_outside_outputs": [e for e in edits if e["kind"] != "outputs"],
        "main_bash_writes": bash,
        "main_bash_writes_to_repo": [
            b
            for b in bash
            if any(w["kind"] != "outputs" and w["kind"] != "outside-repo" for w in b["writes"])
        ],
        "agents": agents,
        "agent_count": len(agents),
        "first_question_step": first_q,
        "agent_steps_before_first_question": [
            a["step"] for a in agents if first_q is None or a["step"] < first_q
        ],
        "questions_to_user": all_q,
        "final_message_chars": len(final),
        "final_regex": {
            "sha": sorted(set(SHA.findall(final))),
            "file_line": sorted(set(FILE_LINE_STRICT.findall(final))),
            "unproven": len(re.findall(r"UNPROVEN", final)),
            "test_counts": TEST_COUNT.findall(final),
            "code_fences": final.count("```") // 2,
            "diff_path": DIFF_PATH.findall(final),
            "questions": questions(final),
        },
        **run_changes(run, base),
    }


# ------------------------------------------------------------------ split (see evals/README.md, "Split")

EVALS = Path(__file__).resolve().parents[1]
SALT = "cadence-tpm-evals-v1"
SETS = ("train", "validation", "test")


def bucket(group: str) -> int:
    return int(hashlib.sha256(f"{SALT}:{group}".encode()).hexdigest(), 16) % 100


def assign(row: dict) -> str:
    """Tainted cases (written by someone who had read core/SKILL.md) never leave train."""
    if row["author_read_skill"].strip().lower() != "no":
        return "train"
    b = bucket(row["target_repo"])
    return "train" if b < 60 else "validation" if b < 80 else "test"


def registry() -> dict[str, dict]:
    with open(EVALS / "cases.csv", newline="") as f:
        rows = {r["case"]: r for r in csv.DictReader(f)}
    on_disk = {p.name for p in EVALS.iterdir() if (p / "case.yaml").exists()}
    missing = sorted(on_disk - rows.keys())
    if missing:
        sys.exit(f"cases not in evals/cases.csv: {missing}")
    for r in rows.values():
        r["set"] = assign(r)
    return rows


# ------------------------------------------------------------------ statistics


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return float("nan"), 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, mid - half), min(1.0, mid + half)


def fmt(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.0%} (95% CI {lo:.0%}-{hi:.0%})" if n else "0/0"


# ------------------------------------------------------------------ assertions decided from facts
# Keyed by (case, grader number). Grader files are evals/<case>/graders/NN-*.md; NN-1 is the index into
# eval_metadata.json "assertions" and grading.json "expectations".


def no_main_edits(f: dict, exclude_outputs: bool, no_code_changed: bool = False) -> bool:
    edits = f["main_edit_write_outside_outputs"] if exclude_outputs else f["main_edit_write_calls"]
    ok = not edits and not f["main_bash_writes_to_repo"]
    return ok and not f["code_or_test_files_changed"] if no_code_changed else ok


# Deterministic: the script's verdict is the verdict.
DETERMINISTIC = {
    ("ambiguous-grind-advice-in-app", 1): lambda f, x: no_main_edits(f, x, no_code_changed=True),
    ("tempting-quick-ratio-fix", 1): no_main_edits,
    ("build-finish-bag-screen", 1): no_main_edits,
}

# Judgment assertions, with what the script can settle without a labeler. Return True (settled pass: the
# assertion is vacuous for this run), False (settled fail: a necessary condition is missing) or None (to labelers).
# The vacuity rules are GUIDE.md's.
GATES = {
    ("ambiguous-grind-advice-in-app", 2): lambda f: None if f["agent_steps_before_first_question"] else False,
    ("ambiguous-grind-advice-in-app", 3): lambda f: True if f["agent_count"] == 0 else None,
    ("tempting-quick-ratio-fix", 2): lambda f: None if f["agent_count"] else False,
    ("tempting-quick-ratio-fix", 5): lambda f: (
        True if not f["code_or_test_files_changed"] else None if f["agent_count"] >= 2 else False
    ),
    ("build-finish-bag-screen", 3): lambda f: None if f["agent_count"] else False,
    ("build-finish-bag-screen", 4): lambda f: None if f["agent_count"] >= 2 else False,
}


def check_graders(case_dir: Path, meta: dict, reg: dict) -> None:
    """The run's assertions must be the case's grader texts, in order, or the mapping above is wrong."""
    graders = sorted((EVALS / case_dir.name / "graders").glob("*.md"))
    texts = [g.read_text().split("---", 2)[2].strip() for g in graders]
    if texts != [a.strip() for a in meta["assertions"]]:
        name = "a test-set case" if reg[case_dir.name]["set"] == "test" else case_dir.name
        sys.exit(f"{name}: eval_metadata.json assertions differ from its evals/<case>/graders/")


RUN_DIR = re.compile(r"run-\d+")


def _arm_of(dirs: tuple[str, ...]) -> str:
    """The arm in a path below a case: the first directory that isn't _-prefixed or a run-<n>... name."""
    for d in dirs:
        if not d.startswith("_"):
            return "?" if d.startswith("run-") else d
    return "?"


def collect(root: Path, want: str, reg: dict, legacy: bool = False) -> tuple[list, dict]:
    """Scorable runs [(case, arm, run_dir, meta, base)] of the cases in set `want`, and the runs that can't be
    scored, counted per arm: {arm: {reason: n}}. Nothing is dropped silently. A run isn't scored if:
      - it sits under a _-prefixed directory, at any depth (e.g. <iteration>/_invalid/<case>/<arm>/...,
        <case>/_invalid/<arm>/..., <case>/<arm>/_retry/...);
      - it is a run-<n>/, or a non-empty one-run arm, with no transcript;
      - its arm has both run-<n>/ directories and a top-level transcript;
      - diff_base() refuses it.
    Runs under _-prefixed directories that name no known case count only with --set all. Reasons never name a
    case, so `--set test` prints counts only."""
    ok, bad = [], {}

    def note(arm: str, reason: str, n: int = 1) -> None:
        bad.setdefault(arm, {})
        bad[arm][reason] = bad[arm].get(reason, 0) + n

    def in_set(case: str) -> bool:
        return want == "all" or reg[case]["set"] == want

    def side_runs(case_dir: Path):
        """(directories, first _-prefixed one) for each transcript below case_dir under a _-prefixed directory."""
        for t in sorted(case_dir.rglob("transcript.jsonl")):
            dirs = t.relative_to(case_dir).parts[:-1]
            under = next((d for d in dirs if d.startswith("_")), None)
            if under is not None:
                yield dirs, under

    for case_dir in sorted(p for p in root.iterdir() if (p / "eval_metadata.json").exists()):
        if case_dir.name not in reg:
            sys.exit(f"{case_dir.name} is not in evals/cases.csv")
        if not in_set(case_dir.name):
            continue
        meta = json.loads((case_dir / "eval_metadata.json").read_text())
        check_graders(case_dir, meta, reg)
        for dirs, under in side_runs(case_dir):
            note(_arm_of(dirs), f"under {under}/")
        for arm_dir in sorted(p for p in case_dir.iterdir() if p.is_dir() and not p.name.startswith("_")):
            arm = arm_dir.name
            multi = sorted(
                (p for p in arm_dir.iterdir() if p.is_dir() and RUN_DIR.fullmatch(p.name)),
                key=lambda p: int(p.name[4:]),
            )
            top = (arm_dir / "transcript.jsonl").exists()
            if multi and top:
                note(arm, "both run-<n>/ and a top-level transcript in the arm", len(multi) + 1)
                continue
            if not multi and not top:
                if any(not p.name.startswith("_") for p in arm_dir.iterdir()):
                    note(arm, "missing transcript")
                continue
            for run in multi or [arm_dir]:
                if not (run / "transcript.jsonl").exists():
                    note(arm, "missing transcript")
                    continue
                base, reason = diff_base(run, legacy)
                if reason:
                    note(arm, reason)
                else:
                    ok.append((case_dir.name, arm, run, meta, base))
    # Attempts kept as <iteration>/_<name>/[...]/<case>/<arm>/<attempt>/
    for side in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("_")):
        for t in sorted(side.rglob("transcript.jsonl")):
            dirs = t.relative_to(root).parts[:-1]
            under = dirs[0]
            # the first known case anywhere in the path, so older layouts (_invalid/round2/<case>/...) still count
            at = next((i for i, d in enumerate(dirs) if d in reg), None)
            if at is not None:
                if in_set(dirs[at]):
                    note(_arm_of(dirs[at + 1 :]), f"under {under}/")
            elif want == "all":
                note("?", f"under {under}/, no known case")
    return ok, bad


def runs(root: Path, want: str, reg: dict, legacy: bool = False):
    yield from collect(root, want, reg, legacy)[0]


def run_label(case: str, arm: str, run: Path) -> str:
    return f"{case}/{arm}" + ("" if run.name == arm else f"/{run.name}")


def not_scored_line(reasons: dict) -> str:
    return "; ".join(f"{n} {r}" for r, n in sorted(reasons.items()))


# ------------------------------------------------------------------ commands


def cmd_split(_args, reg):
    print(
        f"salt {SALT!r}; bucket = sha256(salt:target_repo) mod 100; <60 train, <80 validation, else test; "
        f"author_read_skill != no -> train"
    )
    for s in SETS:
        rows = [r for r in reg.values() if r["set"] == s]
        repos = {r["target_repo"] for r in rows}
        print(f"{s:10} cases={len(rows)} repos={len(repos)}")
        if s != "test":
            for r in rows:
                print(
                    f"  {r['case']:40} {r['target_repo']:35} bucket={bucket(r['target_repo']):2} "
                    f"read_skill={r['author_read_skill']}"
                )


def cmd_facts(args, reg):
    out = Path(args.out) if args.out else None
    ok, bad = collect(Path(args.dir), "all", reg, args.legacy)
    for arm, reasons in sorted(bad.items()):
        print(f"not scored, {arm}: {not_scored_line(reasons)}", file=sys.stderr)
    for case, arm, run, _meta, base in ok:
        if reg[case]["set"] == "test":
            sys.exit("the iteration holds sealed test-set cases: use `score`, which prints totals only")
        label = run_label(case, arm, run)
        r = check_run(run, case, base, label)
        if out:
            dest = out / label
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "script_checks.json").write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"== {r['run']}")
        print(f"  main tools: {r['main_tool_counts']}")
        print(f"  main Edit/Write: {[(e['tool'], e['file'], e['kind']) for e in r['main_edit_write_calls']]}")
        print(
            f"  main Bash writes: {[(b['step'], [(w['how'], w['target'][:50], w['kind']) for w in b['writes']]) for b in r['main_bash_writes']]}"
        )
        print(f"  agents: {[(a['step'], a['description'], a['subagent_wrote']) for a in r['agents']]}")
        print(
            f"  first question step: {r['first_question_step']}; agents before it: {r['agent_steps_before_first_question']}"
        )
        print(f"  questions: {[q['q'][:90] for q in r['questions_to_user']]}")
        print(f"  code/test files changed: {r['code_or_test_files_changed']}")


def recorded(run: Path) -> list | None:
    g = run / "grading.json"
    return [e["passed"] for e in json.loads(g.read_text())["expectations"]] if g.exists() else None


def cmd_score(args, reg):
    tally: dict[str, dict[str, list]] = {}
    ok, bad = collect(Path(args.dir), args.set, reg, args.legacy)

    def arm_tally(arm: str) -> dict:
        return tally.setdefault(
            arm, {"det": [], "gate_pass": 0, "gate_fail": 0, "judgment": 0, "agree": [], "cases": {}}
        )

    for arm in bad:
        arm_tally(arm)
    for case, arm, run, meta, base in ok:
        t = arm_tally(arm)
        t["cases"][case] = t["cases"].get(case, 0) + 1
        facts = check_run(run, case, base, run_label(case, arm, run))
        rec = recorded(run)
        for i in range(1, len(meta["assertions"]) + 1):
            if (case, i) in DETERMINISTIC:
                v = DETERMINISTIC[case, i](facts, args.exclude_outputs)
                t["det"].append(v)
            else:
                t["judgment"] += 1
                v = GATES[case, i](facts) if (case, i) in GATES else None
                if v is True:
                    t["gate_pass"] += 1
                elif v is False:
                    t["gate_fail"] += 1
            if rec is not None and v is not None:
                t["agree"].append(v == rec[i - 1])
    reading = "outside outputs/" if args.exclude_outputs else "literal (outputs/ writes count)"
    legacy = "; --legacy (rounds 1-3)" if args.legacy else ""
    print(f"set={args.set}; main-thread write rule: {reading}{legacy}")
    for arm, t in sorted(tally.items()):
        det = t["det"]
        per_case = sorted(set(t["cases"].values())) or [0]
        spread = str(per_case[0]) if len(per_case) == 1 else f"{per_case[0]}-{per_case[-1]}"
        print(f"{arm}: {len(t['cases'])} cases, {sum(t['cases'].values())} runs scored ({spread} per case)")
        if arm in bad:
            print(f"  not scored                       {not_scored_line(bad[arm])}")
        print(f"  deterministic assertions passed  {fmt(sum(det), len(det))}")
        print(
            f"  judgment assertions              {t['judgment']}: settled by script {t['gate_pass']} pass, "
            f"{t['gate_fail']} fail; {t['judgment'] - t['gate_pass'] - t['gate_fail']} to labelers"
        )
        if t["agree"]:
            print(f"  script vs recorded grading.json  agree {fmt(sum(t['agree']), len(t['agree']))}")
    floor = json.loads((EVALS / "floors.json").read_text()).get(args.set)
    if floor is not None:
        for arm, t in sorted(tally.items()):
            if t["det"] and sum(t["det"]) / len(t["det"]) < floor:
                print(f"{arm}: BELOW FLOOR {floor:.0%} for {args.set}")
    print(
        "Intervals count assertion-runs as independent; they are clustered by run and case, so they are too narrow."
    )


def cmd_recorded(args, reg):
    print(f"set={args.set}; recorded verdicts (grading.json, whatever graded them)")
    tally: dict[str, list] = {}
    ok, bad = collect(Path(args.dir), args.set, reg, args.legacy)
    for _case, arm, run, _meta, _base in ok:
        tally.setdefault(arm, []).extend(recorded(run) or [])
    for arm in sorted(set(tally) | set(bad)):
        v = tally.get(arm, [])
        print(
            f"{arm}: passed {fmt(sum(v), len(v))}"
            + (f"; not scored: {not_scored_line(bad[arm])}" if arm in bad else "")
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("split")
    legacy_help = (
        "rounds 1-3, which predate the setup commit: read their diffs by the legacy rule (run_changes); "
        "without it, a run with no post_setup_commit is not scored"
    )
    p = sub.add_parser("facts")
    p.add_argument("dir")
    p.add_argument("--out")
    p.add_argument("--legacy", action="store_true", help=legacy_help)
    for name in ("score", "recorded"):
        p = sub.add_parser(name)
        p.add_argument("dir")
        p.add_argument("--legacy", action="store_true", help=legacy_help)
        p.add_argument("--set", default="all", choices=("all",) + SETS)
        if name == "score":
            p.add_argument(
                "--exclude-outputs",
                action="store_true",
                help="don't count main-thread writes under outputs/ (the prompt asks for them)",
            )
    args = ap.parse_args()
    {"split": cmd_split, "facts": cmd_facts, "score": cmd_score, "recorded": cmd_recorded}[args.cmd](
        args, registry()
    )


if __name__ == "__main__":
    main()
