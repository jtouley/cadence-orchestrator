#!/usr/bin/env python3
"""Vendor the tpm kit into a repository for one or more agent platforms.

Copies core (SKILL.md, references, guard + runtime) and the platform shim into
the platform's skills directory, and merges hook config idempotently: earlier
tpm entries are replaced, everything else in the file is kept. Run once per
repo, then commit the result. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
ADAPTERS = os.path.join(ROOT, "adapters")
MARK = "skills/tpm/scripts/shim_"  # identifies our hook entries on re-install

TARGETS = {
    # target: skill dir, hook template -> destination, pointer files
    "claude": dict(skill=".claude/skills/tpm",
                   hooks=[("claude/settings.hooks.json", ".claude/settings.json")]),
    "copilot": dict(skill=".github/skills/tpm",
                    hooks=[("copilot/hooks.json", ".github/hooks/tpm.json")]),
    "codex": dict(skill=".agents/skills/tpm",
                  hooks=[("codex/hooks.json", ".codex/hooks.json")],
                  blocks=[("codex/AGENTS.pointer.md", "AGENTS.md")]),
    "cursor": dict(skill=".agents/skills/tpm",
                   hooks=[("cursor/hooks.json", ".cursor/hooks.json")],
                   files=[("cursor/tpm.mdc", ".cursor/rules/tpm.mdc")]),
    "gemini": dict(skill=".agents/skills/tpm",
                   hooks=[("gemini/settings.hooks.json", ".gemini/settings.json")],
                   blocks=[("gemini/GEMINI.pointer.md", "GEMINI.md")]),
}
BLOCK = re.compile(r"<!-- cadence-orchestrator:tpm begin -->.*?<!-- cadence-orchestrator:tpm end -->\n?",
                   re.S)


def template(rel: str, skill: str) -> str:
    return open(os.path.join(ADAPTERS, rel)).read().replace("__SKILL__", skill)


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def copy_skill(repo: str, target: str, skill: str) -> None:
    dest = os.path.join(repo, skill)
    os.makedirs(os.path.join(dest, "scripts"), exist_ok=True)
    text = open(os.path.join(CORE, "SKILL.md")).read()
    if target == "claude":
        # Claude Code only: the user, not the model, starts it (the guard arms on that).
        text = text.replace("\n---\n", "\ndisable-model-invocation: true\n---\n", 1)
    write(os.path.join(dest, "SKILL.md"), text)
    shutil.copytree(os.path.join(CORE, "references"), os.path.join(dest, "references"),
                    dirs_exist_ok=True)
    for name in ("guard.py", "runtime.py"):
        shutil.copy2(os.path.join(CORE, "scripts", name), os.path.join(dest, "scripts", name))
    shutil.copy2(os.path.join(ADAPTERS, target, "shim.py"),
                 os.path.join(dest, "scripts", f"shim_{target}.py"))


def merge_hooks(path: str, ours: dict) -> None:
    current = {}
    if os.path.exists(path):
        with open(path) as f:
            current = json.load(f)
    for key, value in ours.items():
        if key != "hooks":
            current.setdefault(key, value)
    hooks = current.setdefault("hooks", {})
    for event, entries in ours["hooks"].items():
        kept = [e for e in hooks.get(event, []) if MARK not in json.dumps(e)]
        hooks[event] = kept + entries
    write(path, json.dumps(current, indent=2) + "\n")


def add_block(path: str, block: str) -> None:
    text = open(path).read() if os.path.exists(path) else ""
    text = BLOCK.sub("", text).rstrip("\n")
    write(path, (text + "\n\n" if text else "") + block)


def add_gitignore(repo: str) -> None:
    # Ignore only the off switch: .cadence/catalog/ is meant to be committed.
    path = os.path.join(repo, ".gitignore")
    lines = open(path).read().split("\n") if os.path.exists(path) else []
    lines = [".cadence/tpm.off" if line == ".cadence/" else line for line in lines]  # older installs
    if ".cadence/tpm.off" not in lines:
        while lines and lines[-1] == "":
            lines.pop()
        lines += ["# tpm off switch (user-local)", ".cadence/tpm.off"]
    write(path, "\n".join(lines).rstrip("\n") + "\n")


def add_catalogs(repo: str, files: list[str]) -> list[str]:
    dest = os.path.join(repo, ".cadence", "catalog")
    os.makedirs(dest, exist_ok=True)
    out = []
    for f in files:
        if not f.endswith(".md"):
            raise SystemExit(f"install: catalog {f} must be a .md file")
        shutil.copy2(f, os.path.join(dest, os.path.basename(f)))
        out.append(".cadence/catalog/" + os.path.basename(f))
    return out


def install(repo: str, target: str) -> list[str]:
    spec = TARGETS[target]
    skill = spec["skill"]
    copy_skill(repo, target, skill)
    touched = [skill + "/"]
    for src, dst in spec.get("hooks", []):
        merge_hooks(os.path.join(repo, dst), json.loads(template(src, skill)))
        touched.append(dst)
    for src, dst in spec.get("files", []):
        write(os.path.join(repo, dst), template(src, skill))
        touched.append(dst)
    for src, dst in spec.get("blocks", []):
        add_block(os.path.join(repo, dst), template(src, skill))
        touched.append(dst)
    add_gitignore(repo)
    return touched


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True, choices=sorted(TARGETS) + ["all"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--catalog", action="append", default=[], metavar="FILE",
                    help="copy a skill catalog (.md) into <repo>/.cadence/catalog/; repeatable")
    a = ap.parse_args(argv)
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"install: {repo} is not a git repository root", file=sys.stderr)
        return 1
    for target in sorted(TARGETS) if a.target == "all" else [a.target]:
        print(f"{target}: " + ", ".join(install(repo, target)))
    if a.catalog:
        print("catalog: " + ", ".join(add_catalogs(repo, a.catalog)))
    print("Done. Review and commit the changes; see README for per-platform notes.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
