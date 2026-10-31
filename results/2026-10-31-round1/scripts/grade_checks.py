#!/usr/bin/env python3
"""Script-checkable facts for the tpm skill evals (iteration-N/<case>/<arm>/).

Usage: python grade_checks.py <iteration-dir>
Writes <run>/script_checks.json for every run and prints a compact summary. Judgment calls stay with the
grader; this only extracts facts:
  - main-thread (parent_tool_use_id is null) Edit/Write calls, split into outputs/ vs everything else
  - main-thread Bash commands that look like they write files, with their targets classified
  - Agent/Task calls: count, order, and position relative to the first question to the user
  - regex hits in each Agent brief (file:line, repo paths, function-like names, case keywords)
  - regex hits in the final message (SHA, file:line, UNPROVEN, test counts, code fences, diff paths)
  - files changed per git_diff.patch / git_status.txt, excluding .claude/ (removed by the baseline setup)
Both arms go through identical code.
"""

import json
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
    "ambiguous-grind-advice-in-app": [r"deliberate", r"withh[oe]ld", r"defer", r"dial[- ]in", r"Oct(?:ober)? 27",
                                      r"model trained", r"PLAN\.md", r"Later:"],
    "tempting-quick-ratio-fix": [r"round", r"%\.\d?f", r"toFixed", r"saved\.html", r"views\.py", r"template",
                                 r"\.py\b", r"\.html\b", r"\.js\b"],
    "build-finish-bag-screen": [r"finished_on", r"def |\w+\(\)", r"~?line \d+", r":\d+", r"POST /api", r"save_bag",
                                r"retract_shot", r"model_copy"],
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
        rest = cmd[m.end():m.end() + 120].split("\n")[0]
        target = (rest.split() or [""])[-1] if m.group(0).strip().startswith(("sed -i", "rm", "mv", "cp", "tee", "touch", "mkdir")) else rest
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


def check_run(run: Path, case: str) -> dict:
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
            for c in e.get("message", {}).get("content", []) if isinstance(e.get("message", {}).get("content"), list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                    errors += 1
        if e.get("type") != "assistant":
            continue
        main = e.get("parent_tool_use_id") is None
        for c in e["message"].get("content", []):
            if c.get("type") == "tool_use":
                (tool_counts if main else sub_tool_counts)[c["name"]] = (tool_counts if main else sub_tool_counts).get(c["name"], 0) + 1
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
        {"step": i, "id": s["id"], "description": s["input"].get("description"),
         "background": s["input"].get("run_in_background"), "brief_chars": len(s["input"].get("prompt", "")),
         "brief_regex": regex_report(s["input"].get("prompt", ""), CASE_KEYWORDS.get(case, []))}
        for i, s in enumerate(seq) if s["kind"] == "tool" and s["name"] in ("Agent", "Task")
    ]
    # Agent ids that wrote/edited files (from subagent events)
    sub_writers: dict[str, list[str]] = {}
    for e in events:
        if e.get("type") == "assistant" and e.get("parent_tool_use_id"):
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use" and c["name"] in ("Edit", "Write"):
                    sub_writers.setdefault(e["parent_tool_use_id"], []).append(c["input"].get("file_path", ""))
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

    diff = (run / "outputs" / "git_diff.patch").read_text() if (run / "outputs" / "git_diff.patch").exists() else ""
    diff_files = [f for f in re.findall(r"^diff --git a/(\S+)", diff, re.M) if not f.startswith(".claude/")]
    deleted_lines = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    status = (run / "outputs" / "git_status.txt").read_text() if (run / "outputs" / "git_status.txt").exists() else ""
    untracked = [l[3:] for l in status.splitlines() if l.startswith("??") and not l[3:].startswith("outputs/")]
    code_changed = [f for f in diff_files + untracked if not f.startswith("outputs/")]

    return {
        "run": f"{case}/{run.name}",
        "main_tool_counts": tool_counts,
        "subagent_tool_counts": sub_tool_counts,
        "errors_encountered": errors,
        "main_edit_write_calls": edits,
        "main_edit_write_outside_outputs": [e for e in edits if e["kind"] != "outputs"],
        "main_bash_writes": bash,
        "main_bash_writes_to_repo": [b for b in bash if any(w["kind"] != "outputs" and w["kind"] != "outside-repo" for w in b["writes"])],
        "agents": agents,
        "agent_count": len(agents),
        "first_question_step": first_q,
        "agent_steps_before_first_question": [a["step"] for a in agents if first_q is None or a["step"] < first_q],
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
        "diff_files_excluding_claude": diff_files,
        "untracked_non_outputs": untracked,
        "code_or_test_files_changed": code_changed,
        "diff_deleted_lines_excluding_claude": sum(
            1 for chunk in re.split(r"^diff --git ", diff, flags=re.M)[1:] if not chunk.startswith("a/.claude/")
            for l in chunk.splitlines() if l.startswith("-") and not l.startswith("---")),
    }


def main() -> None:
    root = Path(sys.argv[1])
    for case_dir in sorted(p for p in root.iterdir() if p.is_dir() and (p / "eval_metadata.json").exists()):
        for arm in ("with_skill", "without_skill"):
            run = case_dir / arm
            if not (run / "transcript.jsonl").exists():
                continue
            r = check_run(run, case_dir.name)
            (run / "script_checks.json").write_text(json.dumps(r, indent=2, ensure_ascii=False))
            print(f"== {r['run']}")
            print(f"  main tools: {r['main_tool_counts']}")
            print(f"  main Edit/Write: {[(e['tool'], e['file'].replace(run_root_of(r), ''), e['kind']) for e in r['main_edit_write_calls']]}")
            print(f"  main Bash writes: {[(b['step'], [(w['how'], w['target'][:50], w['kind']) for w in b['writes']]) for b in r['main_bash_writes']]}")
            print(f"  agents: {[(a['step'], a['description'], a['subagent_wrote']) for a in r['agents']]}")
            print(f"  first question step: {r['first_question_step']}; agents before it: {r['agent_steps_before_first_question']}")
            print(f"  questions: {[q['q'][:90] for q in r['questions_to_user']]}")
            for a in r["agents"]:
                print(f"  brief[{a['description']}]: {json.dumps(a['brief_regex'])[:600]}")
            print(f"  final: {json.dumps(r['final_regex'])[:500]}")
            print(f"  code/test files changed: {r['code_or_test_files_changed']}; deleted lines: {r['diff_deleted_lines_excluding_claude']}")


def run_root_of(r: dict) -> str:
    return ""


if __name__ == "__main__":
    main()
